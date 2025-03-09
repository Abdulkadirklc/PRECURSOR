from flask import Flask, jsonify, request, render_template
import feedparser
import os
import json
from datetime import datetime
import time
from transformers import pipeline
from dotenv import load_dotenv
import sqlite3
import threading
import logging
import sys
import re
import webbrowser

# Başlangıç mesajı
print("="*50)
print("PRECURSOR - Haber Özet Platformu başlatılıyor...")
print("Python sürümü:", sys.version)
print("Çalışma dizini:", os.getcwd())

# GPU kontrolü
import torch
device = torch.device("cuda" if torch.cuda.is_available() and os.getenv("GPU_AVAILABLE") == "1" else "cpu")
print(f"Kullanılan cihaz: {device}")
if device.type == "cuda":
    print(f"GPU modeli: {torch.cuda.get_device_name(0)}")
    print(f"Kullanılabilir GPU sayısı: {torch.cuda.device_count()}")
    print(f"CUDA sürümü: {torch.version.cuda}")
print("="*50)

# Loglama yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("haber_ozet.log"),  # Log dosyasını da aynı isimle değiştirdim
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# .env dosyasını yükle
load_dotenv()

# LLM model seçimi (çevre değişkeninden veya varsayılan)
DEFAULT_MODEL = "mrm8488/bert2bert_shared-turkish-summarization"  # Varsayılan model
LLM_MODEL = os.getenv("LLM_MODEL", DEFAULT_MODEL)
LLM_TYPE = os.getenv("LLM_TYPE", "transformers")
OZET_MODU = os.getenv("OZET_MODU", "normal")  # normal veya super

print(f"LLM Tipi: {LLM_TYPE}, Model: {LLM_MODEL}, Özet Modu: {OZET_MODU}")

def init_llm_model():
    """LLM modelini başlatır"""
    global summarizer
    try:
        if LLM_TYPE == "transformers":
            try:
                from transformers import EncoderDecoderModel, BertTokenizer
                # Önce tokenizer'ı yüklemeyi dene
                tokenizer = BertTokenizer.from_pretrained(LLM_MODEL, local_files_only=True)
                model = EncoderDecoderModel.from_pretrained(LLM_MODEL, local_files_only=True)
                summarizer = pipeline("summarization", model=model, tokenizer=tokenizer, device=-1 if device.type == "cpu" else 0)
                logger.info(f"Transformers modeli başarıyla yüklendi (offline mod): {LLM_MODEL}")
            except Exception as offline_error:
                logger.warning(f"Offline model yüklenemedi, online deneniyor: {offline_error}")
                # Online yüklemeyi dene
                try:
                    model = EncoderDecoderModel.from_pretrained(LLM_MODEL)
                    tokenizer = BertTokenizer.from_pretrained(LLM_MODEL)
                    summarizer = pipeline("summarization", model=model, tokenizer=tokenizer, device=-1 if device.type == "cpu" else 0)
                    logger.info(f"Transformers modeli başarıyla yüklendi (online mod): {LLM_MODEL}")
                except Exception as online_error:
                    logger.error(f"Online model yükleme hatası: {online_error}")
                    raise
        else:
            logger.warning(f"Desteklenmeyen LLM tipi: {LLM_TYPE}, basit özetleme kullanılacak")
            summarizer = lambda metin, **kwargs: [{"summary_text": gelismis_basit_ozet(metin)}]
    except Exception as e:
        logger.error(f"LLM model yükleme hatası: {e}")
        logger.warning("Basit özetleme moduna geçiliyor...")
        summarizer = lambda metin, **kwargs: [{"summary_text": gelismis_basit_ozet(metin)}]

def gelismis_basit_ozet(metin, super_ozet=False):
    """Basit kurallara dayalı özetleme yapar"""
    try:
        # Noktalama işaretlerine göre cümlelere ayır
        cumleler = re.split(r'[.!?]+', metin)
        cumleler = [c.strip() for c in cumleler if len(c.strip()) > 10]
        
        if not cumleler:
            return metin if len(metin) < 200 else metin[:197] + "..."
            
        if super_ozet:
            # Sadece ilk cümleyi al
            return cumleler[0]
        else:
            # İlk 3 cümleyi al (veya daha az varsa hepsini)
            ozet = '. '.join(cumleler[:3]) + '.'
            return ozet if len(ozet) < 500 else ozet[:497] + "..."
            
    except Exception as e:
        logger.error(f"Basit özetleme hatası: {e}")
        return metin[:197] + "..." if len(metin) > 200 else metin

