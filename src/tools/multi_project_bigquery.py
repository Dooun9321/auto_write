"""Multi-project BigQuery tool with schema discovery"""

from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
from typing import Optional, List, Dict
from .bigquery_tool import BigQueryTool


class MultiProjectBigQueryTool:
    """Tool for working with multiple BigQuery projects"""

    def __init__(
        self,
        project_ids: List[str],
        credentials_path: Optional[str] = None,
        auto_discover_schemas: bool = True,
    ):
        """
        Initialize Multi-Project BigQuery client

        Args:
            project_ids: List of GCP project IDs
            credentials_path: Path to service account JSON
            auto_discover_schemas: Whether to automatically discover schemas
        """
        self.project_ids = project_ids
        self.credentials_path = credentials_path
        self.auto_discover_schemas = auto_discover_schemas

        # Create BigQueryTool for each project
        self.tools: Dict[str, BigQueryTool] = {}
        for project_id in project_ids:
            self.tools[project_id] = BigQueryTool(project_id, credentials_path)

        # Cache for schemas
        self.schema_cache: Dict[str, List[Dict]] = {}

        if auto_discover_schemas:
            print("🔍 Discovering BigQuery schemas across all projects...")
            self.discover_all_schemas()

    def discover_all_schemas(self) -> Dict[str, List[Dict]]:
        """
        Discover all datasets and tables across all projects

        Returns:
            Dictionary mapping project_id to list of datasets and tables
        """
        all_schemas = {}

        for project_id, tool in self.tools.items():
            try:
                print(f"  📊 Discovering schemas in project: {project_id}")
                datasets = self._discover_datasets(project_id, tool)
                all_schemas[project_id] = datasets
                self.schema_cache[project_id] = datasets
                print(f"    ✓ Found {len(datasets)} datasets")
            except Exception as e:
                print(f"    ✗ Error discovering schemas in {project_id}: {str(e)}")
                all_schemas[project_id] = []

        return all_schemas

    def _discover_datasets(
        self, project_id: str, tool: BigQueryTool
    ) -> List[Dict]:
        """Discover all datasets and tables in a project"""
        datasets_info = []

        try:
            client = tool.client
            datasets = list(client.list_datasets())

            for dataset in datasets:
                dataset_id = dataset.dataset_id
                dataset_info = {
                    "dataset_id": dataset_id,
                    "full_dataset_id": f"{project_id}.{dataset_id}",
                    "tables": [],
                }

                # List tables in the dataset
                try:
                    tables = list(client.list_tables(f"{project_id}.{dataset_id}"))
                    for table in tables:
                        table_info = {
                            "table_id": table.table_id,
                            "full_table_id": f"{project_id}.{dataset_id}.{table.table_id}",
                            "table_type": table.table_type,
                        }

                        # Get basic schema info
                        try:
                            table_obj = client.get_table(table_info["full_table_id"])
                            table_info["num_rows"] = table_obj.num_rows
                            table_info["schema_fields"] = [
                                {
                                    "name": field.name,
                                    "type": field.field_type,
                                    "description": field.description or "",
                                }
                                for field in table_obj.schema[:10]  # First 10 fields
                            ]
                        except Exception:
                            pass

                        dataset_info["tables"].append(table_info)

                except Exception as e:
                    print(f"      Warning: Could not list tables in {dataset_id}: {str(e)}")

                datasets_info.append(dataset_info)

        except Exception as e:
            print(f"    Error discovering datasets: {str(e)}")

        return datasets_info

    def execute_query(
        self, query: str, project_id: Optional[str] = None, max_results: int = 1000
    ) -> Dict:
        """
        Execute a SQL query on BigQuery

        Args:
            query: SQL query to execute
            project_id: Specific project ID (if None, tries to detect from query)
            max_results: Maximum number of results to return

        Returns:
            Dictionary containing results and metadata
        """
        # If no project specified, try to detect from query or use first project
        if not project_id:
            project_id = self._detect_project_from_query(query)

        if project_id not in self.tools:
            return {
                "success": False,
                "error": f"Project {project_id} not configured",
            }

        print(f"🔍 Executing query on project: {project_id}")
        result = self.tools[project_id].execute_query(query, max_results)
        result["project_id"] = project_id
        return result

    def _detect_project_from_query(self, query: str) -> str:
        """Try to detect which project a query should run on"""
        query_upper = query.upper()

        # Check if any project ID is mentioned in the query
        for project_id in self.project_ids:
            if project_id.upper() in query_upper or project_id.replace("-", "_").upper() in query_upper:
                return project_id

        # Default to first project
        return self.project_ids[0]

    def get_schema_context(self, include_sample_rows: bool = False) -> str:
        """
        Get a comprehensive schema context for all projects

        Args:
            include_sample_rows: Whether to include sample row counts

        Returns:
            Formatted string with schema information
        """
        context_parts = ["=== AVAILABLE BIGQUERY SCHEMAS ===\n"]

        for project_id, datasets in self.schema_cache.items():
            context_parts.append(f"\n📊 Project: {project_id}\n")
            context_parts.append(f"{'=' * 60}\n")

            for dataset in datasets:
                dataset_id = dataset["dataset_id"]
                tables = dataset.get("tables", [])

                context_parts.append(f"\n  Dataset: {dataset_id} ({len(tables)} tables)\n")

                for table in tables[:20]:  # Limit to 20 tables per dataset
                    table_id = table["table_id"]
                    full_table_id = table["full_table_id"]
                    num_rows = table.get("num_rows", "unknown")

                    context_parts.append(f"    • {full_table_id}")
                    if include_sample_rows:
                        context_parts.append(f" ({num_rows:,} rows)" if isinstance(num_rows, int) else f" ({num_rows})")
                    context_parts.append("\n")

                    # Include schema fields if available
                    schema_fields = table.get("schema_fields", [])
                    if schema_fields:
                        context_parts.append("      Fields:\n")
                        for field in schema_fields[:5]:  # Show first 5 fields
                            field_desc = f"        - {field['name']} ({field['type']})"
                            if field.get("description"):
                                field_desc += f": {field['description']}"
                            context_parts.append(field_desc + "\n")
                        if len(schema_fields) > 5:
                            context_parts.append(f"        ... and {len(schema_fields) - 5} more fields\n")

                if len(tables) > 20:
                    context_parts.append(f"    ... and {len(tables) - 20} more tables\n")

        return "".join(context_parts)

    def get_table_schema(self, project_id: str, dataset_id: str, table_id: str) -> Dict:
        """Get detailed schema for a specific table"""
        if project_id not in self.tools:
            return {
                "success": False,
                "error": f"Project {project_id} not configured",
            }

        return self.tools[project_id].get_table_schema(dataset_id, table_id)

    def list_all_tables(self) -> List[Dict]:
        """List all tables across all projects"""
        all_tables = []

        for project_id, datasets in self.schema_cache.items():
            for dataset in datasets:
                for table in dataset.get("tables", []):
                    all_tables.append(
                        {
                            "project_id": project_id,
                            "dataset_id": dataset["dataset_id"],
                            "table_id": table["table_id"],
                            "full_table_id": table["full_table_id"],
                            "num_rows": table.get("num_rows"),
                        }
                    )

        return all_tables

    def search_tables(self, keyword: str) -> List[Dict]:
        """Search for tables by keyword"""
        keyword_lower = keyword.lower()
        matching_tables = []

        for project_id, datasets in self.schema_cache.items():
            for dataset in datasets:
                for table in dataset.get("tables", []):
                    # Search in table name, dataset name, and field names
                    if (
                        keyword_lower in table["table_id"].lower()
                        or keyword_lower in dataset["dataset_id"].lower()
                    ):
                        matching_tables.append(
                            {
                                "project_id": project_id,
                                "dataset_id": dataset["dataset_id"],
                                "table_id": table["table_id"],
                                "full_table_id": table["full_table_id"],
                            }
                        )

        return matching_tables
