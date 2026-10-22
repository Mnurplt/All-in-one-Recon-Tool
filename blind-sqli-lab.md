# Blind SQL Injection with Conditional Responses — Write-up

PortSwigger Web Security Academy'nin "Blind SQL injection with conditional responses" lab'ını çözerken yaşadıklarımı, hem kendi notum olsun hem de benzer bir yerde takılan biri işine yarasın diye yazıyorum. Spoiler: teorik olarak basit görünen bir lab, pratikte beklenmedik yerlerde beni oyaladı.

## Lab ne istiyor

Uygulama bir `TrackingId` çerezi kullanıyor ve bu çerez, arka planda bir SQL sorgusuna doğrudan ekleniyor — ama sorgunun sonucu hiçbir şekilde ekrana yansımıyor, hata mesajı da yok. Tek gördüğünüz şey, çerez değerine bağlı olarak sayfada "Welcome back" mesajının çıkıp çıkmaması. Yani klasik bir blind (kör) SQL injection senaryosu: veriyi doğrudan göremiyorsunuz, sadece evet/hayır tipi bir sinyal alıyorsunuz. Hedef, bu sinyali kullanarak administrator kullanıcısının parolasını karakter karakter çıkarmak.

## Önce enjeksiyonu doğrulamak

İlk iş, enjeksiyon noktasının gerçekten çalışıp çalışmadığını anlamaktı. Burp'te isteği yakalayıp çerezi şuna çevirdim:

```
TrackingId=xyz' AND '1'='1
```

"Welcome back" göründü. Sonra:

```
TrackingId=xyz' AND '1'='2
```

Bu sefer mesaj kayboldu. Bu küçük test aslında çok şey söylüyor: uygulama, sorgunun doğru/yanlış dönmesine göre farklı davranıyor, yani buradan bir sinyal alabileceğim kesinleşti.

## "Var mı yok mu" testleri

Sonraki adım, tabloyu ve kullanıcıyı doğrulamaktı:

```
' AND (SELECT 'a' FROM users LIMIT 1)='a
```

Burada biraz kafam karıştı itiraf etmeliyim — `'a'` ifadesinin bir sütun değil, sabit bir metin olduğunu, yani veritabanından gerçek bir şey okumadığımızı, sadece "bu tabloda satır var mı" diye sorduğumuzu anlamam biraz zaman aldı. Mantığı oturunca gayet basit: alt sorgu bir satır bulursa `'a'` döner, dışarıdaki `='a'` doğru olur; tablo boşsa `NULL` döner, karşılaştırma yanlış olur.

Aynı mantığı `WHERE username='administrator'` ekleyerek kullanıcı varlığına daralttım — koşul yine doğru çıktı, administrator kullanıcısı gerçekten varmış.

## Parola uzunluğunu bulmak

```
' AND (SELECT 'a' FROM users WHERE username='administrator' AND LENGTH(password)>N)='a
```

N'i 1'den başlayıp artırarak (Burp Repeater'da elle) denedim. "Welcome back" mesajı kaybolduğu nokta, parolanın uzunluğunu veriyor — benim durumumda **20 karakter** çıktı.

## Burp Intruder ile asıl mücadele

Burada işler ilginçleşti. 20 karakter × 36 ihtimal (a-z, 0-9) elle yapılamayacak kadar çok istek demek, bu yüzden Burp Intruder'a geçtim. Ama Community sürümü kullandığım için birkaç şeyle uğraştım:

**"Add from list" yok.** Community sürümde bu özellik Pro'ya kilitli, yani a-z ve 0-9'u tek tek, 36 satır halinde elle (ya da toplu paste ile) eklemem gerekti.

**Target URL'si bozuldu.** Bir ara Target alanı yanlışlıkla sadece `https://0` gibi kesilmiş bir hale geldi — muhtemelen kopyala-yapıştır sırasında bir şeyler ters gitti. Sonuç: tüm istekler "Status code: 0" ve "Error" ile döndü, yani Burp sunucuya hiç bağlanamıyordu. Target'ı tam host adıyla düzeltince düzeldi.

**Payload'ı yanlış yere koydum.** Bir noktada pozisyon işaretini (`§...§`) uzunluk testi payload'ına (`LENGTH(password)>100`) koymuşum, karakter çıkarma payload'ına (`SUBSTRING`) değil — bu da anlamsız bir saldırı kurmama yol açtı. Fark edip düzelttim.

**Lab oturumu süresi doldu.** Uzun sürdüğü için bir ara lab tamamen yeni bir URL/TrackingId ile karşıma çıktı, Target'ı ve cookie'yi yeniden ayarlamam gerekti.

Bunları çözünce nihayet doğru kurulum şu hale geldi:

```
TrackingId=xyz' AND (SELECT SUBSTRING(password,1,1) FROM users WHERE username='administrator')='§a§
```

Grep - Match ayarına `Welcome back!` ekledim, payload listesine 36 karakteri yükledim, saldırıyı başlattım. Sonuç tablosunda "Welcome back!" sütununda tik olan satır, o pozisyondaki doğru karakteri veriyordu.

## Karakter karakter, pozisyon pozisyon

`SUBSTRING(password,1,1)` içindeki pozisyon numarasını 1'den 20'ye kadar elle değiştirip, her seferinde saldırıyı tekrar çalıştırdım. İki noktada art arda aynı harf çıktı (4-5. pozisyonda "x, x" ve 16-17. pozisyonda "p, p") ve ilk anda "bir yerde hata yaptım herhalde" diye şüphelendim — ama tekrar test edince ikisinin de gerçekten doğru olduğunu gördüm. Bu beni şaşırtmadı değil, ama "garip görünüyor diye hemen yanlış varsayma" konusunda iyi bir ders oldu.

Bir ara da pozisyon takibini (hangi saldırının kaçıncı karakteri test ettiğini) karıştırdım — tahmine güvenmek yerine her seferinde Positions sekmesindeki gerçek sayıya bakarak teyit ettim, bu da birkaç kez beni yanlış bir sıralamadan kurtardı.

Sonuçta parola ortaya çıktı: **20 karakterlik, küçük harf ve rakamlardan oluşan bir dizi.**

## Giriş ve sonuç

Elde ettiğim parolayla `My account` sayfasından administrator olarak giriş yaptım — lab çözüldü.

## Çıkardığım dersler

- **Teori ile pratik arasındaki boşluk gerçek.** Blind SQLi'nin mantığını (sinyal okuma, binary search, var-mı testleri) zaten iyi anlıyordum, ama Burp Intruder'ı gerçek bir hedefe karşı kurmak, Target/payload/pozisyon gibi "sıradan" ayarlarda bile beklenmedik şekilde takılabileceğimi gösterdi.
- **Şüphelendiğinizde tahmin etmeyin, tekrar test edin.** Art arda aynı karakterin çıkması garip görünebilir ama bu otomatik olarak hata anlamına gelmiyor — gerçek veriyle teyit etmek, varsayımla ilerlemekten her zaman daha güvenilir.
- **Community sürümün kısıtlamaları gerçek bir fark yaratıyor.** "Add from list" gibi küçük bir Pro özelliğinin eksikliği bile, iş akışınızı belirgin şekilde yavaşlatabiliyor — bunu bilmek, ileride hangi noktada Pro'ya geçmenin mantıklı olacağını değerlendirirken işime yarayacak.
- **Pozisyon/durum takibini yazılı tutmak şart.** 20 ayrı saldırı çalıştırırken hangi pozisyonda olduğumu zihnimde tutmaya çalışmak hataya açık bir yöntemdi — bir dahaki sefere her sonucu anında bir yere not ederek ilerleyeceğim.
