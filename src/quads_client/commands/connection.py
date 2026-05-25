class ConnectionCommands:
    def __init__(self, shell):
        self.shell = shell

    def cmd_connect(self, args):
        """Connect to a QUADS server. Usage: connect [server_name | number] [session <label>]"""
        if not self.shell.session_manager:
            self.shell.perror("Configuration not loaded")
            return

        parts = args.split()
        session_label = None

        # Parse session keyword
        i = 0
        server_parts = []
        while i < len(parts):
            if parts[i] == "session" and i + 1 < len(parts):
                session_label = parts[i + 1]
                i += 2
            else:
                server_parts.append(parts[i])
                i += 1

        # Determine server name
        if not server_parts:
            default = self.shell.config.get_default_server() if self.shell.config else None
            if default:
                server_name = default
                self.shell.poutput(f"Connecting to default server: {default}")
            else:
                all_servers = self.shell.config.get_all_servers() if self.shell.config else {}
                servers = list(all_servers.keys())
                self.shell.poutput("Available servers:")
                for i, server in enumerate(servers, 1):
                    self.shell.poutput(f"  {i}. {server}")
                self.shell.poutput("\nUsage: connect <server_name|number> [session <label>]")
                return
        else:
            arg = server_parts[0]
            # Check if arg is a number (server index)
            if arg.isdigit():
                server_index = int(arg)
                all_servers = self.shell.config.get_all_servers() if self.shell.config else {}
                servers = list(all_servers.keys())
                if server_index < 1 or server_index > len(servers):
                    self.shell.perror(f"Invalid server number: {server_index}")
                    self.shell.perror(f"Available servers: 1-{len(servers)}")
                    return
                # Convert to 0-based index
                server_name = servers[server_index - 1]
            else:
                server_name = arg

        try:
            from quads_client.connection import ConnectionError

            # Create session
            session = self.shell.session_manager.create_session(server_name, session_label)
            session.connection.connect(server_name)

            self.shell._update_prompt()
            self.shell._update_visible_commands()

            # Check if we're in registration mode (no credentials)
            # Suppress connection messages in quiet mode (one-shot commands)
            if not self.shell.quiet:
                if session.connection._registration_mode:
                    self.shell.poutput(f"OK: Connected to {server_name} (session {session.id})")
                    self.shell.poutput("  No credentials configured. Authenticate with:")
                    self.shell.poutput("    token-login              (SSO token)")
                    self.shell.poutput("    register <email> <pass>  (new account)")
                else:
                    username = session.connection.username
                    self.shell.poutput(f"OK: Connected to {server_name} as {username} (session {session.id})")
        except ConnectionError as e:
            self.shell.perror(str(e))

    def cmd_disconnect(self, args):
        """Disconnect from current QUADS server"""
        if not self.shell.connection or not self.shell.connection.is_connected:
            self.shell.pwarning("Not connected to any server")
            return

        server = self.shell.connection.current_server
        self.shell.connection.disconnect()
        self.shell._update_prompt()
        self.shell._update_visible_commands()
        self.shell.poutput(f"Disconnected from {server}")

    def cmd_status(self, args):
        """Show current connection status and all active sessions"""
        if not self.shell.session_manager:
            self.shell.perror("Configuration not loaded")
            return

        # Get active session info
        active_session = self.shell.session_manager.active_session

        if active_session and active_session.connection.is_connected:
            server = active_session.connection.current_server
            url = self.shell.config.get_server_url(server)
            username = active_session.connection.username
            version = active_session.get_version()

            from quads_client.utils import get_ssl_status_text

            ssl_status = get_ssl_status_text(url, self.shell.config.get_server_verify(server))

            self.shell.poutput(f"Current Session: {active_session.id} ({active_session.label})")
            self.shell.poutput(f"Server: {server}")
            self.shell.poutput(f"Version: {version}")
            self.shell.poutput(f"Status: Connected (authenticated as {username})")
            self.shell.poutput(f"SSL: {ssl_status}")
        else:
            self.shell.poutput("Not connected")

        # Show all sessions if more than one exists
        sessions = self.shell.session_manager.list_sessions()
        if len(sessions) > 1:
            self.shell.poutput("\nAll Sessions:")
            for session in sessions:
                active_marker = " *" if session.id == self.shell.session_manager.active_session_id else ""
                status = "connected" if session.connection.is_connected else "offline"

                # Format last active time
                from datetime import datetime

                now = datetime.now()
                delta = now - session.last_active
                if delta.total_seconds() < 60:
                    last_active = "active"
                elif delta.total_seconds() < 3600:
                    minutes = int(delta.total_seconds() / 60)
                    last_active = f"{minutes}m ago"
                else:
                    hours = int(delta.total_seconds() / 3600)
                    last_active = f"{hours}h ago"

                session_line = (
                    f"  {session.id}. {session.label:10} - {session.server_name} "
                    f"({status}, {last_active}){active_marker}"
                )
                self.shell.poutput(session_line)
