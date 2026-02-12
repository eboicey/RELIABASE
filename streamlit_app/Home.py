"""RELIABASE Streamlit Application - Main Entry Point.

This is the home page and entry point for the Streamlit application.
Run with: streamlit run streamlit_app/Home.py
"""
import streamlit as st
from sqlmodel import Session

# Configure page - MUST be first Streamlit command
st.set_page_config(
    page_title="RELIABASE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import after page config
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from reliabase.config import init_db, get_engine
from reliabase.services import AssetService, EventService, ExposureService, DemoService

# Initialize database
init_db()


def get_session():
    """Get a database session."""
    engine = get_engine()
    return Session(engine)


def main():
    # Sidebar branding
    with st.sidebar:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; padding: 10px 0;">
            <div style="width: 40px; height: 40px; border-radius: 50%; background: rgba(99, 102, 241, 0.2); 
                        border: 1px solid rgba(99, 102, 241, 0.4); display: flex; align-items: center; 
                        justify-content: center; color: #818cf8; font-weight: 600; font-size: 18px;">R</div>
            <div>
                <div style="font-size: 18px; font-weight: 600;">RELIABASE</div>
                <div style="font-size: 12px; color: #94a3b8;">Reliability Analytics</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
    
    # Main content
    st.title("📊 RELIABASE Dashboard")
    st.markdown("*Reliability engineering tracking and analytics platform*")
    
    # Load data
    with get_session() as session:
        asset_svc = AssetService(session)
        event_svc = EventService(session)
        exposure_svc = ExposureService(session)
        demo_svc = DemoService(session)
        
        assets = asset_svc.list(limit=500)
        events = event_svc.list(limit=500)
        exposures = exposure_svc.list(limit=500)
        totals = demo_svc.get_totals()
    
    # KPI Cards
    st.subheader("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    total_hours = sum(e.hours or 0 for e in exposures)
    failure_count = len([e for e in events if e.event_type == "failure"])
    
    with col1:
        st.metric("Assets", len(assets), help="Total tracked assets")
    with col2:
        st.metric("Events", len(events), help="All event types")
    with col3:
        st.metric("Failures", failure_count, help="Events with type = failure")
    with col4:
        st.metric("Exposure Hours", f"{total_hours:.1f}", help="Sum of exposure logs")
    
    st.divider()
    
    # Recent Events
    st.subheader("Recent Events")
    
    if events:
        # Sort by timestamp descending and show top 10
        sorted_events = sorted(events, key=lambda e: e.timestamp, reverse=True)[:10]
        
        event_data = []
        for evt in sorted_events:
            event_data.append({
                "Timestamp": evt.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Asset ID": f"#{evt.asset_id}",
                "Type": evt.event_type.capitalize(),
                "Downtime (min)": evt.downtime_minutes or 0,
                "Description": evt.description or "—",
            })
        
        st.dataframe(event_data, use_container_width=True, hide_index=True)
    else:
        st.info("No events yet. Use the sidebar to navigate to **Operations** and seed demo data.")
        
        # Seed button for empty state
        if st.button("🌱 Seed Demo Data", type="primary"):
            with get_session() as session:
                demo_svc = DemoService(session)
                result = demo_svc.seed(reset=True)
                st.success(f"Seeded {result['created']['assets']} assets, {result['created']['events']} events, "
                          f"{result['created']['exposures']} exposures!")
                st.rerun()
    
    st.divider()
    
    # What's Next section
    st.subheader("What's Next?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **📈 Analytics**
        
        View MTBF, MTTR, availability metrics and failure mode Pareto charts.
        """)
    
    with col2:
        st.markdown("""
        **🛰 Operations**
        
        Re-seed data, export tables to CSV, and manage the database.
        """)
    
    with col3:
        st.markdown("""
        **📚 Reports**
        
        Generate Weibull analysis and PDF reports via CLI:
        ```bash
        python -m reliabase.make_report --asset-id 1
        ```
        """)


if __name__ == "__main__":
    main()
