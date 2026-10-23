#!/usr/bin/env python3
"""
All-In-One Recon Framework
Author: Nur & AI Co-Engineer
Purpose: Asynchronous Network & Web Attack Surface Discovery
"""
import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

from core import (
    ReconConfig,
    console,
    print_banner,
    log_info,
    log_success,
    log_warn,
    log_error,
    log_status,
)
from modules import run_port_scan, run_subdomain_scan


def parse_ports(port_arg: str) -> list[int]:
    """
    Parses port arguments supporting:
    - Comma-separated: '80,443,8080'
    - Range: '1-100'
    - Presets: 'top20', 'top100'
    """
    if not port_arg:
        return []
        
    port_arg = port_arg.strip().lower()
    
    top_20 = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 8080, 8443]
    top_100 = top_20 + [
        7, 9, 13, 26, 37, 79, 88, 106, 113, 119, 144, 179, 199, 389, 427, 465, 513, 514, 515, 543, 548, 554,
        587, 631, 646, 873, 990, 1025, 1026, 1027, 1028, 1029, 1110, 1433, 1720, 2000, 2049, 2121, 2717,
        3000, 3128, 3268, 3986, 4000, 4899, 5000, 5009, 5051, 5060, 5101, 5190, 5357, 5432, 5631, 5666,
        5800, 5900, 6000, 6001, 6646, 7070, 8000, 8008, 8009, 8081, 8443, 8888, 9000, 9100, 9999, 10000,
        32768, 49152, 49153, 49154, 49155, 49156, 49157
    ]
    
    if port_arg == "top20":
        return top_20
    elif port_arg == "top100":
        return sorted(list(set(top_100)))
        
    ports = set()
    for part in port_arg.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            ports.update(range(int(start), int(end) + 1))
        elif part.isdigit():
            ports.add(int(part))
            
    return sorted(list(ports))


def build_cli_parser() -> argparse.ArgumentParser:
    """Builds the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="recon.py",
        description="All-In-One Network & Web Reconnaissance Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "-t", "--target",
        type=str,
        required=True,
        help="Target domain or IP address (e.g. example.com or 192.168.1.50)",
    )
    
    # Scan modes
    mode_group = parser.add_argument_group("Scan Modes (Choose one or more)")
    mode_group.add_argument(
        "-a", "--all",
        action="store_true",
        help="Run all enumeration modules (Ports, Subdomains, Dirs, VHosts)",
    )
    mode_group.add_argument(
        "-p", "--ports",
        nargs="?",
        const="top20",
        type=str,
        help="Run TCP port scan. (e.g. 'top20', 'top100', '80,443,8080', '1-1024')",
    )
    mode_group.add_argument(
        "--subdomains",
        action="store_true",
        help="Run Subdomain enumeration (DNS Brute-force + crt.sh OSINT)",
    )
    mode_group.add_argument(
        "--dirs",
        action="store_true",
        help="Run HTTP directory and file fuzzing",
    )
    mode_group.add_argument(
        "--vhosts",
        action="store_true",
        help="Run Virtual Host (VHost) header fuzzing",
    )
    
    # Performance & Concurrency
    perf_group = parser.add_argument_group("Performance & Tuning")
    perf_group.add_argument(
        "-c", "--concurrency",
        type=int,
        default=100,
        help="Maximum concurrent async tasks / connections (default: 100)",
    )
    perf_group.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="Socket / DNS / HTTP connection timeout in seconds (default: 3.0)",
    )
    
    # Wordlists
    wl_group = parser.add_argument_group("Wordlists")
    wl_group.add_argument(
        "--wordlist",
        type=str,
        help="Custom wordlist path (applies to active fuzzing/subdomain mode)",
    )
    
    # Output
    out_group = parser.add_argument_group("Output & Reporting")
    out_group.add_argument(
        "-o", "--output",
        type=str,
        help="Path to save JSON scan results (e.g. report.json)",
    )
    
    return parser


async def main_async() -> None:
    """Asynchronous entry point."""
    print_banner()
    
    parser = build_cli_parser()
    args = parser.parse_args()
    
    # Validate and clean target
    target = args.target.strip().replace("http://", "").replace("https://", "").rstrip("/")
    if not target:
        log_error("Target cannot be empty!")
        sys.exit(1)
        
    config = ReconConfig(
        target=target,
        concurrency_limit=args.concurrency,
        timeout=args.timeout,
    )
    
    # Custom wordlist override
    if args.wordlist:
        custom_wl = Path(args.wordlist)
        if custom_wl.exists():
            config.subdomain_wordlist = custom_wl
            config.dir_wordlist = custom_wl
            config.vhost_wordlist = custom_wl
            log_info(f"Using custom wordlist: [bold white]{custom_wl}[/bold white]")
        else:
            log_warn(f"Specified wordlist '{args.wordlist}' not found! Using built-in defaults.")
    
    # Determine which modes to run
    should_scan_ports = args.ports is not None or args.all or not (args.subdomains or args.dirs or args.vhosts)
    should_scan_subs = args.subdomains or args.all
    should_scan_dirs = args.dirs or args.all
    should_scan_vhosts = args.vhosts or args.all
    
    if should_scan_ports:
        port_spec = args.ports if args.ports else "top20"
        config.ports = parse_ports(port_spec)
        
    log_info(f"Target: [bold white]{config.target}[/bold white]")
    log_info(f"Concurrency Limit (Semaphore): [bold yellow]{config.concurrency_limit}[/bold yellow]")
    log_info(f"Network Timeout: [bold yellow]{config.timeout}s[/bold yellow]")
    
    active_modes = []
    if should_scan_ports:
        active_modes.append(f"Port Scan ({len(config.ports)} ports)")
    if should_scan_subs:
        active_modes.append("Subdomain Enumeration")
    if should_scan_dirs:
        active_modes.append("Directory Fuzzing")
    if should_scan_vhosts:
        active_modes.append("VHost Enumeration")
        
    log_info(f"Active Scan Modules: [bold cyan]{', '.join(active_modes)}[/bold cyan]")
    
    scan_results = {
        "target": config.target,
        "concurrency": config.concurrency_limit,
    }
    
    # Phase 2: Execute Port Scan
    if should_scan_ports:
        ports_result = await run_port_scan(config)
        scan_results["ports"] = [asdict(r) for r in ports_result]
        
    # Phase 3: Execute Subdomain Enumeration
    if should_scan_subs:
        subs_result = await run_subdomain_scan(config)
        scan_results["subdomains"] = [asdict(r) for r in subs_result]
        
    # Phase 4 & 5: Future Modules hook here
    if should_scan_dirs:
        log_warn("Directory fuzzing module scheduled for Phase 4.")
    if should_scan_vhosts:
        log_warn("VHost module scheduled for Phase 5.")
        
    # Save results to JSON if requested
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(scan_results, indent=2), encoding="utf-8")
        log_success(f"Results saved to: [bold white]{out_path.resolve()}[/bold white]")


def main() -> None:
    """CLI launcher with graceful keyboard interrupt handling."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        console.print("\n[bold red][!] Scan aborted by user (Ctrl+C). Cleaning up tasks...[/bold red]")
        sys.exit(0)


if __name__ == "__main__":
    main()
