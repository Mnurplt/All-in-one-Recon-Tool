# Blind SQL Injection with Time Delays — Write-up

**Platform:** PortSwigger Web Security Academy **Lab:** Blind SQL injection with time delays **Sonuç:** Çözüldü ✅

## Özet

Bu lab'da `/product` endpoint'ine gönderilen isteklerdeki `TrackingId` cookie değeri, sunucu tarafında herhangi bir sanitizasyon yapılmadan bir SQL sorgusuna doğrudan dahil ediliyor. Uygulama, sorgu sonucunu (true/false, hata, veri) hiçbir şekilde sayfa içeriğine veya response'a yansıtmadığı için klasik **blind SQL injection** senaryosu ile karşı karşıyayız. Injection'ın varlığı, PostgreSQL'e özgü `pg_sleep()` fonksiyonu ile tetiklenen bir zaman gecikmesi (time delay) üzerinden kanıtlanmıştır.

## Ortam ve Araçlar

- Burp Suite Community Edition (Repeater sekmesi üzerinden manuel test)
- Hedef: `https://<lab-id>.web-security-academy.net`
- Injection noktası: `Cookie: TrackingId=<değer>`

## Metodoloji

Blind SQL injection senaryolarında izlenen standart yaklaşım, sırasıyla farklı sinyal kaynaklarının (content/boolean, error, time) mevcut olup olmadığını test etmek ve çalışanı bulduktan sonra onunla devam etmektir. Bu write-up'ta izlenen adımlar bu sırayı takip etmiştir.

### Adım 1 — İlk İsteğin Yakalanması

Burp Repeater'da yakalanan temel istek:

```
GET /product?productId=1 HTTP/2
Cookie: TrackingId=Z59TkUUGGOGYLM9h; session=...
```

Bu istekteki `TrackingId` cookie'si, olası bir injection noktası olarak test edilmeye başlandı.

### Adım 2 — Injection Noktasının Doğrulanması

`TrackingId` değerine tek tırnak ve SQL yorum satırı eklendi:

```
TrackingId=Z59TkUUGGOGYLM9h'--
```

Sayfa normal şekilde yüklendi, hata mesajı veya görsel bir fark oluşmadı. Uygulamanın davranışı injection sonucuna göre değişmediği için, injection'ın varlığının zaman tabanlı (time-based) bir teknikle test edilmesi gerektiği öngörüldü.

### Adım 3 — Boolean-based (Content-based) Test

Her zaman doğru ve her zaman yanlış olan koşullar ayrı ayrı denendi:

```
TrackingId=Z59TkUUGGOGYLM9h' AND 1=1--   → 105ms, sayfa normal
TrackingId=Z59TkUUGGOGYLM9h' AND 1=2--   → 101ms, sayfa normal
```

İki durumda da sayfa içeriğinde veya response süresinde ayırt edici bir fark gözlenmedi. `productId` parametresine karşılık gelen ürün bilgisi (ad, fiyat, görsel) sabit içerik olduğu için, enjekte edilen koşulun sonucu sayfaya hiçbir şekilde yansımıyor. Bu, boolean-based blind tekniğinin bu uygulamada kullanılamayacağını doğruladı.

### Adım 4 — Syntax / WAF Hassasiyeti ve DB Türünün Daraltılması

String concatenation operatörü (`||`) ve içine gömülü bir `SELECT` alt sorgusu ile hem syntax kabulü hem de olası bir WAF/filtre varlığı test edildi:

```
TrackingId=Z59TkUUGGOGYLM9h'||(SELECT '')||'
```

İstek hatasız işlendi (104ms). Bunun anlamlı olmasının nedeni: **Oracle'da** `SELECT` ifadesi her zaman bir `FROM` cümlesi gerektirir (örn. `FROM dual`); `FROM` olmadan kullanılan bir `SELECT` Oracle'da sözdizimi hatası verir. Bu payload'ın sorunsuz çalışması:

- Hedef veritabanının **Oracle olmadığını** gösterdi,
- `SELECT` içeren alt sorguların bir WAF/filtre tarafından engellenmediğini doğruladı.

### Adım 5 — Error-based Sinyal Testi

**5a) Division by zero (kontrol amaçlı, true koşul):**

```
TrackingId=Z59TkUUGGOGYLM9h' AND 1=(SELECT CASE WHEN (1=1) THEN 1 ELSE 1/0 END)--
```

Koşul (`1=1`) doğru olduğu için CASE ifadesi `1/0` dalına girmedi, beklendiği gibi hata oluşmadı (92ms).

**5b) Casting error:**

```
TrackingId=Z59TkUUGGOGYLM9h' AND 1=CAST((SELECT 'a') AS int)--
```

`'a'` string'inin `int` tipine cast edilmesi normalde bir dönüşüm hatası doğurur; ancak response'ta herhangi bir hata, status code değişikliği veya boyut farkı gözlenmedi (95ms, 4.378 byte — önceki isteklerle aynı).

**Ara değerlendirme:** Content-based ve error-based sinyal kaynaklarının hiçbiri uygulama davranışında ayırt edici bir fark yaratmadı. Geriye tek güvenilir sinyal kaynağı olarak **response süresi (time-based blind)** kaldı.

### Adım 6 — DB Türüne Özgü Time-Delay Testleri

PortSwigger Academy'nin referans tablosundaki syntax'lar `||` concatenation kalıbına uyarlanarak sırayla test edildi:

| DB | Payload | Sonuç |
| --- | --- | --- |
| MySQL | `'\|\|(SELECT SLEEP(10))\|\|'` | 93ms — gecikme yok |
| PostgreSQL | `'\|\|(SELECT pg_sleep(10))\|\|'` | **\~10.125ms (\~10sn)** — gecikme doğrulandı ✅ |

MySQL'e özgü ilk testte de (`' AND SLEEP(10)--`) benzer şekilde gecikme gözlenmemişti.

## Sonuç

Hedef veritabanı **PostgreSQL**'dir. `TrackingId` cookie'si, sunucu tarafında sanitize edilmeden bir SQL sorgusuna doğrudan dahil edilmektedir ve `pg_sleep()` fonksiyonu ile tetiklenen \~10 saniyelik gecikme, zaman tabanlı (time-based) blind SQL injection zafiyetinin varlığını kesin olarak kanıtlamıştır.

**Başarılı payload:**

```
Cookie: TrackingId=Z59TkUUGGOGYLM9h'||(SELECT pg_sleep(10))||'
```

## Elenen İhtimaller ve Gerekçeleri

| Veritabanı | Neden Elendi |
| --- | --- |
| Oracle | `FROM`'suz `SELECT` hata vermedi (Oracle'da hata vermesi beklenirdi) |
| MySQL | `SLEEP(10)` ve `SELECT SLEEP(10)` payload'ları gecikme yaratmadı |
| Microsoft SQL Server | Test edilmedi (PostgreSQL ilk denemede başarılı olduğu için gerek kalmadı) |

## Çıkarılan Dersler

- Blind SQLi tespitinde sinyal kaynaklarını (content, error, time) sistematik olarak sırayla test etmek, rastgele payload denemekten daha güvenilir sonuç verir.
- Bir syntax'ın hatasız çalışması/çalışmaması, DB'ye özgü davranış farklarından (örn. Oracle'ın `FROM` zorunluluğu) yola çıkılarak DB türünü daraltmak için kullanılabilir.
- Uygulama sayfa içeriğini ve hata davranışını tamamen gizlese bile, response süresi her zaman gözlemlenebilir bir yan kanal olarak kalır — bu da time-based tekniği blind SQLi'de en güvenilir yöntemlerden biri yapar.
