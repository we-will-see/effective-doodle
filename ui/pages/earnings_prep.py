"""Earnings prep page."""

from __future__ import annotations

import streamlit as st

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.types.sqlalchemy_models import Company, Catalyst
from datetime import date, datetime


def show_earnings_prep():
    """Show earnings preparation."""
    st.markdown('<h1 class="main-header">📈 Earnings Prep</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Prepare for upcoming earnings announcements.
    
    **What you'll see:**
    - Your estimates vs consensus
    - Key drivers to watch
Material risks
What managements likely to say
    """)

    # Company selector
    import os
    db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://agentos:agentos@localhost:5431/agentos")
    
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        db = Session()
        
        companies = db.query(Company).filter(
            Company.coverage_status == "active"
        ).all()
        
        if not companies:
            st.warning("No active coverage.")
            db.close()
            return
        
        company = st.selectbox(
            "Generate Earnings Prep For",
            companies,
            format_func=lambda c: c.display_name
        )
        
        if company:
            st.markdown("---")
            
            # Show earnings catalysts
            catalysts = db.query(Catalyst).filter(
                Catalyst.company_id == company.id,
                Catalyst.catalyst_type == "earnings",
                Catalyst.expected_date >= date.today()
            ).order_by(Catalyst.expected_date).all()
            
            st.subheader("📅 Upcoming Earnings")
            
            if catalysts:
                for cat in catalysts:
                    with st.container():
                        cols = st.columns([2, 3, 2])
                        cols[0].write(f"**{cat.expected_date}**")
                        cols[1].write(cat.description or "Earnings announcement")
                        cols[2].write(f"Confidence: {cat.date_confidence or 'Unknown'}")
                    st.markdown("---")
            else:
                st.info("No earnings dates scheduled. Check back later!")
            
            # Quick prep form
            st.markdown("---")
            st.subheader("⚡ Quick Prep")
            
            with st.form("prep_form"):
                st.write(f"Generate one-pager for {company.display_name}")
                
                period = st.selectbox(
                    "Period",
                    ["1QFY26", "2QFY26", "3QFY26", "4QFY26", "FY26"]
                )
                
                focus = st.multiselect(
                    "Focus Areas",
                    ["Revenue", "EBITDA", "PAT", "Margins", "Guidance", "Working Capital"],
                    default=["Revenue", "EBITDA"]
                )
                
                generate = st.form_submit_button("🎯 Generate Prep", use_container_width=True)
            
            if generate:
                with st.spinner("Generating earnings prep..."):
                    st.info("This would call the Earnings Prep Agent.")
                    st.write("For now, showing placeholder output:")
                    
                    st.markdown(f"""
                    ### Earnings Prep: {company.display_name} ({period})
                    
                    **Your Estimate vs Consensus:**
                    - Revenue: ₹X cr (You) vs ₹Y cr (Consensus) - Z% variance
                    - EBITDA: ₹A cr (You) vs ₹B cr (Consensus)
                    
                    **Key Drivers to Watch:**
                    1. Export demand trends
                    2. Raw material costs
                    3. Guidance update
                    
                    **Questions for Management:**
                    - What is happening with exports
                    - Guidance for FY26
                    
                    **Risk Factors:**
                    - currency volatility
                    - competition
                    """)
        
        db.close()
        
    except Exception as e:
        st.error(f"Error: {e}")
