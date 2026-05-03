"""Twilio dev-mode OTP fallback tests (does not require real Twilio creds)."""
import pytest

from services import twilio_provider as tw


@pytest.mark.asyncio
async def test_dev_otp_send_and_verify(monkeypatch):
    # Force unconfigured so dev fallback kicks in
    monkeypatch.setattr(tw, "TWILIO_ACCOUNT_SID", "")
    monkeypatch.setattr(tw, "TWILIO_AUTH_TOKEN", "")
    monkeypatch.setattr(tw, "TWILIO_VERIFY_SERVICE_SID", "")

    sent, code = await tw.send_otp("+905550000000")
    assert sent is True
    assert code is not None and len(code) == 6 and code.isdigit()

    assert await tw.verify_otp("+905550000000", code) is True
    # Used once → should now be invalid
    assert await tw.verify_otp("+905550000000", code) is False
    assert await tw.verify_otp("+905550000000", "000000") is False
