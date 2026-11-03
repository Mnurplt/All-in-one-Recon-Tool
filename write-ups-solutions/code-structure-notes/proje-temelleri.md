---
tags: [python, siber-guvenlik, recon, ders-notu, temel]
---

# 00 - Python Projesi Nasıl Çalışır? (Başlamadan Önce)

> Bu not, diğer 5 notun **ön hazırlığıdır**. Tek dosyalık script yazmak ile çok dosyalı proje yazmak arasındaki farkı anlatır.
> Sonraki notlar: [[01_config]] · [[02_logger]] · [[03_port_scanner]] · [[04_subdomain_scanner]] · [[05_recon_cli]]

---

## 1. Script mi, proje mi?

**Script:** Tek bir `.py` dosyası. `python dosya.py` ile çalışır.

**Proje:** Birden çok dosya/klasör. Her dosyanın tek bir işi vardır, dosyalar birbirini `import` eder.

Bizim araç bir projedir:

```
All-in-one-Recon/
├── recon.py              ← Programı BAŞLATAN dosya (giriş noktası)
├── core/                 ← Ortak kullanılan parçalar
│   ├── __init__.py
│   ├── config.py         ← ayarlar
│   └── logger.py         ← ekrana yazdırma
├── modules/              ← Asıl iş yapan parçalar
│   ├── __init__.py
│   ├── port_scanner.py
│   └── subdomain_scanner.py
└── wordlists/            ← kelime listeleri (.txt)
```

**Neden bölünür?** 1500 satırlık tek dosyada hata bulmak zordur. Port taramada hata varsa sadece `port_scanner.py`'a bakarsın.

---

## 2. Modül, paket, import

### Modül
Her `.py` dosyası bir **modüldür**. Modülün içindeki fonksiyon/sınıf/değişkenleri başka dosyada kullanabilirsin.

`matematik.py`:
```python
def topla(a, b):
    return a + b
```

`ana.py`:
```python
import matematik
print(matematik.topla(2, 3))      # 5
```

### `import` çeşitleri

| Yazım | Anlamı | Kullanım |
|---|---|---|
| `import asyncio` | Modülün tamamını al | `asyncio.run(...)` |
| `from pathlib import Path` | Modülden sadece bir parça al | `Path(...)` (başına modül adı yazmadan) |
| `from typing import List, Optional` | Birden çok parça al | `List[int]` |
| `import numpy as np` | Takma ad ver | `np.array(...)` |

### Paket
İçinde **`__init__.py`** dosyası bulunan klasör = **paket**. `core` ve `modules` klasörlerimiz paket.

```python
from core.config import ReconConfig
#    │    │          └─ sınıf
#    │    └─ dosya (config.py)
#    └─ klasör (paket)
```

Nokta "içindeki" demektir: `core` paketinin `config` modülünden `ReconConfig`'i getir.

### `__init__.py` ne işe yarar?
1. Klasörün "paket" olduğunu belirtir.
2. İçine şunu yazarsan kısaltma sağlar:

`core/__init__.py`:
```python
from .config import ReconConfig
from .logger import console, log_info
```
Artık dışarıdan şöyle çağrılabilir:
```python
from core import ReconConfig, console        # core.config.ReconConfig yazmaya gerek kalmaz
```
`recon.py` bunu yapıyor. (Bu `__init__.py` dosyalarını bana göndermedin, ama kod böyle çalıştığına göre içlerinde bunlar olmalı.)

---

## 3. `if __name__ == "__main__":`

Her modülün otomatik bir `__name__` değişkeni vardır:
- Dosyayı **doğrudan çalıştırırsan** → `__name__` = `"__main__"`
- Dosyayı **import edersen** → `__name__` = dosyanın adı

Deneme: `deneme.py`
```python
print("Ben:", __name__)

if __name__ == "__main__":
    print("Doğrudan çalıştırıldım")
```
- `python deneme.py` → `Ben: __main__` + `Doğrudan çalıştırıldım`
- Başka dosyada `import deneme` → sadece `Ben: deneme`

**Amaç:** `recon.py` import edilirse tarama kendiliğinden başlamasın.

---

## 4. Dışarıdan kütüphane kurmak: pip ve venv

Standart kütüphane (`asyncio`, `json`...) Python ile gelir. **Harici** kütüphane (`rich`, `aiohttp`, `dnspython`) kurulmalıdır.

