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

def temizle_veritabani():
    """Veritabanını temizler ve yeni baştan başlar"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tüm haberleri sil
    cursor.execute('DELETE FROM haberler')
    
    conn.commit()
    conn.close()
    print("Veritabanı temizlendi, yeni haberler yüklenecek...")

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
        url TEXT NOT NULL UNIQUE,
        resim_url TEXT,
        tarih TIMESTAMP NOT NULL,
        olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

# Veritabanını başlat ve temizle
init_db()
temizle_veritabani()

def ilk_haberleri_yukle():
    """Uygulama başlatıldığında tüm kategorilerden haberleri yükler"""
    print("İlk haberler yükleniyor...")
    for kategori in RSS_FEEDS.keys():
        print(f"{kategori} kategorisi yükleniyor...")
        haberler = haberleri_getir(kategori)
        haberleri_veritabanina_kaydet(haberler)
    print("İlk haberler başarıyla yüklendi.")

# İlk haberleri yükle
ilk_haberleri_yukle()

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

# Transformers modelini yükle
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def ozet_olustur(metin, max_length=150):
    """Metni özetler"""
    if len(metin) < 100:  # Çok kısa metinleri özetleme
        return metin
    
    try:
        ozet = summarizer(metin, max_length=max_length, min_length=30, do_sample=False)
        return ozet[0]['summary_text']
    except Exception as e:
        print(f"Özetleme hatası: {e}")
        # Basit bir alternatif: ilk birkaç cümleyi al
        return ". ".join(metin.split(". ")[:3]) + "."

def haberleri_getir(kategori):
    """Belirli bir kategorideki RSS feed'lerinden haberleri çeker"""
    haberler = []
    
    if kategori not in RSS_FEEDS:
        return haberler
    
    for feed_url in RSS_FEEDS[kategori]:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:  # Her feed'den en fazla 5 haber al
                haber = {
                    'baslik': entry.title,
                    'icerik': entry.description if hasattr(entry, 'description') else "",
                    'ozet': "",  # Özetleme işlemi sonra yapılacak
                    'url': entry.link,
                    'tarih': datetime.now().isoformat(),
                    'kaynak': feed.feed.title if hasattr(feed.feed, 'title') else feed_url,
                    'kategori': kategori,
                    'resim_url': ""  # Resim URL'si varsa eklenecek
                }
                
                # Özet oluştur
                haber['ozet'] = ozet_olustur(haber['icerik'])
                
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

if __name__ == '__main__':
    app.run(debug=True) 