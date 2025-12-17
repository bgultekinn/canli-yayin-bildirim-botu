# bot.py
import logging
import sqlite3
import asyncio # kick_api modülümüz asenkron olduğu için botun da asenkron olması şart
from config import TELEGRAM_TOKEN, CHECK_INTERVAL_SECONDS
import kick_api # Kendi yazdığımız Kick API modülümüzü import ediyoruz
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from telegram.constants import ParseMode # Mesajları 'bold' vb. yazmak için

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

DB_NAME = "db.sqlite3" # Veritabanı dosya adı

# --- Veritabanı Yardımcı Fonksiyonları ---
# Sürekli veritabanına bağlanıp kapanmak yerine
# temiz, kısa fonksiyonlar yazmak daha iyidir.

def db_query(query: str, params=()):
    """Veritabanından veri çeker (SELECT)."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        log.error(f"DB SORGUSUNDA HATA (Query): {query} | {e}")
        return []

def db_exec(query: str, params=()):
    """Veritabanına veri yazar (INSERT, UPDATE, DELETE)."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
    except Exception as e:
        log.error(f"DB KOMUTUNDA HATA (Exec): {query} | {e}")
        return False

# --- Bot Komutları ---
# Kullanıcıların '/start', '/add' gibi komutlarına cevap verecek fonksiyonlar.

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutuna cevap verir."""
    chat_id = update.effective_chat.id
    # Kullanıcıyı 'users' tablosuna ekle (zaten varsa hata vermez)
    db_exec("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,))
    
    welcome_text = """
👋 **Kick Yayın Bildirim Botuna Hoş Geldiniz!**

Bu bot, takip etmek istediğiniz Kick yayıncıları canlı yayına geçtiğinde size anında haber verir.

