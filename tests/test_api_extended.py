from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlmodel import Session, SQLModel


def _make_asset(client) -> int:
    resp = client.post("/assets/", json={"name": "Temp Asset"})
    assert resp.status_code == 201
    return resp.json()["id"]


def _make_failure_mode(client) -> int:
    resp = client.post("/failure-modes/", json={"name": "Leak", "category": "mech"})
    assert resp.status_code == 201
    return resp.json()["id"]


def _make_event(client, asset_id: int, event_type: str = "failure") -> int:
    ts = datetime.now(timezone.utc).isoformat()
    resp = client.post(
        "/events/",
        json={"asset_id": asset_id, "timestamp": ts, "event_type": event_type, "downtime_minutes": 5},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _make_exposure(client, asset_id: int, start: datetime, hours: float = 10.0) -> int:
    end = start + timedelta(hours=hours)
    resp = client.post(
        "/exposures/",
        json={
            "asset_id": asset_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "hours": hours,
            "cycles": 1.0,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _make_part(client) -> int:
    resp = client.post("/parts/", json={"name": "Demo Part", "part_number": "P-1"})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_failure_mode_crud(client):
    fm_id = _make_failure_mode(client)
    get_resp = client.get(f"/failure-modes/{fm_id}")
    assert get_resp.status_code == 200
    patch = client.patch(f"/failure-modes/{fm_id}", json={"category": "updated"})
    assert patch.status_code == 200
    assert patch.json()["category"] == "updated"


def test_event_detail_flow(client):
    asset_id = _make_asset(client)
    fm_id = _make_failure_mode(client)
    event_id = _make_event(client, asset_id)
    create = client.post(
        "/event-details/",
        json={"event_id": event_id, "failure_mode_id": fm_id, "root_cause": "cause"},
    )
    assert create.status_code == 201
    detail_id = create.json()["id"]
    patch = client.patch(f"/event-details/{detail_id}", json={"corrective_action": "fix"})
    assert patch.status_code == 200
    delete = client.delete(f"/event-details/{detail_id}")
    assert delete.status_code == 204


def test_exposure_patch_recomputes_hours(client):
    asset_id = _make_asset(client)
    start = datetime.now(timezone.utc)
    log_id = _make_exposure(client, asset_id, start, hours=2)
    new_end = (start + timedelta(hours=5)).isoformat()
    patch = client.patch(f"/exposures/{log_id}", json={"end_time": new_end})
    assert patch.status_code == 200
    assert abs(patch.json()["hours"] - 5.0) < 1e-6


def test_exposure_filter_by_asset(client):
    a1 = _make_asset(client)
    a2 = _make_asset(client)
    base = datetime.now(timezone.utc)
    _make_exposure(client, a1, base, hours=1)
    _make_exposure(client, a2, base + timedelta(hours=2), hours=1)
    filtered = client.get(f"/exposures/?asset_id={a1}")
    assert filtered.status_code == 200
    assert all(item["asset_id"] == a1 for item in filtered.json())


def test_event_type_normalization(client):
    asset_id = _make_asset(client)
    ts = datetime.now(timezone.utc).isoformat()
    resp = client.post(
        "/events/",
        json={"asset_id": asset_id, "timestamp": ts, "event_type": "FAILURE", "downtime_minutes": 1},
    )
    assert resp.status_code == 201
    assert resp.json()["event_type"] == "failure"


def test_part_install_update(client):
    asset_id = _make_asset(client)
    part_id = _make_part(client)
    now = datetime.now(timezone.utc)
    create = client.post(
        f"/parts/{part_id}/installs",
        json={"asset_id": asset_id, "install_time": now.isoformat()},
    )
    assert create.status_code == 201
    inst_id = create.json()["id"]
    patch = client.patch(
        f"/parts/installs/{inst_id}",
        json={"remove_time": (now + timedelta(hours=1)).isoformat()},
    )
    assert patch.status_code == 200
    assert patch.json()["remove_time"] is not None


def test_part_install_delete(client):
    asset_id = _make_asset(client)
    part_id = _make_part(client)
    now = datetime.now(timezone.utc)
    create = client.post(
        f"/parts/{part_id}/installs",
        json={"asset_id": asset_id, "install_time": now.isoformat()},
    )
    inst_id = create.json()["id"]
    delete = client.delete(f"/parts/installs/{inst_id}")
    assert delete.status_code == 204


def test_asset_pagination(client):
    for i in range(5):
        client.post("/assets/", json={"name": f"A-{i}"})
    resp = client.get("/assets/?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_asset_not_found(client):
    resp = client.get("/assets/99999")
    assert resp.status_code == 404


def test_event_delete(client):
    asset_id = _make_asset(client)
    event_id = _make_event(client, asset_id)
    delete = client.delete(f"/events/{event_id}")
    assert delete.status_code == 204


def test_overlapping_exposure_update_rejected(client):
    asset_id = _make_asset(client)
    base = datetime.now(timezone.utc)
    log_id = _make_exposure(client, asset_id, base, hours=4)
    _make_exposure(client, asset_id, base + timedelta(hours=4), hours=4)
    conflict_end = (base + timedelta(hours=5)).isoformat()
    patch = client.patch(f"/exposures/{log_id}", json={"end_time": conflict_end})
    assert patch.status_code == 400


def test_events_filtered_by_asset(client):
    a1 = _make_asset(client)
    a2 = _make_asset(client)
    _make_event(client, a1)
    _make_event(client, a2)
    filtered = client.get(f"/events/?asset_id={a1}")
    assert filtered.status_code == 200
    assert all(evt["asset_id"] == a1 for evt in filtered.json())


def test_event_invalid_patch_rejected(client):
    asset_id = _make_asset(client)
    event_id = _make_event(client, asset_id)
    patch = client.patch(f"/events/{event_id}", json={"event_type": "bad"})
    assert patch.status_code == 400


def test_failure_mode_delete(client):
    fm_id = _make_failure_mode(client)
    delete = client.delete(f"/failure-modes/{fm_id}")
    assert delete.status_code == 204


def test_csv_import_assets(session: Session, tmp_path):
    # seed one asset and export
    session.exec(text("delete from asset"))
    session.commit()
    session.exec(text("insert into asset (name) values ('csv-asset')"))
    session.commit()
    from reliabase.io import csv_io
    from reliabase.models import Asset

    csv_path = tmp_path / "assets.csv"
    csv_io.export_table(session, Asset, csv_path)
    # clear and import back
    session.exec(text("delete from asset"))
    session.commit()
    count = csv_io.import_table(session, Asset, csv_path)
    assert count == 1
    assert session.exec(text("select count(*) from asset")).one() == (1,)


def test_seed_demo_repeatable(tmp_path):
    from reliabase.seed_demo import seed_demo_dataset
    from reliabase.config import get_engine
    from reliabase.models import Asset
    engine = get_engine(f"sqlite:///{tmp_path/'demo.sqlite'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_demo_dataset(session)
        assets = session.exec(text("select count(*) from asset")).one()[0]
        assert assets >= 2
