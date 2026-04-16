# OmniHub - İş Fikri Değerlendirme ve Geliştirme Raporu

**Tarih:** 16 Nisan 2026  
**Son Güncelleme:** 16 Nisan 2026 (Modüler refactoring sonrası)  
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
- ✅ **Oda Folyosu** — Misafir konaklama süresince tüm harcamalarını (oda servisi, minibar, spa, çamaşırhane, transfer) tarih filtreli olarak görebiliyor
- ✅ **Misafir Push Bildirimleri** — Talep durum değişikliklerinde Web Push ile anlık bildirim (TR/EN), kategori bazlı bildirim tercih yönetimi, uygulama içi bildirim paneli ve okunmamış rozeti
- ✅ **Modüler Frontend Mimarisi** — Guest panel 442 satır orkestratör + 5 tab bileşeni + 10 dialog bileşeni + paylaşılan context/sabitler olarak ayrıştırıldı
- ✅ **Modüler Backend Mimarisi** — Auth, tenant, billing, system route'ları bağımsız router dosyalarına taşındı; server.py ~3300 satıra indirildi

---

## 2. KRİTİK EKSİKLER (Mutlaka Yapılması Gereken)

### 2.1 ~~❌~~ ✅ ODA FOLYOSU (Room Folio) - TAMAMLANDI

**Durum:** Misafir panelinde "Folio" sekmesi aktif. Check-in tarihinden itibaren tüm harcamalar (oda servisi siparişleri, minibar, spa randevuları, çamaşırhane, transfer) tarih filtreli olarak gösteriliyor. Kalem bazlı tutar ve genel toplam mevcut.

**Kalan İyileştirmeler:**
- PDF olarak folyo indirme / e-posta gönderme
- Check-out öncesi folyo onaylama / itiraz mekanizması
- Konaklama ücreti + ekstra harcamalar ayrımı

### 2.2 ❌ MİSAFİR GİRİŞ / HESAP SİSTEMİ - MEVCUT DEĞİL

**Durum:** Misafir QR ile odaya erişiyor ama bir "hesabı" yok. Sadakat programına katılsa bile tekrar girdiğinde bilgilerini göremiyor.

**Neden Kritik:** Misafir bir sonraki konaklamasında da puanlarını görmek, geçmiş konaklamalarını görmek ve yeni rezervasyon yapmak isteyecek. QR sadece o anlık oda erişimi sağlıyor.

**Yapılması Gerekenler:**
- Telefon numarası + OTP (SMS doğrulama) ile misafir girişi
- "Hatırla beni" özelliği (cihaz bazlı token)
- Sadakat üyesi olan misafirin QR taradığında otomatik tanınması
- Misafir profil sayfası (isim, telefon, e-posta, tercihler)
- Geçmiş konaklama ve talep geçmişi görüntüleme

### 2.3 ❌ MİSAFİRDEN YENİ REZERVASYON OLUŞTURMA - MEVCUT DEĞİL

**Durum:** Misafir panelinde "yeni otel rezervasyonu oluşturma" özelliği bulunmuyor. Sadece restoran rezervasyonu var.

**Neden Kritik:** Mevcut misafir "bir dahaki sefere de gelmek istiyorum" dediğinde doğrudan sistem üzerinden rezervasyon yapabilmeli.

**Yapılması Gerekenler:**
- Misafir portalından tarih ve oda tipi seçerek konaklama talebi oluşturma
- Müsaitlik kontrolü
- Sadakat puanı ile indirim uygulama
- Ön ödeme / depozito alma (payment link)
- Rezervasyon onay e-postası / SMS
- "Geçmiş Rezervasyonlarım" görüntüleme

### 2.4 ~~❌~~ ✅ GERÇEK BİLDİRİM SİSTEMİ - TAMAMLANDI

