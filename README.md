# 🟢 Kick.com Canlı Yayın Bildirim Botu (Telegram)

### 🚀 Temel Özellikler
* **Anlık Takip (Real-Time Monitoring):** Kick'in dahili API'si üzerinden yayıncı durumunu anlık olarak kontrol eder.
* **Hızlı Bildirimler:** Yayın başladığı anda Telegram Bot API aracılığıyla doğrudan mesaj gönderir.
* **Durum Yönetimi (State Management):** Yayın durumunu takip etmek için yerel bir **SQLite** veritabanı (`db.sqlite3`) kullanır. Bu mantık, internet kesintilerinde veya bot yeniden başladığında bildirim spam'i yapılmasını engeller.
* **Arka Planda Sessiz Çalışma:** Özel **VBScript** ve **Batch file** konfigürasyonu sayesinde, ekranda terminal penceresi açık kalmadan arka planda (background process) çalışır.

### 🛠️ Teknolojiler
* **Dil:** Python 3.11.9
* **Veri & Depolama:** SQLite3
* **API'ler:** Kick Internal API, Telegram Bot API
* **OS Entegrasyonu:** Windows Batch (`.bat`), VBScript (`.vbs`)
* **Kütüphaneler:** `requests`, `json`, `sqlite3`, `time`

### 📂 Dosya Yapısı ve İşlevleri
* `bot.py`: Ana döngü ve karar mekanizması. API isteklerini yönetir ve bildirim tetikler.
* `kick_api.py`: Kick.com'un veri yapısını işlemek için yazdığım özel modül.
* `database.py`: Tüm SQL işlemlerini yönetir. Veritabanı bağlantılarını ve imleç (cursor) mantığını daha iyi kavramak için ham SQL sorguları kullandım.
* `run_invisible.vbs`: Botu siyah komut ekranı açmadan çalıştırmayı sağlayan script (Kullanıcı Deneyimi iyileştirmesi).
* `config_example.py`: API anahtarları için şablon dosyası. **(Güvenlik Notu: Kendi gerçek anahtarlarım yerel bilgisayarımda gizlidir.)**

### ⚙️ Nasıl Çalıştırılır?
**Projeyi Klonlayın ve Zip Olarak İndirin:**

**Ayarları Yapın:**
config_example.py dosyasının adını config.py olarak değiştirin ve içine kendi Telegram Token ve Chat ID bilgilerinizi girin.

**Çalıştırın:**

Logları görmek isterseniz run_bot.bat dosyasına çift tıklayın.

VEYA tamamen gizli çalışması için run_invisible.vbs dosyasına çift tıklayın.
