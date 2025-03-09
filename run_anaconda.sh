#!/bin/bash

echo "PRECURSOR - Haber Özet Platformu"
echo "================================================"
echo

# Çalışma dizinini kontrol et
cd "$(dirname "$0")"
echo "Çalışma dizini: $(pwd)"

# Backend dizinini kontrol et
if [ ! -d "backend" ]; then
    echo "HATA: Backend dizini bulunamadı!"
    read -p "Devam etmek için bir tuşa basın..."
    exit 1
fi

# GPU kontrolü
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU bulundu. CUDA desteği aktif edilecek..."
    GPU_AVAILABLE=1
else
    echo "GPU bulunamadı veya NVIDIA sürücüleri yüklü değil. CPU modu kullanılacak..."
    GPU_AVAILABLE=0
fi

# Conda ortamını kontrol et/oluştur
if ! conda activate precursor 2>/dev/null; then
    echo "Precursor ortamı bulunamadı. Ortam oluşturuluyor..."
    conda create -n precursor python=3.8 -y
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate precursor
fi

# Gerekli paketleri yükle
echo "Gerekli paketler kontrol ediliyor/yükleniyor..."
conda install -c conda-forge flask=2.0.1 -y
conda install -c conda-forge feedparser=6.0.8 -y
conda install -c conda-forge python-dotenv=0.19.2 -y
conda install -c conda-forge transformers=4.18.0 -y
conda install -c conda-forge nltk=3.6.5 -y

# PyTorch yükle (GPU/CPU kontrolü)
echo "PyTorch yükleniyor..."
if [ "$GPU_AVAILABLE" = "1" ]; then
    echo "GPU destekli PyTorch yükleniyor..."
    conda install -c pytorch pytorch torchvision torchaudio pytorch-cuda=11.8 -y
else
    echo "CPU versiyonu PyTorch yükleniyor..."
    conda install -c pytorch pytorch torchvision torchaudio cpuonly -y
fi

# CUDA sürümünü kontrol et (GPU varsa)
if [ "$GPU_AVAILABLE" = "1" ]; then
    python -c "import torch; print('CUDA Kullanılabilir:', torch.cuda.is_available()); print('CUDA Sürüm:', torch.version.cuda if torch.cuda.is_available() else 'Yok')"
fi

# Diğer gerekli paketler
pip install --no-cache-dir sentencepiece

# Model seçimi
echo
echo "LLM Modeli Seçin:"
echo "1. mlsum/bert2bert (Varsayılan, Türkçe haber özetleme)"
echo "2. google/mt5-small (Çoklu dil desteği, hafif model)"
echo "3. facebook/mbart-large-cc25 (Çoklu dil desteği, güçlü model)"
echo "4. tiiuae/falcon-7b-instruct (Güçlü dil modeli, Türkçe destekli)"
echo
read -p "Seçiminiz (1-4, varsayılan: 1): " model_choice

# Özet modu seçimi
echo
echo "Özetleme Modu Seçin:"
echo "1. Normal Özet (3-4 cümle)"
echo "2. Süper Özet (En fazla 2 cümle)"
echo
read -p "Seçiminiz (1-2, varsayılan: 1): " ozet_modu

# Model seçimini ayarla
if [ "$model_choice" = "2" ]; then
    LLM_MODEL="google/mt5-small"
elif [ "$model_choice" = "3" ]; then
    LLM_MODEL="facebook/mbart-large-cc25"
elif [ "$model_choice" = "4" ]; then
    LLM_MODEL="tiiuae/falcon-7b-instruct"
else
    LLM_MODEL="mlsum/bert2bert"
fi

# Özet modunu ayarla
if [ "$ozet_modu" = "2" ]; then
    OZET_MODU="super"
else
    OZET_MODU="normal"
fi

# .env dosyasını oluştur
cd backend
echo "# LLM model ayarları" > .env
echo "LLM_TYPE=transformers" >> .env
echo "LLM_MODEL=$LLM_MODEL" >> .env
echo "OZET_MODU=$OZET_MODU" >> .env
echo "GPU_AVAILABLE=$GPU_AVAILABLE" >> .env

# Uygulamayı başlat
echo
echo "Uygulama başlatılıyor..."
echo "Tarayıcınızda http://localhost:5000 adresine giderek uygulamayı görüntüleyebilirsiniz."
echo "Çıkmak için Ctrl+C tuşlarına basın."
echo

python app.py

if [ $? -ne 0 ]; then
    echo "HATA: Uygulama çalıştırılırken bir hata oluştu!"
    read -p "Devam etmek için bir tuşa basın..."
    exit 1
fi

echo "Uygulama sonlandı."
read -p "Devam etmek için bir tuşa basın..." 