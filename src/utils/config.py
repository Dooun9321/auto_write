"""Configuration management"""

import os
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""

    # ============================================
    # LLM Configuration
    # ============================================
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

    # ============================================
    # BigQuery Configuration (Multi-Project)
    # ============================================
    @classmethod
    def get_bigquery_projects(cls) -> List[str]:
        """Get list of BigQuery projects"""
        projects_str = os.getenv("BIGQUERY_PROJECTS", "")
        if projects_str:
            try:
                projects = json.loads(projects_str)
                if isinstance(projects, list):
                    return projects
            except json.JSONDecodeError:
                pass

        # Fallback to single project (legacy)
        single_project = os.getenv("GCP_PROJECT_ID", "")
        if single_project:
            return [single_project]

        return []

    @classmethod
    def get_bigquery_datasets(cls) -> Dict[str, List[str]]:
        """Get datasets per project"""
        datasets_str = os.getenv("BIGQUERY_DATASETS", "{}")
        try:
            datasets = json.loads(datasets_str)
            if isinstance(datasets, dict):
                return datasets
        except json.JSONDecodeError:
            pass

        # Fallback to single dataset (legacy)
        single_dataset = os.getenv("BIGQUERY_DATASET", "")
        single_project = os.getenv("GCP_PROJECT_ID", "")
        if single_dataset and single_project:
            return {single_project: [single_dataset]}

        return {}

    # Legacy support
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
    BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "")

    # ============================================
    # Confluence Configuration
    # ============================================
    CONFLUENCE_URL = os.getenv("CONFLUENCE_URL", "")
    CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL", "")
    CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN", "")
    CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY", "")
    CONFLUENCE_PARENT_PAGE_ID = os.getenv("CONFLUENCE_PARENT_PAGE_ID", "")

    # ============================================
    # Git Repository Configuration (Multi-Repo)
    # ============================================
    @classmethod
    def get_git_repositories(cls) -> List[str]:
        """Get list of Git repositories"""
        repos_str = os.getenv("GIT_REPOSITORIES", "")
        if repos_str:
            try:
                repos = json.loads(repos_str)
                if isinstance(repos, list):
                    return repos
            except json.JSONDecodeError:
                pass

        # Fallback to single repo (legacy)
        single_repo = os.getenv("GIT_REPO_PATH", "./")
        return [single_repo]

    # Git Authentication (applies to all repos)
    GIT_TOKEN = os.getenv("GIT_TOKEN", "")
    GIT_USERNAME = os.getenv("GIT_USERNAME", "")
    GIT_PASSWORD = os.getenv("GIT_PASSWORD", "")

    # Legacy support
    GIT_REPO_PATH = os.getenv("GIT_REPO_PATH", "./")

    # ============================================
    # Advanced Settings
    # ============================================
    MAX_REPOS_TO_ANALYZE = int(os.getenv("MAX_REPOS_TO_ANALYZE", "10"))
    MAX_FILES_PER_REPO = int(os.getenv("MAX_FILES_PER_REPO", "50"))
    AUTO_DISCOVER_SCHEMAS = os.getenv("AUTO_DISCOVER_SCHEMAS", "true").lower() == "true"

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """Validate required configuration"""
        missing = []
        warnings = []

        # LLM validation
        if cls.LLM_PROVIDER == "openai":
            if not cls.OPENAI_API_KEY:
                missing.append("OPENAI_API_KEY")
        elif cls.LLM_PROVIDER == "gemini":
            if not cls.GEMINI_API_KEY:
                missing.append("GEMINI_API_KEY")
        else:
            warnings.append(f"Unknown LLM_PROVIDER: {cls.LLM_PROVIDER}, defaulting to openai")

        # BigQuery validation
        projects = cls.get_bigquery_projects()
        if not projects:
            missing.append("BIGQUERY_PROJECTS or GCP_PROJECT_ID")

        return len(missing) == 0, missing

    @classmethod
    def get_llm_config(cls) -> Dict:
        """Get LLM configuration based on provider"""
        if cls.LLM_PROVIDER == "gemini":
            return {
                "provider": "gemini",
                "api_key": cls.GEMINI_API_KEY,
                "model": cls.GEMINI_MODEL,
            }
        else:  # default to openai
            return {
                "provider": "openai",
                "api_key": cls.OPENAI_API_KEY,
                "model": cls.OPENAI_MODEL,
            }
