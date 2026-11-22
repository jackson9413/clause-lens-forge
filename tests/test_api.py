"""API tests for Clause Lens."""

import json

import pytest

import app as app_module
from engine.samples import SAMPLES, by_id


@pytest.fixture()
def client():
    app_module.db.init_db()
    with app_module.app.test_client() as c:
        yield c


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_meta_lists_types_perspectives_and_samples(client):
    res = client.get("/api/meta")
    data = res.get_json()
    assert len(data["contract_types"]) == 8
    assert {p["key"] for p in data["perspectives"]} == {"client", "vendor", "employee", "party"}
    assert len(data["samples"]) == len(SAMPLES)


def test_review_returns_a_full_report(client):
    payload = {"text": by_id("vendor-msa-one-sided")["text"], "contract_type": "msa",
               "perspective": "client", "title": "Test MSA"}
    res = client.post("/api/review", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["score"]["overall"] > 0
    assert data["findings"]
    assert data["meta"]["title"] == "Test MSA"
    assert data["review_id"]


def test_review_without_text_is_rejected(client):
    res = client.post("/api/review", json={"text": "   "})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_review_with_huge_text_is_rejected(client):
    res = client.post("/api/review", json={"text": "x" * (app_module.MAX_CHARS + 10)})
    assert res.status_code == 400


def test_sample_endpoint(client):
    res = client.get("/api/samples/vendor-msa-one-sided")
    assert res.status_code == 200
    assert res.get_json()["id"] == "vendor-msa-one-sided"
    assert client.get("/api/samples/nope").status_code == 404


def test_history_save_rate_and_delete(client):
    res = client.post("/api/review", json={"text": "A contract effective as of January 1, 2026. "
                                              "Client shall pay net 30 days.", "contract_type": "msa"})
    review_id = res.get_json()["review_id"]
    assert review_id

    history = client.get("/api/history").get_json()["reviews"]
    assert any(h["id"] == review_id for h in history)

    rated = client.post("/api/history/%d" % review_id, json={"rating": 4, "notes": "useful"})
    assert rated.status_code == 200
    row = [h for h in client.get("/api/history").get_json()["reviews"] if h["id"] == review_id][0]
    assert row["rating"] == 4
    assert row["notes"] == "useful"

    assert client.post("/api/history/%d" % review_id, json={"rating": 9}).status_code == 400
    assert client.delete("/api/history/%d" % review_id).status_code == 200
    assert client.delete("/api/history/%d" % review_id).status_code == 404


def test_exports(client):
    res = client.post("/api/review", json={"text": by_id("saas-subscription")["text"],
                                            "contract_type": "saas", "title": "SaaS deal"})
    review_id = res.get_json()["review_id"]

    md = client.get("/api/export/%d?format=md" % review_id)
    assert md.status_code == 200
    assert "# Contract review" in md.get_data(as_text=True)

    js = client.get("/api/export/%d?format=json" % review_id)
    assert js.status_code == 200
    assert "score" in json.loads(js.get_data(as_text=True))

    ics = client.get("/api/export/%d?format=ics" % review_id)
    assert ics.status_code == 200
    assert ics.get_data(as_text=True).startswith("BEGIN:VCALENDAR")


def test_index_page_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "Clause Lens" in body
    assert "/static/app.js" in body
    assert "/static/styles.css" in body


def test_static_assets_are_served(client):
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200


def test_unknown_route_returns_json_404(client):
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    assert "error" in res.get_json()


def test_frontend_calls_the_expected_endpoints():
    with open(app_module.BASE_DIR + "/static/app.js") as fh:
        source = fh.read()
    assert "/api/review" in source
    assert "/api/meta" in source
    assert "/api/export/" in source
    assert "/api/history" in source
    assert "/api/samples/" in source
