"""Enhanced LangGraph workflow with multi-project and multi-repo support"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from ..agent.state import AgentState
from ..tools.multi_repo_analyzer import MultiRepoAnalyzer
from ..tools.query_generator import QueryGenerator
from ..tools.multi_project_bigquery import MultiProjectBigQueryTool
from ..tools.confluence_tool import ConfluenceTool
from ..utils.config import Config
from ..utils.llm_factory import LLMFactory


class EnhancedDataAnalysisAgent:
    """Enhanced LangGraph-based data analysis agent with multi-project support"""

    def __init__(self, config: Config = None):
        """Initialize the enhanced agent with configuration"""
        self.config = config or Config()

        # Get LLM configuration
        llm_config = self.config.get_llm_config()
        print(f"🤖 Using LLM: {llm_config['provider']} - {llm_config['model']}")

        # Initialize LLMs for different purposes
        self.query_llm = LLMFactory.create_query_generator_llm(llm_config)
        self.analysis_llm = LLMFactory.create_analysis_llm(llm_config)
        self.doc_llm = LLMFactory.create_documentation_llm(llm_config)

        # Initialize multi-repository analyzer
        git_repos = self.config.get_git_repositories()
        print(f"📂 Configured {len(git_repos)} Git repositories")

        self.code_analyzer = MultiRepoAnalyzer(
            repo_paths=git_repos,
            git_token=self.config.GIT_TOKEN,
            git_username=self.config.GIT_USERNAME,
            git_password=self.config.GIT_PASSWORD,
            max_repos=self.config.MAX_REPOS_TO_ANALYZE,
            max_files_per_repo=self.config.MAX_FILES_PER_REPO,
        )

        # Initialize multi-project BigQuery tool
        bq_projects = self.config.get_bigquery_projects()
        print(f"📊 Configured {len(bq_projects)} BigQuery projects")

        self.bq_tool = MultiProjectBigQueryTool(
            project_ids=bq_projects,
            auto_discover_schemas=self.config.AUTO_DISCOVER_SCHEMAS,
        )

        # Initialize query generator with LLM
        self.query_generator = QueryGenerator(
            api_key=llm_config['api_key'],
            model=llm_config['model'],
            llm=self.query_llm,
        )

        # Initialize Confluence tool
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
                parent_page_id=self.config.CONFLUENCE_PARENT_PAGE_ID,
                llm=self.doc_llm,
            )
            print(f"📝 Confluence configured for space: {self.config.CONFLUENCE_SPACE_KEY}")

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("analyze_code", self._analyze_code_node)
        workflow.add_node("discover_schemas", self._discover_schemas_node)
        workflow.add_node("generate_query", self._generate_query_node)
        workflow.add_node("execute_query", self._execute_query_node)
        workflow.add_node("analyze_results", self._analyze_results_node)
        workflow.add_node("create_documentation", self._create_documentation_node)
        workflow.add_node("publish_to_confluence", self._publish_to_confluence_node)

        # Define edges
        workflow.set_entry_point("analyze_code")
        workflow.add_edge("analyze_code", "discover_schemas")
        workflow.add_edge("discover_schemas", "generate_query")
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
        """Analyze multiple code repositories for SQL patterns"""
        state["current_step"] = "Analyzing code repositories..."

        try:
            analysis_result = self.code_analyzer.analyze_all_repositories()

            if analysis_result.get("success"):
                # Format code context
                context = f"""
Multi-Repository Analysis:
- Repositories analyzed: {analysis_result.get('repositories_analyzed', 0)} / {analysis_result.get('total_repositories', 0)}
- Total queries found: {analysis_result.get('queries_found', 0)}
- Total files analyzed: {analysis_result.get('files_analyzed', 0)}
- Tables referenced: {', '.join(analysis_result.get('table_references', [])[:20])}

Common patterns across repositories:
{analysis_result.get('common_patterns', {})}

Example queries available: {len(analysis_result.get('queries', []))}
"""
                state["code_context"] = context
                state["messages"] = state.get("messages", []) + [
                    AIMessage(content=f"Code analysis complete across multiple repositories.\n{context}")
                ]
            else:
                state["code_context"] = "No code context available"
                state["error"] = "Failed to analyze repositories"

        except Exception as e:
            state["error"] = str(e)
            state["code_context"] = f"Error analyzing code: {str(e)}"

        return state

    def _discover_schemas_node(self, state: AgentState) -> AgentState:
        """Discover BigQuery schemas across all projects"""
        state["current_step"] = "Discovering BigQuery schemas..."

        try:
            # Get schema context
            schema_context = self.bq_tool.get_schema_context(include_sample_rows=True)

            # Add to state
            state["schema_context"] = schema_context
            state["messages"] = state.get("messages", []) + [
                AIMessage(content=f"Discovered BigQuery schemas:\n{schema_context[:500]}...")
            ]

        except Exception as e:
            state["error"] = str(e)
            state["schema_context"] = ""

        return state

    def _generate_query_node(self, state: AgentState) -> AgentState:
        """Generate SQL query based on question, code context, and schemas"""
        state["current_step"] = "Generating SQL query..."

        try:
            # Prepare enhanced context with schemas
            enhanced_context = {
                "success": True,
                "code_context": state.get("code_context", ""),
                "schema_context": state.get("schema_context", ""),
            }

            result = self.query_generator.generate_query(
                user_question=state["user_question"],
                code_context=enhanced_context,
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
        """Execute the generated SQL query on appropriate BigQuery project"""
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
                        content=f"Query executed successfully on project: {result.get('project_id')}!\n\nResults:\n{result['summary'][:1000]}"
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
            response = self.analysis_llm.invoke(messages)

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
                parent_id=self.config.CONFLUENCE_PARENT_PAGE_ID or None,
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
            "schema_context": "",
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
            "schema_context": "",
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