# Global değişkenler
summarizer = None
init_llm_model()

app = Flask(__name__, 
            static_folder="../frontend/static",
            template_folder="../frontend")

# RSS feed'lerini yapılandırma dosyasından yükle
def load_rss_feeds():
    """RSS feed'lerini yapılandırma dosyasından yükler"""
    config_file = os.path.join(os.path.dirname(__file__), 'rss_feeds.json')
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            feeds = json.load(f)
            logger.info(f"RSS feedleri başarıyla yüklendi: {config_file}")
            return feeds
    except Exception as e:
        logger.error(f"RSS feed yapılandırma dosyası yüklenirken hata: {e}")
        logger.warning("Varsayılan RSS feed'leri kullanılacak.")
        return {
            "gundem": [
                "https://www.hurriyet.com.tr/rss/gundem",
                "https://www.ntv.com.tr/gundem.rss"
            ]
        }

# RSS feed'lerini yükle
RSS_FEEDS = load_rss_feeds()
print(f"Yüklenen RSS kategorileri: {', '.join(RSS_FEEDS.keys())}")

# Veritabanı bağlantısı
DB_FILE = 'haber_ozet.db'  # Tek bir veritabanı dosyası kullanacağız

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def ozet_olustur(metin):
    """Verilen metni özetler"""
    try:
        # HTML etiketlerini temizle
        temiz_metin = re.sub(r'<[^>]+>', '', metin)
        temiz_metin = re.sub(r'\s+', ' ', temiz_metin).strip()
        
        if not temiz_metin:
            return ""
            
        # Metin çok kısaysa direkt döndür
        if len(temiz_metin) < 200:
            return temiz_metin
            
        if LLM_TYPE == "transformers":
            try:
                if not summarizer:
                    init_llm_model()
                return summarizer(temiz_metin, max_length=150 if OZET_MODU != "super" else 75, min_length=50 if OZET_MODU != "super" else 20, do_sample=False)[0]['summary_text']
            except Exception as e:
                logger.error(f"Transformers özetleme hatası: {e}")
                return gelismis_basit_ozet(temiz_metin, super_ozet=OZET_MODU == "super")
        else:
            return gelismis_basit_ozet(temiz_metin, super_ozet=OZET_MODU == "super")
            
    except Exception as e:
        logger.error(f"Özetleme hatası: {e}")
        return ""

