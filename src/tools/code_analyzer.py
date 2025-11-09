"""Code analyzer for extracting SQL queries and patterns from repository"""

import os
import re
from pathlib import Path
from typing import List, Dict
import git


class CodeAnalyzer:
    """Analyzes repository code to find SQL queries and patterns"""

    def __init__(self, repo_path: str):
        """
        Initialize code analyzer

        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path)
        self.sql_extensions = [".sql", ".py", ".java", ".js", ".ts", ".go"]

    def analyze_repository(self, max_files: int = 100) -> Dict:
        """
        Analyze repository for SQL queries and patterns

        Args:
            max_files: Maximum number of files to analyze

        Returns:
            Dictionary containing analysis results
        """
        try:
            queries = []
            table_references = set()
            files_analyzed = 0

            for file_path in self._find_relevant_files():
                if files_analyzed >= max_files:
                    break

                file_queries = self._extract_queries_from_file(file_path)
                if file_queries:
                    queries.extend(file_queries)
                    files_analyzed += 1

                    # Extract table references
                    for query_info in file_queries:
                        tables = self._extract_table_names(query_info["query"])
                        table_references.update(tables)

            return {
                "success": True,
                "queries_found": len(queries),
                "files_analyzed": files_analyzed,
                "queries": queries[:50],  # Limit to 50 most recent
                "table_references": sorted(list(table_references)),
                "common_patterns": self._identify_patterns(queries),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _find_relevant_files(self) -> List[Path]:
        """Find files that might contain SQL queries"""
        relevant_files = []

        for ext in self.sql_extensions:
            relevant_files.extend(self.repo_path.rglob(f"*{ext}"))

        # Sort by modification time (most recent first)
        relevant_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        return relevant_files

    def _extract_queries_from_file(self, file_path: Path) -> List[Dict]:
        """Extract SQL queries from a file"""
        queries = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Pattern for SQL queries
            sql_patterns = [
                # Direct SQL queries
                r"(SELECT[\s\S]*?FROM[\s\S]*?(?:WHERE[\s\S]*?)?(?:GROUP BY[\s\S]*?)?(?:ORDER BY[\s\S]*?)?(?:LIMIT[\s\S]*?)?)[;\n]",
                # Queries in strings
                r'["\']\\s*(SELECT[\s\S]*?FROM[\s\S]*?)\\s*["\']',
                # BigQuery specific
                r"(WITH[\s\S]*?SELECT[\s\S]*?FROM[\s\S]*?)",
            ]

            for pattern in sql_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    query = match.group(1).strip()
                    if len(query) > 20:  # Filter out very short matches
                        queries.append(
                            {
                                "query": query,
                                "file": str(file_path.relative_to(self.repo_path)),
                                "type": self._categorize_query(query),
                            }
                        )

        except Exception as e:
            # Skip files that can't be read
            pass

        return queries

    def _extract_table_names(self, query: str) -> List[str]:
        """Extract table names from a SQL query"""
        tables = []

        # Pattern for table names after FROM and JOIN
        patterns = [
            r"FROM\s+`?([a-zA-Z0-9_\.]+)`?",
            r"JOIN\s+`?([a-zA-Z0-9_\.]+)`?",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                table_name = match.group(1)
                # Clean up table name
                table_name = table_name.split()[ 0].strip("`")
                tables.append(table_name)

        return tables

    def _categorize_query(self, query: str) -> str:
        """Categorize the type of SQL query"""
        query_upper = query.upper()

        if "INSERT" in query_upper:
            return "INSERT"
        elif "UPDATE" in query_upper:
            return "UPDATE"
        elif "DELETE" in query_upper:
            return "DELETE"
        elif "CREATE" in query_upper:
            return "CREATE"
        elif "WITH" in query_upper and "SELECT" in query_upper:
            return "CTE"
        elif "SELECT" in query_upper:
            if "JOIN" in query_upper:
                return "SELECT_JOIN"
            elif "GROUP BY" in query_upper:
                return "SELECT_AGGREGATION"
            else:
                return "SELECT"
        else:
            return "OTHER"

    def _identify_patterns(self, queries: List[Dict]) -> Dict:
        """Identify common patterns in queries"""
        patterns = {
            "total_queries": len(queries),
            "query_types": {},
            "common_tables": {},
            "uses_cte": 0,
            "uses_window_functions": 0,
            "uses_subqueries": 0,
        }

        for query_info in queries:
            query = query_info["query"]
            query_type = query_info["type"]

            # Count query types
            patterns["query_types"][query_type] = (
                patterns["query_types"].get(query_type, 0) + 1
            )

            # Check for advanced SQL features
            if "WITH" in query.upper():
                patterns["uses_cte"] += 1
            if any(
                window in query.upper()
                for window in ["ROW_NUMBER()", "RANK()", "DENSE_RANK()", "OVER("]
            ):
                patterns["uses_window_functions"] += 1
            if query.count("SELECT") > 1:
                patterns["uses_subqueries"] += 1

        return patterns

    def get_query_examples(self, query_type: str = None, limit: int = 5) -> List[str]:
        """
        Get example queries from the repository

        Args:
            query_type: Filter by query type (SELECT, JOIN, etc.)
            limit: Maximum number of examples to return

        Returns:
            List of example queries
        """
        analysis = self.analyze_repository()
        if not analysis.get("success"):
            return []

        queries = analysis.get("queries", [])

        if query_type:
            queries = [q for q in queries if q["type"] == query_type]

        return [q["query"] for q in queries[:limit]]
