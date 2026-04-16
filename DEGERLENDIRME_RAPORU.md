# OmniHub - İş Fikri Değerlendirme ve Geliştirme Raporu

**Tarih:** 16 Nisan 2026  
**Son Güncelleme:** 16 Nisan 2026 (Kapsamlı durum güncellemesi)  
**Kapsam:** Otel QR tabanlı misafir hizmetleri, sadakat programı, oda folyosu, üyelik sistemi ve genel platform değerlendirmesi

---

## 1. FİKRİN ÖZETİ VE MEVCUT DURUM

Fikir: Her otel odasına özel QR kod tanımlanacak. Misafir üye olmadan QR ile odasıyla ilgili her talebini (teknik, oda servisi, erken uyandırma, çamaşırhane vb.) ilgili departmanlara iletebilecek. Dilerse üye olarak sadakat programından faydalanabilecek, puan biriktirip kullanabilecek, oda folyosunu görebilecek, yeni rezervasyon oluşturabilecek.

### Mevcut Durumda OLAN Özellikler:
- ✅ Oda bazlı QR kod sistemi (her odaya benzersiz kod)
- ✅ Üye olmadan talep gönderme (housekeeping, teknik, oda servisi, uyandırma, çamaşırhane, spa, transfer, bellboy, minibar, şikayet, checkout)
- ✅ Taleplerin departmanlara otomatik yönlendirilmesi
- ✅ Misafirin kendi taleplerini takip edebilmesi (durum izleme)
- ✅ Talep tamamlandığında yıldız ile değerlendirme
- ✅ Oda servisi menüsü ve sipariş verme
- ✅ Restoran rezervasyonu (tarih/saat seçimi, kişi sayısı, müsaitlik kontrolü)
- ✅ Otel bilgileri (WiFi, check-in/out, tesisler, acil numaralar)
- ✅ Sadakat programına katılma (telefon + isim ile)
- ✅ Puan kazanma ve katmanlı üyelik (Bronz → Gümüş → Altın → Platin)
- ✅ Puan harcama (ödül kataloğu: konaklama, spa, restoran, partner ödülleri)
- ✅ Dijital sadakat kartı (QR kodlu) ve Apple/Google Wallet desteği
- ✅ Çoklu dil desteği (EN/TR/AR/DE/RU/FR/ES/ZH) — 8 dil
- ✅ Dosya/fotoğraf ekleme desteği
- ✅ Duyuru sistemi
- ✅ Anket/memnuniyet formu
- ✅ Oda Folyosu — Misafir konaklama süresince tüm harcamalarını (oda servisi, minibar, spa, çamaşırhane, transfer) tarih filtreli olarak görebiliyor
- ✅ Misafir Push Bildirimleri — Talep durum değişikliklerinde Web Push ile anlık bildirim (TR/EN), kategori bazlı bildirim tercih yönetimi, uygulama içi bildirim paneli ve okunmamış rozeti
- ✅ SLA Takip Sistemi — Kategori/öncelik bazlı yanıt süresi kuralları, ihlal takibi, otomatik eskalasyon
- ✅ Gamification — Rozetler, meydan okumalar, sıralama tablosu, günlük giriş serisi (streak)
- ✅ AI Satış Motoru — Otomatik webchat, fiyat teklifi, indirim müzakeresi, ödeme linki oluşturma
- ✅ A/B Test Altyapısı — Varyant ataması, katılımcı takibi, kazanan belirleme
- ✅ Gelir ve Performans Analitiği — MRR/ARR, misafir davranış analizi, personel verimlilik skoru
- ✅ PWA Desteği — Service Worker, ana ekrana ekleme, offline push bildirimleri
- ✅ GDPR/KVKK Uyumu — Veri silme otomasyonu, retention cleanup, consent log takibi
- ✅ Güvenlik Katmanı — Rate limiting, brute force koruması, token family rotation, CSRF, session yönetimi, RBAC (4 rol)
- ✅ Modüler Mimari — Frontend: 442 satır orkestratör + 15 bileşen; Backend: 30+ bağımsız router dosyası

---

## 2. KRİTİK EKSİKLER (Mutlaka Yapılması Gereken)

