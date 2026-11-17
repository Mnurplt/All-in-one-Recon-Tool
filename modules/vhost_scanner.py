"""
Asynchronous virtual host enumerator.
This probes candidate Host headers against the same HTTP endpoint and highlights responses
that differ from the baseline request.
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import aiohttp

from core.config import ReconConfig
from core.logger import create_table, console, log_info, log_status, log_success, log_warn


@dataclass
class VhostResult:
    """Stores a virtual-host response for a single candidate host."""
    host: str
    status_code: int
    length: int
    note: str


def load_vhost_wordlist(wordlist_path: Path) -> List[str]:
    """Load vhost candidates from a wordlist or fallback to a compact built-in list."""
    defaults = [
        "localhost", "admin", "internal", "dev", "development", "stage", "staging", "test",
        "api", "api-internal", "corp", "intra", "intranet", "backend", "portal", "private",
        "management", "billing", "auth", "mail", "webmail", "cpanel", "jenkins", "grafana",
        "monitor",
    ]

    if not wordlist_path.exists():
        return defaults

    with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as handle:
        values = (line.strip().lower() for line in handle)
        cleaned = [value for value in values if value and not value.startswith("#")]
    return cleaned or defaults


async def fetch_baseline(session: aiohttp.ClientSession, target: str, user_agent: str) -> tuple[int, int, str]:
    """Fetch the default response for the target host so vhost responses can be compared against it."""
    url = f"http://{target}/"
    async with session.get(
        url,
        headers={"Host": target, "User-Agent": user_agent, "Accept": "text/html,*/*"},
        timeout=aiohttp.ClientTimeout(total=3.0),
        allow_redirects=True,
    ) as response:
        body = await response.text(errors="ignore")
        return response.status, len(body.encode("utf-8", errors="ignore")), body


async def probe_vhost(
    session: aiohttp.ClientSession,
    target: str,
    candidate: str,
    baseline_status: int,
    baseline_length: int,
    baseline_body: str,
    timeout: float,
    user_agent: str,
) -> Optional[VhostResult]:
    """Compare a virtual-host response with the baseline response."""
    host = f"{candidate}.{target}" if candidate != target else target
    url = f"http://{target}/"

    try:
        async with session.get(
            url,
            headers={"Host": host, "User-Agent": user_agent, "Accept": "text/html,*/*"},
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
        ) as response:
            body = await response.text(errors="ignore")
            status = response.status
            length = len(body.encode("utf-8", errors="ignore"))

            if status in {200, 301, 302, 307, 308, 401, 403} and (
                status != baseline_status or length != baseline_length or body.lower() != baseline_body.lower()
            ):
                note = "different response profile"
                if status != baseline_status:
                    note = f"status changed ({baseline_status} -> {status})"
                elif length != baseline_length:
                    note = f"length changed ({baseline_length} -> {length})"
                return VhostResult(host=host, status_code=status, length=length, note=note)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return None

    return None


async def run_vhost_scan(config: ReconConfig) -> List[VhostResult]:
    """Enumerate possible virtual hosts for the target by varying the Host header."""
    log_status("Virtual Host Enumeration (L7 - Reverse Proxy)")
    log_info(f"Target: [bold white]{config.target}[/bold white]")

    words = load_vhost_wordlist(config.vhost_wordlist)
    seen = set()
    candidates = []
    for word in words:
        cleaned = word.strip().lower().strip(".")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        candidates.append(cleaned)

    async with aiohttp.ClientSession() as session:
        baseline_status, baseline_length, baseline_body = await fetch_baseline(session, config.target, config.user_agent)
        semaphore = asyncio.Semaphore(config.concurrency_limit)
        results: List[VhostResult] = []

        async def worker(candidate: str):
            async with semaphore:
                result = await probe_vhost(
                    session=session,
                    target=config.target,
                    candidate=candidate,
                    baseline_status=baseline_status,
                    baseline_length=baseline_length,
                    baseline_body=baseline_body,
                    timeout=config.timeout,
                    user_agent=config.user_agent,
                )
                if result:
                    results.append(result)
                    log_success(f"Possible VHost: [bold green]{result.host}[/bold green] [dim]HTTP {result.status_code} ({result.note})[/dim]")

        await asyncio.gather(*(worker(candidate) for candidate in candidates))

    results.sort(key=lambda item: item.host)

    table = create_table(
        title=f"Virtual Hosts for {config.target}",
        columns=["HOST", "STATUS", "LENGTH", "NOTE"],
    )
    for item in results:
        table.add_row(
            f"[bold green]{item.host}[/bold green]",
            f"[cyan]{item.status_code}[/cyan]",
            f"{item.length} bytes",
            f"[dim]{item.note}[/dim]",
        )

    console.print()
    console.print(table)
    log_info(f"VHost scan complete: [bold green]{len(results)}[/bold green] candidate virtual hosts discovered.\n")
    return results
