"""Exposures management page."""
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Exposures - RELIABASE", page_icon="⏳", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import AssetService, ExposureService  # noqa: E402
from reliabase.schemas import ExposureLogCreate, ExposureLogUpdate  # noqa: E402


def main():
    st.title("⏳ Exposure Logs")
    st.markdown("Track operating hours and cycles for your assets.")
    
    # Load assets for dropdown
    with get_session() as session:
        asset_svc = AssetService(session)
        assets = asset_svc.list(limit=500)
    
    if not assets:
        st.warning("No assets found. Please create assets first.")
        return
    
    asset_options = {f"#{a.id} - {a.name}": a.id for a in assets}
    
    # Add Exposure Form
    with st.expander("➕ Log New Exposure", expanded=False):
        with st.form("add_exposure_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                selected_asset = st.selectbox("Asset *", options=list(asset_options.keys()), key="add_asset")
                start_time = st.datetime_input("Start Time *", value=datetime.now())
                hours = st.number_input("Hours (optional)", min_value=0.0, step=0.1, 
                                       help="Leave at 0 to auto-calculate from duration")
            
            with col2:
                st.markdown("&nbsp;")  # Spacer
                end_time = st.datetime_input("End Time *", value=datetime.now())
                cycles = st.number_input("Cycles (optional)", min_value=0.0, step=0.1)
            
            submitted = st.form_submit_button("Create Exposure", type="primary")
            
            if submitted:
                if start_time >= end_time:
                    st.error("End time must be after start time")
                else:
                    with get_session() as session:
                        svc = ExposureService(session)
                        data = ExposureLogCreate(
                            asset_id=asset_options[selected_asset],
                            start_time=start_time,
                            end_time=end_time,
                            hours=hours or 0.0,
                            cycles=cycles or 0.0,
                        )
                        svc.create(data)
                        st.success("Exposure logged!")
                        st.rerun()
    
    st.divider()
    
    # Filter
    col1, col2 = st.columns([1, 3])
    with col1:
        filter_options = ["All Assets"] + list(asset_options.keys())
        filter_asset = st.selectbox("Filter by Asset", options=filter_options)
    
    # Load exposures
    with get_session() as session:
        svc = ExposureService(session)
        if filter_asset == "All Assets":
            exposures = svc.list(limit=500)
        else:
            exposures = svc.list(limit=500, asset_id=asset_options[filter_asset])
    
    st.subheader("Exposure Logs")
    
    if not exposures:
        st.info("No exposure logs yet.")
        return
    
    # Build asset name lookup
    asset_names = {a.id: a.name for a in assets}
    
    # Convert to display format
    exposure_data = []
    for e in sorted(exposures, key=lambda x: x.start_time, reverse=True):
        exposure_data.append({
            "ID": e.id,
            "Asset": f"#{e.asset_id} - {asset_names.get(e.asset_id, 'Unknown')}",
            "Start": e.start_time.strftime("%Y-%m-%d %H:%M"),
            "End": e.end_time.strftime("%Y-%m-%d %H:%M"),
            "Hours": f"{e.hours:.2f}",
            "Cycles": e.cycles or 0,
        })
    
    st.dataframe(exposure_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Edit/Delete section
    st.subheader("Edit or Delete Exposure")
    
    exposure_options = {f"#{e.id} (Asset #{e.asset_id})": e.id for e in exposures}
    selected = st.selectbox("Select Exposure", options=list(exposure_options.keys()))
    
    if selected:
        exposure_id = exposure_options[selected]
        
        with get_session() as session:
            svc = ExposureService(session)
            exposure = svc.get(exposure_id)
        
        if exposure:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                with st.form("edit_exposure_form"):
                    edit_asset = st.selectbox(
                        "Asset", 
                        options=list(asset_options.keys()),
                        index=list(asset_options.values()).index(exposure.asset_id) if exposure.asset_id in asset_options.values() else 0
                    )
                    edit_start = st.datetime_input("Start Time", value=exposure.start_time)
                    edit_end = st.datetime_input("End Time", value=exposure.end_time)
                    edit_hours = st.number_input("Hours", value=exposure.hours, min_value=0.0, step=0.1)
                    edit_cycles = st.number_input("Cycles", value=exposure.cycles or 0.0, min_value=0.0, step=0.1)
                    
                    if st.form_submit_button("Save Changes", type="primary"):
                        with get_session() as session:
                            svc = ExposureService(session)
                            update_data = ExposureLogUpdate(
                                start_time=edit_start,
                                end_time=edit_end,
                                hours=edit_hours,
                                cycles=edit_cycles,
                            )
                            svc.update(exposure_id, update_data)
                            st.success("Exposure updated!")
                            st.rerun()
            
            with col2:
                st.markdown("### Danger Zone")
                if st.button("🗑️ Delete Exposure", type="secondary", use_container_width=True):
                    with get_session() as session:
                        svc = ExposureService(session)
                        svc.delete(exposure_id)
                        st.success("Exposure deleted!")
                        st.rerun()


main()
