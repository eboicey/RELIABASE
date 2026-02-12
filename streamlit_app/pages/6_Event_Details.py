"""Event Details management page."""
import streamlit as st

st.set_page_config(page_title="Event Details - RELIABASE", page_icon="🧩", layout="wide")

from _common import get_session  # noqa: E402

from reliabase.services import AssetService, EventService, FailureModeService, EventDetailService  # noqa: E402
from reliabase.schemas import EventFailureDetailCreate, EventFailureDetailUpdate  # noqa: E402


def main():
    st.title("🧩 Event Details")
    st.markdown("Link events to failure modes with root cause analysis.")
    with st.expander("ℹ️ What are Event Details?", expanded=False):
        st.markdown(
            "**Event Details** link each event to a specific failure mode, enabling Pareto analysis, "
            "RPN (Risk Priority Number) calculations, and root cause tracking. "
            "Adding root cause and corrective action data improves failure pattern recognition "
            "and supports FMEA (Failure Mode and Effects Analysis)."
        )
    
    # Load data for dropdowns
    with get_session() as session:
        asset_svc = AssetService(session)
        event_svc = EventService(session)
        mode_svc = FailureModeService(session)
        
        assets = asset_svc.list(limit=500)
        events = event_svc.list(limit=500)
        failure_modes = mode_svc.list(limit=500)
    
    if not events:
        st.warning("No events found. Please create events first.")
        return
    
    if not failure_modes:
        st.warning("No failure modes found. Please create failure modes first.")
        return
    
    # Build lookups
    asset_names = {a.id: a.name for a in assets}
    mode_names = {m.id: m.name for m in failure_modes}
    
    def format_event(e):
        asset_name = asset_names.get(e.asset_id, f"Asset {e.asset_id}")
        return f"#{e.id} - {e.event_type} on {asset_name} ({e.timestamp.strftime('%Y-%m-%d')})"
    
    event_options = {format_event(e): e.id for e in events}
    mode_options = {f"#{m.id} - {m.name}": m.id for m in failure_modes}
    
    # Add Detail Form
    with st.expander("➕ Add Event Detail", expanded=False):
        with st.form("add_detail_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                selected_event = st.selectbox("Event *", options=list(event_options.keys()))
                selected_mode = st.selectbox("Failure Mode *", options=list(mode_options.keys()))
                root_cause = st.text_input("Root Cause", placeholder="Fatigue, wear, contamination...")
            
            with col2:
                corrective_action = st.text_input("Corrective Action", placeholder="Replace seal, rebalance...")
                part_replaced = st.text_input("Part Replaced", placeholder="Seal, bearing...")
            
            submitted = st.form_submit_button("Create Detail", type="primary")
            
            if submitted:
                with get_session() as session:
                    svc = EventDetailService(session)
                    data = EventFailureDetailCreate(
                        event_id=event_options[selected_event],
                        failure_mode_id=mode_options[selected_mode],
                        root_cause=root_cause or None,
                        corrective_action=corrective_action or None,
                        part_replaced=part_replaced or None,
                    )
                    svc.create(data)
                    st.success("Detail added!")
                    st.rerun()
    
    st.divider()
    
    # Filter
    col1, col2 = st.columns([1, 3])
    with col1:
        filter_options = ["All Events"] + list(event_options.keys())
        filter_event = st.selectbox("Filter by Event", options=filter_options)
    
    # Load details
    with get_session() as session:
        svc = EventDetailService(session)
        if filter_event == "All Events":
            details = svc.list(limit=500)
        else:
            details = svc.list(limit=500, event_id=event_options[filter_event])
    
    st.subheader("Event Failure Details")
    
    if not details:
        st.info("No event details yet. Add failure details above to populate Pareto charts in Analytics.")
        return
    
    # Convert to display format
    detail_data = []
    for d in details:
        detail_data.append({
            "ID": d.id,
            "Event ID": f"#{d.event_id}",
            "Failure Mode": mode_names.get(d.failure_mode_id, f"#{d.failure_mode_id}"),
            "Root Cause": d.root_cause or "—",
            "Corrective Action": d.corrective_action or "—",
            "Part Replaced": d.part_replaced or "—",
        })
    
    st.dataframe(detail_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Edit/Delete section
    st.subheader("Edit or Delete Detail")
    
    detail_options = {f"#{d.id} (Event #{d.event_id})": d.id for d in details}
    selected = st.selectbox("Select Detail", options=list(detail_options.keys()))
    
    if selected:
        detail_id = detail_options[selected]
        
        with get_session() as session:
            svc = EventDetailService(session)
            detail = svc.get(detail_id)
        
        if detail:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                with st.form("edit_detail_form"):
                    # Find current indices
                    event_idx = list(event_options.values()).index(detail.event_id) if detail.event_id in event_options.values() else 0
                    mode_idx = list(mode_options.values()).index(detail.failure_mode_id) if detail.failure_mode_id in mode_options.values() else 0
                    
                    edit_event = st.selectbox("Event", options=list(event_options.keys()), index=event_idx)
                    edit_mode = st.selectbox("Failure Mode", options=list(mode_options.keys()), index=mode_idx)
                    edit_root_cause = st.text_input("Root Cause", value=detail.root_cause or "")
                    edit_action = st.text_input("Corrective Action", value=detail.corrective_action or "")
                    edit_part = st.text_input("Part Replaced", value=detail.part_replaced or "")
                    
                    if st.form_submit_button("Save Changes", type="primary"):
                        with get_session() as session:
                            svc = EventDetailService(session)
                            update_data = EventFailureDetailUpdate(
                                root_cause=edit_root_cause or None,
                                corrective_action=edit_action or None,
                                part_replaced=edit_part or None,
                            )
                            svc.update(detail_id, update_data)
                            st.success("Detail updated!")
                            st.rerun()
            
            with col2:
                st.markdown("### Danger Zone")
                if st.button("🗑️ Delete Detail", type="secondary", use_container_width=True):
                    with get_session() as session:
                        svc = EventDetailService(session)
                        svc.delete(detail_id)
                        st.success("Detail deleted!")
                        st.rerun()


main()
