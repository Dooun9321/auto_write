"""LangGraph agent state definition"""

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """State for the data analysis agent"""

    # Messages in the conversation
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # User's original question
    user_question: str

    # Analyzed code context from repository
    code_context: str

    # BigQuery schema context
    schema_context: str

    # Generated SQL query
    sql_query: str

    # Query execution results
    query_results: str

    # Data analysis insights
    analysis: str

    # Generated documentation
    documentation: str

    # Confluence page URL
    confluence_url: str

    # Error tracking
    error: str

    # Current step
    current_step: str
