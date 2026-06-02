from quads_client.progress import TOTAL_STAGES, stage_of


class MoveCommands:
    def __init__(self, shell):
        self.shell = shell

    def cmd_move_status(self, args):
        """Show move/rebuild progress for active moves or a specific host"""
        if not self.shell.connection or not self.shell.connection.is_connected:
            self.shell.rich_console.print_error("Not connected")
            return

        if not self.shell.connection.is_authenticated:
            self.shell.rich_console.print_error("Not authenticated")
            return

        hostname = args.strip() if args else None

        if hostname:
            try:
                progress = self.shell.connection.api.get_move_progress(hostname)
            except Exception:
                progress = None

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
                active = self.shell.connection.api.get_all_move_progress()
            except Exception:
                active = []

            if not active:
                self.shell.rich_console.print_info("No active moves")
                return

            headers = ["Host", "From", "To", "Progress", "Status", "Message"]
            rows = []
            for move in active:
                status = move.get("status", "pending")
                stage = stage_of(status)
                if status == "failed":
                    progress_str = f"FAILED @ {stage}/{TOTAL_STAGES}"
                elif status == "completed":
                    progress_str = f"{TOTAL_STAGES}/{TOTAL_STAGES}"
                else:
                    progress_str = f"{stage}/{TOTAL_STAGES}"
                rows.append(
                    [
                        move.get("host", "?"),
                        move.get("source_cloud", ""),
                        move.get("target_cloud", ""),
                        progress_str,
                        status,
                        move.get("message", "") or "",
                    ]
                )
            self.shell.rich_console.print_table(headers, rows, title="Active Moves")
