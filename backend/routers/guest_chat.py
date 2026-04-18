"""Webchat / conversation routes + AI mock suggest-reply.
Extracted from server.py for maintainability.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from core.config import db
from core.tenant_guard import serialize_doc, new_id, now_utc
from core.legacy_helpers import get_tenant_by_slug, ws_manager

logger = logging.getLogger("omnihub.guest_chat")
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/g/{tenant_slug}/chat/start")
async def start_chat(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    conversation = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "channel": "webchat",
        "status": "open",
        "guest_name": "",
        "assigned_agent": None,
        "needs_attention": False,
        "last_message": "",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }
    await db.conversations.insert_one(conversation)
    result = serialize_doc(conversation)
    await ws_manager.broadcast_tenant(tenant["id"], "conversation", "conversation", "created", result)
    return result


@router.post("/g/{tenant_slug}/chat/{conversation_id}/messages")
async def send_chat_message(tenant_slug: str, conversation_id: str, message: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    conv = await db.conversations.find_one({"id": conversation_id, "tenant_id": tenant["id"]})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    content = message.get("content", "")
    msg = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "conversation_id": conversation_id,
        "sender_type": message.get("sender_type", "guest"),
        "sender_name": message.get("sender_name", "Guest"),
        "content": content,
        "created_at": now_utc().isoformat(),
    }
    await db.messages.insert_one(msg)

    update = {"updated_at": now_utc().isoformat(), "last_message": content[:100]}
    urgent_keywords = ["urgent", "emergency", "broken", "complaint", "terrible", "acil", "sorun", "korkunç"]
    if any(kw in content.lower() for kw in urgent_keywords):
        update["needs_attention"] = True
    if message.get("sender_name"):
        update["guest_name"] = message["sender_name"]

    await db.conversations.update_one({"id": conversation_id}, {"$set": update})
    result = serialize_doc(msg)
    await ws_manager.broadcast_tenant(tenant["id"], "message", "message", "created", result)
    return result


@router.get("/g/{tenant_slug}/chat/{conversation_id}/messages")
async def get_chat_messages(tenant_slug: str, conversation_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    messages = await db.messages.find(
        {"tenant_id": tenant["id"], "conversation_id": conversation_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    return [serialize_doc(m) for m in messages]


@router.get("/tenants/{tenant_slug}/conversations")
async def list_conversations(tenant_slug: str, status: Optional[str] = None):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if status:
        query["status"] = status
    convs = await db.conversations.find(query, {"_id": 0}).sort("updated_at", -1).to_list(100)
    return [serialize_doc(c) for c in convs]


@router.patch("/tenants/{tenant_slug}/conversations/{conv_id}")
async def update_conversation(tenant_slug: str, conv_id: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    allowed = ["status", "assigned_agent", "needs_attention"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    update_data["updated_at"] = now_utc().isoformat()
    await db.conversations.update_one({"id": conv_id, "tenant_id": tenant["id"]}, {"$set": update_data})
    updated = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    return serialize_doc(updated)


@router.post("/tenants/{tenant_slug}/ai/suggest-reply")
async def ai_suggest_reply(tenant_slug: str, context: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    message_text = context.get("message", "")
    language = context.get("language", "en")
    sector = context.get("sector", tenant.get("business_type", "hotel"))

    turkish_words = ["merhaba", "teşekkür", "lütfen", "rica", "oda", "yardım", "sipariş", "garson", "hesap"]
    if any(w in message_text.lower() for w in turkish_words):
        language = "tr"

    templates = {
        "hotel": {
            "en": {
                "greeting": "Welcome! Thank you for reaching out. How can we assist you during your stay?",
                "request": "We've received your request and our team is working on it. Is there anything else you need?",
                "complaint": "We sincerely apologize for the inconvenience. Our team has been notified and will address this immediately.",
                "checkout": "Thank you for staying with us! We hope you had a wonderful experience. Safe travels!",
                "default": "Thank you for your message. Our team will get back to you shortly.",
            },
            "tr": {
                "greeting": "Hos geldiniz! Bize ulastiginiz icin tesekkur ederiz. Konaklamaniz suresince size nasil yardimci olabiliriz?",
                "request": "Talebinizi aldik ve ekibimiz uzerinde calisiyor. Baska bir ihtiyaciniz var mi?",
                "complaint": "Yasadiginiz rahatsizlik icin ictenlikle ozur dileriz. Ekibimiz bilgilendirildi.",
                "checkout": "Bizde kaldiginiz icin tesekkur ederiz! Harika bir deneyim yasamis olmanizi umuyoruz.",
                "default": "Mesajiniz icin tesekkur ederiz. Ekibimiz en kisa surede size donus yapacaktir.",
            },
        },
        "restaurant": {
            "en": {
                "greeting": "Welcome! Thank you for dining with us. How can we help?",
                "order": "Your order has been received and is being prepared. We'll update you when it's ready!",
                "complaint": "We're sorry about that. We'll make it right. A team member will be with you shortly.",
                "bill": "Your bill is being prepared. Thank you for dining with us!",
                "default": "Thank you for your message. How can we help you today?",
            },
            "tr": {
                "greeting": "Hos geldiniz! Bizi tercih ettiginiz icin tesekkur ederiz.",
                "order": "Siparisinis alindi ve hazirlaniyor. Hazir oldugunda sizi bilgilendireceğiz!",
                "complaint": "Bunun icin uzgunuz. Hemen duzelteceğiz.",
                "bill": "Hesabiniz hazirlaniyor. Bizi tercih ettiginiz icin tesekkur ederiz!",
                "default": "Mesajiniz icin tesekkurler. Bugün size nasil yardimci olabiliriz?",
            },
        },
    }

    intent = "default"
    lower = message_text.lower()
    if any(w in lower for w in ["hello", "hi", "merhaba", "selam"]):
        intent = "greeting"
    elif any(w in lower for w in ["order", "sipariş", "menu"]):
        intent = "order"
    elif any(w in lower for w in ["request", "need", "talep", "istiyorum"]):
        intent = "request"
    elif any(w in lower for w in ["complaint", "problem", "issue", "şikayet", "sorun"]):
        intent = "complaint"
    elif any(w in lower for w in ["bill", "check", "hesap", "ödeme"]):
        intent = "bill"
    elif any(w in lower for w in ["checkout", "leaving", "çıkış"]):
        intent = "checkout"

    sector_templates = templates.get(sector, templates["hotel"])
    lang_templates = sector_templates.get(language, sector_templates["en"])
    reply = lang_templates.get(intent, lang_templates["default"])

    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.ai_replies_this_month": 1}})

    return {"suggestion": reply, "intent": intent, "language": language, "sector": sector, "provider": "mock_template_v1"}
