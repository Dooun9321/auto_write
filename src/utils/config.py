"""Configuration management"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # Google Cloud
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
    BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "")

    # Confluence
    CONFLUENCE_URL = os.getenv("CONFLUENCE_URL", "")
    CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL", "")
    CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN", "")
    CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY", "")

    # Git Repository
    GIT_REPO_PATH = os.getenv("GIT_REPO_PATH", "./")
    GIT_TOKEN = os.getenv("GIT_TOKEN", "")
    GIT_USERNAME = os.getenv("GIT_USERNAME", "")
    GIT_PASSWORD = os.getenv("GIT_PASSWORD", "")

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """Validate required configuration"""
        missing = []

        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not cls.GCP_PROJECT_ID:
            missing.append("GCP_PROJECT_ID")

        return len(missing) == 0, missing
