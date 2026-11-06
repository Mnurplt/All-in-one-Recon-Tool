---
tags: [python, siber-guvenlik, recon, ders-notu, dataclass, pathlib]
kaynak: config.py
---

# 01 - config.py (Merkezi Ayarlar)

> **Bu dosya ne yapar?** Aracın tüm ayarlarını (hedef, timeout, port listesi, wordlist yolları...) **tek bir nesnede** toplar.
> Ön bilgi: [[00_proje_temelleri]] (f-string, liste, lambda, dataclass'a kısa giriş)
> Diğer notlar: [[02_logger]] · [[03_port_scanner]] · [[04_subdomain_scanner]] · [[05_recon_cli]]

---

## 1. Dosyanın tamamı tek bakışta

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
WORDLISTS_DIR = BASE_DIR / "wordlists"

@dataclass
class ReconConfig:
    target: str = ""
    concurrency_limit: int = 100
    timeout: float = 3.0
    ports: List[int] = field(default_factory=lambda: [21, 22, 80, ...])
    ...
```

Üç bölüm var: **(1)** import'lar, **(2)** klasör yolları, **(3)** ayar sınıfı.

---

## 2. Kütüphaneler

| Kütüphane | Standart mı? | Ne için |
|---|---|---|
| `dataclasses` | Evet | Ayar sınıfını az kodla yazmak |
| `pathlib` | Evet | Dosya/klasör yollarını kolay yönetmek |
| `typing` | Evet | Tip ipuçları (`List[int]`) |

Hiçbirini `pip install` ile kurmak gerekmez.

---

## 3. `dataclasses` modülü

### 3.1 Önce sorun: dataclass olmasaydı

Ayarları tutan bir sınıfı elle yazalım:

```python
class Ayar:
    def __init__(self, target="", timeout=3.0, concurrency_limit=100):
        self.target = target
        self.timeout = timeout
        self.concurrency_limit = concurrency_limit

a = Ayar(target="example.com")
print(a)        # <__main__.Ayar object at 0x000001...>   ← okunmuyor
```
Hem uzun hem `print` çıktısı anlamsız.

### 3.2 `@dataclass` ile

```python
from dataclasses import dataclass

@dataclass
class Ayar:
    target: str = ""
    timeout: float = 3.0
    concurrency_limit: int = 100

a = Ayar(target="example.com")
print(a)
# Ayar(target='example.com', timeout=3.0, concurrency_limit=100)

a.timeout = 5.0              # değer değiştirme
print(a.timeout)             # 5.0
```
`@dataclass` (dekoratör) sınıfın üstüne yazılır ve şunları **otomatik üretir**:
- `__init__` (yapıcı), `__repr__` (güzel print), `__eq__` (karşılaştırma).

**Kural:** Alan şöyle yazılır: `isim: tip = varsayılan_değer`.

**Kodumuzda:** `ReconConfig`, ayrıca `PortScanResult` ([[03_port_scanner]]) ve `SubdomainResult` ([[04_subdomain_scanner]]).

### 3.3 `field(default_factory=...)`: liste neden özel yazılıyor?

Şunu yazmayı dene:

```python
@dataclass
class Ayar:
    ports: list = [80, 443]       # ❌
```
Hata: `ValueError: mutable default <class 'list'> for field ports is not allowed: use default_factory`

**Neden yasak?** Liste "değiştirilebilir" (mutable) bir nesnedir. Aynı liste tüm nesneler arasında **paylaşılırdı**. Düz Python'da bu hatayı simüle edelim:

```python
class Kotu:
    def __init__(self, liste=[]):      # liste fonksiyon tanımlanırken BİR KERE oluşur
        self.liste = liste

a = Kotu()
b = Kotu()
a.liste.append(80)
print(b.liste)       # [80]   ← b'ye hiç dokunmadık ama değişti!
```

**Çözüm:** `default_factory` = "varsayılanı **her nesne için yeniden üret**":

```python
from dataclasses import dataclass, field

@dataclass
class Ayar:
    ports: list = field(default_factory=lambda: [80, 443])

a = Ayar()
b = Ayar()
a.ports.append(22)
print(a.ports)    # [80, 443, 22]
print(b.ports)    # [80, 443]        ← b bağımsız
```

- `field(...)` → alan hakkında özel ayar verir.
- `default_factory=` → değeri üretecek **fonksiyon** (burada `lambda`).
- `lambda: [80, 443]` → çağrıldığında yeni liste döndüren isimsiz fonksiyon. ([[00_proje_temelleri#6.6 lambda]])
- `default_factory=list` → boş liste üretir (`subdomain_scanner.py` içinde `ips: List[str] = field(default_factory=list)` böyle).

**Pratik kural:**
| Değer tipi | Nasıl yazılır |
|---|---|
| `int`, `float`, `str`, `bool`, `Path` | `timeout: float = 3.0` |
| `list`, `dict`, `set` | `ports: List[int] = field(default_factory=...)` |

---

## 4. `pathlib` modülü

### 4.1 Neden var?
Eski yöntemle yol string'dir ve işletim sistemine göre bozulur:
```python
"wordlists" + "\\" + "dosya.txt"      # sadece Windows'ta çalışır
```
`pathlib` ile yol **nesnedir** ve Windows/Linux/macOS'ta doğru ayraç kullanılır.

### 4.2 `Path(...)`: yol nesnesi oluşturma
```python
from pathlib import Path

p = Path("C:/proje/core/config.py")
print(p.name)       # config.py          (dosya adı)
print(p.suffix)     # .py                (uzantı)
print(p.stem)       # config             (uzantısız ad)
print(p.parent)     # C:\proje\core      (bir üst klasör)
```

### 4.3 `__file__`
Python'un her modülde hazır verdiği değişken: **o anki dosyanın yolu**.
```python
print(__file__)     # C:\proje\core\config.py
```

### 4.4 `.resolve()`
Yolu **mutlak** (tam) yola çevirir. `..` ve `.` gibi kısaltmaları açar.
```python
Path("../core/config.py").resolve()     # C:\proje\core\config.py
```
Neden? `python recon.py` çalıştırılan klasöre göre `__file__` bazen göreli (relative) yol verebilir. `.resolve()` ile her zaman tam yol elde edilir.

### 4.5 `.parent`
Bir üst klasör. Zincirleme kullanılabilir:
```python
p = Path("C:/proje/core/config.py")
p.parent              # C:\proje\core
p.parent.parent       # C:\proje        ← proje kökü
```

### 4.6 `/` operatörü (yol birleştirme)
```python
kok = Path("C:/proje")
print(kok / "wordlists")                          # C:\proje\wordlists
print(kok / "wordlists" / "common_dirs.txt")      # C:\proje\wordlists\common_dirs.txt
```
`/` burada bölme değil, **yol birleştirme**. Python `Path` sınıfında bu operatörü özel olarak tanımlamış.

### 4.7 Kodda adım adım
```python
BASE_DIR = Path(__file__).resolve().parent.parent
```
| Adım | Sonuç |
|---|---|
| `__file__` | `C:\proje\core\config.py` |
| `Path(...)` | Yol nesnesi |
| `.resolve()` | Tam yol |
| `.parent` | `C:\proje\core` |
| `.parent` (2.) | `C:\proje` ← **proje kökü** |

```python
WORDLISTS_DIR = BASE_DIR / "wordlists"      # C:\proje\wordlists
```
**Sonuç:** Aracı hangi klasörden çalıştırırsan çalıştır, wordlist yolu hep doğru bulunur.

Ek `pathlib` metotları (diğer dosyalarda kullanılıyor):
```python
Path("x.txt").exists()                       # dosya var mı → True/False
Path("rapor.json").write_text("{}", encoding="utf-8")   # dosyaya yaz
```

---

## 5. `typing` modülü

```python
from typing import List

ports: List[int]          # "int'lerden oluşan liste"
dns_servers: List[str]    # "string'lerden oluşan liste"
```
- Sadece **ipucu**'dur; yanlış tipte değer verirsen Python hata vermez.
- Python 3.9+ ta `list[int]` yazılabilir (`logger.py` böyle yazıyor). `typing.List` eski yazımdır, ikisi aynı işi görür.

---

## 6. `ReconConfig` alanları ve anlamı

### Hedef
| Alan | Varsayılan | Anlamı |
|---|---|---|
| `target` | `""` | Taranan domain veya IP (örn `example.com`) |
| `target_ip` | `""` | Port taramada domain IP'ye çevrilince buraya yazılır |

### Performans
| Alan | Varsayılan | Anlamı |
|---|---|---|
| `concurrency_limit` | `100` | Aynı anda en fazla kaç bağlantı. [[03_port_scanner#Semaphore]] |
| `timeout` | `3.0` | Bir işlem için bekleme süresi (saniye) |

### Port tarama
| Alan | Varsayılan | Anlamı |
|---|---|---|
| `ports` | 24 yaygın port | Taranacak portlar |
| `banner_timeout` | `2.0` | Banner için bekleme süresi |

### Subdomain tarama
| Alan | Varsayılan | Anlamı |
|---|---|---|
| `dns_servers` | `1.1.1.1`, `8.8.8.8`, `9.9.9.9` | Sorgulanacak DNS sunucuları (Cloudflare, Google, Quad9) |
| `subdomain_wordlist` | `wordlists/common_subdomains.txt` | Kelime listesi yolu |
| `enable_crtsh` | `True` | crt.sh pasif taraması açık mı |

### Gelecek modüller (henüz kullanılmıyor)
`dir_wordlist`, `extensions`, `user_agent`, `status_codes_to_show`, `vhost_wordlist`, `vhost_similarity_threshold`

---

## 7. Config nesnesi nasıl kullanılıyor?

```python
from core.config import ReconConfig

config = ReconConfig(target="example.com", timeout=5.0)   # sadece istenenleri ver
print(config.concurrency_limit)      # 100  (varsayılan)
print(config.timeout)                # 5.0  (bizim verdiğimiz)

config.target_ip = "93.184.216.34"   # sonradan değiştirme
```

`recon.py`, komut satırından gelen değerleri bu nesneye yazar. Tarama modülleri `run_port_scan(config)` gibi **sadece config nesnesini** alır.

### Neden tek nesne? (Configuration Object deseni)
Alternatif: fonksiyona her ayarı tek tek geçmek:
```python
run_port_scan(target, ports, timeout, banner_timeout, concurrency, dns_servers, ...)   # ❌ uzun
```
Config nesnesiyle:
```python
run_port_scan(config)                                                                  # ✅
```
Yeni ayar eklediğinde fonksiyon imzalarını değiştirmen gerekmez.

---

## 8. Dikkat edilecek noktalar
- `config.py` içindeki `ports` ile `recon.py` içindeki `top20` listesi **aynı değil**. Tek yerde tutmak daha temiz.
- `dir_*`, `extensions`, `vhost_*` alanları henüz hiçbir kod tarafından okunmuyor.
- `user_agent` alanı var ama `subdomain_scanner.py` içinde crt.sh isteği kendi User-Agent'ını yazıyor.

## 9. Tekrar soruları
1. `ports: List[int] = [21, 22]` yazınca neden hata alırız? `default_factory` bunu nasıl çözer?
2. `Path(__file__).resolve().parent.parent` adım adım ne verir?
3. `BASE_DIR / "wordlists"` içindeki `/` ne yapar?
4. `@dataclass` olmasaydı hangi metodu elle yazmamız gerekirdi?
5. Configuration Object deseninin faydası nedir?
