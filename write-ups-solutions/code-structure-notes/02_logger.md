---
tags: [python, siber-guvenlik, recon, ders-notu, rich]
kaynak: logger.py
---

# 02 - logger.py (Renkli Terminal Çıktısı)

> **Bu dosya ne yapar?** Ekrana renkli ve standart biçimli mesaj yazan küçük fonksiyonlar sunar: `log_info`, `log_success`, `log_warn`, `log_error`, `log_status`, `create_table`, `print_banner`.
> Ön bilgi: [[00_proje_temelleri]]
> Diğer notlar: [[01_config]] · [[03_port_scanner]] · [[04_subdomain_scanner]] · [[05_recon_cli]]

---

## 1. Kütüphaneler

| Kütüphane | Standart mı? | Ne için |
|---|---|---|
| `sys` | Evet | Platform bilgisi, ekran çıktısı ayarı |
| `typing.Optional` | Evet | **Kullanılmıyor** (gereksiz import, silinebilir) |
| `rich` | **Hayır** → `pip install rich` | Renk, tablo, panel, ilerleme çubuğu |

### Rich neden var?
`print()` düz, renksiz yazar. Rich ile:
```python
from rich.console import Console
console = Console()
console.print("[bold red]Hata![/bold red] Dosya bulunamadı")
```
çıktıda "Hata!" kırmızı ve kalın görünür.

---

## 2. `sys` modülü

### 2.1 `sys.platform`
Kodun hangi işletim sisteminde çalıştığını söyler.
```python
import sys
print(sys.platform)
# Windows → win32     Linux → linux     macOS → darwin
```
Kodda: `if sys.platform == "win32":` → "Eğer Windows isem..."

### 2.2 `sys.stdout.reconfigure(...)`
- `sys.stdout` → programın ekrana yazdığı akış (normal `print` buraya yazar).
- `sys.stderr` → hata mesajı akışı.
- `.reconfigure(encoding="utf-8", errors="replace")` → bu akışın **karakter kodlamasını** değiştirir.

**Neden gerekli? (Gerçek hayat sorunu)**
Türkçe Windows terminali eski bir kodlama olan **CP1254** kullanır. `━` veya `🔍` gibi karakterler bu kodlamada yoktur. Bunları `print` etmeye çalışınca:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2501'
```
ile program çöker. Çözüm: çıktıyı UTF-8'e çevirmek.

| Parametre | Anlamı |
|---|---|
| `encoding="utf-8"` | UTF-8 kullan (her karakteri destekler) |
| `errors="replace"` | Yine de yazılamayan karakter olursa `?` bas, **çökme** |

```python
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass            # olmazsa sorun değil, devam et
```
`try/except` neden var? Çıktı bir dosyaya yönlendirilmişse `reconfigure` bulunmayabilir. Bu küçük özellik yüzünden tüm program çökmesin.

> Bu kod modülün en üstünde olduğu için dosya **ilk import edildiği anda** bir kez çalışır.

---

## 3. `rich.console`: `Console`

```python
console = Console(highlight=False)
```

- `Console(...)` → Rich'in yazdırma nesnesi. `print` yerine `console.print` kullanılır.
- `highlight=False` → Rich normalde sayı, IP, URL gibi şeyleri **otomatik renklendirir**. Bunu kapatırız; sadece bizim yazdığımız renkler görünsün.

```python
console.print("[bold green]Başarılı[/bold green]")
console.print("[bold cyan]Port 80[/bold cyan] açık")
```

### Rich markup rehberi
`[stil]...[/stil]` ile metin süslenir:

| Yazım | Görünüm |
|---|---|
| `[bold]metin[/bold]` | Kalın |
| `[red]metin[/red]` | Kırmızı |
| `[bold cyan]metin[/bold cyan]` | Kalın + turkuaz |
| `[dim]metin[/dim]` | Soluk |
| `[bold white]metin[/bold white]` | Kalın beyaz |

Kullanılan renkler: `blue`, `green`, `yellow`, `red`, `cyan`, `magenta`, `white`, `bright_blue`.

> **Bilmeyince şaşırtan detay:** Rich, köşeli parantez içi `a-z`, `#`, `/`, `@` ile başlıyorsa etiket sayar. Koddaki `[*]`, `[+]`, `[!]`, `[-]` bu şartı sağlamadığı için **olduğu gibi** yazdırılır.

> **Güvenlik/hata notu:** Hedeften gelen metin (banner, hata mesajı) `[bold]` gibi bir şey içerirse Rich bunu etiket sanabilir. Dış kaynaklı metin için `from rich.markup import escape; escape(metin)` kullanılabilir.

### Neden `console` nesnesi dosyanın en üstünde, fonksiyonların dışında?
```python
console = Console(highlight=False)     # modül seviyesi: dosya import edilince BİR KERE oluşur
```
Python bir modülü bir kez yükler. `port_scanner.py` ve `subdomain_scanner.py` aynı satırı yazsa bile **aynı `console` nesnesini** alır. Bu önemli, çünkü ilerleme çubuğu (`Progress(console=console)`) ile `log_success` mesajları aynı konsoldan basılmazsa ekran karışır.

---

## 4. `rich.table`: `Table`

