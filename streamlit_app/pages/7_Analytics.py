"""Analytics page - MTBF, MTTR, availability, Weibull analysis, and PDF reports."""
import streamlit as st
import pandas as pd
import tempfile
from pathlib import Path
import numpy as np

st.set_page_config(page_title="Analytics - RELIABASE", page_icon="📈", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import (  # noqa: E402
    AssetService, EventService, ExposureService,
    FailureModeService, EventDetailService,
)
from reliabase.analytics import metrics, weibull, reporting  # noqa: E402


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
    
    # Weibull Analysis Section
    st.subheader("📊 Weibull Analysis")
    
    if selected_asset_id is None:
        st.info("Select a specific asset to perform Weibull analysis.")
    else:
        with get_session() as session:
            asset_svc = AssetService(session)
            event_svc = EventService(session)
            exposure_svc = ExposureService(session)
            detail_svc = EventDetailService(session)
            mode_svc = FailureModeService(session)
            
            asset = asset_svc.get(selected_asset_id)
            asset_exposures = exposure_svc.list(asset_id=selected_asset_id, limit=500)
            asset_events = event_svc.list(asset_id=selected_asset_id, limit=500)
            
            # Calculate KPIs with censoring
            kpi_data = metrics.aggregate_kpis(asset_exposures, asset_events)
            intervals = kpi_data.get("intervals_hours", [])
            censored = kpi_data.get("censored_flags", [])
            
            # Check if we have enough data for Weibull
            uncensored_count = sum(1 for c in censored if not c) if censored else 0
            
            if uncensored_count >= 1:
                try:
                    # Fit Weibull
                    weibull_fit = weibull.fit_weibull_mle_censored(intervals, censored)
                    ci = weibull.bootstrap_weibull_ci(intervals, censored, n_bootstrap=200)
                    
                    # Display parameters
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Shape (β)", f"{weibull_fit.shape:.3f}")
                        st.caption(f"95% CI: [{ci.shape_ci[0]:.3f}, {ci.shape_ci[1]:.3f}]")
                    
                    with col2:
                        st.metric("Scale (η)", f"{weibull_fit.scale:.2f} h")
                        st.caption(f"95% CI: [{ci.scale_ci[0]:.2f}, {ci.scale_ci[1]:.2f}]")
                    
                    with col3:
                        # Interpret shape parameter
                        if weibull_fit.shape < 1:
                            pattern = "Infant Mortality"
                            pattern_desc = "β < 1: Early life failures"
                        elif weibull_fit.shape == 1:
                            pattern = "Random Failures"
                            pattern_desc = "β = 1: Constant failure rate"
                        else:
                            pattern = "Wear-out"
                            pattern_desc = "β > 1: Aging/degradation"
                        st.metric("Failure Pattern", pattern)
                        st.caption(pattern_desc)
                    
                    with col4:
                        # B10 life
                        b10 = weibull_fit.scale * ((-np.log(0.9)) ** (1 / weibull_fit.shape))
                        st.metric("B10 Life", f"{b10:.1f} h")
                        st.caption("Time at which 10% fail")
                    
                    st.divider()
                    
                    # Reliability curves
                    st.markdown("**Reliability & Hazard Curves**")
                    
                    max_time = max(intervals) * 1.5 if intervals else 1000
                    times = np.linspace(0, max_time, 100)
                    curves = weibull.reliability_curves(weibull_fit.shape, weibull_fit.scale, times)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        rel_df = pd.DataFrame({
                            "Time (hours)": times,
                            "Reliability R(t)": curves.reliability,
                        })
                        st.line_chart(rel_df.set_index("Time (hours)"))
                        st.caption("Probability of survival at time t")
                    
                    with col2:
                        haz_df = pd.DataFrame({
                            "Time (hours)": times,
                            "Hazard h(t)": curves.hazard,
                        })
                        st.line_chart(haz_df.set_index("Time (hours)"))
                        st.caption("Instantaneous failure rate")
                    
                    st.divider()
                    
                    # PDF Report Download
                    st.subheader("📄 Download PDF Report")
                    
                    if st.button("Generate & Download PDF Report", type="primary"):
                        with st.spinner("Generating report..."):
                            # Get failure details for pareto
                            all_details = detail_svc.list(limit=500)
                            event_ids = {e.id for e in asset_events}
                            asset_details = [d for d in all_details if d.event_id in event_ids]
                            
                            # Get failure mode names
                            all_modes = mode_svc.list(limit=500)
                            mode_names = {m.id: m.name for m in all_modes}
                            
                            failure_counts = {}
                            for d in asset_details:
                                name = mode_names.get(d.failure_mode_id, "Unknown")
                                failure_counts[name] = failure_counts.get(name, 0) + 1
                            
                            # Build context for report
                            context = {
                                "asset": asset,
                                "metrics": kpi_data,
                                "weibull": {
                                    "shape": weibull_fit.shape,
                                    "scale": weibull_fit.scale,
                                    "shape_ci": ci.shape_ci,
                                    "scale_ci": ci.scale_ci,
                                },
                                "curves": {
                                    "times": list(curves.times),
                                    "reliability": list(curves.reliability),
                                    "hazard": list(curves.hazard),
                                },
                                "events": [
                                    {
                                        "timestamp": e.timestamp,
                                        "event_type": e.event_type,
                                        "downtime_minutes": e.downtime_minutes or 0,
                                        "description": e.description,
                                    }
                                    for e in asset_events
                                ],
                                "failure_counts": failure_counts,
                            }
                            
                            # Generate PDF
                            with tempfile.TemporaryDirectory() as tmpdir:
                                output_dir = Path(tmpdir)
                                pdf_path = reporting.generate_asset_report(output_dir, context)
                                
                                with open(pdf_path, "rb") as f:
                                    pdf_bytes = f.read()
                                
                                st.download_button(
                                    label="📥 Download PDF",
                                    data=pdf_bytes,
                                    file_name=f"asset_{selected_asset_id}_reliability_report.pdf",
                                    mime="application/pdf",
                                )
                        
                        st.success("Report generated! Click the download button above.")
                
                except Exception as e:
                    st.error(f"Weibull fitting failed: {str(e)}")
            else:
                st.warning("Weibull analysis requires at least one complete failure interval. Log more failure events with exposure data.")


main()
