"""Admin schedule view - for schedule management with explicit dates (refactored)"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timezone

from quads_client.gui.widgets.base import BaseAdminView, ScrolledTreeview, FormDialog
from quads_client.gui.widgets.date_picker import DatePickerDialog, get_next_sunday_22utc, get_two_weeks_sunday_22utc


class AdminScheduleView(BaseAdminView):
    """View for admin schedule management"""

    def __init__(self, parent, shell):
        super().__init__(parent, shell, "Schedule Management (Admin)", requires_admin=True)
        self._create_ui()

    def _create_ui(self):
        """Create the UI"""
        # Header with buttons
        self.create_header(
            [
                ("➕ New Schedule", self._create_schedule),
                ("🔄 Refresh", self._load_schedules),
            ]
        )

        # Filter frame
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        ttk.Label(filter_frame, text="Filter by Cloud:").pack(side=tk.LEFT, padx=(0, 5))
        self.cloud_filter = ttk.Entry(filter_frame, width=20)
        self.cloud_filter.pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="Host:").pack(side=tk.LEFT, padx=(20, 5))
        self.host_filter = ttk.Entry(filter_frame, width=20)
        self.host_filter.pack(side=tk.LEFT, padx=5)

        ttk.Button(filter_frame, text="Apply", command=self._load_schedules).pack(side=tk.LEFT, padx=10)

        # Content frame with scrolled treeview
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        columns = ("id", "cloud", "description", "owner", "validated")
        column_configs = {
            "id": ("ID", 80),
            "cloud": ("Cloud", 120),
            "description": ("Description", 300),
            "owner": ("Owner", 150),
            "validated": ("Validated", 100),
        }

        self.tree = ScrolledTreeview(content_frame, columns, column_configs)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Action buttons
        self.create_action_bar(
            [
                ("Extend", self._extend_assignment),
                ("Shrink", self._shrink_assignment),
                ("Terminate", self._terminate_assignment),
            ]
        )

        # Status label
        self.create_status_label()

        # Initial load
        self._load_schedules()

    def _get_free_clouds(self):
        """Get list of free clouds (no active or future assignment)"""
        try:
            # utilize quads-lib endpoint: get_free_clouds()
            return [cloud.get("name") for cloud in (self.shell.connection.api.get_free_clouds() or [])]
        except Exception as e:
            self.update_status(f"Error getting free clouds: {e}")
            return []

    def _load_schedules(self):
        """Load all active assignments from server"""
        from quads_client.utils import extract_assignment_id, extract_cloud_name

        def load_data():
            filters = {"active": True}
            if self.cloud_filter.get().strip():
                filters["cloud"] = self.cloud_filter.get().strip()
            # Load all active assignments (admin sees everything)
            return self.shell.connection.api.filter_assignments(filters)

        self.tree.clear()

        def on_loaded(assignments):
            if not assignments:
                return

            for assignment in assignments:
                if isinstance(assignment, dict):
                    assignment_id = extract_assignment_id(assignment)
                    cloud_name = extract_cloud_name(assignment)
                    description = assignment.get("description", "No description")
                    owner = assignment.get("owner", "N/A")
                    validated = "✓" if assignment.get("validated") else "○"

                    self.tree.insert(
                        "",
                        tk.END,
                        values=(assignment_id, cloud_name, description, owner, validated),
                    )

        self.safe_load_data_async(load_data, on_loaded, success_message="Showing {count} assignment(s)")

    def _validate_hosts_availability(self, hostnames, start_date, end_date):
        """Validate hosts are available for the specified date range

        Uses is_available() API which checks:
        - Host exists
        - Host is not broken or retired
        - No schedule conflicts in the date range

        Args:
            hostnames: List of hostname strings
            start_date: Start date string (YYYY-MM-DD HH:MM)
            end_date: End date string (YYYY-MM-DD HH:MM)

        Returns:
            tuple: (is_valid, error_list) where error_list contains hostname:reason pairs
        """
        from quads_client.commands.schedule import parse_flexible_datetime

        errors = []

        try:
            start_iso = parse_flexible_datetime(start_date).isoformat()[:-3]
            end_iso = parse_flexible_datetime(end_date).isoformat()[:-3]
        except ValueError as e:
            return (False, [str(e)])

        for hostname in hostnames:
            hostname = hostname.strip()
            if not hostname:
                continue

            try:
                is_available = self.shell.connection.api.is_available(hostname, {"start": start_iso, "end": end_iso})

                if not is_available:
                    errors.append(f"{hostname}: Not available for {start_date} to {end_date}")

            except Exception as e:
                errors.append(f"{hostname}: Error checking availability ({str(e)})")

        return (len(errors) == 0, errors)

    def _create_schedule(self, prefill_hosts=None):
        """Create new schedule with admin parameters

        Args:
            prefill_hosts: Optional comma-separated string of hostnames to pre-fill
        """
        dialog = self.create_simple_dialog("Create Schedule (Admin)", "650x700")
        dialog.resizable(True, True)  # Make it resizable so users can adjust if needed

        ttk.Label(
            dialog,
            text="Create Schedule with Explicit Dates",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(pady=10, padx=20)

        # Create scrollable container for form
        # Get background color from ttk style to match theme
        style = ttk.Style()
        bg_color = style.lookup("TFrame", "background")

        canvas = tk.Canvas(dialog, highlightthickness=0, background=bg_color, borderwidth=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)

        # Enable mouse wheel scrolling (use bind_all but unbind on dialog close)
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

        form_frame = ttk.Frame(scrollable_frame)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Load admin preferences
        prefs = {}
        if self.shell.config and hasattr(self.shell.config, "config_data"):
            prefs = self.shell.config.config_data.get("gui_preferences", {})

        cadence = prefs.get("admin_schedule_cadence", "2 weeks")
        start_hour = prefs.get("admin_schedule_start_hour", 22)
        end_hour = prefs.get("admin_schedule_end_hour", 22)

        # Cloud - populate with free clouds
        ttk.Label(form_frame, text="Cloud:").grid(row=0, column=0, sticky=tk.W, pady=5)
        cloud_frame = ttk.Frame(form_frame)
        cloud_frame.grid(row=0, column=1, pady=5, sticky=tk.W)

        free_clouds = self._get_free_clouds()
        cloud_var = tk.StringVar()
        cloud_combo = ttk.Combobox(cloud_frame, textvariable=cloud_var, values=free_clouds, width=27, state="readonly")
        cloud_combo.pack(side=tk.LEFT)

        if free_clouds:
            cloud_combo.current(0)  # Select first free cloud by default

        ttk.Label(cloud_frame, text=f"({len(free_clouds)} free)", font=("TkDefaultFont", 8), foreground="gray").pack(
            side=tk.LEFT, padx=5
        )

        # Hosts selection mode
        ttk.Label(form_frame, text="Hosts:").grid(row=1, column=0, sticky=tk.W, pady=5)
        mode_var = tk.StringVar(value="list")

        mode_frame = ttk.Frame(form_frame)
        mode_frame.grid(row=1, column=1, pady=5, sticky=tk.W)

        ttk.Radiobutton(mode_frame, text="Comma-separated", variable=mode_var, value="list").pack(anchor=tk.W)
        hosts_entry = ttk.Entry(mode_frame, width=40)
        hosts_entry.pack(fill=tk.X, pady=2)

        # Pre-fill hosts if provided
        if prefill_hosts:
            hosts_entry.insert(0, prefill_hosts)

        ttk.Radiobutton(mode_frame, text="From file", variable=mode_var, value="file").pack(anchor=tk.W, pady=(5, 0))
        file_frame = ttk.Frame(mode_frame)
        file_frame.pack(fill=tk.X, pady=2)
        file_entry = ttk.Entry(file_frame, width=30)
        file_entry.pack(side=tk.LEFT)

        def browse_file():
            filename = filedialog.askopenfilename(parent=dialog)
            if filename:
                file_entry.delete(0, tk.END)
                file_entry.insert(0, filename)

        ttk.Button(file_frame, text="Browse", command=browse_file).pack(side=tk.LEFT, padx=5)

        # Dates with smart defaults (using admin preferences)
        default_start = get_next_sunday_22utc(start_hour)
        default_end = get_two_weeks_sunday_22utc(default_start, cadence, end_hour)

        ttk.Label(form_frame, text="Start Date:").grid(row=2, column=0, sticky=tk.W, pady=5)
        start_frame = ttk.Frame(form_frame)
        start_frame.grid(row=2, column=1, pady=5, sticky=tk.W)
        start_entry = ttk.Entry(start_frame, width=25)
        start_entry.pack(side=tk.LEFT)
        start_entry.insert(0, default_start.strftime("%Y-%m-%d %H:%M"))

        def pick_start_date():
            # Pass end date as range_end to show the selection range
            picker = DatePickerDialog(
                dialog,
                "Select Start Date",
                start_entry.get(),
                range_start=start_entry.get(),
                range_end=end_entry.get(),
            )
            dialog.wait_window(picker)
            result = picker.get_result()
            if result:
                start_entry.delete(0, tk.END)
                start_entry.insert(0, result)
                # Update end date using admin preferences
                new_end = get_two_weeks_sunday_22utc(result, cadence, end_hour)
                end_entry.delete(0, tk.END)
                end_entry.insert(0, new_end.strftime("%Y-%m-%d %H:%M"))

        def set_start_now():
            now = datetime.now(timezone.utc)
            start_entry.delete(0, tk.END)
            start_entry.insert(0, now.strftime("%Y-%m-%d %H:%M"))
            # Also update end date using admin preferences
            new_end = get_two_weeks_sunday_22utc(now, cadence, end_hour)
            end_entry.delete(0, tk.END)
            end_entry.insert(0, new_end.strftime("%Y-%m-%d %H:%M"))

        ttk.Button(start_frame, text="📅", command=pick_start_date, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(start_frame, text="Now", command=set_start_now, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(start_frame, text="(UTC)", font=("TkDefaultFont", 8)).pack(side=tk.LEFT, padx=5)

        ttk.Label(form_frame, text="End Date:").grid(row=3, column=0, sticky=tk.W, pady=5)
        end_frame = ttk.Frame(form_frame)
        end_frame.grid(row=3, column=1, pady=5, sticky=tk.W)
        end_entry = ttk.Entry(end_frame, width=25)
        end_entry.pack(side=tk.LEFT)
        end_entry.insert(0, default_end.strftime("%Y-%m-%d %H:%M"))

        def pick_end_date():
            # Pass start date as range_start to show the selection range
            picker = DatePickerDialog(
                dialog, "Select End Date", end_entry.get(), range_start=start_entry.get(), range_end=end_entry.get()
            )
            dialog.wait_window(picker)
            result = picker.get_result()
            if result:
                end_entry.delete(0, tk.END)
                end_entry.insert(0, result)

        ttk.Button(end_frame, text="📅", command=pick_end_date, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(end_frame, text="(UTC)", font=("TkDefaultFont", 8)).pack(side=tk.LEFT, padx=5)

        # Assignment parameters
        desc_entry = FormDialog.create_labeled_entry(form_frame, "Description:", 4, 40)
        owner_entry = FormDialog.create_labeled_entry(form_frame, "Cloud Owner:", 5, 30)
        ticket_entry = FormDialog.create_labeled_entry(form_frame, "Ticket ID:", 6, 30)
        cc_entry = FormDialog.create_labeled_entry(form_frame, "CC Users:", 7, 40)

        # VLAN dropdown - populate with free VLANs only
        ttk.Label(form_frame, text="VLAN:").grid(row=8, column=0, sticky=tk.W, pady=5)
        free_vlans = self.shell.get_available_vlans()
        if free_vlans:
            vlan_values = ["Select VLAN..."] + free_vlans
            vlan_combo = ttk.Combobox(form_frame, values=vlan_values, width=17, state="readonly")
            vlan_combo.set("Select VLAN...")
        else:
            vlan_combo = ttk.Combobox(form_frame, values=["No free VLANs available"], width=17, state="readonly")
            vlan_combo.set("No free VLANs available")
        vlan_combo.grid(row=8, column=1, pady=5, sticky=tk.W)

        ttk.Label(form_frame, text="QinQ:").grid(row=9, column=0, sticky=tk.W, pady=5)
        qinq_combo = ttk.Combobox(form_frame, values=["0", "1"], width=17, state="readonly")
        qinq_combo.set("0")
        qinq_combo.grid(row=9, column=1, pady=5, sticky=tk.W)

        # OS dropdown - populate with available OS options
        ttk.Label(form_frame, text="OS:").grid(row=10, column=0, sticky=tk.W, pady=5)
        available_os = self.shell.get_available_os()
        if available_os:
            os_values = ["Select OS..."] + available_os
            os_combo = ttk.Combobox(form_frame, values=os_values, width=17, state="readonly")
            os_combo.set("Select OS...")
        else:
            os_combo = ttk.Combobox(form_frame, values=["No OS options available"], width=17, state="readonly")
            os_combo.set("No OS options available")
        os_combo.grid(row=10, column=1, pady=5, sticky=tk.W)

        nowipe_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(form_frame, text="No wipe", variable=nowipe_var).grid(row=11, column=1, sticky=tk.W, pady=5)

        def on_create():
            cloud = cloud_var.get().strip()
            start = start_entry.get().strip()
            end = end_entry.get().strip()

            if not cloud or not start or not end:
                messagebox.showerror("Error", "Cloud, start, and end dates are required", parent=dialog)
                return

            # Build host argument and validate
            hostname_list = []
            if mode_var.get() == "list":
                hosts = hosts_entry.get().strip()
                if not hosts:
                    messagebox.showerror("Error", "Host list is required", parent=dialog)
                    return

                # Parse comma-separated hostnames
                hostname_list = [h.strip() for h in hosts.split(",") if h.strip()]

            else:
                hosts_file = file_entry.get().strip()
                if not hosts_file:
                    messagebox.showerror("Error", "Host file is required", parent=dialog)
                    return

                # Read hostnames from file
                try:
                    with open(hosts_file, "r") as f:
                        hostname_list = [line.strip() for line in f if line.strip()]

                    if not hostname_list:
                        messagebox.showerror("Error", f"No hostnames found in file: {hosts_file}", parent=dialog)
                        return

                except FileNotFoundError:
                    messagebox.showerror("Error", f"File not found: {hosts_file}", parent=dialog)
                    return
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to read file: {e}", parent=dialog)
                    return

                hosts = f"host-list {hosts_file}"

            # Validate hostnames before scheduling
            is_valid, errors = self._validate_hosts_availability(hostname_list, start, end)

            if not is_valid:
                error_msg = "The following hosts are invalid or unavailable:\n\n"
                error_msg += "\n".join(f"  • {err}" for err in errors)
                error_msg += "\n\nPlease fix these issues before scheduling."
                messagebox.showerror("Invalid Hostnames", error_msg, parent=dialog)
                return

            # Build host argument for CLI
            if mode_var.get() == "list":
                hosts = hosts_entry.get().strip()
            else:
                hosts = f"host-list {file_entry.get().strip()}"

            # Build args string (dates must be quoted for shlex.split)
            args = f'{cloud} {hosts} "{start}" "{end}"'

            if desc_entry.get().strip():
                safe_desc = desc_entry.get().strip().replace('"', '\\"')
                args += f' description "{safe_desc}"'
            if owner_entry.get().strip():
                args += f" cloud-owner {owner_entry.get().strip()}"
            if ticket_entry.get().strip():
                args += f" cloud-ticket {ticket_entry.get().strip()}"
            if cc_entry.get().strip():
                safe_cc = cc_entry.get().strip().replace('"', '\\"')
                args += f' cc-users "{safe_cc}"'
            # Only add VLAN if a valid one is selected
            vlan = vlan_combo.get()
            if vlan and vlan != "Select VLAN..." and vlan != "No free VLANs available":
                args += f" vlan {vlan}"
            if qinq_combo.get():
                args += f" qinq {qinq_combo.get()}"
            # Only add OS if a valid one is selected
            os_val = os_combo.get()
            if os_val and os_val != "Select OS..." and os_val != "No OS options available":
                safe_os = os_val.replace('"', '\\"')
                args += f' os "{safe_os}"'
            if nowipe_var.get():
                args += " nowipe"

            self.safe_execute(
                lambda: self.shell.schedule_commands.cmd_schedule_admin(args),
                "Schedule created successfully",
                "Create Schedule Failed",
                self._load_schedules,
            )
            dialog.destroy()

        # Button row inside scrollable frame
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Create", command=on_create).pack(side=tk.LEFT, padx=5)

    def _extend_assignment(self):
        """Extend selected assignment (admin only)"""
        _, values = self.get_selected_item("Please select an assignment to extend")
        if not values:
            return

        assignment_id = values[0]
        cloud_name = values[1]

        # Create dialog for extend options
        dialog = self.create_simple_dialog(f"Extend Assignment #{assignment_id}", "350x200")

        ttk.Label(
            dialog, text=f"Extend assignment #{assignment_id} ({cloud_name})", font=("TkDefaultFont", 10, "bold")
        ).pack(pady=10)

        # Weeks input
        input_frame = ttk.Frame(dialog)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="Number of weeks:").pack(side=tk.LEFT, padx=5)
        weeks_var = tk.StringVar(value="2")
        weeks_entry = ttk.Entry(input_frame, textvariable=weeks_var, width=10)
        weeks_entry.pack(side=tk.LEFT, padx=5)
        weeks_entry.focus()

        def on_extend():
            weeks_str = weeks_var.get().strip()

            # Validate integer
            try:
                weeks = int(weeks_str)
                if weeks <= 0:
                    messagebox.showerror("Invalid Input", "Weeks must be a positive integer", parent=dialog)
                    return
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid integer for weeks", parent=dialog)
                return

            dialog.destroy()

            # Confirm action
            if not self.confirm_action(
                "Confirm Extend",
                f"Extend assignment #{assignment_id} ({cloud_name}) by {weeks} week(s)?\n\n"
                "This will extend ALL schedules in this assignment.",
            ):
                return

            # Call extend command with cloud name
            self.safe_execute(
                lambda: self.shell.schedule_commands.cmd_extend(f"{cloud_name} weeks {weeks}"),
                f"Extended assignment #{assignment_id} by {weeks} week(s)",
                "Extend Failed",
                self._load_schedules,
            )

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Extend", command=on_extend).pack(side=tk.LEFT, padx=5)

    def _shrink_assignment(self):
        """Shrink selected assignment (admin only)"""
        _, values = self.get_selected_item("Please select an assignment to shrink")
        if not values:
            return

        assignment_id = values[0]
        cloud_name = values[1]

        # Create dialog for shrink options
        dialog = self.create_simple_dialog(f"Shrink Assignment #{assignment_id}", "400x250")

        ttk.Label(
            dialog, text=f"Shrink assignment #{assignment_id} ({cloud_name})", font=("TkDefaultFont", 10, "bold")
        ).pack(pady=10)

        # Mode selection
        mode_frame = ttk.Frame(dialog)
        mode_frame.pack(pady=10)

        mode_var = tk.StringVar(value="weeks")

        ttk.Radiobutton(mode_frame, text="By weeks:", variable=mode_var, value="weeks").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=2
        )
        weeks_var = tk.StringVar(value="1")
        weeks_entry = ttk.Entry(mode_frame, textvariable=weeks_var, width=10)
        weeks_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Radiobutton(mode_frame, text="By days:", variable=mode_var, value="days").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=2
        )
        days_var = tk.StringVar(value="7")
        days_entry = ttk.Entry(mode_frame, textvariable=days_var, width=10)
        days_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Radiobutton(mode_frame, text="End now (terminate)", variable=mode_var, value="now").grid(
            row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2
        )

        def on_shrink():
            mode = mode_var.get()

            if mode == "weeks":
                value_str = weeks_var.get().strip()
                unit = "week(s)"
                try:
                    value = int(value_str)
                    if value <= 0:
                        messagebox.showerror("Invalid Input", "Weeks must be a positive integer", parent=dialog)
                        return
                except ValueError:
                    messagebox.showerror("Invalid Input", "Please enter a valid integer for weeks", parent=dialog)
                    return
            elif mode == "days":
                value_str = days_var.get().strip()
                unit = "day(s)"
                try:
                    value = int(value_str)
                    if value <= 0:
                        messagebox.showerror("Invalid Input", "Days must be a positive integer", parent=dialog)
                        return
                except ValueError:
                    messagebox.showerror("Invalid Input", "Please enter a valid integer for days", parent=dialog)
                    return
            else:  # now
                value = 0
                value_str = "0"
                unit = "(end now)"

            dialog.destroy()

            # Confirm action
            if mode == "now":
                confirm_msg = (
                    f"End assignment #{assignment_id} ({cloud_name}) NOW?\n\n"
                    "This will terminate the assignment immediately."
                )
            else:
                confirm_msg = (
                    f"Shrink assignment #{assignment_id} ({cloud_name}) by {value_str} {unit}?\n\n"
                    "This will shrink ALL schedules in this assignment."
                )

            if not self.confirm_action("Confirm Shrink", confirm_msg):
                return

            # Build command based on mode
            if mode == "weeks":
                cmd_args = f"{cloud_name} weeks {value}"
            elif mode == "days":
                if value % 7 != 0:
                    messagebox.showwarning(
                        "Days Not Evenly Divisible",
                        f"{value} days is not evenly divisible by 7.\n\n"
                        f"The shrink command works in whole weeks.\n"
                        f"{value} days = {value // 7} full week(s) + {value % 7} day(s).\n\n"
                        f"Shrinking by {value // 7} week(s) instead.",
                    )
                weeks_value = max(1, value // 7)
                cmd_args = f"{cloud_name} weeks {weeks_value}"
            else:  # now
                # Terminate the assignment
                self.safe_execute(
                    lambda: self.shell.user_commands.cmd_terminate(str(assignment_id)),
                    f"Assignment #{assignment_id} terminated",
                    "Terminate Failed",
                    self._load_schedules,
                )
                return

            # Call shrink command
            self.safe_execute(
                lambda: self.shell.schedule_commands.cmd_shrink(cmd_args),
                f"Shrunk assignment #{assignment_id} by {value_str} {unit}",
                "Shrink Failed",
                self._load_schedules,
            )

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Shrink", command=on_shrink).pack(side=tk.LEFT, padx=5)

    def _terminate_assignment(self):
        """Terminate selected assignment"""
        _, values = self.get_selected_item("Please select an assignment to terminate")
        if not values:
            return

        assignment_id = values[0]

        if not self.confirm_action(
            "Confirm Termination",
            f"Are you sure you want to terminate assignment #{assignment_id}?\n\n"
            "This will release all hosts in this assignment.",
        ):
            return

        self.safe_execute(
            lambda: self.shell.user_commands.cmd_terminate(str(assignment_id)),
            f"Assignment #{assignment_id} terminated\n\n"
            "Note: It may take a few moments for the termination to complete.",
            "Termination Failed",
            self._load_schedules,
        )

    def refresh(self):
        """Public method to refresh the view"""
        self._load_schedules()
