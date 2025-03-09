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
from logging.handlers import RotatingFileHandler

# .env dosyasını yükle
load_dotenv()

app = Flask(__name__, 
            static_folder="../frontend/static",
            template_folder="../frontend")

# Veritabanı bağlantısı
def get_db_connection():
    conn = sqlite3.connect('haber_ozet.db')
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
        url TEXT NOT NULL,
        resim_url TEXT,
        tarih TIMESTAMP NOT NULL,
        olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

# Veritabanını başlat
init_db()

# RSS kaynakları
RSS_FEEDS = {
    'spor': [
        'https://spor.haberler.com/rss/',
        'https://www.sporx.com/rss/',
    ],
    'ekonomi': [
        'https://ekonomi.haberler.com/rss/',
        'https://www.bloomberght.com/rss',
    ],
    'teknoloji': [
        'https://www.chip.com.tr/rss/',
        'https://shiftdelete.net/feed',
    ],
    'gundem': [
        'https://www.hurriyet.com.tr/rss/gundem',
        'https://www.sozcu.com.tr/rss/gundem.xml',
    ]
}

# LLM modelini yükle
AVAILABLE_MODELS = {
    'mlsum/bert2bert': 'BERTurk (Türkçe)',
    'google/mt5-small': 'MT5 (Çoklu Dil, Hızlı)',
    'facebook/mbart-large-cc25': 'mBART (Çoklu Dil, Detaylı)',
    'tiiuae/falcon-7b-instruct': 'Falcon (Güçlü)'
}

summarizer = None
sentiment_analyzer = None

def init_models(model_name='mlsum/bert2bert'):
    """Modelleri başlat"""
    global summarizer, sentiment_analyzer
    try:
        # Özetleme modeli
        summarizer = pipeline("summarization", model=model_name)
        # Duygu analizi modeli (Türkçe için)
        sentiment_analyzer = pipeline("sentiment-analysis", model="savasy/bert-base-turkish-sentiment")
        print(f"Modeller başarıyla yüklendi: {model_name}")
        return {"durum": "başarılı", "basit_mod": False}
    except Exception as e:
        print(f"Model yükleme hatası: {e}")
        # Yedek fonksiyonları kullan
        summarizer = basit_ozet_wrapper
        sentiment_analyzer = basit_duygu_analizi
        return {"durum": "başarılı", "basit_mod": True}

def basit_ozet_wrapper(metin, **kwargs):
    return [{"summary_text": basit_ozet(metin)}]

def basit_ozet(metin):
    """Basit özetleme fonksiyonu"""
    cumleler = metin.split('.')
    return '. '.join(cumleler[:3]) + '.'

def basit_duygu_analizi(metin):
    """Basit duygu analizi"""
    # Pozitif ve negatif kelime listeleri
    pozitif = ['başarı', 'mutlu', 'güzel', 'iyi', 'kazanç', 'artış', 'olumlu', 'sevindi']
    negatif = ['kaza', 'ölüm', 'kötü', 'zarar', 'düşüş', 'kayıp', 'kriz', 'üzücü']
    
    metin = metin.lower()
    puan = 0
    
    for kelime in pozitif:
        if kelime in metin:
            puan += 1
    for kelime in negatif:
        if kelime in metin:
            puan -= 1
            
    if puan > 0:
        return [{'label': 'positive'}]
    elif puan < 0:
        return [{'label': 'negative'}]
    return [{'label': 'neutral'}]

def ozet_olustur(metin, ozet_modu="normal"):
    """Metni özetler"""
    if len(metin) < 100:  # Çok kısa metinleri özetleme
        return metin
    
    try:
        # Metni cümlelere ayır
        cumleler = [c.strip() for c in metin.split('.') if len(c.strip()) > 0]
        
        # Özet uzunluğunu ayarla
        if ozet_modu == "super":
            max_cumleler = 2
        else:
            max_cumleler = 4
            
        if summarizer == basit_ozet_wrapper:
            return '. '.join(cumleler[:max_cumleler]) + '.'
            
        # Transformers modeliyle özet oluştur
        ozet = summarizer(metin, max_length=512, min_length=30, do_sample=False)
        ozet_cumleler = [c.strip() for c in ozet[0]['summary_text'].split('.') if len(c.strip()) > 0]
        
        return '. '.join(ozet_cumleler[:max_cumleler]) + '.'
    except Exception as e:
        print(f"Özetleme hatası: {e}")
        return basit_ozet(metin)