def haberleri_getir(kategori):
    """Belirli bir kategorideki RSS feed'lerinden haberleri çeker"""
    haberler = []
    islenen_urller = set()  # İşlenen URL'leri takip etmek için set
    
    if kategori not in RSS_FEEDS:
        logger.warning(f"Geçersiz kategori: {kategori}")
        return haberler
    
    for feed_url in RSS_FEEDS[kategori]:
        try:
            logger.info(f"Feed çekiliyor: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            # Feed'in geçerli olup olmadığını kontrol et
            if hasattr(feed, 'bozo_exception'):
                logger.warning(f"Feed çekilirken uyarı: {feed.bozo_exception}")
            
            if not hasattr(feed, 'entries') or len(feed.entries) == 0:
                logger.warning(f"Feed'de haber bulunamadı: {feed_url}")
                continue
                
            for entry in feed.entries[:5]:  # Her feed'den en fazla 5 haber al
                # URL kontrolü - aynı URL'den haber varsa atla
                haber_url = entry.link if hasattr(entry, 'link') else ''
                if not haber_url or haber_url in islenen_urller:
                    continue
                islenen_urller.add(haber_url)
                
                # İçerik alanını belirle - bazı RSS'lerde farklı alanlar kullanılabilir
                icerik = ""
                if hasattr(entry, 'description'):
                    icerik = entry.description
                elif hasattr(entry, 'summary'):
                    icerik = entry.summary
                elif hasattr(entry, 'content'):
                    icerik = entry.content[0].value if len(entry.content) > 0 else ""
                
                # İçerik yoksa veya çok kısaysa atla
                if not icerik or len(icerik) < 50:
                    logger.warning(f"Haber içeriği çok kısa veya yok: {entry.title if hasattr(entry, 'title') else 'Başlıksız'}")
                    continue
                
                # Resim URL'sini bul
                resim_url = None
                if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
                    resim_url = entry.media_content[0]['url']
                elif hasattr(entry, 'links'):
                    for link in entry.links:
                        if link.get('type', '').startswith('image/'):
                            resim_url = link.get('href')
                            break
                
                # Tarihi parse et
                try:
                    tarih = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                except:
                    tarih = datetime.now()
                
                # Özet oluştur
                try:
                    logger.info(f"Haber özetleniyor: {entry.title if hasattr(entry, 'title') else 'Başlıksız'}")
                    ozet = ozet_olustur(icerik)
                except Exception as e:
                    logger.error(f"Özet oluşturma hatası: {str(e)}")
                    ozet = entry.title if hasattr(entry, 'title') else 'Özet oluşturulamadı'
                
                haber = {
                    'baslik': entry.title if hasattr(entry, 'title') else 'Başlıksız',
                    'icerik': icerik,
                    'ozet': ozet,
                    'url': haber_url,
                    'resim_url': resim_url,
                    'kategori': kategori,
                    'kaynak': feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else 'Bilinmeyen Kaynak',
                    'tarih': tarih
                }
                haberler.append(haber)
                
        except Exception as e:
            logger.error(f"Feed işlenirken hata: {feed_url} - {str(e)}")
            continue
    
    return haberler

def haberleri_veritabanina_kaydet(haberler):
    """Haberleri veritabanına kaydeder"""
    if not haberler:
        return
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for haber in haberler:
        try:
            cursor.execute('''
            INSERT INTO haberler (baslik, ozet, icerik, kategori, kaynak, url, resim_url, tarih)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                haber['baslik'],
                haber['ozet'],
                haber['icerik'],
                haber['kategori'],
                haber['kaynak'],
                haber['url'],
                haber['resim_url'],
                haber['tarih']
            ))
        except sqlite3.IntegrityError:
            logger.warning(f"Haber zaten mevcut: {haber['baslik']}")
            continue
        except Exception as e:
            logger.error(f"Haber kaydedilirken hata: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    logger.info(f"{len(haberler)} haber veritabanına kaydedildi.")

def temizle_veritabani():
    """Veritabanını temizler ve yeni baştan başlar"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tüm haberleri sil
    cursor.execute('DELETE FROM haberler')
    
    conn.commit()
    conn.close()
    logger.info("Veritabanı temizlendi, yeni haberler yüklenecek...")

def ilk_haberleri_yukle():
    """Uygulama başlatıldığında tüm kategorilerden haberleri yükler"""
    logger.info("İlk haberler yükleniyor...")
    for kategori in RSS_FEEDS.keys():
        logger.info(f"{kategori} kategorisi yükleniyor...")
        haberler = haberleri_getir(kategori)
        haberleri_veritabanina_kaydet(haberler)
    logger.info("İlk haberler başarıyla yüklendi.")
    
    # Tarayıcıyı aç
    logger.info("Web arayüzü açılıyor...")
    webbrowser.open('http://localhost:5000')

# Veritabanını oluştur
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Haberler tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS haberler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        baslik TEXT NOT NULL,
        ozet TEXT NOT NULL,
        icerik TEXT NOT NULL,
        kategori TEXT NOT NULL,
        kaynak TEXT NOT NULL,
        url TEXT NOT NULL UNIQUE,  -- URL'yi benzersiz yap
        resim_url TEXT,
        tarih TIMESTAMP NOT NULL,
        olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"Veritabanı başarıyla oluşturuldu veya mevcut veritabanı kullanıldı: {DB_FILE}")

# Veritabanını başlat, temizle ve ilk haberleri yükle
init_db()
temizle_veritabani()
ilk_haberleri_yukle()

def temizle_html(html_icerik):
    """HTML içeriğini temizler ve düz metne dönüştürür"""
    from html import unescape
    
    # Boş içerik kontrolü
    if not html_icerik:
        return ""
    
    # HTML içeriğini string'e dönüştür
    if not isinstance(html_icerik, str):
        try:
            html_icerik = str(html_icerik)
        except:
            return ""
    
    # CDATA bölümlerini temizle
    html_icerik = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', html_icerik)
    
    # Script ve style etiketlerini tamamen kaldır
    html_icerik = re.sub(r'<script.*?>.*?</script>', ' ', html_icerik, flags=re.DOTALL)
    html_icerik = re.sub(r'<style.*?>.*?</style>', ' ', html_icerik, flags=re.DOTALL)
    
    # HTML yorumlarını kaldır
    html_icerik = re.sub(r'<!--.*?-->', ' ', html_icerik, flags=re.DOTALL)
    
    # Diğer HTML etiketlerini kaldır
    html_icerik = re.sub(r'<.*?>', ' ', html_icerik)
    
    # HTML karakter kodlarını çöz
    temiz_metin = unescape(html_icerik)
    
    # Fazla boşlukları temizle
    temiz_metin = re.sub(r'\s+', ' ', temiz_metin).strip()
    
    # URL'leri temizle
    temiz_metin = re.sub(r'https?://\S+', '', temiz_metin)
    
    # "Devamı için tıklayınız" gibi ifadeleri kaldır
    temiz_metin = re.sub(r'Devamı için tıklayınız.*', '', temiz_metin)
    temiz_metin = re.sub(r'Haberin devamı için.*', '', temiz_metin)
    temiz_metin = re.sub(r'Detaylar için tıklayınız.*', '', temiz_metin)
    temiz_metin = re.sub(r'Ayrıntılar için tıklayınız.*', '', temiz_metin)
    temiz_metin = re.sub(r'Devamını oku.*', '', temiz_metin)
    
    # Fazla noktalama işaretlerini temizle
    temiz_metin = re.sub(r'\.{2,}', '.', temiz_metin)
    temiz_metin = re.sub(r'\s+\.', '.', temiz_metin)
    
    # Başlangıç ve sondaki boşlukları temizle
    temiz_metin = temiz_metin.strip()
    
    return temiz_metin

def temizle_metin(metin):
    """Metni özetleme için hazırlar"""
    # Önce HTML temizliği
    temiz_metin = temizle_html(metin)
    
    # Gereksiz boşlukları temizle
    temiz_metin = re.sub(r'\s+', ' ', temiz_metin).strip()
    
    # Noktalama işaretlerini düzelt
    temiz_metin = re.sub(r'\.{2,}', '.', temiz_metin)  # Fazla noktaları temizle
    temiz_metin = re.sub(r'\s+\.', '.', temiz_metin)   # Nokta öncesi boşlukları temizle
    
    # Reklam ve yönlendirme metinlerini temizle
    reklam_kaliplari = [
        r'Bu haber\s+.+\s+tarafından hazırlanmıştır\.',
        r'Kaynak:.+',
        r'Sponsorlu İçerik',
        r'Reklam',
        r'İlgili Haberler:.*',
        r'Devamı için tıklayınız.*',
        r'Haberin devamı için.*',
        r'Detaylar için tıklayınız.*',
        r'Ayrıntılar için tıklayınız.*',
        r'Devamını oku.*',
        r'Daha fazlası için.*'
    ]
    
    for kalip in reklam_kaliplari:
        temiz_metin = re.sub(kalip, '', temiz_metin, flags=re.IGNORECASE)
    
    return temiz_metin.strip()

def ozet_olustur(metin, max_length=150):
    """Metni özetler"""
    if len(metin) < 100:  # Çok kısa metinleri özetleme
        return metin
    
    # Metni temizle ve özetleme için hazırla
    temiz_metin = temizle_metin(metin)
    
    # Özet uzunluğunu ayarla
    if OZET_MODU == "super":
        max_length = 75  # Süper özet için daha kısa
        min_length = 20
    else:
        max_length = 150  # Normal özet
        min_length = 30
    
    try:
        if LLM_TYPE == "transformers":
            if "falcon" in LLM_MODEL.lower():
                # Falcon modeli için özel prompt
                prompt = f"Lütfen bu haberi {'en fazla 2 cümle ile' if OZET_MODU == 'super' else 'detaylı şekilde'} özetle:\n\n{temiz_metin}"
                ozet = summarizer(prompt, max_length=max_length, min_length=min_length, do_sample=False)
            elif "bert2bert" in LLM_MODEL.lower():
                # BERT2BERT modeli için özel ayarlar
                ozet = summarizer(temiz_metin, max_length=max_length, min_length=min_length, do_sample=False, num_beams=4)
            elif "mt5" in LLM_MODEL.lower() or "mbart" in LLM_MODEL.lower():
                # Çok dilli modeller için
                ozet = summarizer(temiz_metin, max_length=max_length, min_length=min_length, do_sample=False, num_beams=4, length_penalty=2.0)
            else:
                ozet = summarizer(temiz_metin, max_length=max_length, min_length=min_length, do_sample=False)
            
            return ozet[0]['summary_text']
            
        elif LLM_TYPE == "openai":
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            if not openai.api_key:
                raise ValueError("OPENAI_API_KEY çevre değişkeni ayarlanmamış")
            
            prompt = f"Aşağıdaki haberi {'en fazla 2 cümle ile' if OZET_MODU == 'super' else 'detaylı şekilde'} özetle. Sadece özeti yaz, başka bir şey ekleme:\n\n{temiz_metin}"
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=max_length,
                temperature=0.3
            )
            return response.choices[0].text.strip()
        else:
            # Bilinmeyen LLM tipi, basit özetleme kullan
            return gelismis_basit_ozet(temiz_metin, super_ozet=OZET_MODU == "super")
    except Exception as e:
        logger.error(f"Özetleme hatası: {e}")
        # Gelişmiş basit özetleme
        return gelismis_basit_ozet(temiz_metin, super_ozet=OZET_MODU == "super")

def arkaplan_haber_guncelleme():
    """Arka planda çalışarak haberleri düzenli olarak günceller"""
    while True:
        logger.info("Haberler güncelleniyor...")
        for kategori in RSS_FEEDS.keys():
            haberler = haberleri_getir(kategori)
            haberleri_veritabanina_kaydet(haberler)
        
        # 30 dakikada bir güncelle
        logger.info("Haber güncellemesi tamamlandı. 30 dakika sonra tekrar güncellenecek.")
        time.sleep(1800)

# Arka plan görevini başlat
haber_guncelleme_thread = threading.Thread(target=arkaplan_haber_guncelleme)
haber_guncelleme_thread.daemon = True
haber_guncelleme_thread.start()

@app.route('/')
def index():
    """Ana sayfa"""
    return render_template('index.html')

@app.route('/api/haberler')
def tum_haberler():
    """Tüm haberleri döndürür"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM haberler ORDER BY tarih DESC LIMIT 50')
    haberler = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(haberler)

@app.route('/api/haberler/<kategori>')
def kategori_haberleri(kategori):
    """Belirli bir kategorideki haberleri döndürür"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM haberler WHERE kategori = ? ORDER BY tarih DESC LIMIT 20', (kategori,))
    haberler = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(haberler)

@app.route('/api/kategoriler')
def kategoriler():
    """Mevcut kategorileri döndürür"""
    return jsonify(list(RSS_FEEDS.keys()))

@app.route('/api/yenile/<kategori>')
def kategori_yenile(kategori):
    """Belirli bir kategorideki haberleri yeniler"""
    if kategori in RSS_FEEDS:
        haberler = haberleri_getir(kategori)
        haberleri_veritabanina_kaydet(haberler)
        return jsonify({"durum": "başarılı", "mesaj": f"{len(haberler)} haber güncellendi"})
    else:
        return jsonify({"durum": "hata", "mesaj": "Geçersiz kategori"}), 400

@app.route('/api/model-bilgisi')
def model_bilgisi():
    """Kullanılan LLM modeli hakkında bilgi verir"""
    return jsonify({
        "model_tipi": LLM_TYPE,
        "model_adi": LLM_MODEL if LLM_TYPE == "transformers" else "API tabanlı model"
    })

@app.route('/api/models')
def get_models():
    """Kullanılabilir modelleri döndürür"""
    models = {
        "mrm8488/bert2bert_shared-turkish-summarization": "Türkçe Haber Özetleme (Varsayılan)",
        "google/mt5-small": "Çok Dilli MT5 (Hafif)",
        "facebook/mbart-large-cc25": "Çok Dilli MBART",
        "basic": "Basit Özetleme"
    }
    return jsonify(models)

@app.route('/api/model_status')
def get_model_status():
    """Model durumunu döndürür"""
    global summarizer
    return jsonify({
        "ready": summarizer is not None,
        "current_model": LLM_MODEL,
        "type": LLM_TYPE,
        "device": str(device)
    })

@app.route('/api/change_summary_mode', methods=['POST'])
def change_summary_mode():
    """Özet modunu değiştirir"""
    global OZET_MODU
    try:
        data = request.get_json()
        new_mode = data.get('mode')
        
        if new_mode not in ['normal', 'super']:
            return jsonify({"success": False, "error": "Geçersiz özet modu"})
        
        OZET_MODU = new_mode
        logger.info(f"Özet modu değiştirildi: {new_mode}")
        return jsonify({"success": True, "message": f"Özet modu değiştirildi: {new_mode}"})
    except Exception as e:
        logger.error(f"Özet modu değiştirme hatası: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/change_model', methods=['POST'])
def change_model():
    """Model değişikliği yapar"""
    global summarizer, LLM_MODEL, LLM_TYPE
    
    try:
        data = request.get_json()
        new_model = data.get('model')
        
        if new_model == "basic":
            summarizer = lambda metin, **kwargs: [{"summary_text": gelismis_basit_ozet(metin)}]
            LLM_MODEL = "basic"
            logger.info("Basit özetleme moduna geçildi")
            return jsonify({"success": True, "message": "Basit özetleme moduna geçildi"})
            
        if new_model not in ["mrm8488/bert2bert_shared-turkish-summarization", "google/mt5-small", 
                           "facebook/mbart-large-cc25"]:
            return jsonify({"success": False, "error": "Geçersiz model"})
        
        try:
            if "t5" in new_model.lower():
                from transformers import T5ForConditionalGeneration, T5Tokenizer
                model = T5ForConditionalGeneration.from_pretrained(new_model).to(device)
                tokenizer = T5Tokenizer.from_pretrained(new_model)
            elif "bert2bert" in new_model.lower():
                from transformers import EncoderDecoderModel, BertTokenizer
                model = EncoderDecoderModel.from_pretrained(new_model).to(device)
                tokenizer = BertTokenizer.from_pretrained(new_model)
            elif "mbart" in new_model.lower():
                from transformers import MBartForConditionalGeneration, MBart50TokenizerFast
                model = MBartForConditionalGeneration.from_pretrained(new_model).to(device)
                tokenizer = MBart50TokenizerFast.from_pretrained(new_model)
            
            summarizer = pipeline("summarization", model=model, tokenizer=tokenizer, 
                               device=-1 if device.type == "cpu" else 0)
            LLM_MODEL = new_model
            logger.info(f"Model değiştirildi: {new_model}")
            return jsonify({"success": True, "message": f"Model değiştirildi: {new_model}"})
            
        except Exception as e:
            logger.error(f"Model değiştirme hatası: {e}")
            summarizer = lambda metin, **kwargs: [{"summary_text": gelismis_basit_ozet(metin)}]
            LLM_MODEL = "basic"
            return jsonify({"success": False, "error": str(e)})
            
    except Exception as e:
        logger.error(f"Model değiştirme isteği hatası: {e}")
        return jsonify({"success": False, "error": "İstek işlenirken hata oluştu"})

if __name__ == '__main__':
    try:
        logger.info(f"Uygulama başlatılıyor... LLM Tipi: {LLM_TYPE}, Model: {LLM_MODEL if LLM_TYPE == 'transformers' else 'API tabanlı'}")
        # Debug modunu kapatıp host'u açıyoruz
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logger.error(f"Uygulama başlatma hatası: {e}")
        input("Devam etmek için bir tuşa basın...") 