```bash
pip install rich aiohttp dnspython
```
> Dikkat: **paket adı** ile **import adı** farklı olabilir. `pip install dnspython` ama kodda `import dns`.

### Sanal ortam (venv)
Her proje için ayrı kütüphane kutusu. Projeler birbirinin sürümlerini bozmaz.

```bash
python -m venv venv                # venv adlı ortamı oluştur
venv\Scripts\activate              # Windows'ta aç
source venv/bin/activate           # Linux/macOS'ta aç
pip install rich aiohttp dnspython
pip freeze > requirements.txt      # kurulu paketleri dosyaya yaz
pip install -r requirements.txt    # başkası bu dosyadan hepsini kurar
```

---

## 5. Projeyi çalıştırmak

```bash
cd All-in-one-Recon
python recon.py -t example.com -p
```
**Proje kök klasöründen çalıştırmalısın.** Çünkü `from core.config import ...` Python'a "bulunduğum klasörde `core` ara" der. Başka klasörden çalıştırırsan `ModuleNotFoundError: No module named 'core'` hatası alırsın.

---

## 6. Sık karşılaşılan Python yapıları (kısa W3Schools turu)

Aşağıdakiler 5 kodun hepsinde geçiyor. Diğer notlarda tekrar anlatılmayacak, buraya bakılacak.

### 6.1 f-string
Metnin içine değişken gömer. Başına `f` yazılır, değişken `{}` içine konur.
```python
isim = "Nur"
port = 80
print(f"Merhaba {isim}, port {port} açık")      # Merhaba Nur, port 80 açık
print(f"2 + 3 = {2 + 3}")                         # 2 + 3 = 5
print(f"{3.14159:.2f}")                           # 3.14   (2 ondalık)
print(f"{5:>3}")                                  # "  5"  (3 karakter, sağa yaslı)
```

### 6.2 `try / except / finally`
Hata çıkabilecek kodu dener; hata olursa program çökmez.
```python
try:
    sayi = int("abc")            # hata verir
except ValueError:
    print("Bu sayı değil")
finally:
    print("Ben her durumda çalışırım")
```
Çıktı: `Bu sayı değil` → `Ben her durumda çalışırım`

- `except (A, B):` → iki hata türünden biri için.
- `except Exception:` → hemen her hata için.
- `pass` → "hiçbir şey yapma".

### 6.3 `with`
Kaynağı açar, iş bitince **otomatik kapatır** (hata olsa bile).
```python
with open("notlar.txt", "r", encoding="utf-8") as f:
    icerik = f.read()
# burada dosya otomatik kapanmış olur
```
Projede: `with open(...)`, `with Progress(...)`, `async with semaphore`, `async with aiohttp.ClientSession()`.

### 6.4 Liste / küme / sözlük
```python
liste = [80, 443, 80]            # sıralı, tekrar olabilir
kume = {80, 443, 80}             # tekrarsız → {80, 443}
sozluk = {80: "HTTP", 22: "SSH"} # anahtar: değer

liste.append(21)                 # sona ekle
kume.add(25)                     # ekle
sozluk.get(80, "Bilinmiyor")     # "HTTP"
sozluk.get(9999, "Bilinmiyor")   # "Bilinmiyor"  (anahtar yoksa varsayılan; hata VERMEZ)
sozluk[9999]                     # KeyError! (.get kullanmanın sebebi)
```

### 6.5 Comprehension (tek satırda liste/küme üretme)
```python
kelimeler = ["www", "mail", "api"]
adaylar = [f"{k}.example.com" for k in kelimeler]
# ['www.example.com', 'mail.example.com', 'api.example.com']

kume = {k.upper() for k in kelimeler}   # süslü parantez = küme
```
Koşul ekleme:
```python
temiz = [s.strip() for s in ["a ", "", "b"] if s.strip()]    # ['a', 'b']
```

### 6.6 `lambda`
İsimsiz tek satırlık fonksiyon.
```python
kare = lambda x: x * x
print(kare(4))                                   # 16

sonuclar = [(443, "HTTPS"), (22, "SSH"), (80, "HTTP")]
sonuclar.sort(key=lambda r: r[0])                # ilk elemana göre sırala
# [(22, 'SSH'), (80, 'HTTP'), (443, 'HTTPS')]
```

### 6.7 Dilimleme (slicing)
```python
s = "Merhaba"
s[0]      # 'M'
s[:3]     # 'Mer'     (baştan 3 karakter)
s[2:]     # 'rhaba'   (2. karakterden sona)
s[-1]     # 'a'       (sondan ilk)
```

