# PortSwigger Lab Write-up: Blind SQL Injection with Time Delays and Information Retrieval

**Lab:** Blind SQL injection with time delays and information retrieval
**Araç:** Burp Suite Community Edition (Repeater + Intruder)
**Enjeksiyon noktası:** `TrackingId` cookie değeri

---

## Adım 1 — TrackingId cookie'sine tek tırnak enjekte etme

**Payload:**
```
Cookie: TrackingId=IQguipmvRGtEYuxf'; session=...
```

**Ne yapıldı / neden:**
Klasik SQL injection keşif adımı. Eğer backend bu cookie değerini bir SQL sorgusuna doğrudan (parametrize etmeden) yapıştırıyorsa, tek tırnak sorgunun string literal'ini erken kapatır ve sorgu sözdizimsel olarak bozulur. Normal bir uygulamada bu genelde bir hata ya da davranış farkı olarak görünür. Lab adında "blind" geçtiği için sayfa hata mesajı göstermeyecek şekilde tasarlanmış olabilir — yani injection var olsa bile ekranda görünmeyecek.

**Sonuç:** Sayfa normal şekilde render oldu ("Couple's Umbrella", $82.13). Görünür hata yok. Bu beklenen bir sonuç — "blind" SQLi'de hata görmeyi beklemiyoruz zaten.

---

## Adım 2 — Tek tırnaktan sonra SQL yorum satırı (`--`) ekleme

**Payload:**
```
Cookie: TrackingId=IQguipmvRGtEYuxf'--; session=...
```

**Ne yapıldı / neden:**
`--` SQL'de "bu satırın geri kalanını yorum satırı yap" anlamına gelir. Böylece açılan tırnağı kapatmak zorunda kalmadan sorgunun geri kalanı devre dışı bırakılır:

```sql
SELECT * FROM tracking WHERE id = 'IQguipmvRGtEYuxf'--' AND ...
```

`--`'den sonrası yorum olduğu için sorgu sözdizimsel olarak geçerli hale gelir. Bu, tek tırnağın sorguyu gerçekten bozduğunu (injection noktası olduğunu) doğrulamak için klasik bir yöntem.

**Sonuç:** Sayfa yine tamamen normal geldi, hata yok, davranış farkı yok.

---

## Adım 3 — Boolean-based test: `AND 1=1--` (TRUE koşulu)

**Payload:**
```
Cookie: TrackingId=CXmVOSo7cE4oAbb1' AND 1=1--; session=...
```

**Ne yapıldı / neden:**
Boolean-based blind SQLi testinin ilk yarısı. `AND 1=1` her zaman doğru olduğu için, sorgu normal şekilde çalışmaya devam etmeli ve sayfa her zamanki gibi dönmeli.

**Sonuç:** Sayfa normal geldi ("Six Pack Beer Belt", $44.70). Beklenen davranış.

---

## Adım 4 — Boolean-based test: `AND 1=2--` (FALSE koşulu)

**Payload:**
```
Cookie: TrackingId=CXmVOSo7cE4oAbb1' AND 1=2--; session=...
```

**Ne yapıldı / neden:**
Kontrol grubu. `1=2` her zaman yanlış olduğu için, eğer injection çalışıyorsa sorgu hiçbir satır döndürmemeli ve sayfa davranışı adım 3'ten farklı olmalı.

**Sonuç:** Aynı ürün bilgisi döndü ("Six Pack Beer Belt", $44.70) — adım 3 ile **aynı**, fark yok.

**Yorum:** Bu sonuç, `TrackingId` cookie'sinin sorgu sonucunun sayfaya yansıdığı bir yer olmadığını gösteriyor — muhtemelen bu sorgu bir loglama/tracking amaçlı sorgu, ürün verisini etkilemiyor. Bu yüzden boolean-based (içerik farkına dayalı) yaklaşım burada işe yaramıyor. Bu da lab adının neden "time delays" dediğini açıklıyor: sonucu kanıtlamanın tek yolu zamanlama farkı yaratmak.

---

## Adım 5 — String concatenation ile subquery testi

**Payload:**
```
Cookie: TrackingId=CXmVOSo7cE4oAbb1'||(SELECT '')||'; session=...
```

**Ne yapıldı / neden:**
`||` operatörü ile (Oracle/PostgreSQL string concatenation) cookie değerinin sonuna boş bir string döndüren bir subquery birleştirildi. Amaç: sorgunun subquery ile birlikte hâlâ sözdizimsel olarak geçerli çalışıp çalışmadığını test etmek — zaman tabanlı asıl payload'a geçmeden önceki bir iskelet testi.

**Sonuç:** Sayfa normal geldi, hata yok — bu sözdizimi hedef veritabanında kabul ediliyor.

---

## Adım 6 — Zaman tabanlı payload: temel TRUE testi

**Payload:**
```
TrackingId=x'; SELECT CASE WHEN (1=1) THEN pg_sleep(10) ELSE pg_sleep(0) END--
```

**Ne yapıldı / neden:**
Tek tırnaktan sonra `;` ile yeni bir SQL ifadesi başlatılıyor (stacked query) ve bir `CASE WHEN` koşulu enjekte ediliyor:
- Koşul (`1=1`) doğruysa → `pg_sleep(10)` çalışır → sunucu 10 saniye bekler
- Koşul yanlışsa → `pg_sleep(0)` çalışır → gecikme olmaz

Sonuç artık sayfa içeriğinden değil, **yanıt süresinden** okunuyor — içerik fark etmiyor, sadece zamanlama önemli.

**Beklenen sonuç:** Yanıt ~10 saniyede gelmeli. Bu, injection'ın çalıştığının kesin kanıtı.

