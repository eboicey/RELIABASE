from datetime import datetime, timedelta

from reliabase.models import Asset, ExposureLog, Event


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_asset_crud(client):
    create_resp = client.post("/assets/", json={"name": "Unit 1", "type": "pump"})
    assert create_resp.status_code == 201
    asset_id = create_resp.json()["id"]

    list_resp = client.get("/assets/")
    assert list_resp.status_code == 200
    assert any(a["id"] == asset_id for a in list_resp.json())

    patch_resp = client.patch(f"/assets/{asset_id}", json={"notes": "updated"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["notes"] == "updated"

    delete_resp = client.delete(f"/assets/{asset_id}")
    assert delete_resp.status_code == 204


def test_event_and_exposure_flow(session, client):
    asset = Asset(name="Asset A")
    session.add(asset)
    session.commit()
    session.refresh(asset)

    start = datetime.utcnow()
    exp1 = ExposureLog(asset_id=asset.id, start_time=start, end_time=start + timedelta(hours=100), hours=100)
    exp2 = ExposureLog(asset_id=asset.id, start_time=start + timedelta(hours=100), end_time=start + timedelta(hours=200), hours=100)
    session.add_all([exp1, exp2])
    session.commit()

    fail_time = exp1.end_time
    event = Event(asset_id=asset.id, timestamp=fail_time, event_type="failure", downtime_minutes=60)
    session.add(event)
    session.commit()

    resp = client.get(f"/events/?asset_id={asset.id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_invalid_event_type_rejected(client):
    asset_resp = client.post("/assets/", json={"name": "Unit X"})
    asset_id = asset_resp.json()["id"]
    resp = client.post(
        "/events/",
        json={
            "asset_id": asset_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "bad",
            "downtime_minutes": 10,
        },
    )
    assert resp.status_code == 400


def test_overlapping_exposure_rejected(session, client):
    asset_resp = client.post("/assets/", json={"name": "Unit O"})
    asset_id = asset_resp.json()["id"]
    base = datetime.utcnow()
    start = base.isoformat()
    end = (base + timedelta(hours=10)).isoformat()
    ok = client.post(
        "/exposures/",
        json={"asset_id": asset_id, "start_time": start, "end_time": end, "hours": 10},
    )
    assert ok.status_code == 201
    conflict = client.post(
        "/exposures/",
        json={"asset_id": asset_id, "start_time": start, "end_time": end, "hours": 5},
    )
    assert conflict.status_code == 400


def test_part_install_time_validation(client):
    part_resp = client.post("/parts/", json={"name": "Seal"})
    part_id = part_resp.json()["id"]
    asset_resp = client.post("/assets/", json={"name": "Unit P"})
    asset_id = asset_resp.json()["id"]
    install = client.post(
        f"/parts/{part_id}/installs",
        json={"asset_id": asset_id, "install_time": datetime.utcnow().isoformat(), "remove_time": (datetime.utcnow() - timedelta(hours=1)).isoformat()},
    )
    assert install.status_code == 400
