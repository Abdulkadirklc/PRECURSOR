# Anaconda ile Haber Özet Platformu Kurulumu

Anaconda kullanarak haber özet platformunu kurmak ve çalıştırmak için aşağıdaki adımları izleyebilirsiniz:

## 1. Yeni Conda Ortamı Oluşturma

```bash
# Yeni bir conda ortamı oluşturun
conda create -n haber-ozet python=3.8

# Ortamı aktifleştirin
conda activate haber-ozet
```

## 2. Gerekli Paketleri Yükleme

```bash
# Temel paketleri conda ile yükleyin
conda install -c conda-forge flask=2.0.1
conda install -c conda-forge feedparser=6.0.8
conda install -c conda-forge requests=2.26.0
conda install -c conda-forge beautifulsoup4=4.10.0
conda install -c conda-forge python-dotenv=0.19.2
conda install -c conda-forge nltk=3.6.5
conda install -c conda-forge scikit-learn=1.0.1
conda install -c conda-forge sqlalchemy=1.4.27

# PyTorch ve Transformers'ı yükleyin
conda install -c pytorch pytorch=1.11.0
pip install transformers==4.18.0
```

## 3. Uygulamayı Çalıştırma

```bash
# Backend klasörüne gidin
cd backend

# Flask uygulamasını çalıştırın
python app.py
```

## 4. Tarayıcıda Görüntüleme

Tarayıcınızda `http://localhost:5000` adresine giderek uygulamayı görüntüleyebilirsiniz.

## Not

Eğer conda ile paket yüklemede sorun yaşarsanız, pip kullanarak da yükleyebilirsiniz:

```bash
pip install -r backend/requirements.txt
```

Transformers modelinin ilk yüklemesi biraz zaman alabilir, çünkü model dosyaları indirilecektir. 