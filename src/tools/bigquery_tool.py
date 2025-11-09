"""BigQuery integration tool"""

from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
from typing import Optional
import json


class BigQueryTool:
    """Tool for executing queries on BigQuery"""

    def __init__(self, project_id: str, credentials_path: Optional[str] = None):
        """
        Initialize BigQuery client

        Args:
            project_id: GCP project ID
            credentials_path: Path to service account JSON (optional, uses default credentials if not provided)
        """
        self.project_id = project_id

        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            self.client = bigquery.Client(
                project=project_id, credentials=credentials
            )
        else:
            # Use application default credentials
            self.client = bigquery.Client(project=project_id)

    def execute_query(self, query: str, max_results: int = 1000) -> dict:
        """
        Execute a SQL query on BigQuery

        Args:
            query: SQL query to execute
            max_results: Maximum number of results to return

        Returns:
            Dictionary containing results and metadata
        """
        try:
            query_job = self.client.query(query)
            results = query_job.result(max_results=max_results)

            # Convert to pandas DataFrame
            df = results.to_dataframe()

            # Get query statistics
            stats = {
                "total_rows": query_job.total_rows,
                "total_bytes_processed": query_job.total_bytes_processed,
                "total_bytes_billed": query_job.total_bytes_billed,
                "cache_hit": query_job.cache_hit,
            }

            return {
                "success": True,
                "data": df.to_dict(orient="records"),
                "columns": list(df.columns),
                "row_count": len(df),
                "stats": stats,
                "summary": self._generate_summary(df),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _generate_summary(self, df: pd.DataFrame) -> str:
        """Generate a summary of the query results"""
        summary = f"Query returned {len(df)} rows with {len(df.columns)} columns.\n\n"

        if len(df) > 0:
            summary += "Column types:\n"
            for col in df.columns:
                summary += f"  - {col}: {df[col].dtype}\n"

            summary += f"\nFirst few rows:\n{df.head(10).to_string()}\n"

            # Basic statistics for numeric columns
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                summary += f"\nNumeric column statistics:\n{df[numeric_cols].describe().to_string()}\n"

        return summary

    def get_table_schema(self, dataset_id: str, table_id: str) -> dict:
        """
        Get schema information for a table

        Args:
            dataset_id: Dataset ID
            table_id: Table ID

        Returns:
            Dictionary containing schema information
        """
        try:
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            table = self.client.get_table(table_ref)

            schema_info = {
                "success": True,
                "table": table_ref,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "created": str(table.created),
                "modified": str(table.modified),
                "schema": [
                    {
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode,
                        "description": field.description,
                    }
                    for field in table.schema
                ],
            }

            return schema_info

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def list_tables(self, dataset_id: str) -> dict:
        """
        List all tables in a dataset

        Args:
            dataset_id: Dataset ID

        Returns:
            Dictionary containing list of tables
        """
        try:
            dataset_ref = f"{self.project_id}.{dataset_id}"
            tables = list(self.client.list_tables(dataset_ref))

            table_list = [
                {
                    "table_id": table.table_id,
                    "full_table_id": f"{self.project_id}.{dataset_id}.{table.table_id}",
                }
                for table in tables
            ]

            return {"success": True, "dataset": dataset_ref, "tables": table_list}

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
