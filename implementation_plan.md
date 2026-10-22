# All-in-One Recon Tool — Implementation Plan

## Proje Nedir

**All-in-One Recon Tool**, bir pentest/bug bounty engagement'ının **recon (keşif) fazını** tek bir çatı altında toplayan, Python ile geliştirilen modüler bir araçtır. Amaç, piyasada ayrı ayrı var olan recon araçlarının (nmap, gobuster, subfinder, gobuster vhost gibi) işlevlerini kendi implementasyonlarıyla bir araya getirip, hem **tek başına** hem de **birbirine zincirlenmiş (piped)** şekilde çalışabilen tutarlı bir sistem kurmaktır.

### Kapsanan modüller

1. **Network enumeration** — hedefteki açık portları ve servisleri tespit eden modül (nmap mantığına dayalı).
2. **Web dizin/dosya tarama (directory brute-forcing)** — bir web hedefinde gizli dizin ve dosyaları bulan modül (gobuster/ffuf mantığına dayalı).
3. **Subdomain tarama** — bir domain altındaki alt alan adlarını keşfeden modül.
4. **Virtual host (vhost) tarama** — aynı IP üzerinde barındırılan farklı sanal hostları tespit eden modül.

### Tasarım felsefesi: Modülerlik + Entegrasyon

Projenin en kritik tasarım kararı şudur: her modül **bağımsız, kendi başına çalışabilen bir araç** olarak yazılır (kendi CLI argümanları, kendi girdi/çıktı formatı ile), ama aynı zamanda modüller arasında **pipe (|) yöntemiyle veri aktarımı** yapılabilecek şekilde tasarlanır. Yani:

- Kullanıcı sadece network enumeration modülünü tek başına çalıştırabilir.
- Kullanıcı network enumeration çıktısını doğrudan web dizin tarama modülüne pipe'layarak, bulunan HTTP servisleri üzerinde otomatik dizin taraması başlatabilir.
- Aynı mantık subdomain → vhost → dizin tarama zincirinde de kurulabilir.

Bu, hem UNIX felsefesine (her araç bir işi iyi yapar, araçlar birbirine bağlanabilir) uygun bir yapı hem de tek bir monolitik script yerine, her modülün ayrı ayrı test edilip geliştirilebildiği sürdürülebilir bir mimari sağlar.

---

## Proje Adımları ve Süreçler

### Adım 1 — Teorik Altyapı
Projeye başlamadan önce gerekli teorik temeli oluşturmak:
- **PortSwigger Web Security Academy** kaynaklarından web uygulama güvenliği ve ilgili zafiyet sınıfları üzerine çalışma.
- **Black Hat Python** kitabından, özellikle ağ programlama, brute-forcing ve fuzzing ile ilgili bölümlerden pratik Python/network programlama bilgisi edinme.

*Çıktı: Modülleri yazmak için gereken teorik ve pratik Python/network/web bilgisi.*

### Adım 2 — Network Enumeration Modülü
Projenin ilk teknik bileşeni olarak network enumeration (port/servis tarama) modülünün geliştirilmesi.
- Hedef host(lar) üzerinde port tarama mantığının kodlanması.
- Açık portlardan servis/banner bilgisinin çıkarılması.
- Sonuçların, sonraki modüllere aktarılabilecek yapılandırılmış bir formatta (ör. JSON/plain text) üretilmesi.

*Çıktı: Bağımsız çalışabilen, komut satırından bir hedef alıp açık port/servis listesi üreten ilk modül.*

### Adım 3 — Web Dizin Tarama Modülü ve Pipe Entegrasyonu
- Web dizin/dosya tarama (directory brute-forcing) modülünün geliştirilmesi: bir hedef URL ve wordlist alıp, var olan dizin/dosyaları tespit etme.
- **Modüller arası pipe entegrasyonunun kurulması**: Adım 2'deki network enumeration modülünün çıktısının, bu modüle doğrudan girdi olarak verilebilmesi (örn. `python network_scan.py <hedef> | python dir_scan.py`).
- Pipe yönteminin genel bir standart haline getirilmesi — yani bundan sonra eklenecek her modülün bu aynı girdi/çıktı sözleşmesine uyması.

*Çıktı: Web dizin tarama modülü + network ve web tarama modüllerinin birbirine zincirlenebildiği çalışan bir pipeline.*

### Adım 4 — Subdomain ve Virtual Host Tarama Modülleri
- **Subdomain tarama modülü**: bir ana domain altındaki alt alan adlarını (wordlist tabanlı ve/veya DNS sorgularıyla) keşfeden bileşenin geliştirilmesi.
- **Virtual host tarama modülü**: aynı IP adresinde barındırılan, farklı Host header'larıyla ayrışan sanal hostları tespit eden bileşenin geliştirilmesi.
- Bu iki modülün de Adım 3'te kurulan pipe standardına uygun şekilde entegre edilmesi — böylece subdomain/vhost sonuçları da doğrudan dizin tarama veya network enumeration modüllerine aktarılabilir hale gelir.

*Çıktı: Dört modülün tamamının bağımsız ve zincirlenebilir şekilde çalıştığı, projenin ilk eksiksiz versiyonu.*

---

## Sonraki Adımlar (bu dosyanın kapsamı dışında, ileride planlanacak)

- Her modül için README/kullanım dokümantasyonu.
- Orchestrator (ana akışı yöneten) bir script ile tüm modüllerin tek bir komutla uçtan uca zincirlenmesi.
- Hız/performans ayarları (thread/rate limiting) ve hata yönetimi.
