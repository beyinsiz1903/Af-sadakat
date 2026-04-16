# OmniHub - İş Fikri Değerlendirme ve Geliştirme Raporu

**Tarih:** 16 Nisan 2026  
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

---

## 2. KRİTİK EKSİKLER (Mutlaka Yapılması Gereken)

### 2.1 ❌ ODA FOLYOSU (Room Folio) - MEVCUT DEĞİL

**Durum:** Backend'de `/folio` endpoint'i yok. Misafir oda masraflarını göremiyor.

**Neden Kritik:** Bu, otel misafirleri için en temel beklentilerden biri. Misafir odasında ne kadar harcama yaptığını (minibar, oda servisi, çamaşırhane, spa vb.) görebilmeli.

**Yapılması Gerekenler:**
- Misafirin tüm harcamalarını (oda servisi, minibar, spa, restoran, çamaşırhane) birleşik bir "Oda Folyosu" ekranında gösterme
- Harcama kalemleri, tarih, tutar ve toplam gösterimi
- Konaklama ücreti + ekstra harcamalar ayrımı
- Ödeme durumu gösterimi (açık hesap / ödendi)
- Check-out öncesi folyo onaylama / itiraz mekanizması
- PDF olarak folyo indirme/e-posta gönderme

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

### 2.4 ❌ GERÇEK BİLDİRİM SİSTEMİ - EKSİK

**Durum:** Talep durumu değiştiğinde misafirin haberi olmuyor. Push notification altyapısı var ama misafir tarafına bağlı değil.

**Neden Kritik:** "Teknik ekip odanıza geldi", "Çamaşırlarınız hazır", "Siparişiniz yola çıktı" gibi bildirimler misafir memnuniyeti için çok önemli.

**Yapılması Gerekenler:**
- Web Push Notification ile misafire bildirim (talep durum değişikliği)
- SMS bildirim seçeneği (opsiyonel, ücretli)
- WhatsApp bildirim entegrasyonu
- Misafirin bildirim tercihlerini yönetebilmesi

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
- Rate limiting (spam talep engelleme)
- GDPR/KVKK uyumlu veri silme otomasyonu

---

## 5. MEVCUT YAPIYLA İLGİLİ TEKNİK NOTLAR

### 5.1 İyi Taraflar
- **Modüler mimari:** V2 router yapısı ile her modül bağımsız. Yeni özellik eklemek kolay.
- **Multi-tenant:** Tek sistemde birden fazla otel barındırma altyapısı hazır.
- **QR akışı düzgün:** `/g/{slug}/room/{code}` formatı güzel, her oda benzersiz.
- **Departman yönlendirme:** Talep kategorisine göre otomatik departman ataması çalışıyor.
- **Sadakat backend'i güçlü:** Tier sistemi, puan kazanma/harcama, dijital kart, wallet pass altyapısı mevcut.
- **Real-time polling:** Talep durumu 8 saniyede bir güncelleniyor.

### 5.2 Geliştirilmesi Gereken Taraflar
- **Guest panel 1130 satır tek dosya:** Bu dosya çok büyük. Servis bazlı bileşenlere bölünmeli.
- **Backend server.py 3800+ satır:** Monolitik yapı. Modüler router'lara taşınmaya devam edilmeli.
- **Gerçek SMS/OTP yok:** Sadakat katılımı stub OTP kullanıyor.
- **WebSocket yok:** Anlık bildirim için polling kullanılıyor, WebSocket daha verimli olur.
- **Fotoğraf/dosya storage:** Şu an veritabanında saklanıyor, CDN/S3 gibi object storage kullanılmalı.

---

## 6. ÖNCELİK SIRASI ÖNERİSİ

| Öncelik | Özellik | Etki | Efor |
|---------|---------|------|------|
| 🔴 1 | Misafir Hesap/Giriş Sistemi (OTP) | Çok Yüksek | Orta |
| 🔴 2 | Oda Folyosu Görüntüleme | Çok Yüksek | Orta |
| 🔴 3 | Misafir Paneline Sadakat Sekmesi | Yüksek | Düşük |
| 🟡 4 | Talep Durum Bildirimi (Push) | Yüksek | Orta |
| 🟡 5 | Misafirden Yeni Rezervasyon | Yüksek | Orta |
| 🟡 6 | Online Check-in/Check-out | Yüksek | Yüksek |
| 🟡 7 | Gerçek Ödeme Entegrasyonu | Yüksek | Yüksek |
| 🟢 8 | Çok Dilli Destek Genişletme | Orta | Düşük |
| 🟢 9 | Upsell/Cross-sell Motoru | Orta | Yüksek |
| 🟢 10 | PMS Entegrasyonu | Yüksek | Çok Yüksek |

---

## 7. SONUÇ

Platform **çekirdeği iyi kurgulanmış** bir durumda. QR bazlı talep sistemi, çok departmanlı yönlendirme, sadakat altyapısı ve çoklu hizmet desteği güçlü. Ancak vizyonun tam olarak hayata geçmesi için **misafir hesap sistemi, oda folyosu ve misafir tarafında sadakat gösterimi** gibi kritik eksikler kapatılmalı.

En büyük rekabet avantajı, misafirin telefonundan uygulama indirmeden, QR tarayarak her şeyi yapabilmesi olacak. Bu deneyimi kusursuz hale getirmek için yukarıdaki öncelik sırasına göre ilerlenebilir.
