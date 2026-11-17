"""
Asynchronous directory / file discovery module.
Minimal but effective HTTP fuzzing with concurrency control and soft-404 filtering.
"""
import asyncio
import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

import aiohttp

from core.config import ReconConfig
from core.logger import create_table, console, log_info, log_success, log_warn, log_status


@dataclass
class DirectoryResult:
    """Stores a single discovered HTTP path."""
    path: str
    status_code: int
    length: int
    title: str


def load_dir_wordlist(wordlist_path: Path) -> List[str]:
    """Load directory candidates from disk or fallback to a compact builtin list."""
    defaults = [
        "admin", "administrator", "login", "logout", "dashboard", "api", "api/v1", "api/v2",
        "config", "test", "backup", "backups", "dev", "development", "staging", "git", ".git",
        ".git/HEAD", ".env", ".env.example", ".gitignore", ".htaccess", "robots.txt",
        "sitemap.xml", "uploads", "upload", "files", "images", "assets", "static", "js", "css",
        "include", "includes", "app", "server-status", "swagger", "swagger-ui.html", "docs",
        "openapi.json", "graphql", "console", "phpinfo", "phpinfo.php", "info.php", "temp", "tmp",
        "database", "db", "dump.sql", "wp-admin", "wp-login.php", "wp-content", "secret", "private",
        "internal", "metrics", "health", "healthcheck", "actuator", "actuator/health", "actuator/env",
        "actuator/beans"
    ]

    if not wordlist_path.exists():
        return defaults

    with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as handle:
        words = (line.strip() for line in handle)
        cleaned = [word for word in words if word and not word.startswith("#")]
    return cleaned or defaults


async def probe_directory(
    session: aiohttp.ClientSession,
    target: str,
    candidate: str,
    timeout: float,
    user_agent: str,
    extensions: List[str],
) -> Optional[DirectoryResult]:
    """Probe a single path and return it when it appears valid."""
    cleaned = candidate.strip("/")
    if not cleaned:
        return None

    urls = [f"http://{target}/{cleaned}"]
    for ext in extensions:
        if not ext:
            continue
        urls.append(f"http://{target}/{cleaned}{ext}")

    for url in urls:
        try:
            async with session.get(
                url,
                headers={"User-Agent": user_agent, "Accept": "text/html,application/json,*/*"},
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=True,
            ) as response:
                text = await response.text(errors="ignore")
                body = text.strip()
                if response.status == 404:
                    continue

                if response.status not in {200, 204, 301, 302, 307, 308, 401, 403, 405, 500}:
                    continue

                if response.status == 200:
                    lower = body.lower()
                    if not body:
                        continue
                    if "404 not found" in lower or "page not found" in lower:
                        continue
                    if "apache" in lower and "not found" in lower and len(body) < 200:
                        continue

                title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
                title = html.unescape(title_match.group(1)).strip() if title_match else "-"
                return DirectoryResult(
                    path=url.replace(f"http://{target}/", "/", 1),
                    status_code=response.status,
                    length=len(body.encode("utf-8", errors="ignore")),
                    title=title[:80],
                )
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            continue

    return None


async def run_dir_scan(config: ReconConfig) -> List[DirectoryResult]:
    """Run a lightweight directory fuzzing pass against the target."""
    log_status("Directory Fuzzing (L7 - HTTP)")
    log_info(f"Target: [bold white]{config.target}[/bold white]")

    words = load_dir_wordlist(config.dir_wordlist)
    if not words:
        words = ["admin", "login", "api", "docs", "static"]

    candidates = []
    seen: Set[str] = set()
    for entry in words:
        cleaned = entry.strip().strip("/")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        candidates.append(cleaned)

    for ext in config.extensions:
        if not ext:
            continue
        for word in list(candidates):
            suffix = f"{word}{ext}"
            if suffix not in seen:
                seen.add(suffix)
                candidates.append(suffix)

    semaphore = asyncio.Semaphore(config.concurrency_limit)
    results: List[DirectoryResult] = []

    async with aiohttp.ClientSession() as session:
        async def worker(candidate: str):
            async with semaphore:
                result = await probe_directory(
                    session=session,
                    target=config.target,
                    candidate=candidate,
                    timeout=config.timeout,
                    user_agent=config.user_agent,
                    extensions=[],
                )
                if result:
                    results.append(result)
                    log_success(f"Discovered: [bold green]{result.path}[/bold green] [dim]HTTP {result.status_code}[/dim]")

        await asyncio.gather(*(worker(c) for c in candidates))

    results.sort(key=lambda item: (item.status_code, item.path))

    table = create_table(
        title=f"HTTP Paths Discovered for {config.target}",
        columns=["PATH", "STATUS", "SIZE", "TITLE"],
    )
    for item in results:
        table.add_row(
            f"[bold green]{item.path}[/bold green]",
            f"[cyan]{item.status_code}[/cyan]",
            f"{item.length} bytes",
            f"[dim]{item.title}[/dim]",
        )

    console.print()
    console.print(table)
    log_info(f"Directory scan complete: [bold green]{len(results)}[/bold green] candidate paths discovered.\n")
    return results
