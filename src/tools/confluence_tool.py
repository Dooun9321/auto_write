"""Confluence documentation tool"""

from atlassian import Confluence
from datetime import datetime
from typing import Optional, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class ConfluenceTool:
    """Tool for creating and updating Confluence documentation"""

    def __init__(
        self,
        url: str,
        username: str,
        api_token: str,
        space_key: str,
        parent_page_id: Optional[str] = None,
        llm = None,
    ):
        """
        Initialize Confluence client

        Args:
            url: Confluence base URL
            username: Confluence username/email
            api_token: Confluence API token
            space_key: Confluence space key
            parent_page_id: Optional parent page ID for creating documents
            llm: LLM instance for documentation generation
        """
        self.confluence = Confluence(url=url, username=username, password=api_token)
        self.space_key = space_key
        self.parent_page_id = parent_page_id
        self.llm = llm

    def generate_documentation(
        self,
        user_question: str,
        sql_query: str,
        query_results: str,
        analysis: str,
    ) -> Dict:
        """
        Generate documentation content using LLM

        Args:
            user_question: Original user question
            sql_query: SQL query used
            query_results: Results from query execution
            analysis: Analysis of the results

        Returns:
            Dictionary containing generated documentation
        """
        if not self.llm:
            return {
                "success": False,
                "error": "LLM not configured for documentation generation",
            }

        try:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are an expert data analyst creating comprehensive documentation.
Create clear, well-structured documentation that explains the analysis in a way that both technical and non-technical stakeholders can understand.

Use Confluence storage format (XHTML) for formatting.
Include:
- Executive Summary
- Analysis Question
- Methodology (SQL query with explanation)
- Key Findings
- Detailed Results
- Recommendations (if applicable)
- Technical Details

Make it professional and easy to understand.
""",
                    ),
                    (
                        "user",
                        """Create documentation for the following data analysis:

Question: {question}

SQL Query:
```sql
{query}
```

Query Results Summary:
{results}

Analysis:
{analysis}

Date: {date}

Generate comprehensive Confluence documentation in XHTML format.
""",
                    ),
                ]
            )

            chain = prompt | self.llm | StrOutputParser()

            content = chain.invoke(
                {
                    "question": user_question,
                    "query": sql_query,
                    "results": query_results[:2000],  # Limit results size
                    "analysis": analysis,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

            return {"success": True, "content": content}

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def create_page(
        self,
        title: str,
        content: str,
        parent_id: Optional[str] = None,
        labels: Optional[list] = None,
    ) -> Dict:
        """
        Create a new Confluence page

        Args:
            title: Page title
            content: Page content (in Confluence storage format)
            parent_id: Optional parent page ID
            labels: Optional list of labels to add

        Returns:
            Dictionary containing page information
        """
        try:
            # Create the page
            page = self.confluence.create_page(
                space=self.space_key,
                title=title,
                body=content,
                parent_id=parent_id,
                type="page",
                representation="storage",
            )

            page_id = page["id"]
            page_url = f"{self.confluence.url}/pages/viewpage.action?pageId={page_id}"

            # Add labels if provided
            if labels:
                for label in labels:
                    self.confluence.set_page_label(page_id, label)

            return {
                "success": True,
                "page_id": page_id,
                "page_url": page_url,
                "title": title,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def update_page(self, page_id: str, title: str, content: str) -> Dict:
        """
        Update an existing Confluence page

        Args:
            page_id: Page ID to update
            title: New page title
            content: New page content

        Returns:
            Dictionary containing update status
        """
        try:
            page = self.confluence.update_page(
                page_id=page_id,
                title=title,
                body=content,
                representation="storage",
            )

            page_url = f"{self.confluence.url}/pages/viewpage.action?pageId={page_id}"

            return {
                "success": True,
                "page_id": page_id,
                "page_url": page_url,
                "title": title,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def search_pages(self, query: str, limit: int = 10) -> Dict:
        """
        Search for Confluence pages

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            Dictionary containing search results
        """
        try:
            results = self.confluence.cql(
                f'space="{self.space_key}" AND text~"{query}"', limit=limit
            )

            pages = []
            for result in results.get("results", []):
                pages.append(
                    {
                        "id": result["content"]["id"],
                        "title": result["content"]["title"],
                        "url": f"{self.confluence.url}{result['content']['_links']['webui']}",
                    }
                )

            return {"success": True, "pages": pages, "count": len(pages)}

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def format_content_with_metadata(
        self, content: str, metadata: Dict
    ) -> str:
        """
        Add metadata panel to content

        Args:
            content: Main content
            metadata: Dictionary of metadata to display

        Returns:
            Formatted content with metadata
        """
        metadata_html = '<ac:structured-macro ac:name="info">\n<ac:rich-text-body>\n'
        metadata_html += "<table>\n"

        for key, value in metadata.items():
            metadata_html += f"<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>\n"

        metadata_html += "</table>\n"
        metadata_html += "</ac:rich-text-body>\n</ac:structured-macro>\n\n"

        return metadata_html + content
