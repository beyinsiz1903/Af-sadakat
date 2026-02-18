"""Email & SMS Notification Engine
Sends notifications via email (SMTP) and SMS (configurable provider)
Supports templates and multi-language
"""
import os
import logging
import asyncio
from typing import Optional, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ---- Email Configuration ----
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@hotel.com")
SMTP_ENABLED = bool(SMTP_HOST and SMTP_USER)

# ---- SMS Configuration ----
SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "")  # twilio, netgsm, iletimerkezi
SMS_API_KEY = os.environ.get("SMS_API_KEY", "")
SMS_API_SECRET = os.environ.get("SMS_API_SECRET", "")
SMS_FROM = os.environ.get("SMS_FROM", "Hotel")
SMS_ENABLED = bool(SMS_PROVIDER and SMS_API_KEY)

# ---- Email Templates ----
EMAIL_TEMPLATES = {
    "request_received": {
        "subject_en": "Your request has been received - {hotel_name}",
        "subject_tr": "Talebiniz alindi - {hotel_name}",
        "body_en": """Dear {guest_name},\n\nYour request has been received and assigned to our {department} team.\n\nRequest Details:\n- Category: {category}\n- Description: {description}\n- Priority: {priority}\n- Request ID: {request_id}\n\nWe will update you as soon as there is progress.\n\nBest regards,\n{hotel_name}""",
        "body_tr": """Sayin {guest_name},\n\nTalebiniz alinmis olup {department} ekibimize iletilmistir.\n\nTalep Detaylari:\n- Kategori: {category}\n- Aciklama: {description}\n- Oncelik: {priority}\n- Talep No: {request_id}\n\nGelisme oldugunda sizi bilgilendirecegiz.\n\nSaygilarimizla,\n{hotel_name}""",
    },
    "request_updated": {
        "subject_en": "Request update - {hotel_name}",
        "subject_tr": "Talep guncelleme - {hotel_name}",
        "body_en": """Dear {guest_name},\n\nYour request ({request_id}) has been updated.\n\nNew Status: {status}\n{notes}\n\nBest regards,\n{hotel_name}""",
        "body_tr": """Sayin {guest_name},\n\nTalebiniz ({request_id}) guncellendi.\n\nYeni Durum: {status}\n{notes}\n\nSaygilarimizla,\n{hotel_name}""",
    },
    "request_completed": {
        "subject_en": "Request completed - {hotel_name}",
        "subject_tr": "Talebiniz tamamlandi - {hotel_name}",
        "body_en": """Dear {guest_name},\n\nYour request ({request_id}) has been completed.\n\nWe hope everything is to your satisfaction. Please don't hesitate to contact us if you need anything else.\n\nWe would appreciate if you could rate our service.\n\nBest regards,\n{hotel_name}""",
        "body_tr": """Sayin {guest_name},\n\nTalebiniz ({request_id}) tamamlanmistir.\n\nHer sey yolundaysa mutluyuz. Baska bir ihtiyaciniz olursa bize ulasmaniz yeterli.\n\nHizmetimizi degerlendirirseniz cok seviniriz.\n\nSaygilarimizla,\n{hotel_name}""",
    },
    "spa_booking_confirmed": {
        "subject_en": "Spa booking confirmation - {hotel_name}",
        "subject_tr": "Spa randevu onayi - {hotel_name}",
        "body_en": """Dear {guest_name},\n\nYour spa booking has been confirmed.\n\nService: {service_type}\nDate: {date}\nTime: {time}\n\nPlease arrive 15 minutes early.\n\nBest regards,\n{hotel_name}""",
        "body_tr": """Sayin {guest_name},\n\nSpa randevunuz onaylanmistir.\n\nHizmet: {service_type}\nTarih: {date}\nSaat: {time}\n\nLutfen 15 dakika erken geliniz.\n\nSaygilarimizla,\n{hotel_name}""",
    },
    "transport_confirmed": {
        "subject_en": "Transport request confirmation - {hotel_name}",
        "subject_tr": "Transfer talebi onayi - {hotel_name}",
        "body_en": """Dear {guest_name},\n\nYour transport request has been confirmed.\n\nType: {transport_type}\nDate: {date}\nTime: {time}\nDestination: {destination}\n\nBest regards,\n{hotel_name}""",
        "body_tr": """Sayin {guest_name},\n\nTransfer talebiniz onaylanmistir.\n\nTur: {transport_type}\nTarih: {date}\nSaat: {time}\nHedef: {destination}\n\nSaygilarimizla,\n{hotel_name}""",
    },
}

