"""Parts management page."""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Parts - RELIABASE", page_icon="📦", layout="wide")

src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from sqlmodel import Session
from reliabase.config import init_db, get_engine
from reliabase.services import AssetService, PartService
from reliabase.schemas import PartCreate, PartUpdate, PartInstallCreate, PartInstallUpdate

init_db()


def get_session():
    engine = get_engine()
    return Session(engine)


def main():
    st.title("📦 Parts & Installations")
    st.markdown("Track parts and their installation history on assets.")
    
    # Tabs for Parts vs Installs
    tab1, tab2 = st.tabs(["Parts Catalog", "Part Installations"])
    
    with tab1:
        render_parts_tab()
    
    with tab2:
        render_installs_tab()


def render_parts_tab():
    """Render the parts catalog tab."""
    
    # Add Part Form
    with st.expander("➕ Add New Part", expanded=False):
        with st.form("add_part_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                name = st.text_input("Name *", placeholder="Seal")
            
            with col2:
                part_number = st.text_input("Part Number", placeholder="P-123")
            
            with col3:
                st.markdown("&nbsp;")
                submitted = st.form_submit_button("Create", type="primary")
            
            if submitted:
                if not name:
                    st.error("Name is required")
                else:
                    with get_session() as session:
                        svc = PartService(session)
                        data = PartCreate(name=name, part_number=part_number or None)
                        svc.create_part(data)
                        st.success(f"Part '{name}' created!")
                        st.rerun()
    
    st.divider()
    
    # Part List
    st.subheader("Parts Catalog")
    
    with get_session() as session:
        svc = PartService(session)
        parts = svc.list_parts(limit=500)
    
    if not parts:
        st.info("No parts yet. Create one above or seed demo data from Operations.")
        return
    
    part_data = []
    for p in parts:
        part_data.append({
            "ID": p.id,
            "Name": p.name,
            "Part Number": p.part_number or "—",
        })
    
    st.dataframe(part_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Edit/Delete section
    st.subheader("Edit or Delete Part")
    
    part_options = {f"#{p.id} - {p.name}": p.id for p in parts}
    selected = st.selectbox("Select Part", options=list(part_options.keys()), key="edit_part_select")
    
    if selected:
        part_id = part_options[selected]
        
        with get_session() as session:
            svc = PartService(session)
            part = svc.get_part(part_id)
        
        if part:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                with st.form("edit_part_form"):
                    edit_name = st.text_input("Name", value=part.name)
                    edit_number = st.text_input("Part Number", value=part.part_number or "")
                    
                    if st.form_submit_button("Save Changes", type="primary"):
                        with get_session() as session:
                            svc = PartService(session)
                            update_data = PartUpdate(
                                name=edit_name,
                                part_number=edit_number or None,
                            )
                            svc.update_part(part_id, update_data)
                            st.success("Part updated!")
                            st.rerun()
            
            with col2:
                st.markdown("### Danger Zone")
                if st.button("🗑️ Delete Part", type="secondary", use_container_width=True):
                    with get_session() as session:
                        svc = PartService(session)
                        svc.delete_part(part_id)
                        st.success("Part deleted!")
                        st.rerun()


def render_installs_tab():
    """Render the part installations tab."""
    
    # Load data
    with get_session() as session:
        asset_svc = AssetService(session)
        part_svc = PartService(session)
        assets = asset_svc.list(limit=500)
        parts = part_svc.list_parts(limit=500)
    
    if not parts:
        st.warning("No parts found. Create parts first.")
        return
    
    if not assets:
        st.warning("No assets found. Create assets first.")
        return
    
    part_options = {f"#{p.id} - {p.name}": p.id for p in parts}
    asset_options = {f"#{a.id} - {a.name}": a.id for a in assets}
    part_names = {p.id: p.name for p in parts}
    asset_names = {a.id: a.name for a in assets}
    
    # Add Install Form
    with st.expander("➕ Add Part Installation", expanded=False):
        with st.form("add_install_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                selected_part = st.selectbox("Part *", options=list(part_options.keys()))
                selected_asset = st.selectbox("Asset *", options=list(asset_options.keys()))
            
            with col2:
                install_time = st.datetime_input("Install Time *", value=datetime.now())
                remove_time = st.datetime_input("Remove Time (optional)", value=None)
            
            submitted = st.form_submit_button("Create Installation", type="primary")
            
            if submitted:
                with get_session() as session:
                    svc = PartService(session)
                    data = PartInstallCreate(
                        asset_id=asset_options[selected_asset],
                        install_time=install_time,
                        remove_time=remove_time if remove_time else None,
                    )
                    svc.create_install(part_options[selected_part], data)
                    st.success("Installation recorded!")
                    st.rerun()
    
    st.divider()
    
    # Filter
    col1, col2 = st.columns([1, 3])
    with col1:
        filter_options = ["All Parts"] + list(part_options.keys())
        filter_part = st.selectbox("Filter by Part", options=filter_options)
    
    # Load installs
    with get_session() as session:
        svc = PartService(session)
        if filter_part == "All Parts":
            installs = svc.list_installs(limit=500)
        else:
            installs = svc.list_installs(limit=500, part_id=part_options[filter_part])
    
    st.subheader("Part Installations")
    
    if not installs:
        st.info("No installations recorded yet.")
        return
    
    install_data = []
    for i in installs:
        install_data.append({
            "ID": i.id,
            "Part": f"#{i.part_id} - {part_names.get(i.part_id, 'Unknown')}",
            "Asset": f"#{i.asset_id} - {asset_names.get(i.asset_id, 'Unknown')}",
            "Installed": i.install_time.strftime("%Y-%m-%d %H:%M"),
            "Removed": i.remove_time.strftime("%Y-%m-%d %H:%M") if i.remove_time else "Still installed",
        })
    
    st.dataframe(install_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Edit/Delete section
    st.subheader("Edit or Delete Installation")
    
    install_options = {f"#{i.id} - {part_names.get(i.part_id, 'Part')} on {asset_names.get(i.asset_id, 'Asset')}": i.id for i in installs}
    selected = st.selectbox("Select Installation", options=list(install_options.keys()))
    
    if selected:
        install_id = install_options[selected]
        
        with get_session() as session:
            svc = PartService(session)
            install = svc.get_install(install_id)
        
        if install:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                with st.form("edit_install_form"):
                    edit_install_time = st.datetime_input("Install Time", value=install.install_time)
                    edit_remove_time = st.datetime_input("Remove Time", value=install.remove_time)
                    
                    if st.form_submit_button("Save Changes", type="primary"):
                        with get_session() as session:
                            svc = PartService(session)
                            update_data = PartInstallUpdate(
                                install_time=edit_install_time,
                                remove_time=edit_remove_time if edit_remove_time else None,
                            )
                            svc.update_install(install_id, update_data)
                            st.success("Installation updated!")
                            st.rerun()
            
            with col2:
                st.markdown("### Danger Zone")
                if st.button("🗑️ Delete Install", type="secondary", use_container_width=True):
                    with get_session() as session:
                        svc = PartService(session)
                        svc.delete_install(install_id)
                        st.success("Installation deleted!")
                        st.rerun()


if __name__ == "__main__":
    main()