def haberleri_getir(kategori):
    """Belirli bir kategorideki RSS feed'lerinden haberleri çeker"""
    haberler = []
    
    if kategori not in RSS_FEEDS:
        return haberler
    
    for feed_url in RSS_FEEDS[kategori]:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                haber = {
                    'baslik': entry.title,
                    'icerik': entry.description if hasattr(entry, 'description') else "",
                    'ozet': "",
                    'url': entry.link,
                    'tarih': datetime.now().isoformat(),
                    'kaynak': feed.feed.title if hasattr(feed.feed, 'title') else feed_url,
                    'kategori': kategori,
                    'resim_url': "",
                    'duygu': 'neutral'  # Varsayılan duygu
                }
                
                # Özet ve duygu analizi
                haber['ozet'] = ozet_olustur(haber['icerik'])
                try:
                    duygu = sentiment_analyzer(haber['icerik'])[0]['label']
                    haber['duygu'] = duygu
                except Exception as e:
                    print(f"Duygu analizi hatası: {e}")
                
                haberler.append(haber)
        except Exception as e:
            print(f"Feed çekme hatası ({feed_url}): {e}")
    
    return haberler

def haberleri_veritabanina_kaydet(haberler):
    """Haberleri veritabanına kaydeder"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
        else:
            # Yeni ekle
            cursor.execute('''
            INSERT INTO haberler (baslik, ozet, icerik, kategori, kaynak, url, resim_url, tarih)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                haber['baslik'], haber['ozet'], haber['icerik'], haber['kategori'],
                haber['kaynak'], haber['url'], haber['resim_url'], haber['tarih']
            ))
    
    conn.commit()
    conn.close()

def arkaplan_haber_guncelleme():
    """Arka planda çalışarak haberleri düzenli olarak günceller"""
    while True:
        print("Haberler güncelleniyor...")
        for kategori in RSS_FEEDS.keys():
            haberler = haberleri_getir(kategori)
            haberleri_veritabanina_kaydet(haberler)
        
        # 30 dakikada bir güncelle
        time.sleep(1800)

# Arka plan görevini başlat
haber_guncelleme_thread = threading.Thread(target=arkaplan_haber_guncelleme)
haber_guncelleme_thread.daemon = True
haber_guncelleme_thread.start()

# Log dosyası yapılandırması
log_handler = RotatingFileHandler('haber_ozet.log', maxBytes=10*1024*1024, backupCount=5)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(log_handler)
app.logger.setLevel(logging.INFO)

@app.route('/')
def index():
    """Ana sayfa"""
    return render_template('index.html')

@app.route('/api/ozet', methods=['POST'])
def ozet_olustur_api():
    """Metin özetleme API'si"""
    data = request.get_json()
    metin = data.get('metin', '')
    ozet_modu = data.get('ozet_modu', 'normal')
    
    if not metin:
        return jsonify({"hata": "Metin boş olamaz"}), 400
    
    ozet = ozet_olustur(metin, ozet_modu)
    return jsonify({"ozet": ozet})

@app.route('/api/haberler')
def tum_haberler():
    """Tüm haberleri döndürür"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    ozet_modu = request.args.get('ozet_modu', 'normal')
    
    cursor.execute('SELECT * FROM haberler ORDER BY tarih DESC LIMIT 50')
    haberler = []
    for row in cursor.fetchall():
        haber = dict(row)
        haber['ozet'] = ozet_olustur(haber['icerik'], ozet_modu)
        haberler.append(haber)
    
    conn.close()
    return jsonify(haberler)

@app.route('/api/haberler/<kategori>')
def kategori_haberleri(kategori):
    """Belirli bir kategorideki haberleri döndürür"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    ozet_modu = request.args.get('ozet_modu', 'normal')
    
    cursor.execute('SELECT * FROM haberler WHERE kategori = ? ORDER BY tarih DESC LIMIT 20', (kategori,))
    haberler = []
    for row in cursor.fetchall():
        haber = dict(row)
        haber['ozet'] = ozet_olustur(haber['icerik'], ozet_modu)
        haberler.append(haber)
    
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

@app.route('/api/models')
def get_models():
    """Kullanılabilir modelleri döndürür"""
    return jsonify(AVAILABLE_MODELS)

@app.route('/api/model/durum')
def get_model_status():
    """Model durumunu döndürür"""
    return jsonify({
        "basit_mod": summarizer == basit_ozet_wrapper
    })

@app.route('/api/model', methods=['POST'])
def set_model():
    """Kullanılacak modeli ayarlar"""
    data = request.get_json()
    model_name = data.get('model')
    
    if model_name not in AVAILABLE_MODELS:
        return jsonify({"hata": "Geçersiz model"}), 400
        
    sonuc = init_models(model_name)
    app.logger.info(f"Model değiştirildi: {model_name} - Basit mod: {sonuc['basit_mod']}")
    return jsonify(sonuc)

if __name__ == '__main__':
    app.run(debug=True) 