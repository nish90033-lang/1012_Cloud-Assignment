import json

import app as svc
import pytest
from fastapi.testclient import TestClient

REPLY = '{"intent": "weather_query", "date": null, "time": null, "place": "london"}'


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(svc, "MODEL_VERSION", "v1")
    monkeypatch.setattr(svc, "POD_NAME", "pod-a")
    with TestClient(svc.app) as c:
        svc.state.update(ready=False)
        yield c
    svc.state.update(ready=False)


def test_health_always_ok_and_ready_503_until_loaded(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 503
    svc.state["ready"] = True
    assert client.get("/readyz").status_code == 200


def test_parse_returns_only_the_json_and_both_headers(client, monkeypatch):
    svc.state["ready"] = True
    monkeypatch.setattr(svc, "run_model", lambda text: REPLY)
    r = client.post("/parse", json={"text": "what is the weather in london"})
    assert r.status_code == 200
    assert r.json() == json.loads(REPLY)
    assert r.headers["X-Model-Version"] == "v1" and r.headers["X-Served-By"] == "pod-a"


def test_fault_injection_returns_500_with_exact_body(client, monkeypatch):
    svc.state["ready"] = True
    monkeypatch.setattr(svc, "run_model", lambda text: REPLY)
    monkeypatch.setenv("FAULT_INJECT", "1")
    r = client.post("/parse", json={"text": "x"})
    assert r.status_code == 500 and r.json() == {"error": "invalid_model_output"}


@pytest.mark.parametrize("bad", ['{"intent": "alarm_set", "date": "tomor', '{"intent": "alarm_set"}',
                                 '{"intent": "dance", "date": null, "time": null, "place": null}',
                                 '{"intent": "alarm_set", "date": null, "time": null, "place": null, "x": 1}'])
def test_invalid_model_output_never_returned_with_200(client, monkeypatch, bad):
    svc.state["ready"] = True
    monkeypatch.setattr(svc, "run_model", lambda text: bad)
    r = client.post("/parse", json={"text": "x"})
    assert r.status_code == 500 and r.json() == {"error": "invalid_model_output"}


def test_parse_before_model_is_loaded_is_503(client):
    assert client.post("/parse", json={"text": "x"}).status_code == 503
