"""RELIABASE Streamlit Application - Main Entry Point.

This is the home page and entry point for the Streamlit application.
Run with: streamlit run streamlit_app/Home.py
"""
import streamlit as st

# Configure page - MUST be first Streamlit command
st.set_page_config(
    page_title="RELIABASE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from _common import get_session  # noqa: E402

from reliabase.services import AssetService, EventService, ExposureService, DemoService  # noqa: E402
from reliabase.analytics import metrics, manufacturing, business  # noqa: E402


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
        
        assets = asset_svc.list(limit=500)
        events = event_svc.list(limit=500)
        exposures = exposure_svc.list(limit=500)
    
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
    
    # Fleet Health Summary
    st.subheader("Fleet Health Summary")
    
    if assets and events:
        health_data = []
        for asset in assets:
            a_events = [e for e in events if e.asset_id == asset.id]
            a_exposures = [e for e in exposures if e.asset_id == asset.id]
            a_kpi = metrics.aggregate_kpis(a_exposures, a_events)
            a_avail = a_kpi["availability"]
            a_mtbf = a_kpi["mtbf_hours"]

            dt_split = manufacturing.compute_downtime_split(a_events)
            perf = manufacturing.compute_performance_rate(a_exposures)
            oee_result = manufacturing.compute_oee(a_avail, perf.performance_rate)

            hi = business.compute_health_index(
                availability=a_avail,
                mtbf_hours=a_mtbf,
                unplanned_ratio=dt_split.unplanned_ratio,
                oee=oee_result.oee,
            )

            health_data.append({
                "Asset": f"#{asset.id} - {asset.name}",
                "Health Score": hi.score,
                "Grade": hi.grade,
                "Availability": f"{a_avail * 100:.1f}%",
                "MTBF (h)": f"{a_mtbf:.1f}",
                "OEE": f"{oee_result.oee * 100:.1f}%",
            })

        st.dataframe(health_data, use_container_width=True, hide_index=True)
    else:
        st.info("Seed demo data from Operations to see fleet health.")
    
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
        **Analytics**
        
        View MTBF, MTTR, availability, Weibull analysis, OEE,
        health index, RPN, and business impact metrics.
        """)
    
    with col2:
        st.markdown("""
        **Operations**
        
        Re-seed data, export CSVs, view spare parts forecast,
        and monitor fleet bad actors.
        """)
    
    with col3:
        st.markdown("""
        **Reports**
        
        Generate Weibull analysis and PDF reports via CLI:
        ```bash
        python -m reliabase.make_report --asset-id 1
        ```
        """)


main()
