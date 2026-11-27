import time
from datetime import datetime

from rich.live import Live
from rich.table import Table

from quads_client.error_handler import handle_api_error, require_auth
from quads_client.progress import format_progress_str

# A failed move is retried by the next move cycle; past this window a move that
# keeps failing is reported dead even if the server keeps re-queuing it.
# failed_since is per track session and measured from the first failure; it is
# not reset when the move recovers, so a recover-then-refail move is still
# dead once total time in the session passes the window (deliberate: resets
# would hide a move that only briefly leaves the failed state each cycle).
RETRY_WINDOW_MINUTES = 120


def _scheduled_move_hosts(api, cloud=None):
    """Hosts the server still expects to move; None when that query fails."""
    try:
        scheduled = api.get_moves()
        if cloud:
            scheduled = [m for m in scheduled if m.get("new") == cloud]
        return {m.get("host") for m in scheduled}
    except Exception:
        return None


def _failed_retrying(move, scheduled_hosts, failed_since=None):
    """A failed move is retryable while the server lists it for a move and the
    failure has not outlived the retry window.

    A None scheduled_hosts means the query failed; keep polling rather than
    show a false terminal FAILED for a move the next cycle may still retry.
    """
    if move.get("status") != "failed":
        return False
    if failed_since is not None:
        if (datetime.now() - failed_since).total_seconds() > RETRY_WINDOW_MINUTES * 60:
            return False
    if scheduled_hosts is None:
        return True
    return move.get("host") in scheduled_hosts


def _display_progress(move, scheduled_hosts=None, failed_since=None):
    """Progress label and row style; a failed move still retrying shows Retrying."""
    status = move.get("status", "pending")
    if _failed_retrying(move, scheduled_hosts, failed_since):
        return "Retrying", "yellow"
    if status == "failed":
        return format_progress_str(status), "red"
    if status == "completed":
        return format_progress_str(status), "green"
    return format_progress_str(status), None


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
        failed_terminal = False
        last_data = dict(data)
        gone_count = 0
        failed_since = None
        scheduled = _scheduled_move_hosts(api) if data.get("status") == "failed" else None
        try:
            with Live(self._build_single_table(data, scheduled), console=console, refresh_per_second=0.2) as live:
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
                    if data.get("status") == "failed":
                        scheduled = _scheduled_move_hosts(api)
                        if failed_since is None:
                            failed_since = datetime.now()
                    else:
                        scheduled = None
                    live.update(self._build_single_table(data, scheduled, failed_since))
                    status = data.get("status")
                    if status == "failed" and not _failed_retrying(data, scheduled, failed_since):
                        failed_terminal = True
                        completed = True
                        time.sleep(1)
                        break
        except KeyboardInterrupt:
            pass
        if completed:
            if failed_terminal:
                console.print("[dim]Move failed.[/dim]")
            else:
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
        failed_terminal = False
        last_moves = list(moves)
        gone_count = 0
        failed_since = {}
        scheduled = (
            _scheduled_move_hosts(api, cloud=cloud) if any(m.get("status") == "failed" for m in moves) else None
        )
        try:
            with Live(self._build_all_table(moves, scheduled), console=console, refresh_per_second=0.2) as live:
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
                    if any(m.get("status") == "failed" for m in moves):
                        scheduled = _scheduled_move_hosts(api, cloud=cloud)
                        for m in moves:
                            if m.get("status") == "failed":
                                failed_since.setdefault(m.get("host"), datetime.now())
                    else:
                        scheduled = None
                    live.update(self._build_all_table(moves, scheduled, failed_since))
                    if all(m.get("status") == "failed" for m in moves) and not any(
                        _failed_retrying(m, scheduled, failed_since.get(m.get("host")) if failed_since else None)
                        for m in moves
                    ):
                        failed_terminal = True
                        completed = True
                        time.sleep(1)
                        break
        except KeyboardInterrupt:
            pass

        if completed:
            count = len(last_moves)
            if failed_terminal:
                console.print(f"[dim]{count} move(s) failed.[/dim]")
            else:
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

    def _build_all_table(self, moves, scheduled_hosts=None, failed_since=None):
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
        table.add_column("Error")

        for move in moves:
            first_at = failed_since.get(move.get("host")) if failed_since else None
            progress, style = _display_progress(move, scheduled_hosts, first_at)
            status = move.get("status", "pending")
            table.add_row(
                move.get("host", "?"),
                move.get("source_cloud", ""),
                move.get("target_cloud", ""),
                progress,
                status.replace("_", " ").title(),
                move.get("message", "") or "",
                move.get("error_message", "") or "",
                style=style,
            )
        return table

    def _build_single_table(self, data, scheduled_hosts=None, failed_since=None):
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
        progress, style = _display_progress(data, scheduled_hosts, failed_since)
        table.add_row("Progress", f"[{style}]{progress}[/{style}]" if style else progress)
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
