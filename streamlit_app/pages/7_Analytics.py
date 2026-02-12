"""Analytics page - MTBF, MTTR, availability, and charts."""
import streamlit as st
import sys
from pathlib import Path

st.set_page_config(page_title="Analytics - RELIABASE", page_icon="📈", layout="wide")

src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from sqlmodel import Session
from reliabase.config import init_db, get_engine
from reliabase.services import AssetService, EventService, ExposureService, FailureModeService, EventDetailService
from reliabase.analytics.metrics import aggregate_kpis

init_db()


def get_session():
    engine = get_engine()
    return Session(engine)


def main():
    st.title("📈 Analytics")
    st.markdown("Reliability metrics, failure analysis, and trends.")
    
    # Load all data
    with get_session() as session:
        asset_svc = AssetService(session)
        event_svc = EventService(session)
        exposure_svc = ExposureService(session)
        mode_svc = FailureModeService(session)
        detail_svc = EventDetailService(session)
        
        assets = asset_svc.list(limit=500)
        events = event_svc.list(limit=500)
        exposures = exposure_svc.list(limit=500)
        failure_modes = mode_svc.list(limit=500)
        event_details = detail_svc.list(limit=500)
    
    if not assets:
        st.warning("No data available. Seed demo data from the Operations page.")
        return
    
    # Asset filter
    asset_options = {"All Assets": None}
    asset_options.update({f"#{a.id} - {a.name}": a.id for a in assets})
    
    selected_filter = st.selectbox("Filter by Asset", options=list(asset_options.keys()))
    selected_asset_id = asset_options[selected_filter]
    
    # Filter data
    if selected_asset_id:
        filtered_events = [e for e in events if e.asset_id == selected_asset_id]
        filtered_exposures = [e for e in exposures if e.asset_id == selected_asset_id]
    else:
        filtered_events = events
        filtered_exposures = exposures
    
    st.divider()
    
    # Calculate KPIs
    failure_events = [e for e in filtered_events if e.event_type == "failure"]
    total_exposure = sum(e.hours or 0 for e in filtered_exposures)
    total_downtime_hrs = sum((e.downtime_minutes or 0) / 60 for e in failure_events)
    failure_count = len(failure_events)
    
    mtbf = total_exposure / failure_count if failure_count > 0 else total_exposure
    mttr = total_downtime_hrs / failure_count if failure_count > 0 else 0
    availability = mtbf / (mtbf + mttr) if (mtbf + mttr) > 0 else 1.0
    
    # KPI Cards
    st.subheader("Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Failures", failure_count, help="Events with type = failure")
    
    with col2:
        st.metric("Total Exposure (h)", f"{total_exposure:.1f}", help="Sum of exposure hours")
    
    with col3:
        st.metric("MTBF (h)", f"{mtbf:.2f}", help="Mean Time Between Failures")
    
    with col4:
        st.metric("MTTR (h)", f"{mttr:.2f}", help="Mean Time To Repair")
    
    st.divider()
    
    # Availability Card
    st.subheader("Availability")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.metric("System Availability", f"{availability * 100:.2f}%")
        st.caption("Computed from MTBF / (MTBF + MTTR)")
    
    with col2:
        # Simple progress bar for availability
        st.progress(availability, text=f"Availability: {availability * 100:.2f}%")
    
    st.divider()
    
    # Failure Timeline
    st.subheader("Failure Timeline")
    
    if failure_events:
        sorted_failures = sorted(failure_events, key=lambda e: e.timestamp, reverse=True)[:20]
        
        asset_names = {a.id: a.name for a in assets}
        failure_data = []
        for evt in sorted_failures:
            failure_data.append({
                "Timestamp": evt.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Asset": f"#{evt.asset_id} - {asset_names.get(evt.asset_id, 'Unknown')}",
                "Downtime (min)": evt.downtime_minutes or 0,
                "Description": evt.description or "—",
            })
        
        st.dataframe(failure_data, use_container_width=True, hide_index=True)
    else:
        st.info("No failure events recorded yet.")
    
    st.divider()
    
    # Failure Mode Pareto
    st.subheader("Failure Mode Pareto")
    
    if event_details and failure_modes:
        # Count failure modes
        event_ids = {e.id for e in filtered_events}
        mode_counts = {}
        
        for detail in event_details:
            if detail.event_id in event_ids:
                mode_id = detail.failure_mode_id
                mode_counts[mode_id] = mode_counts.get(mode_id, 0) + 1
        
        if mode_counts:
            # Sort by count descending
            mode_names = {m.id: m.name for m in failure_modes}
            pareto_data = []
            for mode_id, count in sorted(mode_counts.items(), key=lambda x: x[1], reverse=True):
                pareto_data.append({
                    "Failure Mode": mode_names.get(mode_id, f"Mode #{mode_id}"),
                    "Count": count,
                })
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(pareto_data, use_container_width=True, hide_index=True)
            
            with col2:
                # Bar chart
                import pandas as pd
                df = pd.DataFrame(pareto_data)
                st.bar_chart(df.set_index("Failure Mode")["Count"])
        else:
            st.info("No failure mode data linked to filtered events.")
    else:
        st.info("Add failure details in Event Details to populate Pareto chart.")
    
    st.divider()
    
    # MTBF Trend
    st.subheader("MTBF Trend")
    
    if len(failure_events) >= 2:
        sorted_failures = sorted(failure_events, key=lambda e: e.timestamp)
        
        intervals = []
        labels = []
        for i in range(1, len(sorted_failures)):
            prev = sorted_failures[i - 1].timestamp
            curr = sorted_failures[i].timestamp
            hours = (curr - prev).total_seconds() / 3600
            intervals.append(hours)
            labels.append(f"#{i + 1}")
        
        if intervals:
            import pandas as pd
            trend_df = pd.DataFrame({
                "Failure": labels,
                "Time Between Failures (h)": intervals,
            })
            
            st.line_chart(trend_df.set_index("Failure"))
            
            # Summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Min Interval", f"{min(intervals):.1f} h")
            with col2:
                st.metric("Max Interval", f"{max(intervals):.1f} h")
            with col3:
                st.metric("Avg Interval", f"{sum(intervals)/len(intervals):.1f} h")
    else:
        st.info("Log at least 2 failure events to see MTBF trend.")
    
    st.divider()
    
    # CLI Commands for Advanced Analytics
    st.subheader("Advanced Analytics")
    st.markdown("""
    For Weibull analysis and PDF reports, use the CLI:
    
    ```bash
    python -m reliabase.make_report --asset-id 1 --output-dir ./examples
    ```
    
    This generates:
    - Weibull probability plots
    - Failure mode Pareto charts
    - Event timeline visualization
    - Full PDF report
    """)


if __name__ == "__main__":
    main()
