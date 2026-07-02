"""GUI Shell Adapter - bridges GUI with existing command classes"""

import time

from quads_client.commands.available import AvailableCommands
from quads_client.commands.cloud import CloudCommands
from quads_client.commands.connection import ConnectionCommands
from quads_client.commands.host import HostCommands
from quads_client.commands.schedule import ScheduleCommands
from quads_client.commands.server import ServerCommands
from quads_client.commands.session import SessionCommands
from quads_client.commands.user import UserCommands
from quads_client.commands.version import VersionCommands
from quads_client.config import ConfigError, QuadsClientConfig
from quads_client.history import CommandHistory
from quads_client.session_manager import SessionManager


class GuiShell:
    """
    Adapter that allows GUI to reuse command logic without cmd2 dependency.
    Mimics the QuadsClientShell interface that command classes expect.
    """

    def __init__(self, gui_app):
        """
        Initialize GUI shell adapter

        Args:
            gui_app: Reference to the main GUI application (QuadsClientApp)
        """
        self.gui_app = gui_app
        self.config = None
        self.session_manager = None
        self.command_history = CommandHistory()
        self.rich_console = None
        self.debug = False
        self.quiet = False
        self.gui_mode = True
        self._capture_output = False
        self._captured_messages = []
        self._models_cache = None
        self._models_cache_time = 0
        self._nic_vendors_cache = None
        self._nic_vendors_cache_time = 0
        self._hosts_cache = None
        self._hosts_cache_time = 0
        self._metadata_cache_ttl = 300

        try:
            self.config = QuadsClientConfig()
            self.session_manager = SessionManager(self.config)
        except ConfigError as e:
            self.pwarning(f"Configuration error: {e}")

        self.connection_commands = ConnectionCommands(self)
        self.version_commands = VersionCommands(self)
        self.cloud_commands = CloudCommands(self)
        self.user_commands = UserCommands(self)
        self.host_commands = HostCommands(self)
        self.schedule_commands = ScheduleCommands(self)
        self.available_commands = AvailableCommands(self)
        self.server_commands = ServerCommands(self)
        self.session_commands = SessionCommands(self)

    @property
    def connection(self):
        """Active session's connection for backward compatibility"""
        if self.session_manager:
            return self.session_manager.active_connection
        return None

    def poutput(self, message):
        """Output message to GUI (info level)"""
        if self._capture_output:
            self._captured_messages.append(("info", message))
        elif self.gui_app:
            self.gui_app.show_message(message, level="info")
        else:
            print(message)

    def perror(self, message):
        """Error output to GUI"""
        if self._capture_output:
            self._captured_messages.append(("error", message))
        elif self.gui_app:
            self.gui_app.show_message(message, level="error")
        else:
            print(f"ERROR: {message}")

    def pwarning(self, message):
        """Warning output to GUI"""
        if self._capture_output:
            self._captured_messages.append(("warning", message))
        elif self.gui_app:
            self.gui_app.show_message(message, level="warning")
        else:
            print(f"WARNING: {message}")

    def pfeedback(self, message):
        """Feedback output to GUI (same as poutput for GUI)"""
        self.poutput(message)

    def invalidate_metadata_cache(self):
        """Clear cached metadata (call after connecting to a different server)"""
        self._models_cache = None
        self._models_cache_time = 0
        self._nic_vendors_cache = None
        self._nic_vendors_cache_time = 0
        self._hosts_cache = None
        self._hosts_cache_time = 0

    def _get_cached_hosts(self):
        """Fetch hosts with TTL cache, shared by models and NIC vendor lookups."""
        now = time.monotonic()
        if self._hosts_cache is not None and (now - self._hosts_cache_time) < self._metadata_cache_ttl:
            return self._hosts_cache
        if not self.is_authenticated():
            return []
        try:
            hosts = self.connection.api.get_hosts()
            if hosts and isinstance(hosts, list):
                self._hosts_cache = hosts
                self._hosts_cache_time = now
                return hosts
        except Exception:
            pass
        return []

    def get_available_models(self):
        """
        Fetch unique host models from the API.
        Uses existing host_commands to get data. Results cached for 5 minutes.

        Returns:
            list: Sorted list of unique model names, or empty list if error
        """
        now = time.monotonic()
        if self._models_cache is not None and (now - self._models_cache_time) < self._metadata_cache_ttl:
            return self._models_cache

        if not self.is_authenticated():
            return []

        hosts = self._get_cached_hosts()
        if not hosts:
            return []

        models = set()
        for host in hosts:
            model = host.get("model", "").strip()
            if model:
                models.add(model)

        result = sorted(list(models))
        self._models_cache = result
        self._models_cache_time = now
        return result

    def get_available_vlans(self):
        """
        Fetch available (free) VLANs from API.
        Uses existing cloud_commands logic.

        Returns:
            list: List of free VLAN IDs
        """
        if not self.is_authenticated():
            return []

        try:
            # Get all VLANs
            vlans = self.connection.api.get_vlans()
            if not vlans:
                return []

            # Get active assignments to check which VLANs are in use
            try:
                assignments = self.connection.api.filter_assignments({"active": True})
            except Exception:
                assignments = []

            # Find VLANs not assigned to any cloud
            free_vlans = []
            for vlan in vlans:
                vlan_id = vlan.get("vlan_id")
                if not vlan_id:
                    continue

                # Check if this VLAN is assigned
                is_assigned = False
                for assignment in assignments:
                    if assignment.get("vlan", {}).get("vlan_id") == vlan_id:
                        is_assigned = True
                        break

                if not is_assigned:
                    free_vlans.append(str(vlan_id))

            return sorted(free_vlans, key=lambda x: int(x) if x.isdigit() else 0)

        except Exception:
            # Silently fail
            return []

    def get_available_os(self):
        """
        Fetch available OS options from API.

        Returns:
            list: List of OS title strings, or empty list if error
        """
        if not self.is_authenticated():
            return []

        try:
            os_list = self.connection.api.get_os_list()
            if not os_list:
                return []
            return [os_item.get("Title", "") for os_item in os_list if os_item.get("Title")]
        except Exception:
            return []

    def get_available_nic_vendors(self):
        """
        Fetch unique NIC vendor names from hosts for dropdown population.
        Results cached for 5 minutes.

        Returns:
            list: Sorted list of unique NIC vendor names, or empty list if error
        """
        now = time.monotonic()
        if self._nic_vendors_cache is not None and (now - self._nic_vendors_cache_time) < self._metadata_cache_ttl:
            return self._nic_vendors_cache

        if not self.is_authenticated():
            return []

        hosts = self._get_cached_hosts()
        if not hosts:
            return []

        vendors = set()
        for host in hosts:
            interfaces = host.get("interfaces", [])
            if isinstance(interfaces, list):
                for iface in interfaces:
                    if isinstance(iface, dict):
                        vendor = iface.get("vendor", "").strip()
                        if vendor:
                            vendors.add(vendor)

        result = sorted(list(vendors))
        self._nic_vendors_cache = result
        self._nic_vendors_cache_time = now
        return result

    def get_available_hosts_data(self, **filters):
        """
        Fetch available hosts from API and return structured data.
        Uses existing quads-client logic but returns data instead of printing.

        Accepts filter keys matching the CLI ls-available command:
            model, memory__gte, disks.disk_type, disks.size_gb__gte,
            disks.count__gte, interfaces.vendor, interfaces.speed__gte,
            processors.processor_type, start, end

        Start/end dates trigger per-host is_available() checks (same as CLI).

        Returns:
            list: List of dicts with keys: name, model, host_type, can_self_schedule
        """
        if not self.is_authenticated():
            return []

        try:
            from datetime import datetime

            from quads_client.utils import extract_host_field, get_available_hosts_filter

            # Pop start/end for schedule checking (not passed to filter_hosts)
            start_date = filters.pop("start", None)
            end_date = filters.pop("end", None)

            # Get available hosts using filter_hosts for cloud01 (available pool)
            host_filters = get_available_hosts_filter(**filters)

            if not self.is_admin():
                host_filters["can_self_schedule"] = True

            hosts = self.connection.api.filter_hosts(host_filters)

            # Check if API returned an error
            if isinstance(hosts, str) or not isinstance(hosts, list):
                return []

            if not hosts:
                return []

            # Get current schedules to filter out hosts that are scheduled to move
            # A host may be IN cloud01 now but SCHEDULED to move to another cloud
            current_schedules = []
            try:
                current_schedules = self.connection.api.get_current_schedules({})
            except Exception:
                pass

            # Build set of hosts that have current schedules (excluding cloud01)
            scheduled_hosts = set()
            if current_schedules:
                for schedule in current_schedules:
                    if isinstance(schedule, dict):
                        assignment = schedule.get("assignment", {})
                        if isinstance(assignment, dict):
                            cloud = assignment.get("cloud", {})
                            cloud_name = cloud.get("name") if isinstance(cloud, dict) else str(cloud)
                            if cloud_name and cloud_name != "cloud01":
                                host = schedule.get("host", {})
                                host_name = host.get("name") if isinstance(host, dict) else str(host)
                                if host_name:
                                    scheduled_hosts.add(host_name)

            # Build structured data - filter out scheduled hosts
            results = []
            for host in hosts:
                name = extract_host_field(host, "name", field_aliases=["hostname"], default="")
                model_val = extract_host_field(host, "model", field_aliases=["host_model"], default="N/A")
                host_type = extract_host_field(host, "host_type", field_aliases=["type"], default="N/A")
                can_self_schedule = extract_host_field(host, "can_self_schedule", default=False)

                if not name:
                    continue

                # Skip hosts that have active schedules to other clouds
                if name in scheduled_hosts:
                    continue

                # If start/end dates specified, check schedule availability
                if start_date and end_date:
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        start_iso = start_dt.isoformat()[:-3]
                        end_iso = end_dt.isoformat()[:-3]

                        is_available = self.connection.api.is_available(name, {"start": start_iso, "end": end_iso})
                        if not is_available:
                            continue
                    except Exception:
                        pass

                results.append(
                    {"name": name, "model": model_val, "host_type": host_type, "can_self_schedule": can_self_schedule}
                )

            return results

        except Exception:
            return []

    def execute_command(self, command_name, args=""):
        """
        Execute a command by name with arguments

        Args:
            command_name: Name of the command (e.g., 'connect', 'schedule')
            args: Command arguments as string

        Returns:
            Command result (if any)
        """
        command_map = {
            "connect": self.connection_commands.cmd_connect,
            "disconnect": self.connection_commands.cmd_disconnect,
            "status": self.connection_commands.cmd_status,
            "login": self.user_commands.cmd_login,
            "logout": self.user_commands.cmd_logout,
            "register": self.user_commands.cmd_register,
            "whoami": self.user_commands.cmd_whoami,
            "schedule": self.user_commands.cmd_schedule,
            "my-hosts": self.user_commands.cmd_my_hosts,
            "my-assignments": self.user_commands.cmd_my_assignments,
            "terminate": self.user_commands.cmd_terminate,
            "cloud-list": self.cloud_commands.cmd_cloud_list,
            "ls-available": self.available_commands.cmd_ls_available,
            "ls-hosts": self.host_commands.cmd_ls_hosts,
            "version": self.version_commands.cmd_version,
            "servers": self.server_commands.cmd_servers,
            "add-server": self.server_commands.cmd_add_server,
            "session-list": self.session_commands.cmd_session_list,
            "session-create": self.session_commands.cmd_session_create,
            "session-switch": self.session_commands.cmd_session_switch,
            "session-close": self.session_commands.cmd_session_close,
        }

        command_func = command_map.get(command_name)
        if command_func:
            try:
                return command_func(args)
            except Exception as e:
                self.perror(f"Command failed: {e}")
                import traceback

                traceback.print_exc()
        else:
            self.perror(f"Unknown command: {command_name}")

    def is_authenticated(self):
        """Check if user is authenticated"""
        return self.connection and self.connection.is_authenticated

    def is_admin(self):
        """Check if user has admin role"""
        return self.connection and self.connection.is_admin

    def get_auto_login_server(self):
        """
        Determine which server to auto-connect to.
        Priority: gui_preferences default > config default > last-connected session > first server with credentials.
        Returns server name or None if no servers configured.
        """
        servers = {}
        if self.config:
            servers = self.config.get_all_servers()

        if not servers:
            return None

        if len(servers) == 1:
            return list(servers.keys())[0]

        # Check gui_preferences default_server
        if self.config and hasattr(self.config, "config_data"):
            prefs = self.config.config_data.get("gui_preferences", {})
            pref_default = prefs.get("default_server")
            if pref_default and pref_default in servers:
                return pref_default

        # Check main config default_server
        if self.config:
            config_default = self.config.get_default_server()
            if config_default and config_default in servers:
                return config_default

        # Check last-connected server from session history
        if self.session_manager:
            for session in self.session_manager.sessions.values():
                if session.connection and session.connection.current_server in servers:
                    return session.connection.current_server

        # Fall back to first server that has credentials
        for name, cfg in servers.items():
            if cfg.get("username") and cfg.get("password"):
                return name

        # Last resort: first server
        return list(servers.keys())[0]

    def connect_to_server(self, server_name):
        """
        Connect to a server with session dedup and zombie cleanup.
        Reuses existing session if one exists for this server.
        Cleans up the session if the connection fails.

        Returns:
            (success: bool, error_message: str or None)
        """
        from quads_client.connection import ConnectionError as ConnError

        self.invalidate_metadata_cache()

        if not self.session_manager:
            return False, "Configuration not loaded"

        # Check if a session already exists for this server
        existing_session = None
        for session in self.session_manager.sessions.values():
            if session.server_name == server_name:
                existing_session = session
                break

        try:
            if existing_session:
                if existing_session.id != self.session_manager.active_session_id:
                    self.session_manager.switch_session(existing_session.id)

                if not existing_session.connection.is_connected:
                    existing_session.connection.connect(server_name)

                return True, None
            else:
                session = self.session_manager.create_session(server_name)
                try:
                    session.connection.connect(server_name)
                    return True, None
                except (ConnError, Exception) as e:
                    self.session_manager.close_session(session.id)
                    return False, str(e)
        except (ConnError, Exception) as e:
            return False, str(e)

    def _update_prompt(self):
        """Update prompt (no-op for GUI, used by CLI)"""
        pass

    def _update_visible_commands(self):
        """Update visible commands (no-op for GUI, used by CLI)"""
        pass
