"""Fleet Overview — standalone fleet-wide analytics dashboard."""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Fleet Overview - RELIABASE", page_icon="🏭", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import (  # noqa: E402
    AssetService, EventService, ExposureService,
    FailureModeService, EventDetailService, PartService,
)
from reliabase.analytics import (  # noqa: E402
    metrics, reliability_extended, business, manufacturing,
)


_GRADE_ICON = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🟠", "F": "🔴"}


def main():
    st.title("🏭 Fleet Overview")
    st.markdown("Fleet-wide reliability analytics — compare every asset at a glance.")

    # --- Load all data ------------------------------------------------------
    with get_session() as session:
        assets = AssetService(session).list(limit=500)
        events = EventService(session).list(limit=500)
        exposures = ExposureService(session).list(limit=500)
        failure_modes = FailureModeService(session).list(limit=500)
        details = EventDetailService(session).list(limit=500)
        parts = PartService(session).list_parts(limit=500)

    if not assets:
        st.warning("No data available. Seed demo data from the **Operations** page.")
        return

    failure_events = [e for e in events if e.event_type == "failure"]
    fleet_kpi = metrics.aggregate_kpis(exposures, events)

    # ========================================================================
    # Fleet KPIs
    # ========================================================================
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(
        "Assets", len(assets),
        help="Total number of registered assets in the fleet.",
    )
    c2.metric(
        "Total Failures", fleet_kpi["failure_count"],
        help="Count of all failure-type events across the fleet.",
    )
    c3.metric(
        "Fleet MTBF",
        f"{fleet_kpi['mtbf_hours']:,.0f} h" if fleet_kpi["mtbf_hours"] < 1e6 else "N/A",
        help="Mean Time Between Failures for the entire fleet. "
             "Calculated as total operating hours / total failures.",
    )
    c4.metric(
        "Fleet Availability", f"{fleet_kpi['availability'] * 100:.1f}%",
        help="Proportion of time the fleet is operational. "
             "Calculated as MTBF / (MTBF + MTTR).",
    )
    c5.metric(
        "Exposure Hours", f"{fleet_kpi['total_exposure_hours']:,.0f}",
        help="Sum of all logged operating hours across every asset.",
    )

    st.divider()

    # ========================================================================
    # Asset Comparison Table
    # ========================================================================
    st.subheader("Asset Comparison")
    st.caption(
        "All assets ranked by health index. "
        "Select an asset in **Asset Deep Dive** for full analysis."
    )

    comparison_rows = []
    grade_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}

    for asset in assets:
        a_events = [e for e in events if e.asset_id == asset.id]
        a_exposures = [e for e in exposures if e.asset_id == asset.id]
        a_kpi = metrics.aggregate_kpis(a_exposures, a_events)
        a_failures = [e for e in a_events if e.event_type == "failure"]
        dt_hrs = sum((e.downtime_minutes or 0) for e in a_failures) / 60.0

        dt_split = manufacturing.compute_downtime_split(a_events)
        perf = manufacturing.compute_performance_rate(a_exposures)
        oee_result = manufacturing.compute_oee(a_kpi["availability"], perf.performance_rate)

        hi = business.compute_health_index(
            availability=a_kpi["availability"],
            mtbf_hours=a_kpi["mtbf_hours"],
            unplanned_ratio=dt_split.unplanned_ratio,
            oee=oee_result.oee,
        )
        grade_counts[hi.grade] = grade_counts.get(hi.grade, 0) + 1

        comparison_rows.append({
            "Asset": f"#{asset.id} — {asset.name}",
            "Grade": f"{_GRADE_ICON.get(hi.grade, '')} {hi.grade}",
            "Score": hi.score,
            "Failures": len(a_failures),
            "Downtime (h)": round(dt_hrs, 1),
            "MTBF (h)": round(a_kpi["mtbf_hours"], 1) if a_kpi["mtbf_hours"] < 1e6 else "N/A",
            "Availability": f"{a_kpi['availability'] * 100:.1f}%",
            "OEE": f"{oee_result.oee * 100:.1f}%",
        })

    # Sort by score ascending (worst first)
    comparison_rows.sort(key=lambda r: r["Score"])
    st.dataframe(comparison_rows, use_container_width=True, hide_index=True)

    st.divider()

    # ========================================================================
    # Grade Distribution
    # ========================================================================
    st.subheader("Grade Distribution")
    st.caption(
        "How many assets fall into each health grade. "
        "A (≥ 85) = Excellent, B (≥ 70) = Good, C (≥ 55) = Fair, "
        "D (≥ 40) = Poor, F (< 40) = Critical."
    )

    grade_cols = st.columns(5)
    for i, (grade, count) in enumerate([("A", grade_counts["A"]), ("B", grade_counts["B"]),
                                         ("C", grade_counts["C"]), ("D", grade_counts["D"]),
                                         ("F", grade_counts["F"])]):
        with grade_cols[i]:
            st.metric(
                f"{_GRADE_ICON.get(grade, '')} Grade {grade}", count,
                help={
                    "A": "Score ≥ 85 — Excellent condition. Minimal risk.",
                    "B": "Score ≥ 70 — Good condition. Monitor normally.",
                    "C": "Score ≥ 55 — Fair. Some degradation; plan maintenance.",
                    "D": "Score ≥ 40 — Poor. Significant risk; prioritize action.",
                    "F": "Score < 40 — Critical. Immediate attention required.",
                }[grade],
            )

    st.divider()

    # ========================================================================
    # Fleet Failure Mode Pareto
    # ========================================================================
    st.subheader("Failure Mode Pareto")
    st.caption("Which failure modes dominate across the fleet. Focus corrective action on the top items.")

    if details and failure_modes:
        ev_ids = {e.id for e in failure_events}
        mode_counts: dict[int, int] = {}
        for d in details:
            if d.event_id in ev_ids:
                mode_counts[d.failure_mode_id] = mode_counts.get(d.failure_mode_id, 0) + 1

        if mode_counts:
            name_map = {m.id: m.name for m in failure_modes}
            cat_map = {m.id: m.category for m in failure_modes}
            pareto_data = []
            for mode_id, count in sorted(mode_counts.items(), key=lambda x: x[1], reverse=True):
                pareto_data.append({
                    "Failure Mode": name_map.get(mode_id, f"Mode #{mode_id}"),
                    "Category": cat_map.get(mode_id, "N/A"),
                    "Count": count,
                })

            p_left, p_right = st.columns(2)
            with p_left:
                st.dataframe(pareto_data, use_container_width=True, hide_index=True)
            with p_right:
                df = pd.DataFrame(pareto_data)
                st.bar_chart(df.set_index("Failure Mode")["Count"])
        else:
            st.info("No failure mode data linked to events yet.")
    else:
        st.info("Add failure modes and event details in the Configuration pages to populate the Pareto chart.")

    st.divider()

    # ========================================================================
    # Bad Actor Ranking
    # ========================================================================
    st.subheader("Bad Actor Ranking")
    st.caption(
        "Worst-performing assets ranked by composite score "
        "(failures, downtime, availability). Higher score = worse performer."
    )

    ba_input = []
    for asset in assets:
        a_events = [e for e in events if e.asset_id == asset.id]
        a_exposures = [e for e in exposures if e.asset_id == asset.id]
        a_kpi = metrics.aggregate_kpis(a_exposures, a_events)
        a_failures = [e for e in a_events if e.event_type == "failure"]
        dt_hrs = sum((e.downtime_minutes or 0) for e in a_failures) / 60.0
        ba_input.append({
            "asset_id": asset.id,
            "asset_name": asset.name,
            "failure_count": len(a_failures),
            "total_downtime_hours": dt_hrs,
            "availability": a_kpi["availability"],
        })

    ranked = reliability_extended.rank_bad_actors(ba_input, top_n=10)
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
        st.info("No ranking data available.")

    st.divider()

    # ========================================================================
    # Fleet MTBF Trend
    # ========================================================================
    st.subheader("Fleet MTBF Trend")
    st.caption(
        "Time between consecutive failures across all fleet assets. "
        "An upward trend means reliability is improving."
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

            m1, m2, m3 = st.columns(3)
            m1.metric(
                "Min Interval", f"{min(trend_intervals):.1f} h",
                help="Shortest gap between consecutive fleet failures.",
            )
            m2.metric(
                "Max Interval", f"{max(trend_intervals):.1f} h",
                help="Longest gap between consecutive fleet failures.",
            )
            m3.metric(
                "Avg Interval", f"{sum(trend_intervals) / len(trend_intervals):.1f} h",
                help="Average gap between consecutive fleet failures.",
            )
    else:
        st.info("Log at least 2 failure events to see the MTBF trend.")

    st.divider()

    # ========================================================================
    # Spare Parts Demand Forecast
    # ========================================================================
    st.subheader("Spare Parts Demand Forecast")
    st.caption("Projected part consumption based on fleet failure rate.")

    total_exp = fleet_kpi["total_exposure_hours"]
    total_failures = fleet_kpi["failure_count"]

    if total_exp > 0 and total_failures > 0 and parts:
        horizon = st.slider("Forecast horizon (months)", 1, 24, 6,
                            help="How far ahead to forecast spare part demand.")
        fleet_rate = total_failures / total_exp

        # Build per-part failure-rate data from fleet rate
        part_number_map = {p.name: getattr(p, "part_number", "") or "" for p in parts}
        part_failure_data = [
            {
                "part_name": p.name,
                "failure_rate_per_hour": fleet_rate,  # each part assumed 1 usage per failure
            }
            for p in parts
        ]
        horizon_hours = horizon * 30 * 24  # approximate months → hours

        forecast = business.forecast_spare_demand(
            part_failure_data=part_failure_data,
            horizon_hours=horizon_hours,
        )

        f_rows = [
            {
                "Part": f.part_name,
                "Part Number": part_number_map.get(f.part_name, ""),
                "Expected Demand": f"{f.expected_failures:.1f}",
                "Safety Stock": f"{max(f.upper_bound - f.expected_failures, 0):.0f}",
                "Reorder Qty": f"{f.upper_bound:.0f}",
            }
            for f in forecast.forecasts
        ]
        st.dataframe(f_rows, use_container_width=True, hide_index=True)
        st.caption(
            f"Fleet failure rate: {fleet_rate * 1000:.2f} / 1,000 h | "
            f"Horizon: {horizon} months | "
            f"Expected failures: {forecast.total_expected_failures:.1f}"
        )
    else:
        st.info("Need exposure data, failure events, and parts to forecast demand. "
                "Add them in the Configuration pages or seed demo data from Operations.")

    st.divider()

    # ========================================================================
    # Failure Timeline
    # ========================================================================
    st.subheader("Failure Timeline")
    st.caption("Most recent failure events across the fleet.")

    if failure_events:
        recent = sorted(failure_events, key=lambda e: e.timestamp, reverse=True)[:20]
        asset_names = {a.id: a.name for a in assets}
        f_data = [
            {
                "Timestamp": e.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Asset": f"#{e.asset_id} — {asset_names.get(e.asset_id, 'Unknown')}",
                "Downtime (min)": e.downtime_minutes or 0,
                "Description": e.description or "—",
            }
            for e in recent
        ]
        st.dataframe(f_data, use_container_width=True, hide_index=True)
    else:
        st.info("No failure events recorded yet.")


main()
