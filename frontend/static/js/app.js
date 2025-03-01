// DOM elementleri
const haberContainer = document.getElementById('haber-container');
const kategoriMenu = document.getElementById('kategori-menu');
const loadingElement = document.getElementById('loading');

// Mevcut kategori
let aktifKategori = 'tum';

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
async function haberleriYukle(kategori) {
    // Yükleniyor göster
    loadingElement.style.display = 'block';
    haberContainer.innerHTML = '';
    
    try {
        const url = kategori === 'tum' ? '/api/haberler' : `/api/haberler/${kategori}`;
        const response = await fetch(url);
        const haberler = await response.json();
        
        // Yükleniyor gizle
        loadingElement.style.display = 'none';
        
        // Haber kartlarını oluştur
        if (haberler.length === 0) {
            haberContainer.innerHTML = '<div class="no-results">Bu kategoride haber bulunamadı.</div>';
            return;
        }
        
        haberler.forEach(haber => {
            const haberKart = document.createElement('div');
            haberKart.className = 'haber-kart';
            
            // Resim varsa ekle
            if (haber.resim_url) {
                const haberResim = document.createElement('div');
                haberResim.className = 'haber-resim';
                haberResim.style.backgroundImage = `url(${haber.resim_url})`;
                haberKart.appendChild(haberResim);
            }
            
            const haberIcerik = document.createElement('div');
            haberIcerik.className = 'haber-icerik';
            
            // Kategori etiketi
            const haberKategori = document.createElement('span');
            haberKategori.className = `haber-kategori ${haber.kategori}`;
            haberKategori.textContent = kategoriIsmiDuzenle(haber.kategori);
            haberIcerik.appendChild(haberKategori);
            
            // Başlık
            const haberBaslik = document.createElement('h2');
            haberBaslik.className = 'haber-baslik';
            haberBaslik.textContent = haber.baslik;
            haberIcerik.appendChild(haberBaslik);
            
            // Özet
            const haberOzet = document.createElement('p');
            haberOzet.className = 'haber-ozet';
            haberOzet.textContent = haber.ozet;
            haberIcerik.appendChild(haberOzet);
            
            // Kaynak ve link
            const haberKaynak = document.createElement('div');
            haberKaynak.className = 'haber-kaynak';
            
            const kaynakBilgisi = document.createElement('span');
            kaynakBilgisi.textContent = `Kaynak: ${haber.kaynak}`;
            haberKaynak.appendChild(kaynakBilgisi);
            
            const haberLink = document.createElement('a');
            haberLink.className = 'haber-link';
            haberLink.href = haber.url;
            haberLink.target = '_blank';
            haberLink.textContent = 'Habere Git';
            haberKaynak.appendChild(haberLink);
            
            haberIcerik.appendChild(haberKaynak);
            haberKart.appendChild(haberIcerik);
            
            haberContainer.appendChild(haberKart);
        });
    } catch (error) {
        console.error('Haberler yüklenirken hata oluştu:', error);
        loadingElement.style.display = 'none';
        haberContainer.innerHTML = '<div class="error">Haberler yüklenirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.</div>';
    }
}

// Kategori ismini düzenle (ilk harf büyük, diğerleri küçük)
function kategoriIsmiDuzenle(kategori) {
    return kategori.charAt(0).toUpperCase() + kategori.slice(1).toLowerCase();
} 