from quads_client.error_handler import handle_api_error, require_auth
from quads_client.progress import TOTAL_STAGES, format_progress_str, stage_of


class MoveCommands:
    def __init__(self, shell):
        self.shell = shell

    def _require_auth(self):
        return require_auth(self.shell)

    def cmd_move_status(self, args):
        """Show move/rebuild progress for active moves or a specific host"""
        if not self._require_auth():
            return

        hostname = args.strip() if args else None

        if hostname:
            try:
                progress = self.shell.connection.api.get_move_status(hostname)
            except Exception as e:
                error_msg = str(e).lower()
                if "404" in str(e) or "not found" in error_msg:
                    self.shell.rich_console.print_info("Move tracking is not available on this server")
                else:
                    handle_api_error(self.shell, e, "Move status")
                return

            if not progress:
                self.shell.rich_console.print_info(f"No active move for {hostname}")
                return

            status = progress.get("status", "pending")
            stage = stage_of(status)
            msg = progress.get("message", "") or ""
            err = progress.get("error_message", "") or ""

            rows = [
                ["Host", progress.get("host", hostname)],
                ["From", progress.get("source_cloud", "")],
                ["To", progress.get("target_cloud", "")],
                ["Status", status],
                ["Progress", f"{stage}/{TOTAL_STAGES} stages"],
            ]
            if msg:
                rows.append(["Message", msg])
            if err:
                rows.append(["Error", err])

            self.shell.rich_console.print_table(
                ["Field", "Value"],
                rows,
                title=f"Move Progress: {hostname}",
            )
        else:
            try:
                active = self.shell.connection.api.get_all_move_status()
            except Exception as e:
                error_msg = str(e).lower()
                if "404" in str(e) or "not found" in error_msg:
                    self.shell.rich_console.print_info("Move tracking is not available on this server")
                else:
                    handle_api_error(self.shell, e, "Move status")
                return

            if not active:
                self.shell.rich_console.print_info("No active moves")
                return

            headers = ["Host", "From", "To", "Progress", "Status", "Message"]
            rows = []
            for move in active:
                status = move.get("status", "pending")
                rows.append(
                    [
                        move.get("host", "?"),
                        move.get("source_cloud", ""),
                        move.get("target_cloud", ""),
                        format_progress_str(status),
                        status,
                        move.get("message", "") or "",
                    ]
                )
            self.shell.rich_console.print_table(headers, rows, title="Active Moves")

    def cmd_activity(self, args):
        """Show active moves grouped by cloud. Usage: activity"""
        if not self._require_auth():
            return

        try:
            active = self.shell.connection.api.get_all_move_status()
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in str(e) or "not found" in error_msg:
                self.shell.rich_console.print_info("Move tracking is not available on this server")
            else:
                handle_api_error(self.shell, e, "Activity")
            return

        if not active:
            self._show_pending_activity()
            return

        by_cloud = {}
        for move in active:
            cloud = move.get("target_cloud", "unknown")
            by_cloud.setdefault(cloud, []).append(move)

        icons = {"active": "✓", "completed": "✓", "failed": "✗"}
        total_moves = len(active)
        total_clouds = len(by_cloud)
        self.shell.rich_console.print_section(
            f"Active Operations: {total_moves} move(s) across {total_clouds} cloud(s)"
        )

        for cloud, moves in sorted(by_cloud.items()):
            count = len(moves)
            host_word = "host" if count == 1 else "hosts"
            self.shell.poutput(f"\n  Cloud: {cloud} ({count} {host_word})")
            for move in moves:
                status = move.get("status", "pending")
                icon = icons.get(status, "⏳")
                host = move.get("host", "?")
                progress = format_progress_str(status)
                msg = move.get("message", "") or ""
                display_status = status.replace("_", " ")
                line = f"    {icon} {host:<45} {display_status:<16} {progress:<8}"
                if msg:
                    line += f"  {msg}"
                self.shell.poutput(line)

    def _show_pending_activity(self):
        try:
            pending = self.shell.connection.api.get_moves()
        except Exception:
            pending = []

        if not pending:
            self.shell.rich_console.print_info("No active or scheduled operations")
            return

        by_cloud = {}
        for move in pending:
            cloud = move.get("new", "unknown")
            by_cloud.setdefault(cloud, []).append(move)

        total = len(pending)
        clouds = len(by_cloud)
        self.shell.rich_console.print_section(
            f"Scheduled Operations: {total} move(s) across {clouds} cloud(s) (awaiting next move cycle)"
        )

        for cloud, moves in sorted(by_cloud.items()):
            count = len(moves)
            host_word = "host" if count == 1 else "hosts"
            self.shell.poutput(f"\n  Cloud: {cloud} ({count} {host_word})")
            for move in moves:
                host = move.get("host", "?")
                current = move.get("current", "?")
                line = f"    ○ {host:<45} {current} -> {cloud}"
                self.shell.poutput(line)
