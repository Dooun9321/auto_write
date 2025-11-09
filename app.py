"""Streamlit app for Data Analysis Agent"""

import streamlit as st
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agent.multi_project_graph import EnhancedDataAnalysisAgent
from src.utils.config import Config


def initialize_session_state():
    """Initialize Streamlit session state"""
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "history" not in st.session_state:
        st.session_state.history = []
    if "current_analysis" not in st.session_state:
        st.session_state.current_analysis = None


def display_analysis_result(state: dict):
    """Display analysis results in a structured format"""

    # Display current step if available
    if state.get("current_step"):
        st.info(f"**Status:** {state['current_step']}")

    # Display error if present
    if state.get("error"):
        st.error(f"**Error:** {state['error']}")

    # Display SQL Query
    if state.get("sql_query"):
        with st.expander("📝 Generated SQL Query", expanded=True):
            st.code(state["sql_query"], language="sql")

    # Display Query Results
    if state.get("query_results"):
        with st.expander("📊 Query Results", expanded=True):
            st.text(state["query_results"])

    # Display Analysis
    if state.get("analysis"):
        with st.expander("🔍 Analysis", expanded=True):
            st.markdown(state["analysis"])

    # Display Documentation
    if state.get("documentation"):
        with st.expander("📄 Documentation", expanded=False):
            st.markdown(state["documentation"])

    # Display Confluence URL
    if state.get("confluence_url"):
        st.success(
            f"✅ Documentation published to Confluence: [{state['confluence_url']}]({state['confluence_url']})"
        )


def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="Data Analysis Agent",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_session_state()

    # Sidebar
    with st.sidebar:
        st.title("⚙️ Configuration")

        st.markdown("### Setup")
        st.markdown(
            """
        1. Create a `.env` file based on `.env.example`
        2. Configure your API keys and settings
        3. Run the app with `streamlit run app.py`
        """
        )

        # Initialize Agent
        if st.button("🔄 Initialize Agent", use_container_width=True):
            with st.spinner("Initializing agent..."):
                try:
                    config = Config()
                    is_valid, missing = config.validate()

                    if not is_valid:
                        st.error(f"Missing required configuration: {', '.join(missing)}")
                    else:
                        st.session_state.agent = EnhancedDataAnalysisAgent(config)
                        st.success("✅ Agent initialized successfully!")

                except Exception as e:
                    st.error(f"Failed to initialize agent: {str(e)}")

        # Display configuration status
        st.markdown("### Status")
        config = Config()
        is_valid, missing = config.validate()

        if is_valid:
            st.success("✅ Configuration valid")
        else:
            st.error(f"❌ Missing: {', '.join(missing)}")

        # LLM Provider
        st.markdown("### LLM Provider")
        llm_config = config.get_llm_config()
        st.info(f"🤖 {llm_config['provider'].upper()}: {llm_config['model']}")

        # BigQuery Projects
        st.markdown("### BigQuery Projects")
        bq_projects = config.get_bigquery_projects()
        if bq_projects:
            st.success(f"✅ {len(bq_projects)} project(s)")
            for proj in bq_projects[:3]:
                st.text(f"  • {proj}")
            if len(bq_projects) > 3:
                st.text(f"  ... and {len(bq_projects) - 3} more")
        else:
            st.error("❌ No BigQuery projects")

        # Git Repositories
        st.markdown("### Git Repositories")
        git_repos = config.get_git_repositories()
        if git_repos:
            st.success(f"✅ {len(git_repos)} repo(s)")
            for repo in git_repos[:3]:
                st.text(f"  • {repo}")
            if len(git_repos) > 3:
                st.text(f"  ... and {len(git_repos) - 3} more")

        # Optional configurations
        st.markdown("### Optional Features")
        if config.CONFLUENCE_URL:
            st.success("✅ Confluence configured")
            if config.CONFLUENCE_PARENT_PAGE_ID:
                st.text(f"  Parent Page ID: {config.CONFLUENCE_PARENT_PAGE_ID}")
        else:
            st.warning("⚠️ Confluence not configured")

        # History
        if st.session_state.history:
            st.markdown("### Recent Analyses")
            for i, item in enumerate(reversed(st.session_state.history[-5:])):
                if st.button(
                    f"{item['timestamp']}: {item['question'][:30]}...",
                    key=f"history_{i}",
                    use_container_width=True,
                ):
                    st.session_state.current_analysis = item["state"]

    # Main content
    st.title("📊 Data Analysis Agent")
    st.markdown(
        """
    Ask questions about your data and get automated analysis with SQL queries,
    insights, and documentation published to Confluence.
    """
    )

    # Check if agent is initialized
    if st.session_state.agent is None:
        st.warning(
            "⚠️ Please initialize the agent first using the sidebar configuration."
        )
        return

    # Question input
    col1, col2 = st.columns([4, 1])

    with col1:
        user_question = st.text_input(
            "💬 Ask a data analysis question:",
            placeholder="e.g., What are the top 10 products by revenue last month?",
            key="question_input",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_button = st.button("🚀 Analyze", use_container_width=True, type="primary")

    # Example questions
    with st.expander("💡 Example Questions"):
        st.markdown(
            """
        - What are the top 10 customers by total revenue in 2024?
        - Show me the monthly trend of new user signups
        - Which products have the highest return rate?
        - What is the average order value by customer segment?
        - Analyze the conversion funnel for the last quarter
        """
        )

    # Process question
    if analyze_button and user_question:
        st.session_state.current_analysis = None

        # Create placeholder for streaming updates
        status_placeholder = st.empty()
        result_placeholder = st.container()

        try:
            with st.spinner("Running analysis..."):
                # Stream results
                for update in st.session_state.agent.stream(user_question):
                    # Get the latest state from the update
                    for node_name, node_state in update.items():
                        current_state = node_state

                        # Update status
                        with status_placeholder:
                            if current_state.get("current_step"):
                                st.info(f"**Step:** {current_state['current_step']}")

                        # Display results as they come in
                        with result_placeholder:
                            display_analysis_result(current_state)

                        st.session_state.current_analysis = current_state

            # Add to history
            st.session_state.history.append(
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "question": user_question,
                    "state": st.session_state.current_analysis,
                }
            )

            st.success("✅ Analysis complete!")

        except Exception as e:
            st.error(f"Error during analysis: {str(e)}")
            import traceback

            st.code(traceback.format_exc())

    # Display current/loaded analysis
    elif st.session_state.current_analysis:
        st.markdown("### Analysis Results")
        display_analysis_result(st.session_state.current_analysis)

    # Footer
    st.markdown("---")
    st.markdown(
        """
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
    Data Analysis Agent powered by LangGraph, OpenAI, BigQuery, and Confluence
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
