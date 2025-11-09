"""SQL query generator using LLM"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, List


class QueryGenerator:
    """Generates SQL queries based on user questions and code context"""

    def __init__(self, api_key: str = None, model: str = "gpt-4o", llm=None):
        """
        Initialize query generator

        Args:
            api_key: OpenAI API key (deprecated, use llm parameter)
            model: Model to use for generation (deprecated, use llm parameter)
            llm: LLM instance to use for generation
        """
        if llm:
            self.llm = llm
        elif api_key:
            # Legacy support
            self.llm = ChatOpenAI(
                api_key=api_key, model=model, temperature=0.1
            )
        else:
            raise ValueError("Either llm or api_key must be provided")

    def generate_query(
        self,
        user_question: str,
        code_context: Dict,
        dataset_info: Dict = None,
    ) -> Dict:
        """
        Generate SQL query based on user question and context

        Args:
            user_question: User's data analysis question
            code_context: Context from code repository analysis
            dataset_info: Information about available datasets and tables

        Returns:
            Dictionary containing generated query and explanation
        """
        try:
            # Build context string
            context_str = self._build_context_string(code_context, dataset_info)

            # Create prompt
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are an expert SQL query generator specializing in BigQuery.
Your task is to generate SQL queries that answer the user's question based on the provided context.

Guidelines:
- Use BigQuery syntax (backticks for table names, etc.)
- Follow the patterns and style from the example queries
- Include comments to explain complex logic
- Use CTEs for better readability when appropriate
- Optimize for performance
- Use appropriate aggregations and window functions
- Handle NULL values properly

Context from repository:
{context}
""",
                    ),
                    (
                        "user",
                        """Question: {question}

Generate a SQL query to answer this question. Provide:
1. The complete SQL query
2. A brief explanation of what the query does
3. Any assumptions made

Format your response as:
QUERY:
```sql
[your SQL query here]
```

EXPLANATION:
[brief explanation]

ASSUMPTIONS:
[any assumptions made]
""",
                    ),
                ]
            )

            # Generate query
            chain = prompt | self.llm | StrOutputParser()

            response = chain.invoke({"context": context_str, "question": user_question})

            # Parse response
            query, explanation, assumptions = self._parse_response(response)

            return {
                "success": True,
                "query": query,
                "explanation": explanation,
                "assumptions": assumptions,
                "raw_response": response,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _build_context_string(
        self, code_context: Dict, dataset_info: Dict = None
    ) -> str:
        """Build context string from code analysis and dataset info"""
        context_parts = []

        # Add schema context if available
        if code_context and code_context.get("schema_context"):
            context_parts.append(code_context["schema_context"])
            context_parts.append("\n\n")

        if code_context and code_context.get("success"):
            context_parts.append("=== CODE REPOSITORY ANALYSIS ===\n")
            context_parts.append(
                f"Found {code_context.get('queries_found', 0)} queries in {code_context.get('files_analyzed', 0)} files\n"
            )

            # Add table references
            tables = code_context.get("table_references", [])
            if tables:
                context_parts.append(f"\nKnown tables: {', '.join(tables[:20])}\n")

        # Add code context string if provided
        if code_context and code_context.get("code_context"):
            context_parts.append("\n")
            context_parts.append(code_context["code_context"])

            # Add common patterns
            patterns = code_context.get("common_patterns", {})
            if patterns:
                context_parts.append("\nQuery patterns:\n")
                for key, value in patterns.items():
                    context_parts.append(f"  - {key}: {value}\n")

            # Add example queries
            example_queries = code_context.get("queries", [])[:3]
            if example_queries:
                context_parts.append("\nExample queries from repository:\n")
                for i, query_info in enumerate(example_queries, 1):
                    context_parts.append(f"\n{i}. Type: {query_info['type']}\n")
                    context_parts.append(f"   File: {query_info['file']}\n")
                    context_parts.append(f"   Query:\n{query_info['query'][:500]}...\n")

        if dataset_info:
            context_parts.append("\n=== DATASET INFORMATION ===\n")
            context_parts.append(str(dataset_info))

        return "".join(context_parts)

    def _parse_response(self, response: str) -> tuple:
        """Parse LLM response to extract query, explanation, and assumptions"""
        query = ""
        explanation = ""
        assumptions = ""

        # Extract SQL query
        query_match = response.split("QUERY:")
        if len(query_match) > 1:
            query_section = query_match[1].split("EXPLANATION:")[0]
            # Extract from code block
            if "```sql" in query_section:
                query = query_section.split("```sql")[1].split("```")[0].strip()
            elif "```" in query_section:
                query = query_section.split("```")[1].split("```")[0].strip()
            else:
                query = query_section.strip()

        # Extract explanation
        expl_match = response.split("EXPLANATION:")
        if len(expl_match) > 1:
            explanation = expl_match[1].split("ASSUMPTIONS:")[0].strip()

        # Extract assumptions
        assump_match = response.split("ASSUMPTIONS:")
        if len(assump_match) > 1:
            assumptions = assump_match[1].strip()

        return query, explanation, assumptions

    def refine_query(
        self, original_query: str, error_message: str, user_feedback: str = ""
    ) -> Dict:
        """
        Refine a query based on errors or user feedback

        Args:
            original_query: The original SQL query
            error_message: Error message from query execution
            user_feedback: Optional feedback from user

        Returns:
            Dictionary containing refined query
        """
        try:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are an expert at debugging and refining BigQuery SQL queries.",
                    ),
                    (
                        "user",
                        """Original Query:
```sql
{query}
```

Error: {error}

User Feedback: {feedback}

Please provide a refined version of the query that fixes the issues.
Respond with only the corrected SQL query in a code block.
""",
                    ),
                ]
            )

            chain = prompt | self.llm | StrOutputParser()

            response = chain.invoke(
                {
                    "query": original_query,
                    "error": error_message,
                    "feedback": user_feedback or "None",
                }
            )

            # Extract refined query
            if "```sql" in response:
                refined_query = response.split("```sql")[1].split("```")[0].strip()
            elif "```" in response:
                refined_query = response.split("```")[1].split("```")[0].strip()
            else:
                refined_query = response.strip()

            return {"success": True, "query": refined_query, "raw_response": response}

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
