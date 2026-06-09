import getpass

from tabulate import tabulate

from quads_client.arg_parser import parse_schedule_ssm_args
from quads_client.error_handler import auto_refresh_on_auth_error, handle_api_error, require_auth, require_connection
from quads_client.utils import (
    extract_assignment_id,
    extract_cloud_name,
    extract_cloud_number,
    extract_hostname,
    get_username_short,
)


class UserCommands:
    def __init__(self, shell):
        self.shell = shell

    def _require_connection(self):
        """Check if connected to a server"""
        return require_connection(self.shell)

    def _require_auth(self):
        """Check if user is authenticated"""
        return require_auth(self.shell)

    def cmd_register(self, args):
        """Register a new user. Usage: register <email> <password>"""
        if not self._require_connection():
            return

        parts = args.strip().split()
        if len(parts) < 2:
            self.shell.perror("Usage: register <email> <password>")
            return

        email = parts[0]
        password = parts[1]

        try:
            # Set credentials on API instance for registration
            self.shell.connection.api.username = email
            self.shell.connection.api.password = password
            result = self.shell.connection.api.register()

            # Check for registration disabled (require_auth_provider: true)
            if isinstance(result, dict) and result.get("status_code") == 403:
                self.shell.perror("Registration is disabled on this server.")
                self.shell.poutput("This server requires SSO authentication.")
                self.shell.poutput("To authenticate with an SSO token:")
                self.shell.poutput("  1. Visit the QUADS web portal and log in via SSO")
                self.shell.poutput("  2. Go to Profile > API Tokens and generate a token")
                self.shell.poutput("  3. Run: token-login")
                return

            # Check if user already exists - attempt auto-login
            if isinstance(result, dict) and result.get("message"):
                message = result["message"]
                if "already exists" in message.lower():
                    self.shell.poutput("Account already exists - attempting login...")
                    success, login_msg, role = self.login_programmatic(email, password)
                    if success:
                        server_name = self.shell.connection.current_server
                        if server_name:
                            self.shell.config.update_server_credentials(server_name, email, password)
                            self.shell.poutput("OK: Credentials saved to configuration")
                            self.shell._update_prompt()
                            self.shell._update_visible_commands()
                            self.shell.poutput(f"OK: Logged in successfully as {email}")
                    else:
                        self.shell.pwarning(f"Login failed: {login_msg}")
                        server = self.shell.connection.current_server
                        self.shell.pwarning("If this is your account, verify your password and try:")
                        self.shell.pwarning(
                            f"  1. Update config: edit-server {server} username {email} password <correct_password>"
                        )
                        self.shell.pwarning(f"  2. Reconnect: connect {server}")
                        self.shell.pwarning("If you forgot your password, contact your QUADS administrator.")
                    return

            # Only save credentials and login for NEW registrations
            self.shell.poutput(f"OK: User registered successfully: {email}")
            if isinstance(result, dict) and result.get("message"):
                self.shell.poutput(f"  {result['message']}")

            # Save credentials to config file and auto-reconnect
            if self.shell.connection.current_server:
                try:
                    server_name = self.shell.connection.current_server
                    self.shell.config.update_server_credentials(server_name, email, password)
                    self.shell.poutput("OK: Credentials saved to configuration")

                    # Automatically reconnect with new credentials
                    try:
                        self.shell.poutput("OK: Logging in with new credentials...")
                        self.shell.connection.disconnect()
                        self.shell.connection.connect(server_name)
                        self.shell._update_prompt()
                        self.shell._update_visible_commands()
                        self.shell.poutput(f"OK: Logged in successfully as {email}")
                    except Exception as login_error:
                        self.shell.pwarning(f"Warning: Auto-login failed: {login_error}")
                        self.shell.pwarning("Please use 'connect' command to login")
                except Exception as e:
                    self.shell.pwarning(f"Warning: Could not save credentials: {e}")
                    self.shell.pwarning("You will need to manually update your config file")
        except Exception as e:
            self.shell.perror(f"Failed to register user: {e}")

    def login_programmatic(self, email, password):
        """
        Non-interactive login for GUI and scripting.

        Args:
            email: User email
            password: User password

        Returns:
            (success: bool, message: str, role: str or None)
        """
        if not self.shell.connection or not self.shell.connection.is_connected:
            return (False, "Not connected to any server", None)

        try:
            # Get current connection details
            from quads_lib import QuadsApi

            server_name = self.shell.connection.current_server
            url = self.shell.config.get_server_url(server_name)
            verify = self.shell.config.get_server_verify(server_name)

            # Create new API instance with credentials (quads-lib uses credentials from __init__)
            api = QuadsApi(base_url=url, username=email, password=password, verify=verify)
            result = api.login()

            if isinstance(result, dict) and result.get("auth_token"):
                # Update connection with new authenticated API instance
                self.shell.connection._api = api
                self.shell.connection._token = result["auth_token"]
                self.shell.connection._username = email
                self.shell.connection._registration_mode = False

                # Try to decode role
                role = self.shell.connection._decode_role_from_token()
                if role:
                    self.shell.connection._user_role = role

                # Update visible commands based on new authentication state
                if hasattr(self.shell, "_update_visible_commands"):
                    self.shell._update_visible_commands()

                return (True, "Logged in successfully", role)
            else:
                # Login succeeded but no token in response (older API version?)
                if hasattr(self.shell, "_update_visible_commands"):
                    self.shell._update_visible_commands()
                return (True, "Logged in successfully", None)

        except Exception as e:
            # Check if error message indicates wrong credentials (JSON decode errors from 401)
            error_msg = str(e).lower()
            if (
                "expecting value" in error_msg
                or "jsondecode" in error_msg
                or "401" in error_msg
                or "unauthorized" in error_msg
            ):
                return (False, "Login failed: incorrect username or password", None)
            return (False, f"Failed to login: {e}", None)

    def register_programmatic(self, email, password):
        """
        Non-interactive user registration for GUI and scripting.
        Admin accounts cannot be registered -- they must be created server-side.

        Args:
            email: User email
            password: User password

        Returns:
            (success: bool, message: str, role: str or None)
        """
        if not self.shell.connection or not self.shell.connection.is_connected:
            return (False, "Not connected to any server", None)

        try:
            self.shell.connection.api.username = email
            self.shell.connection.api.password = password
            result = self.shell.connection.api.register()

            if isinstance(result, dict) and result.get("status_code") == 403:
                return (
                    False,
                    "Registration is disabled. Use the SSO Token tab to authenticate.",
                    None,
                )

            if isinstance(result, dict) and result.get("message"):
                if "already exists" in result["message"].lower():
                    return (False, "Email already registered. Please use Login instead.", None)

            return self.login_programmatic(email, password)

        except Exception as e:
            return (False, f"Registration failed: {e}", None)

    def token_login_programmatic(self, email, token):
        """
        Non-interactive SSO token login for GUI and scripting.

        Args:
            email: User email (identity anchor)
            token: qat_-prefixed API token

        Returns:
            (success: bool, message: str, role: str or None)
        """
        if not self.shell.connection or not self.shell.connection.is_connected:
            return (False, "Not connected to any server", None)

        if not token.startswith("qat_"):
            return (False, "Invalid token format: must start with qat_", None)

        try:
            from quads_lib import QuadsApi

            server_name = self.shell.connection.current_server
            url = self.shell.config.get_server_url(server_name)
            verify = self.shell.config.get_server_verify(server_name)

            api = QuadsApi(base_url=url, username="", password="", verify=verify, api_token=token)

            # Verify token works with a lightweight API call
            api.get_version()

            self.shell.connection._api = api
            self.shell.connection._token = token
            self.shell.connection._username = email
            self.shell.connection._registration_mode = False

            # Detect role via /me endpoint
            role = self.shell.connection._detect_role_from_api()
            self.shell.connection._user_role = role

            if hasattr(self.shell, "_update_visible_commands"):
                self.shell._update_visible_commands()

            return (True, "Authenticated via SSO token", role)

        except Exception as e:
            error_msg = str(e).lower()
            if "401" in error_msg or "unauthorized" in error_msg:
                return (False, "Invalid or revoked token", None)
            return (False, f"Token authentication failed: {e}", None)

    def cmd_token_login(self, args):
        """Login with an SSO API token. Usage: token-login"""
        if not self._require_connection():
            return

        email = input("Email: ").strip()
        if not email:
            self.shell.perror("Email is required")
            return

        token = getpass.getpass("SSO Token: ")
        if not token:
            self.shell.perror("Token is required")
            return

        success, message, role = self.token_login_programmatic(email, token)

        if success:
            server_name = self.shell.connection.current_server
            if server_name:
                self.shell.config.update_server_api_token(server_name, email, token)
                self.shell.poutput("OK: Token saved to configuration")
            self.shell._update_prompt()
            self.shell._update_visible_commands()
            self.shell.poutput(f"OK: {message} as {email}")
            if role:
                self.shell.poutput(f"  Role: {role}")
        else:
            self.shell.perror(message)

    def cmd_login(self, args):
        """Explicit login. Usage: login"""
        if not self._require_connection():
            return

        # Check if already authenticated via API token
        if self.shell.connection.is_authenticated:
            token = getattr(self.shell.connection, "_token", None)
            if token and token.startswith("qat_"):
                self.shell.poutput(f"Already authenticated via SSO token as {self.shell.connection.username}")
                return

        # If we already have credentials from API instance, use them
        email = getattr(self.shell.connection.api, "username", None)
        password = getattr(self.shell.connection.api, "password", None)

        if not email or not password:
            self.shell.perror("No credentials configured.")
            self.shell.poutput("To authenticate, use one of:")
            self.shell.poutput("  token-login              (SSO token)")
            self.shell.poutput("  register <email> <pass>  (new account)")
            return

        success, message, role = self.login_programmatic(email, password)

        if success:
            self.shell.poutput(f"OK: {message}")
            if role:
                self.shell.poutput(f"  Role: {role}")
        else:
            self.shell.perror(message)

    def cmd_whoami(self, args):
        """Show current user information. Usage: whoami"""
        if not self._require_connection():
            return

        try:
            username = self.shell.connection.username
            role = self.shell.connection.user_role
            is_auth = self.shell.connection.is_authenticated

            self.shell.poutput(f"\nCurrent user: {username or 'Not authenticated'}")
            if is_auth:
                # Display role from JWT token
                if role:
                    role_color = "red" if role == "admin" else "green"
                    if self.shell.rich_console:
                        self.shell.rich_console.console.print(f"Role: [{role_color}]{role}[/{role_color}]")
                    else:
                        self.shell.poutput(f"Role: {role}")
                self.shell.poutput("Authenticated: Yes")
            else:
                self.shell.poutput("Authenticated: No")

            # Try to get additional user info
            if is_auth:
                try:
                    user_info = self.shell.connection.api.get_user_info()
                    if user_info:
                        self.shell.poutput(f"Email: {user_info.get('email', 'N/A')}")
                except (AttributeError, Exception):
                    pass
        except Exception as e:
            self.shell.perror(f"Failed to get user info: {e}")

    def cmd_assignment_create(self, args):
        """Create an assignment. Usage: assignment-create description <desc> [wipe true|false] [qinq <vlan>]"""
        if not self._require_auth():
            return

        parts = args.strip().split()
        if not parts or "description" not in args:
            self.shell.perror("Usage: assignment-create description <desc> [wipe true|false] [qinq <vlan>]")
            return

        data = {}
        keywords = ["description", "wipe", "qinq"]
        i = 0
        while i < len(parts):
            if parts[i] == "description" and i + 1 < len(parts):
                # Handle multi-word descriptions
                desc_parts = []
                i += 1
                while i < len(parts) and parts[i] not in keywords:
                    desc_parts.append(parts[i])
                    i += 1
                data["description"] = " ".join(desc_parts)
            elif parts[i] == "wipe" and i + 1 < len(parts):
                data["wipe"] = parts[i + 1].lower() == "true"
                i += 2
            elif parts[i] == "qinq" and i + 1 < len(parts):
                data["qinq"] = int(parts[i + 1])
                i += 2
            else:
                i += 1

        try:
            username = self.shell.connection.username
            data["owner"] = username

            assignment = self.shell.connection.api.create_self_assignment(data)
            assignment_id = extract_assignment_id(assignment, default="unknown")
            cloud_name = extract_cloud_name(assignment, default="unknown")

            self.shell.poutput("OK: Assignment created successfully")
            self.shell.poutput(f"  Assignment ID: {assignment_id}")
            self.shell.poutput(f"  Cloud: {cloud_name}")
            self.shell.poutput(f"  Owner: {username}")
            if assignment.get("qinq"):
                self.shell.poutput(f"  VLAN (QinQ): {assignment['qinq']}")
        except Exception as e:
            self.shell.perror(f"Failed to create assignment: {e}")

    def cmd_assignment_status(self, args):
        """Show assignment details. Usage: assignment-status <assignment_id>"""
        if not self._require_auth():
            return

        assignment_id = args.strip()
        if not assignment_id:
            self.shell.perror("Usage: assignment-status <assignment_id>")
            return

        try:
            assignments = self.shell.connection.api.filter_assignments({"id": int(assignment_id)})
            if not assignments:
                self.shell.perror(f"Assignment {assignment_id} not found")
                return

            assignment = assignments[0]
            cloud = assignment.get("cloud", {})

            self.shell.poutput(f"\nAssignment: {assignment.get('id')}")
            self.shell.poutput("=" * 80)
            self.shell.poutput(f"Cloud         {cloud.get('name', 'N/A')}")
            self.shell.poutput(f"Owner         {assignment.get('owner', 'N/A')}")
            self.shell.poutput(f"Description   {assignment.get('description', 'N/A')}")
            self.shell.poutput(f"Ticket        {assignment.get('ticket', 'N/A')}")
            self.shell.poutput(f"VLAN (QinQ)   {assignment.get('qinq', 'N/A')}")
            self.shell.poutput(f"Wipe          {'Yes' if assignment.get('wipe') else 'No'}")
            self.shell.poutput(f"Validated     {'Yes' if assignment.get('validated') else 'No'}")
            self.shell.poutput(f"Active        {'Yes' if assignment.get('active') else 'No'}")

            # Get schedules for this assignment
            schedules = self.shell.connection.api.get_schedules({"assignment_id": int(assignment_id)})
            if schedules:
                self.shell.poutput(f"\nAssigned Hosts ({len(schedules)}):")
                self.shell.poutput("-" * 80)
                table_data = []
                for schedule in schedules:
                    host = schedule.get("host", {})
                    hostname = host.get("name", "Unknown")
                    model = host.get("model", "N/A")
                    start = schedule.get("start", "N/A").replace("GMT", "UTC")
                    end = schedule.get("end", "N/A").replace("GMT", "UTC")
                    table_data.append([hostname, model, start, end])

                headers = ["Hostname", "Model", "Start", "End"]
                self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))
            else:
                self.shell.poutput("\nNo hosts assigned")
        except Exception as e:
            self.shell.perror(f"Failed to get assignment status: {e}")

    def cmd_assignment_list(self, args):
        """List user's assignments. Usage: assignment-list (deprecated, use my-assignments)"""
        self.cmd_my_assignments(args)

    def cmd_my_assignments(self, args):
        """List active assignments. Usage: my-assignments (admins see all assignments)"""
        if not self._require_auth():
            return

        try:
            username = get_username_short(self.shell.connection.username)
            is_admin = self.shell.connection.is_admin

            # Admin users see ALL active assignments, regular users see only their own
            if is_admin:
                assignments = self.shell.connection.api.filter_assignments({"active": True})
                title = "All active assignments"
            else:
                assignments = self.shell.connection.api.filter_assignments({"owner": username, "active": True})
                title = f"Active assignments for {username}"

            if not assignments:
                if is_admin:
                    self.shell.poutput("No active assignments found")
                else:
                    self.shell.poutput(f"No active assignments found for {username}")
                return

            self.shell.poutput(f"\n{title}:")
            self.shell.poutput("=" * 80)

            assignments = sorted(assignments, key=lambda a: extract_cloud_number(extract_cloud_name(a)))

            table_data = []
            for assignment in assignments:
                assignment_id = extract_assignment_id(assignment)
                cloud_name = extract_cloud_name(assignment)
                owner = assignment.get("owner", "-")
                description = assignment.get("description", "")
                if len(description) > 40:
                    description = description[:37] + "..."
                validated = "✓" if assignment.get("validated") else "○"

                # For admins, show owner column; for regular users, skip it
                if is_admin:
                    table_data.append([assignment_id, cloud_name, owner, description, validated])
                else:
                    table_data.append([assignment_id, cloud_name, description, validated])

            # Different headers based on admin status
            if is_admin:
                headers = ["ID", "Cloud", "Owner", "Description", "Validated"]
            else:
                headers = ["ID", "Cloud", "Description", "Validated"]

            self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))
        except Exception as e:
            handle_api_error(self.shell, e, "Listing assignments")

    def cmd_terminate(self, args):
        """
        Terminate assignment or release host. Usage: terminate <assignment_id> [hostname]

        Examples:
          terminate 42                    # Terminate entire assignment
          terminate 42 host03.example.com # Release specific host from assignment
        """
        if not self._require_auth():
            return

        parts = args.strip().split()
        if not parts or parts[0] in ("?", "--help", "-h"):
            self.shell.poutput("Usage: terminate <assignment_id> [hostname]")
            self.shell.poutput("\nExamples:")
            self.shell.poutput("  terminate 42                    # Terminate entire assignment")
            self.shell.poutput("  terminate 42 host01.example.com # Release single host from assignment")
            return

        assignment_id_str = parts[0]
        hostname = parts[1] if len(parts) > 1 else None

        # Validate assignment_id is a number
        if not assignment_id_str.isdigit():
            self.shell.perror(f"Invalid assignment ID: {assignment_id_str}")
            self.shell.perror("Assignment ID must be a number (e.g., 42)")
            return

        try:
            assignment_id = int(assignment_id_str)
            # Get assignment details first
            assignments = self.shell.connection.api.filter_assignments({"id": assignment_id})
            if not assignments:
                self.shell.perror(f"Assignment {assignment_id} not found")
                return

            assignment = assignments[0]

            # SSM users can only terminate their own assignments
            if not self.shell.connection.is_admin:
                owner = get_username_short(self.shell.connection.username)

                # Handle both dict and object responses for owner
                if isinstance(assignment, dict):
                    assignment_owner = assignment.get("owner", "")
                else:
                    assignment_owner = getattr(assignment, "owner", "")

                if assignment_owner != owner:
                    self.shell.perror("Permission denied: You can only terminate your own assignments")
                    return

            cloud_name = extract_cloud_name(assignment)

            if hostname:
                # Release specific host
                if not getattr(self.shell, "gui_mode", False):
                    response = input(
                        f"Release {hostname} from assignment {assignment_id} (cloud: {cloud_name})? [y/N]: "
                    )
                    if response.lower() != "y":
                        self.shell.poutput("Host not released")
                        return

                schedules = self.shell.connection.api.get_schedules({"assignment_id": assignment_id, "host": hostname})
                if not schedules:
                    self.shell.perror(f"No schedule found for {hostname} in assignment {assignment_id}")
                    return

                self.shell.connection.api.remove_schedule(schedules[0]["id"])
                self.shell.poutput(f"OK: Released {hostname} from assignment #{assignment_id}")
            else:
                # Terminate entire assignment
                if not getattr(self.shell, "gui_mode", False):
                    response = input(f"Terminate assignment {assignment_id} (cloud: {cloud_name})? [y/N]: ")
                    if response.lower() != "y":
                        self.shell.poutput("Assignment not terminated")
                        return

                result = self.shell.connection.api.terminate_assignment(assignment_id)

                # Check if termination was successful
                if isinstance(result, dict):
                    if result.get("status") == "error" or result.get("error"):
                        self.shell.perror(
                            f"Failed to terminate: {result.get('message', result.get('error', 'Unknown error'))}"
                        )
                        return

                self.shell.poutput(f"OK: Terminated assignment #{assignment_id}")
                self.shell.poutput("  Note: It may take a few moments for the termination to complete")

        except Exception as e:
            handle_api_error(self.shell, e, "Terminate")

    def cmd_schedule(self, args):
        """
        SSM Mode: Schedule hosts for self-service

        Syntax:
          schedule <NUMBER>                           description <desc> [options]
          schedule <hostname[,hostname,...]>          description <desc> [options]
          schedule host-list <file-path>              description <desc> [options]

        Options: nowipe vlan <id> qinq <0|1> model <name> ram <GB>

        Examples:
          schedule 3 description "Dev testing"                        # Count: QUADS picks 3 hosts
          schedule 5 description "Perf lab" model r640 ram 128        # Count with filters
          schedule host01.example.com,host02.example.com description "CI pipeline"
          schedule host-list ~/hosts.txt description "Batch test" vlan 1150 nowipe

        Note: SSM mode does NOT require tickets - the server automatically creates the assignment.
        """
        if not self._require_auth():
            return

        try:
            # Parse arguments
            parsed = parse_schedule_ssm_args(args)

            # Get host list (if count mode)
            host_list = parsed["host_list"]
            if host_list is None:
                # Count mode: query available hosts
                filters = {"can_self_schedule": True}
                if parsed["model"]:
                    filters["model"] = parsed["model"]
                if parsed["ram"]:
                    filters["memory__gte"] = parsed["ram"] * 1024

                available = auto_refresh_on_auth_error(self.shell, self.shell.connection.api.filter_available, filters)

                # Debug info
                if self.shell.debug:
                    self.shell.poutput(f"DEBUG: filter_available returned {len(available) if available else 0} hosts")

                if not available or len(available) == 0:
                    self.shell.perror("No available hosts found for self-scheduling")
                    self.shell.perror("Hint: Contact admin to configure hosts with can_self_schedule flag")
                    if parsed["model"] or parsed["ram"]:
                        self.shell.perror("Or try removing model/ram filters")
                    return

                if len(available) < parsed["count"]:
                    self.shell.perror(
                        f"Not enough hosts available: found {len(available)}, requested {parsed['count']}"
                    )
                    self.shell.perror("Hint: Try removing filters or requesting fewer hosts")
                    return

                # Extract hostnames - handle string, dict, and object responses
                host_list = []
                for i, h in enumerate(available[: parsed["count"]]):
                    name = extract_hostname(h)
                    if not name:
                        # Debug: show what we received
                        if isinstance(h, dict):
                            self.shell.perror(f"DEBUG: Host {i} is dict but has no 'name' key. Keys: {list(h.keys())}")
                        elif isinstance(h, str):
                            self.shell.perror(f"DEBUG: Host {i} is empty string")
                        else:
                            attrs = dir(h) if hasattr(h, "__dict__") else "no __dict__"
                            self.shell.perror(f"DEBUG: Host {i} is {type(h).__name__} with attrs: {attrs}")
                    if name:
                        host_list.append(name)

                # Final safety check
                if not host_list:
                    self.shell.perror("Failed to extract hostnames from available hosts")
                    item_type = type(available[0]).__name__ if available else "N/A"
                    self.shell.perror(f"  Available returned {len(available)} items of type: {item_type}")
                    if available:
                        self.shell.perror(f"  First item: {available[0]}")
                    self.shell.perror("Please report this bug with the above debug info")
                    return

            # Create self-assignment (server auto-assigns cloud, handles ticketing)
            owner = get_username_short(self.shell.connection.username)
            assignment_data = {
                "description": parsed["description"],
                "owner": owner,
                "wipe": parsed["wipe"],  # Default: True (wipe enabled)
            }
            # Optional fields - do NOT include cloud (let server auto-select)
            if parsed["qinq"]:
                assignment_data["qinq"] = parsed["qinq"]
            if parsed["vlan"]:
                assignment_data["vlan"] = parsed["vlan"]
            if parsed["os"]:
                assignment_data["ostype"] = parsed["os"]

            # Step 1: Create self-assignment (SSM endpoint auto-assigns cloud)
            assignment = auto_refresh_on_auth_error(
                self.shell, self.shell.connection.api.create_self_assignment, assignment_data
            )

            # Extract cloud name from response
            cloud_name = extract_cloud_name(assignment, default="unknown")
            assignment_id = extract_assignment_id(assignment, default="unknown")

            # Step 2: Create schedules for each host separately (per QUADS API spec)
            created_schedules = 0
            for hostname in host_list:
                schedule_data = {
                    "cloud": cloud_name,
                    "hostname": hostname,  # API expects "hostname" not "host"
                    # NO start/end - server controls duration via ssm_default_lifetime
                }
                try:
                    result = auto_refresh_on_auth_error(
                        self.shell, self.shell.connection.api.create_schedule, schedule_data
                    )
                    if result:
                        created_schedules += 1
                except Exception as schedule_error:
                    self.shell.pwarning(f"  Warning: Failed to schedule {hostname}: {schedule_error}")

            if created_schedules == 0:
                self.shell.perror(f"Failed to schedule any hosts to assignment #{assignment_id}")
                self.shell.perror("The assignment was created but no hosts were scheduled")
                return

            self.shell.poutput(f"OK: Reserved {created_schedules} host(s) - activated immediately")
            self.shell.poutput(f"  Cloud: {cloud_name}")
            self.shell.poutput(f"  Assignment: #{assignment_id}")
            self.shell.poutput("  Duration: Automatic (5 days or Sunday 21:00 UTC)")
            if created_schedules < len(host_list):
                self.shell.pwarning(
                    f"  Note: Only {created_schedules} of {len(host_list)} hosts were successfully scheduled"
                )

        except ValueError as e:
            self.shell.perror(f"Invalid arguments: {e}")
            self.shell.perror("\nValid syntax:")
            self.shell.perror('  schedule <NUMBER> description "..."                    # Count mode')
            self.shell.perror('  schedule <hostname,hostname> description "..."         # Specific hosts')
            self.shell.perror('  schedule host-list <file> description "..."            # Host list file')
            self.shell.perror("\nExamples:")
            self.shell.perror('  schedule 3 description "Dev testing"')
            self.shell.perror('  schedule host01.example.com,host02.example.com description "CI"')
            self.shell.perror('  schedule host-list ~/hosts.txt description "Batch"')
        except ConnectionError:
            self.shell.perror("Connection failed: unable to reach QUADS server")
            self.shell.perror("Hint: Check 'status' or run 'connect <server>'")
        except Exception as e:
            handle_api_error(self.shell, e, "Scheduling")

    def cmd_my_hosts(self, args):
        """Show your currently scheduled hosts. Usage: my-hosts"""
        if not self._require_auth():
            return

        from quads_client.progress import format_progress_str

        try:
            username = get_username_short(self.shell.connection.username)
            # Get assignments by owner
            assignments = self.shell.connection.api.filter_assignments({"owner": username, "active": True})
            if not assignments:
                self.shell.poutput(f"No active hosts scheduled by {username}")
                return

            self.shell.poutput(f"\nHosts scheduled by {username}:")
            self.shell.poutput("=" * 80)

            move_status_map = {}
            try:
                all_moves = self.shell.connection.api.get_all_move_status()
                if all_moves:
                    move_status_map = {m["host"]: m for m in all_moves if isinstance(m, dict)}
            except Exception:
                pass

            # Collect all unique hosts across all assignments
            unique_hosts = {}
            for assignment in assignments:
                assignment_id = extract_assignment_id(assignment)
                cloud_name = extract_cloud_name(assignment)
                description = assignment.get("description", "")
                is_validated = assignment.get("validated", False)

                # Get current schedules for this assignment
                schedules = self.shell.connection.api.get_schedules({"assignment_id": assignment_id})
                if schedules:
                    for schedule in schedules:
                        host_name = schedule.get("host", {}).get("name", "Unknown")
                        end = schedule.get("end", "N/A").replace("GMT", "UTC")
                        # Use hostname as key to ensure uniqueness
                        if host_name not in unique_hosts:
                            if is_validated:
                                status = "Active"
                                progress = format_progress_str("completed")
                            else:
                                move_data = move_status_map.get(host_name)
                                if move_data:
                                    move_st = move_data.get("status", "pending")
                                    progress = format_progress_str(move_st)
                                    status = move_st.replace("_", " ").title()
                                else:
                                    status = "Scheduled"
                                    progress = "Awaiting move"

                            unique_hosts[host_name] = {
                                "status": status,
                                "progress": progress,
                                "end": end,
                                "assignment_id": assignment_id,
                                "cloud": cloud_name,
                                "description": description,
                            }

            if not unique_hosts:
                self.shell.poutput(f"\nNo active hosts scheduled by {username}")
                return

            # Display unique hosts in a single table
            table_data = []
            for host_name, info in sorted(unique_hosts.items()):
                table_data.append(
                    [
                        host_name,
                        info["assignment_id"],
                        info["cloud"],
                        info["status"],
                        info["progress"],
                        f"Expires: {info['end']}",
                    ]
                )

            headers = ["Host", "Assignment", "Cloud", "Status", "Progress", "Schedule"]
            self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))
            self.shell.poutput(f"\nTotal unique hosts: {len(unique_hosts)}")

        except Exception as e:
            handle_api_error(self.shell, e, "Listing hosts")
