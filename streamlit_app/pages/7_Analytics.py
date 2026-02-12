"""Analytics page - Full reliability, manufacturing, and business analytics."""
import streamlit as st
import pandas as pd
import tempfile
from pathlib import Path
import numpy as np

st.set_page_config(page_title="Analytics - RELIABASE", page_icon="", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import (  # noqa: E402
    AssetService, EventService, ExposureService,
    FailureModeService, EventDetailService,
)
from reliabase.analytics import (  # noqa: E402
    metrics, weibull, reporting,
    reliability_extended, manufacturing, business,
)


def main():
    st.title(" Analytics")
    st.markdown("Reliability metrics, manufacturing performance, failure analysis, and business impact.")

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
        filtered_details = [
            d for d in event_details
            if d.event_id in {e.id for e in filtered_events}
        ]
    else:
        filtered_events = events
        filtered_exposures = exposures
        filtered_details = event_details

    st.divider()

    # =====================================================================
    # Core KPIs
    # =====================================================================
    failure_events = [e for e in filtered_events if e.event_type == "failure"]
    total_exposure = sum(e.hours or 0 for e in filtered_exposures)
    failure_count = len(failure_events)

    # Use the analytics module for proper TBF-based MTBF
    kpi_data = metrics.aggregate_kpis(filtered_exposures, filtered_events)
    mtbf = kpi_data["mtbf_hours"]
    mttr = kpi_data["mttr_hours"]
    availability = kpi_data["availability"]
    intervals = kpi_data.get("intervals_hours", [])
    censored = kpi_data.get("censored_flags", [])
    failure_rate_val = kpi_data.get("failure_rate", 0)

    st.subheader("Key Performance Indicators")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Failures", failure_count)
    c2.metric("Exposure (h)", f"{total_exposure:.1f}")
    c3.metric("MTBF (h)", f"{mtbf:.2f}")
    c4.metric("MTTR (h)", f"{mttr:.2f}")
    c5.metric("Availability", f"{availability * 100:.1f}%")

    st.divider()

    # =====================================================================
    # Weibull Analysis (asset-specific)
    # =====================================================================
    st.subheader(" Weibull Analysis")

    weibull_fit = None
    ci = None

    if selected_asset_id is None:
        st.info("Select a specific asset to perform Weibull analysis and extended metrics.")
    else:
        uncensored_count = sum(1 for c_flag in censored if not c_flag) if censored else 0

        if uncensored_count >= 1 and intervals:
            try:
                weibull_fit = weibull.fit_weibull_mle_censored(intervals, censored)
                ci = weibull.bootstrap_weibull_ci(intervals, censored, n_bootstrap=200)

                c1, c2, c3, c4 = st.columns(4)

                with c1:
                    st.metric("Shape (beta)", f"{weibull_fit.shape:.3f}")
                    st.caption(f"95% CI: [{ci.shape_ci[0]:.3f}, {ci.shape_ci[1]:.3f}]")

                with c2:
                    st.metric("Scale (eta)", f"{weibull_fit.scale:.2f} h")
                    st.caption(f"95% CI: [{ci.scale_ci[0]:.2f}, {ci.scale_ci[1]:.2f}]")

                with c3:
                    if weibull_fit.shape < 0.95:
                        pattern = "Infant Mortality"
                    elif weibull_fit.shape <= 1.05:
                        pattern = "Random Failures"
                    else:
                        pattern = "Wear-out"
                    st.metric("Failure Pattern", pattern)

                with c4:
                    b10 = reliability_extended.compute_b_life(weibull_fit.shape, weibull_fit.scale, 10.0)
                    st.metric("B10 Life", f"{b10.life_hours:.1f} h")
                    st.caption("Time at which 10% fail")

                # Reliability curves
                st.markdown("**Reliability & Hazard Curves**")
                max_time = max(intervals) * 1.5 if intervals else 1000
                times = np.linspace(0, max_time, 100)
                curves = weibull.reliability_curves(weibull_fit.shape, weibull_fit.scale, times)

                col_r, col_h = st.columns(2)
                with col_r:
                    st.line_chart(
                        pd.DataFrame({"Time (h)": times, "Reliability R(t)": curves.reliability}).set_index("Time (h)")
                    )
                    st.caption("Probability of survival at time t")
                with col_h:
                    st.line_chart(
                        pd.DataFrame({"Time (h)": times, "Hazard h(t)": curves.hazard}).set_index("Time (h)")
                    )
                    st.caption("Instantaneous failure rate")

            except Exception as e:
                st.error(f"Weibull fitting failed: {e}")
        else:
            st.warning("Weibull analysis requires at least one complete failure interval.")

    st.divider()

    # =====================================================================
    # Extended Reliability Metrics (asset-specific)
    # =====================================================================
    if selected_asset_id is not None:
        st.subheader(" Extended Reliability")

        c1, c2, c3, c4 = st.columns(4)

        # MTTF
        with c1:
            if weibull_fit:
                mttf = reliability_extended.compute_mttf(weibull_fit.shape, weibull_fit.scale)
                st.metric("MTTF", f"{mttf:.1f} h")
                st.caption("Mean time to failure (Weibull)")
            else:
                st.metric("MTTF", "N/A")
                st.caption("Requires Weibull fit")

        # Failure rate
        with c2:
            fr = reliability_extended.compute_failure_rate(
                failure_count, total_exposure,
                shape=weibull_fit.shape if weibull_fit else None,
                scale=weibull_fit.scale if weibull_fit else None,
                current_age_hours=total_exposure,
            )
            st.metric("Failure Rate (lambda)", f"{fr.average_rate * 1000:.2f}")
            st.caption("per 1,000 hours (avg)")

        # Repair effectiveness
        with c3:
            if intervals and len(intervals) >= 4:
                re = reliability_extended.compute_repair_effectiveness(intervals)
                marker = "[+]" if re.improving else "[-]"
                st.metric("Repair Trend", f"{re.trend_ratio:.2f}x")
                st.caption(f"{marker} {'Improving' if re.improving else 'Degrading'}")
            else:
                st.metric("Repair Trend", "N/A")
                st.caption("Requires >= 4 intervals")

        # Instantaneous hazard
        with c4:
            if weibull_fit and total_exposure > 0:
                st.metric("Inst. Hazard", f"{fr.instantaneous_rate * 1000:.3f}")
                st.caption(f"per 1,000 h at {total_exposure:.0f} h age")
            else:
                st.metric("Inst. Hazard", "N/A")
                st.caption("Requires Weibull fit")

        # Conditional reliability calculator
        if weibull_fit:
            st.markdown("**Conditional Reliability Calculator**")
            st.caption("What is the probability this asset survives an additional mission given it has already survived to current age?")
            cr_c1, cr_c2, cr_c3 = st.columns(3)
            with cr_c1:
                current_age = st.number_input("Current age (hours)", value=float(total_exposure), min_value=0.0, step=50.0)
            with cr_c2:
                mission_time = st.number_input("Mission time (hours)", value=100.0, min_value=1.0, step=10.0)
            with cr_c3:
                cr = reliability_extended.compute_conditional_reliability(
                    weibull_fit.shape, weibull_fit.scale, current_age, mission_time
                )
                st.metric("Survival Probability", f"{cr.conditional_reliability * 100:.1f}%")
                st.caption(f"P(survive {mission_time:.0f}h more | already at {current_age:.0f}h)")

        st.divider()

    # =====================================================================
    # Asset Health Index (asset-specific)
    # =====================================================================
    if selected_asset_id is not None:
        st.subheader("Asset Health Index")

        # Compute components needed for health index
        dt_split = manufacturing.compute_downtime_split(filtered_events)
        perf = manufacturing.compute_performance_rate(filtered_exposures)
        oee_result = manufacturing.compute_oee(availability, perf.performance_rate)

        re_ratio = 1.0
        if intervals and len(intervals) >= 4:
            re = reliability_extended.compute_repair_effectiveness(intervals)
            re_ratio = re.trend_ratio

        hi = business.compute_health_index(
            availability=availability,
            mtbf_hours=mtbf,
            unplanned_ratio=dt_split.unplanned_ratio,
            weibull_shape=weibull_fit.shape if weibull_fit else None,
            oee=oee_result.oee,
            repair_trend_ratio=re_ratio,
        )

        # Display
        score_col, detail_col = st.columns([1, 3])

        with score_col:
            grade_colors = {"A": "green", "B": "green", "C": "orange", "D": "orange", "F": "red"}
            g_color = grade_colors.get(hi.grade, "gray")
            st.markdown(
                f"<div style='text-align:center; padding:20px;'>"
                f"<div style='font-size:64px; font-weight:bold; color:{g_color};'>{hi.score:.0f}</div>"
                f"<div style='font-size:32px; font-weight:600; color:{g_color};'>Grade {hi.grade}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        with detail_col:
            component_df = pd.DataFrame(
                [{"Component": k.replace("_", " ").title(), "Score": v} for k, v in hi.components.items()]
            )
            for _, row in component_df.iterrows():
                c_left, c_bar = st.columns([1, 3])
                with c_left:
                    st.markdown(f"**{row['Component']}**")
                with c_bar:
                    score_val = float(row["Score"])
                    st.progress(score_val / 100.0, text=f"{score_val:.0f} / 100")

        st.divider()

    # =====================================================================
    # RPN - Risk Priority Number (asset-specific)
    # =====================================================================
    if selected_asset_id is not None and filtered_details and failure_modes:
        st.subheader("Risk Priority Number (RPN)")
        st.caption("FMEA-style ranking: Severity x Occurrence x Detection")

        mode_names = {m.id: m.name for m in failure_modes}
        mode_categories = {m.id: m.category for m in failure_modes}

        # Build failure mode data with avg downtime
        event_map = {e.id: e for e in filtered_events}
        fm_agg = {}
        for d in filtered_details:
            m_name = mode_names.get(d.failure_mode_id, f"Mode #{d.failure_mode_id}")
            if m_name not in fm_agg:
                fm_agg[m_name] = {"name": m_name, "count": 0, "total_dt": 0.0}
            fm_agg[m_name]["count"] += 1
            evt = event_map.get(d.event_id)
            if evt:
                fm_agg[m_name]["total_dt"] += (evt.downtime_minutes or 0)

        fm_data = []
        for v in fm_agg.values():
            v["avg_downtime_minutes"] = v["total_dt"] / v["count"] if v["count"] > 0 else 0
            fm_data.append(v)

        if fm_data:
            rpn = reliability_extended.compute_rpn(fm_data, total_events=len(filtered_events))

            rpn_rows = []
            for entry in rpn.entries:
                risk_label = "HIGH" if entry.rpn >= 200 else ("MEDIUM" if entry.rpn >= 100 else "LOW")
                rpn_rows.append({
                    "Failure Mode": entry.failure_mode,
                    "Severity": entry.severity,
                    "Occurrence": entry.occurrence,
                    "Detection": entry.detection,
                    "RPN": entry.rpn,
                    "Risk": risk_label,
                })

            st.dataframe(rpn_rows, use_container_width=True, hide_index=True)
            st.caption(f"Max RPN: {rpn.max_rpn} - Higher values indicate higher risk priority.")
        else:
            st.info("No failure mode data to compute RPN.")

        st.divider()

    # =====================================================================
    # Manufacturing / OEE (asset-specific)
    # =====================================================================
    if selected_asset_id is not None:
        st.subheader("Manufacturing Performance (OEE)")

        mfg = manufacturing.aggregate_manufacturing_kpis(
            filtered_exposures, filtered_events, availability
        )

        # OEE headline
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            oee_val = mfg.oee.oee * 100
            if oee_val >= 85:
                label = "World-class"
            elif oee_val >= 65:
                label = "Typical"
            else:
                label = "Below average"
            st.metric("OEE", f"{oee_val:.1f}%", help=label)
        with c2:
            st.metric("Availability", f"{mfg.oee.availability * 100:.1f}%")
        with c3:
            st.metric("Performance", f"{mfg.oee.performance * 100:.1f}%")
        with c4:
            st.metric("Quality", f"{mfg.oee.quality * 100:.1f}%")

        # Downtime breakdown
        st.markdown("**Downtime Breakdown**")
        dt_c1, dt_c2 = st.columns(2)

        with dt_c1:
            total_dt = mfg.downtime_split.total_downtime_hours
            planned_pct = (1 - mfg.downtime_split.unplanned_ratio) if total_dt > 0 else 0
            st.markdown(f"**Planned:** {mfg.downtime_split.planned_downtime_hours:.1f} h ({mfg.downtime_split.planned_count} events)")
            st.progress(planned_pct, text=f"Planned: {planned_pct * 100:.0f}%")
            st.markdown(f"**Unplanned:** {mfg.downtime_split.unplanned_downtime_hours:.1f} h ({mfg.downtime_split.unplanned_count} events)")
            st.progress(mfg.downtime_split.unplanned_ratio, text=f"Unplanned: {mfg.downtime_split.unplanned_ratio * 100:.0f}%")

        with dt_c2:
            st.metric("MTBM", f"{mfg.mtbm.mtbm_hours:.1f} h", help="Mean time between maintenance (all types)")
            st.metric("Throughput", f"{mfg.performance.actual_throughput:.1f} cycles/h",
                       help=f"Design: {mfg.performance.design_throughput:.1f} cycles/h")
            st.metric("Total Cycles", f"{mfg.performance.total_cycles:.0f}")

        st.divider()

    # =====================================================================
    # Business Impact (asset-specific)
    # =====================================================================
    if selected_asset_id is not None:
        st.subheader("Business Impact")

        biz_c1, biz_c2 = st.columns(2)

        with biz_c1:
            st.markdown("**Cost of Unreliability (COUR)**")

            # Configurable cost parameters
            with st.expander("Cost Parameters", expanded=False):
                hourly_prod_val = st.number_input("Hourly production value ($)", value=500.0, step=50.0)
                avg_repair = st.number_input("Average repair cost ($)", value=1500.0, step=100.0)

            dt_split = manufacturing.compute_downtime_split(filtered_events)
            cour = business.compute_cour(
                dt_split.unplanned_downtime_hours, failure_count,
                hourly_production_value=hourly_prod_val,
                avg_repair_cost=avg_repair,
            )

            st.metric("Total Cost", f"${cour.total_cost:,.0f}")
            sub_c1, sub_c2 = st.columns(2)
            with sub_c1:
                st.metric("Lost Production", f"${cour.lost_production_cost:,.0f}")
                st.metric("Repair Cost", f"${cour.repair_cost:,.0f}")
            with sub_c2:
                st.metric("Cost per Failure", f"${cour.cost_per_failure:,.0f}")
                st.metric("Unplanned DT", f"{cour.unplanned_downtime_hours:.1f} h")

        with biz_c2:
            st.markdown("**PM Optimization**")

            if weibull_fit:
                pm = business.compute_pm_optimization(weibull_fit.shape, weibull_fit.scale)

                st.metric("Failure Pattern", pm.failure_pattern.replace("_", " ").title())
                st.metric("Recommended PM Interval", f"{pm.recommended_pm_hours:.0f} h")

                assessment_msgs = {
                    "pm_not_recommended": "PM may not reduce failures. Consider condition-based monitoring.",
                    "appropriate": "Current PM interval is well-matched to failure behavior.",
                    "over_maintaining": "PM is more frequent than necessary. Consider extending intervals.",
                    "under_maintaining": "PM is too infrequent. Risk of unplanned failures.",
                    "no_pm_data": "No PM scheduling data available for comparison.",
                }
                st.info(assessment_msgs.get(pm.assessment, pm.assessment))
            else:
                st.info("PM optimization requires Weibull analysis (select an asset with failure data).")

        st.divider()

    # =====================================================================
    # Failure Mode Pareto
    # =====================================================================
    st.subheader("Failure Mode Pareto")

    if filtered_details and failure_modes:
        event_ids = {e.id for e in filtered_events}
        mode_counts = {}
        for detail in filtered_details:
            if detail.event_id in event_ids:
                mode_counts[detail.failure_mode_id] = mode_counts.get(detail.failure_mode_id, 0) + 1

        if mode_counts:
            mode_names_map = {m.id: m.name for m in failure_modes}
            mode_cat_map = {m.id: m.category for m in failure_modes}
            pareto_data = []
            for mode_id, count in sorted(mode_counts.items(), key=lambda x: x[1], reverse=True):
                pareto_data.append({
                    "Failure Mode": mode_names_map.get(mode_id, f"Mode #{mode_id}"),
                    "Category": mode_cat_map.get(mode_id, "N/A"),
                    "Count": count,
                })

            p_c1, p_c2 = st.columns(2)
            with p_c1:
                st.dataframe(pareto_data, use_container_width=True, hide_index=True)
            with p_c2:
                df = pd.DataFrame(pareto_data)
                st.bar_chart(df.set_index("Failure Mode")["Count"])
        else:
            st.info("No failure mode data linked to filtered events.")
    else:
        st.info("Add failure details in Event Details to populate Pareto chart.")

    st.divider()

    # =====================================================================
    # MTBF Trend
    # =====================================================================
    st.subheader("MTBF Trend")

    if len(failure_events) >= 2:
        sorted_failures = sorted(failure_events, key=lambda e: e.timestamp)
        trend_intervals = []
        trend_labels = []
        for i in range(1, len(sorted_failures)):
            prev = sorted_failures[i - 1].timestamp
            curr = sorted_failures[i].timestamp
            hours = (curr - prev).total_seconds() / 3600
            trend_intervals.append(hours)
            trend_labels.append(f"#{i + 1}")

        if trend_intervals:
            trend_df = pd.DataFrame({"Failure": trend_labels, "TBF (h)": trend_intervals})
            st.line_chart(trend_df.set_index("Failure"))

            m_c1, m_c2, m_c3 = st.columns(3)
            m_c1.metric("Min Interval", f"{min(trend_intervals):.1f} h")
            m_c2.metric("Max Interval", f"{max(trend_intervals):.1f} h")
            m_c3.metric("Avg Interval", f"{sum(trend_intervals) / len(trend_intervals):.1f} h")
    else:
        st.info("Log at least 2 failure events to see MTBF trend.")

    st.divider()

    # =====================================================================
    # Fleet Bad Actors
    # =====================================================================
    st.subheader("Fleet Bad Actors")
    st.caption("Worst-performing assets ranked by composite score (failures, downtime, availability)")

    bad_actor_data = []
    for asset in assets:
        a_events = [e for e in events if e.asset_id == asset.id]
        a_exposures = [e for e in exposures if e.asset_id == asset.id]
        a_kpi = metrics.aggregate_kpis(a_exposures, a_events)
        a_failures = [e for e in a_events if e.event_type == "failure"]
        total_dt_hrs = sum((e.downtime_minutes or 0) for e in a_failures) / 60.0
        bad_actor_data.append({
            "asset_id": asset.id,
            "asset_name": asset.name,
            "failure_count": len(a_failures),
            "total_downtime_hours": total_dt_hrs,
            "availability": a_kpi["availability"],
        })

    if bad_actor_data:
        ranked = reliability_extended.rank_bad_actors(bad_actor_data, top_n=10)
        if ranked.entries:
            ba_rows = []
            for i, e in enumerate(ranked.entries):
                ba_rows.append({
                    "Rank": i + 1,
                    "Asset": e.asset_name,
                    "Failures": e.failure_count,
                    "Downtime (h)": f"{e.total_downtime_hours:.1f}",
                    "Availability": f"{e.availability * 100:.1f}%",
                    "Score": f"{e.composite_score:.3f}",
                })
            st.dataframe(ba_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No bad actor data to display.")
    else:
        st.info("No assets to rank.")

    st.divider()

    # =====================================================================
    # Failure Timeline
    # =====================================================================
    st.subheader("Failure Timeline")

    if failure_events:
        sorted_failures = sorted(failure_events, key=lambda e: e.timestamp, reverse=True)[:20]
        asset_names = {a.id: a.name for a in assets}
        f_data = []
        for evt in sorted_failures:
            f_data.append({
                "Timestamp": evt.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Asset": f"#{evt.asset_id} - {asset_names.get(evt.asset_id, 'Unknown')}",
                "Downtime (min)": evt.downtime_minutes or 0,
                "Description": evt.description or "N/A",
            })
        st.dataframe(f_data, use_container_width=True, hide_index=True)
    else:
        st.info("No failure events recorded yet.")

    st.divider()

    # =====================================================================
    # PDF Report Download (asset-specific)
    # =====================================================================
    if selected_asset_id is not None and weibull_fit and ci:
        st.subheader("Download PDF Report")

        if st.button("Generate & Download PDF Report", type="primary"):
            with st.spinner("Generating report..."):
                with get_session() as session:
                    detail_svc = EventDetailService(session)
                    mode_svc = FailureModeService(session)
                    asset_svc = AssetService(session)
                    exposure_svc = ExposureService(session)
                    event_svc = EventService(session)

                    asset = asset_svc.get(selected_asset_id)
                    asset_exposures = exposure_svc.list(asset_id=selected_asset_id, limit=500)
                    asset_events = event_svc.list(asset_id=selected_asset_id, limit=500)
                    all_details = detail_svc.list(limit=500)
                    all_modes = mode_svc.list(limit=500)

                    ev_ids = {e.id for e in asset_events}
                    asset_details = [d for d in all_details if d.event_id in ev_ids]
                    mode_name_map = {m.id: m.name for m in all_modes}

                    failure_counts_map = {}
                    for d in asset_details:
                        name = mode_name_map.get(d.failure_mode_id, "Unknown")
                        failure_counts_map[name] = failure_counts_map.get(name, 0) + 1

                    max_t = max(intervals) * 1.5 if intervals else 1000
                    t_arr = np.linspace(0, max_t, 100)
                    c_data = weibull.reliability_curves(weibull_fit.shape, weibull_fit.scale, t_arr)

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
                            "times": list(c_data.times),
                            "reliability": list(c_data.reliability),
                            "hazard": list(c_data.hazard),
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
                        "failure_counts": failure_counts_map,
                    }

                    with tempfile.TemporaryDirectory() as tmpdir:
                        output_dir = Path(tmpdir)
                        pdf_path = reporting.generate_asset_report(output_dir, context)
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()

                        st.download_button(
                            label="Download PDF",
                            data=pdf_bytes,
                            file_name=f"asset_{selected_asset_id}_reliability_report.pdf",
                            mime="application/pdf",
                        )

                st.success("Report generated! Click the download button above.")


main()