### 4.1 Mini örnek
```python
from rich.table import Table
from rich.console import Console

tablo = Table(title="Açık Portlar")
tablo.add_column("PORT")
tablo.add_column("SERVİS")
tablo.add_row("22/tcp", "SSH")
tablo.add_row("80/tcp", "HTTP")
Console().print(tablo)
```
Çıktı (yaklaşık):
```
   Açık Portlar
┏━━━━━━━━┳━━━━━━━━━┓
┃ PORT   ┃ SERVİS  ┃
┡━━━━━━━━╇━━━━━━━━━┩
│ 22/tcp │ SSH     │
│ 80/tcp │ HTTP    │
└────────┴─────────┘
```

### 4.2 Kullanılan parametreler
| Parametre | Anlamı |
|---|---|
| `title=` | Tablo başlığı |
| `show_header=True` | Sütun başlıkları görünsün |
| `header_style="bold cyan"` | Başlık satırı stili |
| `border_style="dim"` | Çerçeve soluk renkte |

### 4.3 Metotlar
| Metot | Görev |
|---|---|
| `table.add_column("ADI")` | Sütun ekler |
| `table.add_row(a, b, c)` | Satır ekler. Her argüman bir hücre; sütun sayısıyla **aynı sayıda** olmalı |

---

## 5. `rich.panel` ve `rich.text`

### 5.1 `Panel`: çerçeveli kutu
```python
from rich.panel import Panel
console.print(Panel("Merhaba", subtitle="alt yazı", border_style="bright_blue", padding=(0, 2)))
```
| Parametre | Anlamı |
|---|---|
| ilk parametre | Kutunun içeriği |
| `subtitle=` | Çerçevenin alt kenarında yazı |
| `border_style=` | Çerçeve rengi |
| `padding=(0, 2)` | İç boşluk: (üst-alt, sol-sağ) |

### 5.2 `Text.from_markup(...)`
Markup içeren string'i Rich'in `Text` nesnesine çevirir:
```python
from rich.text import Text
Text.from_markup("[bold cyan]Selam[/bold cyan]")
```
Panel içine konan metinde renklerin doğru çıkması için kullanılır.

### 5.3 Banner'daki `\\`
Python string'inde `\` özel karakterdir (`\n` yeni satır gibi). Gerçek bir `\` yazmak için `\\` yazılır:
```python
print("a\\b")     # a\b
```
ASCII art'taki `/ _ \\` bu yüzden iki ters bölü içerir.

---

## 6. Dosyadaki fonksiyonlar

Hepsi aynı kalıp: **mesaj al → renkli yazdır.**

```python
def log_success(message: str) -> None:
    console.print(f"[bold green][+][/bold green] [green]{message}[/green]")
```
- `message: str` → parametre tipi metin.
- `-> None` → "bir şey döndürmez" (sadece ekrana yazar).

| Fonksiyon | Ekran görünümü | Ne zaman |
|---|---|---|
| `log_info("...")` | `[*]` mavi | Bilgi, ilerleme |
| `log_success("...")` | `[+]` yeşil | Bulgu / başarı |
| `log_warn("...")` | `[!]` sarı | Uyarı |
| `log_error("...")` | `[-]` kırmızı | Hata |
| `log_status("Port Scan")` | `━━━ 🔍 PORT SCAN ━━━` | Bölüm başlığı (`.upper()` BÜYÜK HARF yapar) |
| `create_table(title, columns)` | boş tablo döner | Tablo oluşturma yardımcı |
| `print_banner()` | ASCII art panel | Program açılışı |

`create_table` içindeki döngü:
```python
for col in columns:          # columns = ["PORT", "STATE", ...]
    table.add_column(col)    # her başlık için sütun aç
```

Güvenlik araçlarında yaygın önek gelenekleri: `[*]` bilgi, `[+]` başarı, `[-]` hata, `[!]` uyarı (Metasploit tarzı).

---

## 7. Mimari: neden bu fonksiyonlar var?

Fonksiyonlar olmasaydı `console.print("[bold green][+][/bold green] ...")` satırı **her yerde** tekrar yazılırdı. Yarın "yeşil yerine turkuaz olsun" dersen onlarca satırı değiştirirsin. Şimdi tek yerde değiştirirsin. Buna **DRY** (Don't Repeat Yourself) prensibi denir.

Bu "yardımcı fonksiyon" yaklaşımı tüm modüllerde kullanılır:
```python
from core.logger import console, log_info, log_success, create_table
```

---

## 8. Dikkat edilecek noktalar
- `Optional` import'u kullanılmıyor.
- Dış kaynaklı metinler için `rich.markup.escape()` düşünülebilir.
- `log_status` içindeki 🔍 emojisi eski terminallerde bozuk görünebilir. UTF-8 düzeltmesi bu yüzden eklenmiş.

## 9. Tekrar soruları
1. `sys.platform == "win32"` neden kontrol ediliyor?
2. `errors="replace"` ne yapar?
3. `console` neden fonksiyon içinde değil de dosya başında tanımlanmış?
4. `[+]` Rich'te neden etiket sayılmaz?
5. `Table`'a satır eklerken hücre sayısı ne olmalı?
