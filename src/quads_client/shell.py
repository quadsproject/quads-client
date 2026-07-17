import time

import cmd2

from quads_client.commands.available import AvailableCommands
from quads_client.commands.cloud import CloudCommands
from quads_client.commands.connection import ConnectionCommands
from quads_client.commands.host import HostCommands
from quads_client.commands.moves import MoveCommands
from quads_client.commands.schedule import ScheduleCommands
from quads_client.commands.server import ServerCommands
from quads_client.commands.session import SessionCommands
from quads_client.commands.track import TrackCommands
from quads_client.commands.user import UserCommands
from quads_client.commands.version import VersionCommands
from quads_client.config import ConfigError, QuadsClientConfig
from quads_client.history import CommandHistory
from quads_client.rich_console import RichConsole
from quads_client.session_manager import SessionManager
from quads_client.utils import get_ssl_indicator


class QuadsClientShell(cmd2.Cmd):
    intro = ""  # We'll use rich console for the banner

    def __init__(self, quiet=False):
        super().__init__(
            multiline_commands=[],
            persistent_history_file="~/.config/quads/.quads-client_readline_history",
            persistent_history_length=1000,
        )
        self.config = None
        self.session_manager = None
        self.command_history = CommandHistory()
        self.rich_console = RichConsole()
        self.quiet = quiet

        # Hide unwanted cmd2 built-in commands and dangerous cloud management commands
        self.permanently_hidden = [
            "macro",
            "run_script",
            "edit",
            "run_pyscript",
            "shortcuts",
            "_relative_run_script",
            "eof",
            "set",
            "ipy",
            "py",
            "cloud_create",  # Too dangerous - no use case for empty clouds
            "cloud_delete",  # Too dangerous - can break active assignments
        ]
        self.hidden_commands.extend(self.permanently_hidden)

        try:
            self.config = QuadsClientConfig()
            self.session_manager = SessionManager(self.config)
        except ConfigError as e:
            self.pwarning(f"Configuration error: {e}")

        # Print banner after config is loaded so we know if servers exist
        if not quiet:
            has_servers = self.config and not self.config.needs_initial_setup()
            self.rich_console.print_banner(has_servers=has_servers)

            if not has_servers:
                self._print_onboarding_message()

        self._last_activity_check = 0
        self._cached_activity_indicator = ""

        self.connection_commands = ConnectionCommands(self)
        self.version_commands = VersionCommands(self)
        self.cloud_commands = CloudCommands(self)
        self.user_commands = UserCommands(self)
        self.host_commands = HostCommands(self)
        self.schedule_commands = ScheduleCommands(self)
        self.available_commands = AvailableCommands(self)
        self.move_commands = MoveCommands(self)
        self.track_commands = TrackCommands(self)
        self.server_commands = ServerCommands(self)
        self.session_commands = SessionCommands(self)

        self._update_prompt()
        self._update_visible_commands()

    @property
    def connection(self):
        """Active session's connection for backward compatibility"""
        if self.session_manager:
            return self.session_manager.active_connection
        return None

    def preloop(self):
        """Configure custom readline keybindings"""
        super().preloop()
        try:
            import readline

            readline.parse_and_bind('"\\C-a\\C-a": "session_switch\\n"')
        except (ImportError, OSError):
            pass

    def postcmd(self, stop, line):
        self._update_prompt()
        return stop

    def _get_activity_indicator(self):
        if not self.connection or not self.connection.is_authenticated:
            return ""
        now = time.time()
        if now - self._last_activity_check < 30:
            return self._cached_activity_indicator
        self._last_activity_check = now
        try:
            moves = self.connection.api.get_all_move_status()
            if moves:
                self._cached_activity_indicator = "\033[1;33m⚡\033[0m"
            else:
                self._cached_activity_indicator = ""
        except Exception:
            self._cached_activity_indicator = ""
        return self._cached_activity_indicator

    def do_exit(self, args):
        """Exit the application"""
        return True

    def _print_onboarding_message(self):
        """Display first-time setup instructions"""
        self.poutput("\n\033[1;33m Welcome to QUADS Client! \033[0m")
        self.poutput("\n\033[1mGetting Started:\033[0m")
        self.poutput("  1. Add your QUADS server:")
        self.poutput("     \033[1;36madd_quads_server\033[0m")
        self.poutput("     (Follow the interactive prompts)\n")
        self.poutput("  2. Connect to your server:")
        self.poutput("     \033[1;36mconnect <server_name>\033[0m\n")
        self.poutput("  3. Authenticate:")
        self.poutput("     \033[1;36mtoken-login\033[0m              (SSO token)")
        self.poutput("     \033[1;36mregister <email> <pass>\033[0m  (new account)\n")
        self.poutput("  Type \033[1mhelp\033[0m for more commands.\n")

    def _shorten_server_name(self, name):
        """Shorten server name by stripping last 2 segments (e.g. quads2-dev.rdu2.scalelab)"""
        parts = name.split(".")
        if len(parts) > 3:
            return ".".join(parts[:-2])
        return name

    def _update_prompt(self):
        if self.connection and self.connection.is_connected:
            server = self.connection.current_server
            short_name = self._shorten_server_name(server)

            url = self.config.get_server_url(server)
            verify = self.config.get_server_verify(server)
            symbol, color = get_ssl_indicator(url, verify)

            session_info = self._get_session_indicators()

            admin_badge = ""
            if self.connection and self.connection.is_admin:
                admin_badge = " \033[1;31m[ADMIN]\033[0m"

            activity = self._get_activity_indicator()

            self.prompt = f"{color}{symbol} {session_info}({short_name}){activity}{admin_badge}\033[0m > "
        else:
            self.prompt = "\033[1;31m(disconnected)\033[0m > "

    def _get_session_indicators(self) -> str:
        """Generate session indicator string like '[1:dev* 2:prod]'"""
        if not self.session_manager:
            return ""

        sessions = self.session_manager.list_sessions()
        if len(sessions) <= 1:
            return ""

        indicators = []
        for session in sessions[:4]:  # Max 4 visible
            label = session.label[:8]  # Truncate long labels
            active = "*" if session.id == self.session_manager.active_session_id else ""
            indicators.append(f"{session.id}:{label}{active}")

        if len(sessions) > 4:
            indicators.append(f"+{len(sessions) - 4}")

        return f"[{' '.join(indicators)}] "

    def _update_visible_commands(self):
        """Update visible commands based on user role"""
        # Admin-only commands (hidden from SSM users)
        admin_commands = [
            "cloud_create",
            "cloud_delete",
            "mod_cloud",
            "find_free_cloud",
            "ls_vlan",
            "ls_hosts",
            "mark_broken",
            "mark_repaired",
            "retire",
            "unretire",
            "ls_broken",
            "ls_retired",
            "ls_schedule",
            "mod_schedule",
            "extend",
            "shrink",
            "add_server",
            "rm_server",
            "debug_admin",
        ]

        # Deprecated commands (hidden from all users)
        deprecated_commands = [
            "assignment_create",
            "assignment_terminate",
            "assignment_status",
        ]

        # Commands requiring authentication (user or admin)
        auth_required_commands = [
            "login",
            "whoami",
            "schedule",
            "assignment_list",
            "my_hosts",
            "my_assignments",
            "terminate",
            "cloud_list",
            "cloud_only",
            "ls_available",
            "os_list",
            "move_status",
            "track",
            "activity",
        ]

        # Get current authentication state
        is_authenticated = self.connection and self.connection.is_authenticated if self.connection else False
        is_admin = self.connection and self.connection.is_admin if self.connection else False

        # Reset hidden commands to permanently hidden list
        self.hidden_commands = list(self.permanently_hidden)

        # Always hide deprecated commands
        self.hidden_commands.extend(deprecated_commands)

        # Hide auth-required commands if not authenticated
        if not is_authenticated:
            self.hidden_commands.extend(auth_required_commands)
            # Also hide admin commands if not authenticated
            self.hidden_commands.extend(admin_commands)
        elif not is_admin:
            # Authenticated but not admin - hide admin commands from SSM users
            self.hidden_commands.extend(admin_commands)

    def do_version(self, args):
        """Display QUADS Client version"""
        self.version_commands.cmd_version(args)

    def do_debug_admin(self, args):
        """DEBUG: Check admin status"""
        if self.connection:
            print(f"Connected: {self.connection.is_connected}")
            print(f"Authenticated: {self.connection.is_authenticated}")
            print(f"Username: {self.connection.username}")
            print(f"User role: {self.connection.user_role}")
            print(f"Is admin: {self.connection.is_admin}")
            print(f"Hidden commands count: {len(self.hidden_commands)}")
            print(f"Admin commands in hidden: {'cloud_create' in self.hidden_commands}")
        else:
            print("No connection")

    def do_connect(self, args):
        """Connect to a QUADS server. Usage: connect [server_name|number] [session <label>]"""
        self.connection_commands.cmd_connect(args)

    def complete_connect(self, text, line, begidx, endidx):
        """Autocomplete for connect command"""
        servers = []
        if self.connection:
            servers = self.connection.get_available_servers()
        elif self.config:
            servers = list(self.config.get_all_servers().keys())
        return self.basic_complete(text, line, begidx, endidx, servers)

    def do_disconnect(self, args):
        """Disconnect from current QUADS server"""
        self.connection_commands.cmd_disconnect(args)

    def do_status(self, args):
        """Show current connection status"""
        self.connection_commands.cmd_status(args)

    def do_cloud_list(self, args):
        """List all clouds"""
        self.cloud_commands.cmd_cloud_list(args)

    def do_find_free_cloud(self, args):
        """Find clouds without active assignments (admin only)"""
        self.cloud_commands.cmd_find_free_cloud(args)

    def do_cloud_only(self, args):
        """List hosts assigned to a specific cloud"""
        self.cloud_commands.cmd_cloud_only(args)

    def do_ls_vlan(self, args):
        """List VLANs with assigned clouds (admin only)"""
        self.cloud_commands.cmd_ls_vlan(args)

    def do_os_list(self, args):
        """List available operating systems for provisioning"""
        self.cloud_commands.cmd_os_list(args)

    def do_cloud_create(self, args):
        """Create a new cloud (admin only)"""
        self.cloud_commands.cmd_cloud_create(args)

    def do_cloud_delete(self, args):
        """Delete a cloud (admin only)"""
        self.cloud_commands.cmd_cloud_delete(args)

    def do_register(self, args):
        """Register a new user"""
        self.user_commands.cmd_register(args)

    def do_login(self, args):
        """Login to current server"""
        self.user_commands.cmd_login(args)

    def do_token_login(self, args):
        """Login with an SSO API token"""
        self.user_commands.cmd_token_login(args)

    def do_whoami(self, args):
        """Show current user information"""
        self.user_commands.cmd_whoami(args)

    def do_assignment_create(self, args):
        """Create an assignment"""
        self.user_commands.cmd_assignment_create(args)

    def do_assignment_list(self, args):
        """List user's assignments"""
        self.user_commands.cmd_assignment_list(args)

    def do_assignment_status(self, args):
        """Show assignment details"""
        self.user_commands.cmd_assignment_status(args)

    def do_assignment_terminate(self, args):
        """Terminate an assignment (deprecated, use terminate)"""
        self.user_commands.cmd_terminate(args)

    def help_schedule(self):
        """Role-aware help for the schedule command"""
        if self.connection and self.connection.is_admin:
            self.poutput("Usage: schedule <cloud> <hosts|host-list path> <start> <end> [options]")
            self.poutput("\nSchedule hosts to a cloud (admin mode).")
            self.poutput("\nOptions:")
            self.poutput("  description <text>       Assignment description")
            self.poutput("  cloud-owner <username>   Cloud owner username")
            self.poutput("  cloud-ticket <ticket_id> Ticket ID (JIRA, etc.)")
            self.poutput("  cc-users <user1,user2>   Comma-separated CC users")
            self.poutput("  vlan <vlan_id>           VLAN ID number")
            self.poutput("  qinq <0|1>              QinQ setting (0=disabled, 1=enabled)")
            self.poutput("  os <title>               OS for provisioning (see os-list)")
            self.poutput("  nowipe                   Disable host wiping")
            self.poutput("\nExamples:")
            self.poutput('  schedule cloud02 host01,host02 "2026-08-01 22:00" "2026-08-15 22:00"')
            self.poutput('  schedule cloud03 host-list ~/hosts.txt "2026-08-01 22:00" "2026-08-15 22:00"')
            self.poutput('  schedule cloud02 host01 "2026-08-01 22:00" "2026-08-15 22:00" description "CI env"')
        else:
            self.poutput("Usage: schedule <count|hostname[,hostname...]|host-list path> description <desc> [options]")
            self.poutput("\nRequest a host assignment (SSM mode).")
            self.poutput("\nOptions:")
            self.poutput("  description <text>       Assignment description (required)")
            self.poutput("  nowipe                   Disable host wiping")
            self.poutput("  vlan <vlan_id>           VLAN ID number")
            self.poutput("  qinq <0|1>              QinQ setting (0=disabled, 1=enabled)")
            self.poutput("  os <title>               OS for provisioning (see os-list)")
            self.poutput("  model <name>             Filter by server model (e.g., r640)")
            self.poutput("  ram <GB>                 Minimum RAM in GB")
            self.poutput("  disk-type <type>         Disk type (nvme, ssd, sata)")
            self.poutput("  disk-size <GB>           Minimum disk size in GB")
            self.poutput("  disk-count <N>           Minimum number of disks")
            self.poutput("  gpu-vendor <vendor>      GPU vendor (e.g., 'NVIDIA Corporation')")
            self.poutput("  gpu-product <product>    GPU model (e.g., 'Tesla V100')")
            self.poutput("  interfaces <N>           Minimum number of network interfaces")
            self.poutput("  nic-vendor <vendor>      NIC vendor (e.g., 'Intel', 'Mellanox')")
            self.poutput("  nic-speed <Gbps>         Minimum NIC speed in Gbps")
            self.poutput("\nExamples:")
            self.poutput('  schedule 3 description "Dev testing"')
            self.poutput('  schedule host01,host02 description "CI" model r640 ram 256')
            self.poutput('  schedule host-list ~/hosts.txt description "Batch"')

    def do_schedule(self, args):
        """Schedule hosts (use 'help schedule' for full options)"""
        if args.strip() in ("?", "-h", "--help"):
            self.help_schedule()
            return
        if self.connection and self.connection.is_admin:
            self.schedule_commands.cmd_schedule_admin(args)
        else:
            self.user_commands.cmd_schedule(args)

    def _filter_completions(self, candidates, text, line, begidx, endidx):
        return self.basic_complete(text, line, begidx, endidx, candidates)

    def _get_arg_position(self, parts, text):
        """Return the 1-based argument position being completed."""
        if text:
            return len(parts) - 1
        return len(parts)

    def complete_schedule(self, text, line, begidx, endidx):
        """Autocomplete for schedule command"""
        if not self.connection or not self.connection.is_authenticated:
            return []

        parts = line.split()

        if self.connection.is_admin:
            return self._complete_schedule_admin(text, line, parts, begidx, endidx)

        return self._complete_schedule_ssm(text, line, parts, begidx, endidx)

    def _complete_schedule_admin(self, text, line, parts, begidx, endidx):
        """Position-aware completion for admin schedule.

        Syntax: schedule <cloud> <hosts|host-list> [path] <start> <end> [options]
        """
        admin_keywords = [
            "description",
            "cloud-owner",
            "cc-users",
            "cloud-ticket",
            "vlan",
            "qinq",
            "os",
            "nowipe",
        ]
        value_keywords = [
            "description",
            "cloud-owner",
            "cc-users",
            "cloud-ticket",
            "vlan",
            "qinq",
            "os",
        ]

        pos = self._get_arg_position(parts, text)

        try:
            if pos == 1:
                clouds = self.connection.api.get_clouds()
                cloud_names = [c.get("name") for c in clouds if c.get("name")]
                return self._filter_completions(cloud_names, text, line, begidx, endidx)

            if pos == 2:
                hosts = self.connection.api.get_hosts()
                hostnames = [h.get("name") for h in hosts]
                candidates = ["host-list"] + hostnames
                return self._filter_completions(candidates, text, line, begidx, endidx)

            prev_word = parts[-2] if text else parts[-1]

            if prev_word == "host-list":
                return self.path_complete(text, line, begidx, endidx)

            has_host_list = "host-list" in parts
            date_start = 4 if has_host_list else 3
            options_start = date_start + 2

            if pos < options_start:
                return []

            if prev_word == "os":
                os_list = self.connection.api.get_os_list()
                os_names = [o.get("Title") for o in os_list if o.get("Title")]
                return self._filter_completions(os_names, text, line, begidx, endidx)

            if prev_word == "vlan":
                vlans = self.connection.api.get_free_vlans()
                vlan_ids = [str(v.get("vlan_id")) for v in vlans if v.get("vlan_id")]
                return self._filter_completions(vlan_ids, text, line, begidx, endidx)

            if prev_word in value_keywords:
                return []

            return self._filter_completions(admin_keywords, text, line, begidx, endidx)
        except Exception:
            pass
        return self.basic_complete(text, line, begidx, endidx, admin_keywords)

    def _complete_schedule_ssm(self, text, line, parts, begidx, endidx):
        """Position-aware completion for SSM schedule.

        Syntax: schedule <count|hostname[,hostname]|host-list path> description <desc> [options]
        """
        ssm_keywords = [
            "description",
            "nowipe",
            "vlan",
            "qinq",
            "os",
            "model",
            "ram",
            "disk-type",
            "disk-size",
            "disk-count",
            "gpu-vendor",
            "gpu-product",
            "interfaces",
            "nic-vendor",
            "nic-speed",
        ]

        pos = self._get_arg_position(parts, text)

        try:
            if pos == 1:
                hosts = self.connection.api.filter_hosts({"can_self_schedule": True})
                hostnames = [h.get("name") for h in hosts]
                count_suggestions = ["1", "2", "3", "5", "10"]
                candidates = ["host-list"] + hostnames + count_suggestions
                return self._filter_completions(candidates, text, line, begidx, endidx)

            prev_word = parts[-2] if text else parts[-1]

            if prev_word == "host-list":
                return self.path_complete(text, line, begidx, endidx)

            if prev_word == "os":
                os_list = self.connection.api.get_os_list()
                os_names = [o.get("Title") for o in os_list if o.get("Title")]
                return self._filter_completions(os_names, text, line, begidx, endidx)

            if prev_word == "vlan":
                vlans = self.connection.api.get_free_vlans()
                vlan_ids = [str(v.get("vlan_id")) for v in vlans if v.get("vlan_id")]
                return self._filter_completions(vlan_ids, text, line, begidx, endidx)

            ssm_value_keywords = [
                "description",
                "vlan",
                "qinq",
                "os",
                "model",
                "ram",
                "disk-type",
                "disk-size",
                "disk-count",
                "gpu-vendor",
                "gpu-product",
                "interfaces",
                "nic-vendor",
                "nic-speed",
            ]
            if prev_word in ssm_value_keywords:
                return []

            return self._filter_completions(ssm_keywords, text, line, begidx, endidx)
        except Exception:
            pass

        return self.basic_complete(text, line, begidx, endidx, ssm_keywords)

    def complete_terminate(self, text, line, begidx, endidx):
        """Autocomplete for terminate command - assignment IDs and hostnames"""
        if not self.connection or not self.connection.is_authenticated:
            return []

        parts = line.split()
        try:
            # If no args yet, suggest assignment IDs
            if len(parts) <= 2:
                username = self.connection.username.split("@")[0]
                assignments = self.connection.api.filter_assignments({"owner": username, "active": True})
                ids = sorted(
                    [str(a.get("id", "")) for a in assignments],
                    key=lambda x: int(x) if x.isdigit() else float("inf"),
                )
                return self.basic_complete(text, line, begidx, endidx, ids)

            # If assignment ID provided, suggest hostnames from that assignment
            if len(parts) >= 2:
                assignment_id = parts[1]
                schedules = self.connection.api.get_schedules({"assignment": assignment_id})
                hostnames = [s.get("host", {}).get("name", "") for s in schedules]
                return self.basic_complete(text, line, begidx, endidx, hostnames)
        except Exception:
            pass
        return []

    def complete_extend(self, text, line, begidx, endidx):
        """Autocomplete for extend command - cloud names or hostnames, then weeks/date"""
        if not self.connection or not self.connection.is_admin:
            return []

        parts = line.split()
        try:
            # First arg: cloud names or hostnames
            if len(parts) <= 2:
                clouds = self.connection.api.get_clouds()
                cloud_names = [c.get("name") for c in clouds]
                # Also get currently scheduled hostnames
                schedules = self.connection.api.get_current_schedules({})
                hostnames = list(set(s.get("host", {}).get("name", "") for s in schedules))
                candidates = cloud_names + hostnames
                return self.basic_complete(text, line, begidx, endidx, candidates)

            # Second arg: "weeks" or "date"
            if len(parts) == 3:
                keywords = ["weeks", "date"]
                return self.basic_complete(text, line, begidx, endidx, keywords)
        except Exception:
            pass
        return []

    def complete_shrink(self, text, line, begidx, endidx):
        """Autocomplete for shrink command - cloud names or hostnames, then mode keywords"""
        if not self.connection or not self.connection.is_admin:
            return []

        parts = line.split()
        try:
            if len(parts) <= 2:
                clouds = self.connection.api.get_clouds()
                cloud_names = [c.get("name") for c in clouds]
                schedules = self.connection.api.get_current_schedules({})
                hostnames = list(set(s.get("host", {}).get("name", "") for s in schedules))
                candidates = cloud_names + hostnames
                return self.basic_complete(text, line, begidx, endidx, candidates)

            if len(parts) == 3:
                keywords = ["weeks", "days", "now", "date"]
                return self.basic_complete(text, line, begidx, endidx, keywords)
        except Exception:
            pass
        return []

    def complete_cloud_delete(self, text, line, begidx, endidx):
        """Autocomplete for cloud-delete command"""
        if not self.connection or not self.connection.is_admin:
            return []

        try:
            clouds = self.connection.api.get_clouds()
            cloud_names = [c.get("name") for c in clouds]
            return self.basic_complete(text, line, begidx, endidx, cloud_names)
        except Exception:
            pass
        return []

    def complete_mod_cloud(self, text, line, begidx, endidx):
        """Autocomplete for mod-cloud command"""
        if not self.connection or not self.connection.is_admin:
            return []

        parts = line.split()
        try:
            # First arg: cloud name
            if len(parts) <= 2:
                clouds = self.connection.api.get_clouds()
                cloud_names = [c.get("name") for c in clouds]
                return self.basic_complete(text, line, begidx, endidx, cloud_names)

            # Subsequent args: attributes
            keywords = [
                "cloud-owner",
                "description",
                "cloud-ticket",
                "cc-users",
                "vlan",
                "qinq",
                "os",
                "wipe",
                "nowipe",
            ]
            return self.basic_complete(text, line, begidx, endidx, keywords)
        except Exception:
            pass
        return []

    def complete_cloud_list(self, text, line, begidx, endidx):
        """Autocomplete for cloud-list command"""
        if not self.connection or not self.connection.is_connected:
            return []

        parts = line.split()
        try:
            keywords = ["cloud", "detail"]

            # If looking for cloud name after cloud keyword
            if len(parts) > 1 and parts[-2] == "cloud":
                clouds = self.connection.api.get_clouds()
                cloud_names = [c.get("name") for c in clouds]
                return self.basic_complete(text, line, begidx, endidx, cloud_names)

            # Otherwise suggest keywords
            return self.basic_complete(text, line, begidx, endidx, keywords)
        except Exception:
            pass
        return []

    def complete_mark_broken(self, text, line, begidx, endidx):
        """Autocomplete for mark-broken command"""
        if not self.connection or not self.connection.is_admin:
            return []

        try:
            hosts = self.connection.api.get_hosts()
            # Filter out already broken hosts
            hostnames = [h.get("name") for h in hosts if not h.get("broken", False)]
            return self.basic_complete(text, line, begidx, endidx, hostnames)
        except Exception:
            pass
        return []

    def complete_mark_repaired(self, text, line, begidx, endidx):
        """Autocomplete for mark-repaired command"""
        if not self.connection or not self.connection.is_admin:
            return []

        try:
            # Only show broken hosts
            hosts = self.connection.api.filter_hosts({"broken": True})
            hostnames = [h.get("name") for h in hosts]
            return self.basic_complete(text, line, begidx, endidx, hostnames)
        except Exception:
            pass
        return []

    def complete_retire(self, text, line, begidx, endidx):
        """Autocomplete for retire command"""
        if not self.connection or not self.connection.is_admin:
            return []

        try:
            hosts = self.connection.api.get_hosts()
            # Filter out already retired hosts
            hostnames = [h.get("name") for h in hosts if not h.get("retired", False)]
            return self.basic_complete(text, line, begidx, endidx, hostnames)
        except Exception:
            pass
        return []

    def complete_unretire(self, text, line, begidx, endidx):
        """Autocomplete for unretire command"""
        if not self.connection or not self.connection.is_admin:
            return []

        try:
            # Only show retired hosts
            hosts = self.connection.api.filter_hosts({"retired": True})
            hostnames = [h.get("name") for h in hosts]
            return self.basic_complete(text, line, begidx, endidx, hostnames)
        except Exception:
            pass
        return []

    def complete_ls_schedule(self, text, line, begidx, endidx):
        """Autocomplete for ls-schedule command"""
        if not self.connection or not self.connection.is_connected:
            return []

        parts = line.split()
        try:
            keywords = ["host", "cloud"]

            # If looking for hostname after host keyword
            if len(parts) > 1 and parts[-2] == "host":
                hosts = self.connection.api.get_hosts()
                hostnames = [h.get("name") for h in hosts]
                return self.basic_complete(text, line, begidx, endidx, hostnames)

            # If looking for cloud name after cloud keyword
            if len(parts) > 1 and parts[-2] == "cloud":
                clouds = self.connection.api.get_clouds()
                cloud_names = [c.get("name") for c in clouds]
                return self.basic_complete(text, line, begidx, endidx, cloud_names)

            # Otherwise suggest keywords
            return self.basic_complete(text, line, begidx, endidx, keywords)
        except Exception:
            pass
        return []

    def complete_mod_schedule(self, text, line, begidx, endidx):
        """Autocomplete for mod-schedule command"""
        if not self.connection or not self.connection.is_admin:
            return []

        parts = line.split()
        try:
            keywords = ["id", "start", "end"]

            # If looking for schedule ID after id keyword
            if len(parts) > 1 and parts[-2] == "id":
                schedules = self.connection.api.get_schedules({})
                schedule_ids = [str(s.get("id")) for s in schedules]
                return self.basic_complete(text, line, begidx, endidx, schedule_ids)

            # Otherwise suggest keywords
            return self.basic_complete(text, line, begidx, endidx, keywords)
        except Exception:
            pass
        return []

    def complete_edit_server(self, text, line, begidx, endidx):
        """Autocomplete for edit-server command"""
        if not self.config:
            return []

        parts = line.split()
        try:
            # First arg: server name
            if len(parts) <= 2:
                servers = list(self.config.get_all_servers().keys())
                return self.basic_complete(text, line, begidx, endidx, servers)

            # Subsequent args: attributes
            keywords = ["url", "username", "password", "token", "verify"]
            return self.basic_complete(text, line, begidx, endidx, keywords)
        except Exception:
            pass
        return []

    def complete_rm_server(self, text, line, begidx, endidx):
        """Autocomplete for rm-server command"""
        if not self.config:
            return []

        try:
            servers = list(self.config.get_all_servers().keys())
            # Exclude currently connected server
            if self.connection and self.connection.current_server:
                servers = [s for s in servers if s != self.connection.current_server]
            return self.basic_complete(text, line, begidx, endidx, servers)
        except Exception:
            pass
        return []

    def do_my_hosts(self, args):
        """Show your currently scheduled hosts"""
        self.user_commands.cmd_my_hosts(args)

    def do_my_assignments(self, args):
        """List your self-scheduled assignments"""
        self.user_commands.cmd_my_assignments(args)

    def do_terminate(self, args):
        """Terminate assignment or release host"""
        self.user_commands.cmd_terminate(args)

    def do_ls_hosts(self, args):
        """List all hosts"""
        self.host_commands.cmd_ls_hosts(args)

    def do_mark_broken(self, args):
        """Mark a host as broken"""
        self.host_commands.cmd_mark_broken(args)

    def do_mark_repaired(self, args):
        """Mark a broken host as repaired"""
        self.host_commands.cmd_mark_repaired(args)

    def do_retire(self, args):
        """Mark a host as retired"""
        self.host_commands.cmd_retire(args)

    def do_unretire(self, args):
        """Mark a retired host as active"""
        self.host_commands.cmd_unretire(args)

    def do_ls_broken(self, args):
        """List all broken hosts"""
        self.host_commands.cmd_ls_broken(args)

    def do_ls_retired(self, args):
        """List all retired hosts"""
        self.host_commands.cmd_ls_retired(args)

    def do_ls_schedule(self, args):
        """List schedules"""
        self.schedule_commands.cmd_ls_schedule(args)

    def do_mod_schedule(self, args):
        """Modify a schedule"""
        self.schedule_commands.cmd_mod_schedule(args)

    def do_extend(self, args):
        """Extend a schedule"""
        self.schedule_commands.cmd_extend(args)

    def do_shrink(self, args):
        """Shrink a schedule"""
        self.schedule_commands.cmd_shrink(args)

    def complete_ls_available(self, text, line, begidx, endidx):
        """Autocomplete for ls_available command - filter keywords"""
        keywords = [
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
        return self.basic_complete(text, line, begidx, endidx, keywords)

    def do_ls_available(self, args):
        """List available hosts"""
        self.available_commands.cmd_ls_available(args)

    def complete_cloud_only(self, text, line, begidx, endidx):
        """Autocomplete for cloud-only command"""
        if not self.connection or not self.connection.is_authenticated:
            return []
        try:
            clouds = self.connection.api.get_clouds()
            cloud_names = [c.get("name") for c in clouds if c.get("name")]
            return self.basic_complete(text, line, begidx, endidx, cloud_names)
        except Exception:
            pass
        return []

    def do_move_status(self, args):
        """Show move/rebuild progress. Usage: move_status [hostname]"""
        self.move_commands.cmd_move_status(args)

    def complete_move_status(self, text, line, begidx, endidx):
        """Autocomplete for move-status command"""
        if not self.connection or not self.connection.is_authenticated:
            return []
        try:
            hosts = self.connection.api.get_hosts()
            hostnames = [h.get("name") for h in hosts if h.get("name")]
            return self.basic_complete(text, line, begidx, endidx, hostnames)
        except Exception:
            pass
        return []

    def do_track(self, args):
        """Live-track move/rebuild progress. Usage: track [hostname|cloudname]"""
        self.track_commands.cmd_track(args)

    def complete_track(self, text, line, begidx, endidx):
        """Autocomplete for track command"""
        if not self.connection or not self.connection.is_authenticated:
            return []
        try:
            hosts = self.connection.api.get_hosts()
            hostnames = [h.get("name") for h in hosts if h.get("name")]
            clouds = self.connection.api.get_clouds()
            cloud_names = [c.get("name") for c in clouds if c.get("name")]
            candidates = hostnames + cloud_names
            return self.basic_complete(text, line, begidx, endidx, candidates)
        except Exception:
            pass
        return []

    def do_activity(self, args):
        """Show active moves grouped by cloud. Usage: activity"""
        self.move_commands.cmd_activity(args)

    def do_servers(self, args):
        """List all configured servers"""
        self.server_commands.cmd_servers(args)

    def do_add_server(self, args):
        """Add a new server to configuration"""
        self.server_commands.cmd_add_server(args)

    def do_add_quads_server(self, args):
        """Interactive wizard to add a new QUADS server"""
        self.server_commands.cmd_add_quads_server(args)

    def do_edit_server(self, args):
        """Edit an existing server configuration"""
        self.server_commands.cmd_edit_server(args)

    def do_rm_server(self, args):
        """Remove a server from configuration"""
        self.server_commands.cmd_rm_server(args)

    def do_config_reload(self, args):
        """Reload configuration from file"""
        self.server_commands.cmd_config_reload(args)

    def do_session_create(self, args):
        """Create new session"""
        self.session_commands.cmd_session_create(args)

    def complete_session_create(self, text, line, begidx, endidx):
        """Autocomplete for session-create command"""
        servers = []
        if self.config:
            servers = list(self.config.get_all_servers().keys())
        return self.basic_complete(text, line, begidx, endidx, servers)

    def do_session_switch(self, args):
        """Switch active session"""
        self.session_commands.cmd_session_switch(args)

    def complete_session_switch(self, text, line, begidx, endidx):
        """Autocomplete for session-switch command"""
        if not self.session_manager:
            return []
        sessions = self.session_manager.list_sessions()
        candidates = [str(s.id) for s in sessions]
        return self.basic_complete(text, line, begidx, endidx, candidates)

    def do_session(self, args):
        """Quick switch to session by ID or label"""
        self.session_commands.cmd_session(args)

    def complete_session(self, text, line, begidx, endidx):
        """Autocomplete for session command"""
        if not self.session_manager:
            return []
        sessions = self.session_manager.list_sessions()
        candidates = [str(s.id) for s in sessions] + [s.label for s in sessions if s.label]
        return self.basic_complete(text, line, begidx, endidx, candidates)

    def do_session_list(self, args):
        """List all sessions"""
        self.session_commands.cmd_session_list(args)

    def do_session_close(self, args):
        """Close session"""
        self.session_commands.cmd_session_close(args)

    def complete_session_close(self, text, line, begidx, endidx):
        """Autocomplete for session-close command"""
        if not self.session_manager:
            return []
        sessions = self.session_manager.list_sessions()
        candidates = [str(s.id) for s in sessions]
        return self.basic_complete(text, line, begidx, endidx, candidates)

    def do_session_close_all(self, args):
        """Close all inactive sessions"""
        self.session_commands.cmd_session_close_all(args)

    def do_mod_cloud(self, args):
        """Modify cloud attributes"""
        self.cloud_commands.cmd_mod_cloud(args)

    def _auto_connect_for_oneshot(self, cmd_str):
        """Auto-connect to default server for one-shot commands that need it"""
        # Commands that don't require connection
        no_connection_cmds = [
            "version",
            "help",
            "servers",
            "exit",
            "quit",
            "add_quads_server",
            "add_server",
            "edit_server",
            "rm_server",
            "config_reload",
        ]
        cmd_name = cmd_str.split()[0] if cmd_str else ""

        # Skip auto-connect for commands that don't need it
        if cmd_name in no_connection_cmds:
            return True

        if not self.config:
            self.perror("Configuration not loaded")
            return False

        # Check if already connected (active_session is a property, not a method)
        if self.session_manager and self.session_manager.active_session:
            return True

        # Get default server
        default_server = self.config.get_default_server()
        if not default_server:
            self.perror("No default server configured")
            self.perror("Hint: Set default_server in ~/.config/quads/quads-client.yml")
            return False

        # Connect to default server (silent)
        try:
            self.connection_commands.cmd_connect(default_server)
            return True
        except Exception as e:
            self.perror(f"Auto-connect failed: {e}")
            return False

    def execute_oneshot_command(self, cmd_str):
        """
        Execute a single command in one-shot mode and return exit code.

        Supports special syntax: "connect <server> <command> <args>"
        This allows specifying a non-default server for one-shot commands.

        Args:
            cmd_str: Command string to execute

        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        # Check for "connect <server> <command>" pattern in one-shot mode
        actual_command = cmd_str
        if cmd_str.startswith("connect "):
            parts = cmd_str.split(None, 2)  # Split into at most 3 parts: ["connect", server, rest]

            # If there are 3+ parts and the third part doesn't look like a connect keyword
            if len(parts) >= 3:
                # Check if third part is a keyword for connect command
                third_word = parts[2].split()[0] if parts[2] else ""
                if third_word not in ["session", "label"]:
                    # Pattern: connect <server> <command> <args>
                    # Execute connect first, then the subsequent command
                    server_name = parts[1]
                    next_command = parts[2]

                    try:
                        # Don't use auto-connect; connect explicitly to specified server
                        self.connection_commands.cmd_connect(server_name)
                    except Exception as e:
                        self.perror(f"Connection failed: {e}")
                        return 3

                    # Now execute the actual command
                    actual_command = next_command

        # Auto-connect if needed (for commands without explicit connect)
        if not actual_command.startswith("connect") and not self._auto_connect_for_oneshot(actual_command):
            return 3  # Exit code 3: Connection error

        # Execute the command
        try:
            # onecmd returns True if the command wants to stop cmdloop, False otherwise
            # We don't care about the return value for one-shot mode
            self.onecmd(actual_command)
            return 0  # Success
        except KeyboardInterrupt:
            return 130  # Standard exit code for Ctrl+C
        except Exception as e:
            self.perror(f"Error: {e}")
            return 1  # General error
