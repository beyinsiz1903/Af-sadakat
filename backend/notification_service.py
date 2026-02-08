"""Notification Service (Mock) - Sprint 6
Provides provider interface for future email/SMS integration.
Currently logs structured JSON to console and inserts notification records.
"""
import logging
from core.config import db
from core.tenant_guard import new_id, now_utc, serialize_doc

logger = logging.getLogger("omnihub.notifications")

# Template types
TEMPLATE_TYPES = [
    "OFFER_SENT",
    "PAYMENT_SUCCEEDED",
    "RESERVATION_CONFIRMED",
    "REQUEST_CREATED",
    "ORDER_COMPLETED",
]

# Default templates (mock)
DEFAULT_TEMPLATES = {
    "OFFER_SENT": {
        "subject": "Your reservation offer from {hotel_name}",
        "body": "Dear {guest_name}, we've prepared an offer for your stay ({check_in} to {check_out}). Total: {currency} {price}. Pay here: {payment_url}",
    },
    "PAYMENT_SUCCEEDED": {
        "subject": "Payment confirmed - {hotel_name}",
        "body": "Dear {guest_name}, your payment of {currency} {price} has been received. Confirmation code: {confirmation_code}.",
    },
    "RESERVATION_CONFIRMED": {
        "subject": "Reservation confirmed - {confirmation_code}",
        "body": "Dear {guest_name}, your reservation at {hotel_name} is confirmed. Check-in: {check_in}, Check-out: {check_out}. Code: {confirmation_code}.",
    },
    "REQUEST_CREATED": {
        "subject": "Service request received - {hotel_name}",
        "body": "Your request ({category}) has been received and our team is on it.",
    },
    "ORDER_COMPLETED": {
        "subject": "Order ready - {hotel_name}",
        "body": "Your order is ready. Thank you for dining with us!",
    },
}


class NotificationProvider:
    """Base provider interface for future real integrations (SendGrid, Twilio, etc.)"""
    async def send_email(self, to: str, subject: str, body: str, **kwargs) -> dict:
        raise NotImplementedError

    async def send_sms(self, to: str, body: str, **kwargs) -> dict:
        raise NotImplementedError


class MockNotificationProvider(NotificationProvider):
    """Mock provider - logs to console, no real delivery."""
    async def send_email(self, to: str, subject: str, body: str, **kwargs) -> dict:
        logger.info(
            '{"notification":"email","to":"%s","subject":"%s","status":"mock_sent"}',
            to.replace('"', ''), subject.replace('"', '')
        )
        return {"status": "mock_sent", "channel": "email", "to": to}

    async def send_sms(self, to: str, body: str, **kwargs) -> dict:
        logger.info(
            '{"notification":"sms","to":"%s","status":"mock_sent"}',
            to.replace('"', '')
        )
        return {"status": "mock_sent", "channel": "sms", "to": to}


# Singleton provider
_provider = MockNotificationProvider()


def get_notification_provider() -> NotificationProvider:
    return _provider


async def send_notification(
    tenant_id: str,
    template_type: str,
    recipient_email: str = "",
    recipient_phone: str = "",
    context: dict = None,
    actor_id: str = "system",
):
    """Send notification using template + provider. Records in DB."""
    ctx = context or {}
    template = DEFAULT_TEMPLATES.get(template_type, {})
    subject = template.get("subject", template_type).format_map(
        {**ctx, **{k: ctx.get(k, "") for k in ["hotel_name", "guest_name", "check_in", "check_out",
                                                   "currency", "price", "confirmation_code", "payment_url",
                                                   "category"]}}
    )
    body = template.get("body", "").format_map(
        {**ctx, **{k: ctx.get(k, "") for k in ["hotel_name", "guest_name", "check_in", "check_out",
                                                   "currency", "price", "confirmation_code", "payment_url",
                                                   "category"]}}
    )

    provider = get_notification_provider()
    result = {}

    if recipient_email:
        try:
            result = await provider.send_email(recipient_email, subject, body)
        except Exception as e:
            logger.error("Email notification failed: %s", str(e))
            result = {"status": "error", "error": str(e)}

    if recipient_phone:
        try:
            sms_result = await provider.send_sms(recipient_phone, body)
            result = {**result, "sms": sms_result}
        except Exception as e:
            logger.error("SMS notification failed: %s", str(e))

    # Record notification in DB
    record = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "template_type": template_type,
        "recipient_email": recipient_email,
        "recipient_phone": recipient_phone,
        "subject": subject,
        "body": body[:500],
        "status": result.get("status", "sent"),
        "provider": "mock",
        "context": {k: str(v)[:100] for k, v in (ctx or {}).items()},
        "created_at": now_utc().isoformat(),
    }
    await db.notifications.insert_one(record)

    # Audit log
    await db.audit_logs.insert_one({
        "id": new_id(),
        "tenant_id": tenant_id,
        "action": f"NOTIFICATION_{template_type}",
        "entity_type": "notification",
        "entity_id": record["id"],
        "actor_user_id": actor_id,
        "details": {"template": template_type, "to_email": recipient_email[:3] + "***" if recipient_email else "",
                     "to_phone": "****" + recipient_phone[-4:] if len(recipient_phone) > 4 else ""},
        "created_at": now_utc().isoformat(),
    })

    return serialize_doc(record)
