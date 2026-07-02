"""Schedule view for self-service scheduling (SSM users)"""

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from quads_client.gui.widgets.dialogs import show_error_dialog
from quads_client.gui.widgets.host_filters import HostFilterFrame


class ScheduleView(ttk.Frame):
    """View for scheduling hosts (SSM mode)"""

    def __init__(self, parent, shell):
        super().__init__(parent)
        self.shell = shell
        self._validating = False  # Prevent validation loops

        self._create_ui()

    def _create_ui(self):
        """Create the UI"""
        # Check if authenticated - if not, show login prompt
        if not self.shell.is_authenticated():
            self._show_login_prompt()
            return

        title_label = ttk.Label(self, text="Schedule Hosts", font=("TkDefaultFont", 14, "bold"))
        title_label.pack(pady=20, padx=20, anchor=tk.W)

        # Create a container for canvas and scrollbar
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        # Create a canvas with scrollbar for main content
        # Use ttk style lookup to get proper background color for current theme
        style = ttk.Style()
        bg_color = style.lookup("TFrame", "background")
        canvas = tk.Canvas(container, highlightthickness=0, bg=bg_color)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        def _on_frame_configure(event):
            # Update scroll region when content changes
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", _on_frame_configure)

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Bind canvas width changes to update window width
        def _configure_canvas_window(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _configure_canvas_window)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Enable mouse wheel scrolling (guarded to avoid errors if canvas is destroyed)
        def _on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_scroll_up(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(-1, "units")

        def _on_scroll_down(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(1, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_scroll_up)
        canvas.bind_all("<Button-5>", _on_scroll_down)

        main_frame = scrollable_frame

        ttk.Label(
            main_frame,
            text="How many hosts do you need?",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(anchor=tk.W, pady=(0, 10))

        self.mode_var = tk.StringVar(value="count")

        mode_frame = ttk.LabelFrame(main_frame, text="Selection Mode", padding=10)
        mode_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Radiobutton(
            mode_frame,
            text="Specific number of hosts",
            variable=self.mode_var,
            value="count",
            command=self._on_mode_changed,
        ).grid(row=0, column=0, sticky=tk.W, pady=5)

        count_frame = ttk.Frame(mode_frame)
        count_frame.grid(row=0, column=1, padx=20, sticky=tk.W)
        ttk.Label(count_frame, text="Count:").pack(side=tk.LEFT)
        self.count_spinbox = ttk.Spinbox(count_frame, from_=1, to=50, width=10)
        self.count_spinbox.set(1)
        self.count_spinbox.pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            mode_frame,
            text="Specific hostnames",
            variable=self.mode_var,
            value="hosts",
            command=self._on_mode_changed,
        ).grid(row=1, column=0, sticky=tk.W, pady=5)

        self.hosts_entry = ttk.Entry(mode_frame, width=40, state=tk.DISABLED)
        self.hosts_entry.grid(row=1, column=1, padx=20, sticky=tk.W)
        self.hosts_entry.insert(0, "host01.example.com,host02.example.com")

        ttk.Radiobutton(
            mode_frame,
            text="Host list from file",
            variable=self.mode_var,
            value="file",
            command=self._on_mode_changed,
        ).grid(row=2, column=0, sticky=tk.W, pady=5)

        file_frame = ttk.Frame(mode_frame)
        file_frame.grid(row=2, column=1, padx=20, sticky=tk.W)
        self.file_entry = ttk.Entry(file_frame, width=30, state=tk.DISABLED)
        self.file_entry.pack(side=tk.LEFT)
        self.browse_button = ttk.Button(file_frame, text="Browse...", command=self._browse_file, state=tk.DISABLED)
        self.browse_button.pack(side=tk.LEFT, padx=5)

        ttk.Label(main_frame, text="Description:", font=("TkDefaultFont", 10)).pack(anchor=tk.W, pady=(10, 5))
        self.description_entry = ttk.Entry(main_frame, width=50)
        self.description_entry.pack(fill=tk.X, pady=(0, 10))
        self.description_entry.insert(0, "Development testing environment")

        # Browse available hosts section
        self.browse_available_var = tk.BooleanVar(value=False)
        browse_check = ttk.Checkbutton(
            main_frame,
            text="Browse available hosts ▼",
            variable=self.browse_available_var,
            command=self._toggle_browse_available,
        )
        browse_check.pack(anchor=tk.W, pady=(0, 10))

        self.available_frame = ttk.LabelFrame(main_frame, text="Available Hosts", padding=10)

        available_controls = ttk.Frame(self.available_frame)
        available_controls.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(available_controls, text="Load Available Hosts", command=self._load_available_hosts).pack(
            side=tk.LEFT, padx=(0, 10)
        )

        self.available_status = ttk.Label(available_controls, text="", font=("TkDefaultFont", 8), foreground="gray")
        self.available_status.pack(side=tk.LEFT, padx=10)

        # Scrollable list of available hosts
        avail_list_frame = ttk.Frame(self.available_frame)
        avail_list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(avail_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.available_listbox = tk.Listbox(
            avail_list_frame, selectmode=tk.MULTIPLE, height=6, yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.available_listbox.yview)
        self.available_listbox.pack(fill=tk.BOTH, expand=True)

        avail_buttons = ttk.Frame(self.available_frame)
        avail_buttons.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(avail_buttons, text="Use Selected Hosts", command=self._use_selected_hosts).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(avail_buttons, text="Clear", command=lambda: self.available_listbox.delete(0, tk.END)).pack(
            side=tk.LEFT, padx=5
        )

        # Advanced options row with checkboxes
        advanced_row = ttk.Frame(main_frame)
        advanced_row.pack(fill=tk.X, pady=(0, 10))

        self.advanced_var = tk.BooleanVar(value=False)
        advanced_check = ttk.Checkbutton(
            advanced_row,
            text="Show advanced options ▼",
            variable=self.advanced_var,
            command=self._toggle_advanced,
        )
        advanced_check.pack(side=tk.LEFT)

        # Checkboxes to the right of advanced options
        options_right = ttk.Frame(advanced_row)
        options_right.pack(side=tk.RIGHT)

        # No Wipe checkbox
        self.nowipe_var = tk.BooleanVar(value=False)
        nowipe_check = ttk.Checkbutton(
            options_right, text="No Wipe", variable=self.nowipe_var, command=self._update_preview
        )
        nowipe_check.pack(side=tk.LEFT, padx=5)

        # VLAN checkbox
        self.use_vlan_var = tk.BooleanVar(value=False)
        vlan_check = ttk.Checkbutton(
            options_right, text="Use VLAN", variable=self.use_vlan_var, command=self._toggle_vlan
        )
        vlan_check.pack(side=tk.LEFT, padx=5)

        # VLAN dropdown (initially disabled, populated async)
        vlan_values = ["Select VLAN..."]
        self.vlan_combo = ttk.Combobox(options_right, values=vlan_values, width=12, state="disabled")
        self.vlan_combo.set("Select VLAN...")
        self.vlan_combo.pack(side=tk.LEFT, padx=5)
        self.vlan_combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())

        # QinQ checkbox
        self.use_qinq_var = tk.BooleanVar(value=False)
        qinq_check = ttk.Checkbutton(
            options_right, text="Use QinQ", variable=self.use_qinq_var, command=self._toggle_qinq
        )
        qinq_check.pack(side=tk.LEFT, padx=5)

        # QinQ dropdown (initially disabled, default 0)
        self.qinq_combo = ttk.Combobox(options_right, values=["0", "1"], width=5, state="disabled")
        self.qinq_combo.set("0")
        self.qinq_combo.pack(side=tk.LEFT, padx=5)
        self.qinq_combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())

        # OS checkbox
        self.use_os_var = tk.BooleanVar(value=False)
        os_check = ttk.Checkbutton(options_right, text="Use OS", variable=self.use_os_var, command=self._toggle_os)
        os_check.pack(side=tk.LEFT, padx=5)

        # OS dropdown (initially disabled, populated async)
        os_values = ["Select OS..."]
        self.os_combo = ttk.Combobox(options_right, values=os_values, width=18, state="disabled")
        self.os_combo.set("Select OS...")
        self.os_combo.pack(side=tk.LEFT, padx=5)
        self.os_combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())

        self.advanced_frame = ttk.LabelFrame(main_frame, text="Advanced Options", padding=10)

        self.host_filter_frame = HostFilterFrame(self.advanced_frame, self.shell, show_dates=True)
        self.host_filter_frame.pack(fill=tk.X)

        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding=10)
        preview_frame.pack(fill=tk.X, pady=(20, 20))

        # Preview text with theme-aware colors
        self.preview_text = tk.Text(
            preview_frame,
            height=5,
            width=60,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg=self.shell.gui_app.theme_manager.get_color("text_bg"),
            fg=self.shell.gui_app.theme_manager.get_color("text_fg"),
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        self._update_preview()

        # Result/Status box (initially hidden)
        self.result_frame = ttk.LabelFrame(main_frame, text="Scheduling Result", padding=10)

        # Result text with theme-aware success color
        self.result_text = tk.Text(
            self.result_frame,
            height=4,
            width=60,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg=self.shell.gui_app.theme_manager.get_color("text_bg"),
            fg=self.shell.gui_app.theme_manager.get_color("success"),
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 20))

        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Schedule Now", command=self._schedule).pack(side=tk.RIGHT, padx=5)

        self.after(100, self._load_metadata_async)

    def _load_metadata_async(self):
        """Populate VLAN, OS, model, and NIC vendor dropdowns in background."""

        def _fetch():
            vlans = self.shell.get_available_vlans()
            os_list = self.shell.get_available_os()
            return vlans, os_list

        def _apply(vlans, os_list):
            if vlans:
                self.vlan_combo.config(values=["Select VLAN..."] + vlans)
            if os_list:
                self.os_combo.config(values=["Select OS..."] + os_list)

        def _worker():
            try:
                vlans, os_list = _fetch()
                self.after(0, lambda: _apply(vlans, os_list))
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

        if hasattr(self, "host_filter_frame"):
            self.host_filter_frame.populate_metadata_async()

    def _on_mode_changed(self):
        """Handle mode change"""
        mode = self.mode_var.get()

        self.count_spinbox.config(state=tk.NORMAL if mode == "count" else tk.DISABLED)
        self.hosts_entry.config(state=tk.NORMAL if mode == "hosts" else tk.DISABLED)
        self.file_entry.config(state=tk.NORMAL if mode == "file" else tk.DISABLED)
        self.browse_button.config(state=tk.NORMAL if mode == "file" else tk.DISABLED)

        self._update_preview()

    def _toggle_browse_available(self):
        """Toggle browse available hosts section"""
        if self.browse_available_var.get():
            self.available_frame.pack(fill=tk.X, pady=(0, 10))
        else:
            self.available_frame.pack_forget()

    def _toggle_advanced(self):
        """Toggle advanced options"""
        if self.advanced_var.get():
            self.advanced_frame.pack(fill=tk.X, pady=(0, 20))
        else:
            self.advanced_frame.pack_forget()

        self._update_preview()

    def _toggle_vlan(self):
        """Toggle VLAN dropdown based on checkbox"""
        if self.use_vlan_var.get():
            # Refresh VLAN list from server when enabled
            free_vlans = self.shell.get_available_vlans()
            if free_vlans:
                vlan_values = ["Select VLAN..."] + free_vlans
                self.vlan_combo.config(values=vlan_values, state="readonly")
            else:
                self.vlan_combo.config(values=["No free VLANs available"], state="readonly")
                self.vlan_combo.set("No free VLANs available")
        else:
            self.vlan_combo.config(state="disabled")
            self.vlan_combo.set("Select VLAN...")

        self._update_preview()

    def _toggle_qinq(self):
        """Toggle QinQ dropdown based on checkbox"""
        if self.use_qinq_var.get():
            self.qinq_combo.config(state="readonly")
        else:
            self.qinq_combo.config(state="disabled")
            self.qinq_combo.set("0")

        self._update_preview()

    def _toggle_os(self):
        """Toggle OS dropdown based on checkbox"""
        if self.use_os_var.get():
            available_os = self.shell.get_available_os()
            if available_os:
                os_values = ["Select OS..."] + available_os
                self.os_combo.config(values=os_values, state="readonly")
            else:
                self.os_combo.config(values=["No OS options available"], state="readonly")
                self.os_combo.set("No OS options available")
        else:
            self.os_combo.config(state="disabled")
            self.os_combo.set("Select OS...")

        self._update_preview()

    def _load_available_hosts(self):
        """Load available hosts and display in listbox, using filters from advanced options"""
        if not self.shell.is_authenticated():
            self.available_status.config(text="Not connected")
            return

        self.available_status.config(text="Loading...")
        self.update()

        filters = {}
        if hasattr(self, "host_filter_frame"):
            filters = self.host_filter_frame.get_filters()

        def _fetch():
            return self.shell.get_available_hosts_data(**filters)

        def _on_loaded(hosts):
            self.available_listbox.delete(0, tk.END)
            if not hosts:
                self.available_listbox.insert(tk.END, "No available hosts found")
                self.available_status.config(text="No hosts found")
                return
            for host in hosts:
                self.available_listbox.insert(tk.END, host["name"])
            self.available_status.config(text=f"Loaded {len(hosts)} host(s)")

        def _worker():
            try:
                result = _fetch()
                self.after(0, lambda: _on_loaded(result))
            except Exception as exc:
                msg = str(exc)
                self.after(0, lambda: self.available_status.config(text=f"Error: {msg}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _use_selected_hosts(self):
        """Use selected hosts from listbox"""
        selection_indices = self.available_listbox.curselection()
        if not selection_indices:
            messagebox.showwarning("No Selection", "Please select hosts from the list")
            return

        # Get selected hostnames
        hostnames = []
        for idx in selection_indices:
            hostname = self.available_listbox.get(idx).strip()
            # Only add if it looks like a hostname (contains a dot)
            if hostname and "." in hostname:
                hostnames.append(hostname)

        if not hostnames:
            messagebox.showinfo(
                "Info",
                "No valid hostnames selected.\n\n"
                "Note: The available hosts view is currently informational.\n"
                "Please manually enter hostnames in the 'Specific hostnames' field.",
            )
            return

        # Validate selected hostnames before using them
        is_valid, errors = self._validate_hostnames(hostnames)

        if not is_valid:
            error_msg = "The following selected hosts are invalid:\n\n"
            error_msg += "\n".join(f"  • {err}" for err in errors)
            error_msg += "\n\nPlease select different hosts or contact an admin."
            messagebox.showerror("Invalid Hostnames", error_msg)
            return

        # Switch to "Specific hostnames" mode and populate
        self.mode_var.set("hosts")
        self._on_mode_changed()

        # Join hostnames and set in entry
        self.hosts_entry.delete(0, tk.END)
        self.hosts_entry.insert(0, ",".join(hostnames))

        messagebox.showinfo("Success", f"Added {len(hostnames)} host(s) to the schedule")
        self._update_preview()

    def _browse_file(self):
        """Browse for host list file"""
        filename = filedialog.askopenfilename(
            title="Select Host List File",
            filetypes=[("All files", "*.*"), ("Text files", "*.txt")],
        )
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
            self._update_preview()

    def _update_preview(self):
        """Update preview text"""
        mode = self.mode_var.get()

        preview = ""
        if mode == "count":
            count = self.count_spinbox.get()
            preview += f"• {count} hosts will be automatically selected\n"
        elif mode == "hosts":
            hosts = self.hosts_entry.get()
            host_list = [h.strip() for h in hosts.split(",") if h.strip()]
            preview += f"• {len(host_list)} specific hosts\n"
        elif mode == "file":
            file_path = self.file_entry.get()
            preview += f"• Hosts from file: {file_path or 'Not selected'}\n"

        preview += "• Cloud will be auto-assigned\n"
        preview += "• Duration: 5 days or until Sunday 21:00 UTC\n"
        preview += "• Assignment will be activated immediately\n"

        # Show VLAN if enabled
        if self.use_vlan_var.get():
            vlan = self.vlan_combo.get()
            if vlan and vlan != "Select VLAN..." and vlan != "No free VLANs available":
                preview += f"• VLAN: {vlan}\n"

        # Show QinQ if enabled
        if self.use_qinq_var.get():
            qinq = self.qinq_combo.get()
            if qinq:
                preview += f"• QinQ: {qinq}\n"

        # Show OS if enabled
        if self.use_os_var.get():
            os_val = self.os_combo.get()
            if os_val and os_val != "Select OS..." and os_val != "No OS options available":
                preview += f"• OS: {os_val}\n"

        # Show nowipe if enabled
        if self.nowipe_var.get():
            preview += "• No wipe (data will be preserved)\n"

        if self.advanced_var.get() and hasattr(self, "host_filter_frame"):
            active_filters = self.host_filter_frame.get_filters()
            if "model" in active_filters:
                preview += f"• Filter: Model {active_filters['model']}\n"
            if "memory__gte" in active_filters:
                ram_gb = active_filters["memory__gte"] // 1024
                preview += f"• Filter: RAM >= {ram_gb} GB\n"
            if "disks.disk_type" in active_filters:
                preview += f"• Filter: Disk Type {active_filters['disks.disk_type']}\n"
            if "disks.size_gb__gte" in active_filters:
                preview += f"• Filter: Disk Size >= {active_filters['disks.size_gb__gte']} GB\n"
            if "disks.count__gte" in active_filters:
                preview += f"• Filter: Disk Count >= {active_filters['disks.count__gte']}\n"
            if "interfaces.vendor" in active_filters:
                preview += f"• Filter: NIC Vendor {active_filters['interfaces.vendor']}\n"
            if "interfaces.speed__gte" in active_filters:
                preview += f"• Filter: NIC Speed >= {active_filters['interfaces.speed__gte']} Gbps\n"
            if "processors.vendor__like" in active_filters:
                preview += "• Filter: Has GPU\n"
            if "start" in active_filters and "end" in active_filters:
                preview += f"• Filter: Available {active_filters['start']} to {active_filters['end']}\n"

        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", preview)
        self.preview_text.config(state=tk.DISABLED)

    def _validate_hostnames(self, hostnames):
        """Validate hostnames exist and are eligible for SSM scheduling

        Args:
            hostnames: List of hostname strings

        Returns:
            tuple: (is_valid, error_list) where error_list contains hostname:reason pairs
        """
        errors = []

        for hostname in hostnames:
            hostname = hostname.strip()
            if not hostname:
                continue

            try:
                # Check if host exists
                host = self.shell.connection.api.get_host(hostname)

                if not host:
                    errors.append(f"{hostname}: Host not found (typo?)")
                    continue

                # Check if host is broken or retired
                if host.get("broken"):
                    errors.append(f"{hostname}: Host is marked as broken")
                    continue

                if host.get("retired"):
                    errors.append(f"{hostname}: Host is retired")
                    continue

                # Check if host can self-schedule
                if not host.get("can_self_schedule"):
                    errors.append(f"{hostname}: Not enabled for self-scheduling")
                    continue

            except Exception as e:
                errors.append(f"{hostname}: Error checking host ({str(e)})")

        return (len(errors) == 0, errors)

    def _schedule(self):
        """Perform the scheduling"""
        if not self.shell.is_authenticated():
            messagebox.showerror("Error", "You must be logged in to schedule hosts")
            return

        description = self.description_entry.get().strip()
        if not description:
            messagebox.showerror("Error", "Description is required")
            return

        mode = self.mode_var.get()
        args = ""

        # Validate hostnames for "hosts" and "file" modes (pre-flight validation)
        if mode == "hosts":
            hosts = self.hosts_entry.get().strip()
            if not hosts:
                messagebox.showerror("Error", "Hostnames are required")
                return

            # Parse and validate hostnames
            hostname_list = [h.strip() for h in hosts.split(",") if h.strip()]
            is_valid, errors = self._validate_hostnames(hostname_list)

            if not is_valid:
                error_msg = "The following hostnames are invalid:\n\n"
                error_msg += "\n".join(f"  • {err}" for err in errors)
                error_msg += "\n\nPlease fix these issues before scheduling."
                messagebox.showerror("Invalid Hostnames", error_msg)
                return

            args = hosts

        elif mode == "file":
            file_path = self.file_entry.get().strip()
            if not file_path:
                messagebox.showerror("Error", "Please select a host list file")
                return

            # Read and validate hostnames from file
            try:
                with open(file_path, "r") as f:
                    hostname_list = [line.strip() for line in f if line.strip()]

                if not hostname_list:
                    messagebox.showerror("Error", f"No hostnames found in file: {file_path}")
                    return

                is_valid, errors = self._validate_hostnames(hostname_list)

                if not is_valid:
                    error_msg = f"The following hostnames in {file_path} are invalid:\n\n"
                    error_msg += "\n".join(f"  • {err}" for err in errors)
                    error_msg += "\n\nPlease fix these issues before scheduling."
                    messagebox.showerror("Invalid Hostnames", error_msg)
                    return

            except FileNotFoundError:
                messagebox.showerror("Error", f"File not found: {file_path}")
                return
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read file: {e}")
                return

            args = f"host-list {file_path}"

        elif mode == "count":
            count = self.count_spinbox.get()
            args = f"{count}"

        safe_description = description.replace('"', '\\"')
        args += f' description "{safe_description}"'

        # Add VLAN if enabled
        if self.use_vlan_var.get():
            vlan = self.vlan_combo.get()
            if vlan and vlan != "Select VLAN..." and vlan != "No free VLANs available":
                args += f" vlan {vlan}"

        # Add QinQ if enabled
        if self.use_qinq_var.get():
            qinq = self.qinq_combo.get()
            if qinq:
                args += f" qinq {qinq}"

        # Add OS if enabled
        if self.use_os_var.get():
            os_val = self.os_combo.get()
            if os_val and os_val != "Select OS..." and os_val != "No OS options available":
                safe_os = os_val.replace('"', '\\"')
                args += f' os "{safe_os}"'

        # Add nowipe if enabled
        if self.nowipe_var.get():
            args += " nowipe"

        # Add advanced hardware filters for count mode
        if self.advanced_var.get() and hasattr(self, "host_filter_frame"):
            active_filters = self.host_filter_frame.get_filters()
            if "model" in active_filters:
                args += f" model {active_filters['model']}"
            if "memory__gte" in active_filters:
                ram_gb = active_filters["memory__gte"] // 1024
                args += f" ram {ram_gb}"
            if "disks.disk_type" in active_filters:
                args += f" disk-type {active_filters['disks.disk_type']}"
            if "disks.size_gb__gte" in active_filters:
                args += f" disk-size {active_filters['disks.size_gb__gte']}"
            if "disks.count__gte" in active_filters:
                args += f" disk-count {active_filters['disks.count__gte']}"
            if "interfaces.vendor" in active_filters:
                args += f" nic-vendor {active_filters['interfaces.vendor']}"
            if "interfaces.speed__gte" in active_filters:
                args += f" nic-speed {active_filters['interfaces.speed__gte']}"

        try:
            # Capture output from schedule command
            self.shell._capture_output = True
            self.shell._captured_messages = []

            self.shell.user_commands.cmd_schedule(args)

            # Display captured messages in result box
            if self.shell._captured_messages:
                result_text = "\n".join([msg[1] for msg in self.shell._captured_messages])
                self.result_text.config(state=tk.NORMAL)
                self.result_text.delete("1.0", tk.END)
                self.result_text.insert("1.0", result_text)
                self.result_text.config(state=tk.DISABLED)

                # Show result frame
                self.result_frame.pack(fill=tk.X, pady=(10, 20))

            # Check for errors in captured output before declaring success
            errors = [msg for level, msg in self.shell._captured_messages if level == "error"]
            if errors:
                error_msg = "\n".join(errors)
                messagebox.showerror("Scheduling Failed", error_msg)
            else:
                messagebox.showinfo(
                    "Success",
                    "Hosts scheduled successfully!\n\n"
                    "View your assignments in the 'My Hosts' or 'Assignments' tab.",
                )

        except Exception as e:
            import traceback

            details = traceback.format_exc()
            show_error_dialog(self, "Scheduling Failed", str(e), details)
        finally:
            self.shell._capture_output = False

    def _reset_form(self):
        """Reset the form to defaults"""
        self.mode_var.set("count")
        self.count_spinbox.set(1)
        self.description_entry.delete(0, tk.END)
        self.description_entry.insert(0, "Development testing environment")
        if hasattr(self, "host_filter_frame"):
            self.host_filter_frame.clear_filters()
        self.nowipe_var.set(False)
        self.use_vlan_var.set(False)
        self.vlan_combo.set("Select VLAN...")
        self.vlan_combo.config(state="disabled")
        self.use_qinq_var.set(False)
        self.qinq_combo.set("0")
        self.qinq_combo.config(state="disabled")
        self.use_os_var.set(False)
        self.os_combo.set("Select OS...")
        self.os_combo.config(state="disabled")
        self.advanced_var.set(False)
        self.advanced_frame.pack_forget()
        self._on_mode_changed()

    def _cancel(self):
        """Cancel scheduling"""
        self._reset_form()

    def _show_login_prompt(self):
        """Show login prompt when not authenticated"""
        # Clear any existing widgets
        for widget in self.winfo_children():
            widget.destroy()

        # Center frame
        center_frame = ttk.Frame(self)
        center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ttk.Label(center_frame, text="Please login to schedule hosts", font=("TkDefaultFont", 12)).pack(pady=(0, 20))

        ttk.Button(center_frame, text="Login", command=self._auto_login).pack()

    def _auto_login(self):
        """Auto-login using centralized server selection logic"""
        from quads_client.gui.widgets.dialogs import show_error_dialog

        target_server = self.shell.get_auto_login_server()

        if target_server:
            success, error = self.shell.connect_to_server(target_server)
            if success:
                self.refresh()
            else:
                show_error_dialog(self, "Login Failed", f"Failed to connect to {target_server}", error or "")
        else:
            self.shell.gui_app._show_servers_view()

    def _get_preferences(self):
        """Get GUI preferences from config"""
        if self.shell.config and hasattr(self.shell.config, "config_data"):
            return self.shell.config.config_data.get("gui_preferences", {})
        return {}

    def refresh(self):
        """Public method to refresh the view"""
        # Check if auth status changed - rebuild UI if needed
        if not self.shell.is_authenticated():
            # Clear and show login prompt
            for widget in self.winfo_children():
                widget.destroy()
            self._show_login_prompt()
        elif hasattr(self, "mode_var"):
            # Full UI is built (mode_var only exists after _create_ui completes)
            self._update_preview()
        else:
            # Need to rebuild full UI
            for widget in self.winfo_children():
                widget.destroy()
            self._create_ui()

    def refresh_theme(self):
        """Update colors when theme changes"""
        if not hasattr(self, "preview_text"):
            return
        self.preview_text.config(
            bg=self.shell.gui_app.theme_manager.get_color("text_bg"),
            fg=self.shell.gui_app.theme_manager.get_color("text_fg"),
        )
        if hasattr(self, "result_text"):
            self.result_text.config(
                bg=self.shell.gui_app.theme_manager.get_color("text_bg"),
                fg=self.shell.gui_app.theme_manager.get_color("success"),
            )
