"""Session management commands"""

from datetime import datetime

from rich.table import Table


class SessionCommands:
    def __init__(self, shell):
        self.shell = shell

    def cmd_session_create(self, args):
        """
        Create new session.
        Usage: session-create <server_name> [label <name>]
        """
        if not args.strip():
            self.shell.perror("Usage: session-create <server_name> [label <name>]")
            return

        parts = args.split()
        server_name = None
        label = None

        # Parse arguments (server_name is positional, label is keyword)
        i = 0
        while i < len(parts):
            if parts[i] == "label" and i + 1 < len(parts):
                label = parts[i + 1]
                i += 2
            else:
                # First non-keyword argument is server name
                if server_name is None:
                    server_name = parts[i]
                i += 1

        if not server_name:
            self.shell.perror("Usage: session-create <server_name> [label <name>]")
            return

        try:
            session = self.shell.session_manager.create_session(server_name, label)
            session.connection.connect(server_name)
            self.shell._update_prompt()
            self.shell._update_visible_commands()
            self.shell.poutput(f"Created session {session.id} ({session.label})")
        except Exception as e:
            self.shell.perror(f"Failed to create session: {e}")

    def cmd_session_switch(self, args):
        """
        Switch active session.
        Usage: session-switch [session_id]

        Without arguments, toggles to previous session (like screen Ctrl+A Ctrl+A).
        With session_id, switches to that specific session.
        """
        session_id = args.strip()

        # If no session_id provided, toggle to previous session
        if not session_id:
            session_id = self.shell.session_manager.previous_session_id
            if session_id is None:
                if self.shell.rich_console:
                    self.shell.rich_console.console.print("[yellow]No previous session to switch to[/yellow]")
                else:
                    self.shell.poutput("No previous session to switch to")
                return

        # Check if already on this session
        if session_id == self.shell.session_manager.active_session_id:
            session = self.shell.session_manager.get_session(session_id)
            if session:
                self.shell.poutput(f"Already on session {session_id} ({session.label})")
            return

        try:
            self.shell.session_manager.switch_session(session_id)
            session = self.shell.session_manager.get_session(session_id)
            self.shell._update_prompt()
            self.shell._update_visible_commands()
            self.shell.poutput(f"Switched to session {session_id} ({session.label})")
        except ValueError as e:
            self.shell.perror(str(e))

    def cmd_session(self, args):
        """
        Quick switch to session by ID or label.
        Usage: session <session_id|label>
        """
        target = args.strip()

        if not target or target in ("?", "-h", "--help"):
            self.shell.poutput("Usage: session <session_id|label>")
            self.shell.poutput("\nQuick switch to a session by ID or label.")
            self.shell.poutput("See also: session-list, session-switch")
            return

        # Try as session ID first
        session = self.shell.session_manager.get_session(target)

        # If not found, try as label
        if not session:
            session = self.shell.session_manager.get_session_by_label(target)

        if session:
            # Check if already on this session
            if session.id == self.shell.session_manager.active_session_id:
                self.shell.poutput(f"Already on session {session.id} ({session.label})")
                return

            try:
                self.shell.session_manager.switch_session(session.id)
                self.shell._update_prompt()
                self.shell._update_visible_commands()
                self.shell.poutput(f"Switched to session {session.id} ({session.label})")
            except ValueError as e:
                self.shell.perror(str(e))
        else:
            self.shell.perror(f"Session not found: {target}")

    def cmd_session_list(self, args):
        """List all sessions"""
        sessions = self.shell.session_manager.list_sessions()

        if not sessions:
            self.shell.poutput("No active sessions")
            return

        # Use RichConsole helper if available
        if self.shell.rich_console:
            self._print_session_table_rich(sessions)
        else:
            self._print_session_table_plain(sessions)

    def _print_session_table_rich(self, sessions):
        """Print session table using rich formatting"""
        table = Table(title="Active Sessions", show_header=True, header_style="bold cyan")

        table.add_column("Session", style="cyan", width=10)
        table.add_column("Server", style="dim", width=26)
        table.add_column("Label", width=9)
        table.add_column("Version", width=9)
        table.add_column("Status", width=14)
        table.add_column("Last Active", width=14)

        active_id = self.shell.session_manager.active_session_id

        for session in sessions:
            # Get version
            version = session.get_version()

            # Format session ID
            session_id = session.id

            # Format status with indicator
            if session.connection.is_connected:
                if session.id == active_id:
                    status = "[green]● Active ✓[/green]"
                else:
                    status = "[yellow]● Idle[/yellow]"
            else:
                status = "[red]✗ Offline[/red]"

            # Format last active time
            now = datetime.now()
            delta = now - session.last_active
            if delta.total_seconds() < 60:
                last_active = "now"
            elif delta.total_seconds() < 3600:
                minutes = int(delta.total_seconds() / 60)
                last_active = f"{minutes}m ago"
            elif delta.total_seconds() < 86400:
                hours = int(delta.total_seconds() / 3600)
                last_active = f"{hours}h ago"
            else:
                days = int(delta.total_seconds() / 86400)
                last_active = f"{days}d ago"

            table.add_row(session_id, session.server_name, session.label, version, status, last_active)

        self.shell.rich_console.console.print(table)

    def _print_session_table_plain(self, sessions):
        """Print session table in plain text format"""
        from tabulate import tabulate

        active_id = self.shell.session_manager.active_session_id
        table_data = []

        for session in sessions:
            version = session.get_version()
            session_id = f"{session.id} (*)" if session.id == active_id else session.id

            if session.connection.is_connected:
                status = "Active" if session.id == active_id else "Idle"
            else:
                status = "Offline"

            # Format last active time
            now = datetime.now()
            delta = now - session.last_active
            if delta.total_seconds() < 60:
                last_active = "now"
            elif delta.total_seconds() < 3600:
                minutes = int(delta.total_seconds() / 60)
                last_active = f"{minutes}m ago"
            else:
                hours = int(delta.total_seconds() / 3600)
                last_active = f"{hours}h ago"

            table_data.append([session_id, session.server_name, session.label, version, status, last_active])

        headers = ["Session", "Server", "Label", "Version", "Status", "Last Active"]
        self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))

    def cmd_session_close(self, args):
        """
        Close session.
        Usage: session-close <session_id>
        """
        session_id = args.strip()

        if not session_id:
            self.shell.perror("Usage: session-close <session_id>")
            return

        session = self.shell.session_manager.get_session(session_id)
        if not session:
            self.shell.perror(f"Session not found: {session_id}")
            return

        label = session.label
        self.shell.session_manager.close_session(session_id)
        self.shell._update_prompt()
        self.shell._update_visible_commands()
        self.shell.poutput(f"Closed session {session_id} ({label})")

    def cmd_session_close_all(self, args):
        """Close all inactive sessions"""
        count = self.shell.session_manager.close_all_inactive()
        if count > 0:
            self.shell._update_prompt()
            self.shell._update_visible_commands()
            self.shell.poutput(f"Closed {count} inactive session{'s' if count > 1 else ''}")
        else:
            self.shell.poutput("No inactive sessions to close")
