# kick_api.py
import cloudscraper  # httpx yerine cloudscraper import ediyoruz
import asyncio
import logging
from functools import partial # Fonksiyonlara ön-parametre atamak için

log = logging.getLogger(__name__)

API_URL_BASE = "https://kick.com/api/v2/channels/"

# Cloudscraper'ı standart bir tarayıcı gibi davranacak şekilde
# bir 'session' (oturum) olarak başlatıyoruz.
# Bu, JavaScript testini geçmesini ve çerezleri saklamasını sağlar.
# Bu scraper'ı tüm fonksiyonlarda tekrar tekrar kullanacağız.
try:
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True,
            'custom': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        }
    )
    log.info("Cloudscraper oturumu başarıyla oluşturuldu.")
except Exception as e:
    log.error(f"Cloudscraper başlatılamadı! {e}")
    # scraper'ı None olarak ayarlayıp fonksiyonların içinde hata vermesini sağlayabiliriz
    # ama en iyisi programın burada durması.
    # Şimdilik devam edelim, belki kurulum hatasıdır.
    scraper = None

# --- Senkron (Engelleyici) Fonksiyonlar ---
# Bu fonksiyonlar doğrudan 'async def' içinde ÇAĞRILAMAZ.
# 'asyncio.to_thread' ile çağrılmaları gerekir.

def _sync_get_request(url: str):
    """cloudscraper kullanarak senkron bir GET isteği yapar."""
    if not scraper:
        log.error("Cloudscraper başlatılamadığı için istek yapılamıyor.")
        return None
        
    try:
        response = scraper.get(url)
        
        # 404'ü hata olarak görme, sadece None döndür
        if response.status_code == 404:
            log.warning(f"Kaynak bulunamadı (404): {url}")
            return None # 404
        
        # Diğer tüm hataları (403, 500 vb.) yakala
        response.raise_for_status() 
        
        return response.json() # Başarılıysa JSON verisini döndür
        
    except Exception as e:
        log.error(f"Cloudscraper isteği başarısız oldu: {url} | Hata: {e}")
        return None # Hata durumunda None döndür

# --- Asenkron (Engelleyici Olmayan) Fonksiyonlar ---
# bot.py'nin çağıracağı fonksiyonlar bunlardır.

async def get_user_info(streamer_name: str):
    """
    Bir yayıncının Kick'te var olup olmadığını kontrol eder.
    Bunu, _sync_get_request fonksiyonunu ayrı bir thread'de çalıştırarak yapar.
    """
    url = f"{API_URL_BASE}{streamer_name.lower()}"
    
    # asyncio.to_thread, senkron fonksiyonu botu dondurmadan çalıştırır
    data = await asyncio.to_thread(_sync_get_request, url)
    
    if not data:
        log.warning(f"Kullanıcı bilgisi alınamadı (None): {streamer_name}")
        return None

    try:
        # Veri yapısını doğrula
        return {
            "login_name": data['slug'],
            "display_name": data['user']['username'] 
        }
    except KeyError as e:
        log.error(f"Kick user info'da beklenmedik veri yapısı (KeyError): {streamer_name} | {e}")
        return None
    except Exception as e:
        log.error(f"Kick user info işlenirken hata: {streamer_name} | {e}")
        return None

async def _get_single_streamer_status(streamer_name: str):
    """
    (Yardımcı Fonksiyon) Tek bir yayıncının durumunu senkron olarak alır
    ve asenkron bot için sonucu işler.
    """
    url = f"{API_URL_BASE}{streamer_name.lower()}"
    
    # partial kullanarak _sync_get_request fonksiyonunu url parametresiyle
    # hazır hale getiriyoruz. asyncio.to_thread sadece fonksiyon adı alır.
    func_to_run = partial(_sync_get_request, url)
    
    data = await asyncio.to_thread(func_to_run)
    
    if not data:
        # Hata veya 404
        return streamer_name, {"live": False, "title": None, "game": None}

    try:
        livestream_data = data.get('livestream')
        
        if livestream_data: # Yayında
            categories = livestream_data.get('categories', [])
            game_name = categories[0]['name'] if categories else 'Bilinmiyor'

            return streamer_name, {
                "live": True,
                "title": livestream_data.get('session_title', 'Başlık yok'),
                "game": game_name
            }
        else:
            # Yayında değil (çevrimdışı)
            return streamer_name, {"live": False, "title": None, "game": None}
            
    except Exception as e:
        log.error(f"Kick stream status işlenirken hata: {streamer_name} | {e}")
        return streamer_name, {"live": False, "title": None, "game": None}

async def get_streamers_status(streamer_names: list):
    """
    Tüm yayıncıların durumunu paralel olarak (ama botu dondurmadan) kontrol eder.
    """
    if not streamer_names:
        return {}

    # Her bir yayıncı için bir '_get_single_streamer_status' görevi oluştur.
    # asyncio.gather bu görevlerin hepsini "aynı anda" çalıştırır.
    tasks = []
    for name in streamer_names:
        tasks.append(_get_single_streamer_status(name.lower()))
    
    task_results = await asyncio.gather(*tasks)
    
    # Sonuçları [('isim1', data1), ('isim2', data2)] formatından
    # {'isim1': data1, 'isim2': data2} formatına dök
    results = {}
    for name, data in task_results:
        results[name] = data
    
    return results