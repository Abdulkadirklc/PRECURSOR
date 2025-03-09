@echo off
chcp 65001 > nul

echo PRECURSOR - Haber Ozet Platformu
echo ================================================
echo.

cd %~dp0
echo Calisma dizini: %CD%

REM Conda yolu kontrolü
set "CONDA_PATH=%USERPROFILE%\miniconda3"
if exist "%USERPROFILE%\Anaconda3" (
    set "CONDA_PATH=%USERPROFILE%\Anaconda3"
)

set "CONDA_EXE=%CONDA_PATH%\Scripts\conda.exe"
set "CONDA_ACTIVATE=%CONDA_PATH%\Scripts\activate.bat"

if not exist "%CONDA_EXE%" (
    echo HATA: Conda bulunamadi!
    echo Lutfen Anaconda veya Miniconda'yi yukleyin.
    echo Beklenen yollar:
    echo - %USERPROFILE%\miniconda3\Scripts\conda.exe
    echo - %USERPROFILE%\Anaconda3\Scripts\conda.exe
    pause
    exit /b 1
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

REM Conda aktivasyonu
echo Conda ortami aktif ediliyor...
if not exist "%CONDA_ACTIVATE%" (
    echo HATA: Conda aktivasyon scripti bulunamadi!
    echo Aranan dosya: %CONDA_ACTIVATE%
    pause
    exit /b 1
)

call "%CONDA_ACTIVATE%"
if errorlevel 1 (
    echo HATA: Conda ortami aktif edilemedi!
    echo Lutfen Anaconda/Miniconda kurulumunuzu kontrol edin.
    pause
    exit /b 1
)

REM Conda'yı hızlandır
call conda config --set channel_priority flexible
if errorlevel 1 (
    echo UYARI: Conda yapilandirmasi ayarlanamadi, devam ediliyor...
)

call conda config --set solver libmamba
if errorlevel 1 (
    echo UYARI: Conda solver ayarlanamadi, devam ediliyor...
)

REM Ortam kontrolü
call conda env list | findstr "precursor" > nul
if errorlevel 1 (
    echo Precursor ortami olusturuluyor...
    call conda create -n precursor python=3.8 --yes
    if errorlevel 1 (
        echo HATA: Precursor ortami olusturulamadi!
        pause
        exit /b 1
    )
) else (
    echo Precursor ortami zaten mevcut, aktif ediliyor...
)

echo Precursor ortami aktif ediliyor...
call conda activate precursor
if errorlevel 1 (
    echo HATA: Precursor ortami aktif edilemedi!
    pause
    exit /b 1
)

REM Paket kontrolü
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Flask ve gerekli paketler yukleniyor...
    call pip install flask==2.0.1 werkzeug==2.0.1
)

python -c "import transformers" 2>nul
if errorlevel 1 (
    echo Transformers yukleniyor...
    pip install transformers==4.18.0
)

python -c "import dotenv" 2>nul
if errorlevel 1 (
    echo Python-dotenv yukleniyor...
    pip install python-dotenv==0.19.2
)

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

python -c "import feedparser" 2>nul
if errorlevel 1 (
    echo Feedparser yukleniyor...
    pip install feedparser==6.0.8
)

if not exist "backend" mkdir backend
cd backend

echo # LLM model ayarlari > .env
echo LLM_TYPE=transformers >> .env
echo LLM_MODEL=mrm8488/bert2bert_shared-turkish-summarization >> .env
echo GPU_AVAILABLE=%GPU_AVAILABLE% >> .env

echo.
echo Kurulum tamamlandi. Uygulama baslatiliyor...
python app_anaconda.py
echo ==================================================
echo Web arayuzune erisim: http://localhost:5000
echo ==================================================
pause 