**Kullanılabilir Komutlar:**
/add [yayıncı_adı] - Takip listesine yayıncı ekler. (örn: `/add adinross`)
/remove [yayıncı_adı] - Yayıncıyı takipten çıkarır.
/list - Takip ettiğiniz yayıncıları listeler.
/help - Bu yardım mesajını gösterir.
"""
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help komutuna cevap verir."""
    await start_command(update, context) # Şimdilik /start ile aynı işi yapsın

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/add komutu. Listeye yeni yayıncı ekler."""
    chat_id = update.effective_chat.id
    
    # '/add' komutundan sonra yazılan kelimeyi (yayıncı adı) al
    try:
        streamer_name = context.args[0].lower()
    except (IndexError, ValueError):
        await update.message.reply_text("Kullanım: `/add yayıncı_adı`")
        return

    # 1. Bu yayıncı Kick'te gerçekten var mı? kick_api modülümüzü kullanıyoruz.
    user_info = await kick_api.get_user_info(streamer_name)
    if not user_info:
        await update.message.reply_text(f"❌ `{streamer_name}` adında bir Kick kanalı bulunamadı.", parse_mode=ParseMode.MARKDOWN)
        return
    
    login_name = user_info['login_name'] # URL adı (örn: 'adinross')
    display_name = user_info['display_name'] # Görünen ad (örn: 'AdinRoss')

    # 2. Yayıncıyı ana 'streamers' tablosuna ekle (veritabanı bunu zaten varsa es geçer)
    db_exec("INSERT OR IGNORE INTO streamers (streamer_name, display_name) VALUES (?, ?)", (login_name, display_name))
    
    # 3. Kullanıcıyı bu yayıncıya 'abone' yap (eşleştirme tablosuna ekle)
    success = db_exec("INSERT OR IGNORE INTO subscriptions (chat_id, streamer_name) VALUES (?, ?)", (chat_id, login_name))
    
    if success:
        await update.message.reply_text(f"✅ **{display_name}** (`{login_name}`) takip listenize eklendi. Yayına girince haber vereceğim.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"ℹ️ **{display_name}** (`{login_name}`) zaten takip listenizde.", parse_mode=ParseMode.MARKDOWN)

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/remove komutu. Yayıncıyı takipten çıkarır."""
    chat_id = update.effective_chat.id
    try:
        streamer_name = context.args[0].lower()
    except (IndexError, ValueError):
        await update.message.reply_text("Kullanım: `/remove yayıncı_adı`")
        return

    # Aboneliği sil (Sadece eşleştirme tablosundan)
    db_exec("DELETE FROM subscriptions WHERE chat_id = ? AND streamer_name = ?", (chat_id, streamer_name))
    
    await update.message.reply_text(f"🗑️ `{streamer_name}` takip listenizden çıkarıldı.", parse_mode=ParseMode.MARKDOWN)

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/list komutu. Takip edilen yayıncıları listeler."""
    chat_id = update.effective_chat.id
    
    # İki tabloyu (subscriptions ve streamers) birleştirerek veri çekeriz
    query = """
    SELECT s.display_name, s.streamer_name, s.last_status 
    FROM subscriptions sub
    JOIN streamers s ON sub.streamer_name = s.streamer_name
    WHERE sub.chat_id = ?
    """
    followed_streamers = db_query(query, (chat_id,))
    
    if not followed_streamers:
        await update.message.reply_text("Henüz hiçbir yayıncıyı takip etmiyorsunuz. /add komutuyla ekleyebilirsiniz.")
        return

    message = "🔔 **Takip Listeniz:**\n\n"
    for (display_name, login_name, last_status) in followed_streamers:
        status_icon = "🟢 (Şu an yayında)" if last_status == 1 else "🔴 (Çevrimdışı)"
        message += f"• **{display_name}** (`{login_name}`) - {status_icon}\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

# --- Arka Plan Kontrolcüsü ---
# BOTUN ASIL İŞİ BURADA DÖNER

async def check_streams_job(context: ContextTypes.DEFAULT_TYPE):
    """Periyodik olarak çalışıp tüm yayıncıları kontrol eder."""
    log.info("Yayın kontrol döngüsü başlıyor...")
    
    # 1. Veritabanından takip edilen TÜM benzersiz yayıncıları al
    all_streamers_query = db_query("SELECT streamer_name, last_status, display_name FROM streamers")
    if not all_streamers_query:
        log.info("Takip edilen yayıncı yok, döngü atlanıyor.")
        return

    streamer_names = [s[0] for s in all_streamers_query]
    
    # 2. Kick API'den bu yayıncıların durumunu SORGULA (paralel olarak)
    try:
        live_statuses = await kick_api.get_streamers_status(streamer_names)
    except Exception as e:
        log.error(f"Kick API'den durum alınırken kritik hata: {e}")
        return

    # 3. Durumları karşılaştır ve bildirim gönder
    for (streamer_name, local_status, display_name) in all_streamers_query:
        
        live_info = live_statuses.get(streamer_name)
        if not live_info:
            log.warning(f"{streamer_name} için API'den veri gelmedi, atlanıyor.")
            continue

        is_live_now = live_info["live"] # API'den gelen canlı durum (True/False)
        
        # --- BİLDİRİM MANTIĞI ---
        # 1. Durum: Yayına GİRDİ
        # Veritabanında 'offline' (0) kayıtlı ama API 'online' (True) diyorsa
        if is_live_now and local_status == 0:
            log.info(f"DURUM DEĞİŞİKLİĞİ: {display_name} ({streamer_name}) yayına başladı!")
            
            # a. Veritabanını güncelle (artık 'online' (1) olarak kaydet)
            db_exec("UPDATE streamers SET last_status = 1 WHERE streamer_name = ?", (streamer_name,))
            
            # b. Bu yayıncıyı takip eden TÜM kullanıcıları bul
            users_to_notify = db_query("SELECT chat_id FROM subscriptions WHERE streamer_name = ?", (streamer_name,))
            
            # c. Hepsine bildirim mesajı gönder
            notification_message = (
                f"🟢 **{display_name}** Kick.com'da yayına başladı!\n\n"
                f"**Yayın Başlığı:** {live_info.get('title', 'Başlık yok')}\n"
                f"**Kategori:** {live_info.get('game', 'Bilinmiyor')}\n\n"
                f"https://www.kick.com/{streamer_name}"
            )
            
            for (chat_id,) in users_to_notify:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=notification_message)
                except Exception as e:
                    log.warning(f"Kullanıcı {chat_id} için bildirim gönderilemedi (botu engellemiş olabilir): {e}")
                    # İsteğe bağlı: Engellediyse kullanıcıyı veritabanından silebilirsin.

        # 2. Durum: Yayını KAPATTI
        # Veritabanında 'online' (1) kayıtlı ama API 'offline' (False) diyorsa
        elif not is_live_now and local_status == 1:
            log.info(f"DURUM DEĞİŞİKLİĞİ: {display_name} ({streamer_name}) yayını kapattı.")
            # a. Veritabanını güncelle (artık 'offline' (0) olarak kaydet)
            db_exec("UPDATE streamers SET last_status = 0 WHERE streamer_name = ?", (streamer_name,))
            # (Yayın kapandı diye bildirim göndermeye gerek yok)

    log.info("Yayın kontrol döngüsü tamamlandı.")


async def post_init(application: Application):
    """Bot başladıktan sonra çalışır, komut menüsünü ayarlar."""
    await application.bot.set_my_commands([
        BotCommand("add", "Yayıncıyı takibe al"),
        BotCommand("remove", "Yayıncıyı takipten çıkar"),
        BotCommand("list", "Takip listenizi göster"),
        BotCommand("help", "Yardım"),
    ])
    log.info("Bot komutları Telegram'a yüklendi.")


def main():
    """Ana fonksiyon: Botu çalıştırır."""
    log.info("Bot başlatılıyor...")
    
    # Telegram Bot uygulamasını oluştur
    application = Application.builder() \
        .token(TELEGRAM_TOKEN) \
        .post_init(post_init) \
        .build()

    # Komutları ekle
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("list", list_command))
    
    # Arka plan görev yöneticisini (Job Queue) al
    job_queue = application.job_queue
    
    # 'check_streams_job' fonksiyonunu periyodik bir görev olarak ata
    job_queue.run_repeating(
        check_streams_job, 
        interval=CHECK_INTERVAL_SECONDS, # 'config.py' dosyasından gelen saniye
        first=10 # Bot başladıktan 10 saniye sonra ilk kontrolü yap
    )
    
    log.info(f"Kontrol döngüsü {CHECK_INTERVAL_SECONDS} saniyede bir çalışacak.")

    # Botu başlat ve yeni mesajları dinlemeye başla
    application.run_polling()
    log.info("Bot durduruldu.")

if __name__ == "__main__":
    main()