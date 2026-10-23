"""
Asynchronous Subdomain Enumeration Module (L7 - DNS & OSINT Layer).
Features:
- Asynchronous DNS Brute-force via dnspython
- Wildcard DNS Detection and False-Positive Filtering
- Passive OSINT Certificate Transparency harvesting (crt.sh)
- Automatic CNAME and IPv4 resolution
"""
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

import aiohttp
import dns.asyncresolver
import dns.resolver

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)

from core.config import ReconConfig
from core.logger import console, log_info, log_success, log_warn, log_error, log_status, create_table


@dataclass
class SubdomainResult:
    """Stores the enumeration result for a single discovered subdomain."""
    subdomain: str
    ips: List[str] = field(default_factory=list)
    cnames: List[str] = field(default_factory=list)
    source: str = "DNS Brute-force"  # 'DNS Brute-force', 'crt.sh (OSINT)', or 'Both'
    latency_ms: float = 0.0


def create_async_resolver(nameservers: List[str], timeout: float = 2.0) -> dns.asyncresolver.Resolver:
    """Configures a custom high-performance async DNS resolver."""
    resolver = dns.asyncresolver.Resolver()
    resolver.nameservers = nameservers
    resolver.timeout = timeout
    resolver.lifetime = timeout
    return resolver


async def detect_wildcard(target: str, resolver: dns.asyncresolver.Resolver) -> Set[str]:
    """
    Detects whether the target domain utilizes Wildcard DNS (*.target.com).
    Sends a query for a non-existent UUID subdomain.
    If resolved, returns the set of wildcard IP addresses to avoid false positives.
    """
    test_subdomain = f"wildcard-test-{uuid.uuid4().hex[:10]}.{target}"
    wildcard_ips = set()
    try:
        answers = await resolver.resolve(test_subdomain, "A")
        for rdata in answers:
            wildcard_ips.add(rdata.to_text())
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.LifetimeTimeout, Exception):
        pass

    return wildcard_ips


async def fetch_crtsh_subdomains(target: str, timeout: float = 8.0) -> Set[str]:
    """
    Harvests subdomains passively via Certificate Transparency logs on crt.sh.
    Requires no packets to be sent directly to the target.
    """
    url = f"https://crt.sh/?q=%.{target}&output=json"
    discovered = set()
    headers = {"User-Agent": "AllInOneRecon/1.0 (+https://github.com/Mnurplt/All-in-one-Recon-Tool)"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    if isinstance(data, list):
                        for entry in data:
                            name_val = entry.get("name_value", "")
                            # An entry may contain multiple newline-separated subdomains or wildcards
                            for sub in name_val.split("\n"):
                                sub = sub.strip().lower()
                                if sub.startswith("*."):
                                    sub = sub[2:]
                                if sub.endswith(f".{target}") or sub == target:
                                    discovered.add(sub)
    except Exception as e:
        log_warn(f"crt.sh passive OSINT check could not complete ({type(e).__name__}). Continuing with DNS brute-force.")

    return discovered


async def resolve_single_subdomain(
    subdomain: str,
    resolver: dns.asyncresolver.Resolver,
    semaphore: asyncio.Semaphore,
    wildcard_ips: Set[str],
    source: str = "DNS Brute-force",
) -> Optional[SubdomainResult]:
    """
    Asynchronously resolves a single subdomain for A and CNAME records.
    Filters out results that resolve exclusively to wildcard IP addresses.
    """
    async with semaphore:
        start_time = time.perf_counter()
        ips = []
        cnames = []

        # Step 1: Query CNAME (Canonical Name / Alias)
        try:
            cname_answers = await resolver.resolve(subdomain, "CNAME")
            for rdata in cname_answers:
                cnames.append(rdata.target.to_text().rstrip("."))
        except Exception:
            pass

        # Step 2: Query A Records (IPv4)
        try:
            a_answers = await resolver.resolve(subdomain, "A")
            for rdata in a_answers:
                ips.append(rdata.to_text())
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.LifetimeTimeout, Exception):
            pass

        # If no IPs were found, subdomain is not live
        if not ips:
            return None

        # Wildcard filter check:
        # If the subdomain was ONLY guessed via brute-force and matches the wildcard IP, discard as false positive.
        # However, if it was found via crt.sh (verified SSL certificate history), keep it even if it shares the host IP!
        if wildcard_ips and set(ips).issubset(wildcard_ips):
            if source == "DNS Brute-force":
                return None
            else:
                source += " (Shares Wildcard IP)"


        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return SubdomainResult(
            subdomain=subdomain,
            ips=sorted(ips),
            cnames=cnames,
            source=source,
            latency_ms=round(latency_ms, 2),
        )


