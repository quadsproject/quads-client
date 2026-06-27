import time
from datetime import datetime

from rich.live import Live
from rich.table import Table

from quads_client.error_handler import handle_api_error, require_auth
from quads_client.progress import format_progress_str


class TrackCommands:
    def __init__(self, shell):
        self.shell = shell

    def _require_auth(self):
        return require_auth(self.shell)

    def cmd_track(self, args):
        """Live-track move/rebuild progress. Usage: track [hostname|cloudname]"""
        if not self._require_auth():
            return

        args = args.strip() if args else ""
        hostname = None
        cloud = None

        if args:
            if args.startswith("cloud"):
                cloud = args
            else:
                hostname = args

        console = self.shell.rich_console.console
        api = self.shell.connection.api

        try:
            if hostname:
                self._track_single(api, console, hostname)
            else:
                self._track_all(api, console, cloud)
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in str(e) or "not found" in error_msg:
                self.shell.rich_console.print_info("Move tracking is not available on this server")
            else:
                handle_api_error(self.shell, e, "Track")

    def _track_single(self, api, console, hostname):
        try:
            data = api.get_move_status(hostname)
        except Exception:
            data = None

        if not data:
            pending = self._get_pending_moves(api, hostname=hostname)
            if not pending:
                self.shell.rich_console.print_info(f"No active or scheduled moves for {hostname}")
                return
            data = self._wait_for_active_single(api, console, hostname, pending)
            if not data:
                return

        completed = False
        last_data = dict(data)
        gone_count = 0
        try:
            with Live(self._build_single_table(data), console=console, refresh_per_second=0.2) as live:
                while True:
                    time.sleep(5)
                    try:
                        data = api.get_move_status(hostname)
                    except Exception:
                        data = None
                    if not data:
                        gone_count += 1
                        if gone_count < 6:
                            continue
                        last_data["status"] = "completed"
                        last_data["message"] = "Completed"
                        live.update(self._build_single_table(last_data))
                        completed = True
                        time.sleep(1)
                        break
                    gone_count = 0
                    last_data = dict(data)
                    live.update(self._build_single_table(data))
                    status = data.get("status")
                    if status == "failed":
                        completed = True
                        time.sleep(1)
                        break
        except KeyboardInterrupt:
            pass
        if completed:
            console.print("[dim]Move completed.[/dim]")
        else:
            console.print("[dim]Stopped tracking.[/dim]")

    def _track_all(self, api, console, cloud=None):
        moves = api.get_all_move_status(cloud=cloud)

        if not moves:
            pending = self._get_pending_moves(api, cloud=cloud)
            if not pending:
                label = f" for {cloud}" if cloud else ""
                self.shell.rich_console.print_info(f"No active or scheduled moves{label}")
                return
            moves = self._wait_for_active_all(api, console, cloud, pending)
            if not moves:
                return

        completed = False
        last_moves = list(moves)
        gone_count = 0
        try:
            with Live(self._build_all_table(moves), console=console, refresh_per_second=0.2) as live:
                while True:
                    time.sleep(5)
                    try:
                        moves = api.get_all_move_status(cloud=cloud)
                    except Exception:
                        moves = []
                    if not moves:
                        gone_count += 1
                        if gone_count < 6:
                            continue
                        for m in last_moves:
                            m["status"] = "completed"
                            m["message"] = "Completed"
                        live.update(self._build_all_table(last_moves))
                        completed = True
                        time.sleep(1)
                        break
                    gone_count = 0
                    last_moves = list(moves)
                    live.update(self._build_all_table(moves))
                    if all(m.get("status") == "failed" for m in moves):
                        completed = True
                        time.sleep(1)
                        break
        except KeyboardInterrupt:
            pass

        if completed:
            count = len(last_moves)
            console.print(f"[dim]All moves completed. {count} host(s) finished.[/dim]")
        else:
            count = len(last_moves)
            console.print(f"[dim]Stopped tracking. {count} move(s) active.[/dim]")

    def _get_pending_moves(self, api, cloud=None, hostname=None):
        try:
            pending = api.get_moves()
        except Exception:
            pending = []

        if cloud:
            pending = [m for m in pending if m.get("new") == cloud]
        if hostname:
            pending = [m for m in pending if m.get("host") == hostname]
        return pending

    def _wait_for_active_all(self, api, console, cloud, pending):
        try:
            with Live(
                self._build_pending_table(pending), console=console, refresh_per_second=0.2, transient=True
            ) as live:
                while True:
                    time.sleep(10)
                    active = api.get_all_move_status(cloud=cloud)
                    if active:
                        return active
                    pending = self._get_pending_moves(api, cloud=cloud)
                    if not pending:
                        return []
                    live.update(self._build_pending_table(pending))
        except KeyboardInterrupt:
            console.print("[dim]Stopped tracking.[/dim]")
            return None

    def _wait_for_active_single(self, api, console, hostname, pending):
        try:
            with Live(
                self._build_pending_table(pending), console=console, refresh_per_second=0.2, transient=True
            ) as live:
                while True:
                    time.sleep(10)
                    try:
                        data = api.get_move_status(hostname)
                    except Exception:
                        data = None
                    if data:
                        return data
                    pending = self._get_pending_moves(api, hostname=hostname)
                    if not pending:
                        return None
                    live.update(self._build_pending_table(pending))
        except KeyboardInterrupt:
            console.print("[dim]Stopped tracking.[/dim]")
            return None

    def _build_pending_table(self, pending):
        now = datetime.now().strftime("%H:%M:%S")
        table = Table(
            title="Scheduled Moves (awaiting next move cycle)",
            caption=f"Last check: {now} | Refresh: 10s | Ctrl+C to stop",
            show_header=True,
            header_style="bold yellow",
        )
        table.add_column("Host")
        table.add_column("From")
        table.add_column("To")
        table.add_column("Status")

        for move in pending:
            table.add_row(
                move.get("host", "?"),
                move.get("current", ""),
                move.get("new", ""),
                "Scheduled",
                style="yellow",
            )
        return table

    def _build_all_table(self, moves):
        now = datetime.now().strftime("%H:%M:%S")
        table = Table(
            title="Live Move Progress",
            caption=f"Last update: {now} | Refresh: 5s | Ctrl+C to stop",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Host")
        table.add_column("From")
        table.add_column("To")
        table.add_column("Progress")
        table.add_column("Status")
        table.add_column("Message")

        for move in moves:
            status = move.get("status", "pending")
            if status == "failed":
                style = "red"
            elif status == "completed":
                style = "green"
            else:
                style = None
            table.add_row(
                move.get("host", "?"),
                move.get("source_cloud", ""),
                move.get("target_cloud", ""),
                format_progress_str(status),
                status.replace("_", " ").title(),
                move.get("message", "") or "",
                style=style,
            )
        return table

    def _build_single_table(self, data):
        now = datetime.now().strftime("%H:%M:%S")
        status = data.get("status", "pending")
        hostname = data.get("host", "?")
        table = Table(
            title=f"Tracking: {hostname}",
            caption=f"Last update: {now} | Refresh: 5s | Ctrl+C to stop",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Field")
        table.add_column("Value")

        table.add_row("Host", hostname)
        table.add_row("From", data.get("source_cloud", ""))
        table.add_row("To", data.get("target_cloud", ""))
        table.add_row("Status", status.replace("_", " ").title())
        table.add_row("Progress", format_progress_str(status))
        msg = data.get("message", "") or ""
        if msg:
            table.add_row("Message", msg)
        err = data.get("error_message", "") or ""
        if err:
            table.add_row("Error", f"[red]{err}[/red]")
        started = data.get("started_at")
        if started:
            table.add_row("Started", started)
        return table
