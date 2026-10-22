"""
Core configuration settings for All-In-One Recon.
Defines default timeouts, concurrency limits, ports, and wordlist paths.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent
WORDLISTS_DIR = BASE_DIR / "wordlists"


@dataclass
class ReconConfig:
    """Central configuration class passed to scan modules."""
    
    # Target specification
    target: str = ""
    target_ip: str = ""
    
    # Concurrency and performance controls
    # Semaphore controls how many active socket/HTTP connections exist simultaneously
    concurrency_limit: int = 100
    timeout: float = 3.0  # seconds
    
    # Network scan settings
    ports: List[int] = field(default_factory=lambda: [
        21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995,
        1723, 3306, 3389, 5900, 8000, 8080, 8443, 8888, 9000
    ])
    banner_timeout: float = 2.0
    
    # Subdomain scan settings
    dns_servers: List[str] = field(default_factory=lambda: [
        "1.1.1.1", "8.8.8.8", "9.9.9.9"
    ])
    subdomain_wordlist: Path = WORDLISTS_DIR / "common_subdomains.txt"
    enable_crtsh: bool = True
    
    # Directory scan settings
    dir_wordlist: Path = WORDLISTS_DIR / "common_dirs.txt"
    extensions: List[str] = field(default_factory=lambda: ["", ".html", ".php", ".txt", ".json", ".bak"])
    user_agent: str = "AllInOneRecon/1.0 (+https://github.com/internship-project)"
    status_codes_to_show: List[int] = field(default_factory=lambda: [
        200, 204, 301, 302, 307, 308, 401, 403, 405, 500
    ])
    
    # VHost scan settings
    vhost_wordlist: Path = WORDLISTS_DIR / "common_vhosts.txt"
    vhost_similarity_threshold: float = 0.95