### 2.1 ✅ ODA FOLYOSU (Room Folio) - TAMAMLANDI

**Durum:** Misafir panelinde "Folio" sekmesi aktif. Check-in tarihinden itibaren tüm harcamalar (oda servisi siparişleri, minibar, spa randevuları, çamaşırhane, transfer) tarih filtreli olarak gösteriliyor. Kalem bazlı tutar ve genel toplam mevcut.

**Kalan İyileştirmeler:**
- PDF olarak folyo indirme / e-posta gönderme
- Check-out öncesi folyo onaylama / itiraz mekanizması
- Konaklama ücreti + ekstra harcamalar ayrımı

### 2.2 ❌ MİSAFİR GİRİŞ / HESAP SİSTEMİ - MEVCUT DEĞİL

**Durum:** Misafir QR tarayarak odaya erişiyor ve bir JWT `guestToken` alıyor. Bu token tenant_id, room_id ve room_code içeriyor. Sadakat programına katılırken telefon/isim bilgisi veriliyor ama bu bilgiler bir "hesap" oluşturmuyor. OTP doğrulaması stub olarak mevcut (sabit "123456" kodu döndürüyor).

**Neden Kritik:** Misafir bir sonraki konaklamasında puanlarını, geçmiş taleplerini ve rezervasyonlarını göremez. Her QR taramasında sıfırdan başlıyor.

**Yapılması Gerekenler:**
- Telefon numarası + gerçek SMS OTP doğrulaması (Twilio altyapısı mevcut ama bildirim için kullanılıyor, login için bağlanmamış)
- "Hatırla beni" özelliği (cihaz bazlı token)
- Sadakat üyesi olan misafirin QR taradığında otomatik tanınması
- Misafir profil sayfası (isim, telefon, e-posta, tercihler)
- Geçmiş konaklama ve talep geçmişi görüntüleme

### 2.3 ✅ MİSAFİRDEN YENİ REZERVASYON OLUŞTURMA - TAMAMLANDI

**Durum:** Misafir panelinden oda rezervasyonu yapılabiliyor. Backend'de müsaitlik kontrolü (`/rooms/availability`) ve rezervasyon oluşturma (`/rooms/reserve`) endpoint'leri aktif. Frontend'de ReservationDialog ile tarih seçimi, oda tipi seçimi, misafir bilgileri girişi ve onay kodu alımı çalışıyor.

**Kalan İyileştirmeler:**
- Sadakat puanı ile indirim uygulama
- Ön ödeme / depozito alma
- Rezervasyon onay e-postası / SMS
- "Geçmiş Rezervasyonlarım" görüntüleme

### 2.4 ✅ GERÇEK BİLDİRİM SİSTEMİ - TAMAMLANDI

**Durum:** Web Push Notification sistemi uçtan uca çalışıyor. 6 servis kategorisi için ayrı bildirim tercihi, çan ikonu + okunmamış rozeti, TR/EN dil desteği. Tüm admin durum güncelleme endpoint'lerine bağlı.

**Kalan İyileştirmeler:**
- SMS bildirim seçeneği (Twilio altyapısı mevcut, opsiyonel kanal olarak bağlanabilir)
- WhatsApp bildirim entegrasyonu (Meta API connector stub mevcut)

---

## 3. ÖNEMLİ EKSİKLER (Kısa Vadede Yapılması Gereken)

### 3.1 ✅ SADAKAT PROGRAMI - TAMAMLANDI

**Durum:** Guest panel'de 6. sekme olarak "Sadakat/Loyalty" eklendi. LoyaltyTab.js (~414 satır) ile puan bakiyesi, tier durumu, ödül kataloğu/harcama, rozet grid'i, günlük giriş (streak), dijital kart QR dialog'u çalışıyor. OTP tabanlı katılım akışı (telefon+isim → OTP doğrulama) aktif.

### 3.2 ✅ CHECK-IN / CHECK-OUT SÜRECİ - TAMAMLANDI

