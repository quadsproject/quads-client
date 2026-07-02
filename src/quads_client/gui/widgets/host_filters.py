"""Reusable host metadata filter widget for Available and Schedule views"""

import threading
import tkinter as tk
from tkinter import ttk

from quads_client.gui.widgets.date_picker import DatePickerDialog


class HostFilterFrame(ttk.Frame):
    """Reusable filter panel for host metadata search.

    Provides primary filters (Model, RAM, Start/End dates) and a collapsible
    advanced section (Disk, NIC, GPU filters). Used in both Available and
    Schedule views for DRY.
    """

    DISK_TYPES = ["All", "nvme", "ssd", "sata"]

    def __init__(self, parent, shell, show_dates=True):
        super().__init__(parent)
        self.shell = shell
        self.show_dates = show_dates
        self._advanced_visible = False
        self._create_ui()

    def _create_ui(self):
        # Row 1: Model + RAM
        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row1, text="Model:").pack(side=tk.LEFT, padx=(0, 5))
        models = ["All"]
        self.model_combo = ttk.Combobox(row1, values=models, width=15, state="readonly")
        self.model_combo.set("All")
        self.model_combo.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row1, text="RAM (GB):").pack(side=tk.LEFT, padx=(0, 5))
        self.ram_entry = ttk.Entry(row1, width=10)
        self.ram_entry.pack(side=tk.LEFT)

        # Row 2: Start/End dates (optional)
        if self.show_dates:
            row2 = ttk.Frame(self)
            row2.pack(fill=tk.X, pady=(0, 5))

            ttk.Label(row2, text="Start Date:").pack(side=tk.LEFT, padx=(0, 5))
            self.start_entry = ttk.Entry(row2, width=20)
            self.start_entry.pack(side=tk.LEFT)
            ttk.Button(row2, text="\U0001f4c5", command=self._pick_start_date, width=3).pack(side=tk.LEFT, padx=2)

            ttk.Label(row2, text="End Date:").pack(side=tk.LEFT, padx=(15, 5))
            self.end_entry = ttk.Entry(row2, width=20)
            self.end_entry.pack(side=tk.LEFT)
            ttk.Button(row2, text="\U0001f4c5", command=self._pick_end_date, width=3).pack(side=tk.LEFT, padx=2)

        # Row 3: Advanced toggle
        row3 = ttk.Frame(self)
        row3.pack(fill=tk.X, pady=(0, 5))

        self._adv_toggle_btn = ttk.Button(row3, text="▶ Advanced Filters", command=self._toggle_advanced)
        self._adv_toggle_btn.pack(side=tk.LEFT)

        # Advanced section (initially hidden)
        self._advanced_frame = ttk.LabelFrame(self, text="Advanced Filters", padding=10)

        adv_row1 = ttk.Frame(self._advanced_frame)
        adv_row1.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(adv_row1, text="Disk Type:").pack(side=tk.LEFT, padx=(0, 5))
        self.disk_type_combo = ttk.Combobox(adv_row1, values=self.DISK_TYPES, width=10, state="readonly")
        self.disk_type_combo.set("All")
        self.disk_type_combo.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(adv_row1, text="Disk Size (GB):").pack(side=tk.LEFT, padx=(0, 5))
        self.disk_size_entry = ttk.Entry(adv_row1, width=10)
        self.disk_size_entry.pack(side=tk.LEFT)

        adv_row2 = ttk.Frame(self._advanced_frame)
        adv_row2.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(adv_row2, text="Disk Count:").pack(side=tk.LEFT, padx=(0, 5))
        self.disk_count_entry = ttk.Entry(adv_row2, width=10)
        self.disk_count_entry.pack(side=tk.LEFT)

        adv_row3 = ttk.Frame(self._advanced_frame)
        adv_row3.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(adv_row3, text="NIC Vendor:").pack(side=tk.LEFT, padx=(0, 5))
        nic_vendors = ["All"]
        self.nic_vendor_combo = ttk.Combobox(adv_row3, values=nic_vendors, width=20, state="readonly")
        self.nic_vendor_combo.set("All")
        self.nic_vendor_combo.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(adv_row3, text="NIC Speed (Gbps):").pack(side=tk.LEFT, padx=(0, 5))
        self.nic_speed_entry = ttk.Entry(adv_row3, width=10)
        self.nic_speed_entry.pack(side=tk.LEFT)

        adv_row4 = ttk.Frame(self._advanced_frame)
        adv_row4.pack(fill=tk.X, pady=(0, 5))

        self.gpu_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(adv_row4, text="Has GPU", variable=self.gpu_var).pack(side=tk.LEFT)

    def _toggle_advanced(self):
        if self._advanced_visible:
            self._advanced_frame.pack_forget()
            self._adv_toggle_btn.config(text="▶ Advanced Filters")
        else:
            self._advanced_frame.pack(fill=tk.X, pady=(0, 5))
            self._adv_toggle_btn.config(text="▼ Advanced Filters")
        self._advanced_visible = not self._advanced_visible

    def _pick_start_date(self):
        range_end = self.end_entry.get() if hasattr(self, "end_entry") else None
        picker = DatePickerDialog(
            self.winfo_toplevel(),
            "Select Start Date",
            self.start_entry.get() or None,
            range_start=self.start_entry.get() or None,
            range_end=range_end,
        )
        self.winfo_toplevel().wait_window(picker)
        result = picker.get_result()
        if result:
            self.start_entry.delete(0, tk.END)
            self.start_entry.insert(0, result)

    def _pick_end_date(self):
        range_start = self.start_entry.get() if hasattr(self, "start_entry") else None
        picker = DatePickerDialog(
            self.winfo_toplevel(),
            "Select End Date",
            self.end_entry.get() or None,
            range_start=range_start,
            range_end=self.end_entry.get() or None,
        )
        self.winfo_toplevel().wait_window(picker)
        result = picker.get_result()
        if result:
            self.end_entry.delete(0, tk.END)
            self.end_entry.insert(0, result)

    def get_filters(self):
        """Return active filters as a dict with API filter keys.

        Returns:
            dict: Filter keys mapped to values, ready for get_available_hosts_data().
                  Empty/default values are omitted.
        """
        filters = {}

        model = self.model_combo.get()
        if model and model != "All":
            filters["model"] = model.upper()

        ram = self.ram_entry.get().strip()
        if ram:
            try:
                filters["memory__gte"] = int(ram) * 1024
            except ValueError:
                pass

        if self.show_dates:
            start = self.start_entry.get().strip()
            if start:
                filters["start"] = start.split()[0]

            end = self.end_entry.get().strip()
            if end:
                filters["end"] = end.split()[0]

        if self._advanced_visible or True:
            disk_type = self.disk_type_combo.get()
            if disk_type and disk_type != "All":
                filters["disks.disk_type"] = disk_type

            disk_size = self.disk_size_entry.get().strip()
            if disk_size:
                try:
                    filters["disks.size_gb__gte"] = int(disk_size)
                except ValueError:
                    pass

            disk_count = self.disk_count_entry.get().strip()
            if disk_count:
                try:
                    filters["disks.count__gte"] = int(disk_count)
                except ValueError:
                    pass

            nic_vendor = self.nic_vendor_combo.get()
            if nic_vendor and nic_vendor != "All":
                filters["interfaces.vendor"] = nic_vendor

            nic_speed = self.nic_speed_entry.get().strip()
            if nic_speed:
                try:
                    filters["interfaces.speed__gte"] = int(nic_speed)
                except ValueError:
                    pass

            if self.gpu_var.get():
                filters["processors.processor_type"] = "GPU"

        return filters

    def clear_filters(self):
        """Reset all filters to defaults."""
        self.model_combo.set("All")
        self.ram_entry.delete(0, tk.END)

        if self.show_dates:
            self.start_entry.delete(0, tk.END)
            self.end_entry.delete(0, tk.END)

        self.disk_type_combo.set("All")
        self.disk_size_entry.delete(0, tk.END)
        self.disk_count_entry.delete(0, tk.END)
        self.nic_vendor_combo.set("All")
        self.nic_speed_entry.delete(0, tk.END)
        self.gpu_var.set(False)

    def populate_metadata_async(self):
        """Fetch models and NIC vendors in a background thread, then update combos."""

        def _fetch():
            models = self.shell.get_available_models()
            nic_vendors = self.shell.get_available_nic_vendors()
            return models, nic_vendors

        def _apply(models, nic_vendors):
            current_model = self.model_combo.get()
            self.model_combo.config(values=["All"] + models)
            if current_model not in (["All"] + models):
                self.model_combo.set("All")

            current_vendor = self.nic_vendor_combo.get()
            self.nic_vendor_combo.config(values=["All"] + nic_vendors)
            if current_vendor not in (["All"] + nic_vendors):
                self.nic_vendor_combo.set("All")

        def _worker():
            try:
                models, nic_vendors = _fetch()
                self.after(0, lambda: _apply(models, nic_vendors))
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()
