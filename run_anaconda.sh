#!/bin/bash

echo "PRECURSOR - Haber Özet Platformu"
echo "================================================"

# Conda ortamını etkinleştir
if ! conda activate haber-ozet 2>/dev/null; then
    echo "Haber-ozet ortamı bulunamadı. Ortam oluşturuluyor..."
    conda create -n haber-ozet python=3.8 -y
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate haber-ozet
    
    echo "Gerekli paketler yükleniyor..."
    conda install -c conda-forge flask=2.0.1 -y
    conda install -c conda-forge feedparser=6.0.8 -y
    conda install -c conda-forge requests=2.26.0 -y
    conda install -c conda-forge beautifulsoup4=4.10.0 -y
    conda install -c conda-forge python-dotenv=0.19.2 -y
    conda install -c conda-forge nltk=3.6.5 -y
    conda install -c conda-forge scikit-learn=1.0.1 -y
    conda install -c conda-forge sqlalchemy=1.4.27 -y
    
    echo "PyTorch yükleniyor (GPU destekli)..."
    conda install -c pytorch pytorch torchvision torchaudio cudatoolkit=11.3 -y
    
    echo "Transformers yükleniyor..."
    pip install transformers==4.18.0
fi

# Çalışma dizinine git
cd backend

# LLM modelini seç
echo ""
echo "LLM Modeli Seçin:"
echo "1. facebook/bart-large-cnn (Varsayılan, İngilizce)"
echo "2. t5-small (Daha hızlı, daha az doğru)"
echo "3. google/mt5-small (Çoklu dil desteği)"
echo "4. OpenAI API (API anahtarı gerektirir)"
echo "5. Google Gemini API (API anahtarı gerektirir)"
echo ""

read -p "Seçiminiz (1-5, varsayılan: 1): " model_choice

if [ "$model_choice" = "1" ] || [ -z "$model_choice" ]; then
    export LLM_TYPE=transformers
    export LLM_MODEL=facebook/bart-large-cnn
elif [ "$model_choice" = "2" ]; then
    export LLM_TYPE=transformers
    export LLM_MODEL=t5-small
elif [ "$model_choice" = "3" ]; then
    export LLM_TYPE=transformers
    export LLM_MODEL=google/mt5-small
elif [ "$model_choice" = "4" ]; then
    export LLM_TYPE=openai
    read -p "OpenAI API Anahtarınızı girin: " OPENAI_API_KEY
    export OPENAI_API_KEY
elif [ "$model_choice" = "5" ]; then
    export LLM_TYPE=gemini
    read -p "Google Gemini API Anahtarınızı girin: " GEMINI_API_KEY
    export GEMINI_API_KEY
else
    echo "Geçersiz seçim. Varsayılan model kullanılıyor."
    export LLM_TYPE=transformers
    export LLM_MODEL=facebook/bart-large-cnn
fi

# Uygulamayı çalıştır
echo ""
echo "Uygulama başlatılıyor..."
echo "Tarayıcınızda http://localhost:5000 adresine giderek uygulamayı görüntüleyebilirsiniz."
echo "Çıkmak için Ctrl+C tuşlarına basın."
echo ""

python app_anaconda.py 