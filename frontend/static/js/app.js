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

// Model değişikliğini dinle
document.getElementById('model-select').addEventListener('change', function() {
    const modelDurum = document.getElementById('model-durum');
    modelDurum.textContent = 'Model değiştiriliyor...';
    modelDurum.className = 'model-durum yukleniyor';

    fetch('/api/change_model', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            model: this.value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            modelDurum.textContent = 'Model hazır';
            modelDurum.className = 'model-durum hazir';
            loadNews(); // Haberleri yeni modelle yükle
        } else {
            modelDurum.textContent = 'Hata: ' + data.error;
            modelDurum.className = 'model-durum hata';
        }
    })
    .catch(error => {
        modelDurum.textContent = 'Hata oluştu';
        modelDurum.className = 'model-durum hata';
        console.error('Model değiştirme hatası:', error);
    });
});

// Özet modu değişikliğini dinle
document.querySelectorAll('.ozet-modu .btn').forEach(button => {
    button.addEventListener('click', function() {
        // Aktif sınıfı güncelle
        document.querySelectorAll('.ozet-modu .btn').forEach(btn => {
            btn.classList.remove('active');
        });
        this.classList.add('active');

        // Özet modunu güncelle
        const mode = this.getAttribute('data-mode');
        fetch('/api/change_summary_mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mode: mode
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadNews(); // Haberleri yeni özet moduyla yükle
            }
        })
        .catch(error => {
            console.error('Özet modu değiştirme hatası:', error);
        });
    });
});

// Sayfa yüklendiğinde model durumunu kontrol et
window.addEventListener('DOMContentLoaded', function() {
    const modelDurum = document.getElementById('model-durum');
    modelDurum.textContent = 'Model kontrol ediliyor...';
    modelDurum.className = 'model-durum yukleniyor';

    fetch('/api/model_status')
        .then(response => response.json())
        .then(data => {
            if (data.ready) {
                modelDurum.textContent = 'Model hazır';
                modelDurum.className = 'model-durum hazir';
            } else {
                modelDurum.textContent = 'Model yükleniyor...';
                modelDurum.className = 'model-durum yukleniyor';
            }
        })
        .catch(error => {
            modelDurum.textContent = 'Hata oluştu';
            modelDurum.className = 'model-durum hata';
            console.error('Model durumu kontrolü hatası:', error);
        });
});

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