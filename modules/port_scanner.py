"""
Asynchronous TCP Port Scanner & Banner Grabber (L4 - Transport Layer).
Performs non-blocking TCP connect scans with active and passive service banner interrogation.
"""
import asyncio
import socket
import time
from dataclasses import dataclass
from typing import List, Optional

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)

from core.config import ReconConfig
from core.logger import console, log_info, log_success, log_warn, log_error, log_status, create_table


# Common well-known port to service name mapping
WELL_KNOWN_SERVICES = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    111: "RPCBind",
    135: "MSRPC",
    139: "NetBIOS",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    587: "SMTP-Submission",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    1521: "Oracle",
    1723: "PPTP",
    2049: "NFS",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    6379: "Redis",
    8000: "HTTP-Alt",
    8080: "HTTP-Proxy",
    8443: "HTTPS-Alt",
    8888: "HTTP-Alt",
    9000: "SonarQube/PHP-FPM",
    9200: "Elasticsearch",
    27017: "MongoDB",
}


@dataclass
class PortScanResult:
    """Stores the scan result for a single port."""
    port: int
    state: str  # 'open', 'closed', 'filtered'
    service: str
    banner: str
    latency_ms: float


async def grab_banner(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int, timeout: float = 1.5) -> str:
    """
    Attempts to retrieve a service banner from an open connection.
    Uses passive listening first, then falls back to an active probe if needed.
    """
    banner = ""
    try:
        # Step 1: Passive grab (services that speak first: SSH, FTP, SMTP, MySQL)
        try:
            data = await asyncio.wait_for(reader.read(512), timeout=timeout)
            if data:
                banner = data.decode(errors="replace").strip()
        except asyncio.TimeoutError:
            pass

        # Step 2: Active probe if still empty (services that wait for client: HTTP, etc.)
        if not banner:
            probe = b"HEAD / HTTP/1.0\r\nUser-Agent: ReconEngine/1.0\r\n\r\n"
            writer.write(probe)
            await asyncio.wait_for(writer.drain(), timeout=1.0)
            
            data = await asyncio.wait_for(reader.read(512), timeout=timeout)
            if data:
                text = data.decode(errors="replace")
                # Look for Server header or HTTP status line
                for line in text.splitlines():
                    if line.lower().startswith("server:") or line.startswith("HTTP/"):
                        banner = line.strip()
                        break
                if not banner:
                    banner = text.splitlines()[0].strip() if text.splitlines() else ""
    except Exception:
        pass
    finally:
        # Sanitize banner: remove extra newlines, keep single line, truncate
        if banner:
            banner = " ".join(banner.split())
            if len(banner) > 60:
                banner = banner[:57] + "..."
    return banner


async def scan_single_port(
    target_ip: str,
    port: int,
    semaphore: asyncio.Semaphore,
    timeout: float,
    banner_timeout: float,
) -> Optional[PortScanResult]:
    """
    Scans a single TCP port using asyncio.open_connection (TCP Connect Scan).
    """
    async with semaphore:
        start_time = time.perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(target_ip, port),
                timeout=timeout,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            
            # Connection succeeded -> Port is OPEN
            service_name = WELL_KNOWN_SERVICES.get(port, "Unknown")
            banner = await grab_banner(reader, writer, port, timeout=banner_timeout)
            
            # If banner indicates SSH / Apache / etc., refine service name
            if "SSH" in banner:
                service_name = "SSH"
            elif "HTTP" in banner or "Apache" in banner or "nginx" in banner or "Cloudflare" in banner:
                service_name = "HTTPS" if port in (443, 8443) else "HTTP"
            elif "FTP" in banner:
                service_name = "FTP"
            elif "MySQL" in banner:
                service_name = "MySQL"
                
            # Safely close the socket
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
                
            return PortScanResult(
                port=port,
                state="open",
                service=service_name,
                banner=banner if banner else "-",
                latency_ms=round(latency_ms, 2),
            )
        except (asyncio.TimeoutError, OSError):
            # Port is closed or filtered
            return None


async def resolve_target(target: str) -> Optional[str]:
    """Resolves target hostname to IPv4 address."""
    try:
        loop = asyncio.get_running_loop()
        addr_info = await loop.getaddrinfo(target, None, family=socket.AF_INET)
        if addr_info:
            return addr_info[0][4][0]
    except Exception as e:
        log_error(f"DNS Resolution failed for {target}: {e}")
    return None


async def run_port_scan(config: ReconConfig) -> List[PortScanResult]:
    """
    Orchestrates the asynchronous port scan against the target.
    """
    log_status("Port Scanning & Service Enumeration (L4)")
    
    # Step 1: Resolve Target to IP
    log_info(f"Resolving hostname: [bold white]{config.target}[/bold white]...")
    target_ip = await resolve_target(config.target)
    if not target_ip:
        log_error(f"Could not resolve target '{config.target}'. Aborting port scan.")
        return []
        
    config.target_ip = target_ip
    log_success(f"Resolved target to IP: [bold yellow]{target_ip}[/bold yellow]")
    log_info(f"Starting scan of [bold cyan]{len(config.ports)}[/bold cyan] ports (Concurrency: {config.concurrency_limit})...")

    # Step 2: Initialize Semaphore and Tasks
    semaphore = asyncio.Semaphore(config.concurrency_limit)
    open_ports: List[PortScanResult] = []

    # Progress bar setup
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style="cyan", finished_style="green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Scanning TCP ports...", total=len(config.ports))
        
        async def worker(port: int):
            result = await scan_single_port(
                target_ip=target_ip,
                port=port,
                semaphore=semaphore,
                timeout=config.timeout,
                banner_timeout=config.banner_timeout,
            )
            progress.advance(task)
            if result and result.state == "open":
                open_ports.append(result)
                log_success(f"Port [bold green]{result.port}/TCP[/bold green] is OPEN ({result.service}) {f'-> [dim]{result.banner}[/dim]' if result.banner != '-' else ''}")

        # Fire all tasks concurrently
        await asyncio.gather(*(worker(port) for port in config.ports))

    # Step 3: Display Summary Table
    open_ports.sort(key=lambda r: r.port)
    
    table = create_table(
        title=f"Open Ports on {config.target} ({target_ip})",
        columns=["PORT", "STATE", "SERVICE", "BANNER / IDENTIFIER", "LATENCY"],
    )
    
    for r in open_ports:
        table.add_row(
            f"[bold green]{r.port}/tcp[/bold green]",
            f"[green]{r.state}[/green]",
            f"[cyan]{r.service}[/cyan]",
            f"[dim]{r.banner}[/dim]",
            f"{r.latency_ms} ms",
        )
        
    console.print()
    console.print(table)
    log_info(f"Scan complete: Discovered [bold green]{len(open_ports)}[/bold green] open ports out of {len(config.ports)} scanned.\n")
    
    return open_ports
