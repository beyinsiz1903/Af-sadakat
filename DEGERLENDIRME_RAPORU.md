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
- ✅ Çoklu dil desteği (EN/TR)
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

### 2.3 ❌ MİSAFİRDEN YENİ REZERVASYON OLUŞTURMA - MEVCUT DEĞİL

**Durum:** Misafir panelinde restoran rezervasyonu yapılabiliyor (tarih/saat/kişi sayısı/müsaitlik kontrolü tam çalışıyor). Ancak otel oda rezervasyonu yapma özelliği yok. Backend'de admin tarafı için `reservations.py` router'ı mevcut ve teklif kabul edildiğinde otomatik rezervasyon oluşturuyor, ama misafir panelinden doğrudan "oda ayırt" akışı bulunmuyor.

**Yapılması Gerekenler:**
- Misafir portalından tarih ve oda tipi seçerek konaklama talebi oluşturma
- Müsaitlik kontrolü
- Sadakat puanı ile indirim uygulama
- Ön ödeme / depozito alma (payment link altyapısı mevcut)
- Rezervasyon onay e-postası / SMS
- "Geçmiş Rezervasyonlarım" görüntüleme

### 2.4 ✅ GERÇEK BİLDİRİM SİSTEMİ - TAMAMLANDI

**Durum:** Web Push Notification sistemi uçtan uca çalışıyor. 6 servis kategorisi için ayrı bildirim tercihi, çan ikonu + okunmamış rozeti, TR/EN dil desteği. Tüm admin durum güncelleme endpoint'lerine bağlı.

**Kalan İyileştirmeler:**
- SMS bildirim seçeneği (Twilio altyapısı mevcut, opsiyonel kanal olarak bağlanabilir)
- WhatsApp bildirim entegrasyonu (Meta API connector stub mevcut)

---

## 3. ÖNEMLİ EKSİKLER (Kısa Vadede Yapılması Gereken)

### 3.1 ⚠️ SADAKAT PROGRAMI - MİSAFİR TARAFINDA GÖSTERİM EKSİK

**Durum:** Backend'de kapsamlı bir sadakat altyapısı var: Loyalty Engine (puan kazanma/harcama, tier yönetimi, dijital kart), Gamification (rozetler, meydan okumalar, streak, leaderboard), Loyalty Analytics (puan raporları, tier geçişleri). Ancak bunların hiçbiri misafir QR panelinde gösterilmiyor. Guest panel'de 5 sekme var (Home, Services, Dining, Folio, Requests) — "Sadakat/Loyalty" sekmesi yok. Admin panelinde Loyalty Engine sayfası mevcut.

**Yapılması Gerekenler:**
- Guest Room Panel'e "Sadakat" sekmesi eklenmeli
- Puan bakiyesi, tier durumu, sonraki tier'e kalan puan gösterimi
- Puan geçmişi (ne zaman, ne kadar kazandı/harcadı)
- Ödül kataloğu görüntüleme ve puan harcama (redeem)
- Dijital kart gösterimi (QR kod dahil)
- Tier avantajları listesi
- Gamification rozetleri ve meydan okumaları gösterimi

### 3.2 ⚠️ CHECK-IN / CHECK-OUT SÜRECİ - KISMİ

**Durum:**
- **Dijital Check-in:** Yok. Misafir QR tarayarak sisteme giriyor ama kimlik/pasaport yükleme, form doldurma gibi özellikler bulunmuyor. A/B test altyapısında "Check-in Akışı Optimizasyonu" adında bir seed denemesi var, yani planlanan bir özellik.
- **Express Check-out:** Kısmen mevcut. `constants.js`'de "Express Check-out" kategorisi tanımlı ve bir talep oluşturuyor, ancak bu sadece resepsiyona bir servis talebi gönderiyor. Gerçek bir folyo onaylama + ödeme + oda bırakma akışı yok.
- **Tier avantajı:** Gold ve Platinum üyelere "Late Check-out" avantajı tanımlı ama uygulanmıyor.

**Yapılması Gerekenler:**
- **Online Check-in:** Varıştan önce kimlik bilgileri, pasaport fotoğrafı yükleme, form doldurma
- **Express Check-out:** Folyo kontrolü + onay + ödeme + anahtar bırakma talimatı (folyo zaten hazır, ödeme ve onay akışı eklenmeli)
- PMS entegrasyon altyapısı

### 3.3 ⚠️ ÇOK DİLLİ DESTEK YETERSİZ

**Durum:** Sadece EN ve TR var. Dil geçişi frontend'de manuel olarak yönetiliyor (`constants.js`'de `label`/`labelTr` ayrımı). i18next gibi bir kütüphane kullanılmıyor. Backend connector stub'ları da sadece `en` ve `tr` destekliyor.

