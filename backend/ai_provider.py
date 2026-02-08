"""Sentiment analysis (rule-based MVP)"""

NEG_KEYWORDS_EN = {"dirty", "noise", "noisy", "not working", "bad", "terrible", "disappointed",
                   "refund", "worst", "awful", "broken", "cold", "rude", "slow", "unacceptable",
                   "horrible", "disgusting", "complaint"}
NEG_KEYWORDS_TR = {"pis", "gurultu", "bozuk", "kotu", "berbat", "korkunc", "hayal kirikligi",
                   "iade", "kabul edilemez", "kaba", "yavas", "sikayet", "sorun"}

POS_KEYWORDS_EN = {"great", "amazing", "perfect", "excellent", "wonderful", "beautiful",
                   "friendly", "clean", "loved", "best", "impressed", "fantastic", "outstanding"}
POS_KEYWORDS_TR = {"harika", "mukemmel", "muhtesem", "temiz", "guzel", "hizli",
                   "tesekkur", "sevdik", "etkilendik", "iyi"}

def classify_sentiment(text: str) -> str:
    """Returns POS, NEU, or NEG"""
    lower = text.lower()
    neg = sum(1 for w in (NEG_KEYWORDS_EN | NEG_KEYWORDS_TR) if w in lower)
    pos = sum(1 for w in (POS_KEYWORDS_EN | POS_KEYWORDS_TR) if w in lower)
    if neg > pos:
        return "NEG"
    elif pos > neg:
        return "POS"
    return "NEU"


# ---- AI Mock Templates ----
REPLY_TEMPLATES = {
    "inbox": {
        "en": {
            "greeting": "Welcome! Thank you for reaching out to {hotel_name}. How can we help you today?",
            "booking": "We'd be happy to help with your reservation! Could you share your preferred dates and room type?",
            "complaint": "We sincerely apologize for the inconvenience. Our team has been notified and will address this right away.",
            "thanks": "Thank you for your kind words! We're glad you enjoyed your stay.",
            "default": "Thank you for your message. Our team will get back to you shortly.",
        },
        "tr": {
            "greeting": "Hos geldiniz! {hotel_name} olarak size nasil yardimci olabiliriz?",
            "booking": "Rezervasyonunuz icin yardimci olmaktan mutluluk duyariz! Tercih ettiginiz tarihleri paylasir misiniz?",
            "complaint": "Yasadiginiz rahatsizlik icin ozur dileriz. Ekibimiz hemen ilgilenecektir.",
            "thanks": "Guzel sozleriniz icin tesekkur ederiz!",
            "default": "Mesajiniz icin tesekkurler. En kisa surede donus yapacagiz.",
        }
    },
    "review": {
        "en": {
            "positive": "Thank you so much for your wonderful review, {author}! We're thrilled you enjoyed your stay at {hotel_name}. We look forward to welcoming you again!",
            "neutral": "Thank you for your feedback, {author}. We appreciate your honest review and are always working to improve. We hope to serve you better next time!",
            "negative": "Dear {author}, we sincerely apologize for your experience. Your feedback is very important to us. We've shared it with our team and are taking immediate action. We'd love the chance to make things right.",
        },
        "tr": {
            "positive": "Harika yorumunuz icin cok tesekkur ederiz, {author}! Konaklamanizdan memnun kalmaniz bizi cok mutlu etti.",
            "neutral": "Geri bildiriminiz icin tesekkur ederiz, {author}. Surekli gelismek icin calisiyoruz.",
            "negative": "Sayin {author}, yasadiginiz deneyim icin ictenlikle ozur dileriz. Geri bildiriminizi ekibimizle paylaştik.",
        }
    }
}

def detect_language(text: str) -> str:
    tr_indicators = ["merhaba", "tesekkur", "lutfen", "oda", "yardim", "siparis", "kahvalti",
                     "guzel", "harika", "otel", "rezervasyon"]
    lower = text.lower()
    tr_count = sum(1 for w in tr_indicators if w in lower)
    return "tr" if tr_count >= 2 else "en"

def detect_intent(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ["hello", "hi", "merhaba", "selam", "hey"]):
        return "greeting"
    if any(w in lower for w in ["book", "reserve", "room", "date", "rezervasyon", "oda"]):
        return "booking"
    if any(w in lower for w in ["complaint", "problem", "issue", "bad", "broken", "sikayet", "sorun"]):
        return "complaint"
    if any(w in lower for w in ["thank", "great", "amazing", "tesekkur", "harika"]):
        return "thanks"
    return "default"

def generate_inbox_reply(message_text: str, hotel_name: str = "Our Hotel") -> dict:
    lang = detect_language(message_text)
    intent = detect_intent(message_text)
    template = REPLY_TEMPLATES["inbox"].get(lang, REPLY_TEMPLATES["inbox"]["en"]).get(intent, REPLY_TEMPLATES["inbox"]["en"]["default"])
    suggestion = template.format(hotel_name=hotel_name)
    return {"suggestion": suggestion, "intent": intent, "language": lang, "provider": "MockTemplateV1"}

def generate_review_reply(review_text: str, sentiment: str, author: str = "", hotel_name: str = "Our Hotel") -> dict:
    lang = detect_language(review_text)
    sent_key = {"POS": "positive", "NEG": "negative"}.get(sentiment, "neutral")
    template = REPLY_TEMPLATES["review"].get(lang, REPLY_TEMPLATES["review"]["en"]).get(sent_key, REPLY_TEMPLATES["review"]["en"]["neutral"])
    suggestion = template.format(author=author or "Guest", hotel_name=hotel_name)
    return {"suggestion": suggestion, "sentiment": sent_key, "language": lang, "provider": "MockTemplateV1"}
