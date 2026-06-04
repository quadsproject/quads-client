"""Move Progress view - shows active move/rebuild progress"""

import tkinter as tk
from tkinter import ttk

from quads_client.gui.widgets.base import BaseAdminView, ScrolledTreeview
from quads_client.progress import format_progress_str


class MoveProgressView(BaseAdminView):
    """View for displaying active move/rebuild progress"""

    def __init__(self, parent, shell):
        super().__init__(parent, shell, "Move Progress", requires_admin=False)
        self._auto_refresh = False
        self._refresh_job = None
        self._loading = False
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

        self.tree.tree.tag_configure("failed", foreground="red")
        self.tree.tree.tag_configure("completed", foreground="green")

        self.create_status_label()
        self._load_progress()

    def _load_progress(self):
        if self._loading:
            return
        if not self.check_auth():
            return

        self._loading = True

        def _fetch():
            return self.shell.connection.api.get_all_move_status()

        def _on_loaded(moves):
            self._loading = False
            if not self.winfo_exists():
                return
            self.tree.clear()
            if not moves:
                self.update_status("No active moves")
                return
            for move in moves:
                status = move.get("status", "pending")
                tag = ""
                if status == "failed":
                    tag = "failed"
                elif status == "completed":
                    tag = "completed"
                values = (
                    move.get("host", "?"),
                    move.get("source_cloud", ""),
                    move.get("target_cloud", ""),
                    format_progress_str(status),
                    status,
                    move.get("message", "") or "",
                )
                self.tree.tree.insert("", tk.END, values=values, tags=(tag,) if tag else ())

            self.update_status(f"{len(moves)} active move(s)")

        def _on_error(exc):
            self._loading = False
            if not self.winfo_exists():
                return
            self.update_status(f"Error: {exc}")

        self._run_in_thread(_fetch, _on_loaded, _on_error)

    def refresh(self):
        """Public method to refresh the view"""
        self._load_progress()

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
