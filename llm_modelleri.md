# Haber Özetleme için LLM Modelleri

Haber özetleme platformunda kullanabileceğiniz çeşitli LLM (Large Language Model) seçenekleri ve bunların Anaconda ortamında nasıl kullanılacağı aşağıda açıklanmıştır.

## 1. Hugging Face Transformers Modelleri

### Facebook BART (Varsayılan)
Projede varsayılan olarak kullanılan model, haber özetleme için özel olarak eğitilmiş `facebook/bart-large-cnn` modelidir.

```python
from transformers import pipeline
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
```

### Alternatif Modeller

#### T5 (Daha Hızlı)
```python
from transformers import pipeline
summarizer = pipeline("summarization", model="t5-small")
```

#### PEGASUS (Daha Doğru)
```python
from transformers import pipeline
summarizer = pipeline("summarization", model="google/pegasus-xsum")
```

#### mT5 (Çoklu Dil Desteği)
```python
from transformers import pipeline
summarizer = pipeline("summarization", model="google/mt5-small")
```

## 2. Türkçe Dil Desteği İçin Öneriler

Türkçe haber özetleme için şu modelleri deneyebilirsiniz:

### BERTurk
```python
# Önce modeli yükleyin
conda install -c conda-forge transformers
pip install sentencepiece

# Kodu değiştirin
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

tokenizer = AutoTokenizer.from_pretrained("dbmdz/bert-base-turkish-cased")
model = AutoModelForSeq2SeqLM.from_pretrained("dbmdz/bert-base-turkish-cased")
```

### mBART (Çoklu Dil)
```python
from transformers import MBartForConditionalGeneration, MBartTokenizer

model = MBartForConditionalGeneration.from_pretrained("facebook/mbart-large-50")
tokenizer = MBartTokenizer.from_pretrained("facebook/mbart-large-50", src_lang="tr_TR")
```

## 3. API Tabanlı Modeller

### OpenAI GPT
```python
# Kurulum
pip install openai

# Kullanım
import openai
openai.api_key = "API_ANAHTARINIZ"

def ozet_olustur(metin, max_length=150):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Aşağıdaki haberi özetle:\n\n{metin}",
        max_tokens=max_length,
        temperature=0.3
    )
    return response.choices[0].text.strip()
```

### Google Gemini
```python
# Kurulum
pip install google-generativeai

# Kullanım
import google.generativeai as genai

genai.configure(api_key="API_ANAHTARINIZ")

def ozet_olustur(metin, max_length=150):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(f"Aşağıdaki haberi özetle:\n\n{metin}")
    return response.text
```

## 4. Yerel Çalıştırılabilir Küçük Modeller

Daha az kaynak gerektiren ve yerel olarak çalıştırılabilir modeller:

### ONNX Runtime ile Optimize Edilmiş Modeller
```bash
# Kurulum
conda install -c conda-forge onnxruntime
pip install optimum[onnxruntime]

# Kullanım
from optimum.onnxruntime import ORTModelForSeq2SeqLM
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")
model = ORTModelForSeq2SeqLM.from_pretrained("facebook/bart-large-cnn", export=True)
```

### LLaMA veya Mistral
Bu modeller daha fazla bellek gerektirir ancak API'ye bağımlı değildir:

```bash
# Kurulum
pip install llama-cpp-python

# Kullanım için model dosyasını indirmeniz gerekir
```

## Anaconda Ortamında Model Değişikliği

Modeli değiştirmek için `app.py` dosyasındaki ilgili satırı düzenleyin:

```python
# Transformers modelini yükle
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
```

Örneğin, T5 modeline geçmek için:

```python
# Transformers modelini yükle
summarizer = pipeline("summarization", model="t5-small")
``` 