from tabulate import tabulate

from quads_client.error_handler import require_connection
from quads_client.utils import extract_host_field, get_available_hosts_filter


class AvailableCommands:
    def __init__(self, shell):
        self.shell = shell

    def _require_connection(self):
        return require_connection(self.shell)

    def cmd_ls_available(self, args):
        """List available hosts.
        Usage: ls-available [start YYYY-MM-DD] [end YYYY-MM-DD] [model MODEL] [ram GB]
                            [gpu-vendor VENDOR] [gpu-product PRODUCT]
                            [disk-size GB] [disk-type TYPE] [disk-count N]
                            [interfaces N] [nic-vendor VENDOR] [nic-speed GBPS]
        """
        if not self._require_connection():
            return

        # Handle help request
        if args.strip() in ("?", "-h", "--help"):
            self.shell.poutput("Usage: ls-available [OPTIONS]")
            self.shell.poutput("\nList available hosts with optional hardware filtering.")
            self.shell.poutput("\nOptions:")
            self.shell.poutput("  start YYYY-MM-DD        Start date for availability")
            self.shell.poutput("  end YYYY-MM-DD          End date for availability")
            self.shell.poutput("  model MODEL             Filter by server model (e.g., r640)")
            self.shell.poutput("  ram GB                  Minimum RAM in GB")
            self.shell.poutput("  gpu-vendor VENDOR       GPU vendor (e.g., 'NVIDIA Corporation')")
            self.shell.poutput("  gpu-product PRODUCT     GPU model (e.g., 'Tesla V100')")
            self.shell.poutput("  disk-size GB            Minimum disk size in GB")
            self.shell.poutput("  disk-type TYPE          Disk type (nvme, ssd, sata)")
            self.shell.poutput("  disk-count N            Minimum number of disks")
            self.shell.poutput("  interfaces N            Minimum number of network interfaces")
            self.shell.poutput("  nic-vendor VENDOR       NIC vendor (e.g., 'Intel', 'Mellanox')")
            self.shell.poutput("  nic-speed GBPS          Minimum NIC speed in Gbps")
            self.shell.poutput("\nExamples:")
            self.shell.poutput("  ls-available model r640 ram 256")
            self.shell.poutput("  ls-available gpu-vendor 'NVIDIA Corporation' gpu-product 'Tesla V100'")
            self.shell.poutput("  ls-available nic-vendor Mellanox nic-speed 25")
            self.shell.poutput("  ls-available start 2026-06-01 end 2026-06-15")
            return

        parts = args.split()
        filters = {}

        i = 0
        while i < len(parts):
            if parts[i] == "start" and i + 1 < len(parts):
                filters["start"] = parts[i + 1]
                i += 2
            elif parts[i] == "end" and i + 1 < len(parts):
                filters["end"] = parts[i + 1]
                i += 2
            elif parts[i] == "model" and i + 1 < len(parts):
                # Models are stored as uppercase in QUADS
                filters["model"] = parts[i + 1].upper()
                i += 2
            elif parts[i] == "ram" and i + 1 < len(parts):
                filters["memory__gte"] = int(parts[i + 1]) * 1024
                i += 2
            elif parts[i] == "gpu-vendor" and i + 1 < len(parts):
                filters["processors.vendor"] = parts[i + 1]
                i += 2
            elif parts[i] == "gpu-product" and i + 1 < len(parts):
                filters["processors.product"] = parts[i + 1]
                i += 2
            elif parts[i] == "disk-size" and i + 1 < len(parts):
                filters["disks.size_gb__gte"] = int(parts[i + 1])
                i += 2
            elif parts[i] == "disk-type" and i + 1 < len(parts):
                filters["disks.disk_type"] = parts[i + 1]
                i += 2
            elif parts[i] == "disk-count" and i + 1 < len(parts):
                filters["disks.count__gte"] = int(parts[i + 1])
                i += 2
            elif parts[i] == "interfaces" and i + 1 < len(parts):
                filters["interfaces.count__gte"] = int(parts[i + 1])
                i += 2
            elif parts[i] == "nic-vendor" and i + 1 < len(parts):
                filters["interfaces.vendor"] = parts[i + 1]
                i += 2
            elif parts[i] == "nic-speed" and i + 1 < len(parts):
                filters["interfaces.speed__gte"] = int(parts[i + 1])
                i += 2
            else:
                known_keywords = [
                    "start",
                    "end",
                    "model",
                    "ram",
                    "gpu-vendor",
                    "gpu-product",
                    "disk-size",
                    "disk-type",
                    "disk-count",
                    "interfaces",
                    "nic-vendor",
                    "nic-speed",
                ]
                if parts[i] in known_keywords:
                    self.shell.perror(f"Filter '{parts[i]}' requires a value")
                    return
                i += 1

        try:
            # Get available hosts using filter_hosts for cloud01 (available pool)
            # This returns full host objects with all fields populated
            # Extract start/end for schedule checking, remove from filter_hosts params
            start_date = filters.pop("start", None)
            end_date = filters.pop("end", None)

            host_filters = get_available_hosts_filter(**filters)

            if not (self.shell.connection and self.shell.connection.is_admin):
                host_filters["can_self_schedule"] = True

            hosts = self.shell.connection.api.filter_hosts(host_filters)

            # Check if API returned an error
            if isinstance(hosts, str):
                self.shell.perror(f"API error: {hosts}")
                return

            if not hosts:
                self.shell.poutput("No available hosts found")
                return

            # Ensure hosts is a list
            if not isinstance(hosts, list):
                self.shell.perror(f"Unexpected response type: {type(hosts)}")
                return

            table_data = []
            for host in hosts:
                name = extract_host_field(host, "name", field_aliases=["hostname"], default="")
                model = extract_host_field(host, "model", field_aliases=["host_model"], default="N/A")
                host_type = extract_host_field(host, "host_type", field_aliases=["type"], default="N/A")
                can_self_schedule = extract_host_field(host, "can_self_schedule", default=False)

                if not name:
                    continue

                # If start/end dates specified, check schedule availability
                if start_date and end_date:
                    try:
                        # Convert dates to ISO format for API
                        from datetime import datetime

                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        start_iso = start_dt.isoformat()[:-3]
                        end_iso = end_dt.isoformat()[:-3]

                        is_available = self.shell.connection.api.is_available(
                            name, {"start": start_iso, "end": end_iso}
                        )
                        if not is_available:
                            continue  # Skip hosts with schedule conflicts
                    except Exception:
                        # If availability check fails, include the host
                        pass

                table_data.append([name, model, host_type, "Yes" if can_self_schedule else "No"])

            if not table_data:
                self.shell.poutput("No available hosts found")
                return

            headers = ["Name", "Model", "Type", "Self-Schedule"]
            self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))

        except Exception as e:
            self.shell.perror(f"Failed to list available hosts: {e}")
