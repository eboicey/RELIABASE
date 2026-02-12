"""Operations page - Demo seeding, exports, spare parts, and admin tasks."""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Operations - RELIABASE", page_icon="🛰", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import (  # noqa: E402
    AssetService, EventService, ExposureService,
    FailureModeService, EventDetailService, PartService, DemoService,
)
from reliabase.analytics import (  # noqa: E402
    metrics, reliability_extended, business, manufacturing,
)


def convert_to_csv(data, columns):
    """Convert list of objects to CSV string."""
    rows = []
    for item in data:
        row = {}
        for col in columns:
            val = getattr(item, col, None)
            row[col] = str(val) if val is not None else ""
        rows.append(row)
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def main():
    st.title("🛰 Operations")
    st.markdown("Database management, demo data, and exports.")
    with st.expander("ℹ️ About Operations", expanded=False):
        st.markdown(
            "**Operations** provides administrative tools — seed demo data for testing, "
            "export your data as CSV, view spare parts demand, and find CLI commands "
            "for advanced usage like PDF report generation and API mode."
        )
    
    # Demo Dataset Section
    st.subheader("Demo Dataset")
    st.markdown("Seed sample data for testing and demonstration. "
                "The demo dataset includes **10 assets** across 4 equipment types with "
                "realistic failure patterns (wear-out, random, infant mortality) and "
                "correlated failure modes, root causes, and part replacements.")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🌱 Seed Demo Data", type="primary", use_container_width=True,
                    help="Clear existing data and load a comprehensive demo dataset"):
            with get_session() as session:
                try:
                    svc = DemoService(session)
                    result = svc.seed(reset=True)
                    c = result['created']
                    st.success(
                        f"✅ Demo dataset loaded!\n\n"
                        f"**{c.get('assets', 0)}** assets, "
                        f"**{c.get('exposures', 0)}** exposures, "
                        f"**{c.get('events', 0)}** events, "
                        f"**{c.get('failure_details', 0)}** failure details, "
                        f"**{c.get('failure_modes', 0)}** failure modes, "
                        f"**{c.get('parts', 0)}** parts, "
                        f"**{c.get('installs', 0)}** part installs."
                    )
                except Exception as exc:
                    st.error(f"❌ Seeding failed: {exc}")
                st.rerun()
    
    with col2:
        if st.button("➕ Append Data", type="secondary", use_container_width=True, 
                    help="Add demo data without clearing existing"):
            with get_session() as session:
                try:
                    svc = DemoService(session)
                    result = svc.seed(reset=False)
                    c = result['created']
                    st.success(f"Added {c.get('assets', 0)} assets, "
                              f"{c.get('events', 0)} events!")
                except Exception as exc:
                    st.error(f"❌ Append failed: {exc}")
                st.rerun()
    
    with col3:
        if st.button("🗑️ Clear All Data", type="secondary", use_container_width=True,
                    help="Remove all data from the database"):
            with get_session() as session:
                try:
                    svc = DemoService(session)
                    deleted = svc.clear()
                    total = sum(deleted.values())
                    if total > 0:
                        st.success(
                            f"🗑️ Cleared {deleted.get('assets', 0)} assets, "
                            f"{deleted.get('events', 0)} events, "
                            f"{deleted.get('exposures', 0)} exposures, "
                            f"{deleted.get('failure_modes', 0)} failure modes, "
                            f"{deleted.get('parts', 0)} parts."
                        )
                    else:
                        st.info("Database is already empty.")
                except Exception as exc:
                    st.error(f"❌ Clear failed: {exc}")
                st.rerun()
    
    # Show current totals
    with get_session() as session:
        svc = DemoService(session)
        totals = svc.get_totals()
    
    st.markdown("**Current Database Totals:**")
    cols = st.columns(5)
    for i, (key, val) in enumerate(totals.items()):
        with cols[i]:
            st.metric(
                key.replace("_", " ").title(), val,
                help=f"Total number of {key.replace('_', ' ')} records in the database.",
            )
    
    st.divider()
    
    # Status Section
    st.subheader("System Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Database**")
        st.markdown("✅ SQLite connected")
        st.caption("File: `reliabase.sqlite`")
    
    with col2:
        st.markdown("**Streamlit App**")
        st.markdown("✅ Running")
        st.caption("All services operational")
    
    st.divider()
    
    # CSV Export Section
    st.subheader("CSV Export")
    st.markdown("Download current data tables as CSV files.")
    
    with get_session() as session:
        asset_svc = AssetService(session)
        event_svc = EventService(session)
        exposure_svc = ExposureService(session)
        mode_svc = FailureModeService(session)
        part_svc = PartService(session)
        
        assets = asset_svc.list(limit=1000)
        events = event_svc.list(limit=1000)
        exposures = exposure_svc.list(limit=1000)
        modes = mode_svc.list(limit=1000)
        parts = part_svc.list_parts(limit=1000)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if assets:
            csv = convert_to_csv(assets, ["id", "name", "type", "serial", "in_service_date", "notes"])
            st.download_button(
                "📥 Assets",
                csv,
                "assets.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.button("📥 Assets", disabled=True, use_container_width=True)
    
    with col2:
        if events:
            csv = convert_to_csv(events, ["id", "asset_id", "timestamp", "event_type", "downtime_minutes", "description"])
            st.download_button(
                "📥 Events",
                csv,
                "events.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.button("📥 Events", disabled=True, use_container_width=True)
    
    with col3:
        if exposures:
            csv = convert_to_csv(exposures, ["id", "asset_id", "start_time", "end_time", "hours", "cycles"])
            st.download_button(
                "📥 Exposures",
                csv,
                "exposures.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.button("📥 Exposures", disabled=True, use_container_width=True)
    
    with col4:
        if modes:
            csv = convert_to_csv(modes, ["id", "name", "category"])
            st.download_button(
                "📥 Failure Modes",
                csv,
                "failure_modes.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.button("📥 Failure Modes", disabled=True, use_container_width=True)
    
    with col5:
        if parts:
            csv = convert_to_csv(parts, ["id", "name", "part_number"])
            st.download_button(
                "📥 Parts",
                csv,
                "parts.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.button("📥 Parts", disabled=True, use_container_width=True)
    
    st.divider()
    
    # =====================================================================
    # Spare Parts Demand Forecast
    # =====================================================================
    st.subheader("Spare Parts Demand Forecast")
    st.caption("Projected part consumption over configurable horizon based on failure rates.")

    with get_session() as session:
        asset_svc = AssetService(session)
        event_svc = EventService(session)
        exposure_svc = ExposureService(session)
        part_svc = PartService(session)

        all_assets = asset_svc.list(limit=500)
        all_events = event_svc.list(limit=500)
        all_exposures = exposure_svc.list(limit=500)
        all_parts = part_svc.list_parts(limit=500)

    if all_assets and all_events:
        horizon_months = st.slider("Forecast horizon (months)", min_value=1, max_value=24, value=6)

        # Compute fleet-wide failure rate
        total_exp = sum(e.hours or 0 for e in all_exposures)
        total_failures = len([e for e in all_events if e.event_type == "failure"])
        fleet_rate = total_failures / total_exp if total_exp > 0 else 0.01

        # Build per-part failure-rate data from fleet rate
        part_number_map = {p.name: getattr(p, "part_number", "") or "" for p in all_parts}
        part_failure_data = [
            {
                "part_name": p.name,
                "failure_rate_per_hour": fleet_rate,
            }
            for p in all_parts
        ]
        horizon_hours = horizon_months * 30 * 24  # approximate months → hours

        if part_failure_data:
            forecast = business.forecast_spare_demand(
                part_failure_data=part_failure_data,
                horizon_hours=horizon_hours,
            )

            f_rows = []
            for f in forecast.forecasts:
                f_rows.append({
                    "Part": f.part_name,
                    "Part Number": part_number_map.get(f.part_name, ""),
                    "Expected Demand": f"{f.expected_failures:.1f}",
                    "Safety Stock": f"{max(f.upper_bound - f.expected_failures, 0):.0f}",
                    "Reorder Qty": f"{f.upper_bound:.0f}",
                })
            st.dataframe(f_rows, use_container_width=True, hide_index=True)
            st.caption(f"Fleet failure rate: {fleet_rate * 1000:.2f}/1,000h | Horizon: {horizon_months} months | Expected failures: {forecast.total_expected_failures:.1f}")
        else:
            st.info("Add parts in the Parts page to see spare demand forecast.")
    else:
        st.info("Seed demo data to compute spare parts demand.")

    st.divider()

    # =====================================================================
    # Fleet Bad Actors (Quick View)
    # =====================================================================
    st.subheader("Fleet Bad Actors")
    st.caption("Top underperforming assets at a glance.")

    if all_assets and all_events:
        ba_data = []
        for asset in all_assets:
            a_events = [e for e in all_events if e.asset_id == asset.id]
            a_exposures = [e for e in all_exposures if e.asset_id == asset.id]
            a_kpi = metrics.aggregate_kpis(a_exposures, a_events)
            a_failures = [e for e in a_events if e.event_type == "failure"]
            total_dt_hrs = sum((e.downtime_minutes or 0) for e in a_failures) / 60.0
            ba_data.append({
                "asset_id": asset.id,
                "asset_name": asset.name,
                "failure_count": len(a_failures),
                "total_downtime_hours": total_dt_hrs,
                "availability": a_kpi["availability"],
            })

        ranked = reliability_extended.rank_bad_actors(ba_data, top_n=5)
        if ranked.entries:
            ba_rows = []
            for i, entry in enumerate(ranked.entries):
                ba_rows.append({
                    "Rank": i + 1,
                    "Asset": entry.asset_name,
                    "Failures": entry.failure_count,
                    "Downtime (h)": f"{entry.total_downtime_hours:.1f}",
                    "Availability": f"{entry.availability * 100:.1f}%",
                })
            st.dataframe(ba_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No ranking data available.")
    else:
        st.info("Seed demo data to see bad actors.")

    st.divider()

    # CLI Commands Reference
    st.subheader("CLI Commands")
    st.markdown("Additional commands available from the terminal.")
    
    with st.expander("📊 Generate Reliability Report"):
        st.code("python -m reliabase.make_report --asset-id 1 --output-dir ./examples", language="bash")
        st.caption("Creates PDF report with Weibull curves, Pareto charts, and timeline visualization.")
    
    with st.expander("🌱 Seed Demo Data (CLI)"):
        st.code("python -m reliabase.seed_demo", language="bash")
        st.caption("Alternative to the UI button above.")
    
    with st.expander("🚀 Start FastAPI Backend"):
        st.code("uvicorn reliabase.api.main:app --host 127.0.0.1 --port 8000 --reload", language="bash")
        st.caption("For API access when scaling beyond Streamlit.")
    
    st.divider()
    
    # Scaling Notes
    st.subheader("Scaling Beyond Streamlit")
    st.markdown("""
    When you're ready to scale RELIABASE:
    
    1. **API Mode**: The FastAPI backend is still available at `reliabase.api.main`
    2. **Services Layer**: Business logic is in `reliabase.services` - reusable by any frontend
    3. **Database**: SQLite can be swapped for PostgreSQL via `RELIABASE_DATABASE_URL`
    4. **Deployment**: 
       - Streamlit Cloud for quick demos
       - Docker + PostgreSQL for production
       - Separate API + React frontend for enterprise
    
    The architecture is designed for this evolution!
    """)


main()
