"""Asset Deep Dive — comprehensive analytics for a single asset."""
import streamlit as st
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path
from scipy import stats

st.set_page_config(page_title="Asset Deep Dive - RELIABASE", page_icon="🔬", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import (  # noqa: E402
    AssetService, EventService, ExposureService,
    FailureModeService, EventDetailService,
)
from reliabase.analytics import (  # noqa: E402
    metrics, weibull, reporting,
    reliability_extended, manufacturing, business,
)


_GRADE_ICON = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🟠", "F": "🔴"}


def main():
    st.title("🔬 Asset Deep Dive")
    st.markdown("Select an asset for comprehensive reliability, manufacturing, and business analytics.")

    # --- Load all data ------------------------------------------------------
    with get_session() as session:
        assets = AssetService(session).list(limit=500)
        events = EventService(session).list(limit=500)
        exposures = ExposureService(session).list(limit=500)
        failure_modes = FailureModeService(session).list(limit=500)
        event_details = EventDetailService(session).list(limit=500)

    if not assets:
        st.warning("No assets available. Seed demo data from the **Operations** page.")
        return

    # --- Asset Selector (required — no "All Assets") ------------------------
    asset_options = {f"#{a.id} — {a.name}": a.id for a in assets}
    selected_label = st.selectbox("Select Asset", options=list(asset_options.keys()))
    selected_asset_id = asset_options[selected_label]

    # Find the selected asset object
    selected_asset = next(a for a in assets if a.id == selected_asset_id)

    # --- Filter data for selected asset -------------------------------------
    filtered_events = [e for e in events if e.asset_id == selected_asset_id]
    filtered_exposures = [e for e in exposures if e.asset_id == selected_asset_id]
    failure_events = [e for e in filtered_events if e.event_type == "failure"]
    failure_count = len(failure_events)
    filtered_details = [d for d in event_details if d.event_id in {e.id for e in filtered_events}]

    # Compute KPIs
    kpi = metrics.aggregate_kpis(filtered_exposures, filtered_events)
    intervals = kpi["intervals_hours"]
    censored = kpi["censored_flags"]
    availability = kpi["availability"]

    # ========================================================================
    # Identity Header
    # ========================================================================
    dt_split = manufacturing.compute_downtime_split(filtered_events)
    perf = manufacturing.compute_performance_rate(filtered_exposures)
    oee_result = manufacturing.compute_oee(availability, perf.performance_rate)

    hi = business.compute_health_index(
        availability=availability,
        mtbf_hours=kpi["mtbf_hours"],
        unplanned_ratio=dt_split.unplanned_ratio,
        oee=oee_result.oee,
    )
    g_icon = _GRADE_ICON.get(hi.grade, "⚪")

    st.markdown(f"### {g_icon} {selected_asset.name} — Grade {hi.grade} ({hi.score:.0f}/100)")
    meta_parts = []
    if selected_asset.type:
        meta_parts.append(f"**Type:** {selected_asset.type}")
    if selected_asset.serial:
        meta_parts.append(f"**Serial:** {selected_asset.serial}")
    if selected_asset.in_service_date:
        meta_parts.append(f"**In Service:** {selected_asset.in_service_date}")
    if meta_parts:
        st.caption(" · ".join(meta_parts))

    st.divider()

    # ========================================================================
    # Core KPIs
    # ========================================================================
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Failures", failure_count,
        help="Total failure events for this asset. "
             "Each represents an unplanned loss of function.",
    )
    c2.metric(
        "MTBF", f"{kpi['mtbf_hours']:,.0f} h" if kpi["mtbf_hours"] < 1e6 else "N/A",
        help="Mean Time Between Failures — average operating hours between consecutive failures. "
             "Higher = more reliable. Requires ≥ 2 failures to calculate.",
    )
    c3.metric(
        "MTTR", f"{kpi['mttr_hours']:.1f} h",
        help="Mean Time To Repair — average downtime per failure event (in hours). "
             "Lower = faster recovery. Based on logged downtime_minutes.",
    )
    c4.metric(
        "Availability", f"{availability * 100:.1f}%",
        help="Proportion of time the asset is operational. "
             "Calculated as MTBF / (MTBF + MTTR). Target: > 95%.",
    )

    st.divider()

    # ========================================================================
    # Weibull Analysis
    # ========================================================================
    st.subheader("Weibull Analysis")

    weibull_fit = None
    ci = None

    if len(intervals) >= 2:
        weibull_fit = weibull.fit_weibull_mle_censored(intervals, censored)
        ci = weibull.bootstrap_weibull_ci(intervals, censored, n_bootstrap=200)

        # Pattern interpretation
        beta = weibull_fit.shape
        if beta < 1:
            pattern = "Infant Mortality"
            pattern_help = ("Beta < 1 indicates decreasing failure rate — "
                            "failures are more likely early in life. "
                            "Consider burn-in testing or quality screening.")
        elif abs(beta - 1) < 0.15:
            pattern = "Random"
            pattern_help = ("Beta ≈ 1 indicates constant failure rate — "
                            "failures occur randomly regardless of age. "
                            "Time-based PM is not effective; consider CBM.")
        else:
            pattern = "Wear-Out"
            pattern_help = ("Beta > 1 indicates increasing failure rate — "
                            "the asset degrades with age. "
                            "Time-based PM is appropriate and recommended.")

        w1, w2, w3, w4 = st.columns(4)
        w1.metric(
            "Beta (Shape)", f"{beta:.2f}",
            help="Weibull shape parameter (β). Determines the failure pattern: "
                 "β < 1 = infant mortality, β ≈ 1 = random, β > 1 = wear-out. "
                 f"95% CI: [{ci.shape_ci[0]:.2f}, {ci.shape_ci[1]:.2f}]",
        )
        w2.metric(
            "Eta (Scale)", f"{weibull_fit.scale:.0f} h",
            help="Weibull scale parameter (η). The characteristic life — "
                 "63.2% of units will fail by this time. "
                 f"95% CI: [{ci.scale_ci[0]:.0f}, {ci.scale_ci[1]:.0f}]",
        )
        w3.metric(
            "Failure Pattern", pattern,
            help=pattern_help,
        )
        # B10 life
        b10 = reliability_extended.compute_b_life(weibull_fit.shape, weibull_fit.scale, 10.0)
        reliability_at_b10 = 1.0 - b10.percentile / 100.0
        w4.metric(
            "B10 Life", f"{b10.life_hours:.0f} h",
            help=f"B10 life — the time by which {b10.percentile:.0f}% of units are expected to fail. "
                 "Used for warranty, PM scheduling, and spare parts planning. "
                 f"Reliability at B10: {reliability_at_b10 * 100:.1f}%",
        )

        # Confidence intervals
        with st.expander("Confidence Intervals"):
            st.markdown(
                f"- **Shape (β):** {ci.shape_ci[0]:.3f} – {ci.shape_ci[1]:.3f}  \n"
                f"- **Scale (η):** {ci.scale_ci[0]:.1f} – {ci.scale_ci[1]:.1f} hours  \n"
                f"- Method: Bootstrap (200 samples, 95% CI)"
            )

        # Reliability curves
        st.markdown("**Reliability & Hazard Curves**")
        max_t = max(intervals) * 1.5 if intervals else 1000
        times = np.linspace(0, max_t, 200)
        curves = weibull.reliability_curves(weibull_fit.shape, weibull_fit.scale, times)

        curve_left, curve_right = st.columns(2)
        with curve_left:
            r_df = pd.DataFrame({"Time (h)": list(curves.times), "Reliability": list(curves.reliability)})
            st.line_chart(r_df.set_index("Time (h)"), y="Reliability")
            st.caption("Probability of survival over time. R(t) = e^(-(t/η)^β)")
        with curve_right:
            h_df = pd.DataFrame({"Time (h)": list(curves.times), "Hazard Rate": list(curves.hazard)})
            st.line_chart(h_df.set_index("Time (h)"), y="Hazard Rate")
            st.caption("Instantaneous failure rate at time t. Increasing = wear-out.")

    else:
        st.info(
            "Weibull analysis requires at least 2 failure intervals. "
            "Log more failure events and exposure data to enable this section."
        )

    st.divider()

    # ========================================================================
    # Extended Reliability
    # ========================================================================
    st.subheader("Extended Reliability Metrics")

    if weibull_fit:
        er1, er2, er3 = st.columns(3)

        # MTTF
        mttf = reliability_extended.compute_mttf(weibull_fit.shape, weibull_fit.scale)
        er1.metric(
            "MTTF", f"{mttf:,.0f} h",
            help="Mean Time To Failure — statistical average lifespan from the Weibull model. "
                 "MTTF = η × Γ(1 + 1/β). Useful for long-term planning.",
        )

        # Failure rate at median time
        if intervals:
            median_t = sorted(intervals)[len(intervals) // 2]
            fr = reliability_extended.compute_failure_rate(
                total_failures=len(intervals),
                total_operating_hours=sum(intervals),
                shape=weibull_fit.shape,
                scale=weibull_fit.scale,
                current_age_hours=median_t,
            )
            er2.metric(
                "Failure Rate (median)", f"{fr.instantaneous_rate:.4f} /h",
                help=f"Instantaneous failure rate at the median operating time ({median_t:.0f}h). "
                     f"Average rate: {fr.average_rate:.4f} /h. "
                     "A rising failure rate indicates wear-out.",
            )

        # Repair trend
        if len(intervals) >= 3:
            re = reliability_extended.compute_repair_effectiveness(intervals)
            if re.improving and re.trend_ratio <= 1.05:
                trend_label = "Improving"
            elif re.trend_ratio <= 1.2:
                trend_label = "Stable"
            else:
                trend_label = "Degrading"
            er3.metric(
                "Repair Trend", trend_label,
                delta=f"Ratio: {re.trend_ratio:.2f}",
                delta_color="normal" if trend_label == "Improving" else (
                    "off" if trend_label == "Stable" else "inverse"
                ),
                help="Compares recent TBF intervals to earlier ones. "
                     "Ratio < 1 = improving (intervals growing), "
                     "Ratio > 1 = degrading (intervals shrinking), "
                     "Ratio ≈ 1 = stable.",
            )

        # Conditional reliability calculator
        st.markdown("**Conditional Reliability Calculator**")
        st.caption(
            "Given the asset has survived to age T, what is the probability "
            "it survives an additional Δt hours?"
        )
        calc_c1, calc_c2, calc_c3 = st.columns(3)
        with calc_c1:
            current_age = st.number_input(
                "Current age (h)", min_value=0.0,
                value=float(intervals[-1]) if intervals else 100.0,
                step=10.0,
                help="How many hours the asset has operated since last failure or installation.",
            )
        with calc_c2:
            mission_time = st.number_input(
                "Mission time Δt (h)", min_value=1.0, value=100.0, step=10.0,
                help="Additional hours you want the asset to survive.",
            )
        with calc_c3:
            if weibull_fit:
                cr = reliability_extended.compute_conditional_reliability(
                    weibull_fit.shape, weibull_fit.scale, current_age, mission_time
                )
                # Compute unconditional reliabilities for help text
                _dist = stats.weibull_min(c=weibull_fit.shape, scale=weibull_fit.scale)
                _r_t = _dist.sf(current_age)
                _r_t_dt = _dist.sf(current_age + mission_time)
                st.metric(
                    "Conditional R(t+Δt|t)", f"{cr.conditional_reliability * 100:.1f}%",
                    help=f"Probability this asset survives {mission_time:.0f} more hours "
                         f"given it has already run {current_age:.0f} hours. "
                         f"Unconditional reliability at t: {_r_t * 100:.1f}%, "
                         f"at t+Δt: {_r_t_dt * 100:.1f}%.",
                )
    else:
        st.info("Extended reliability metrics require Weibull analysis (≥ 2 failure intervals).")

    st.divider()

    # ========================================================================
    # Health Index
    # ========================================================================
    st.subheader("Asset Health Index")

    hi_c1, hi_c2 = st.columns([1, 2])
    with hi_c1:
        st.metric(
            f"{g_icon} Health Score", f"{hi.score:.0f} / 100",
            help="Composite health index (0-100). Weighted from: "
                 "Availability (30%), MTBF performance (25%), "
                 "Downtime quality (15%), Wear-out margin (15%), "
                 "OEE (10%), Repair trend (5%).",
        )
        st.metric(
            "Grade", hi.grade,
            help="A (≥ 85) Excellent | B (≥ 70) Good | C (≥ 55) Fair | "
                 "D (≥ 40) Poor | F (< 40) Critical",
        )
    with hi_c2:
        st.markdown("**Component Scores**")
        comp = hi.components
        comp_cols = st.columns(3)
        comp_items = [
            ("Availability", comp["availability"],
             "Based on MTBF/(MTBF+MTTR). Weight: 30%."),
            ("MTBF Performance", comp["mtbf_performance"],
             "MTBF vs target ratio. Weight: 25%."),
            ("Downtime Quality", comp["downtime_quality"],
             "Proportion of planned vs unplanned downtime. Weight: 15%."),
            ("Wear-Out Margin", comp["wearout_margin"],
             "Based on Weibull β. Higher β = more wear-out risk. Weight: 15%."),
            ("OEE", comp["oee"],
             "Overall Equipment Effectiveness score. Weight: 10%."),
            ("Repair Trend", comp["repair_trend"],
             "Are repairs restoring the asset effectively? Weight: 5%."),
        ]
        for j, (label, value, tip) in enumerate(comp_items):
            with comp_cols[j % 3]:
                st.metric(label, f"{value:.0f}", help=tip)

    st.divider()

    # ========================================================================
    # RPN / FMEA
    # ========================================================================
    st.subheader("Risk Priority Number (RPN)")
    st.caption(
        "FMEA-style risk ranking. RPN = Severity × Occurrence × Detection. "
        "Higher RPN = higher risk priority."
    )

    # Build failure mode aggregation
    fm_agg: dict[int, dict] = {}
    ev_ids = {e.id for e in filtered_events}
    for d in filtered_details:
        fmid = d.failure_mode_id
        if fmid not in fm_agg:
            fm_agg[fmid] = {
                "failure_mode": next((m.name for m in failure_modes if m.id == fmid), f"Mode #{fmid}"),
                "count": 0,
                "total_dt": 0.0,
            }
        fm_agg[fmid]["count"] += 1
        # Find the event's downtime
        evt = next((e for e in filtered_events if e.id == d.event_id), None)
        if evt:
            fm_agg[fmid]["total_dt"] += (evt.downtime_minutes or 0)

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
        st.caption(f"Max RPN: {rpn.max_rpn} — Higher values indicate higher risk priority.")
    else:
        st.info("No failure mode data to compute RPN. Link event details to failure modes.")

    st.divider()

    # ========================================================================
    # Manufacturing Performance (OEE)
    # ========================================================================
    st.subheader("Manufacturing Performance (OEE)")

    mfg = manufacturing.aggregate_manufacturing_kpis(
        filtered_exposures, filtered_events, availability
    )

    oee_c1, oee_c2, oee_c3, oee_c4 = st.columns(4)
    oee_val = mfg.oee.oee * 100
    if oee_val >= 85:
        oee_label = "World-class"
    elif oee_val >= 65:
        oee_label = "Typical"
    else:
        oee_label = "Below average"

    oee_c1.metric(
        "OEE", f"{oee_val:.1f}%",
        help=f"Overall Equipment Effectiveness = Availability × Performance × Quality. "
             f"Status: {oee_label}. World-class benchmark: ≥ 85%.",
    )
    oee_c2.metric(
        "Availability", f"{mfg.oee.availability * 100:.1f}%",
        help="Proportion of planned production time the equipment was running. "
             "Losses: breakdowns, setup, adjustments.",
    )
    oee_c3.metric(
        "Performance", f"{mfg.oee.performance * 100:.1f}%",
        help="Actual throughput vs design throughput. "
             "Losses: slow cycles, minor stops, speed reductions.",
    )
    oee_c4.metric(
        "Quality", f"{mfg.oee.quality * 100:.1f}%",
        help="Proportion of output meeting quality standards. "
             "Losses: defects, rework, scrap.",
    )

    # Downtime breakdown
    st.markdown("**Downtime Breakdown**")
    dt_left, dt_right = st.columns(2)
    with dt_left:
        total_dt = mfg.downtime_split.total_downtime_hours
        planned_pct = (1 - mfg.downtime_split.unplanned_ratio) if total_dt > 0 else 0
        st.markdown(
            f"**Planned:** {mfg.downtime_split.planned_downtime_hours:.1f} h "
            f"({mfg.downtime_split.planned_count} events)"
        )
        st.progress(planned_pct, text=f"Planned: {planned_pct * 100:.0f}%")
        st.markdown(
            f"**Unplanned:** {mfg.downtime_split.unplanned_downtime_hours:.1f} h "
            f"({mfg.downtime_split.unplanned_count} events)"
        )
        st.progress(
            mfg.downtime_split.unplanned_ratio,
            text=f"Unplanned: {mfg.downtime_split.unplanned_ratio * 100:.0f}%",
        )
    with dt_right:
        st.metric(
            "MTBM", f"{mfg.mtbm.mtbm_hours:.1f} h",
            help="Mean Time Between Maintenance — includes both planned and unplanned events. "
                 "A holistic view of how often the asset requires any maintenance action.",
        )
        st.metric(
            "Throughput", f"{mfg.performance.actual_throughput:.1f} cycles/h",
            help=f"Actual production rate. Design: {mfg.performance.design_throughput:.1f} cycles/h. "
                 "Gap indicates speed losses.",
        )
        st.metric(
            "Total Cycles", f"{mfg.performance.total_cycles:.0f}",
            help="Total production cycles logged across all exposure records.",
        )

    st.divider()

    # ========================================================================
    # Business Impact
    # ========================================================================
    st.subheader("Business Impact")

    biz_left, biz_right = st.columns(2)

    with biz_left:
        st.markdown("**Cost of Unreliability (COUR)**")
        st.caption(
            "Financial impact of unplanned failures. "
            "COUR = lost production + repair costs."
        )

        with st.expander("Cost Parameters", expanded=False):
            hourly_prod_val = st.number_input(
                "Hourly production value ($)", value=500.0, step=50.0,
                help="Revenue lost per hour of unplanned downtime.",
            )
            avg_repair = st.number_input(
                "Average repair cost ($)", value=1500.0, step=100.0,
                help="Average cost of parts + labor per failure event.",
            )

        dt_split_biz = manufacturing.compute_downtime_split(filtered_events)
        cour = business.compute_cour(
            dt_split_biz.unplanned_downtime_hours, failure_count,
            hourly_production_value=hourly_prod_val,
            avg_repair_cost=avg_repair,
        )

        st.metric(
            "Total Cost", f"${cour.total_cost:,.0f}",
            help="Total estimated cost of unreliability = lost production + repair cost.",
        )
        sub1, sub2 = st.columns(2)
        sub1.metric(
            "Lost Production", f"${cour.lost_production_cost:,.0f}",
            help="Unplanned downtime hours × hourly production value.",
        )
        sub1.metric(
            "Repair Cost", f"${cour.repair_cost:,.0f}",
            help="Number of failures × average repair cost.",
        )
        sub2.metric(
            "Cost per Failure", f"${cour.cost_per_failure:,.0f}",
            help="Total COUR / number of failures. Use to justify PM investments.",
        )
        sub2.metric(
            "Unplanned DT", f"{cour.unplanned_downtime_hours:.1f} h",
            help="Total hours of unplanned (failure-related) downtime.",
        )

    with biz_right:
        st.markdown("**PM Optimization**")
        st.caption(
            "Recommended preventive maintenance strategy based on Weibull failure pattern."
        )

        if weibull_fit:
            pm = business.compute_pm_optimization(weibull_fit.shape, weibull_fit.scale)

            st.metric(
                "Failure Pattern", pm.failure_pattern.replace("_", " ").title(),
                help="Derived from Weibull beta: infant_mortality (β<1), "
                     "random (β≈1), or wear_out (β>1).",
            )
            st.metric(
                "Recommended PM Interval", f"{pm.recommended_pm_hours:.0f} h",
                help="Optimal PM interval calculated from the Weibull model. "
                     "Balances failure risk against maintenance cost.",
            )

            assessment_msgs = {
                "pm_not_recommended": "PM may not reduce failures. Consider condition-based monitoring.",
                "appropriate": "Current PM interval is well-matched to failure behavior.",
                "over_maintaining": "PM is more frequent than necessary. Consider extending intervals.",
                "under_maintaining": "PM is too infrequent. Risk of unplanned failures.",
                "no_pm_data": "No PM scheduling data available for comparison.",
            }
            st.info(assessment_msgs.get(pm.assessment, pm.assessment))
        else:
            st.info("PM optimization requires Weibull analysis (≥ 2 failure intervals).")

    st.divider()

    # ========================================================================
    # Failure Mode Pareto
    # ========================================================================
    st.subheader("Failure Mode Pareto")
    st.caption("Failure modes for this asset ranked by frequency. Focus on the top contributors.")

    if filtered_details and failure_modes:
        mode_counts: dict[int, int] = {}
        for detail in filtered_details:
            mode_counts[detail.failure_mode_id] = mode_counts.get(detail.failure_mode_id, 0) + 1

        if mode_counts:
            mode_name_map = {m.id: m.name for m in failure_modes}
            mode_cat_map = {m.id: m.category for m in failure_modes}
            pareto_data = []
            for mode_id, count in sorted(mode_counts.items(), key=lambda x: x[1], reverse=True):
                pareto_data.append({
                    "Failure Mode": mode_name_map.get(mode_id, f"Mode #{mode_id}"),
                    "Category": mode_cat_map.get(mode_id, "N/A"),
                    "Count": count,
                })

            p_left, p_right = st.columns(2)
            with p_left:
                st.dataframe(pareto_data, use_container_width=True, hide_index=True)
            with p_right:
                df = pd.DataFrame(pareto_data)
                st.bar_chart(df.set_index("Failure Mode")["Count"])
        else:
            st.info("No failure mode data linked to this asset's events.")
    else:
        st.info("Add failure details in **Event Details** to populate the Pareto chart.")

    st.divider()

    # ========================================================================
    # TBF Trend
    # ========================================================================
    st.subheader("Time Between Failures Trend")
    st.caption(
        "Tracks how TBF intervals change over time. "
        "An upward trend means reliability is improving after repairs."
    )

    if len(failure_events) >= 2:
        sorted_failures = sorted(failure_events, key=lambda e: e.timestamp)
        trend_intervals = []
        trend_labels = []
        for i in range(1, len(sorted_failures)):
            prev_t = sorted_failures[i - 1].timestamp
            curr_t = sorted_failures[i].timestamp
            hours = (curr_t - prev_t).total_seconds() / 3600
            trend_intervals.append(hours)
            trend_labels.append(f"#{i + 1}")

        if trend_intervals:
            trend_df = pd.DataFrame({"Failure": trend_labels, "TBF (h)": trend_intervals})
            st.line_chart(trend_df.set_index("Failure"))

            tc1, tc2, tc3 = st.columns(3)
            tc1.metric(
                "Min Interval", f"{min(trend_intervals):.1f} h",
                help="Shortest gap between consecutive failures for this asset.",
            )
            tc2.metric(
                "Max Interval", f"{max(trend_intervals):.1f} h",
                help="Longest gap between consecutive failures for this asset.",
            )
            tc3.metric(
                "Avg Interval", f"{sum(trend_intervals) / len(trend_intervals):.1f} h",
                help="Average gap between consecutive failures. Compare to MTBF.",
            )
    else:
        st.info("Log at least 2 failure events to see the TBF trend.")

    st.divider()

    # ========================================================================
    # Failure Timeline
    # ========================================================================
    st.subheader("Failure Timeline")

    if failure_events:
        recent = sorted(failure_events, key=lambda e: e.timestamp, reverse=True)[:20]
        f_data = [
            {
                "Timestamp": e.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Downtime (min)": e.downtime_minutes or 0,
                "Description": e.description or "—",
            }
            for e in recent
        ]
        st.dataframe(f_data, use_container_width=True, hide_index=True)
    else:
        st.info("No failure events recorded for this asset.")

    st.divider()

    # ========================================================================
    # PDF Report Download
    # ========================================================================
    if weibull_fit and ci:
        st.subheader("Download PDF Report")
        st.caption("Generate a comprehensive reliability report for this asset.")

        if st.button("Generate & Download PDF Report", type="primary"):
            with st.spinner("Generating report..."):
                with get_session() as session:
                    detail_svc = EventDetailService(session)
                    mode_svc = FailureModeService(session)

                    all_details = detail_svc.list(limit=500)
                    all_modes = mode_svc.list(limit=500)
                    local_ev_ids = {e.id for e in filtered_events}
                    asset_details = [d for d in all_details if d.event_id in local_ev_ids]
                    mode_name_map = {m.id: m.name for m in all_modes}

                    failure_counts_map: dict[str, int] = {}
                    for d in asset_details:
                        name = mode_name_map.get(d.failure_mode_id, "Unknown")
                        failure_counts_map[name] = failure_counts_map.get(name, 0) + 1

                    max_t = max(intervals) * 1.5 if intervals else 1000
                    t_arr = np.linspace(0, max_t, 100)
                    c_data = weibull.reliability_curves(weibull_fit.shape, weibull_fit.scale, t_arr)

                    context = {
                        "asset": selected_asset,
                        "metrics": kpi,
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
                            for e in filtered_events
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
