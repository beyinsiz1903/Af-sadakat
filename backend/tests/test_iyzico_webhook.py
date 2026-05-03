"""iyzico webhook signature verification."""
import hmac, hashlib, importlib, os


def test_webhook_signature_verification(monkeypatch):
    monkeypatch.setenv("IYZICO_API_KEY", "test_key")
    monkeypatch.setenv("IYZICO_SECRET", "test_secret_xyz")
    import services.iyzico_provider as ip
    importlib.reload(ip)
    raw = b'{"conversationId":"abc","status":"SUCCESS"}'
    good_sig = hmac.new(b"test_secret_xyz", raw, hashlib.sha256).hexdigest()
    assert ip.verify_webhook_signature(raw, good_sig) is True
    assert ip.verify_webhook_signature(raw, "deadbeef") is False
    assert ip.verify_webhook_signature(raw, "") is False


def test_webhook_rejects_when_unconfigured(monkeypatch):
    monkeypatch.delenv("IYZICO_API_KEY", raising=False)
    monkeypatch.delenv("IYZICO_SECRET", raising=False)
    import services.iyzico_provider as ip
    importlib.reload(ip)
    assert ip.verify_webhook_signature(b'{}', "anysig") is False
