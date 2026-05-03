"""OTP env gating: dev returns code, prod fails closed when Twilio unconfigured."""
import importlib
import pytest


@pytest.mark.asyncio
async def test_dev_env_returns_code(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_VERIFY_SERVICE_SID", raising=False)
    import services.twilio_provider as tp
    importlib.reload(tp)
    sent, code = await tp.send_otp("+905550000001")
    assert sent is True and code is not None and len(code) == 6
    assert await tp.verify_otp("+905550000001", code) is True


@pytest.mark.asyncio
async def test_prod_env_fails_closed(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_VERIFY_SERVICE_SID", raising=False)
    import services.twilio_provider as tp
    importlib.reload(tp)
    sent, code = await tp.send_otp("+905550000002")
    assert sent is False and code is None
    assert await tp.verify_otp("+905550000002", "123456") is False
    monkeypatch.setenv("APP_ENV", "development")
    importlib.reload(tp)
