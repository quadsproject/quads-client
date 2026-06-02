"""Move Progress view - shows active move/rebuild progress"""

import tkinter as tk
from tkinter import ttk

from quads_client.gui.widgets.base import BaseAdminView, ScrolledTreeview
from quads_client.progress import TOTAL_STAGES, stage_of


class MoveProgressView(BaseAdminView):
    """View for displaying active move/rebuild progress"""

    def __init__(self, parent, shell):
        super().__init__(parent, shell, "Move Progress", requires_admin=False)
        self._auto_refresh = False
        self._refresh_job = None
        self._create_ui()

    def _create_ui(self):
        header_buttons = [
            ("↻ Refresh", self._load_progress),
        ]
        self.create_header(header_buttons)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 5))

        self._auto_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            btn_frame,
            text="Auto-refresh (10s)",
            variable=self._auto_var,
            command=self._toggle_auto_refresh,
        ).pack(side=tk.LEFT)

        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        columns = ("host", "from_cloud", "to_cloud", "progress", "status", "message")
        column_configs = {
            "host": ("Host", 200),
            "from_cloud": ("From", 100),
            "to_cloud": ("To", 100),
            "progress": ("Progress", 100),
            "status": ("Status", 120),
            "message": ("Message", 250),
        }

        self.tree = ScrolledTreeview(content_frame, columns, column_configs)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.create_status_label()
        self._load_progress()

    def _load_progress(self):
        if not self.check_auth():
            return

        def _fetch():
            return self.shell.connection.api.get_all_move_progress()

        def _on_loaded(moves):
            self.tree.clear()
            if not moves:
                self.update_status("No active moves")
                return
            for move in moves:
                status = move.get("status", "pending")
                stage = stage_of(status)
                if status == "failed":
                    progress_str = f"FAILED @ {stage}/{TOTAL_STAGES}"
                    tag = "failed"
                elif status == "completed":
                    progress_str = f"{TOTAL_STAGES}/{TOTAL_STAGES}"
                    tag = "completed"
                else:
                    progress_str = f"{stage}/{TOTAL_STAGES}"
                    tag = ""
                values = (
                    move.get("host", "?"),
                    move.get("source_cloud", ""),
                    move.get("target_cloud", ""),
                    progress_str,
                    status,
                    move.get("message", "") or "",
                )
                self.tree.tree.insert(
                    "", tk.END, values=values, tags=(tag,) if tag else ()
                )

            self.tree.tree.tag_configure("failed", foreground="red")
            self.tree.tree.tag_configure("completed", foreground="green")
            self.update_status(f"{len(moves)} active move(s)")

        def _on_error(exc):
            self.update_status(f"Error: {exc}")

        self._run_in_thread(_fetch, _on_loaded, _on_error)

    def _toggle_auto_refresh(self):
        if self._auto_var.get():
            self._auto_refresh = True
            self._poll_tick()
        else:
            self._auto_refresh = False
            if self._refresh_job:
                self.after_cancel(self._refresh_job)
                self._refresh_job = None

    def _poll_tick(self):
        if not self._auto_refresh:
            return
        self._load_progress()
        self._refresh_job = self.after(10000, self._poll_tick)

    def destroy(self):
        self._auto_refresh = False
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
            self._refresh_job = None
        super().destroy()
