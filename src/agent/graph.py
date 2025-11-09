"""LangGraph workflow for data analysis agent"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..agent.state import AgentState
from ..tools.code_analyzer import CodeAnalyzer
from ..tools.query_generator import QueryGenerator
from ..tools.bigquery_tool import BigQueryTool
from ..tools.confluence_tool import ConfluenceTool
from ..utils.config import Config


class DataAnalysisAgent:
    """LangGraph-based data analysis agent"""

    def __init__(self, config: Config = None):
        """Initialize the agent with configuration"""
        self.config = config or Config()

        # Initialize tools
        self.code_analyzer = CodeAnalyzer(
            repo_path=self.config.GIT_REPO_PATH,
            git_token=self.config.GIT_TOKEN,
            git_username=self.config.GIT_USERNAME,
            git_password=self.config.GIT_PASSWORD,
        )
        self.query_generator = QueryGenerator(self.config.OPENAI_API_KEY)
        self.bq_tool = BigQueryTool(self.config.GCP_PROJECT_ID)
        self.confluence_tool = None

        if all(
            [
                self.config.CONFLUENCE_URL,
                self.config.CONFLUENCE_EMAIL,
                self.config.CONFLUENCE_API_TOKEN,
            ]
        ):
            self.confluence_tool = ConfluenceTool(
                url=self.config.CONFLUENCE_URL,
                username=self.config.CONFLUENCE_EMAIL,
                api_token=self.config.CONFLUENCE_API_TOKEN,
                space_key=self.config.CONFLUENCE_SPACE_KEY,
                openai_api_key=self.config.OPENAI_API_KEY,
            )

        # Initialize LLM for analysis
        self.llm = ChatOpenAI(
            api_key=self.config.OPENAI_API_KEY, model="gpt-4o", temperature=0.2
        )

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("analyze_code", self._analyze_code_node)
        workflow.add_node("generate_query", self._generate_query_node)
        workflow.add_node("execute_query", self._execute_query_node)
        workflow.add_node("analyze_results", self._analyze_results_node)
        workflow.add_node("create_documentation", self._create_documentation_node)
        workflow.add_node("publish_to_confluence", self._publish_to_confluence_node)

        # Define edges
        workflow.set_entry_point("analyze_code")
        workflow.add_edge("analyze_code", "generate_query")
        workflow.add_edge("generate_query", "execute_query")
        workflow.add_edge("execute_query", "analyze_results")
        workflow.add_edge("analyze_results", "create_documentation")

        # Conditional edge: only publish if Confluence is configured
        workflow.add_conditional_edges(
            "create_documentation",
            self._should_publish_to_confluence,
            {
                "publish": "publish_to_confluence",
                "end": END,
            },
        )
        workflow.add_edge("publish_to_confluence", END)

        return workflow.compile()

    def _analyze_code_node(self, state: AgentState) -> AgentState:
        """Analyze code repository for SQL patterns"""
        state["current_step"] = "Analyzing code repository..."

        try:
            analysis_result = self.code_analyzer.analyze_repository(max_files=50)

            if analysis_result.get("success"):
                # Format code context
                context = f"""
Repository Analysis:
- Queries found: {analysis_result.get('queries_found', 0)}
- Files analyzed: {analysis_result.get('files_analyzed', 0)}
- Tables referenced: {', '.join(analysis_result.get('table_references', [])[:10])}

Common patterns:
{analysis_result.get('common_patterns', {})}

Example queries available: {len(analysis_result.get('queries', []))}
"""
                state["code_context"] = context
                state["messages"] = state.get("messages", []) + [
                    AIMessage(content=f"Code analysis complete. {context}")
                ]
            else:
                state["code_context"] = "No code context available"
                state["error"] = analysis_result.get("error", "Unknown error")

        except Exception as e:
            state["error"] = str(e)
            state["code_context"] = "Error analyzing code"

        return state

    def _generate_query_node(self, state: AgentState) -> AgentState:
        """Generate SQL query based on question and code context"""
        state["current_step"] = "Generating SQL query..."

        try:
            # Prepare code context
            code_context = {"success": True, "queries": [], "table_references": []}

            result = self.query_generator.generate_query(
                user_question=state["user_question"],
                code_context=code_context,
            )

            if result.get("success"):
                state["sql_query"] = result["query"]
                state["messages"] = state.get("messages", []) + [
                    AIMessage(
                        content=f"Generated SQL query:\n```sql\n{result['query']}\n```\n\nExplanation: {result.get('explanation', '')}"
                    )
                ]
            else:
                state["error"] = result.get("error", "Failed to generate query")
                state["sql_query"] = ""

        except Exception as e:
            state["error"] = str(e)
            state["sql_query"] = ""

        return state

    def _execute_query_node(self, state: AgentState) -> AgentState:
        """Execute the generated SQL query"""
        state["current_step"] = "Executing query on BigQuery..."

        if not state.get("sql_query"):
            state["error"] = "No query to execute"
            return state

        try:
            result = self.bq_tool.execute_query(state["sql_query"])

            if result.get("success"):
                state["query_results"] = result["summary"]
                state["messages"] = state.get("messages", []) + [
                    AIMessage(
                        content=f"Query executed successfully!\n\nResults:\n{result['summary'][:1000]}"
                    )
                ]
            else:
                state["error"] = result.get("error", "Query execution failed")
                state["query_results"] = ""

                # Try to refine query if there's an error
                refined = self.query_generator.refine_query(
                    state["sql_query"], state["error"]
                )
                if refined.get("success"):
                    state["sql_query"] = refined["query"]
                    # Retry execution
                    retry_result = self.bq_tool.execute_query(state["sql_query"])
                    if retry_result.get("success"):
                        state["query_results"] = retry_result["summary"]
                        state["error"] = ""

        except Exception as e:
            state["error"] = str(e)
            state["query_results"] = ""

        return state

    def _analyze_results_node(self, state: AgentState) -> AgentState:
        """Analyze query results using LLM"""
        state["current_step"] = "Analyzing results..."

        if not state.get("query_results"):
            state["analysis"] = "No results to analyze"
            return state

        try:
            prompt = f"""
