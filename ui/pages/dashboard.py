"""Dashboard page."""

from __future__ import annotations

import streamlit as st

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from core.types.sqlalchemy_models import Company, Document, Financial, Driver, Catalyst


def show_dashboard():
    """Show dashboard overview."""
    st.markdown('<h1 class="main-header">🏠 Dashboard</h1>', unsafe_allow_html=True)
    
    # Database connection
    import os
    db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://agentos:agentos@localhost:5431/agentos")
    
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            companies = db.query(Company).count()
            st.metric("Companies", companies, "covered")
        
        with col2:
            documents = db.query(Document).filter(
                Document.extraction_status == "extracted"
            ).count()
            st.metric("Documents", documents, "processed")
        
        with col3:
            financials = db.query(Financial).count()
            st.metric("Financials", financials, "rows")
        
        with col4:
            pending = db.query(Document).filter(
                Document.extraction_status == "pending"
            ).count()
            st.metric("Pending", pending, "to extract")
        
        # Recent activity
        st.markdown("---")
        st.subheader("📊 Recent Activity")
        
        recent_docs = db.query(Document).order_by(
            Document.filed_at.desc()
        ).limit(5).all()
        
        if recent_docs:
            for doc in recent_docs:
                company = db.query(Company).filter(
                    Company.id == doc.company_id
                ).first()
                company_name = company.display_name if company else "Unknown"
                
                with st.container():
                    cols = st.columns([3, 2, 2, 1])
                    cols[0].write(f"**{company_name}**")
                    cols[0].write(doc.filing_title or "Untitled")
                    cols[1].write(doc.document_type or "Unknown")
                    cols[2].write(str(doc.filed_at.date()) if doc.filed_at else "N/A")
                    cols[3].write(f"✅ {doc.extraction_status}")
                st.markdown("---")
        else:
            st.info("No documents yet. Go to 📥 Process PDF to add some!")
        
        # Quick links
        st.markdown("---")
        st.subheader("⚡ Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Process PDF", use_container_width=True):
                st.switch_page("ui/streamlit_app.py")
                st.session_state["page"] = "📥 Process PDF"
        
        with col2:
            if st.button("📋 Review Queue", use_container_width=True):
                st.switch_page("ui/streamlit_app.py")
                st.session_state["page"] = "📋 Review Queue"
        
        with col3:
            if st.button("📈 Earnings Prep", use_container_width=True):
                st.switch_page("ui/streamlit_app.py")
                st.session_state["page"] = "📈 Earnings Prep"
        
        db.close()
        
    except Exception as e:
        st.error(f"Database error: {e}")
        st.info("Make sure PostgreSQL is running and DATABASE_URL is set.")
