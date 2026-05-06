"""Variance analysis page."""

from __future__ import annotations

import streamlit as st

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from core.types.sqlalchemy_models import Company, Financial


def show_variance():
    """Show variance analysis."""
    st.markdown('<h1 class="main-header">🔍 Variance Analysis</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Compare actual results vs. your estimates vs. consensus.
    
    **What to look for:**
    - Large variances (>10%) that affect thesis
    Estimate misses by management
Sector-wide trends
    """)

    # Company selector
    import os
    db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://agentos:agentos@localhost:5431/agentos")
    
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        db = Session()
        
        companies = db.query(Company).filter(
            Company.coverage_status.in_(["active", "passive"])
        ).all()
        
        if not companies:
            st.warning("No companies in coverage yet.")
            db.close()
            return
        
        company_names = {c.id: c.display_name for c in companies}
        
        selected_company = st.selectbox(
            "Select Company",
            options=[c.id for c in companies],
            format_func=lambda x: company_names.get(x, x)
        )
        
        if selected_company:
            # Get financials
            financials = db.query(Financial).filter(
                Financial.company_id == selected_company
            ).order_by(Financial.period_label.desc()).limit(20).all()
            
            if financials:
                st.markdown("---")
                st.subheader("📊 Financial Data")
                
                # Group by period
                periods = {}
                for fin in financials:
                    if fin.period_label not in periods:
                        periods[fin.period_label] = []
                    periods[fin.period_label].append(fin)
                
                # Create comparison table
                data = []
                for period in sorted(periods.keys(), reverse=True)[:5]:
                    row = {"Period": period}
                    
                    for fin in periods[period]:
                        if fin.type == "actual":
                            row[f"{fin.metric} (Actual)"] = float(fin.value)
                        elif fin.type == "our_estimate":
                            row[f"{fin.metric} (Our Est)"] = float(fin.value)
                        elif fin.type == "consensus":
                            row[f"{fin.metric} (Consensus)"] = float(fin.value)
                    
                    data.append(row)
                
                # Show as table
                import pandas as pd
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                
                # Variance chart
                st.markdown("---")
                st.subheader("📈 Variance Chart")
                
                # Find revenue rows
                rev_data = [d for d in data if "revenue (Actual)" in str(d)]
                
                if rev_data:
                    periods_chart = [d["Period"] for d in rev_data]
                    actuals = [d.get("revenue (Actual)", 0) for d in rev_data]
                    estimates = [d.get("revenue (Our Est)", 0) for d in rev_data]
                    
                    chart_data = pd.DataFrame({
                        "Period": periods_chart,
                        "Actual": actuals,
                        "Our Estimate": estimates
                    })
                    
                    st.line_chart(chart_data.set_index("Period"))
                else:
                    st.info("No revenue data available for chart.")
            else:
                st.info("No financial data for this company yet.")
        
        db.close()
        
    except Exception as e:
        st.error(f"Error: {e}")
