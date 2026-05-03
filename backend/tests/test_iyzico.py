"""iyzico provider tests — HMAC + webhook signature verification."""
import hashlib
import hmac
import os

from services import iyzico_provider as iyz


def test_is_configured_reflects_env(monkeypatch):
    monkeypatch.setattr(iyz, "IYZICO_API_KEY", "")
    monkeypatch.setattr(iyz, "IYZICO_SECRET", "")
    assert iyz.is_configured() is False
    monkeypatch.setattr(iyz, "IYZICO_API_KEY", "k")
    monkeypatch.setattr(iyz, "IYZICO_SECRET", "s")
    assert iyz.is_configured() is True


def test_auth_header_shape(monkeypatch):
    monkeypatch.setattr(iyz, "IYZICO_API_KEY", "key123")
    monkeypatch.setattr(iyz, "IYZICO_SECRET", "secret456")
    h = iyz._generate_auth_header("/payment/3dsecure/initialize", {"price": "10.00"})
    assert h["Content-Type"] == "application/json"
    assert h["Authorization"].startswith("IYZWSv2 ")
    assert "x-iyzi-rnd" in h
    assert len(h["x-iyzi-rnd"]) == 16


def test_webhook_signature_valid(monkeypatch):
    monkeypatch.setattr(iyz, "IYZICO_SECRET", "topsecret")
    body = b'{"paymentId":"123"}'
    sig = hmac.new(b"topsecret", body, hashlib.sha256).hexdigest()
    assert iyz.verify_webhook_signature(body, sig) is True
    assert iyz.verify_webhook_signature(body, "wrong") is False
    assert iyz.verify_webhook_signature(body, "") is False
