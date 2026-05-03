"""iyzico payment provider (Turkey).

Skeleton implementation:
- HMAC-SHA256 v2 auth header
- create_payment (3DS init)
- callback verification
- webhook signature check

Requires env: IYZICO_API_KEY, IYZICO_SECRET, IYZICO_BASE_URL
(default base: https://sandbox-api.iyzipay.com).

If env not set, is_configured() returns False and routers fall back to stub.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
from typing import Any, Dict, Optional

logger = logging.getLogger("omnihub.iyzico")

IYZICO_API_KEY = os.environ.get("IYZICO_API_KEY", "").strip()
IYZICO_SECRET = os.environ.get("IYZICO_SECRET", "").strip()
IYZICO_BASE_URL = os.environ.get("IYZICO_BASE_URL", "https://sandbox-api.iyzipay.com").strip()


def is_configured() -> bool:
    return bool(IYZICO_API_KEY and IYZICO_SECRET)


def _random_string(n: int = 8) -> str:
    return secrets.token_hex(n)


def _generate_auth_header(uri_path: str, body: Dict[str, Any]) -> Dict[str, str]:
    """iyzipay v2 HMAC-SHA256 authorization."""
    random_key = _random_string(8)
    payload = random_key + uri_path + json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    sig = hmac.new(IYZICO_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    auth_string = f"apiKey:{IYZICO_API_KEY}&randomKey:{random_key}&signature:{sig}"
    auth_b64 = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"IYZWSv2 {auth_b64}",
        "x-iyzi-rnd": random_key,
        "Content-Type": "application/json",
    }


async def create_3ds_payment(
    *,
    conversation_id: str,
    price: float,
    paid_price: float,
    currency: str,
    callback_url: str,
    buyer: Dict[str, Any],
    address: Dict[str, Any],
    items: list[Dict[str, Any]],
    card: Dict[str, Any],
) -> Dict[str, Any]:
    """Initiate iyzico 3DS checkout. Returns dict with htmlContent or error."""
    if not is_configured():
        raise RuntimeError("iyzico not configured")
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx required for iyzico")

    uri = "/payment/3dsecure/initialize"
    body = {
        "locale": "tr",
        "conversationId": conversation_id,
        "price": f"{price:.2f}",
        "paidPrice": f"{paid_price:.2f}",
        "currency": currency,
        "installment": 1,
        "paymentChannel": "WEB",
        "paymentGroup": "PRODUCT",
        "callbackUrl": callback_url,
        "paymentCard": card,
        "buyer": buyer,
        "shippingAddress": address,
        "billingAddress": address,
        "basketItems": items,
    }
    headers = _generate_auth_header(uri, body)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(IYZICO_BASE_URL + uri, headers=headers, json=body)
        try:
            return resp.json()
        except Exception:
            return {"status": "failure", "errorMessage": resp.text}


async def complete_3ds_payment(*, conversation_id: str, payment_id: str, conversation_data: str = "") -> Dict[str, Any]:
    """Complete a 3DS payment after user returned from bank."""
    if not is_configured():
        raise RuntimeError("iyzico not configured")
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx required for iyzico")

    uri = "/payment/3dsecure/auth"
    body = {
        "locale": "tr",
        "conversationId": conversation_id,
        "paymentId": payment_id,
        "conversationData": conversation_data,
    }
    headers = _generate_auth_header(uri, body)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(IYZICO_BASE_URL + uri, headers=headers, json=body)
        try:
            return resp.json()
        except Exception:
            return {"status": "failure", "errorMessage": resp.text}


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verify webhook signature from x-iyz-signature-v3 header."""
    if not IYZICO_SECRET or not signature_header:
        return False
    expected = hmac.new(IYZICO_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