### 6.8 Tip ipuçları (type hints)
Programın çalışmasını **etkilemez**, sadece okuyana ve editöre ipucu verir.
```python
def topla(a: int, b: int) -> int:     # iki int alır, int döndürür
    return a + b

from typing import List, Optional
def ilk_port(portlar: List[int]) -> Optional[int]:   # int veya None döndürür
    return portlar[0] if portlar else None
```

### 6.9 Docstring
Fonksiyonun hemen altına yazılan `"""..."""` açıklama. `help(fonksiyon)` ile görünür.

### 6.10 Dataclass
Sadece veri tutan sınıf yazmanın kısa yolu.
```python
from dataclasses import dataclass

@dataclass
class Port:
    numara: int
    durum: str

p = Port(80, "open")
print(p)             # Port(numara=80, durum='open')
print(p.numara)      # 80
```
`@dataclass` olmadan `__init__` metodunu elle yazmak gerekirdi. Detay: [[01_config]].

### 6.11 Bytes ve string farkı
Ağdan gelen veri **bytes**'tır (`b"..."`). Okunur metne çevirmek için `.decode()`, göndermek için `.encode()`.
```python
b"HTTP/1.1 200 OK".decode()      # 'HTTP/1.1 200 OK'
"GET /".encode()                 # b'GET /'
```
`\r\n` = HTTP/TCP satır sonu (CRLF).

---

## 7. Asenkron (async) programlamanın sıfırdan mantığı

### Sorun
Bir port taramada çoğu zaman **beklersin**: paket gider, cevap gelmesini beklersin. 1000 portu sırayla taramak:
`1000 × 1 sn = 1000 sn` (16 dakika).

### Çözüm
Beklerken **başka işe geç**. Bu "asenkron" programlamadır. Garson örneği: Tek garson, bir masanın siparişini alıp mutfağa verir, yemek pişerken diğer masalara gider. 100 masa için 100 garson gerekmez.

### Üç anahtar kelime
| Kelime | Anlamı |
|---|---|
| `async def` | Bu fonksiyon "duraklatılabilir" (**coroutine**) |
| `await` | "Bunu bekle, beklerken başka işlere geç" |
| `asyncio.run(...)` | Programı başlatır (**event loop**'u kurar) |

### Deney
```python
import asyncio
import time

async def bekle(ad, sn):
    print(f"{ad} başladı")
    await asyncio.sleep(sn)        # 'time.sleep' DEĞİL; beklerken başkasına geçilir
    print(f"{ad} bitti")

async def main():
    t = time.perf_counter()
    await asyncio.gather(bekle("A", 2), bekle("B", 2), bekle("C", 2))
    print(f"Toplam: {time.perf_counter() - t:.1f} sn")

asyncio.run(main())
```
Çıktı:
```
A başladı
B başladı
C başladı
A bitti
B bitti
C bitti
Toplam: 2.0 sn
```
Sırayla çalışsaydı 6 sn sürerdi. `gather` hepsini aynı anda başlattığı için **2 sn**.

### Kurallar
1. `await` sadece `async def` içinde yazılabilir.
2. `async def` fonksiyonu çağırmak onu çalıştırmaz, coroutine nesnesi üretir. Çalıştırmak için `await` veya `asyncio.run` / `gather` gerekir.
3. Event loop **tek thread**'dir. Bir `await` noktasında kontrol başka göreve geçer. Bu yüzden uzun süren, bloklayan normal kod (`time.sleep`, bloklayan `socket.getaddrinfo`) event loop'u dondurur.

---

## 8. Mini sözlük

| Terim | Anlamı |
|---|---|
| **Fonksiyon** | `def` ile yazılan, çağrılınca çalışan kod bloğu |
| **Sınıf (class)** | Veri + davranış şablonu |
| **Nesne / örnek** | Sınıftan üretilen somut parça (`ReconConfig()`) |
| **Parametre / argüman** | Fonksiyonun aldığı değer |
| **Dekoratör** | `@` ile fonksiyon/sınıfa özellik ekleyen yapı (`@dataclass`) |
| **Coroutine** | `async def` ile yazılmış fonksiyon |
| **Event loop** | Coroutine'leri sırayla yöneten döngü |
| **Orkestratör** | İşi kendisi yapmayıp diğer parçaları sırayla çağıran fonksiyon |
| **Giriş noktası** | Programın başladığı dosya/fonksiyon (`recon.py` → `main()`) |