**Durum:** Web Push Notification sistemi uçtan uca çalışıyor. Misafir QR panelinde çan ikonu üzerinden bildirim paneline erişiyor, okunmamış bildirim rozeti gösteriyor. 6 servis kategorisi (housekeeping, oda servisi, spa, çamaşırhane, transfer, uyandırma) için ayrı ayrı bildirim tercihi yönetilebiliyor. Talep durumu her değiştiğinde (yeni → atandı → devam ediyor → tamamlandı) otomatik push gönderiliyor. Bildirimler TR ve EN dillerinde ("Çamaşırlarınız hazır", "Your order is on the way").

**Kalan İyileştirmeler:**
- SMS bildirim seçeneği (opsiyonel, ücretli)
- WhatsApp bildirim entegrasyonu (Meta API bağlantısı mevcut ama misafir tarafına henüz bağlanmadı)

---

## 3. ÖNEMLİ EKSİKLER (Kısa Vadede Yapılması Gereken)

### 3.1 ⚠️ SADAKAT PROGRAMI - MİSAFİR TARAFINDA GÖSTERİM EKSİK

**Durum:** Backend'de dijital kart, puan ledger, ödül kataloğu var. Ama misafir QR panelinde bunları görecek bir arayüz yok.

**Yapılması Gerekenler:**
- Guest Room Panel'e "Sadakat" sekmesi eklenmeli
- Puan bakiyesi, tier durumu, sonraki tier'e kalan puan gösterimi
- Puan geçmişi (ne zaman, ne kadar kazandı/harcadı)
- Ödül kataloğu görüntüleme ve puan harcama (redeem)
- Dijital kart gösterimi (QR kod dahil)
- Tier avantajları listesi

### 3.2 ⚠️ CHECK-IN / CHECK-OUT SÜRECİ - MEVCUT DEĞİL

**Durum:** "Express Check-out" butonu var ama sadece bir talep oluşturuyor. Gerçek bir dijital check-in/check-out akışı yok.

**Yapılması Gerekenler:**
- **Online Check-in:** Varıştan önce kimlik bilgileri, pasaport fotoğrafı yükleme, form doldurma
- **Express Check-out:** Folyo kontrolü + onay + ödeme + anahtar bırakma talimatı
- PMS (Property Management System) entegrasyon altyapısı

### 3.3 ⚠️ ÇOK DİLLİ DESTEK YETERSİZ

**Durum:** Sadece EN ve TR var. Turistik oteller için daha fazla dil lazım.

**Yapılması Gerekenler:**
- Arapça (AR), Almanca (DE), Rusça (RU), Fransızca (FR), İspanyolca (ES), Çince (ZH) gibi yaygın turist dilleri
- Tarayıcı diline göre otomatik dil seçimi
- Otel yöneticisinin çeviri ekleyebilmesi

### 3.4 ⚠️ GERÇEK ÖDEME ENTEGRASYONU - STUB DURUMDA

**Durum:** Ödeme sistemi "STRIPE_STUB" olarak çalışıyor. Gerçek ödeme alınamıyor.

**Yapılması Gerekenler:**
- Stripe veya iyzico gerçek entegrasyonu
- Oda folyosu ödemesi
- Ön ödeme / depozito
- Puan ile kısmi ödeme kombinasyonu

---

## 4. GELİŞTİRME ÖNERİLERİ (Orta-Uzun Vade)

### 4.1 📱 UPSELL / CROSS-SELL MOTORU

Misafir konaklaması sırasında kişiselleştirilmiş öneriler:
- "Bugün spa'da %20 indirim! Hemen rezervasyon yapın" (check-in sonrası 2. gün)
- "Yarın akşam Boğaz manzaralı restoranda yerinizi ayırtın"
- "Oda yükseltme fırsatı: Suite'e sadece 500 TRY farkla geçin"
- AI tabanlı öneri motoru (misafir profiline göre)
- Konum/zaman bazlı tetikleyiciler

