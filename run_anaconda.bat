@echo off
chcp 65001 > nul

echo PRECURSOR - Haber Ozet Platformu
echo ================================================
echo.

REM Çalışma dizinini kontrol et
cd %~dp0
echo Calisma dizini: %CD%

REM Backend dizinini kontrol et
echo Backend dizini kontrol ediliyor...
if not exist "backend" (
    echo HATA: Backend dizini bulunamadi!
    pause
    exit /b 1
)
echo Backend dizini bulundu.

REM app_anaconda.py dosyasını kontrol et
echo app_anaconda.py dosyasi kontrol ediliyor...
if not exist "backend\app_anaconda.py" (
    echo HATA: backend\app_anaconda.py dosyasi bulunamadi!
    pause
    exit /b 1
)
echo app_anaconda.py dosyasi bulundu.

REM Conda yolunu belirle
set CONDA_PATH=C:\Users\Abdulkadir\miniconda3
set CONDA_EXE=%CONDA_PATH%\Scripts\conda.exe
echo Conda yolu: %CONDA_EXE%

REM Conda'nın varlığını kontrol et
echo Conda yolu kontrol ediliyor: %CONDA_EXE%
if not exist "%CONDA_EXE%" (
    echo HATA: Conda bulunamadi! Yol: %CONDA_EXE%
    pause
    exit /b 1
)
echo Conda bulundu.

REM LLM modelini seç
echo.
echo LLM Modeli Secin:
echo 1. facebook/bart-large-cnn (Varsayilan, Ingilizce)
echo 2. t5-small (Daha hizli, daha az dogru)
echo 3. google/mt5-small (Coklu dil destegi)
echo 4. OpenAI API (API anahtari gerektirir)
echo 5. Google Gemini API (API anahtari gerektirir)
echo.
set /p model_secim="Seciminiz (1-5, varsayilan: 1): "

if "%model_secim%"=="2" (
    set "LLM_MODEL=t5-small"
    set "LLM_TYPE=transformers"
    echo t5-small modeli secildi.
) else if "%model_secim%"=="3" (
    set "LLM_MODEL=google/mt5-small"
    set "LLM_TYPE=transformers"
    echo google/mt5-small modeli secildi.
) else if "%model_secim%"=="4" (
    set "LLM_TYPE=openai"
    set "LLM_MODEL=text-davinci-003"
    set /p OPENAI_API_KEY="OpenAI API anahtarinizi girin: "
    echo OpenAI API modeli secildi.
) else if "%model_secim%"=="5" (
    set "LLM_TYPE=gemini"
    set "LLM_MODEL=gemini-pro"
    set /p GEMINI_API_KEY="Gemini API anahtarinizi girin: "
    echo Gemini API modeli secildi.
) else (
    set "LLM_MODEL=facebook/bart-large-cnn"
    set "LLM_TYPE=transformers"
    echo facebook/bart-large-cnn modeli secildi.
)

REM .env dosyasını oluştur
echo # LLM model ayarlari > backend\.env
echo LLM_TYPE=%LLM_TYPE% >> backend\.env
echo LLM_MODEL=%LLM_MODEL% >> backend\.env

REM API anahtarlarını ekle
if "%LLM_TYPE%"=="openai" (
    echo OPENAI_API_KEY=%OPENAI_API_KEY% >> backend\.env
)
if "%LLM_TYPE%"=="gemini" (
    echo GEMINI_API_KEY=%GEMINI_API_KEY% >> backend\.env
)

REM Uygulamayı başlat
echo.
echo Uygulama baslatiliyor...
echo Tarayicinizda http://localhost:5000 adresine giderek uygulamayi goruntuleyebilirsiniz.
echo Cikmak icin Ctrl+C tuslarina basin.
echo.

cd backend
echo Uygulama calistiriliyor...
"%CONDA_EXE%" run -n haber-ozet python app_anaconda.py

echo Uygulama sonlandi.
cd ..
pause 