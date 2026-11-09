---
tags: [python, siber-guvenlik, recon, ders-notu, asyncio, tcp]
kaynak: port_scanner.py
---

# 03 - port_scanner.py (Asenkron TCP Port Tarayıcı + Banner Grabbing)

> **Bu dosya ne yapar?** Hedefin hangi TCP portlarının **açık** olduğunu bulur, açık portlardan "bu hangi servis?" bilgisini (banner) okur.
> Ön bilgi: [[00_proje_temelleri]] (özellikle §7 async mantığı)
> Diğer notlar: [[01_config]] · [[02_logger]] · [[04_subdomain_scanner]] · [[05_recon_cli]]

---

## 1. Önce temel kavramlar

### 1.1 Port nedir?
IP adresi bir **binadır**, port **daire numarasıdır**. Bir sunucuda aynı anda web (80), SSH (22), veritabanı (3306) çalışır; hangi servise gideceğini port belirler.
Portlar 0–65535 arası sayıdır.

### 1.2 Açık / kapalı / filtreli
| Durum | Ne olur | Python'da görünen |
|---|---|---|
| **Açık** | Servis dinliyor, bağlantı kurulur | Bağlantı başarılı |
| **Kapalı** | Dinleyen yok, sunucu "hayır" (RST) der | Hemen `ConnectionRefusedError` |
| **Filtreli** | Firewall paketi sessizce düşürür | Cevap gelmez → `TimeoutError` |