### 4.2 📱 MİSAFİR UYGULAMA DENEYİMİ

- PWA (Progressive Web App) olarak offline destek
- Ana ekrana ekleme önerisi
- Kamera ile QR tarama (oda değişikliğinde)
- Konum tabanlı servisler (havuz/spa/restoran yakınlığı)

### 4.3 🏨 PMS ENTEGRASYONU

- Opera, Protel, Mews, Cloudbeds gibi PMS'lerle oda/misafir senkronizasyonu
- Otomatik check-in/check-out bilgisi
- Oda durumu real-time güncelleme
- Folyo senkronizasyonu

### 4.4 📊 MİSAFİR ANALİTİĞİ

- Misafir davranış analizi (hangi servisleri kullanıyor, ne zaman, ne sıklıkta)
- Memnuniyet trendleri
- Repeat guest analizi
- Churn tahmini (tekrar gelmeyecek misafir tahmini)
- NPS (Net Promoter Score) takibi

### 4.5 🤖 AI GELİŞTİRMELERİ

- Chatbot'un oda folyosunu açıklayabilmesi
- Doğal dilde talep oluşturma ("Odam temizlensin" → otomatik housekeeping talebi)
- Misafir duygu analizi (şikayetleri otomatik algılama ve önceliklendirme)
- Proaktif hizmet önerileri

### 4.6 🏢 MULTI-PROPERTY YÖNETİMİ

- Zincir otellerde ortak sadakat programı
- Property bazlı raporlama
- Merkezi ve yerel yönetim ayrımı
- Misafirin zincirin tüm otellerinde puanlarını kullanabilmesi

### 4.7 📋 DEPARTMAN PERFORMANS TAKİBİ

- Talep yanıt süreleri departman bazlı karşılaştırma
- SLA uyum oranları
- Personel bazlı performans
- Shift planlaması entegrasyonu

### 4.8 🔐 GÜVENLİK İYİLEŞTİRMELERİ