**Yapılması Gerekenler:**
- i18next veya benzeri bir çeviri kütüphanesi entegrasyonu
- Arapça (AR), Almanca (DE), Rusça (RU), Fransızca (FR), İspanyolca (ES), Çince (ZH) gibi yaygın turist dilleri
- Tarayıcı diline göre otomatik dil seçimi
- Otel yöneticisinin çeviri ekleyebilmesi

### 3.4 ⚠️ GERÇEK ÖDEME ENTEGRASYONU - STUB DURUMDA

**Durum:** Ödeme sistemi `STRIPE_STUB` provider kullanıyor. `payments.py` router'ında mock webhook endpoint'leri (`/webhook/mock/succeed`, `/webhook/mock/fail`) ile ödeme simüle ediliyor. Frontend'deki `PaymentPage.js` de bu mock endpoint'leri çağırarak "İşleniyor" durumu gösteriyor. `billing.py`'da fatura üretimi de mock (`generate_mock_invoices`). iyzico entegrasyonu hiç yok.

**Yapılması Gerekenler:**
- Stripe gerçek API entegrasyonu (webhook handler altyapısı hazır, gerçek Stripe secret key ve imza doğrulaması eklenmeli)
- veya iyzico entegrasyonu (Türkiye pazarı için)
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

### 4.3 🏨 PMS ENTEGRASYONU — MEVCUT DEĞİL

**Durum:** PMS entegrasyonu yok. Sistem "Connectors" altyapısı kullanıyor (`connectors/registry.py`) ama şu an sadece Google Business, TripAdvisor ve Booking.com için review/mesaj stub'ları mevcut. Opera, Protel, Mews gibi PMS'lerle bağlantı bulunmuyor.

**Yapılması Gerekenler:**
- Opera, Protel, Mews, Cloudbeds gibi PMS'lerle oda/misafir senkronizasyonu
- Otomatik check-in/check-out bilgisi
- Oda durumu real-time güncelleme
- Folyo senkronizasyonu

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
| 🔴 1 | Misafir Paneline Sadakat Sekmesi | Yüksek | Düşük | Bekliyor |
| 🔴 2 | Misafir Hesap/Giriş Sistemi (Gerçek OTP) | Çok Yüksek | Orta | Bekliyor |
| 🔴 3 | Gerçek Ödeme Entegrasyonu (Stripe/iyzico) | Yüksek | Orta | Bekliyor |
| 🟡 4 | Express Check-out (Folyo + Ödeme Akışı) | Yüksek | Orta | Bekliyor |
| 🟡 5 | Misafirden Otel Rezervasyonu | Yüksek | Orta | Bekliyor |
| 🟡 6 | Çok Dilli Destek (i18n + Ek Diller) | Orta | Orta | Bekliyor |
| 🟡 7 | Kalan server.py Route'ları Ayrıştırma | Orta | Orta | Bekliyor |
| 🟢 8 | Online Digital Check-in | Orta | Yüksek | Bekliyor |
| 🟢 9 | PMS Entegrasyonu (Opera/Mews) | Yüksek | Çok Yüksek | Bekliyor |
| 🟢 10 | Gerçek Connector Entegrasyonları | Orta | Yüksek | Bekliyor |
| 🟢 11 | Dosya Storage (CDN/S3 Geçişi) | Düşük | Orta | Bekliyor |

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

Platform **çekirdeği güçlü ve modüler bir mimariye** kavuşmuş durumda. Toplamda 9 büyük özellik seti tamamlanmış, backend'de 30+ modüler router ve kapsamlı bir güvenlik/analitik altyapısı mevcut. Misafir tarafında QR bazlı talep sistemi, oda folyosu ve push bildirimler tam çalışıyor.

**Tamamlanan büyük özellikler (9):** Oda folyosu, push bildirimler, SLA takibi, gamification, AI satış motoru, A/B testing, güvenlik katmanı, GDPR uyumu, modüler refactoring.

**Kalan en kritik eksikler (3):** Sadakat sekmesinin misafir paneline eklenmesi (backend hazır, sadece frontend gerekli), gerçek OTP ile misafir hesap sistemi, gerçek ödeme entegrasyonu (Stripe/iyzico).

En büyük rekabet avantajı, misafirin telefonundan uygulama indirmeden, QR tarayarak her şeyi yapabilmesi olacak. Bu deneyimi kusursuz hale getirmek için sadakat gösterimini misafir paneline eklemek ilk adım olarak en düşük eforla en yüksek etkiyi sağlayacaktır.
