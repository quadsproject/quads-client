"""Preferences dialog for GUI configuration"""

import tkinter as tk
from tkinter import ttk


class PreferencesDialog(tk.Toplevel):
    """Modal dialog for user preferences"""

    def __init__(self, parent, config, theme_manager, shell=None):
        super().__init__(parent)
        self.parent = parent
        self.config = config
        self.theme_manager = theme_manager
        self.shell = shell
        self.result = None

        self.title("Preferences")
        self.geometry("500x600")
        self.minsize(500, 600)

        # Apply theme
        self.theme_manager.configure_toplevel(self)

        # Load current preferences
        self.prefs = self._load_preferences()

        self._create_ui()

        # Center on parent
        self.transient(parent)
        self.grab_set()

    def _load_preferences(self):
        """Load preferences from config"""
        # Get existing gui preferences from config
        gui_prefs = {}
        if self.config and hasattr(self.config, "config_data"):
            gui_prefs = self.config.config_data.get("gui_preferences", {})

        # Default values
        defaults = {
            "auto_refresh_interval": 30,
            "auto_refresh_my_hosts": True,
            "confirm_terminate": True,
            "confirm_release": True,
            "confirm_exit": False,
            "remember_window": True,
            "auto_connect": False,
            "default_server": "",
            "font_size": "large",
            # Admin-only scheduling defaults
            "admin_schedule_cadence": "2 weeks",  # "1 week" or "2 weeks"
            "admin_schedule_start_hour": 22,  # 0-23
            "admin_schedule_end_hour": 22,  # 0-23
        }

        # Merge with saved preferences
        return {**defaults, **gui_prefs}

    def _create_ui(self):
        """Create the preferences UI"""
        # Main scrollable container
        canvas = tk.Canvas(self, highlightthickness=0, bg=self.theme_manager.get_color("bg"))
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

        # Auto-Refresh Section
        refresh_frame = ttk.LabelFrame(scrollable_frame, text="Auto-Refresh", padding=15)
        refresh_frame.pack(fill=tk.X, pady=(0, 10), padx=10)

        interval_row = ttk.Frame(refresh_frame)
        interval_row.pack(fill=tk.X, pady=5)

        ttk.Label(interval_row, text="Default interval:").pack(side=tk.LEFT)
        self.interval_var = tk.IntVar(value=self.prefs["auto_refresh_interval"])
        interval_spinbox = ttk.Spinbox(
            interval_row, from_=10, to=300, increment=10, width=10, textvariable=self.interval_var
        )
        interval_spinbox.pack(side=tk.LEFT, padx=10)
        ttk.Label(interval_row, text="seconds").pack(side=tk.LEFT)

        self.auto_refresh_my_hosts_var = tk.BooleanVar(value=self.prefs["auto_refresh_my_hosts"])
        ttk.Checkbutton(refresh_frame, text="Enable for My Hosts view", variable=self.auto_refresh_my_hosts_var).pack(
            anchor=tk.W, pady=5
        )

        # Confirmations Section
        confirm_frame = ttk.LabelFrame(scrollable_frame, text="Confirmations", padding=15)
        confirm_frame.pack(fill=tk.X, pady=(0, 10), padx=10)

        self.confirm_terminate_var = tk.BooleanVar(value=self.prefs["confirm_terminate"])
        ttk.Checkbutton(
            confirm_frame, text="Confirm before terminating assignments", variable=self.confirm_terminate_var
        ).pack(anchor=tk.W, pady=5)

        self.confirm_release_var = tk.BooleanVar(value=self.prefs["confirm_release"])
        ttk.Checkbutton(confirm_frame, text="Confirm before releasing hosts", variable=self.confirm_release_var).pack(
            anchor=tk.W, pady=5
        )

        self.confirm_exit_var = tk.BooleanVar(value=self.prefs["confirm_exit"])
        ttk.Checkbutton(
            confirm_frame, text="Confirm on exit with active sessions", variable=self.confirm_exit_var
        ).pack(anchor=tk.W, pady=5)

        # Appearance Section
        appearance_frame = ttk.LabelFrame(scrollable_frame, text="Appearance", padding=15)
        appearance_frame.pack(fill=tk.X, pady=(0, 10), padx=10)

        font_row = ttk.Frame(appearance_frame)
        font_row.pack(fill=tk.X, pady=5)

        ttk.Label(font_row, text="Font size:").pack(side=tk.LEFT)
        self.font_size_var = tk.StringVar(value=self.prefs["font_size"])
        font_combo = ttk.Combobox(
            font_row,
            textvariable=self.font_size_var,
            values=["small", "medium", "large", "extra_large"],
            state="readonly",
            width=15,
        )
        font_combo.pack(side=tk.LEFT, padx=10)

        self.remember_window_var = tk.BooleanVar(value=self.prefs["remember_window"])
        ttk.Checkbutton(
            appearance_frame, text="Remember window size and position", variable=self.remember_window_var
        ).pack(anchor=tk.W, pady=5)

        # Startup Section
        startup_frame = ttk.LabelFrame(scrollable_frame, text="Startup", padding=15)
        startup_frame.pack(fill=tk.X, pady=(0, 10), padx=10)

        self.auto_connect_var = tk.BooleanVar(value=self.prefs["auto_connect"])
        auto_connect_check = ttk.Checkbutton(
            startup_frame,
            text="Auto-connect on startup",
            variable=self.auto_connect_var,
            command=self._toggle_auto_connect,
        )
        auto_connect_check.pack(anchor=tk.W, pady=5)

        server_row = ttk.Frame(startup_frame)
        server_row.pack(fill=tk.X, pady=5)

        ttk.Label(server_row, text="Default server:").pack(side=tk.LEFT)

        # Get list of configured servers
        server_names = []
        if self.config:
            servers = self.config.get_all_servers()
            server_names = list(servers.keys())

        self.default_server_var = tk.StringVar(value=self.prefs["default_server"])
        self.server_combo = ttk.Combobox(
            server_row,
            textvariable=self.default_server_var,
            values=server_names,
            state="readonly" if self.auto_connect_var.get() else "disabled",
            width=25,
        )
        self.server_combo.pack(side=tk.LEFT, padx=10)

        # Admin-only Scheduling Section
        if self.shell and self.shell.is_admin():
            admin_frame = ttk.LabelFrame(scrollable_frame, text="Admin Scheduling Defaults", padding=15)
            admin_frame.pack(fill=tk.X, pady=(0, 10), padx=10)

            ttk.Label(
                admin_frame,
                text="These settings control default values in Admin Schedule creation",
                foreground="gray",
                font=("TkDefaultFont", 9),
            ).pack(anchor=tk.W, pady=(0, 10))

            # Cadence
            cadence_row = ttk.Frame(admin_frame)
            cadence_row.pack(fill=tk.X, pady=5)

            ttk.Label(cadence_row, text="Default cadence:").pack(side=tk.LEFT)
            self.admin_cadence_var = tk.StringVar(value=self.prefs["admin_schedule_cadence"])
            cadence_combo = ttk.Combobox(
                cadence_row,
                textvariable=self.admin_cadence_var,
                values=["1 week", "2 weeks"],
                state="readonly",
                width=12,
            )
            cadence_combo.pack(side=tk.LEFT, padx=10)

            # Start hour
            start_hour_row = ttk.Frame(admin_frame)
            start_hour_row.pack(fill=tk.X, pady=5)

            ttk.Label(start_hour_row, text="Default start time:").pack(side=tk.LEFT)
            self.admin_start_hour_var = tk.IntVar(value=self.prefs["admin_schedule_start_hour"])
            start_hour_spin = ttk.Spinbox(
                start_hour_row, from_=0, to=23, width=5, textvariable=self.admin_start_hour_var, format="%02.0f"
            )
            start_hour_spin.pack(side=tk.LEFT, padx=10)
            ttk.Label(start_hour_row, text=":00 UTC").pack(side=tk.LEFT)

            # End hour
            end_hour_row = ttk.Frame(admin_frame)
            end_hour_row.pack(fill=tk.X, pady=5)

            ttk.Label(end_hour_row, text="Default end time:").pack(side=tk.LEFT)
            self.admin_end_hour_var = tk.IntVar(value=self.prefs["admin_schedule_end_hour"])
            end_hour_spin = ttk.Spinbox(
                end_hour_row, from_=0, to=23, width=5, textvariable=self.admin_end_hour_var, format="%02.0f"
            )
            end_hour_spin.pack(side=tk.LEFT, padx=10)
            ttk.Label(end_hour_row, text=":00 UTC").pack(side=tk.LEFT)

        # Buttons
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=(20, 10), padx=10)

        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=5)

    def _toggle_auto_connect(self):
        """Enable/disable default server combo based on auto-connect"""
        if self.auto_connect_var.get():
            self.server_combo.config(state="readonly")
        else:
            self.server_combo.config(state="disabled")

    def _save(self):
        """Save preferences to config"""
        new_prefs = {
            "auto_refresh_interval": self.interval_var.get(),
            "auto_refresh_my_hosts": self.auto_refresh_my_hosts_var.get(),
            "confirm_terminate": self.confirm_terminate_var.get(),
            "confirm_release": self.confirm_release_var.get(),
            "confirm_exit": self.confirm_exit_var.get(),
            "remember_window": self.remember_window_var.get(),
            "auto_connect": self.auto_connect_var.get(),
            "default_server": self.default_server_var.get(),
            "font_size": self.font_size_var.get(),
        }

        # Add admin settings if user is admin
        if self.shell and self.shell.is_admin():
            new_prefs["admin_schedule_cadence"] = self.admin_cadence_var.get()
            new_prefs["admin_schedule_start_hour"] = self.admin_start_hour_var.get()
            new_prefs["admin_schedule_end_hour"] = self.admin_end_hour_var.get()

        # Save to config file
        if self.config and hasattr(self.config, "config_data"):
            self.config.config_data["gui_preferences"] = new_prefs
            self.config.save_config()

        self.result = new_prefs
        self.destroy()

    def _cancel(self):
        """Cancel without saving"""
        self.result = None
        self.destroy()

    def get_result(self):
        """Get the result (None if cancelled)"""
        return self.result
