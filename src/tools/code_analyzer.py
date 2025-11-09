"""Code analyzer for extracting SQL queries and patterns from repository"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional
import git
import tempfile
import shutil


class CodeAnalyzer:
    """Analyzes repository code to find SQL queries and patterns"""

    def __init__(
        self,
        repo_path: str,
        git_token: Optional[str] = None,
        git_username: Optional[str] = None,
        git_password: Optional[str] = None,
    ):
        """
        Initialize code analyzer

        Args:
            repo_path: Path to local git repository or remote git URL
            git_token: Personal access token for private repositories
            git_username: Git username (alternative to token)
            git_password: Git password (alternative to token)
        """
        self.original_repo_path = repo_path
        self.git_token = git_token
        self.git_username = git_username
        self.git_password = git_password
        self.sql_extensions = [".sql", ".py", ".java", ".js", ".ts", ".go"]
        self.temp_dir = None
        self.repo_path = None

        # Determine if it's a remote URL or local path
        if self._is_remote_url(repo_path):
            self.repo_path = self._clone_repository(repo_path)
        else:
            self.repo_path = Path(repo_path)

    def _is_remote_url(self, path: str) -> bool:
        """Check if the path is a remote git URL"""
        return path.startswith(("http://", "https://", "git@", "ssh://"))

    def _clone_repository(self, repo_url: str) -> Path:
        """
        Clone a remote repository to a temporary directory

        Args:
            repo_url: Remote git repository URL

        Returns:
            Path to cloned repository
        """
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="code_analyzer_")
            temp_path = Path(self.temp_dir)

            # Build authenticated URL if token is provided
            if self.git_token and repo_url.startswith("https://"):
                # For GitHub, GitLab, Bitbucket: https://token@github.com/user/repo.git
                parts = repo_url.replace("https://", "").split("/", 1)
                if len(parts) == 2:
                    host, path = parts
                    repo_url = f"https://{self.git_token}@{host}/{path}"
            elif self.git_username and self.git_password and repo_url.startswith("https://"):
                # Username/password authentication
                parts = repo_url.replace("https://", "").split("/", 1)
                if len(parts) == 2:
                    host, path = parts
                    repo_url = f"https://{self.git_username}:{self.git_password}@{host}/{path}"

            # Clone the repository
            print(f"Cloning repository from {self.original_repo_path}...")
            git.Repo.clone_from(
                repo_url,
                temp_path,
                depth=1,  # Shallow clone for faster cloning
            )
            print(f"Repository cloned to {temp_path}")

            return temp_path

        except git.GitCommandError as e:
            raise Exception(
                f"Failed to clone repository: {str(e)}. "
                "Please check the URL and authentication credentials."
            )
        except Exception as e:
            # Clean up temp directory if cloning failed
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            raise Exception(f"Error cloning repository: {str(e)}")

    def cleanup(self):
        """Clean up temporary directory if it was created"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                print(f"Warning: Failed to clean up temp directory: {str(e)}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()

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
