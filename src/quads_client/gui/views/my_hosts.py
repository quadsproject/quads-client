"""My Hosts view - shows user's active assignments and hosts"""

import threading
import tkinter as tk
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from tkinter import ttk, messagebox

from quads_client.gui.widgets.dialogs import show_error_dialog


class MyHostsView(ttk.Frame):
    """View for displaying user's active hosts and assignments"""

    def __init__(self, parent, shell):
        super().__init__(parent)
        self.shell = shell
        self._loading = False

        # Load preferences
        prefs = self._get_preferences()
        self.auto_refresh_enabled = prefs.get("auto_refresh_my_hosts", True)
        self.refresh_interval = prefs.get("auto_refresh_interval", 30) * 1000  # Convert to ms

        self._create_ui()

    def _run_in_thread(self, work_func, on_success, on_error=None):
        """Run work_func in a background thread, deliver result to main thread."""

        def _worker():
            try:
                result = work_func()
                self.after(0, lambda: on_success(result))
            except Exception as exc:
                if on_error:
                    self.after(0, lambda e=exc: on_error(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _get_preferences(self):
        """Get GUI preferences from config"""
        if self.shell.config and hasattr(self.shell.config, "config_data"):
            return self.shell.config.config_data.get("gui_preferences", {})
        return {}

    def _auto_login(self):
        """Auto-login using centralized server selection logic"""
        target_server = self.shell.get_auto_login_server()

        if target_server:
            success, error = self.shell.connect_to_server(target_server)
            if success:
                self._load_assignments()
            else:
                show_error_dialog(self, "Login Failed", f"Failed to connect to {target_server}", error or "")
        else:
            self.shell.gui_app._show_servers_view()

    def _create_ui(self):
        """Create the UI"""
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=20, pady=10)

        title_label = ttk.Label(header_frame, text="My Hosts", font=("TkDefaultFont", 14, "bold"))
        title_label.pack(side=tk.LEFT)

        ttk.Button(header_frame, text="🔄 Refresh", command=self._manual_refresh).pack(side=tk.RIGHT)

        interval_sec = self.refresh_interval // 1000
        self.auto_refresh_var = tk.BooleanVar(value=self.auto_refresh_enabled)
        self.auto_refresh_check = ttk.Checkbutton(
            header_frame,
            text=f"Auto-refresh ({interval_sec}s)",
            variable=self.auto_refresh_var,
            command=self._toggle_auto_refresh,
        )
        self.auto_refresh_check.pack(side=tk.RIGHT, padx=10)

        # Start auto-refresh if enabled (delay by refresh_interval to avoid double-load)
        if self.auto_refresh_enabled:
            self.after(self.refresh_interval, self._schedule_auto_refresh)

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._canvas = tk.Canvas(
            canvas_frame, highlightthickness=0, bg=self.shell.gui_app.theme_manager.get_color("bg")
        )
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self._canvas.yview)
        self.content_frame = ttk.Frame(self._canvas)

        self.content_frame.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas_window = self._canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._canvas_window, width=e.width))

        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._canvas.bind("<Enter>", self._bind_mousewheel)
        self._canvas.bind("<Leave>", self._unbind_mousewheel)

        self.status_label = ttk.Label(self, text="Loading...", font=("TkDefaultFont", 9))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 10))

        self._load_assignments()

    def _bind_mousewheel(self, event=None):
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event=None):
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _load_assignments(self):
        """Load user's assignments"""
        if self._loading:
            return
        self._loading = True

        for widget in self.content_frame.winfo_children():
            widget.destroy()

        if not self.shell.is_authenticated():
            self._loading = False
            message_frame = ttk.Frame(self.content_frame)
            message_frame.pack(pady=50)

            ttk.Label(
                message_frame,
                text="Please login to view your hosts",
                font=("TkDefaultFont", 12),
            ).pack(pady=(0, 20))

            ttk.Button(message_frame, text="Login", command=self._auto_login).pack()

            self.status_label.config(text="Not authenticated")
            return

        self.status_label.config(text="Loading assignments...")

        def on_success(assignments_data):
            self._loading = False
            for widget in self.content_frame.winfo_children():
                widget.destroy()

            if not assignments_data:
                ttk.Label(
                    self.content_frame,
                    text="No active assignments\n\nGo to Schedule view to reserve hosts",
                    font=("TkDefaultFont", 12),
                    justify=tk.CENTER,
                ).pack(pady=50)
                self.status_label.config(text="No assignments found")
                return

            for assignment in assignments_data:
                self._create_assignment_panel(assignment)

            self.status_label.config(text=f"Showing {len(assignments_data)} assignment(s) | Last updated: Just now")

        def on_error(exc):
            self._loading = False
            for widget in self.content_frame.winfo_children():
                widget.destroy()

            error_label = ttk.Label(
                self.content_frame,
                text=f"Error loading assignments:\n{str(exc)}",
                foreground="red",
            )
            error_label.pack(pady=50)
            self.status_label.config(text="Error loading data")

        self._run_in_thread(self._fetch_assignments, on_success, on_error)

    def _fetch_assignments(self):
        """Fetch assignments from the server via CLI command"""
        from quads_client.utils import get_username_short
        from quads_client.progress import format_progress_str

        assignments_data = []

        try:
            # Use short username (without @domain.com) to match how assignments are created
            username = get_username_short(self.shell.connection.username)
            user_assignments = self.shell.connection.api.filter_assignments({"owner": username, "active": True})

            if not user_assignments:
                return []

            move_status_map = {}
            try:
                all_moves = self.shell.connection.api.get_all_move_status()
                if all_moves:
                    move_status_map = {m["host"]: m for m in all_moves if isinstance(m, dict)}
            except Exception as e:
                self.shell.perror(f"Failed to fetch move status: {e}")

            for assignment in user_assignments:
                if isinstance(assignment, dict):
                    assignment_id = assignment.get("_id") or assignment.get("id")
                    cloud = assignment.get("cloud", {})
                    cloud_name = cloud.get("name") if isinstance(cloud, dict) else str(cloud)
                    description = assignment.get("description", "No description")

                    # Fetch schedules by assignment_id (not cloud - API doesn't support that filter)
                    try:
                        schedules = self.shell.connection.api.get_schedules({"assignment_id": int(assignment_id)})
                    except (TypeError, ValueError):
                        schedules = []

                    is_validated = assignment.get("validated", False)

                    hosts = []
                    created = "N/A"
                    expires = "N/A"
                    days_remaining = "N/A"

                    for schedule in schedules if schedules else []:
                        if isinstance(schedule, dict):
                            hostname = schedule.get("host", {})
                            if isinstance(hostname, dict):
                                hostname = hostname.get("name", "")

                            if is_validated:
                                status = "active"
                                progress = format_progress_str("completed")
                            else:
                                move_data = move_status_map.get(str(hostname))
                                if move_data:
                                    move_status = move_data.get("status", "pending")
                                    progress = format_progress_str(move_status)
                                    status = move_status
                                else:
                                    status = "scheduled"
                                    progress = "Awaiting move"

                            hosts.append({"name": str(hostname), "status": status, "progress": progress})

                    if schedules:
                        first = schedules[0] if isinstance(schedules[0], dict) else {}
                        created = first.get("start", "N/A").replace("GMT", "UTC")
                        expires = first.get("end", "N/A").replace("GMT", "UTC")
                        days_remaining = self._calc_days_remaining(expires)

                    assignments_data.append(
                        {
                            "id": assignment_id,
                            "cloud": cloud_name,
                            "description": description,
                            "created": created,
                            "expires": expires,
                            "hosts": hosts,
                            "days_remaining": days_remaining,
                        }
                    )

        except Exception as e:
            self.shell.perror(f"Failed to fetch assignments: {e}")

        return assignments_data

    @staticmethod
    def _calc_days_remaining(date_str):
        """Calculate days remaining from a date string (RFC 2822 or ISO format)"""
        try:
            try:
                dt = parsedate_to_datetime(date_str)
            except Exception:
                dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = dt - datetime.now(timezone.utc)
            days = max(0, delta.days)
            return str(days)
        except Exception:
            return "N/A"

    def _create_assignment_panel(self, assignment):
        """Create a panel for one assignment"""
        panel = ttk.LabelFrame(
            self.content_frame,
            text=f"Assignment #{assignment['id']}: {assignment['description']}",
            padding=10,
        )
        panel.pack(fill=tk.X, pady=(0, 15))

        info_frame = ttk.Frame(panel)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        info_text = f"Cloud: {assignment['cloud']} | Created: {assignment['created']} | "
        info_text += f"Expires: {assignment['expires']} ({assignment['days_remaining']} days remaining)"

        ttk.Label(info_frame, text=info_text).pack(side=tk.LEFT)

        tree_frame = ttk.Frame(panel)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("host", "status", "progress")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=len(assignment["hosts"]))

        tree.heading("host", text="Host")
        tree.heading("status", text="Status")
        tree.heading("progress", text="Progress")

        tree.column("host", width=250)
        tree.column("status", width=120)
        tree.column("progress", width=150)

        for host in assignment["hosts"]:
            status_icon = self._get_status_icon(host["status"])
            progress_bar = self._get_progress_bar(host["progress"])
            display_status = host["status"].replace("_", " ").title()

            item_id = tree.insert(
                "",
                tk.END,
                values=(host["name"], f"{status_icon} {display_status}", progress_bar),
            )

            if host["status"] == "active":
                tree.item(item_id, tags=("active",))
                tree.tag_configure("active", foreground=self.shell.gui_app.theme_manager.get_color("success"))
            elif host["status"] == "failed":
                tree.item(item_id, tags=("failed",))
                tree.tag_configure("failed", foreground=self.shell.gui_app.theme_manager.get_color("error"))
            elif host["status"] == "scheduled":
                tree.item(item_id, tags=("scheduled",))
                tree.tag_configure("scheduled", foreground=self.shell.gui_app.theme_manager.get_color("warning"))
            else:
                tree.item(item_id, tags=("provisioning",))
                tree.tag_configure(
                    "provisioning", foreground=self.shell.gui_app.theme_manager.get_color("provisioning")
                )

        tree.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(panel)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            button_frame,
            text="Terminate Assignment",
            command=lambda: self._terminate_assignment(assignment["id"]),
        ).pack(side=tk.LEFT)

    def _get_status_icon(self, status):
        icons = {
            "active": "✓",
            "failed": "✗",
            "scheduled": "○",
        }
        return icons.get(status, "⏳")

    def _get_progress_bar(self, progress):
        """Get text progress bar"""
        if progress == "N/A":
            return "░" * 10 + " N/A"
        if isinstance(progress, str):
            if progress.startswith("FAILED"):
                return "░" * 10 + " FAILED"
            if "/" in progress:
                parts = progress.split("/")
                try:
                    current, total = int(parts[0]), int(parts[1])
                    filled = int((current / total) * 10) if total else 0
                except (ValueError, IndexError):
                    filled = 0
                empty = 10 - filled
                return "█" * filled + "░" * empty + f" {progress}"
            return "░" * 10 + f" {progress}"
        filled = int(progress / 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty + f" {progress}%"

    def _terminate_assignment(self, assignment_id):
        """Terminate an assignment"""
        # Check if we should confirm
        prefs = self._get_preferences()
        if prefs.get("confirm_terminate", True):
            if not messagebox.askyesno(
                "Confirm Termination",
                f"Are you sure you want to terminate assignment #{assignment_id}?\n\n"
                "This will release all hosts in this assignment.",
            ):
                return

        try:
            # Set GUI mode to bypass terminal confirmation prompt
            old_gui_mode = getattr(self.shell, "gui_mode", False)
            self.shell.gui_mode = True

            try:
                self.shell.user_commands.cmd_terminate(str(assignment_id))
                messagebox.showinfo(
                    "Success",
                    f"Assignment #{assignment_id} terminated\n\n"
                    "Note: It may take a few moments for the termination to complete.",
                )
                self._load_assignments()
            finally:
                # Restore original gui_mode
                self.shell.gui_mode = old_gui_mode

        except Exception as e:
            import traceback

            details = traceback.format_exc()
            show_error_dialog(self, "Termination Failed", str(e), details)

    def _manual_refresh(self):
        """Manual refresh triggered by button"""
        self._load_assignments()

    def _toggle_auto_refresh(self):
        """Toggle auto-refresh"""
        self.auto_refresh_enabled = self.auto_refresh_var.get()
        if self.auto_refresh_enabled:
            self._schedule_auto_refresh()

    def _schedule_auto_refresh(self):
        """Schedule automatic refresh"""
        if self.auto_refresh_enabled and self.winfo_exists():
            self._load_assignments()
            self.after(self.refresh_interval, self._schedule_auto_refresh)

    def refresh(self):
        """Public method to refresh the view"""
        self._load_assignments()

    def refresh_theme(self):
        """Update non-ttk widget colors after theme change"""
        bg = self.shell.gui_app.theme_manager.get_color("bg")
        self._canvas.configure(bg=bg)

    def apply_preferences(self, preferences):
        """Apply updated preferences"""
        # Update interval
        new_interval = preferences.get("auto_refresh_interval", 30) * 1000
        if new_interval != self.refresh_interval:
            self.refresh_interval = new_interval
            interval_sec = self.refresh_interval // 1000
            self.auto_refresh_check.config(text=f"Auto-refresh ({interval_sec}s)")

        # Update enabled state
        new_enabled = preferences.get("auto_refresh_my_hosts", True)
        if new_enabled != self.auto_refresh_enabled:
            self.auto_refresh_enabled = new_enabled
            self.auto_refresh_var.set(new_enabled)
            if new_enabled:
                self._schedule_auto_refresh()
