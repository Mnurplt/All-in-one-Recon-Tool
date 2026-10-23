# 🚀 All-in-One Recon Tool — Implementation & Progress Plan

## 📌 Proje Özeti ve Vizyon

**All-in-One Recon Tool**, modern bir siber güvenlik testinde (penetration testing & bug bounty) **saldırı yüzeyi keşfi (attack surface mapping)** sürecini tek bir çatı altında toplayan, asenkron mimaride geliştirilmiş modüler bir Python framework'üdür.

Piyasada birbirinden kopuk çalışan araçların (Nmap, Gobuster, Subfinder, Feroxbuster) temel yeteneklerini, harici ikili dosya (binary) bağımlılığı olmadan **saf Python (`asyncio`, `aiohttp`, `dnspython`, `rich`)** kullanarak bir araya getirir.

---

## 🏗️ Mimari ve Tasarım İlkeleri

1. **Non-Blocking Asenkron Çekirdek:**
   * Klasik `multithreading` yerine Python'ın `asyncio` Event Loop mimarisi kullanılır.
   * `asyncio.Semaphore` ile eşzamanlı istek/soket limitleri kontrol altında tutulur (`socket exhaustion` ve işletim sistemi çökmeleri engellenir).
2. **Derinlemesine Ağ ve Protokol Anlayışı:**
   * "Vibe coding" yerine her modülde ilgili OSI katmanının (L4 TCP Handshake, L7 DNS, L7 HTTP) protokol davranışları ve paket seviyesindeki mantığı gözetilir.
3. **Modülerlik ve Zincirlenebilirlik (Pipeline Ready):**
   * Her modül hem bağımsız olarak çalışabilir hem de `target -> subdomains -> open ports -> web fuzzing -> vhosts` zincirinde bir diğer modüle girdi sağlayacak standart veri formatlarına (JSON / Python dataclass) sahiptir.
4. **PortSwigger Hibrit Sinerjisi:**
   * Araç geliştirme süreci, PortSwigger Web Security Academy labları (95 lab) ile eşzamanlı yürütülür (Keşif Modülü ➔ Zafiyet Sömürüsü).

---

## 🧭 Fazlar ve Güncel Durum Tablosu

| Faz | Modül / Konu | Katman | Durum |
| :---: | :--- | :---: | :---: |
| **Faz 1** | **Asenkron Çekirdek, CLI (`recon.py`), Logger & Config** | Core / Engine | ✅ **Tamamlandı** |
| **Faz 2** | **L4 TCP Port Scanner & Banner Grabbing (`port_scanner.py`)** | L4 Transport | ✅ **Tamamlandı** |
| **Faz 3** | **L7 Subdomain Discovery (DNS Brute-Force + `crt.sh` + Wildcard)** | L7 DNS / OSINT | ✅ **Tamamlandı** |
| **Faz 4** | **L7 Web Directory & File Fuzzer (`dir_scanner.py` + Soft-404)** | L7 HTTP | ⏳ **Sırada** |
| **Faz 5** | **L7 Virtual Host (VHost) Enumerator (`vhost_scanner.py`)** | L7 Reverse Proxy | 📋 Planlandı |
| **Faz 6** | **Pipeline Entegrasyonu, Birleşik Raporlama & Staj Savunması** | Integration | 📋 Planlandı |

---

## 🛠️ Tamamlanan Aşamalar Detayı

### ✅ Faz 1: Asenkron Motor ve Proje İskeleti (Tamamlandı)
* **Bağımlılıklar:** `aiohttp>=3.9.0`, `dnspython>=2.6.0`, `rich>=13.7.0` yapılandırıldı.
* **`core/config.py`:** `@dataclass` tabanlı merkezi yapılandırma sınıfı oluşturuldu (`ReconConfig`).
* **`core/logger.py`:** `rich` tabanlı renkli konsol çıktıları ve Windows terminalindeki `CP1254/UTF-8` Unicode kodlama uyumluluğu sağlandı.
* **`recon.py`:** `argparse` ile komut satırı arayüzü kuruldu (`-t`, `-p`, `--subdomains`, `--dirs`, `--vhosts`, `--all`, `-c`, `-o`).
* **`wordlists/`:** Subdomain, dizin ve vhost testleri için dahili mini sözlükler hazırlandı.

