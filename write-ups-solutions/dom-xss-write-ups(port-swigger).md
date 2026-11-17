# DOM XSS Write-up'ları

## Lab 1: DOM XSS in `document.write` sink using source `location.search`

**Source:** `location.search` (URL'deki `?search=...` parametresi)
**Sink:** `document.write()`
**Context:** HTML attribute içi (`<img src="...">`)

**Zafiyetli kod:**
```javascript
function trackSearch(query) {
    document.write('<img src="/resources/images/tracker.gif?searchTerms='+query+'">');
}
var query = (new URLSearchParams(window.location.search)).get('search');
if(query) {
    trackSearch(query);
}
```

**Veri akışı:** `location.search` → `query` değişkeni → `trackSearch(query)` parametresi → `document.write` içinde string birleştirme ile `src` attribute'una ekleniyor.

**Payload:**
```
"><script>alert(1)</script>
```

**Neden çalışıyor:** `"` ile `src` attribute'unun tırnağı kapatılıyor, `>` ile `<img>` etiketi kapatılıyor. Bu noktadan sonra tarayıcı normal HTML gövdesinde — `<script>alert(1)</script>` ayrı, geçerli bir etiket olarak DOM'a ekleniyor ve çalışıyor.

---

## Lab 2: DOM XSS in `document.write` sink using source `location.search` inside a select element

**Source:** `location.search` (URL'deki `?storeId=...` parametresi)
**Sink:** `document.write()`
**Context:** `<select>` etiketinin içi (`<option>` içeriği)

**Zafiyetli kod:**
```javascript
var stores = ["London","Paris","Milan"];
var store = (new URLSearchParams(window.location.search)).get('storeId');
document.write('<select name="storeId">');
if(store) {
    document.write('<option selected>'+store+'</option>');
}
for(var i=0;i<stores.length;i++) {
    if(stores[i] === store) { continue; }
    document.write('<option>'+stores[i]+'</option>');
}
document.write('</select>');
```

**Veri akışı:** `location.search` → `store` değişkeni → `if(store)` kontrolünden geçiyor (sadece boş olup olmadığına bakıyor, içeriği sorgulamıyor) → `document.write` ile `<option>` içeriğine ekleniyor.

**Neden doğrudan `<script>`/`<img>` yazmak yetmiyor:** `<select>` etiketinin HTML content model'i gereği, `<select>...</select>` arasında sadece `<option>`/`<optgroup>` kabul edilir. Payload hâlâ bu sınırların içindeyse (yani `<select>` kapatılmadan eklenmişse), eklenen etiket normal şekilde parse edilip çalıştırılmaz.

**Payload (önce denenen, çalışan):**
```
"></select><img src=1 onerror=alert(1)>
```

**Payload (sonradan test edilen, bu da çalıştı):**
```
"></select><script>alert(1)</script>
```

Tam URL (img versiyonu):
```
/product?productId=1&storeId="></select><img%20src=1%20onerror=alert(1)>
```

**Neden çalışıyor:**
1. `">` — `<option selected>`'ın içinde düz metin, zararsız
2. `</select>` — kodun kendisi henüz `</select>`'i yazmadan, `<select>`'i erken kapatıyor
3. Bu noktadan sonra tarayıcı artık **normal HTML gövdesinde** — `<select>`'in content model kısıtlaması burada geçerli değil, bu yüzden hem `<img onerror>` hem `<script>` aynı şekilde çalışıyor
4. Kodun kendi `document.write('</select>')` çağrısı, karşılığı olmayan fazladan bir kapanış etiketi olarak kalıyor, zararsız

**Önemli düzeltme/bulgu:** `<img onerror>` kullanmak bu lab için teknik bir zorunluluk değildi — `document.write`, `innerHTML`'in aksine enjekte edilen `<script>` etiketlerini de çalıştırıyor (bunu PortSwigger'ın kendi dokümantasyonu da doğruluyor: "`document.write` sink works with script elements"). `<img onerror>`'ın genelde tercih edilmesinin sebebi, sink ne olursa olsun (hem `document.write` hem `innerHTML`) çalışan "evrensel" bir payload olması — yani alışkanlık/pratiklik meselesi, bu spesifik context'in bir zorunluluğu değil.

**İki labın ortak dersi:** `if` kontrolleri (örn. `if(store)`) genelde güvenlik kontrolü değil, sadece akış kontrolüdür — içeriği sorgulamaz, sadece "boş mu dolu mu" bakar. Asıl zafiyet her zaman sink'te: `document.write`, kendisine gelen string'i içeriğine bakmadan HTML olarak işliyor. Hangi context'te olduğun (attribute içi mi, select içi mi) kullanman gereken kaçış karakterlerini belirliyor; sink'in `<script>`'i kabul edip etmediği ise ayrı bir değişken (`document.write` kabul eder, `innerHTML` etmez).
