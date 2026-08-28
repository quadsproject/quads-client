"""Clouds view - admin cloud management (refactored with DRY principles)"""

import tkinter as tk
from tkinter import ttk, messagebox

from quads_client.gui.widgets.base import BaseAdminView, ScrolledTreeview, FormDialog


class CloudsView(BaseAdminView):
    """View for managing clouds (admin only)"""

    def __init__(self, parent, shell):
        super().__init__(parent, shell, "Cloud Management", requires_admin=True)
        self._create_ui()

    def _create_ui(self):
        """Create the UI"""
        # Header with buttons
        self.create_header(
            [
                ("➕ Create Cloud", self._create_cloud),
                ("🔄 Refresh", self._load_clouds),
            ]
        )

        # Content frame with scrolled treeview
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        columns = ("cloud", "assignment", "owner", "description", "vlan", "wipe")
        column_configs = {
            "cloud": ("Cloud", 100),
            "assignment": ("Assignment", 100),
            "owner": ("Owner", 120),
            "description": ("Description", 300),
            "vlan": ("VLAN", 80),
            "wipe": ("Wipe", 60),
        }

        self.tree = ScrolledTreeview(content_frame, columns, column_configs)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Action buttons
        self.create_action_bar(
            [
                ("View Details", self._view_details),
                ("Modify Cloud", self._modify_cloud),
                ("Terminate", self._terminate_assignment),
            ]
        )

        # Status label
        self.create_status_label()

        # Initial load
        self._load_clouds()

    def _load_clouds(self):
        """Load clouds from server"""

        def load_data():
            clouds = self.shell.connection.api.get_clouds()
            if not clouds:
                return []

            active_assignments = {}
            try:
                all_assignments = self.shell.connection.api.filter_assignments({"active": True})
                if all_assignments:
                    for assignment in all_assignments:
                        if isinstance(assignment, dict):
                            cloud_obj = assignment.get("cloud", {})
                            cname = cloud_obj.get("name") if isinstance(cloud_obj, dict) else str(cloud_obj)
                            if cname:
                                active_assignments[cname] = assignment
            except Exception:
                pass

            return (clouds, active_assignments)

        self.tree.clear()

        def on_loaded(data):
            if not data:
                return

            clouds, active_assignments = data

            for cloud in clouds:
                cloud_name = cloud.get("name", "")
                assignment_id = "-"
                owner = "-"
                description = "-"
                vlan = "-"
                wipe = "No"

                assignment = active_assignments.get(cloud_name)
                if assignment and isinstance(assignment, dict):
                    assignment_id = str(assignment.get("id", "-"))
                    owner = assignment.get("owner", "-") or "-"
                    desc_full = assignment.get("description", "-") or "-"
                    description = desc_full[:40] if len(desc_full) > 40 else desc_full
                    wipe = "Yes" if assignment.get("wipe", False) else "No"

                    vlan_obj = assignment.get("vlan")
                    if isinstance(vlan_obj, dict):
                        vlan = str(vlan_obj.get("vlan_id", "-"))
                    elif vlan_obj:
                        vlan = str(vlan_obj)

                self.tree.insert(
                    "",
                    tk.END,
                    values=(cloud_name, assignment_id, owner, description, vlan, wipe),
                )

            self.update_status(f"Showing {len(clouds)} cloud(s) | Last updated: Just now")

        self.safe_load_data_async(load_data, on_loaded)

    def _create_cloud(self):
        """Create a new cloud"""
        dialog = self.create_simple_dialog("Create Cloud", "400x150")

        ttk.Label(dialog, text="Cloud Name:").pack(pady=10, padx=20, anchor=tk.W)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(padx=20, fill=tk.X)
        name_entry.focus()

        def on_create():
            cloud_name = name_entry.get().strip()
            if not cloud_name:
                messagebox.showerror("Error", "Cloud name is required", parent=dialog)
                return

            self.safe_execute(
                lambda: self.shell.cloud_commands.cmd_cloud_create(cloud_name),
                f"Cloud '{cloud_name}' created",
                "Create Cloud Failed",
                self._load_clouds,
            )
            dialog.destroy()

        FormDialog.create_button_row(
            dialog,
            [
                ("Cancel", dialog.destroy),
                ("Create", on_create),
            ],
        )

    def _terminate_assignment(self):
        """Terminate assignment for selected cloud"""
        _, values = self.get_selected_item("Please select a cloud to terminate")
        if not values:
            return

        cloud_name = values[0]
        assignment_id = values[1]

        # Check if cloud has an active assignment
        if assignment_id == "-":
            messagebox.showwarning("No Assignment", f"Cloud '{cloud_name}' has no active assignment to terminate")
            return

        if not self.confirm_action(
            "Confirm Termination",
            f"Are you sure you want to terminate assignment #{assignment_id} for cloud '{cloud_name}'?\n\n"
            "This will release all hosts in this assignment.",
        ):
            return

        self.safe_execute(
            lambda: self.shell.user_commands.cmd_terminate(str(assignment_id)),
            f"Assignment #{assignment_id} terminated\n\n" "Note: It may take a few moments to complete.",
            "Termination Failed",
            self._load_clouds,
        )

    def _modify_cloud(self):
        """Modify selected cloud assignment"""
        _, values = self.get_selected_item("Please select a cloud to modify")
        if not values:
            return

        cloud_name = values[0]
        dialog = self.create_simple_dialog(f"Modify Cloud: {cloud_name}", "500x450")

        ttk.Label(
            dialog,
            text=f"Modify assignment attributes for {cloud_name}",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(pady=10, padx=20)

        form_frame = ttk.Frame(dialog)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Create form fields
        desc_entry = FormDialog.create_labeled_entry(form_frame, "Description:", 0, 40)
        owner_entry = FormDialog.create_labeled_entry(form_frame, "Cloud Owner:", 1, 40)
        ticket_entry = FormDialog.create_labeled_entry(form_frame, "Ticket ID:", 2, 40)
        cc_entry = FormDialog.create_labeled_entry(form_frame, "CC Users:", 3, 40)
        vlan_entry = FormDialog.create_labeled_entry(form_frame, "VLAN ID:", 4, 40)
        ttk.Label(form_frame, text="OS:").grid(row=5, column=0, sticky=tk.W, pady=5)
        available_os = self.shell.get_available_os()
        os_values = [""] + available_os if available_os else [""]
        os_combo = ttk.Combobox(form_frame, values=os_values, width=38, state="readonly")
        os_combo.set("")
        os_combo.grid(row=5, column=1, pady=5, sticky=tk.W)

        ttk.Label(form_frame, text="QinQ:").grid(row=6, column=0, sticky=tk.W, pady=5)
        qinq_combo = ttk.Combobox(form_frame, values=["", "0", "1"], width=38, state="readonly")
        qinq_combo.set("")
        qinq_combo.grid(row=6, column=1, pady=5, sticky=tk.W)

        wipe_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(form_frame, text="Enable wipe", variable=wipe_var).grid(row=7, column=1, sticky=tk.W, pady=5)

        def on_modify():
            args = cloud_name

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
            if vlan_entry.get().strip():
                args += f" vlan {vlan_entry.get().strip()}"
            os_val = os_combo.get()
            if os_val:
                safe_os = os_val.replace('"', '\\"')
                args += f' os "{safe_os}"'
            qinq_val = qinq_combo.get()
            if qinq_val:
                args += f" qinq {qinq_val}"
            if wipe_var.get():
                args += " wipe"

            if args == cloud_name:
                messagebox.showwarning("No Changes", "No modifications specified", parent=dialog)
                return

            self.safe_execute(
                lambda: self.shell.cloud_commands.cmd_mod_cloud(args),
                f"Cloud '{cloud_name}' modified",
                "Modify Cloud Failed",
                self._load_clouds,
            )
            dialog.destroy()

        FormDialog.create_button_row(
            dialog,
            [
                ("Cancel", dialog.destroy),
                ("Modify", on_modify),
            ],
        )

    def _get_cloud_hosts(self, cloud_name):
        """Get hostnames for a cloud.

        cloud01 is the spare pool — hosts live there without schedules,
        so we use filter_hosts. Other clouds use get_current_schedules.
        """
        hostnames = []

        if cloud_name == "cloud01":
            hosts = self.shell.connection.api.filter_hosts({"cloud": "cloud01"})
            if hosts and isinstance(hosts, list):
                for host in hosts:
                    if isinstance(host, dict):
                        name = host.get("name", "")
                    elif isinstance(host, str):
                        name = host
                    else:
                        name = getattr(host, "name", "")
                    if name and name not in hostnames:
                        hostnames.append(name)
        else:
            current_schedules = self.shell.connection.api.get_current_schedules({"cloud": cloud_name})
            if current_schedules:
                for schedule in current_schedules:
                    host = schedule.get("host")
                    if host:
                        hostname = host.get("name") if isinstance(host, dict) else host
                        if hostname and hostname not in hostnames:
                            hostnames.append(hostname)

        hostnames.sort()
        return hostnames

    def _view_details(self):
        """View hosts assigned to selected cloud in a scrollable popup"""
        _, values = self.get_selected_item("Please select a cloud to view")
        if not values:
            return

        cloud_name = values[0]

        try:
            hostnames = self._get_cloud_hosts(cloud_name)

            theme = self.shell.gui_app.theme_manager
            bg = theme.get_color("text_bg")
            fg = theme.get_color("text_fg")
            select_bg = theme.get_color("accent")

            dialog = tk.Toplevel(self)
            dialog.title(f"Hosts in {cloud_name}")
            dialog.geometry("700x500")
            dialog.minsize(700, 500)
            dialog.transient(self.winfo_toplevel())
            dialog.grab_set()
            theme.configure_toplevel(dialog)

            count = len(hostnames)
            count_text = f"{count} host(s) assigned" if count > 0 else "No hosts currently assigned"
            ttk.Label(dialog, text=count_text, font=("TkDefaultFont", 10, "bold")).pack(
                padx=20, pady=(15, 10), anchor=tk.W
            )

            list_frame = ttk.Frame(dialog)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            listbox = tk.Listbox(
                list_frame,
                selectmode=tk.EXTENDED,
                yscrollcommand=scrollbar.set,
                font=("TkFixedFont", 10),
                bg=bg,
                fg=fg,
                selectbackground=select_bg,
                selectforeground="#ffffff",
                highlightthickness=0,
                borderwidth=1,
                relief=tk.SOLID,
            )
            scrollbar.config(command=listbox.yview)
            listbox.pack(fill=tk.BOTH, expand=True)

            for hostname in hostnames:
                listbox.insert(tk.END, hostname)

            def select_all(event=None):
                listbox.select_set(0, tk.END)
                return "break"

            def copy_selected(event=None):
                selection = listbox.curselection()
                if not selection:
                    return
                text = "\n".join(listbox.get(i) for i in selection)
                dialog.clipboard_clear()
                dialog.clipboard_append(text)
                return "break"

            listbox.bind("<Control-a>", select_all)
            listbox.bind("<Control-c>", copy_selected)

            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

            ttk.Button(button_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(
                button_frame,
                text="Deselect All",
                command=lambda: listbox.selection_clear(0, tk.END),
            ).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Copy Selected", command=copy_selected).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)

        except Exception as e:
            from quads_client.gui.widgets.dialogs import show_error_dialog

            show_error_dialog(self, "Failed to get cloud details", str(e))

    def refresh(self):
        """Public method to refresh the view"""
        self._load_clouds()
