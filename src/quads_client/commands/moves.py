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