Analyze the following data query results and provide insights:

Original Question: {state['user_question']}

SQL Query:
```sql
{state['sql_query']}
```

Results:
{state['query_results'][:2000]}

Provide:
1. Key findings
2. Trends or patterns
3. Insights and recommendations
4. Any limitations or caveats
"""

            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)

            state["analysis"] = response.content
            state["messages"] = state.get("messages", []) + [
                AIMessage(content=f"Analysis:\n{response.content}")
            ]

        except Exception as e:
            state["error"] = str(e)
            state["analysis"] = "Error analyzing results"

        return state

    def _create_documentation_node(self, state: AgentState) -> AgentState:
        """Create documentation content"""
        state["current_step"] = "Creating documentation..."

        if not self.confluence_tool:
            # Create simple markdown documentation
            doc = f"""# Data Analysis: {state['user_question']}

## Query
```sql
{state['sql_query']}
```

## Results
{state['query_results'][:1000]}

## Analysis
{state['analysis']}
"""
            state["documentation"] = doc
            return state

        try:
            result = self.confluence_tool.generate_documentation(
                user_question=state["user_question"],
                sql_query=state["sql_query"],
                query_results=state["query_results"],
                analysis=state["analysis"],
            )

            if result.get("success"):
                state["documentation"] = result["content"]
            else:
                state["error"] = result.get("error", "Documentation generation failed")

        except Exception as e:
            state["error"] = str(e)

        return state

    def _publish_to_confluence_node(self, state: AgentState) -> AgentState:
        """Publish documentation to Confluence"""
        state["current_step"] = "Publishing to Confluence..."

        if not self.confluence_tool:
            state["error"] = "Confluence not configured"
            return state

        try:
            # Create page title from question
            from datetime import datetime

            title = f"Data Analysis: {state['user_question'][:100]} - {datetime.now().strftime('%Y-%m-%d')}"

            result = self.confluence_tool.create_page(
                title=title,
                content=state["documentation"],
                labels=["data-analysis", "auto-generated"],
            )

            if result.get("success"):
                state["confluence_url"] = result["page_url"]
                state["messages"] = state.get("messages", []) + [
                    AIMessage(
                        content=f"Documentation published to Confluence: {result['page_url']}"
                    )
                ]
            else:
                state["error"] = result.get("error", "Failed to publish to Confluence")

        except Exception as e:
            state["error"] = str(e)

        return state

    def _should_publish_to_confluence(self, state: AgentState) -> str:
        """Determine if we should publish to Confluence"""
        if self.confluence_tool and state.get("documentation"):
            return "publish"
        return "end"

    def run(self, user_question: str) -> AgentState:
        """
        Run the agent workflow

        Args:
            user_question: User's data analysis question

        Returns:
            Final state after workflow completion
        """
        initial_state = {
            "messages": [HumanMessage(content=user_question)],
            "user_question": user_question,
            "code_context": "",
            "sql_query": "",
            "query_results": "",
            "analysis": "",
            "documentation": "",
            "confluence_url": "",
            "error": "",
            "current_step": "",
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        return final_state

    def stream(self, user_question: str):
        """
        Stream the agent workflow for real-time updates

        Args:
            user_question: User's data analysis question

        Yields:
            State updates as the workflow progresses
        """
        initial_state = {
            "messages": [HumanMessage(content=user_question)],
            "user_question": user_question,
            "code_context": "",
            "sql_query": "",
            "query_results": "",
            "analysis": "",
            "documentation": "",
            "confluence_url": "",
            "error": "",
            "current_step": "",
        }

        # Stream the graph
        for state in self.graph.stream(initial_state):
            yield state
