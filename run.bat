@echo off
chcp 65001 > nul

echo PRECURSOR - Haber Ozet Platformu
echo ================================================
echo.

cd %~dp0
echo Calisma dizini: %CD%

REM Python kontrolü
python --version >nul 2>&1
if errorlevel 1 (
    echo HATA: Python bulunamadi!
    echo Lutfen Python 3.8 veya daha yeni bir surum yukleyin.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Sanal ortam kontrolü
if not exist "venv" (
    echo Sanal ortam olusturuluyor...
    python -m venv venv
    if errorlevel 1 (
        echo HATA: Sanal ortam olusturulamadi!
        pause
        exit /b 1
    )
) else (
    echo Sanal ortam zaten mevcut.
)

REM GPU kontrolü
set "GPU_AVAILABLE=0"
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo NVIDIA GPU bulundu!
    set /p GPU_CHOICE="GPU destegi kullanilsin mi? (E/H): "
    if /i "%GPU_CHOICE%"=="E" (
        echo GPU destegi aktif edilecek...
        set "GPU_AVAILABLE=1"
    ) else (
        echo CPU modu kullanilacak...
    )
) else (
    echo GPU bulunamadi veya NVIDIA suruculeri yuklu degil. CPU modu kullanilacak...
)

REM Sanal ortamı aktifleştir
echo Sanal ortam aktif ediliyor...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo HATA: Sanal ortam aktif edilemedi!
    pause
    exit /b 1
)

REM Paket kontrolü ve yükleme
python -m pip install --upgrade pip

REM requirements.txt kontrolü
if not exist "backend\requirements.txt" (
    echo requirements.txt olusturuluyor...
    echo flask==2.0.1 > backend\requirements.txt
    echo werkzeug==2.0.1 >> backend\requirements.txt
    echo transformers==4.18.0 >> backend\requirements.txt
    echo python-dotenv==0.19.2 >> backend\requirements.txt
    echo feedparser==6.0.8 >> backend\requirements.txt
)

echo Gerekli paketler yukleniyor...
pip install -r backend\requirements.txt

REM PyTorch kurulumu
python -c "import torch" 2>nul
if errorlevel 1 (
    echo PyTorch yukleniyor...
    if "%GPU_AVAILABLE%"=="1" (
        echo GPU destekli PyTorch yukleniyor...
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    ) else (
        echo CPU versiyonu PyTorch yukleniyor...
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    )
)

if not exist "backend" mkdir backend
cd backend

echo # LLM model ayarlari > .env
echo LLM_TYPE=transformers >> .env
echo LLM_MODEL=mlsum/bert2bert >> .env
echo OZET_MODU=normal >> .env
echo GPU_AVAILABLE=%GPU_AVAILABLE% >> .env

echo.
echo Kurulum tamamlandi. Uygulama baslatiliyor...
python app_anaconda.py

pause 