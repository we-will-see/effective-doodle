"""Process PDF from URL page."""

from __future__ import annotations

import streamlit as st
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.types.sqlalchemy_models import Company


def show_process_pdf():
    """Show PDF processing interface."""
    st.markdown('<h1 class="main-header">📥 Process PDF</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Enter a BSE PDF URL to download, extract, and store automatically.
    
    **Example URL format:**
    ```
    https://www.bseindia.com/xml-data/corpfiling/AttachHis/[uuid].pdf
    ```
    """)
    
    # Input form
    with st.form("pdf_form"):
        pdf_url = st.text_input(
            "PDF URL",
            placeholder="https://www.bseindia.com/xml-data/corpfiling/AttachHis/..."
        )
        
        # Company selector
        import os
        db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://agentos:agentos@localhost:5431/agentos")
        
        try:
            engine = create_engine(db_url)
            Session = sessionmaker(bind=engine)
            db = Session()
            
            companies = db.query(Company).all()
            company_options = {c.bse_code: f"{c.display_name} ({c.bse_code})" for c in companies}
            
            selected_bse_code = st.selectbox(
                "Company (optional)",
                options=["Auto-detect"] + list(company_options.keys()),
                format_func=lambda x: company_options.get(x, x) if x != "Auto-detect" else x
            )
            
            db.close()
        except:
            selected_bse_code = "Auto-detect"
        
        submitted = st.form_submit_button("🚀 Process PDF", use_container_width=True)
    
    # Process
    if submitted and pdf_url:
        import subprocess
        import sys
        
        with st.spinner("Processing PDF..."):
            try:
                # Run processor script
                cmd = [
                    sys.executable,
                    "scripts/process_pdf_url.py",
                    pdf_url
                ]
                
                if selected_bse_code != "Auto-detect":
                    cmd.extend(["--company", selected_bse_code])
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd="/root/.openclaw/workspace/effective-doodle",
                    timeout=120
                )
                
                if result.returncode == 0:
                    st.success("✅ PDF processed successfully!")
                    st.code(result.stdout, language="text")
                else:
                    st.error("❌ Processing failed")
                    st.code(result.stderr, language="text")
                    
            except subprocess.TimeoutExpired:
                st.error("⏱️ Processing timed out")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Recent processed
    st.markdown("---")
    st.subheader("🕐 Recently Processed")
    
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        db = Session()
        
        from core.types.sqlalchemy_models import Document
        
        recent = db.query(Document).order_by(
            Document.filed_at.desc()
        ).limit(5).all()
        
        if recent:
            for doc in recent:
                company = db.query(Company).filter(
                    Company.id == doc.company_id
                ).first()
                company_name = company.display_name if company else "Unknown"
                
                cols = st.columns([3, 2, 2, 1])
                cols[0].write(f"**{company_name}**")
                cols[0].write(doc.filing_title or "Untitled")
                cols[1].write(doc.document_type or "Unknown")
                cols[2].write(str(doc.filed_at.date()) if doc.filed_at else "N/A")
                cols[3].write(f"✅ {doc.extraction_status}")
                st.markdown("---")
        else:
            st.info("No documents yet. Process your first PDF above!")
        
        db.close()
    except Exception as e:
        st.error(f"Error loading recent: {e}")
