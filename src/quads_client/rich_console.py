"""Rich console wrapper for enhanced UI output"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from quads_client import __version__


class RichConsole:
    """Wrapper for Rich console with QUADS-specific formatting"""

    def __init__(self):
        self.console = Console()

    def print_banner(self, has_servers=False):
        """Print the QUADS Client banner"""
        banner_text = """
  ___  _   _   _    ____  ____       ____ _ _            _
 / _ \\| | | | / \\  |  _ \\/ ___|     / ___| (_) ___ _ __ | |_
| | | | | | |/ _ \\ | | | \\___ \\ ___| |   | | |/ _ \\ '_ \\| __|
| |_| | |_| / ___ \\| |_| |___) |___| |___| | |  __/ | | | |_
 \\__\\_\\\\___/_/   \\_\\____/|____/     \\____|_|_|\\___|_| |_|\\__|
"""
        if has_servers:
            add_server_line = "[yellow]Type 'add_quads_server' to add a QUADS server[/yellow]\n"
        else:
            add_server_line = "[yellow]Type 'add_quads_server' to add your first QUADS server[/yellow]\n"
        intro_panel = Panel(
            f"[bold cyan]{banner_text}[/bold cyan]\n\n"
            f"[bold white]QUADS Client v{__version__} - Interactive TUI Shell[/bold white]\n"
            "[dim]https://quads.dev[/dim]\n\n"
            f"{add_server_line}"
            "[yellow]Type 'connect' to connect to a server[/yellow]\n"
            "[yellow]Type 'token-login' to authenticate with an SSO token[/yellow]\n"
            "[yellow]Type 'register' to create a new account[/yellow]\n"
            "[yellow]Type 'help' for available commands[/yellow]\n\n"
            "[dim]Configuration: ~/.config/quads/quads-client.yml[/dim]\n"
            "[dim]History: ~/.config/quads/.quads-client-history.db[/dim]",
            border_style="cyan",
            expand=False,
        )
        self.console.print(intro_panel)

    def print_table(self, headers, rows, title=None):
        """Print a formatted table"""
        table = Table(title=title, show_header=True, header_style="bold cyan")

        for header in headers:
            table.add_column(header)

        for row in rows:
            # Convert all values to strings
            str_row = [str(cell) for cell in row]
            table.add_row(*str_row)

        self.console.print(table)

    def print_success(self, message):
        """Print a success message"""
        self.console.print(f"[bold green]>>[/bold green] {message}")

    def print_error(self, message):
        """Print an error message"""
        self.console.print(f"[bold red]ERROR:[/bold red] {message}", style="red")

    def print_warning(self, message):
        """Print a warning message"""
        self.console.print(f"[bold yellow]WARNING:[/bold yellow] {message}", style="yellow")

    def print_info(self, message):
        """Print an info message"""
        self.console.print(message)

    def print_section(self, title):
        """Print a section header"""
        self.console.print(f"\n[bold cyan]{title}[/bold cyan]")
        self.console.print("=" * 80, style="dim")

    def print_property(self, key, value):
        """Print a key-value property"""
        self.console.print(f"[cyan]{key}:[/cyan] {value}")
