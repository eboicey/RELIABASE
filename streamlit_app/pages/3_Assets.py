"""Assets management page."""
import streamlit as st

st.set_page_config(page_title="Assets - RELIABASE", page_icon="🛠", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import AssetService  # noqa: E402
from reliabase.schemas import AssetCreate, AssetUpdate  # noqa: E402


def main():
    st.title("🛠 Asset Management")
    st.markdown("Track and manage your equipment and assets.")
    with st.expander("ℹ️ What are Assets?", expanded=False):
        st.markdown(
            "**Assets** are the physical equipment you want to track — pumps, compressors, "
            "motors, conveyors, etc. Each asset gets its own reliability profile including "
            "Weibull analysis, health index, and failure history. "
            "Assets are the foundation of all analytics in RELIABASE."
        )
    
    # Add Asset Form
    with st.expander("➕ Add New Asset", expanded=False):
        with st.form("add_asset_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                name = st.text_input("Name *", placeholder="Compressor A")
                asset_type = st.text_input("Type", placeholder="pump")
            
            with col2:
                serial = st.text_input("Serial", placeholder="SN-001")
                in_service = st.date_input("In Service Date", value=None)
            
            with col3:
                notes = st.text_area("Notes", placeholder="Critical duty", height=100)
            
            submitted = st.form_submit_button("Create Asset", type="primary")
            
            if submitted:
                if not name:
                    st.error("Name is required")
                else:
                    with get_session() as session:
                        svc = AssetService(session)
                        data = AssetCreate(
                            name=name,
                            type=asset_type or None,
                            serial=serial or None,
                            in_service_date=in_service if in_service else None,
                            notes=notes or None,
                        )
                        svc.create(data)
                        st.success(f"Asset '{name}' created successfully!")
                        st.rerun()
    
    st.divider()
    
    # Asset List
    st.subheader("Assets")
    
    with get_session() as session:
        svc = AssetService(session)
        assets = svc.list(limit=500)
    
    if not assets:
        st.info("No assets yet. Create one above or seed demo data from Operations.")
        return
    
    # Convert to display format
    asset_data = []
    for a in sorted(assets, key=lambda x: x.id):
        asset_data.append({
            "ID": a.id,
            "Name": a.name,
            "Type": a.type or "—",
            "Serial": a.serial or "—",
            "In Service": str(a.in_service_date) if a.in_service_date else "—",
            "Notes": a.notes or "",
        })
    
    st.dataframe(asset_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Edit/Delete section
    st.subheader("Edit or Delete Asset")
    
    asset_options = {f"#{a.id} - {a.name}": a.id for a in assets}
    selected = st.selectbox("Select Asset", options=list(asset_options.keys()))
    
    if selected:
        asset_id = asset_options[selected]
        
        with get_session() as session:
            svc = AssetService(session)
            asset = svc.get(asset_id)
        
        if asset:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                with st.form("edit_asset_form"):
                    edit_name = st.text_input("Name", value=asset.name)
                    edit_type = st.text_input("Type", value=asset.type or "")
                    edit_serial = st.text_input("Serial", value=asset.serial or "")
                    edit_in_service = st.date_input(
                        "In Service Date", 
                        value=asset.in_service_date if asset.in_service_date else None
                    )
                    edit_notes = st.text_area("Notes", value=asset.notes or "")
                    
                    if st.form_submit_button("Save Changes", type="primary"):
                        with get_session() as session:
                            svc = AssetService(session)
                            update_data = AssetUpdate(
                                name=edit_name,
                                type=edit_type or None,
                                serial=edit_serial or None,
                                in_service_date=edit_in_service if edit_in_service else None,
                                notes=edit_notes or None,
                            )
                            svc.update(asset_id, update_data)
                            st.success("Asset updated!")
                            st.rerun()
            
            with col2:
                st.markdown("### Danger Zone")
                if st.button("🗑️ Delete Asset", type="secondary", use_container_width=True):
                    with get_session() as session:
                        svc = AssetService(session)
                        svc.delete(asset_id)
                        st.success("Asset deleted!")
                        st.rerun()


main()
