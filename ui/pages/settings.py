"""Settings page."""

from __future__ import annotations

import streamlit as st


def show_settings():
    """Show settings."""
    st.markdown('<h1 class="main-header">⚙️ Settings</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Configure AgentOS settings and preferences.
    """)
    
    # Database
    st.subheader("🗄️ Database Connection")
    
    db_url = st.text_input(
        "DATABASE_URL",
        value=st.session_state.get("db_url", "postgresql+psycopg://agentos:agentos@localhost:5431/agentos"),
        type="password"
    )
    
    if st.button("Test Connection"):
        try:
            from sqlalchemy import create_engine
            engine = create_engine(db_url)
            conn = engine.connect()
            conn.close()
            st.success("✅ Database connection successful!")
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")
    
    # Agent models
    st.markdown("---")
    st.subheader("🤖 Agent Models")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Filings Classifier**")
        st.info("Model: claude-3-haiku-20240307")
        st.info("Max tool calls: 10")
        st.info("Max tokens: 30K")
    
    with col2:
        st.markdown("**Variance Analysis**")
        st.info("Model: claude-3-sonnet-20241022")
        st.info("Max tool calls: 15")
        st.info("Max tokens: 100K")
    
    # Storage
    st.markdown("---")
    st.subheader("📁 Storage Paths")
    
    st.text_input("Raw PDFs", value="/data/raw/bse")
    st.text_input("Excel Models", value="/data/excel")
    
    # About
    st.markdown("---")
    st.subheader("ℹ️ About")
    
    st.markdown("""
    **AgentOS v1.0**
    
    Your personal research operating system for Indian pharma stocks.
    
    - BSE Filings automated ingestion
    - PDF extraction with tables
    - Excel model integration
    - Variance analysis
    - Approval queue workflow
    
    Built with ❤️ using Python, PostgreSQL, and LLMs.
    """)
    
    # System info
    import platform
    import sys
    
    st.markdown("---")
    st.code(f"""
Platform: {platform.platform()}
Python: {sys.version.split()[0]}
Working Directory: {os.getcwd() if 'os' in dir() else 'N/A'}
    """)
