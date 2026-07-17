import shlex

from tabulate import tabulate

from quads_client.error_handler import require_connection


class CloudCommands:
    def __init__(self, shell):
        self.shell = shell
        self.rich_console = shell.rich_console if hasattr(shell, "rich_console") else None

    def _require_connection(self):
        return require_connection(self.shell)

    def cmd_cloud_list(self, args):
        """List all clouds. Usage: cloud-list [cloud <name>] [detail]"""
        if not self._require_connection():
            return

        parts = args.split()
        cloud_name = None
        show_detail = False

        i = 0
        while i < len(parts):
            if parts[i] == "cloud" and i + 1 < len(parts):
                cloud_name = parts[i + 1]
                i += 2
            elif parts[i] == "detail":
                show_detail = True
                i += 1
            else:
                i += 1

        try:
            if cloud_name:
                self._show_cloud_detail(cloud_name)
            elif show_detail and not cloud_name:
                self.shell.perror("detail requires cloud <name>")
            else:
                clouds = self.shell.connection.api.get_clouds()
                if not clouds:
                    self.shell.poutput("No clouds found")
                    return

                table_data = []
                for cloud in clouds:
                    cloud_name = cloud.get("name", "")

                    # Try to get active assignment for this cloud
                    assignment_id = "-"
                    owner = "-"
                    description = "-"
                    vlan = "-"
                    wipe = "No"

                    try:
                        assignment = self.shell.connection.api.get_active_cloud_assignment(cloud_name)
                        if assignment:
                            # Extract assignment ID
                            if isinstance(assignment, dict):
                                assignment_id = str(assignment.get("id", "-"))
                                owner = assignment.get("owner", "-") or "-"
                                desc_full = assignment.get("description", "-") or "-"
                                description = desc_full[:40] if len(desc_full) > 40 else desc_full
                                wipe = "Yes" if assignment.get("wipe", False) else "No"

                                # Extract VLAN
                                vlan_obj = assignment.get("vlan")
                                if isinstance(vlan_obj, dict):
                                    vlan = str(vlan_obj.get("vlan_id", "-"))
                                elif vlan_obj:
                                    vlan = str(vlan_obj)
                    except Exception:
                        # No active assignment - keep defaults
                        pass

                    table_data.append([cloud_name, assignment_id, owner, description, vlan, wipe])

                headers = ["Cloud", "Assignment", "Owner", "Description", "VLAN", "Wipe"]
                if self.rich_console:
                    self.rich_console.print_table(headers, table_data)
                else:
                    self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))

        except Exception as e:
            self.shell.perror(f"Failed to list clouds: {e}")

    def _show_cloud_detail(self, cloud_name):
        """Show detailed information for a specific cloud"""
        try:
            clouds = self.shell.connection.api.filter_clouds({"name": cloud_name})
            if not clouds:
                if self.rich_console:
                    self.rich_console.print_error(f"Cloud '{cloud_name}' not found")
                else:
                    self.shell.perror(f"Cloud '{cloud_name}' not found")
                return

            cloud = clouds[0]

            if self.rich_console:
                self.rich_console.print_section(f"Cloud: {cloud_name}")

                properties = [
                    ["Name", cloud.get("name", "")],
                    ["Owner", cloud.get("owner", "") or "-"],
                    ["Description", cloud.get("description", "") or "-"],
                    ["Ticket", cloud.get("ticket", "") or "-"],
                    ["CC Users", cloud.get("ccusers", "") or "-"],
                    [
                        "VLAN (QinQ)",
                        cloud.get("vlan", {}).get("vlan_id", "-") if isinstance(cloud.get("vlan"), dict) else "-",
                    ],
                    ["Wipe", "Yes" if cloud.get("wipe", False) else "No"],
                    ["Validated", "Yes" if cloud.get("validated", False) else "No"],
                ]

                self.rich_console.print_table(["Property", "Value"], properties)

                schedules = self.shell.connection.api.get_schedules({"cloud": cloud_name})
                if schedules:
                    self.shell.poutput("")  # Blank line
                    host_data = []
                    for sched in schedules:
                        host = sched.get("host", {})
                        host_data.append(
                            [
                                host.get("name", ""),
                                host.get("model", ""),
                                sched.get("start", "").replace("GMT", "UTC"),
                                sched.get("end", "").replace("GMT", "UTC"),
                            ]
                        )

                    headers = ["Hostname", "Model", "Start", "End"]
                    self.rich_console.print_table(headers, host_data, title=f"Assigned Hosts ({len(schedules)})")
                else:
                    self.rich_console.print_info("\nNo hosts assigned to this cloud")
            else:
                self.shell.poutput(f"\nCloud: {cloud_name}")
                self.shell.poutput("=" * 80)

                properties = [
                    ["Name", cloud.get("name", "")],
                    ["Owner", cloud.get("owner", "") or "-"],
                    ["Description", cloud.get("description", "") or "-"],
                    ["Ticket", cloud.get("ticket", "") or "-"],
                    ["CC Users", cloud.get("ccusers", "") or "-"],
                    [
                        "VLAN (QinQ)",
                        cloud.get("vlan", {}).get("vlan_id", "-") if isinstance(cloud.get("vlan"), dict) else "-",
                    ],
                    ["Wipe", "Yes" if cloud.get("wipe", False) else "No"],
                    ["Validated", "Yes" if cloud.get("validated", False) else "No"],
                ]

                self.shell.poutput(tabulate(properties, tablefmt="simple"))

                schedules = self.shell.connection.api.get_schedules({"cloud": cloud_name})
                if schedules:
                    self.shell.poutput(f"\nAssigned Hosts ({len(schedules)}):")
                    self.shell.poutput("-" * 80)

                    host_data = []
                    for sched in schedules:
                        host = sched.get("host", {})
                        host_data.append(
                            [
                                host.get("name", ""),
                                host.get("model", ""),
                                sched.get("start", "").replace("GMT", "UTC"),
                                sched.get("end", "").replace("GMT", "UTC"),
                            ]
                        )

                    headers = ["Hostname", "Model", "Start", "End"]
                    self.shell.poutput(tabulate(host_data, headers=headers, tablefmt="simple"))
                else:
                    self.shell.poutput("\nNo hosts assigned to this cloud")

        except Exception as e:
            if self.rich_console:
                self.rich_console.print_error(f"Failed to get cloud details: {e}")
            else:
                self.shell.perror(f"Failed to get cloud details: {e}")

    def cmd_cloud_create(self, args):
        """Create a new cloud (admin only). Usage: cloud-create <name>"""
        if not self._require_connection():
            return

        if not args.strip() or args.strip() in ("?", "-h", "--help"):
            self.shell.perror("Usage: cloud-create <name>")
            return

        cloud_name = args.strip()
        try:
            self.shell.connection.api.create_cloud({"cloud": cloud_name})
            if self.rich_console:
                self.rich_console.print_success(f"Cloud '{cloud_name}' created successfully")
            else:
                self.shell.poutput(f"Cloud '{cloud_name}' created successfully")
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                if self.rich_console:
                    self.rich_console.print_error("This command requires admin role")
                else:
                    self.shell.perror("Error: This command requires admin role")
            else:
                if self.rich_console:
                    self.rich_console.print_error(f"Failed to create cloud: {e}")
                else:
                    self.shell.perror(f"Failed to create cloud: {e}")

    def cmd_cloud_delete(self, args):
        """Delete a cloud (admin only). Usage: cloud-delete <name>"""
        if not self._require_connection():
            return

        if not args.strip():
            self.shell.perror("Usage: cloud-delete <name>")
            return

        cloud_name = args.strip()
        try:
            self.shell.connection.api.remove_cloud(cloud_name)
            if self.rich_console:
                self.rich_console.print_success(f"Cloud '{cloud_name}' deleted successfully")
            else:
                self.shell.poutput(f"Cloud '{cloud_name}' deleted successfully")
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                if self.rich_console:
                    self.rich_console.print_error("This command requires admin role")
                else:
                    self.shell.perror("Error: This command requires admin role")
            else:
                if self.rich_console:
                    self.rich_console.print_error(f"Failed to delete cloud: {e}")
                else:
                    self.shell.perror(f"Failed to delete cloud: {e}")

    def cmd_mod_cloud(self, args):
        """Modify cloud assignment attributes.
        Usage: mod-cloud <cloud_name> [OPTIONS]

        Modify attributes of a cloud's active assignment. Cloud must have an active assignment.

        Options:
          description <text>       Assignment description
          cloud-owner <username>   Cloud owner username
          cloud-ticket <ticket_id> Ticket ID (JIRA, etc.)
          cc-users <user1,user2>   Comma-separated CC users
          vlan <vlan_id>           VLAN ID number
          qinq <0|1>              QinQ setting (0=disabled, 1=enabled)
          wipe                     Enable host wiping
          nowipe                   Disable host wiping

        Examples:
          mod-cloud cloud05 description "Updated test environment"
          mod-cloud cloud02 cloud-owner alice cloud-ticket 456
          mod-cloud cloud03 vlan 1234 qinq 1
          mod-cloud cloud04 wipe
          mod-cloud cloud06 cc-users "bob,alice,charlie"
        """
        if not self._require_connection():
            return

        # Handle help request
        if args.strip() in ("?", "-h", "--help"):
            self.shell.poutput("Usage: mod-cloud <cloud_name> [OPTIONS]")
            self.shell.poutput("\nModify attributes of a cloud's active assignment.")
            self.shell.poutput("\nOptions:")
            self.shell.poutput("  description <text>       Assignment description")
            self.shell.poutput("  cloud-owner <username>   Cloud owner username")
            self.shell.poutput("  cloud-ticket <ticket_id> Ticket ID (JIRA, etc.)")
            self.shell.poutput("  cc-users <user1,user2>   Comma-separated CC users")
            self.shell.poutput("  vlan <vlan_id>           VLAN ID number")
            self.shell.poutput("  qinq <0|1>              QinQ setting (0=disabled, 1=enabled)")
            self.shell.poutput("  os <title>               OS for provisioning (see os-list)")
            self.shell.poutput("  wipe                     Enable host wiping")
            self.shell.poutput("  nowipe                   Disable host wiping")
            self.shell.poutput("\nExamples:")
            self.shell.poutput('  mod-cloud cloud05 description "Updated test environment"')
            self.shell.poutput("  mod-cloud cloud02 cloud-owner alice cloud-ticket 456")
            self.shell.poutput("  mod-cloud cloud03 vlan 1234 qinq 1")
            self.shell.poutput('  mod-cloud cloud04 os "RHEL 9.4"')
            self.shell.poutput("  mod-cloud cloud04 wipe")
            self.shell.poutput('  mod-cloud cloud06 cc-users "bob,alice,charlie"')
            return

        try:
            parts = shlex.split(args)
        except ValueError:
            parts = args.split()

        if len(parts) < 1:
            self.shell.perror("Usage: mod-cloud <cloud_name> [OPTIONS]")
            self.shell.perror("Run 'mod-cloud ?' for detailed help")
            return

        cloud_name = parts[0]
        updates = {}
        keywords = ["description", "cloud-owner", "cloud-ticket", "cc-users", "vlan", "qinq", "os", "wipe", "nowipe"]

        i = 1
        while i < len(parts):
            if parts[i] == "description" and i + 1 < len(parts):
                desc_parts = []
                i += 1
                while i < len(parts) and parts[i] not in keywords:
                    desc_parts.append(parts[i])
                    i += 1
                updates["description"] = " ".join(desc_parts)
            elif parts[i] == "cloud-owner" and i + 1 < len(parts):
                updates["owner"] = parts[i + 1]
                i += 2
            elif parts[i] == "cloud-ticket" and i + 1 < len(parts):
                updates["ticket"] = parts[i + 1]
                i += 2
            elif parts[i] == "cc-users" and i + 1 < len(parts):
                updates["ccuser"] = parts[i + 1]
                i += 2
            elif parts[i] == "vlan" and i + 1 < len(parts):
                try:
                    updates["vlan"] = int(parts[i + 1])
                except ValueError:
                    self.shell.perror(f"Invalid VLAN ID: {parts[i + 1]}")
                    return
                i += 2
            elif parts[i] == "qinq" and i + 1 < len(parts):
                try:
                    qinq_val = int(parts[i + 1])
                    if qinq_val not in [0, 1]:
                        self.shell.perror(f"QinQ must be 0 or 1, got: {parts[i + 1]}")
                        return
                    updates["qinq"] = qinq_val
                except ValueError:
                    self.shell.perror(f"Invalid QinQ value: {parts[i + 1]}")
                    return
                i += 2
            elif parts[i] == "os" and i + 1 < len(parts):
                updates["ostype"] = parts[i + 1]
                i += 2
            elif parts[i] == "wipe":
                updates["wipe"] = True
                i += 1
            elif parts[i] == "nowipe":
                updates["wipe"] = False
                i += 1
            else:
                i += 1

        if not updates:
            self.shell.perror("No updates specified")
            self.shell.perror("Run 'mod-cloud ?' for help")
            return

        try:
            assignment = self.shell.connection.api.get_active_cloud_assignment(cloud_name)
            if not assignment or not isinstance(assignment, dict):
                err = f"No active assignment found for cloud '{cloud_name}'"
                if self.rich_console:
                    self.rich_console.print_error(err)
                else:
                    self.shell.perror(err)
                return

            assignment_id = assignment.get("id")
            if assignment_id is None:
                err = f"Could not determine assignment ID for cloud '{cloud_name}'"
                if self.rich_console:
                    self.rich_console.print_error(err)
                else:
                    self.shell.perror(err)
                return

            self.shell.connection.api.update_assignment(assignment_id, updates)
            if self.rich_console:
                self.rich_console.print_success(f"Cloud '{cloud_name}' updated successfully")
                for key, value in updates.items():
                    self.rich_console.print_property(key, value)
            else:
                self.shell.poutput(f"OK: Cloud '{cloud_name}' updated successfully")
                for key, value in updates.items():
                    self.shell.poutput(f"  {key}: {value}")

        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                if self.rich_console:
                    self.rich_console.print_error("This command requires admin role")
                else:
                    self.shell.perror("Error: This command requires admin role")
            else:
                if self.rich_console:
                    self.rich_console.print_error(f"Failed to modify cloud: {e}")
                else:
                    self.shell.perror(f"Failed to modify cloud: {e}")

    def cmd_find_free_cloud(self, args):
        """
        Find clouds without active assignments.
        Usage: find_free_cloud
        """
        if not self._require_connection():
            return

        try:
            # Get all clouds
            clouds = self.shell.connection.api.get_clouds()
            if not clouds:
                self.shell.poutput("No clouds found")
                return

            free_clouds = []

            for cloud in clouds:
                cloud_name = cloud.get("name")

                # Skip cloud01 (spare pool)
                if cloud_name == "cloud01":
                    continue

                # Check if cloud has current schedules
                current_schedules = self.shell.connection.api.get_current_schedules({"cloud": cloud_name})

                # If no current schedules, cloud is free
                if not current_schedules:
                    free_clouds.append(cloud_name)

            if free_clouds:
                self.shell.poutput("Free clouds:")
                for cloud_name in sorted(free_clouds):
                    self.shell.poutput(f"  {cloud_name}")
            else:
                self.shell.poutput("No free clouds available")

        except Exception as e:
            if self.rich_console:
                self.rich_console.print_error(f"Failed to find free clouds: {e}")
            else:
                self.shell.perror(f"Failed to find free clouds: {e}")

    def cmd_cloud_only(self, args):
        """
        List all hosts assigned to a specific cloud.
        Usage: cloud_only <cloud_name>

        Example:
          cloud_only cloud02
        """
        if not self._require_connection():
            return

        cloud_name = args.strip()

        if not cloud_name or cloud_name in ("?", "-h", "--help"):
            self.shell.perror("Usage: cloud_only <cloud_name>")
            return

        try:
            # Verify cloud exists
            clouds = self.shell.connection.api.filter_clouds({"name": cloud_name})
            if not clouds:
                self.shell.perror(f"Cloud '{cloud_name}' not found")
                return

            # cloud01 is the spare pool -- hosts live there without schedules
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

            if hostnames:
                self.shell.poutput(f"Hosts in cloud {cloud_name}:")
                for hostname in sorted(hostnames):
                    self.shell.poutput(f"  {hostname}")
            else:
                self.shell.poutput(f"No hosts currently assigned to {cloud_name}")

        except Exception as e:
            if self.rich_console:
                self.rich_console.print_error(f"Failed to list cloud hosts: {e}")
            else:
                self.shell.perror(f"Failed to list cloud hosts: {e}")

    def cmd_ls_vlan(self, args):
        """
        List all VLANs with assigned clouds.
        Usage: ls-vlan

        Displays VLANs in a table showing VLAN ID, gateway, IP range, netmask, and assigned cloud.
        """
        if not self._require_connection():
            return

        try:
            # Get all VLANs
            vlans = self.shell.connection.api.get_vlans()

            if not vlans:
                self.shell.poutput("No VLANs configured")
                return

            # Build table data
            table_data = []
            headers = ["VLAN ID", "Gateway", "IP Range", "Netmask", "Assigned Cloud"]

            for vlan in vlans:
                vlan_id = vlan.get("vlan_id", "N/A")
                gateway = vlan.get("gateway", "-")
                ip_range = vlan.get("ip_range", "-")
                netmask = vlan.get("netmask", "-")

                # Get assignment for this VLAN
                # Query API for assignments with this VLAN ID
                try:
                    # Get all active assignments and filter for this VLAN
                    assignments = self.shell.connection.api.filter_assignments({"active": True})
                    cloud_assigned = "Free"

                    for assignment in assignments:
                        if assignment.get("vlan", {}).get("vlan_id") == vlan_id:
                            cloud_assigned = assignment.get("cloud", {}).get("name", "Unknown")
                            break

                except Exception:
                    cloud_assigned = "Unknown"

                table_data.append([str(vlan_id), gateway, ip_range, netmask, cloud_assigned])

            # Display table
            if self.rich_console:
                from rich.table import Table

                table = Table(title="Available VLANs")
                for header in headers:
                    table.add_column(header, style="cyan" if header == "VLAN ID" else "white")

                for row in table_data:
                    # Color "Free" in green, assigned clouds in yellow
                    styled_row = row.copy()
                    if row[4] == "Free":
                        styled_row[4] = f"[green]{row[4]}[/green]"
                    elif row[4] != "Unknown":
                        styled_row[4] = f"[yellow]{row[4]}[/yellow]"
                    table.add_row(*styled_row)

                self.shell.rich_console.console.print(table)
            else:
                # Fallback to tabulate
                self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))

        except Exception as e:
            if self.rich_console:
                self.rich_console.print_error(f"Failed to list VLANs: {e}")
            else:
                self.shell.perror(f"Failed to list VLANs: {e}")

    def cmd_os_list(self, args):
        """
        List available operating systems for provisioning.
        Usage: os-list

        Queries the QUADS server for available OS images that can be used
        with the schedule command or mod-cloud.
        """
        if not self._require_connection():
            return

        try:
            os_list = self.shell.connection.api.get_os_list()

            if not os_list:
                self.shell.poutput("No available operating systems")
                return

            headers = ["Id", "Title", "Release Name", "Family"]

            if self.rich_console:
                from rich.table import Table

                table = Table(title="Available Operating Systems")
                for header in headers:
                    table.add_column(header, style="cyan" if header == "Title" else "white")

                for os_item in os_list:
                    table.add_row(
                        str(os_item.get("Id", "")),
                        os_item.get("Title", ""),
                        os_item.get("Release Name", ""),
                        os_item.get("Family", ""),
                    )

                self.shell.rich_console.console.print(table)
            else:
                table_data = [
                    [
                        str(os_item.get("Id", "")),
                        os_item.get("Title", ""),
                        os_item.get("Release Name", ""),
                        os_item.get("Family", ""),
                    ]
                    for os_item in os_list
                ]
                self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))

        except Exception as e:
            if self.rich_console:
                self.rich_console.print_error(f"Failed to list operating systems: {e}")
            else:
                self.shell.perror(f"Failed to list operating systems: {e}")
