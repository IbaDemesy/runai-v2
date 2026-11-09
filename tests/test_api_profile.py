import pytest
from fastapi.testclient import TestClient
from test_api_guided import StubGuide, ready, terminal

from runai.app import create_app
from runai.models import RunnerProfile


def test_profile_normal_empty_and_delete():
    with TestClient(create_app(guide=StubGuide())) as client:
        url = ready(client)
        profile = {key: "Test Runner" for key in RunnerProfile.model_fields}
        profile.update(email="test.runner@example.com", phone="+33 6 00 00 00 00",
                       birth_date="1990-01-01", nationality="FR")
        response = client.post(url + "/profile", json=profile)
        assert response.status_code == 200
        assert response.json()["profile_status"] == {"complete": True, "fields": list(profile)}
        assert "Test Runner" not in response.text
        assert client.delete(url + "/profile").json()["profile_status"] == {
            "complete": False, "fields": [],
        }
        assert client.post(url + "/profile", json={}).json()["profile_status"]["fields"] == []
        assert client.delete(url).status_code == 204
        assert client.get(url).status_code == 404
        assert client.post(url + "/profile", json={}).status_code == 404


def test_delete_mission_purges_only_its_frames():
    with TestClient(create_app(guide=StubGuide())) as client:
        urls = [ready(client), ready(client)]
        frame_ids = []
        for url in urls:
            client.post(url + "/confirm", json={"confirmed": True})
            mission = terminal(client, url)
            ids = [event["frame_id"] for event in mission["events"] if event.get("frame_id")]
            assert ids
            assert all(client.get(f"/api/frames/{frame_id}").status_code == 200 for frame_id in ids)
            frame_ids.append(ids)
        assert client.delete(urls[0]).status_code == 204
        assert all(client.get(f"/api/frames/{frame_id}").status_code == 404
                   for frame_id in frame_ids[0])
        assert all(client.get(f"/api/frames/{frame_id}").status_code == 200
                   for frame_id in frame_ids[1])


@pytest.mark.parametrize("profile", [
    {"email": "invalid"}, {"phone": "not a phone"}, {"birth_date": "1990-02-30"},
    {"birth_date": "19900101"}, {"nationality": "ZZ"}, {"nationality": "FRA"},
    {"full_name": "x" * 201}, {"unknown": "value"}, {"city": 123},
])
def test_invalid_profile(profile):
    with TestClient(create_app(guide=StubGuide())) as client:
        url = ready(client)
        response = client.post(url + "/profile", json=profile)
        assert response.status_code == 422
        assert all(set(error) == {"loc", "msg", "type"} for error in response.json()["detail"])


def test_profile_wrong_state_and_cleared_after_run():
    with TestClient(create_app(guide=StubGuide())) as client:
        url = ready(client)
        client.post(url + "/profile", json={"full_name": "Test Runner"})
        client.post(url + "/confirm", json={"confirmed": True})
        assert terminal(client, url)["profile_status"] == {"complete": False, "fields": []}
        assert client.post(url + "/profile", json={}).status_code == 409
        assert client.delete(url + "/profile").status_code == 409


def test_guiding_profile_and_whitespace():
    with TestClient(create_app(guide=StubGuide())) as client:
        mission = client.post("/api/missions", json={"text": "race"}).json()
        response = client.post(f"/api/missions/{mission['id']}/profile", json={"city": "  "})
        assert response.status_code == 200
        assert response.json()["profile_status"] == {"complete": False, "fields": []}


@pytest.mark.parametrize("names,complete", [
    ({"full_name": "Test Runner"}, True),
    ({"given_name": "Test", "family_name": "Runner"}, True),
    ({"given_name": "Test"}, False), ({}, False),
])
def test_core_identity_completeness(names, complete):
    profile = {**names, "email": "test.runner@example.com", "phone": "+33 6 00 00 00 00",
               "birth_date": "1990-01-01", "gender": "F", "nationality": "FR"}
    with TestClient(create_app(guide=StubGuide())) as client:
        url = ready(client)
        result = client.post(url + "/profile", json=profile).json()
        assert result["profile_status"]["complete"] is complete
        profile.pop("email")
        assert not client.post(url + "/profile", json=profile).json()["profile_status"]["complete"]