---

## Adım 7 — Kontrol testi: FALSE koşulu

**Payload:**
```
TrackingId=x'; SELECT CASE WHEN (1=2) THEN pg_sleep(10) ELSE pg_sleep(0) END--
```

**Ne yapıldı / neden:**
Adım 6'nın kontrol grubu. `1=2` her zaman yanlış olduğu için gecikme olmamalı.

**Beklenen sonuç:** Anında yanıt (gecikme yok). Adım 6 ile birlikte, uygulamanın tek bir boolean koşulu test edip sonucu çıkarım yapabildiğini (infer edebildiğini) kanıtlar — saldırının temel prensibi budur.

---

## Adım 8 — "administrator" kullanıcısının var olduğunu doğrulama

**Payload:**
```
TrackingId=x'; SELECT CASE WHEN (username='administrator') THEN pg_sleep(10) ELSE pg_sleep(0) END FROM users--
```

**Ne yapıldı / neden:**
Sabit `1=1` yerine, gerçek veritabanı verisine bağlı bir koşul test ediliyor. `users` tablosunda `username='administrator'` olan bir satır varsa koşul TRUE olur ve gecikme yaşanır. `FROM users` eklendi çünkü artık bir tablo sorgulanıyor.

**Beklenen sonuç:** 10 saniyelik gecikme → `administrator` kullanıcısının var olduğu doğrulanır.

---

## Adım 9 — Parola uzunluğunu bulma (manuel, Repeater ile)

**Payload (N'yi 1'den başlayarak artırarak):**
```
TrackingId=x'; SELECT CASE WHEN (username='administrator' AND LENGTH(password)>N) THEN pg_sleep(10) ELSE pg_sleep(0) END FROM users--
```

**Ne yapıldı / neden:**
Koşula `LENGTH(password)>N` kriteri eklendi. `N` değeri Repeater'da elle 1, 2, 3... diye artırılarak gönderiliyor:
- `N` parola uzunluğundan küçükse → koşul TRUE → 10 sn gecikme
- `N` parola uzunluğuna eşit/büyükse → koşul FALSE → gecikme yok

Gecikmenin kaybolduğu ilk `N` değeri parolanın gerçek uzunluğunu verir.

**Sonuç:** Parola uzunluğu **20 karakter** olarak belirlendi.

---

## Adım 10 — Karakter karakter parola çıkarma (Burp Intruder'a geçiş)

20 pozisyon × 36 olası karakter (a-z, 0-9) = 720 istek elle yapılamayacağı için Burp Intruder kullanıldı.

**Payload:**
```
TrackingId=x'; SELECT CASE WHEN (username='administrator' AND SUBSTRING(password,1,1)='§a§') THEN pg_sleep(10) ELSE pg_sleep(0) END FROM users--
```

**Ne yapıldı / neden:**
`SUBSTRING(password, 1, 1)` parolanın 1. pozisyonundan 1 karakter alır ve test edilen değerle karşılaştırır. `§a§` Intruder'ın payload position marker'ı — Intruder bu noktaya sırayla a-z ve 0-9'u yerleştirip her birini dener.

**Kurulum:**
1. İsteği Repeater'dan sağ tık → **Send to Intruder**
2. Cookie değerindeki `a` karakterini seçip **Add §** ile pozisyon işaretle
3. **Payloads** sekmesi → *Simple list* → *Add from list* ile `a-z` ve `0-9` aralıkları eklendi
4. **Resource pool** sekmesi → yeni pool, **Maximum concurrent requests = 1**

**Neden tek thread (concurrency=1)?**
Zaman tabanlı saldırılarda paralel istekler sunucuda aynı anda birden fazla `pg_sleep()` çalıştırabilir ve gecikme süreleri çakışır/karışır. Tek thread, her isteğin kendi gecikmesini net şekilde ölçmeyi sağlar.

**Sonucu okuma:**
Attack bitince **Response received** sütununda çoğu satır küçük bir ms değeri gösterirken, doğru karakteri içeren satır ~10.000 ms civarında görünür. O satırın payload'ı, ilgili pozisyondaki doğru karakterdir.

---

## Adım 11 — Diğer pozisyonları tekrarlama

`SUBSTRING(password, 1, 1)` içindeki offset değeri (`1`) 2, 3, 4... diye değiştirilip Intruder attack her pozisyon için yeniden çalıştırıldı. 20 pozisyon tamamlanana kadar devam edildi → tam parola elde edildi.

---

## Adım 12 — Giriş yapma

Elde edilen 20 karakterlik parolayla tarayıcıda **My account** sayfasından `administrator` olarak giriş yapıldı — lab bu noktada **Solved** oldu.

---

## Özet / Öğrenilenler

- Boolean-based blind SQLi her zaman işe yaramaz — enjeksiyon noktası sayfa içeriğine yansımayabilir (bkz. Adım 3-4).
- Zaman tabanlı (time-based) blind SQLi, sayfa içeriğinden bağımsız olarak çalışır çünkü sonucu **yanıt süresinden** okur.
- `pg_sleep()` PostgreSQL'e özgüdür; farklı DBMS'lerde (`SLEEP()` MySQL, `WAITFOR DELAY` MSSQL gibi) farklı fonksiyonlar kullanılır.
- Stacked queries (`;` ile yeni ifade başlatma) ve `CASE WHEN` birlikte kullanılarak tek bir boolean koşul test edilip sonucu zamanlamadan çıkarım yapılabilir.
- Çok sayıda karakter denemesi gerektiren saldırılarda Burp Intruder + payload position marker (`§...§`) kullanılır; zamanlama hassasiyeti için **concurrency 1** şarttır.