- QR kod süreli geçerlilik (check-out sonrası deaktif)
- Misafir OTP doğrulaması SMS ile (şu an stub "123456")
- GDPR/KVKK uyumlu veri silme otomasyonu (compliance modülü mevcut, retention-cleanup endpoint'i aktif)

---

## 5. MEVCUT YAPIYLA İLGİLİ TEKNİK NOTLAR

### 5.1 İyi Taraflar
- **Modüler frontend mimarisi:** Guest panel artık 442 satırlık ince bir orkestratör. 5 tab bileşeni (HomeTab, ServicesTab, DiningTab, FolioTab, RequestsTab), 10 dialog bileşeni ve paylaşılan GuestContext/constants ile temiz bir yapı.
- **Modüler backend mimarisi:** Auth, tenant CRUD, billing ve system route'ları bağımsız router dosyalarına (`routers/auth.py`, `routers/tenants.py`, `routers/billing.py`, `routers/system.py`) taşındı. server.py ~3300 satıra düşürüldü. Toplam 30+ modüler router dosyası mevcut.
- **Multi-tenant:** Tek sistemde birden fazla otel barındırma altyapısı hazır.
- **QR akışı düzgün:** `/g/{slug}/room/{code}` formatı güzel, her oda benzersiz.
- **Departman yönlendirme:** Talep kategorisine göre otomatik departman ataması çalışıyor.
- **Sadakat backend'i güçlü:** Tier sistemi, puan kazanma/harcama, dijital kart, wallet pass altyapısı, gamification, A/B testing mevcut.
- **Push bildirim sistemi tam:** Service Worker, Web Push API, kategori bazlı tercihler, bildirim paneli, okunmamış rozeti tam çalışıyor.
- **Oda folyosu aktif:** Misafirin tüm konaklama harcamalarını check-in tarihinden itibaren filtreli gösteriyor.
- **Güvenlik katmanı:** Rate limiting, brute force koruması, token family rotation, CSRF token, session yönetimi, RBAC (4 rol seviyesi) mevcut.
- **Real-time polling:** Talep durumu 8 saniyede bir güncelleniyor.

### 5.2 Geliştirilmesi Gereken Taraflar
- ~~**Guest panel 1130 satır tek dosya:**~~ **ÇÖZÜLDÜ** — 442 satır orkestratör + modüler bileşenler olarak ayrıştırıldı.
- ~~**Backend server.py 3800+ satır:**~~ **İYİLEŞTİRİLDİ** — ~3300 satıra düşürüldü. Auth, tenant, billing, system route'ları çıkarıldı. Kalan route'lar (room, order, contact, analytics, demo, WebSocket) da ayrıştırılmaya devam edilebilir.
- **Gerçek SMS/OTP yok:** Sadakat katılımı stub OTP kullanıyor.
- **Fotoğraf/dosya storage:** Şu an veritabanında saklanıyor, CDN/S3 gibi object storage kullanılmalı.
- **server.py'de hâlâ kalan route'lar:** Room CRUD, order yönetimi, contact/CRM, analytics, demo, seed, WebSocket gibi bölümler hâlâ server.py içinde. Bunlar da ayrı router dosyalarına taşınabilir.

---

## 6. ÖNCELİK SIRASI ÖNERİSİ (Güncellenmiş)

| Öncelik | Özellik | Etki | Efor | Durum |
|---------|---------|------|------|-------|
| ~~🔴 1~~ | ~~Oda Folyosu Görüntüleme~~ | ~~Çok Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~🔴 2~~ | ~~Talep Durum Bildirimi (Push)~~ | ~~Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| ~~🔴 3~~ | ~~Frontend/Backend Modülerleştirme~~ | ~~Yüksek~~ | ~~Orta~~ | ✅ Tamamlandı |
| 🔴 1 | Misafir Hesap/Giriş Sistemi (OTP) | Çok Yüksek | Orta | Bekliyor |
| 🔴 2 | Misafir Paneline Sadakat Sekmesi | Yüksek | Düşük | Bekliyor |
| 🟡 3 | Misafirden Yeni Rezervasyon | Yüksek | Orta | Bekliyor |
| 🟡 4 | Online Check-in/Check-out | Yüksek | Yüksek | Bekliyor |
| 🟡 5 | Gerçek Ödeme Entegrasyonu | Yüksek | Yüksek | Bekliyor |
| 🟡 6 | Kalan server.py Route'ları Ayrıştırma | Orta | Orta | Bekliyor |
| 🟢 7 | Çok Dilli Destek Genişletme | Orta | Düşük | Bekliyor |
| 🟢 8 | Upsell/Cross-sell Motoru | Orta | Yüksek | Bekliyor |
| 🟢 9 | PMS Entegrasyonu | Yüksek | Çok Yüksek | Bekliyor |

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
- Spa fiyatlama düzeltmesi
- Duplicate bildirim hatası giderildi

---

## 8. SONUÇ

Platform **çekirdeği güçlü ve modüler bir mimariye** kavuşmuş durumda. QR bazlı talep sistemi, departman yönlendirme, push bildirim, oda folyosu, sadakat altyapısı ve güvenlik katmanları tam çalışıyor. Frontend ve backend'de yapılan modülerleştirme çalışmaları ile kod bakımı ve yeni özellik ekleme çok daha kolay hale geldi.

**Tamamlanan kritik özellikler:** Oda folyosu, push bildirimler, modüler mimari refactoring  
**Kalan en kritik eksik:** Misafir hesap/giriş sistemi (OTP ile), sadakat programının misafir arayüzünde gösterimi

En büyük rekabet avantajı, misafirin telefonundan uygulama indirmeden, QR tarayarak her şeyi yapabilmesi olacak. Bu deneyimi kusursuz hale getirmek için güncellenmiş öncelik sırasına göre ilerlenebilir.
