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

# Başlangıç mesajı
print("="*50)
print("PRECURSOR - Haber Özet Platformu başlatılıyor...")
print("Python sürümü:", sys.version)
print("Çalışma dizini:", os.getcwd())
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
LLM_MODEL = os.getenv("LLM_MODEL", "facebook/bart-base")  # Daha hafif bir model
LLM_TYPE = os.getenv("LLM_TYPE", "transformers")  # transformers, openai

print(f"LLM Tipi: {LLM_TYPE}, Model: {LLM_MODEL}")

app = Flask(__name__, 
            static_folder="../frontend/static",
            template_folder="../frontend")

# RSS feed'lerini yapılandırma dosyasından yükle
def load_rss_feeds():
    """RSS feed'lerini yapılandırma dosyasından yükler"""
    config_file = 'rss_feeds.json'
    
    # Varsayılan RSS feed'leri
    default_feeds = {
        'spor': [
            'https://www.ntv.com.tr/spor.rss',
            'https://www.sabah.com.tr/rss/spor.xml',
        ],
        'ekonomi': [
            'https://www.takvim.com.tr/rss/ekonomi.xml',
            'https://www.bloomberght.com/rss',
            'https://www.yeniakit.com.tr/rss/haber/ekonomi'
        ],
        'teknoloji': [
            'https://www.chip.com.tr/rss/',
            'https://www.ntv.com.tr/teknoloji.rss',
        ],
        'gundem': [
            'https://www.hurriyet.com.tr/rss/gundem',
            'https://www.sozcu.com.tr/rss/gundem.xml',
        ],
        'magazin': [
            'http://www.milliyet.com.tr/rss/rssNew/magazinRss.xml',
            'https://www.sabah.com.tr/rss/magazin.xml',
            
        ]
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"RSS feed yapılandırma dosyası yüklenirken hata: {e}")
            return default_feeds
    else:
        return default_feeds

# RSS feed'lerini yükle
RSS_FEEDS = load_rss_feeds()
print(f"Yüklenen RSS kategorileri: {', '.join(RSS_FEEDS.keys())}")

# Veritabanı bağlantısı
DB_FILE = 'haber_ozet.db'  # Tek bir veritabanı dosyası kullanacağız

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

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

# Veritabanını başlat
init_db()

# LLM modelini başlat
summarizer = None
def init_llm_model():
    """Seçilen LLM modelini başlatır"""
    global summarizer, LLM_TYPE
    
    try:
        import torch
        logger.info(f"PyTorch sürümü: {torch.__version__}")
        pytorch_available = True
    except ImportError:
        logger.error("PyTorch yüklü değil. Basit özetleme kullanılacak.")
        pytorch_available = False
    
    if LLM_TYPE == "transformers" and pytorch_available:
        logger.info(f"Transformers modeli yükleniyor: {LLM_MODEL}")
        try:
            # Daha hafif modeller için öneri listesi
            hafif_modeller = [
                "facebook/bart-base",  # İlk tercih
                "sshleifer/distilbart-cnn-6-6",  # Distilled model, daha hafif
                "t5-small",  # Çok daha hafif
                "google/pegasus-xsum"  # Alternatif model
            ]
            
            # Önce belirtilen modeli dene
            try:
                summarizer = pipeline("summarization", model=LLM_MODEL)
                logger.info(f"Model başarıyla yüklendi: {LLM_MODEL}")
            except Exception as e:
                logger.error(f"{LLM_MODEL} modeli yüklenirken hata: {e}")
                
                # Belirtilen model yüklenemediyse, hafif modelleri sırayla dene
                for hafif_model in hafif_modeller:
                    if hafif_model != LLM_MODEL:  # Zaten denenmemişse
                        try:
                            logger.info(f"Alternatif model deneniyor: {hafif_model}")
                            summarizer = pipeline("summarization", model=hafif_model)
                            logger.info(f"Alternatif model başarıyla yüklendi: {hafif_model}")
                            break
                        except Exception as e:
                            logger.error(f"{hafif_model} modeli yüklenirken hata: {e}")
                
                # Hiçbir model yüklenemediyse
                if summarizer is None:
                    raise Exception("Hiçbir model yüklenemedi")
                    
        except Exception as e:
            logger.error(f"Hiçbir model yüklenemedi: {e}")
            logger.warning("Basit özetleme kullanılacak.")
            summarizer = gelismis_basit_ozet_wrapper
    elif LLM_TYPE == "transformers" and not pytorch_available:
        logger.warning("PyTorch yüklü değil. Basit özetleme kullanılacak.")
        summarizer = gelismis_basit_ozet_wrapper
    elif LLM_TYPE == "openai":
        logger.info("OpenAI API kullanılıyor.")
        # OpenAI API kullanımı için gerekli importlar
        try:
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            if not openai.api_key:
                raise ValueError("OPENAI_API_KEY çevre değişkeni ayarlanmamış")
            logger.info("OpenAI API başarıyla yapılandırıldı.")
        except Exception as e:
            logger.error(f"OpenAI API yapılandırılırken hata: {e}")
            # Yedek olarak basit özetleme kullan
            logger.warning("OpenAI API yapılandırılamadı. Basit özetleme kullanılacak.")
            summarizer = gelismis_basit_ozet_wrapper
    else:
        logger.warning(f"Bilinmeyen LLM tipi veya PyTorch yüklü değil: {LLM_TYPE}, basit özetleme kullanılacak.")
        summarizer = gelismis_basit_ozet_wrapper

