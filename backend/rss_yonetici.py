#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSS Feed Yöneticisi
-------------------
Bu script, haber özet platformu için RSS feed'lerini yönetmeye yardımcı olur.
Yeni feed'ler ekleyebilir, mevcut feed'leri test edebilir ve feed'leri kategorilere göre düzenleyebilirsiniz.
"""

import feedparser
import json
import os
import sys
import time
from datetime import datetime

# Varsayılan RSS feed'leri
DEFAULT_FEEDS = {
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

# RSS feed'leri için yapılandırma dosyası
CONFIG_FILE = 'rss_feeds.json'

def load_feeds():
    """Yapılandırma dosyasından RSS feed'lerini yükler"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Varsayılan feed'leri kaydet ve döndür
        save_feeds(DEFAULT_FEEDS)
        return DEFAULT_FEEDS

def save_feeds(feeds):
    """RSS feed'lerini yapılandırma dosyasına kaydeder"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(feeds, f, ensure_ascii=False, indent=4)
    print(f"Feed'ler {CONFIG_FILE} dosyasına kaydedildi.")

def test_feed(url):
    """Bir RSS feed'ini test eder ve sonuçları gösterir"""
    print(f"Feed test ediliyor: {url}")
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            print(f"UYARI: Feed'de sorun olabilir: {feed.bozo_exception}")
        
        print(f"Başlık: {feed.feed.title if hasattr(feed.feed, 'title') else 'Başlık bulunamadı'}")
        print(f"Açıklama: {feed.feed.description if hasattr(feed.feed, 'description') else 'Açıklama bulunamadı'}")
        print(f"Haber sayısı: {len(feed.entries)}")
        
        if len(feed.entries) > 0:
            print("\nİlk haber örneği:")
            entry = feed.entries[0]
            print(f"Başlık: {entry.title if hasattr(entry, 'title') else 'Başlık bulunamadı'}")
            print(f"Link: {entry.link if hasattr(entry, 'link') else 'Link bulunamadı'}")
            print(f"Yayın tarihi: {entry.published if hasattr(entry, 'published') else 'Tarih bulunamadı'}")
            print(f"İçerik uzunluğu: {len(entry.description) if hasattr(entry, 'description') else 'İçerik bulunamadı'} karakter")
        
        return True
    except Exception as e:
        print(f"HATA: Feed test edilirken bir sorun oluştu: {e}")
        return False

def add_feed(category, url):
    """Belirli bir kategoriye yeni bir RSS feed'i ekler"""
    feeds = load_feeds()
    
    # Kategori yoksa oluştur
    if category not in feeds:
        feeds[category] = []
    
    # URL zaten varsa ekleme
    if url in feeds[category]:
        print(f"Bu feed zaten '{category}' kategorisinde mevcut.")
        return
    
    # Feed'i test et
    if test_feed(url):
        feeds[category].append(url)
        save_feeds(feeds)
        print(f"Feed başarıyla '{category}' kategorisine eklendi.")
    else:
        print("Feed eklenemedi. Lütfen URL'yi kontrol edin.")

def remove_feed(category, url):
    """Belirli bir kategoriden bir RSS feed'ini kaldırır"""
    feeds = load_feeds()
    
    if category not in feeds:
        print(f"'{category}' kategorisi bulunamadı.")
        return
    
    if url not in feeds[category]:
        print(f"Bu feed '{category}' kategorisinde bulunamadı.")
        return
    
    feeds[category].remove(url)
    save_feeds(feeds)
    print(f"Feed başarıyla '{category}' kategorisinden kaldırıldı.")

def list_feeds():
    """Tüm RSS feed'lerini kategorilere göre listeler"""
    feeds = load_feeds()
    
    print("\n=== RSS Feed'leri ===")
    for category, urls in feeds.items():
        print(f"\n## {category.upper()} ##")
        for i, url in enumerate(urls, 1):
            print(f"{i}. {url}")
    print("\n====================")

def test_all_feeds():
    """Tüm RSS feed'lerini test eder"""
    feeds = load_feeds()
    
    print("\n=== Tüm Feed'leri Test Etme ===")
    for category, urls in feeds.items():
        print(f"\n## {category.upper()} ##")
        for url in urls:
            print(f"\nTest ediliyor: {url}")
            test_feed(url)
            time.sleep(1)  # Sunucuları çok hızlı isteklerle yüklememek için
    print("\n===============================")

def show_help():
    """Yardım mesajını gösterir"""
    print("""
RSS Feed Yöneticisi - Kullanım:
-------------------------------
python rss_yonetici.py list                       - Tüm feed'leri listele
python rss_yonetici.py test <url>                 - Belirli bir feed'i test et
python rss_yonetici.py test-all                   - Tüm feed'leri test et
python rss_yonetici.py add <kategori> <url>       - Yeni bir feed ekle
python rss_yonetici.py remove <kategori> <url>    - Bir feed'i kaldır
python rss_yonetici.py help                       - Bu yardım mesajını göster
    """)

def main():
    """Ana fonksiyon"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_feeds()
    elif command == "test" and len(sys.argv) >= 3:
        test_feed(sys.argv[2])
    elif command == "test-all":
        test_all_feeds()
    elif command == "add" and len(sys.argv) >= 4:
        add_feed(sys.argv[2], sys.argv[3])
    elif command == "remove" and len(sys.argv) >= 4:
        remove_feed(sys.argv[2], sys.argv[3])
    elif command == "help":
        show_help()
    else:
        print("Geçersiz komut. Yardım için 'python rss_yonetici.py help' komutunu kullanın.")

if __name__ == "__main__":
    main() 