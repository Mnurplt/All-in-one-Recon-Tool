"""
Logger and terminal output styling using Rich.
Provides standardized, color-coded logging and progress tracking.
Includes Windows CP1254/UTF-8 terminal compatibility.
"""
import sys
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Ensure UTF-8 output on Windows consoles to prevent charmap/CP1254 UnicodeEncodeErrors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Shared rich console instance configured for clean output
console = Console(highlight=False)


def print_banner() -> None:
    """Displays the tool banner with metadata."""
    banner = (
        "[bold cyan]   ___  __   __    _____       ____  ____   ___  ___  _  _ [/bold cyan]\n"
        "[bold cyan]  / _ \\/ /  / /   /  _/____   / __ \\/ __/  / _ \\/ _ \\| \\| |[/bold cyan]\n"
        "[bold blue] / __ / /__/ /__ _/ / /___/  / /_/ / _/   / , _/ // /| .` |[/bold blue]\n"
        "[bold magenta]/_/ |_/____/____/___/       /_____/___/  /_/|_|\\___/ |_|\\_|[/bold magenta]\n"
    )
    
    panel = Panel(
        Text.from_markup(banner),
        subtitle="[bold white]All-In-One Network & Web Recon Engine (Async Python)[/bold white]",
        border_style="bright_blue",
        padding=(0, 2),
    )
    console.print(panel)



def log_info(message: str) -> None:
    """Informational message [ * ]"""
    console.print(f"[bold blue][*][/bold blue] {message}")


def log_success(message: str) -> None:
    """Success / finding message [ + ]"""
    console.print(f"[bold green][+][/bold green] [green]{message}[/green]")


def log_warn(message: str) -> None:
    """Warning message [ ! ]"""
    console.print(f"[bold yellow][!][/bold yellow] [yellow]{message}[/yellow]")


def log_error(message: str) -> None:
    """Error message [ - ]"""
    console.print(f"[bold red][-][/bold red] [red]{message}[/red]")


def log_status(section_name: str) -> None:
    """Visual section separator"""
    console.print(f"\n[bold magenta]━━━ 🔍 {section_name.upper()} ━━━[/bold magenta]")


def create_table(title: str, columns: list[str]) -> Table:
    """Helper to create standardized rich tables."""
    table = Table(title=title, show_header=True, header_style="bold cyan", border_style="dim")
    for col in columns:
        table.add_column(col)
    return table