def load_subdomain_wordlist(wordlist_path: Path) -> List[str]:
    """Loads wordlist entries from disk, cleaning empty lines."""
    if not wordlist_path.exists():
        log_warn(f"Wordlist not found at {wordlist_path}. Using fallback list.")
        return ["www", "mail", "api", "dev", "test", "admin", "vpn", "staging", "app", "portal"]
    
    with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip().lower() for line in f if line.strip() and not line.startswith("#")]


async def run_subdomain_scan(config: ReconConfig) -> List[SubdomainResult]:
    """
    Orchestrates the hybrid (Passive OSINT + Active DNS Brute-force) subdomain enumeration.
    """
    log_status("Subdomain Enumeration (L7 - DNS & OSINT)")
    target = config.target.lower()
    
    # Step 1: Configure Custom Async Resolver
    resolver = create_async_resolver(config.dns_servers, timeout=config.timeout)
    log_info(f"Target Domain: [bold white]{target}[/bold white]")
    log_info(f"DNS Servers: [bold cyan]{', '.join(config.dns_servers)}[/bold cyan]")

    # Step 2: Wildcard DNS Detection
    log_info("Testing for Wildcard DNS configuration...")
    wildcard_ips = await detect_wildcard(target, resolver)
    if wildcard_ips:
        log_warn(f"Wildcard DNS DETECTED! *. {target} resolves to: [bold yellow]{', '.join(wildcard_ips)}[/bold yellow]")
        log_warn("False-positive filter active: Any result mapping exclusively to these IPs will be discarded.")
    else:
        log_success("Wildcard DNS is NOT active. DNS resolution results are distinct.")

    # Step 3: Passive OSINT via crt.sh
    passive_subs = set()
    if config.enable_crtsh:
        log_info("Harvesting SSL/TLS Certificate Transparency logs from [bold cyan]crt.sh[/bold cyan]...")
        passive_subs = await fetch_crtsh_subdomains(target)
        if passive_subs:
            log_success(f"Discovered [bold green]{len(passive_subs)}[/bold green] candidate subdomains from crt.sh (Passive OSINT).")
        else:
            log_info("No candidate subdomains retrieved from crt.sh.")

    # Step 4: Prepare Active Wordlist Targets
    words = load_subdomain_wordlist(config.subdomain_wordlist)
    active_candidates = {f"{word}.{target}" for word in words}
    log_info(f"Loaded [bold cyan]{len(active_candidates)}[/bold cyan] words from wordlist: [dim]{config.subdomain_wordlist.name}[/dim]")

    # Step 5: Merge Candidate Pools with Source Tracking
    candidate_sources = {}
    for sub in passive_subs:
        candidate_sources[sub] = "crt.sh (OSINT)"
    for sub in active_candidates:
        if sub in candidate_sources:
            candidate_sources[sub] = "Both (Passive + Brute)"
        else:
            candidate_sources[sub] = "DNS Brute-force"

    all_candidates = list(candidate_sources.keys())
    log_info(f"Total unique subdomains to interrogate: [bold white]{len(all_candidates)}[/bold white]")

    # Step 6: Asynchronous Interrogation with Semaphore
    semaphore = asyncio.Semaphore(config.concurrency_limit)
    discovered_results: List[SubdomainResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style="cyan", finished_style="green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Resolving subdomains...", total=len(all_candidates))

        async def worker(sub: str):
            source = candidate_sources[sub]
            result = await resolve_single_subdomain(
                subdomain=sub,
                resolver=resolver,
                semaphore=semaphore,
                wildcard_ips=wildcard_ips,
                source=source,
            )
            progress.advance(task)
            if result:
                discovered_results.append(result)
                log_success(f"Discovered: [bold green]{result.subdomain}[/bold green] -> [yellow]{', '.join(result.ips)}[/yellow] [dim]({result.source})[/dim]")

        await asyncio.gather(*(worker(sub) for sub in all_candidates))

    # Step 7: Display Structured Table
    discovered_results.sort(key=lambda r: r.subdomain)

    table = create_table(
        title=f"Subdomains Discovered for {target} ({len(discovered_results)} alive)",
        columns=["SUBDOMAIN", "IPV4 ADDRESSES", "CNAME / ALIAS", "DISCOVERY SOURCE", "LATENCY"],
    )

    for r in discovered_results:
        cname_display = r.cnames[0] if r.cnames else "-"
        table.add_row(
            f"[bold green]{r.subdomain}[/bold green]",
            ", ".join(r.ips),
            f"[dim]{cname_display}[/dim]",
            f"[cyan]{r.source}[/cyan]",
            f"{r.latency_ms} ms",
        )

    console.print()
    console.print(table)
    log_info(f"Subdomain enumeration complete: [bold green]{len(discovered_results)}[/bold green] live subdomains verified.\n")

    return discovered_results