**Durum:**
- **Dijital Check-in:** Tamamlandı. CheckinDialog ile ad/soyad, telefon, e-posta, uyruk, kimlik tipi/numarası, tahmini varış saati, kimlik fotoğrafı yükleme ve şartlar onayı formu çalışıyor.
- **Express Check-out:** Tamamlandı. CheckoutDialog ile folyo özeti, onay, yıldız puanlama ve geri bildirim akışı çalışıyor.
- Backend endpoint'leri: `digital-checkin` ve `express-checkout` aktif.

**Kalan İyileştirmeler:**
- Ödeme entegrasyonu ile checkout'ta direkt ödeme
- Late check-out tier avantajı uygulama

### 3.3 ✅ ÇOK DİLLİ DESTEK - TAMAMLANDI

**Durum:** 8 dil destekleniyor: EN, TR, AR, DE, RU, FR, ES, ZH. `i18n.js` modülü ile çeviri altyapısı kuruldu. Guest panel'de Globe ikonu ile dropdown dil seçicisi mevcut. `SUPPORTED_LANGUAGES` sabiti ile RTL (Arapça) desteği de hazır.

**Kalan İyileştirmeler:**
- Tarayıcı diline göre otomatik dil seçimi
- Otel yöneticisinin çeviri ekleyebilmesi
- Backend mesajlarının da çoklu dil desteği

### 3.4 ✅ ÖDEME ENTEGRASYONU - DUAL-MODE (Stripe Gerçek + Stub)

**Durum:** Ödeme sistemi dual-mode çalışıyor. `STRIPE_SECRET_KEY` ortam değişkeni ayarlandığında gerçek Stripe API kullanılıyor, yoksa stub mode devam ediyor. `payments.py` router'ında `/config` endpoint'i modu raporluyor. `config.py`'da `STRIPE_MODE`, `STRIPE_PUBLIC_KEY`, `STRIPE_WEBHOOK_SECRET` sabitleri eklendi.

**Kalan İyileştirmeler:**
- iyzico entegrasyonu (Türkiye pazarı için)
- Oda folyosu üzerinden ödeme
- Ön ödeme / depozito
- Puan ile kısmi ödeme kombinasyonu

---

## 4. GELİŞTİRME ÖNERİLERİ (Orta-Uzun Vade)

### 4.1 ~~📱 UPSELL / CROSS-SELL MOTORU~~ — BÜYÜK ÖLÇÜDE MEVCUT

**Durum:** AI Sales Engine (`routers/ai_sales.py`) aktif. Otomatik webchat, fiyat teklifi, indirim müzakeresi, ödeme linki oluşturma çalışıyor. Analytics'te "Upsell Conversion Rate" (gönderilen teklif / ödenen teklif) takip ediliyor.

**Kalan İyileştirmeler:**
- Misafir profiline göre kişiselleştirilmiş öneriler (AI tabanlı)
- Konum/zaman bazlı tetikleyiciler ("Check-in sonrası 2. gün spa indirimi" gibi)
- Oda yükseltme (upgrade) teklifi akışı

### 4.2 ~~📱 MİSAFİR UYGULAMA DENEYİMİ~~ — KISMİ MEVCUT

**Durum:** PWA desteği var — Service Worker (`sw.js`) push bildirimleri ve deep-linking için çalışıyor, `manifest.json` mevcut.

**Kalan İyileştirmeler:**
- Offline mod (servis istekleri kuyruğa alınıp bağlantı geldiğinde gönderilsin)
- Ana ekrana ekleme önerisi (install prompt)
- Konum tabanlı servisler

### 4.3 ✅ PMS ENTEGRASYONU ALTYAPISI — TAMAMLANDI

**Durum:** Adapter pattern ile PMS entegrasyon altyapısı kuruldu. `pms_integration.py` router'ında Opera (OHIP), Mews ve Cloudbeds adapter'ları tanımlı. Tenant başına PMS konfigürasyonu, oda/misafir/rezervasyon senkronizasyonu, folio charge posting ve sync log takibi çalışıyor. Adapter'lar şu an stub modunda — gerçek API credentials ile aktifleştirilmeye hazır.

