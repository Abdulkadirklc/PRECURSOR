// DOM elementleri
const haberContainer = document.getElementById('haber-container');
const kategoriMenu = document.getElementById('kategori-menu');
const loadingElement = document.getElementById('loading');

// Mevcut kategori
let aktifKategori = 'tum';

// Özet modu yönetimi
let ozetModu = 'normal';

// Model seçimi
const modelSelect = document.getElementById('model-select');

// Sayfa yüklendiğinde
document.addEventListener('DOMContentLoaded', () => {
    // Kategorileri yükle
    kategorileriYukle();
    
    // Tüm haberleri yükle
    haberleriYukle('tum');
    
    // Tüm Haberler butonuna tıklama olayı ekle
    document.querySelector('a[data-kategori="tum"]').addEventListener('click', (e) => {
        e.preventDefault();
        
        // Aktif sınıfını güncelle
        document.querySelectorAll('#kategori-menu a').forEach(link => {
            link.classList.remove('active');
        });
        e.target.classList.add('active');
        
        // Haberleri yükle
        aktifKategori = 'tum';
        haberleriYukle('tum');
    });

    // Özet modu butonlarına tıklama olayı ekle
    document.getElementById('normal-ozet').addEventListener('click', function() {
        setOzetModu('normal');
    });

    document.getElementById('super-ozet').addEventListener('click', function() {
        setOzetModu('super');
    });

    // Modelleri yükle
    modelleriYukle();

    // Model durumunu kontrol et
    modelDurumunuKontrolEt();
});

// Kategorileri API'den çek ve menüyü oluştur
async function kategorileriYukle() {
    try {
        const response = await fetch('/api/kategoriler');
        const kategoriler = await response.json();
        
        // Kategori menüsünü oluştur
        kategoriler.forEach(kategori => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = '#';
            a.textContent = kategoriIsmiDuzenle(kategori);
            a.dataset.kategori = kategori;
            a.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Aktif sınıfını güncelle
                document.querySelectorAll('#kategori-menu a').forEach(link => {
                    link.classList.remove('active');
                });
                a.classList.add('active');
                
                // Haberleri yükle
                aktifKategori = kategori;
                haberleriYukle(kategori);
            });
            
            li.appendChild(a);
            kategoriMenu.appendChild(li);
        });
    } catch (error) {
        console.error('Kategoriler yüklenirken hata oluştu:', error);
    }
}

// Haberleri API'den çek ve görüntüle
async function haberleriYukle(kategori = 'tum') {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('haber-container').innerHTML = '';

    try {
        const url = kategori === 'tum' 
            ? `/api/haberler?ozet_modu=${ozetModu}`
            : `/api/haberler/${kategori}?ozet_modu=${ozetModu}`;
            
        const response = await fetch(url);
        const haberler = await response.json();

        if (haberler.length === 0) {
            document.getElementById('haber-container').innerHTML = '<p class="no-news">Bu kategoride haber bulunamadı.</p>';
        } else {
            haberler.forEach(haber => {
                const haberHTML = createHaberCard(haber);
                document.getElementById('haber-container').innerHTML += haberHTML;
            });
        }
    } catch (error) {
        console.error('Haber yükleme hatası:', error);
        document.getElementById('haber-container').innerHTML = '<p class="error">Haberler yüklenirken bir hata oluştu.</p>';
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

// Kategori ismini düzenle (ilk harf büyük, diğerleri küçük)
function kategoriIsmiDuzenle(kategori) {
    return kategori.charAt(0).toUpperCase() + kategori.slice(1).toLowerCase();
}

function setOzetModu(mod) {
    ozetModu = mod;
    document.querySelectorAll('.ozet-modu button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`${mod}-ozet`).classList.add('active');
    
    // Mevcut haberleri yeni özet moduyla yeniden yükle
    const aktifKategori = document.querySelector('#kategori-menu a.active').dataset.kategori;
    haberleriYukle(aktifKategori);
}

// Modelleri yükle
async function modelleriYukle() {
    try {
        const response = await fetch('/api/models');
        const modeller = await response.json();
        
        // Model seçeneklerini oluştur
        Object.entries(modeller).forEach(([key, value]) => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = value;
            modelSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Modeller yüklenirken hata:', error);
    }
}

// Model değiştiğinde
modelSelect.addEventListener('change', async () => {
    const model = modelSelect.value;
    const modelDurum = document.getElementById('model-durum');
    modelDurum.textContent = 'Yükleniyor...';
    modelDurum.className = 'model-durum';
    
    try {
        const response = await fetch('/api/model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model })
        });
        
        if (response.ok) {
            // Model durumunu kontrol et
            const durum = await response.json();
            if (durum.basit_mod) {
                modelDurum.textContent = 'Basit Mod';
                modelDurum.classList.add('basit');
            } else {
                modelDurum.textContent = 'Yapay Zeka';
                modelDurum.classList.add('yapay-zeka');
            }
            // Haberleri yeniden yükle
            haberleriYukle(aktifKategori);
        }
    } catch (error) {
        console.error('Model değiştirme hatası:', error);
        modelDurum.textContent = 'Hata!';
        modelDurum.classList.add('basit');
    }
});

// Sayfa yüklendiğinde model durumunu kontrol et
async function modelDurumunuKontrolEt() {
    const modelDurum = document.getElementById('model-durum');
    try {
        const response = await fetch('/api/model/durum');
        const durum = await response.json();
        if (durum.basit_mod) {
            modelDurum.textContent = 'Basit Mod';
            modelDurum.classList.add('basit');
        } else {
            modelDurum.textContent = 'Yapay Zeka';
            modelDurum.classList.add('yapay-zeka');
        }
    } catch (error) {
        console.error('Model durum kontrolü hatası:', error);
        modelDurum.textContent = 'Bilinmiyor';
    }
}

// Duygu ikonlarını oluştur
function getDuyguIkonu(duygu) {
    const ikonlar = {
        'positive': '<i class="fas fa-smile duygu-ikonu duygu-positive"></i>',
        'negative': '<i class="fas fa-frown duygu-ikonu duygu-negative"></i>',
        'neutral': '<i class="fas fa-meh duygu-ikonu duygu-neutral"></i>'
    };
    return ikonlar[duygu] || ikonlar['neutral'];
}

// Haber kartı oluştur
function createHaberCard(haber) {
    return `
        <div class="haber-kart">
            ${haber.resim_url ? `<div class="haber-resim" style="background-image: url(${haber.resim_url})"></div>` : ''}
            <div class="haber-icerik">
                <span class="haber-kategori ${haber.kategori}">${kategoriIsmiDuzenle(haber.kategori)}</span>
                <h2 class="haber-baslik">
                    ${haber.baslik}
                    ${getDuyguIkonu(haber.duygu)}
                </h2>
                <p class="haber-ozet">${haber.ozet}</p>
                <div class="haber-kaynak">
                    <span>Kaynak: ${haber.kaynak}</span>
                    <a href="${haber.url}" target="_blank" class="haber-link">Habere Git</a>
                </div>
            </div>
        </div>
    `;
} 