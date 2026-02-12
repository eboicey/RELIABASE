"""Operations page - Demo seeding, exports, and admin tasks."""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Operations - RELIABASE", page_icon="🛰", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import (  # noqa: E402
    AssetService, EventService, ExposureService,
    FailureModeService, EventDetailService, PartService, DemoService,
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
    
    # Demo Dataset Section
    st.subheader("Demo Dataset")
    st.markdown("Seed sample data for testing and demonstration.")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🌱 Seed Demo Data", type="primary", use_container_width=True):
            with get_session() as session:
                svc = DemoService(session)
                result = svc.seed(reset=True)
                st.success(f"✅ Seeded {result['created']['assets']} assets, "
                          f"{result['created']['events']} events, "
                          f"{result['created']['exposures']} exposures!")
                st.rerun()
    
    with col2:
        if st.button("➕ Append Data", type="secondary", use_container_width=True, 
                    help="Add demo data without clearing existing"):
            with get_session() as session:
                svc = DemoService(session)
                result = svc.seed(reset=False)
                st.success(f"Added {result['created']['assets']} assets, "
                          f"{result['created']['events']} events!")
                st.rerun()
    
    # Show current totals
    with get_session() as session:
        svc = DemoService(session)
        totals = svc.get_totals()
    
    st.markdown("**Current Database Totals:**")
    cols = st.columns(5)
    for i, (key, val) in enumerate(totals.items()):
        with cols[i]:
            st.metric(key.replace("_", " ").title(), val)
    
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
