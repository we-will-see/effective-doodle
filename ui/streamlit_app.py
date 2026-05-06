"""Streamlit web UI for AgentOS.

Main entry point for the analyst review surface.
"""

from __future__ import annotations

import streamlit as st

# Page config
st.set_page_config(
    page_title="AgentOS - Analyst Review",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .queue-item {
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        cursor: pointer;
    }
    .queue-item:hover {
        border-color: #1f77b4;
    }
    .tier-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .tier-fast {
        background-color: #d4edda;
        color: #155724;
    }
    .tier-standard {
        background-color: #fff3cd;
        color: #856404;
    }
    .tier-slow {
        background-color: #f8d7da;
        color: #721c24;
    }
    .stale-warning {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("📊 AgentOS")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "📋 Review Queue",
        "🔍 Variance Analysis",
        "📈 Earnings Prep",
        "📥 Process PDF",
        "⚙️ Settings",
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Quick Stats**")

# Import and show stats
try:
    import os
    os.environ["DATABASE_URL"] = "postgresql+psycopg://agentos:agentos@localhost:5431/agentos"
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.types.sqlalchemy_models import Company, Document, Financial
    
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    db = Session()
    
    companies = db.query(Company).count()
    documents = db.query(Document).count()
    financials = db.query(Financial).count()
    
    st.sidebar.metric("Companies", companies)
    st.sidebar.metric("Documents", documents)
    st.sidebar.metric("Financials", financials)
    
    db.close()
except Exception as e:
    st.sidebar.error("DB Error")

st.sidebar.markdown("---")
st.sidebar.markdown("🤖 **v1.0** | Built with ❤️")

# Route to pages
if page == "🏠 Dashboard":
    from ui.pages.dashboard import show_dashboard
    show_dashboard()
    
elif page == "📋 Review Queue":
    from ui.pages.queue_list import show_queue_list
    show_queue_list()
    
elif page == "🔍 Variance Analysis":
    from ui.pages.variance import show_variance
    show_variance()
    
elif page == "📈 Earnings Prep":
    from ui.pages.earnings_prep import show_earnings_prep
    show_earnings_prep()
    
elif page == "📥 Process PDF":
    from ui.pages.process_pdf import show_process_pdf
    show_process_pdf()
    
elif page == "⚙️ Settings":
    from ui.pages.settings import show_settings
    show_settings()
