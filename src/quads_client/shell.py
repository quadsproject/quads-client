import cmd2

from quads_client.commands.available import AvailableCommands
from quads_client.commands.cloud import CloudCommands
from quads_client.commands.connection import ConnectionCommands
from quads_client.commands.host import HostCommands
from quads_client.commands.moves import MoveCommands
from quads_client.commands.schedule import ScheduleCommands
from quads_client.commands.server import ServerCommands
from quads_client.commands.session import SessionCommands
from quads_client.commands.user import UserCommands
from quads_client.commands.version import VersionCommands
from quads_client.config import ConfigError, QuadsClientConfig
from quads_client.history import CommandHistory
from quads_client.rich_console import RichConsole
from quads_client.session_manager import SessionManager
from quads_client.utils import get_ssl_indicator


def _rl(ansi):
    """Wrap ANSI escape code for readline (mark as non-printing)"""
    return f"\001{ansi}\002"


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

        self.connection_commands = ConnectionCommands(self)
        self.version_commands = VersionCommands(self)
        self.cloud_commands = CloudCommands(self)
        self.user_commands = UserCommands(self)
        self.host_commands = HostCommands(self)
        self.schedule_commands = ScheduleCommands(self)
        self.available_commands = AvailableCommands(self)
        self.move_commands = MoveCommands(self)
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
                admin_badge = f" {_rl(chr(27) + '[1;31m')}[ADMIN]{_rl(chr(27) + '[0m')}"

            self.prompt = f"{_rl(color)}{symbol} {session_info}({short_name}){admin_badge}{_rl(chr(27) + '[0m')} > "
        else:
            self.prompt = f"{_rl(chr(27) + '[1;31m')}(disconnected){_rl(chr(27) + '[0m')} > "

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
            "cloud_only",
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
            "ls_available",
            "os_list",
            "move_status",
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
        """Connect to a QUADS server. Usage: connect [server_name]"""
        self.connection_commands.cmd_connect(args)

    def complete_connect(self, text, line, begidx, endidx):
        """Autocomplete for connect command"""
        servers = []
        if self.connection:
            servers = self.connection.get_available_servers()
        elif self.config:
            servers = list(self.config.get_all_servers().keys())
        if text:
            return [s for s in servers if s.startswith(text)]
        return servers

    def do_disconnect(self, args):
        """Disconnect from current QUADS server"""
        self.connection_commands.cmd_disconnect(args)

    def do_status(self, args):
        """Show current connection status"""
        self.connection_commands.cmd_status(args)

    def do_cloud_list(self, args):
        """List all clouds (admin only)"""
        self.cloud_commands.cmd_cloud_list(args)

    def do_find_free_cloud(self, args):
        """Find clouds without active assignments (admin only)"""
        self.cloud_commands.cmd_find_free_cloud(args)

    def do_cloud_only(self, args):
        """List hosts assigned to a specific cloud (admin only)"""
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

    def do_schedule(self, args):
        """
        Unified schedule command (role-aware)
        SSM mode: schedule <count|hosts|host-list path> description <desc> [options]
        Admin mode: schedule <cloud> <hosts|host-list path> <start> <end>
        """
        # Route to appropriate handler based on role
        if self.connection and self.connection.is_admin:
            self.schedule_commands.cmd_schedule_admin(args)
        else:
            self.user_commands.cmd_schedule(args)

    def complete_schedule(self, text, line, begidx, endidx):
        """Autocomplete for schedule command"""
        if not self.connection or not self.connection.is_authenticated:
            return []

        parts = line.split()
        keywords = [
            "description",
            "nowipe",
            "vlan",
            "qinq",
            "os",
            "model",
            "ram",
            "host-list",
        ]

        # For admin mode, try to get cloud names
        if self.connection.is_admin:
            try:
                # First arg: cloud names
                if len(parts) <= 2:
                    clouds = self.connection.api.get_clouds()
                    cloud_names = [c.get("name") for c in clouds if c.get("name")]
                    if text:
                        return [c for c in cloud_names if c.startswith(text)]
                    return cloud_names
                # Later args: hostnames or keywords
                else:
                    hosts = self.connection.api.get_hosts()
                    hostnames = [h.get("name") for h in hosts]
                    candidates = keywords + hostnames
                    if text:
                        return [c for c in candidates if c.startswith(text)]
                    return candidates
            except Exception:
                pass

        # SSM mode
        try:
            # First arg: available hostnames (can_self_schedule) or count suggestions
            if len(parts) <= 2:
                hosts = self.connection.api.filter_hosts({"can_self_schedule": True})
                hostnames = [h.get("name") for h in hosts]
                # Also suggest common counts
                count_suggestions = ["1", "2", "3", "5", "10"]
                candidates = hostnames + count_suggestions
                if text:
                    return [c for c in candidates if c.startswith(text)]
                return candidates
            # After first arg (count/hosts/host-list): only keywords
            else:
                if text:
                    return [k for k in keywords if k.startswith(text)]
                return keywords
        except Exception:
            pass

        return keywords

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
                ids = [str(a.get("id", "")) for a in assignments]
                if text:
                    return [i for i in ids if i.startswith(text)]
                return ids

            # If assignment ID provided, suggest hostnames from that assignment
            if len(parts) >= 2:
                assignment_id = parts[1]
                schedules = self.connection.api.get_schedules({"assignment": assignment_id})
                hostnames = [s.get("host", {}).get("name", "") for s in schedules]
                if text:
                    return [h for h in hostnames if h.startswith(text)]
                return hostnames
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
                if text:
                    return [c for c in candidates if c.startswith(text)]
                return candidates

            # Second arg: "weeks" or "date"
            if len(parts) == 3:
                keywords = ["weeks", "date"]
                if text:
                    return [k for k in keywords if k.startswith(text)]
                return keywords
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
                if text:
                    return [c for c in candidates if c.startswith(text)]
                return candidates

            if len(parts) == 3:
                keywords = ["weeks", "days", "now", "date"]
                if text:
                    return [k for k in keywords if k.startswith(text)]
                return keywords
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
            if text:
                return [c for c in cloud_names if c.startswith(text)]
            return cloud_names
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
                if text:
                    return [c for c in cloud_names if c.startswith(text)]
                return cloud_names

            # Subsequent args: attributes
            keywords = [
                "cloud-owner",
                "description",
                "cloud-ticket",
                "cc-users",
                "vlan",
                "qinq",
                "wipe",
                "nowipe",
            ]
            if text:
                return [k for k in keywords if k.startswith(text)]
            return keywords
        except Exception:
            pass
        return []

    def complete_cloud_list(self, text, line, begidx, endidx):
        """Autocomplete for cloud-list command"""
        if not self.connection or not self.connection.is_connected:
            return []

        parts = line.split()
        try:
            keywords = ["--cloud", "--detail"]

            # If looking for cloud name after --cloud
            if len(parts) > 1 and parts[-2] == "--cloud":
                clouds = self.connection.api.get_clouds()
                cloud_names = [c.get("name") for c in clouds]
                if text:
                    return [c for c in cloud_names if c.startswith(text)]
                return cloud_names

            # Otherwise suggest keywords
            if text:
                return [k for k in keywords if k.startswith(text)]
            return keywords
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
            if text:
                return [h for h in hostnames if h.startswith(text)]
            return hostnames
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
            if text:
                return [h for h in hostnames if h.startswith(text)]
            return hostnames
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
            if text:
                return [h for h in hostnames if h.startswith(text)]
            return hostnames
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
            if text:
                return [h for h in hostnames if h.startswith(text)]
            return hostnames
        except Exception:
            pass
        return []

    def complete_ls_schedule(self, text, line, begidx, endidx):
        """Autocomplete for ls-schedule command"""
        if not self.connection or not self.connection.is_connected:
            return []

        parts = line.split()
        try:
            keywords = ["--host", "--cloud"]

            # If looking for hostname after --host
            if len(parts) > 1 and parts[-2] == "--host":
                hosts = self.connection.api.get_hosts()
                hostnames = [h.get("name") for h in hosts]
                if text:
                    return [h for h in hostnames if h.startswith(text)]
                return hostnames

            # If looking for cloud name after --cloud
            if len(parts) > 1 and parts[-2] == "--cloud":
                clouds = self.connection.api.get_clouds()
                cloud_names = [c.get("name") for c in clouds]
                if text:
                    return [c for c in cloud_names if c.startswith(text)]
                return cloud_names

            # Otherwise suggest keywords
            if text:
                return [k for k in keywords if k.startswith(text)]
            return keywords
        except Exception:
            pass
        return []

    def complete_mod_schedule(self, text, line, begidx, endidx):
        """Autocomplete for mod-schedule command"""
        if not self.connection or not self.connection.is_admin:
            return []

        parts = line.split()
        try:
            keywords = ["--id", "--start", "--end"]

            # If looking for schedule ID after --id
            if len(parts) > 1 and parts[-2] == "--id":
                schedules = self.connection.api.get_schedules({})
                schedule_ids = [str(s.get("id")) for s in schedules]
                if text:
                    return [i for i in schedule_ids if i.startswith(text)]
                return schedule_ids

            # Otherwise suggest keywords
            if text:
                return [k for k in keywords if k.startswith(text)]
            return keywords
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
                if text:
                    return [s for s in servers if s.startswith(text)]
                return servers

            # Subsequent args: attributes
            keywords = ["--url", "--username", "--password", "--token", "--verify"]
            if text:
                return [k for k in keywords if k.startswith(text)]
            return keywords
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
            if text:
                return [s for s in servers if s.startswith(text)]
            return servers
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

    def do_ls_available(self, args):
        """List available hosts"""
        self.available_commands.cmd_ls_available(args)

    def do_move_status(self, args):
        """Show move/rebuild progress. Usage: move_status [hostname]"""
        self.move_commands.cmd_move_status(args)

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

    def do_session_switch(self, args):
        """Switch active session"""
        self.session_commands.cmd_session_switch(args)

    def do_session(self, args):
        """Quick switch to session by ID or label"""
        self.session_commands.cmd_session(args)

    def do_session_list(self, args):
        """List all sessions"""
        self.session_commands.cmd_session_list(args)

    def do_session_close(self, args):
        """Close session"""
        self.session_commands.cmd_session_close(args)

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
