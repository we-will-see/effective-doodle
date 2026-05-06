"""Review queue list page."""

from __future__ import annotations

import streamlit as st

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.types.sqlalchemy_models import Document, Company


def show_queue_list():
    """Show review queue list."""
    st.markdown('<h1 class="main-header">📋 Review Queue</h1>', unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "pending", "in_review", "accepted", "rejected"]
        )
    
    with col2:
        tier_filter = st.selectbox(
            "Tier",
            ["All", "1 (Fast)", "2 (Standard)", "3 (Slow)"]
        )
    
    with col3:
        company_filter = st.text_input("Company", placeholder="Filter by company...")
    
    # Database
    import os
    db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://agentos:agentos@localhost:5431/agentos")
    
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # Get documents
        query = db.query(Document).join(Company)
        
        if status_filter != "All":
            query = query.filter(Document.extraction_status == status_filter)
        
        if company_filter:
            query = query.filter(Company.display_name.contains(company_filter))
        
        documents = query.order_by(Document.filed_at.desc()).limit(50).all()
        
        if documents:
            st.markdown(f"**{len(documents)} items**")
            
            for doc in documents:
                company = db.query(Company).filter(Company.id == doc.company_id).first()
                company_name = company.display_name if company else "Unknown"
                
                # Determine tier badge (simplified logic)
                tier = "2"  # Default
                tier_class = "tier-standard"
                
                if doc.document_type == "results":
                    tier = "3"
                    tier_class = "tier-slow"
                elif doc.document_type in ["press_release", "esg_report"]:
                    tier = "1"
                    tier_class = "tier-fast"
                
                # Queue item card
                with st.expander(f"{company_name} - {doc.filing_title or 'Untitled'}"):
                    cols = st.columns([2, 2, 2, 1, 2])
                    
                    cols[0].write(f"**{company_name}**")
                    cols[0].write(f"{doc.document_type or 'Unknown'}")
                    
                    cols[1].write(f"**Filed**")
                    cols[1].write(str(doc.filed_at.date()) if doc.filed_at else "N/A")
                    
                    cols[2].write(f"**Status**")
                    cols[2].write(doc.extraction_status or "Unknown")
                    
                    cols[3].write(f"**Tier**")
                    cols[3].markdown(
                        f'<span class="tier-badge {tier_class}">{tier}</span>',
                        unsafe_allow_html=True
                    )
                    
                    cols[4].write(f"**Actions**")
                    c1, c2, c3 = cols[4].columns(3)
                    with c1:
                        st.button("👁️", key=f"view_{doc.id}", help="View details")
                    with c2:
                        st.button("✅", key=f"accept_{doc.id}", help="Accept")
                    with c3:
                        st.button("❌", key=f"reject_{doc.id}", help="Reject")
                    
                    # Preview
                    if doc.parsed_text:
                        with st.spinner("Loading preview..."):
                            # Show first 500 chars
                            preview = str(doc.parsed_text)[:500] if doc.parsed_text else "No preview"
                            st.text_area("Preview", preview, height=150, disabled=True)
                    
                    # PDF link (if available)
                    if doc.filesystem_path:
                        import pathlib
                        path = pathlib.Path(doc.filesystem_path)
                        if path.exists():
                            with open(path, "rb") as f:
                                st.download_button(
                                    "📥 Download PDF",
                                    f.read(),
                                    f"{company_name}_{doc.id}.pdf",
                                    mime="application/pdf",
                                    key=f"download_{doc.id}"
                                )
        else:
            st.info("No items in queue. Process some PDFs first!")
        
        db.close()
        
    except Exception as e:
        st.error(f"Error: {e}")
        st.write("Exception details:", str(e))
