import tempfile

from fastapi.testclient import TestClient

from app.server import create_app

HTTP_200_OK = 200


def test_transactions_crud(monkeypatch) -> None:
    # Force data dir to temp in tests
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("MACCOUNTING_DATA_DIR", tmpdir)
        app = create_app()
        client = TestClient(app)

        # List empty
        resp = client.get("/api/transactions")
        assert resp.status_code == HTTP_200_OK
        assert resp.json() == []

        # Upsert
        payload = [
            {
                "id": "t1",
                "date": "2024-01-01",
                "amount": 1.0,
                "currency": "USD",
                "type": "expense",
            }
        ]
        resp = client.post("/api/transactions", json=payload)
        assert resp.status_code == HTTP_200_OK
        assert any(tx["id"] == "t1" for tx in resp.json())

        # Get
        resp = client.get("/api/transactions/t1")
        assert resp.status_code == HTTP_200_OK
        assert resp.json()["id"] == "t1"

        # Delete
        resp = client.delete("/api/transactions/t1")
        assert resp.status_code == HTTP_200_OK
        assert resp.json()["deleted"] is True
