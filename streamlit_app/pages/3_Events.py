"""Events management page."""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Events - RELIABASE", page_icon="📅", layout="wide")

src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from sqlmodel import Session
from reliabase.config import init_db, get_engine
from reliabase.services import AssetService, EventService
from reliabase.schemas import EventCreate, EventUpdate

init_db()

EVENT_TYPES = ["failure", "maintenance", "inspection"]


def get_session():
    engine = get_engine()
    return Session(engine)


def main():
    st.title("📅 Events")
    st.markdown("Log failures, maintenance, and inspections.")
    
    # Load assets for dropdown
    with get_session() as session:
        asset_svc = AssetService(session)
        assets = asset_svc.list(limit=500)
    
    if not assets:
        st.warning("No assets found. Please create assets first.")
        return
    
    asset_options = {f"#{a.id} - {a.name}": a.id for a in assets}
    
    # Add Event Form
    with st.expander("➕ Log New Event", expanded=False):
        with st.form("add_event_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                selected_asset = st.selectbox("Asset *", options=list(asset_options.keys()), key="add_asset")
                timestamp = st.datetime_input("Timestamp *", value=datetime.now())
                event_type = st.selectbox("Event Type *", options=EVENT_TYPES, format_func=str.capitalize)
            
            with col2:
                downtime = st.number_input("Downtime (minutes)", min_value=0.0, step=5.0)
                description = st.text_area("Description", placeholder="Describe what happened...")
            
            submitted = st.form_submit_button("Create Event", type="primary")
            
            if submitted:
                with get_session() as session:
                    svc = EventService(session)
                    data = EventCreate(
                        asset_id=asset_options[selected_asset],
                        timestamp=timestamp,
                        event_type=event_type,
                        downtime_minutes=downtime,
                        description=description or None,
                    )
                    svc.create(data)
                    st.success("Event logged!")
                    st.rerun()
    
    st.divider()
    
    # Filter
    col1, col2 = st.columns([1, 3])
    with col1:
        filter_options = ["All Assets"] + list(asset_options.keys())
        filter_asset = st.selectbox("Filter by Asset", options=filter_options)
    
    # Load events
    with get_session() as session:
        svc = EventService(session)
        if filter_asset == "All Assets":
            events = svc.list(limit=500)
        else:
            events = svc.list(limit=500, asset_id=asset_options[filter_asset])
    
    st.subheader("Events")
    
    if not events:
        st.info("No events yet.")
        return
    
    # Build asset name lookup
    asset_names = {a.id: a.name for a in assets}
    
    # Convert to display format
    event_data = []
    for e in sorted(events, key=lambda x: x.timestamp, reverse=True):
        event_data.append({
            "ID": e.id,
            "Asset": f"#{e.asset_id} - {asset_names.get(e.asset_id, 'Unknown')}",
            "Timestamp": e.timestamp.strftime("%Y-%m-%d %H:%M"),
            "Type": e.event_type.capitalize(),
            "Downtime (min)": e.downtime_minutes or 0,
            "Description": e.description or "—",
        })
    
    st.dataframe(event_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Edit/Delete section
    st.subheader("Edit or Delete Event")
    
    event_options = {f"#{e.id} - {e.event_type} ({e.timestamp.strftime('%Y-%m-%d')})": e.id for e in events}
    selected = st.selectbox("Select Event", options=list(event_options.keys()))
    
    if selected:
        event_id = event_options[selected]
        
        with get_session() as session:
            svc = EventService(session)
            event = svc.get(event_id)
        
        if event:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                with st.form("edit_event_form"):
                    edit_asset = st.selectbox(
                        "Asset", 
                        options=list(asset_options.keys()),
                        index=list(asset_options.values()).index(event.asset_id) if event.asset_id in asset_options.values() else 0
                    )
                    edit_timestamp = st.datetime_input("Timestamp", value=event.timestamp)
                    edit_type = st.selectbox(
                        "Event Type", 
                        options=EVENT_TYPES, 
                        index=EVENT_TYPES.index(event.event_type) if event.event_type in EVENT_TYPES else 0,
                        format_func=str.capitalize
                    )
                    edit_downtime = st.number_input("Downtime (minutes)", value=event.downtime_minutes or 0.0, min_value=0.0, step=5.0)
                    edit_description = st.text_area("Description", value=event.description or "")
                    
                    if st.form_submit_button("Save Changes", type="primary"):
                        with get_session() as session:
                            svc = EventService(session)
                            update_data = EventUpdate(
                                timestamp=edit_timestamp,
                                event_type=edit_type,
                                downtime_minutes=edit_downtime,
                                description=edit_description or None,
                            )
                            svc.update(event_id, update_data)
                            st.success("Event updated!")
                            st.rerun()
            
            with col2:
                st.markdown("### Danger Zone")
                if st.button("🗑️ Delete Event", type="secondary", use_container_width=True):
                    with get_session() as session:
                        svc = EventService(session)
                        svc.delete(event_id)
                        st.success("Event deleted!")
                        st.rerun()


if __name__ == "__main__":
    main()
