"""Tests de contrat minimaux (smoke) contre l'API servie."""

import time

import requests


def _wait_server(url: str, timeout: float = 10.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(url, timeout=1.0)
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Serveur indisponible: {url}")


def test_openapi_served():
    _wait_server("http://localhost:8000/health")
    resp = requests.get("http://localhost:8000/openapi.json", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("info", {}).get("title") == "FilAgent API"


def test_health_ok():
    _wait_server("http://localhost:8000/health")
    resp = requests.get("http://localhost:8000/health", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "components" in data


def test_chat_minimal():
    _wait_server("http://localhost:8000/health")
    payload = {"messages": [{"role": "user", "content": "Bonjour"}]}
    resp = requests.post("http://localhost:8000/chat", json=payload, timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("object") == "chat.completion"
    assert isinstance(data.get("choices"), list) and len(data["choices"]) >= 1
