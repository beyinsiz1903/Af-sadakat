"""Exports require authentication."""
from fastapi.testclient import TestClient
from server import app


client = TestClient(app)


def test_exports_require_auth():
    for ep in [
        "department-performance.xlsx",
        "department-performance.pdf",
        "sla-stats.xlsx",
        "loyalty-cohort.pdf",
    ]:
        r = client.get(f"/api/v2/exports/tenants/grand-hotel/{ep}")
        assert r.status_code in (401, 403), f"{ep} returned {r.status_code}"
