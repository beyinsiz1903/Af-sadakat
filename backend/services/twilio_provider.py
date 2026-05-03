"""Twilio Verify provider for OTP.

Uses Twilio Verify API (preferred over raw SMS for OTP — Twilio handles code
generation, expiry, retries, fraud detection).

Env required:
  TWILIO_ACCOUNT_SID
  TWILIO_AUTH_TOKEN
  TWILIO_VERIFY_SERVICE_SID

If env not set, dev fallback: code is logged to stdout and returned to caller
so existing dev flow keeps working.
"""
from __future__ import annotations

import logging
import os
import secrets
from typing import Optional, Tuple

logger = logging.getLogger("omnihub.twilio")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_VERIFY_SERVICE_SID = os.environ.get("TWILIO_VERIFY_SERVICE_SID", "").strip()
APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()

_dev_codes: dict[str, str] = {}


def is_configured() -> bool:
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_VERIFY_SERVICE_SID)


def is_dev_env() -> bool:
    return APP_ENV in ("development", "dev", "test", "testing", "local")


async def send_otp(phone: str, channel: str = "sms") -> Tuple[bool, Optional[str]]:
    """Send an OTP via Twilio Verify (or dev fallback).

    Returns (sent, dev_code). dev_code is non-None ONLY in dev fallback mode.
    In production with Twilio unconfigured, this fails closed (returns False, None).
    """
    if not is_configured():
        if not is_dev_env():
            logger.error("Twilio unconfigured in production env (APP_ENV=%s) — OTP fails closed", APP_ENV)
            return False, None
        code = f"{secrets.randbelow(1000000):06d}"
        _dev_codes[phone] = code
        logger.warning("[DEV] OTP for %s: %s (Twilio not configured)", phone, code)
        return True, code

    try:
        from twilio.rest import Client
    except ImportError:
        logger.error("twilio package not installed")
        return False, None

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        verification = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID).verifications.create(
            to=phone, channel=channel
        )
        return verification.status == "pending", None
    except Exception as e:
        logger.error("Twilio send_otp failed for %s: %s", phone, e)
        return False, None


async def verify_otp(phone: str, code: str) -> bool:
    """Verify the OTP. Returns True on success.

    In production with Twilio unconfigured, fails closed (returns False).
    """
    if not is_configured():
        if not is_dev_env():
            logger.error("Twilio unconfigured in production env — OTP verify fails closed")
            return False
        expected = _dev_codes.get(phone)
        if expected and expected == code:
            _dev_codes.pop(phone, None)
            return True
        return False

    try:
        from twilio.rest import Client
    except ImportError:
        logger.error("twilio package not installed")
        return False

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        check = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
            to=phone, code=code
        )
        return check.status == "approved"
    except Exception as e:
        logger.error("Twilio verify_otp failed for %s: %s", phone, e)
        return False