# ---- SMS Templates ----
SMS_TEMPLATES = {
    "request_received": {
        "en": "{hotel_name}: Your request #{request_id} received. We're working on it!",
        "tr": "{hotel_name}: #{request_id} talebiniz alindi. Uzerinde calisiyoruz!",
    },
    "request_completed": {
        "en": "{hotel_name}: Your request #{request_id} is complete. Rate us!",
        "tr": "{hotel_name}: #{request_id} talebiniz tamamlandi. Bizi degerlendirin!",
    },
}


async def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email via SMTP"""
    if not SMTP_ENABLED:
        logger.info(f"[EMAIL-MOCK] To: {to_email} | Subject: {subject}")
        return True  # Mock success when SMTP not configured
    
    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASS,
            use_tls=True,
        )
        logger.info(f"[EMAIL] Sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send to {to_email}: {e}")
        return False


async def send_sms(phone: str, message: str) -> bool:
    """Send SMS via configured provider"""
    if not SMS_ENABLED:
        logger.info(f"[SMS-MOCK] To: {phone} | Message: {message}")
        return True  # Mock success when SMS not configured
    
    try:
        if SMS_PROVIDER == "twilio":
            return await _send_twilio_sms(phone, message)
        else:
            logger.warning(f"[SMS] Unknown provider: {SMS_PROVIDER}")
            return False
    except Exception as e:
        logger.error(f"[SMS] Failed to send to {phone}: {e}")
        return False


async def _send_twilio_sms(phone: str, message: str) -> bool:
    """Send SMS via Twilio"""
    import httpx
    account_sid = SMS_API_KEY
    auth_token = SMS_API_SECRET
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, data={
            "From": SMS_FROM,
            "To": phone,
            "Body": message,
        }, auth=(account_sid, auth_token))
        return resp.status_code == 201


async def send_notification_email(
    template_name: str,
    to_email: str,
    lang: str = "en",
    variables: Dict = None,
) -> bool:
    """Send templated notification email"""
    template = EMAIL_TEMPLATES.get(template_name)
    if not template:
        logger.warning(f"Email template not found: {template_name}")
        return False
    
    vars_dict = variables or {}
    subject_key = f"subject_{lang}" if f"subject_{lang}" in template else "subject_en"
    body_key = f"body_{lang}" if f"body_{lang}" in template else "body_en"
    
    subject = template[subject_key].format(**vars_dict)
    body = template[body_key].format(**vars_dict)
    
    return await send_email(to_email, subject, body)


async def send_notification_sms(
    template_name: str,
    phone: str,
    lang: str = "en",
    variables: Dict = None,
) -> bool:
    """Send templated SMS notification"""
    template = SMS_TEMPLATES.get(template_name)
    if not template:
        logger.warning(f"SMS template not found: {template_name}")
        return False
    
    vars_dict = variables or {}
    lang_key = lang if lang in template else "en"
    message = template[lang_key].format(**vars_dict)
    
    return await send_sms(phone, message)


async def notify_guest(
    db,
    tenant_id: str,
    template_name: str,
    guest_email: str = "",
    guest_phone: str = "",
    lang: str = "en",
    variables: Dict = None,
):
    """Send notification to guest via available channels + log"""
    results = {"email": None, "sms": None}
    
    if guest_email:
        results["email"] = await send_notification_email(template_name, guest_email, lang, variables)
    if guest_phone:
        results["sms"] = await send_notification_sms(template_name, guest_phone, lang, variables)
    
    # Log notification
    await db.notification_logs.insert_one({
        "id": str(__import__("uuid").uuid4()),
        "tenant_id": tenant_id,
        "template_name": template_name,
        "guest_email": guest_email,
        "guest_phone": guest_phone,
        "lang": lang,
        "variables": variables or {},
        "results": results,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    
    return results
