# Haber Özetleme için LLM Modelleri

Haber özetleme platformunda kullanılan ve desteklenen LLM (Large Language Model) seçenekleri aşağıda açıklanmıştır.

## 1. Varsayılan Model

### BERT2BERT (Türkçe)
Projede varsayılan olarak kullanılan model, Türkçe haber özetleme için özel olarak eğitilmiş `mlsum/bert2bert` modelidir.

```python
from transformers import pipeline
summarizer = pipeline("summarization", model="mlsum/bert2bert")
```

## 2. Desteklenen Diğer Modeller

### MT5 (Çoklu Dil)
Hafif ve hızlı çoklu dil desteği sunan model.

```python
from transformers import pipeline
summarizer = pipeline("summarization", model="google/mt5-small")
```

### mBART (Çoklu Dil)
Daha güçlü çoklu dil desteği sunan model.

```python
from transformers import pipeline
summarizer = pipeline("summarization", model="facebook/mbart-large-cc25")
```

### Falcon-7B (Güçlü Dil Modeli)
Türkçe desteği olan güçlü bir dil modeli.

```python
from transformers import pipeline
summarizer = pipeline("summarization", model="tiiuae/falcon-7b-instruct")
```

## 3. Yedek Özetleme Sistemi

Model yüklenemediğinde veya hata durumunda otomatik olarak basit özetleme sistemine geçiş yapılır:

```python
def basit_ozet(metin):
    """Basit özetleme fonksiyonu"""
    cumleler = metin.split('.')
    return '. '.join(cumleler[:3]) + '.'
```

## 4. Özet Modları

Sistem iki farklı özet modu sunar:

1. **Normal Özet**: 3-4 cümlelik detaylı özet (max_length=150)
2. **Süper Özet**: En fazla 2 cümlelik kısa özet (max_length=75)

## 5. API Kullanımı

### Özet Oluşturma
```bash
POST /api/ozet
Content-Type: application/json

{
    "metin": "Özetlenecek metin",
    "ozet_modu": "normal"  # veya "super"
}
```

### Haberleri Getirme
```bash
GET /api/haberler?ozet_modu=normal
GET /api/haberler/kategori?ozet_modu=super
``` 