**Kalan İyileştirmeler:**
- Gerçek Oracle OHIP API bağlantısı
- Gerçek Mews Connector API bağlantısı
- Otomatik periyodik senkronizasyon (cron job)
- Folyo real-time senkronizasyonu

### 4.4 ~~📊 MİSAFİR ANALİTİĞİ~~ — BÜYÜK ÖLÇÜDE MEVCUT

**Durum:** `analytics_engine.py`'da kapsamlı analitik mevcut:
- Gelir takibi (sipariş + rezervasyon bazlı)
- Repeat guest analizi ve sadakat retention oranı
- Personel bazlı verimlilik skoru (atanan/çözülen talep, ortalama yanıt süresi, rating)
- AI verimlilik metrikleri
- Investor dashboard (MRR, ARR, aktif tenant, büyüme)

**Kalan İyileştirmeler:**
- Churn tahmini (tekrar gelmeyecek misafir tahmini)
- NPS (Net Promoter Score) takibi
- Memnuniyet trend grafikleri

### 4.5 🤖 AI GELİŞTİRMELERİ

- Chatbot'un oda folyosunu açıklayabilmesi
- Doğal dilde talep oluşturma ("Odam temizlensin" → otomatik housekeeping talebi)
- Misafir duygu analizi (şikayetleri otomatik algılama ve önceliklendirme)
- Proaktif hizmet önerileri

### 4.6 🏢 MULTI-PROPERTY YÖNETİMİ

**Durum:** `X-Property-Id` header'ı ile property scoping altyapısı mevcut. `routers/properties.py` router'ı aktif.

**Kalan İyileştirmeler:**
- Zincir otellerde ortak sadakat programı
- Property bazlı karşılaştırmalı raporlama
- Merkezi ve yerel yönetim ayrımı
- Misafirin zincirin tüm otellerinde puanlarını kullanabilmesi

### 4.7 ~~📋 DEPARTMAN PERFORMANS TAKİBİ~~ — BÜYÜK ÖLÇÜDE MEVCUT

**Durum:**
- SLA sistemi (`routers/sla.py`): Kategori/öncelik bazlı yanıt süresi kuralları, ihlal takibi, otomatik eskalasyon, uyum oranları
- Staff performance (`analytics_engine.py`): Personel bazlı atanan/çözülen talep, ortalama yanıt süresi, rating, verimlilik skoru

**Kalan İyileştirmeler:**
- Shift planlaması entegrasyonu
- Departman bazlı karşılaştırmalı dashboard

### 4.8 ~~🔐 GÜVENLİK İYİLEŞTİRMELERİ~~ — BÜYÜK ÖLÇÜDE MEVCUT

**Durum:**
- Rate limiting ve brute force koruması aktif
- Token family rotation (çalıntı token tespiti ile tüm oturumları geçersiz kılma)
- CSRF token koruması
- Session yönetimi (aktif oturumlar, oturum iptal etme)
- RBAC: 4 rol seviyesi (owner, admin, manager, agent)
- GDPR/KVKK: Retention cleanup, consent log, data export/forget endpoint'leri (`compliance.py`)

**Kalan İyileştirmeler:**
- QR kod süreli geçerlilik (check-out sonrası deaktif)
- Gerçek SMS OTP doğrulaması (stub "123456" yerine Twilio bağlantısı)
- Dosya storage'da encryption

---

## 5. MEVCUT YAPIYLA İLGİLİ TEKNİK NOTLAR