### ✅ Faz 2: L4 Port Scanner & Banner Grabbing (Tamamlandı)
* **`modules/port_scanner.py`:**
  * `asyncio.open_connection` ile root gerektirmeyen taşınabilir **TCP Connect Scan** yazıldı.
  * Açık (`SYN-ACK`), kapalı (`RST`) ve filtrelenmiş (`DROP / Timeout`) port durumları ayrıştırıldı.
  * **İki Kademeli Banner Grabbing:**
    1. *Pasif Dinleme:* İlk konuşan servisler (SSH, FTP, SMTP, MySQL) için 1.5s soket okuması.
    2. *Aktif HTTP Probu:* İstemci bekleyen web servisleri için `HEAD / HTTP/1.0` probu ve `Server:` başlığı ayrıştırma.
  * `time.perf_counter()` ile milisaniye hassasiyetinde bağlantı gecikmesi (latency) ölçümü.
  * `scanme.nmap.org` üzerinde test edilip doğrulandı; JSON çıktı desteği eklendi.

### ✅ Faz 3: L7 Subdomain Enumeration (Tamamlandı)
* **`modules/subdomain_scanner.py`:**
  * `dnspython`'ın asenkron çözücüsü (`dns.asyncresolver.Resolver`) ile paralel DNS sorguları (A ve CNAME kayıtları).
  * **Wildcard DNS Tespiti ve Filtresi:** Rastgele üretilen bir alt alan adı üzerinden `*.domain.com` wildcard IP'si yakalanıp sahte pozitiflerin (false-positive) elenmesi sağlandı.
  * **Hibrit Pasif OSINT:** `crt.sh` üzerinden SSL/TLS Certificate Transparency logları sorgulanarak hedefe paket göndermeden aday alt alan adları toplandı.
  * Subdomainlerin CNAME/Alias zincirleri ve milisaniye bazlı DNS çözümleme gecikmeleri hesaplandı.
  * `python.org` ve `nmap.org` üzerinde test edilip doğrulandı.

---

## 📋 Sıradaki Adımlar

### ⏳ Faz 3: L7 Subdomain Enumeration (Sıradaki Adım)
* `dnspython` asenkron resolver entegrasyonu (A, CNAME sorguları).
* **Wildcard DNS Tespiti:** Rastgele üretilen bir alt alan adı (`random-uuid.target.com`) çözümlenerek sahte pozitiflerin (false-positive) elenmesi.
* **crt.sh Pasif OSINT:** Hedefe sıfır DNS paketi göndermeden SSL/TLS Certificate Transparency loglarından alt alan adlarının çekilmesi.

### 📋 Faz 4: L7 Directory & File Fuzzing
* `aiohttp.ClientSession` bağlantı havuzu (connection pooling) ile yüksek hızlı HTTP GET/HEAD istekleri.
* Uzantı fuzzer (`.php`, `.txt`, `.html`, `.bak`, `.json`).
* **Soft-404 Filtreleme:** HTTP 200 dönen sahte hata sayfalarını gövde boyutu (Content-Length) veya kelime sayısı benzerliğiyle eleme.

### 📋 Faz 5: L7 Virtual Host (VHost) Enumerator
* Aynı IP adresine farklı `Host: <subdomain>.target.com` başlıkları gönderilerek ters proxy (Nginx/Apache vhost) yönlendirmelerinin yakalanması.
* Baseline Profiling ile varsayılan host yanıtının filtrelenmesi.

### 📋 Faz 6: Büyük Entegrasyon & Staj Raporu
* Modüllerin tek bir komutla (`python recon.py -t target.com --all`) birbirine veri aktarması.
* HTML ve JSON formatında son kullanıcı raporu.
* Staj koordinatörüne ve jüriye sunulmak üzere **Teknik Mimari ve Protokol Analiz Dokümantasyonu**.

---

## 🎯 PortSwigger Hibrit Eşleştirme Takvimi (95 Lab)

| Hafta | Recon Proje Fazı | Eşleşen PortSwigger Konuları | Lab Sayısı | Temel Sinerji |
| :---: | :--- | :--- | :---: | :--- |
| **1. Hafta** | Faz 1 & Faz 2 (L4 Port Scan) | **Information Disclosure** (5) + **SSRF** (7) + **Authentication** (14) | 26 Lab | Port tarama ve dahili IP/port keşfi doğrudan SSRF'in temelidir. Banner grabbing ise Information Disclosure ile örtüşür. |
| **2. Hafta** | Faz 3 (L7 Subdomain) | **Access Control** (13) + **JWT Attacks** (8) + **CORS** (3) | 24 Lab | Keşfedilen alt alan adlarındaki admin panelleri ve CORS yapılandırma hataları. |
| **3. Hafta** | Faz 4 (L7 Dizin Fuzzing) | **Business Logic** (11) + **CSRF** (12) | 23 Lab | Dizin taramasında bulunan gizli ödeme/transfer API'lerinin mantık analizi. |
| **4. Hafta** | Faz 5 & Faz 6 (VHost & Final) | **HTTP Request Smuggling** (22) | 22 Lab | VHost modülündeki Ters Proxy mimarisi, Request Smuggling'in tam temelini oluşturur. |
