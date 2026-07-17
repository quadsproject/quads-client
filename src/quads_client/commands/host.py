from tabulate import tabulate

from quads_client.error_handler import require_connection


class HostCommands:
    def __init__(self, shell):
        self.shell = shell
        self.rich_console = shell.rich_console if hasattr(shell, "rich_console") else None

    def _require_connection(self):
        return require_connection(self.shell)

    def cmd_ls_hosts(self, args):
        """List all hosts"""
        if not self._require_connection():
            return

        try:
            hosts = self.shell.connection.api.get_hosts()
            if not hosts:
                self.shell.poutput("No hosts found")
                return

            table_data = []
            for host in hosts:
                table_data.append(
                    [
                        host.get("name", ""),
                        host.get("model", ""),
                        host.get("default_cloud", {}).get("name", ""),
                        host.get("host_type", ""),
                        "Yes" if host.get("broken", False) else "No",
                        "Yes" if host.get("retired", False) else "No",
                    ]
                )

            headers = ["Name", "Model", "Default Cloud", "Type", "Broken", "Retired"]
            if self.rich_console:
                self.rich_console.print_table(headers, table_data, title="Hosts")
            else:
                self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))

        except Exception as e:
            self.shell.perror(f"Failed to list hosts: {e}")

    def cmd_mark_broken(self, args):
        """Mark a host as broken. Usage: mark-broken <hostname>"""
        if not self._require_connection():
            return

        if not args.strip() or args.strip() in ("?", "-h", "--help"):
            self.shell.perror("Usage: mark-broken <hostname>")
            return

        hostname = args.strip()
        try:
            self.shell.connection.api.update_host(hostname, {"broken": True})
            self.shell.poutput(f"Marked {hostname} as broken")
        except Exception as e:
            self.shell.perror(f"Failed to mark host as broken: {e}")

    def cmd_mark_repaired(self, args):
        """Mark a broken host as repaired. Usage: mark-repaired <hostname>"""
        if not self._require_connection():
            return

        if not args.strip() or args.strip() in ("?", "-h", "--help"):
            self.shell.perror("Usage: mark-repaired <hostname>")
            return

        hostname = args.strip()
        try:
            self.shell.connection.api.update_host(hostname, {"broken": False})
            self.shell.poutput(f"Marked {hostname} as repaired")
        except Exception as e:
            self.shell.perror(f"Failed to mark host as repaired: {e}")

    def cmd_retire(self, args):
        """Mark a host as retired. Usage: retire <hostname>"""
        if not self._require_connection():
            return

        if not args.strip() or args.strip() in ("?", "-h", "--help"):
            self.shell.perror("Usage: retire <hostname>")
            return

        hostname = args.strip()
        try:
            self.shell.connection.api.update_host(hostname, {"retired": True})
            self.shell.poutput(f"Marked {hostname} as retired")
        except Exception as e:
            self.shell.perror(f"Failed to mark host as retired: {e}")

    def cmd_unretire(self, args):
        """Mark a retired host as active. Usage: unretire <hostname>"""
        if not self._require_connection():
            return

        if not args.strip() or args.strip() in ("?", "-h", "--help"):
            self.shell.perror("Usage: unretire <hostname>")
            return

        hostname = args.strip()
        try:
            self.shell.connection.api.update_host(hostname, {"retired": False})
            self.shell.poutput(f"Marked {hostname} as active")
        except Exception as e:
            self.shell.perror(f"Failed to mark host as active: {e}")

    def cmd_ls_broken(self, args):
        """List all broken hosts"""
        if not self._require_connection():
            return

        try:
            hosts = self.shell.connection.api.filter_hosts({"broken": True})
            if not hosts:
                self.shell.poutput("No broken hosts found")
                return

            table_data = []
            for host in hosts:
                table_data.append([host.get("name", ""), host.get("model", "")])

            headers = ["Name", "Model"]
            if self.rich_console:
                self.rich_console.print_table(headers, table_data, title="Broken Hosts")
            else:
                self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))

        except Exception as e:
            self.shell.perror(f"Failed to list broken hosts: {e}")

    def cmd_ls_retired(self, args):
        """List all retired hosts"""
        if not self._require_connection():
            return

        try:
            hosts = self.shell.connection.api.filter_hosts({"retired": True})
            if not hosts:
                self.shell.poutput("No retired hosts found")
                return

            table_data = []
            for host in hosts:
                table_data.append([host.get("name", ""), host.get("model", "")])

            headers = ["Name", "Model"]
            if self.rich_console:
                self.rich_console.print_table(headers, table_data, title="Retired Hosts")
            else:
                self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))

        except Exception as e:
            self.shell.perror(f"Failed to list retired hosts: {e}")