### 1.3 TCP Connect Scan
TCP bağlantısı 3 adımda kurulur (**3'lü el sıkışma**):
```
İstemci ──SYN──────►  Sunucu    "Bağlanmak istiyorum"
İstemci ◄──SYN/ACK──  Sunucu    "Tamam, ben hazırım"   ← port AÇIK
İstemci ──ACK──────►  Sunucu    "Anlaştık"
```
**Connect Scan** = bu bağlantıyı gerçekten kurmayı denemek. Bağlandıysa port açık.
- **+** Özel yetki (root) gerekmez, Python'la kolay yazılır.
- **−** Hedef sistem logunda bağlantı izi kalır (gürültülü).

### 1.4 Banner nedir?
Bazı servisler bağlanır bağlanmaz kendini tanıtır:
```
SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.1
220 (vsFTPd 3.0.3)
```
Bu metne **banner** denir. Sürüm bilgisi, bilinen zafiyetlerle (CVE) eşleştirmede işe yarar.
- **Önce sunucu konuşur:** SSH, FTP, SMTP, MySQL → bağlanınca banner'ı kendisi yollar (**pasif dinleme** yeter).
- **Önce istemci konuşur:** HTTP → sen bir istek göndermeden cevap vermez (**aktif prob** gerekir).

> **Kendi bilgisayarında güvenle dene:** Terminalde `python -m http.server 8000` çalıştırıp aracı `-t 127.0.0.1 -p 8000` ile kendine karşı çalıştırabilirsin. Başka sistemleri **izinsiz tarama**. `scanme.nmap.org` Nmap projesinin test için izin verdiği hedeftir.

---

## 2. Kütüphaneler

| Kütüphane | Standart mı? | Rolü |
|---|---|---|
| `asyncio` | Evet | Bağlantı, zaman aşımı, eşzamanlılık |
| `socket` | Evet | Sadece `AF_INET` sabiti için |
| `time` | Evet | Gecikme ölçümü |
| `dataclasses` | Evet | Sonuç sınıfı ([[01_config#3. dataclasses modülü]]) |
| `typing` | Evet | `List`, `Optional` |
| `rich.progress` | **Hayır** (`pip install rich`) | İlerleme çubuğu |
| `core.config`, `core.logger` | Proje içi | [[01_config]], [[02_logger]] |

---

## 3. `asyncio` fonksiyonları (tek tek)

### 3.1 `asyncio.open_connection(host, port)`
TCP bağlantısı açar. Bağlantı kurulunca **iki nesne** döner:
```python
reader, writer = await asyncio.open_connection("example.com", 80)
```
- `reader` (`StreamReader`) → karşıdan veri **okumak** için.
- `writer` (`StreamWriter`) → karşıya veri **göndermek** için.
Bağlanılamazsa hata fırlatır: port kapalıysa `ConnectionRefusedError`, ağ hatasında diğer `OSError` türleri.

Kodda: bağlantı **başarılı** olursa port açıktır.

### 3.2 `asyncio.wait_for(coroutine, timeout=süre)`
Bir işleme **süre sınırı** koyar. Süre dolarsa `asyncio.TimeoutError` fırlatır.
```python
import asyncio

async def yavas():
    await asyncio.sleep(10)

async def main():
    try:
        await asyncio.wait_for(yavas(), timeout=2)
    except asyncio.TimeoutError:
        print("2 saniyede bitmedi, vazgeçtim")

asyncio.run(main())
```
Kodda 3 yerde:
```python
await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=timeout)  # bağlantı
await asyncio.wait_for(reader.read(512), timeout=timeout)                   # banner okuma
await asyncio.wait_for(writer.drain(), timeout=1.0)                         # gönderme
```
Bu olmasa filtreli (cevap vermeyen) bir portta program **sonsuza kadar** beklerdi.

> Python 3.11+ ta `asyncio.TimeoutError`, yerleşik `TimeoutError` ile aynıdır ve o da `OSError`'ın alt türüdür. Kodda `except (asyncio.TimeoutError, OSError)` bu yüzden sorunsuz.

### 3.3 `reader.read(n)`
Karşıdan **en fazla `n` bayt** okur. Veri gelene kadar bekler.
```python
data = await reader.read(512)      # en fazla 512 bayt
```
Dönen değer `bytes`'tır (`b"SSH-2.0-..."`). Metne çevirmek için `.decode()`.

### 3.4 `writer.write(veri)` ve `await writer.drain()`
```python
writer.write(b"HEAD / HTTP/1.0\r\n\r\n")    # gönderme kuyruğuna koy (bekletmez)
await writer.drain()                        # verinin gerçekten gitmesini bekle
```
- `write` bytes ister (`b"..."`), string değil.
- `\r\n` = HTTP'de satır sonu. Boş satır (`\r\n\r\n`) = "istek bitti".

### 3.5 `writer.close()` ve `await writer.wait_closed()`
Bağlantıyı kapatır. `close()` kapatma emrini verir, `wait_closed()` gerçekten kapanana kadar bekler. Kapanışta hata çıkarsa tarama bozulmasın diye `try/except` içinde.

### 3.6 `asyncio.Semaphore(n)` {#Semaphore}
**Eşzamanlılık sınırı.** "Aynı anda en fazla `n` iş içeri girebilir" kuralı. Otoparkın `n` park yeri olması gibi: dolunca yeni arabalar bekler.

```python
import asyncio, time

async def is_yap(no, sem):
    async with sem:                       # kapıdan geç (yer yoksa bekle)
        print(f"{no} başladı")
        await asyncio.sleep(1)
        print(f"{no} bitti")

async def main():
    sem = asyncio.Semaphore(2)            # aynı anda en fazla 2
    t = time.perf_counter()
    await asyncio.gather(*(is_yap(i, sem) for i in range(4)))
    print(f"{time.perf_counter() - t:.0f} sn")

asyncio.run(main())
```
Çıktı: önce 0 ve 1 başlar, 1 sn sonra 2 ve 3 başlar. Toplam **2 sn** (4 iş, 2'şerli gruplar).

**Neden gerekli?** 65 bin porta aynı anda bağlanmaya çalışırsan:
- İşletim sistemi açık bağlantı (file descriptor) sınırına çarpar → hata.
- Hedefi/ağı boğarsın, güvenlik sistemlerini tetiklersin.
Araçtaki `-c 100` değeri bu sınırdır.

### 3.7 `asyncio.get_running_loop()` ve `loop.getaddrinfo()`
- **Event loop:** async görevleri yöneten döngü ([[00_proje_temelleri#7. Asenkron (async) programlamanın sıfırdan mantığı]]).
- `get_running_loop()` → şu an çalışanı verir.
- `loop.getaddrinfo(host, port, family=...)` → alan adını IP'ye çevirir (DNS sorgusu), **ama** event loop'u dondurmadan yapar.

Normal `socket.getaddrinfo` bloklayıcıdır: DNS cevabı gelene kadar tüm program donardı. `loop.getaddrinfo` işi arka planda halleder.

Dönen değer:
```python
[(AddressFamily.AF_INET, SocketKind.SOCK_STREAM, 6, '', ('93.184.216.34', 0))]
#   ↑ ilk kayıt                                         ↑ (IP, port)
```
Kodda: `addr_info[0][4][0]`
- `[0]` → ilk kayıt
- `[4]` → 5. eleman, `('93.184.216.34', 0)`
- `[0]` → bu demetin ilk elemanı = **IP**

### 3.8 `asyncio.gather(*coroutineler)`
Birden fazla görevi **aynı anda** çalıştırır, hepsi bitince döner.
```python
await asyncio.gather(worker(21), worker(22), worker(80))
```
Kodda binlerce port olabilir, elle yazamayız:
```python
await asyncio.gather(*(worker(port) for port in config.ports))
#                    ↑ yıldız: generator'ü ayrı ayrı argümanlara açar
```
`*` operatörü: `f(*[1,2,3])` = `f(1,2,3)`.

### 3.9 `async with`
`with`'in async hali ([[00_proje_temelleri#6.3 with]]). Kodda `async with semaphore:` → kapıdan gir, işin bitince otomatik çık.

---

## 4. `socket` ve `time`

### `socket.AF_INET`
IPv4 adres ailesi sabiti. `getaddrinfo`'ya "bana sadece IPv4 adresi ver" demek için. (`AF_INET6` = IPv6.) Dosyada `socket` ile bağlantı kurulmaz, bağlantıyı `asyncio` kurar.

### `time.perf_counter()`
Çok hassas bir kronometre (saniye, ondalıklı).
```python
import time
baslangic = time.perf_counter()
# ... iş ...
sure = time.perf_counter() - baslangic
print(f"{sure * 1000:.2f} ms")        # saniyeyi milisaniyeye çevir
```
`time.time()`'ın aksine sistem saati değişse bile şaşmaz. Kodda **bağlantı kurma süresi** ölçülür (`latency_ms`).

---

## 5. `rich.progress`: ilerleme çubuğu

```python
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(complete_style="cyan", finished_style="green"),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    TimeRemainingColumn(),
    console=console,
) as progress:
    task = progress.add_task("[cyan]Scanning TCP ports...", total=len(config.ports))
    ...
    progress.advance(task)
```
Görünüm: `⠋ Scanning TCP ports... ━━━━━━━━━━━━ 45% 0:00:03`

| Parça | Ne gösterir |
|---|---|
| `SpinnerColumn()` | Dönen animasyon |
| `TextColumn("...")` | Yazı. `{task.description}` görevin adı, `{task.percentage}` yüzde |
| `BarColumn(...)` | Çubuk; bitmemiş kısım cyan, bitince yeşil |
| `TimeRemainingColumn()` | Tahmini kalan süre |
| `console=console` | Ortak konsol ([[02_logger]]) |

| Metot | Görev |
|---|---|
| `progress.add_task(açıklama, total=N)` | Yeni görev ekler, **kimliğini** döndürür |
| `progress.advance(task)` | İlerlemeyi 1 artırır |

`with` bloğu: çıkışta çubuğu temizler ve terminali düzgün bırakır.

---

## 6. Dosyadaki yapılar ve fonksiyonlar

### 6.1 `WELL_KNOWN_SERVICES` sözlüğü
```python
WELL_KNOWN_SERVICES = {21: "FTP", 22: "SSH", 80: "HTTP", ...}
WELL_KNOWN_SERVICES.get(port, "Unknown")      # port yoksa "Unknown"
```
Port numarasından **tahmini** servis adı. (Port 22'de SSH olduğunu varsayarız ama garanti değil. Banner bunu doğrular/düzeltir.)

### 6.2 `PortScanResult` (dataclass)
```python
@dataclass
class PortScanResult:
    port: int
    state: str
    service: str
    banner: str
    latency_ms: float
```
Tek portun sonucu. `state` yorumunda 3 durum yazıyor ama kod yalnızca `"open"` üretir.

### 6.3 `grab_banner(reader, writer, port, timeout)`

Akış:
```
1) PASİF: bir şey göndermeden timeout kadar dinle
      ├─ veri geldi → banner = o metin
      └─ gelmedi (TimeoutError) → 2'ye geç
2) AKTİF: banner hâlâ boşsa HTTP isteği gönder
      ├─ cevaptaki "Server:" veya "HTTP/" satırını al
      └─ yoksa cevabın ilk satırını al
3) finally: banner'ı temizle (tek satır, en fazla 60 karakter)
```

Kullanılan Python parçaları:
```python
data.decode(errors="replace")
```
bytes → metin. `errors="replace"` bozuk byte varsa `�` koyar, çökmez.

```python
" ".join(banner.split())
```
`split()` boşluk/satır sonu/tab'a göre ayırır, `" ".join` tek boşlukla birleştirir. **Fazla boşlukları ve satır sonlarını tek boşluğa indirir.**
```python
"SSH-2.0\r\n  OpenSSH".split()          # ['SSH-2.0', 'OpenSSH']
" ".join(['SSH-2.0', 'OpenSSH'])        # 'SSH-2.0 OpenSSH'
```

```python
banner[:57] + "..."          # 60 karaktere kısalt
```

```python
for line in text.splitlines():
    if line.lower().startswith("server:") or line.startswith("HTTP/"):
```
- `splitlines()` → satır listesi.
- `.lower()` → büyük/küçük harf farkını yok say (`Server:` / `server:`).
- `.startswith(x)` → x ile başlıyor mu.

Banner içindeki `HEAD / HTTP/1.0` isteği: HTTP'de `HEAD`, sayfanın **gövdesini değil sadece başlıklarını** ister. `Server:` başlığı yazılım bilgisini taşır (`Server: nginx/1.18.0`).

### 6.4 `scan_single_port(...)`
```python
async with semaphore:                                   # sıra bekle
    start_time = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target_ip, port), timeout=timeout)
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        ...
        return PortScanResult(...)
    except (asyncio.TimeoutError, OSError):
        return None                                     # kapalı veya filtreli
```
Servis adını düzeltme mantığı:
```python
if "SSH" in banner:                 service_name = "SSH"
elif "HTTP" in banner or "nginx" in banner ...:
    service_name = "HTTPS" if port in (443, 8443) else "HTTP"
```
- `"SSH" in banner` → metin içinde geçiyor mu.
- `a if koşul else b` → tek satırlık if (üçlü ifade).
- `port in (443, 8443)` → port bu sayılardan biri mi.

Dönüş tipi: `Optional[PortScanResult]` → ya sonuç ya `None`.

### 6.5 `resolve_target(target)`
Alan adı → IPv4. Hata olursa mesaj basıp `None` döndürür:
```python
log_error(f"DNS Resolution failed for {target}: {e}")
```
`except Exception as e` → hatayı `e` değişkenine alır, mesajı yazdırabiliriz.

### 6.6 `run_port_scan(config)`: orkestratör

Adımlar:
1. `resolve_target` ile IP bul. Başarısızsa `return []` (boş liste).
2. `config.target_ip = target_ip` (config'e yaz, diğer modüller de kullanabilir).
3. `Semaphore` ve boş `open_ports` listesi oluştur.
4. `Progress` bloğunda her port için `worker` görevi oluştur → `gather`.
5. `open_ports.sort(key=lambda r: r.port)` → port numarasına göre sırala.
6. `create_table` → satırları ekle → ekrana bas.
7. `open_ports`'u döndür (`recon.py` bunu JSON'a çevirecek).

#### İç fonksiyon (closure) nedir?
`worker`, `run_port_scan`'ın **içinde** tanımlanmış:
```python
def dis():
    sayac = 0
    def ic():
        print(sayac)      # dıştaki değişkeni görebilir
    ic()
```
İç fonksiyon, dıştaki değişkenlere (`progress`, `task`, `open_ports`, `semaphore`) erişir. Bunları parametre olarak geçmek zorunda kalmayız.

#### Neden `open_ports.append` güvenli?
Event loop tek thread'dir. İki `worker` aynı anda **aynı satırı** çalıştırmaz; kontrol sadece `await` noktalarında geçer. Thread'lerde olduğu gibi kilit gerekmez.

---

## 7. Veri akışı

```
config.ports ─► worker(80) ─┐
                worker(443) ─┼─► scan_single_port ─► (bağlan → banner oku → sonuç)
                worker(22) ──┘          │
                                         ▼
                              open_ports listesi ─► tablo ─► recon.py ─► JSON
          (Semaphore: aynı anda en fazla 100 worker bağlantıda)
```

---

## 8. Dikkat edilecek noktalar
- `except Exception: pass` hatayı **gizler**; hata ayıklarken bilgi kaybı olur.
- `import socket` sadece `AF_INET` için; `log_warn` kullanılmıyor.
- `gather`'da bir görev hata fırlatırsa ilk hata yukarı çıkar. `return_exceptions=True` ile bu davranış değiştirilebilir.
- `latency_ms` sadece bağlantı kurma süresidir (banner süresi dahil değil).
- Kapalı ve filtreli port ayrılmıyor; ikisi de `None`. Ayırmak için: `ConnectionRefusedError` → kapalı, `TimeoutError` → filtreli.
- Sadece **izinli** sistemlerde tara. İzinsiz tarama birçok ülkede hukuki sorundur.

## 9. Tekrar soruları
1. Port nedir? Açık, kapalı ve filtreli port arasındaki fark?
2. Pasif ve aktif banner grabbing farkı? Hangi servis hangisine yanıt verir?
3. `Semaphore` olmasaydı ne olurdu?
4. `wait_for` neden her ağ işleminde kullanılıyor?
5. `asyncio.gather(*(worker(p) for p in ports))` içindeki `*` ne yapar?
6. Closure nedir, `worker` bundan nasıl faydalanıyor?