# Gelişmiş basit özetleme için wrapper fonksiyon
def gelismis_basit_ozet_wrapper(metin, **kwargs):
    return [{"summary_text": gelismis_basit_ozet(metin)}]

def gelismis_basit_ozet(metin):
    """Gelişmiş basit özetleme algoritması"""
    # Metni cümlelere ayır
    cumleler = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', metin)
    cumleler = [c.strip() for c in cumleler if len(c.strip()) > 10]  # Çok kısa cümleleri atla
    
    # Çok kısa metinleri özetleme
    if len(cumleler) <= 3:
        return metin
    
    # Anahtar kelimeler ve önem puanları
    anahtar_kelimeler = [
        "önemli", "kritik", "dikkat", "son dakika", "gelişme", 
        "açıklama", "iddia", "karar", "sonuç", "etki", 
        "değişiklik", "yeni", "ilk", "son", "büyük", "artış",
        "zam", "fiyat", "ekonomi", "enflasyon", "kira", "konut",
        "TÜİK", "TÜFE", "ÜFE", "yüzde", "oran", "hesaplama"
    ]
    
    # Cümleleri puanla
    cumle_puanlari = []
    for i, cumle in enumerate(cumleler):
        puan = 0
        
        # Konum puanı (ilk ve son cümleler daha önemli)
        if i == 0:
            puan += 5  # İlk cümle daha önemli
        elif i == len(cumleler) - 1:
            puan += 2  # Son cümle
        elif i <= 2:
            puan += 3  # İlk birkaç cümle
        
        # Uzunluk puanı (çok kısa veya çok uzun cümleler daha az önemli)
        kelime_sayisi = len(cumle.split())
        if 8 <= kelime_sayisi <= 25:
            puan += 2
        elif 5 <= kelime_sayisi < 8 or 25 < kelime_sayisi <= 35:
            puan += 1
        
        # Anahtar kelime puanı
        for kelime in anahtar_kelimeler:
            if kelime.lower() in cumle.lower():
                puan += 3
        
        # Sayısal veri içeren cümleler daha önemli
        if re.search(r'yüzde \d+|\%\d+|\d+(\.\d+)? (TL|lira|dolar|euro)', cumle.lower()):
            puan += 4
        
        # Tarih içeren cümleler önemli olabilir
        if re.search(r'\d{1,2} (ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)', cumle.lower()):
            puan += 2
            
        cumle_puanlari.append((i, puan, cumle))
    
    # Puanlara göre sırala ve en yüksek puanlı 3 cümleyi seç
    cumle_puanlari.sort(key=lambda x: x[1], reverse=True)
    secilen_cumleler = cumle_puanlari[:3]
    
    # Orijinal sıralamaya göre sırala
    secilen_cumleler.sort(key=lambda x: x[0])
    
    # Özeti oluştur
    ozet = ". ".join([cumle for _, _, cumle in secilen_cumleler])
    if not ozet.endswith('.'):
        ozet += "."
    
    return ozet

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

def ozet_olustur(metin, max_length=150):
    """Metni özetler"""
    if len(metin) < 100:  # Çok kısa metinleri özetleme
        return metin
    
    # HTML içeriğini temizle
    temiz_metin = temizle_html(metin)
    
    try:
        if LLM_TYPE == "transformers":
            # Transformers modellerinin maksimum girdi uzunluğu sınırlı olabilir
            # Bu nedenle çok uzun metinleri kısaltıyoruz
            max_input_length = 1024  # Çoğu model için makul bir değer
            if len(temiz_metin) > max_input_length:
                temiz_metin = temiz_metin[:max_input_length]
                
            ozet = summarizer(temiz_metin, max_length=max_length, min_length=30, do_sample=False)
            return ozet[0]['summary_text']
        elif LLM_TYPE == "openai":
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            if not openai.api_key:
                raise ValueError("OPENAI_API_KEY çevre değişkeni ayarlanmamış")
                
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"Aşağıdaki haberi kısa ve öz bir şekilde özetle. Sadece özeti yaz, başka bir şey ekleme:\n\n{temiz_metin}",
                max_tokens=max_length,
                temperature=0.3
            )
            return response.choices[0].text.strip()
        else:
            # Bilinmeyen LLM tipi, basit özetleme kullan
            return gelismis_basit_ozet(temiz_metin)
    except Exception as e:
        logger.error(f"Özetleme hatası: {e}")
        # Gelişmiş basit özetleme
        return gelismis_basit_ozet(temiz_metin)

