# 🚀 All-In-One Recon (Async Network & Web Reconnaissance Engine)

A high-performance, asynchronous reconnaissance framework written in modern Python (`asyncio`, `aiohttp`, `dnspython`, `rich`). Designed for penetration testers, security researchers, and bug bounty hunters to perform unified attack surface mapping without the overhead of heavy external tooling.

---

## ⚡ Key Capabilities & Architecture

* **Engine Architecture (Phase 1):** Non-blocking I/O powered by Python's `asyncio` event loop and `asyncio.Semaphore` concurrency limiting. Zero thread context-switching overhead, low memory footprint.
* **L4 Network & Port Scanner (Phase 2):** Fast asynchronous TCP connect scan with automatic service identification and banner grabbing.
* **L7 Subdomain Discovery (Phase 3):** High-speed asynchronous DNS resolution, wildcard DNS false-positive mitigation, and passive OSINT integration via `crt.sh`.
* **L7 Directory & File Fuzzer (Phase 4):** Concurrent HTTP fuzzing with `aiohttp.ClientSession` connection pooling, recursive discovery, and Soft-404 detection.
* **L7 Virtual Host (VHost) Enumerator (Phase 5):** HTTP `Host` header fuzzing with baseline response profiling and content-length/hash similarity comparison.
* **Unified Reporting (Phase 6):** Rich terminal tables with real-time feedback and exportable structured reports (JSON/HTML/Markdown).

---

## 📁 Project Structure

```text
All-In-One-Recon/
├── recon.py                # Main CLI entry point
├── requirements.txt        # Core dependencies
├── README.md               # Project documentation
├── .gitignore              # Repository exclusions
│
├── core/                   # Engine internals
│   ├── __init__.py
│   ├── config.py           # Centralized configuration dataclass
│   └── logger.py           # Terminal styling and Unicode-safe logging (Rich)
│
├── modules/                # Reconnaissance modules (Phases 2-5)
│   ├── __init__.py
│   ├── port_scanner.py     # (Phase 2: L4 Port Scanner & Banner Grabber)
│   ├── subdomain_scanner.py# (Phase 3: DNS Brute-force & crt.sh)
│   ├── dir_scanner.py      # (Phase 4: HTTP Directory Fuzzer)
│   └── vhost_scanner.py    # (Phase 5: Virtual Host Enumerator)
│
└── wordlists/              # Built-in lightweight test wordlists
    ├── common_subdomains.txt
    ├── common_dirs.txt
    └── common_vhosts.txt
```

---

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/All-In-One-Recon.git
cd All-In-One-Recon

# Install dependencies
pip install -r requirements.txt
```

---

## 💻 Quick Usage

```bash
# Basic port scan (Top 20 ports)
python recon.py -t scanme.nmap.org -p top20

# Scan custom ports with custom concurrency limit
python recon.py -t 192.168.1.1 -p 80,443,8080,8443 -c 200

# Run all enumeration modules (Ports, Subdomains, Dirs, VHosts)
python recon.py -t example.com --all
```

---

## 🛡️ Educational & Defensive Notes

Developed as an in-depth security engineering internship project focusing on raw protocol understanding (TCP handshakes, DNS resolution, HTTP/1.1 pipelining) rather than relying on black-box external utilities.