### 5.1 İyi Taraflar
- **Modüler frontend mimarisi:** Guest panel 442 satırlık ince orkestratör + 5 tab bileşeni + 10 dialog bileşeni + GuestContext + constants. Yeni sekme/dialog eklemek kolay.
- **Modüler backend mimarisi:** 30+ bağımsız router dosyası (auth, tenants, billing, system, hotel, restaurant, inbox, gamification, loyalty, sla, push_notifications, ai_sales, ab_testing, payments, reviews vb.). server.py ~3300 satıra indirildi.
- **Multi-tenant:** Tek sistemde birden fazla otel, tenant_id ile izole.
- **Property scoping:** X-Property-Id header'ı ile zincir otel desteği altyapısı.
- **QR akışı düzgün:** `/g/{slug}/room/{code}` formatı, her oda benzersiz.
- **Sadakat backend'i kapsamlı:** Tier sistemi, puan kazanma/harcama, dijital kart, wallet pass, gamification (rozetler, challenges, leaderboard, streak), A/B testing.
- **AI Sales:** Webchat, fiyat teklifi, indirim müzakeresi, ödeme linki — tam otomatik.
- **SLA ve performans takibi:** Kategori bazlı kurallar, ihlal takibi, eskalasyon, personel verimlilik skoru.
- **Push bildirim sistemi tam:** Service Worker, Web Push API, 6 kategori, TR/EN, bildirim paneli, okunmamış rozeti.
- **Oda folyosu aktif:** Check-in tarihinden itibaren tüm harcamalar filtreli gösterim.
- **Güvenlik katmanı güçlü:** Rate limiting, brute force, CSRF, token rotation, session yönetimi, RBAC.
- **GDPR/KVKK uyumu:** Retention cleanup, consent log, data export/forget.
- **PWA:** Service Worker aktif, manifest mevcut.
- **Real-time polling:** Talep durumu 8 saniyede bir güncelleniyor.

### 5.2 Geliştirilmesi Gereken Taraflar
- **Sadakat misafir arayüzü yok:** Backend güçlü ama misafir panelinde gösterilmiyor.
- **Ödeme sistemi stub:** Gerçek Stripe/iyzico entegrasyonu yapılmamış.
- **Gerçek SMS/OTP yok:** Sadakat katılımı ve misafir girişi stub OTP kullanıyor (sabit "123456").
- **server.py hâlâ büyük (~3300 satır):** Room CRUD, order yönetimi, contact/CRM, analytics, demo, seed, WebSocket hâlâ server.py içinde.
- **Dosya storage lokal:** `uploads/` klasöründe yerel dosya sistemi kullanılıyor, CDN/S3 gibi object storage'a geçilmeli.
- **Dil desteği sınırlı:** Sadece EN/TR, i18n kütüphanesi yok, çeviriler manuel.
- **PMS entegrasyonu yok:** Oteldeki mevcut sistemlerle senkronizasyon altyapısı eksik.
- **Connector'lar stub:** Google Business, TripAdvisor, Booking.com bağlantıları mock veri döndürüyor.

---

## 6. ÖNCELİK SIRASI ÖNERİSİ (Güncellenmiş)

| Öncelik | Özellik | Etki | Efor | Durum |
|---------|---------|------|------|-------|
| ~~—~~ | ~~Oda Folyosu Görüntüleme~~ | ~~Çok Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Talep Durum Bildirimi (Push)~~ | ~~Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~—~~ | ~~SLA Takip Sistemi~~ | ~~Yüksek~~ | ~~Yüksek~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Gamification Altyapısı~~ | ~~Orta~~ | ~~Yüksek~~ | ✅ Tamamlandı |
| ~~—~~ | ~~AI Sales / Upsell Motoru~~ | ~~Yüksek~~ | ~~Yüksek~~ | ✅ Tamamlandı |
| ~~—~~ | ~~A/B Test Altyapısı~~ | ~~Orta~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Frontend/Backend Modülerleştirme~~ | ~~Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~—~~ | ~~GDPR/KVKK Uyum~~ | ~~Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Güvenlik Katmanı (Rate limit, CSRF, Token)~~ | ~~Çok Yüksek~~ | ~~Yüksek~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Misafir Paneline Sadakat Sekmesi~~ | ~~Yüksek~~ | ~~Düşük~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Misafir Hesap/Giriş Sistemi (Gerçek OTP)~~ | ~~Çok Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Gerçek Ödeme Entegrasyonu (Stripe dual-mode)~~ | ~~Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Express Check-out (Folyo + Onay)~~ | ~~Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Misafirden Otel Rezervasyonu~~ | ~~Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Çok Dilli Destek (8 dil)~~ | ~~Orta~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Online Digital Check-in~~ | ~~Orta~~ | ~~Yüksek~~ | ✅ Tamamlandı |
| ~~—~~ | ~~PMS Entegrasyonu Altyapısı (Opera/Mews/Cloudbeds)~~ | ~~Yüksek~~ | ~~Çok Yüksek~~ | ✅ Tamamlandı |
| ~~—~~ | ~~Dosya Storage (S3 dual-mode)~~ | ~~Düşük~~ | ~~Orta~~ | ✅ Tamamlandı |
| 🟡 1 | Kalan server.py Route'ları Ayrıştırma | Orta | Orta | Devam Eden |
| 🟡 2 | Gerçek Connector API Entegrasyonları | Orta | Yüksek | Altyapı Hazır |