def haberleri_getir(kategori):
    """Belirli bir kategorideki RSS feed'lerinden haberleri çeker"""
    haberler = []
    
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
                resim_url = ""
                # 1. Media içeriğinden resim URL'si bul
                if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
                    for media in entry.media_content:
                        if 'url' in media:
                            resim_url = media['url']
                            break
                
                # 2. Enclosure'dan resim URL'si bul
                if not resim_url and hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
                    for enclosure in entry.enclosures:
                        if 'href' in enclosure and enclosure.get('type', '').startswith('image/'):
                            resim_url = enclosure['href']
                            break
                
                # 3. Media thumbnail'dan resim URL'si bul
                if not resim_url and hasattr(entry, 'media_thumbnail') and len(entry.media_thumbnail) > 0:
                    for thumbnail in entry.media_thumbnail:
                        if 'url' in thumbnail:
                            resim_url = thumbnail['url']
                            break
                
                # 4. İçerikten resim URL'si çıkarmaya çalış
                if not resim_url and icerik:
                    img_match = re.search(r'<img[^>]+src="([^">]+)"', icerik)
                    if img_match:
                        resim_url = img_match.group(1)
                
                # Yayın tarihini belirle
                yayin_tarihi = datetime.now().isoformat()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        yayin_tarihi = time.strftime('%Y-%m-%dT%H:%M:%S', entry.published_parsed)
                    except:
                        pass
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    try:
                        yayin_tarihi = time.strftime('%Y-%m-%dT%H:%M:%S', entry.updated_parsed)
                    except:
                        pass
                
                # Haber kaynağını belirle
                kaynak = feed_url
                if hasattr(feed, 'feed') and hasattr(feed.feed, 'title'):
                    kaynak = feed.feed.title
                elif hasattr(entry, 'source') and hasattr(entry.source, 'title'):
                    kaynak = entry.source.title
                
                haber = {
                    'baslik': entry.title if hasattr(entry, 'title') else "Başlık yok",
                    'icerik': icerik,
                    'ozet': "",  # Özetleme işlemi sonra yapılacak
                    'url': entry.link if hasattr(entry, 'link') else "",
                    'tarih': yayin_tarihi,
                    'kaynak': kaynak,
                    'kategori': kategori,
                    'resim_url': resim_url
                }
                
                # Özet oluştur
                logger.info(f"Haber özetleniyor: {haber['baslik']}")
                haber['ozet'] = ozet_olustur(haber['icerik'])
                
                # Özet çok kısaysa veya boşsa, başlığı kullan
                if not haber['ozet'] or len(haber['ozet']) < 20:
                    haber['ozet'] = haber['baslik']
                
                haberler.append(haber)
        except Exception as e:
            logger.error(f"Feed çekme hatası ({feed_url}): {e}")
    
    logger.info(f"{kategori} kategorisinde {len(haberler)} haber çekildi.")
    return haberler

def haberleri_veritabanina_kaydet(haberler):
    """Haberleri veritabanına kaydeder"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    eklenen = 0
    guncellenen = 0
    
    for haber in haberler:
        # URL'ye göre kontrol et, varsa güncelle yoksa ekle
        cursor.execute('SELECT id FROM haberler WHERE url = ?', (haber['url'],))
        result = cursor.fetchone()
        
        if result:
            # Güncelle
            cursor.execute('''
            UPDATE haberler 
            SET baslik = ?, ozet = ?, icerik = ?, tarih = ?
            WHERE url = ?
            ''', (haber['baslik'], haber['ozet'], haber['icerik'], haber['tarih'], haber['url']))
            guncellenen += 1
        else:
            # Yeni ekle
            cursor.execute('''
            INSERT INTO haberler (baslik, ozet, icerik, kategori, kaynak, url, resim_url, tarih)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                haber['baslik'], haber['ozet'], haber['icerik'], haber['kategori'],
                haber['kaynak'], haber['url'], haber['resim_url'], haber['tarih']
            ))
            eklenen += 1
    
    conn.commit()
    conn.close()
    logger.info(f"Veritabanına {eklenen} haber eklendi, {guncellenen} haber güncellendi.")

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

# LLM modelini başlat
init_llm_model()

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

if __name__ == '__main__':
    logger.info(f"Uygulama başlatılıyor... LLM Tipi: {LLM_TYPE}, Model: {LLM_MODEL if LLM_TYPE == 'transformers' else 'API tabanlı'}")
    app.run(debug=True) 