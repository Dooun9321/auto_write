"""Multi-repository analyzer for extracting SQL queries from multiple Git repositories"""

from typing import List, Dict, Optional
from .code_analyzer import CodeAnalyzer


class MultiRepoAnalyzer:
    """Analyzes multiple Git repositories for SQL queries and patterns"""

    def __init__(
        self,
        repo_paths: List[str],
        git_token: Optional[str] = None,
        git_username: Optional[str] = None,
        git_password: Optional[str] = None,
        max_repos: int = 10,
        max_files_per_repo: int = 50,
    ):
        """
        Initialize multi-repository analyzer

        Args:
            repo_paths: List of repository paths or URLs
            git_token: Personal access token for private repositories
            git_username: Git username
            git_password: Git password
            max_repos: Maximum number of repositories to analyze
            max_files_per_repo: Maximum files to analyze per repository
        """
        self.repo_paths = repo_paths[:max_repos]
        self.git_token = git_token
        self.git_username = git_username
        self.git_password = git_password
        self.max_files_per_repo = max_files_per_repo
        self.analyzers: List[CodeAnalyzer] = []

    def analyze_all_repositories(self) -> Dict:
        """
        Analyze all configured repositories

        Returns:
            Dictionary containing aggregated analysis results
        """
        all_queries = []
        all_table_references = set()
        total_files_analyzed = 0
        repos_analyzed = 0
        errors = []

        for repo_path in self.repo_paths:
            try:
                print(f"\n📦 Analyzing repository: {repo_path}")

                analyzer = CodeAnalyzer(
                    repo_path=repo_path,
                    git_token=self.git_token,
                    git_username=self.git_username,
                    git_password=self.git_password,
                )
                self.analyzers.append(analyzer)

                result = analyzer.analyze_repository(max_files=self.max_files_per_repo)

                if result.get("success"):
                    queries = result.get("queries", [])
                    # Add repository info to each query
                    for query in queries:
                        query["repository"] = repo_path

                    all_queries.extend(queries)
                    all_table_references.update(result.get("table_references", []))
                    total_files_analyzed += result.get("files_analyzed", 0)
                    repos_analyzed += 1

                    print(
                        f"✓ Found {result.get('queries_found', 0)} queries in {result.get('files_analyzed', 0)} files"
                    )
                else:
                    error_msg = f"Failed to analyze {repo_path}: {result.get('error', 'Unknown error')}"
                    errors.append(error_msg)
                    print(f"✗ {error_msg}")

            except Exception as e:
                error_msg = f"Error analyzing {repo_path}: {str(e)}"
                errors.append(error_msg)
                print(f"✗ {error_msg}")
                continue

        # Aggregate patterns
        aggregated_patterns = self._aggregate_patterns(all_queries)

        return {
            "success": True,
            "repositories_analyzed": repos_analyzed,
            "total_repositories": len(self.repo_paths),
            "queries_found": len(all_queries),
            "files_analyzed": total_files_analyzed,
            "queries": all_queries[:100],  # Limit to 100 most recent
            "table_references": sorted(list(all_table_references)),
            "common_patterns": aggregated_patterns,
            "errors": errors,
        }

    def _aggregate_patterns(self, queries: List[Dict]) -> Dict:
        """Aggregate patterns from all queries"""
        patterns = {
            "total_queries": len(queries),
            "query_types": {},
            "repositories": {},
            "uses_cte": 0,
            "uses_window_functions": 0,
            "uses_subqueries": 0,
        }

        for query_info in queries:
            query = query_info["query"]
            query_type = query_info.get("type", "OTHER")
            repo = query_info.get("repository", "unknown")

            # Count query types
            patterns["query_types"][query_type] = (
                patterns["query_types"].get(query_type, 0) + 1
            )

            # Count queries per repository
            patterns["repositories"][repo] = patterns["repositories"].get(repo, 0) + 1

            # Check for advanced SQL features
            query_upper = query.upper()
            if "WITH" in query_upper:
                patterns["uses_cte"] += 1
            if any(
                window in query_upper
                for window in ["ROW_NUMBER()", "RANK()", "DENSE_RANK()", "OVER("]
            ):
                patterns["uses_window_functions"] += 1
            if query.count("SELECT") > 1:
                patterns["uses_subqueries"] += 1

        return patterns

    def cleanup(self):
        """Clean up all analyzers"""
        for analyzer in self.analyzers:
            try:
                analyzer.cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup analyzer: {str(e)}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
