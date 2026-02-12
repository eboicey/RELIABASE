"""Failure Modes management page."""
import streamlit as st

st.set_page_config(page_title="Failure Modes - RELIABASE", page_icon="⚠️", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import FailureModeService  # noqa: E402
from reliabase.schemas import FailureModeCreate, FailureModeUpdate  # noqa: E402


def main():
    st.title("⚠️ Failure Modes")
    st.markdown("Define failure modes to categorize and analyze patterns.")
    
    # Add Failure Mode Form
    with st.expander("➕ Add New Failure Mode", expanded=False):
        with st.form("add_mode_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                name = st.text_input("Name *", placeholder="Seal leak")
            
            with col2:
                category = st.text_input("Category", placeholder="Mechanical")
            
            with col3:
                st.markdown("&nbsp;")  # Spacer
                submitted = st.form_submit_button("Create", type="primary")
            
            if submitted:
                if not name:
                    st.error("Name is required")
                else:
                    with get_session() as session:
                        svc = FailureModeService(session)
                        data = FailureModeCreate(
                            name=name,
                            category=category or None,
                        )
                        svc.create(data)
                        st.success(f"Failure mode '{name}' created!")
                        st.rerun()
    
    st.divider()
    
    # Failure Mode List
    st.subheader("Failure Modes")
    
    with get_session() as session:
        svc = FailureModeService(session)
        modes = svc.list(limit=500)
    
    if not modes:
        st.info("No failure modes yet. Create one above or seed demo data from Operations.")
        return
    
    # Convert to display format
    mode_data = []
    for m in modes:
        mode_data.append({
            "ID": m.id,
            "Name": m.name,
            "Category": m.category or "—",
        })
    
    st.dataframe(mode_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Edit/Delete section
    st.subheader("Edit or Delete Failure Mode")
    
    mode_options = {f"#{m.id} - {m.name}": m.id for m in modes}
    selected = st.selectbox("Select Failure Mode", options=list(mode_options.keys()))
    
    if selected:
        mode_id = mode_options[selected]
        
        with get_session() as session:
            svc = FailureModeService(session)
            mode = svc.get(mode_id)
        
        if mode:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                with st.form("edit_mode_form"):
                    edit_name = st.text_input("Name", value=mode.name)
                    edit_category = st.text_input("Category", value=mode.category or "")
                    
                    if st.form_submit_button("Save Changes", type="primary"):
                        with get_session() as session:
                            svc = FailureModeService(session)
                            update_data = FailureModeUpdate(
                                name=edit_name,
                                category=edit_category or None,
                            )
                            svc.update(mode_id, update_data)
                            st.success("Failure mode updated!")
                            st.rerun()
            
            with col2:
                st.markdown("### Danger Zone")
                if st.button("🗑️ Delete Mode", type="secondary", use_container_width=True):
                    with get_session() as session:
                        svc = FailureModeService(session)
                        svc.delete(mode_id)
                        st.success("Failure mode deleted!")
                        st.rerun()


main()