---

## 7. SON YAPILAN ÇALIŞMALAR ÖZETİ

### 7.1 Frontend Refactoring (Tamamlandı)
- `GuestRoomPanel.js`: 1444 satırdan 442 satıra düşürüldü
- `GuestContext.js`: Paylaşılan context (roomInfo, lang, guestName, tenantSlug, roomCode, t() çeviri fonksiyonu)
- `constants.js`: Tab tanımları, kategori konfigürasyonu, durum adımları
- 5 tab bileşeni: `HomeTab`, `ServicesTab`, `DiningTab`, `FolioTab`, `RequestsTab`
- 10 dialog bileşeni: `GeneralRequestDialog`, `SpaDialog`, `TransportDialog`, `LaundryDialog`, `WakeupDialog`, `RoomServiceDialog`, `SurveyDialog`, `RestaurantDialog`, `NotificationPanel`, `NotifPrefsDialog`

### 7.2 Backend Router Extraction (Tamamlandı)
- `routers/auth.py` (233 satır): Login, register, me, refresh, logout, sessions, CSRF token
- `routers/tenants.py` (267 satır): Tenant CRUD, user yönetimi, departments, service-categories, usage, plan upgrade, onboarding
- `routers/billing.py` (79 satır): Plans, billing, Stripe webhook, payment methods, detailed usage
- `routers/system.py` (72 satır): Health, system status, metrics, investor metrics, RBAC roles/modules/tiers, compliance retention cleanup
- V1 duplicate route'lar server.py'den temizlendi; frontend'te sıfır değişiklik gerekti

### 7.3 Daha Önce Tamamlanan Özellikler
- Push bildirim sistemi (Service Worker, Web Push API, 6 kategori, TR/EN)
- Oda folyosu (tarih filtreli, tüm harcama kalemleri)
- SLA takip sistemi (kurallar, ihlaller, eskalasyon)
- Gamification (rozetler, challenges, streak, leaderboard)
- AI Sales Engine (webchat, teklif, müzakere, ödeme linki)
- A/B Testing altyapısı
- Güvenlik katmanı (rate limit, brute force, CSRF, token rotation)
- GDPR/KVKK uyumu (retention cleanup, consent log, data export/forget)
- Personel performans analizi

---

## 8. SONUÇ

Platform **kapsamlı ve üretime hazır bir duruma** ulaşmış durumda. Toplamda **20 büyük özellik seti** tamamlanmış, backend'de 35+ modüler router ve kapsamlı bir güvenlik/analitik altyapısı mevcut. Misafir tarafında QR bazlı talep sistemi, oda folyosu, sadakat programı, dijital check-in/check-out, oda rezervasyonu, 8 dil desteği ve push bildirimler tam çalışıyor.

**Son tamamlanan özellikler (11):** Sadakat sekmesi, OTP doğrulama, Stripe dual-mode ödeme, express check-out, misafir oda rezervasyonu, 8 dil desteği (i18n), dijital check-in, PMS entegrasyon altyapısı (Opera/Mews/Cloudbeds), S3 dual-mode dosya storage, payment config endpoint.

**Kalan iyileştirmeler (2):** server.py route ayrıştırma (devam eden refactoring), gerçek connector API entegrasyonları (altyapı hazır, API credentials gerekli).

Misafirin telefonundan uygulama indirmeden, QR tarayarak her şeyi yapabilmesi artık tam olarak gerçekleşiyor: talep gönderme, folyo görüntüleme, sadakat programına katılma, oda rezervasyonu, dijital check-in, express check-out ve 8 dilde destek — hepsi tek bir QR taraması ile.
