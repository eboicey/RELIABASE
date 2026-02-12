"""Analytics-first Home — instant fleet situational awareness."""
import streamlit as st

st.set_page_config(page_title="RELIABASE", page_icon="📊", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import (  # noqa: E402
    AssetService, EventService, ExposureService,
    FailureModeService, EventDetailService, DemoService,
)
from reliabase.analytics import (  # noqa: E402
    metrics, reliability_extended, business, manufacturing,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_GRADE_ICON = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🟠", "F": "🔴"}


def _letter_grade(score: float) -> str:
    """Map a 0-100 score to a letter grade (mirrors business._grade)."""
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # --- Sidebar branding ---------------------------------------------------
    with st.sidebar:
        st.markdown("### RELIABASE")
        st.caption("Open-source reliability analytics\nfor maintenance teams.")
        st.divider()

    # --- Load all data ------------------------------------------------------
    with get_session() as session:
        assets = AssetService(session).list(limit=500)
        events = EventService(session).list(limit=500)
        exposures = ExposureService(session).list(limit=500)
        failure_modes = FailureModeService(session).list(limit=500)
        details = EventDetailService(session).list(limit=500)

    # --- Empty state / onboarding -------------------------------------------
    if not assets:
        st.title("Welcome to RELIABASE")
        st.markdown(
            "Your reliability analytics platform is ready. "
            "Seed demo data to explore, or start adding your own assets."
        )
        st.markdown(
            """
            **Getting Started**
            1. Click **Seed Demo Data** below to load sample equipment
            2. Visit **Fleet Overview** for fleet-wide analytics
            3. Dive into **Asset Deep Dive** for individual analysis
            4. Or add your own data via the Configuration pages
            """
        )
        if st.button("🌱 Seed Demo Data", type="primary"):
            with get_session() as session:
                DemoService(session).seed(reset=True)
            st.rerun()
        return

    # --- Compute fleet metrics -----------------------------------------------
    failure_events = [e for e in events if e.event_type == "failure"]
    fleet_kpi = metrics.aggregate_kpis(exposures, events)
    failure_count = fleet_kpi["failure_count"]

    # Per-asset health index
    asset_health: dict[int, dict] = {}
    ba_data: list[dict] = []

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
        asset_health[asset.id] = {
            "name": asset.name,
            "grade": hi.grade,
            "score": hi.score,
            "failures": len(a_failures),
            "downtime_hours": dt_hrs,
            "availability": a_kpi["availability"],
            "mtbf": a_kpi["mtbf_hours"],
        }
        ba_data.append({
            "asset_id": asset.id,
            "asset_name": asset.name,
            "failure_count": len(a_failures),
            "total_downtime_hours": dt_hrs,
            "availability": a_kpi["availability"],
        })

    # Fleet average health
    scores = [v["score"] for v in asset_health.values()]
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_grade = _letter_grade(avg_score)

    # ========================================================================
    # Fleet Health Banner
    # ========================================================================
    icon = _GRADE_ICON.get(avg_grade, "⚪")
    st.markdown(f"## {icon} Fleet Health: Grade {avg_grade} — {avg_score:.0f} / 100")
    st.caption(
        "Composite score based on availability, MTBF, downtime quality, "
        "wear-out margin, OEE, and repair trend across all assets."
    )

    # ========================================================================
    # Critical KPIs
    # ========================================================================
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Total Failures", failure_count,
        help="Count of all failure-type events across the fleet. "
             "A primary indicator of overall fleet reliability.",
    )
    c2.metric(
        "Exposure Hours", f"{fleet_kpi['total_exposure_hours']:,.0f}",
        help="Sum of all logged operating hours across every asset. "
             "More hours improve statistical confidence in reliability estimates.",
    )
    mtbf = fleet_kpi["mtbf_hours"]
    c3.metric(
        "Fleet MTBF", f"{mtbf:,.0f} h" if mtbf < 1e6 else "N/A",
        help="Mean Time Between Failures = total operating hours / failure count. "
             "Higher is better. A core reliability KPI.",
    )
    c4.metric(
        "Assets Tracked", len(assets),
        help="Total number of assets registered in the system.",
    )

    st.divider()

    # ========================================================================
    # Worst Performers + Dominant Failure Pattern
    # ========================================================================
    left, right = st.columns(2)

    with left:
        st.subheader("Worst Performers")
        ranked = reliability_extended.rank_bad_actors(ba_data, top_n=3)
        if ranked.entries:
            for i, entry in enumerate(ranked.entries):
                # Find grade by asset_id
                grade = "?"
                for aid, ah in asset_health.items():
                    if ah["name"] == entry.asset_name:
                        grade = ah["grade"]
                        break
                g_icon = _GRADE_ICON.get(grade, "⚪")
                st.markdown(
                    f"**{i + 1}. {entry.asset_name}** {g_icon} Grade {grade}  \n"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;"
                    f"{entry.failure_count} failures · "
                    f"{entry.total_downtime_hours:.1f}h downtime · "
                    f"{entry.availability * 100:.0f}% availability"
                )
        else:
            st.info("No failure data to rank.")

    with right:
        st.subheader("Dominant Failure Pattern")
        if details and failure_modes:
            ev_ids = {e.id for e in failure_events}
            mode_counts: dict[int, int] = {}
            for d in details:
                if d.event_id in ev_ids:
                    mode_counts[d.failure_mode_id] = mode_counts.get(d.failure_mode_id, 0) + 1
            if mode_counts:
                name_map = {m.id: m.name for m in failure_modes}
                cat_map = {m.id: m.category for m in failure_modes}
                top_id = max(mode_counts, key=mode_counts.get)  # type: ignore[arg-type]
                top_count = mode_counts[top_id]
                pct = top_count / sum(mode_counts.values()) * 100
                st.metric(
                    name_map.get(top_id, "Unknown"),
                    f"{top_count} occurrences ({pct:.0f}%)",
                    help="The single most common failure mode across the fleet. "
                         "Focus corrective action here for maximum impact.",
                )
                st.caption(f"Category: {cat_map.get(top_id, 'N/A')}")
            else:
                st.info("Link failure details to events for pattern analysis.")
        else:
            st.info("Add failure modes and event details to see patterns.")

    st.divider()

    # ========================================================================
    # Asset Health Map
    # ========================================================================
    st.subheader("Asset Health Map")
    st.caption(
        "Health grade for every asset. "
        "Visit **Fleet Overview** for the full comparison table, "
        "or **Asset Deep Dive** for individual analysis."
    )

    n_cols = min(len(assets), 5)
    cols = st.columns(n_cols)
    sorted_assets = sorted(asset_health.items(), key=lambda x: x[1]["score"])
    for i, (aid, ah) in enumerate(sorted_assets):
        with cols[i % n_cols]:
            g_icon = _GRADE_ICON.get(ah["grade"], "⚪")
            st.metric(
                f"{g_icon} {ah['name']}",
                f"Grade {ah['grade']}",
                f"{ah['score']:.0f}/100",
                help=(
                    f"Health index for {ah['name']}. "
                    f"Availability: {ah['availability'] * 100:.0f}% | "
                    f"MTBF: {ah['mtbf']:.0f}h | "
                    f"Failures: {ah['failures']} | "
                    f"Downtime: {ah['downtime_hours']:.1f}h"
                ),
            )

    st.divider()

    # ========================================================================
    # Recent Failures
    # ========================================================================
    st.subheader("Recent Failures")
    if failure_events:
        recent = sorted(failure_events, key=lambda e: e.timestamp, reverse=True)[:10]
        names = {a.id: a.name for a in assets}
        rows = [
            {
                "Timestamp": e.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Asset": names.get(e.asset_id, f"#{e.asset_id}"),
                "Downtime (min)": e.downtime_minutes or 0,
                "Description": e.description or "—",
            }
            for e in recent
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No failure events recorded yet.")


main()
