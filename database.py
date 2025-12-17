# database.py
import sqlite3
import logging

# Loglama, terminalde ne olup bittiğini görmek için iyidir.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

DB_NAME = "db.sqlite3" # Veritabanı dosyamızın adı

def initialize_db():
    """Veritabanını ve gerekli tabloları oluşturur."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Kullanıcılar tablosu
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY
        );
        """)

        # Takip edilen yayıncılar tablosu
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS streamers (
            streamer_name TEXT PRIMARY KEY,
            last_status INTEGER DEFAULT 0,
            display_name TEXT DEFAULT '' 
        );
        """)

        # Hangi kullanıcının hangi yayıncıyı takip ettiğini gösteren eşleştirme tablosu
        #
        # DÜZELTME BURADA: 'NOTIES' yerine 'NOT EXISTS' yazıldı.
        #
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            chat_id INTEGER,
            streamer_name TEXT,
            PRIMARY KEY (chat_id, streamer_name),
            FOREIGN KEY (chat_id) REFERENCES users (chat_id),
            FOREIGN KEY (streamer_name) REFERENCES streamers (streamer_name)
        );
        """)

        conn.commit()
        log.info("Veritabanı başarıyla başlatıldı ve tablolar hazırlandı.")
    except Exception as e:
        log.error(f"Veritabanı başlatılırken hata oluştu: {e}")
    finally:
        if conn:
            conn.close()

# Bu dosya 'python database.py' olarak çalıştırıldığında...
if __name__ == "__main__":
    log.info("Veritabanı kurulumu manuel olarak başlatılıyor...")
    initialize_db()