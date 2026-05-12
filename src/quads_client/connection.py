from typing import Optional
import sys
import jwt
import urllib3
Conditionally inject truststore only on macOS
if sys.platform == 'darwin':
    try:
        import truststore
    except ImportError:
        import warnings
        warnings.warn(
            "The 'truststore' package is missing. macOS system certificates "
            "may not be recognized. Please run `pip install truststore`."
        )

from quads_lib import QuadsApi

from quads_client.config import QuadsClientConfig


class ConnectionError(Exception):
    pass


class ConnectionManager:
    def __init__(self, config: QuadsClientConfig):
        self.config = config
        self._current_server: Optional[str] = None
        self._api: Optional[QuadsApi] = None
        self._token: Optional[str] = None
        self._username: Optional[str] = None
        self._user_role: Optional[str] = None
        self._registration_mode: bool = False

    @property
    def is_connected(self) -> bool:
        return self._current_server is not None and self._api is not None

    @property
    def is_authenticated(self) -> bool:
        """Check if user is logged in (has valid token)"""
        return self.is_connected and self._token is not None and not self._registration_mode

    @property
    def current_server(self) -> Optional[str]:
        return self._current_server

    @property
    def api(self) -> QuadsApi:
        if not self.is_connected or self._api is None:
            raise ConnectionError("Not connected to any server")
        return self._api

    @property
    def username(self) -> Optional[str]:
        return self._username

    @property
    def user_role(self) -> Optional[str]:
        """Get user role (admin or user)"""
        return self._user_role

    @property
    def is_admin(self) -> bool:
        """Check if current user has admin role"""
        return self._user_role == "admin"

    @property
    def registration_mode(self) -> bool:
        """Check if connection is in registration mode (connected but not authenticated)"""
        return self._registration_mode

    def _decode_role_from_token(self) -> Optional[str]:
        """Decode role from JWT token"""
        if not self._token:
            return None

        try:
            # Decode without verification (we already trust it from the server)
            decoded = jwt.decode(self._token, options={"verify_signature": False})

            # Check various possible role field names
            role = decoded.get("role") or decoded.get("roles") or decoded.get("user_role")
            if isinstance(role, list) and role:
                # If roles is a list, take the first one or look for 'admin'
                if "admin" in role:
                    return "admin"
                return role[0]

            return role
        except Exception:
            return None

    def _resolve_server_name(self, input_name: str) -> Optional[str]:
        """
        Resolve a server name using fuzzy matching.

        Tries in order:
        1. Exact match with config keys
        2. Match against server URLs (strip https://)
        3. Prefix match with config keys

        Returns the matched config key or None.
        """
        all_servers = self.config.get_all_servers()

        # 1. Exact match
        if input_name in all_servers:
            return input_name

        # 2. Match against URLs (strip protocol)
        # Normalize input by stripping protocol and trailing slashes
        input_normalized = input_name.replace("https://", "").replace("http://", "").rstrip("/")

        for server_key in all_servers:
            server_url = self.config.get_server_url(server_key)
            # Strip protocol and trailing slashes from config URL
            url_host = server_url.replace("https://", "").replace("http://", "").rstrip("/")
            if input_normalized == url_host:
                return server_key

        # 3. Prefix match (e.g., "quads2-dev" matches "quads2-dev.rdu2.scalelab")
        matches = [key for key in all_servers if key.startswith(input_name)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - try to find exact substring match
            for key in matches:
                if input_name in key:
                    return key

        return None

    def connect(self, server_name: str, registration_mode: bool = False) -> None:
        """Connect to a server. Automatically enters registration mode if credentials are blank."""
        # Resolve server name with fuzzy matching
        resolved_name = self._resolve_server_name(server_name)
        if not resolved_name:
            raise ConnectionError(f"Unknown server: {server_name}")

        # Use resolved name for all operations
        server_name = resolved_name
        url = self.config.get_server_url(server_name)
        username, password = self.config.get_server_credentials(server_name)
        verify = self.config.get_server_verify(server_name)

        if sys.platform == 'darwin':
            truststore.inject_into_ssl()

        # Suppress SSL warnings when certificate verification is disabled
        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        try:
            # Automatically use registration mode if credentials are missing
            if not username or not password or registration_mode:
                # Registration mode: connect without login
                api = QuadsApi(base_url=url, username="", password="", verify=verify)
                self._api = api
                self._current_server = server_name
                self._registration_mode = True
                self._username = None
                self._token = None
                self._user_role = None
            else:
                # Normal mode: connect and login
                api = QuadsApi(base_url=url, username=username, password=password, verify=verify)
                response = api.login()

                if response.get("status") != "success":
                    raise ConnectionError("Login failed")

                self._api = api
                self._token = api.token
                self._username = username
                self._current_server = server_name
                self._registration_mode = False

                # Try to decode role from token
                self._user_role = self._decode_role_from_token()

        except Exception as e:
            # Provide user-friendly error messages
            error_str = str(e).lower()

            # Check more specific errors first, then generic ones
            if "timeout" in error_str:
                raise ConnectionError(
                    f"Failed to connect to {server_name}: Connection timed out. "
                    f"The server may be slow or unreachable."
                )
            elif "ssl" in error_str or "certificate" in error_str:
                raise ConnectionError(
                    f"Failed to connect to {server_name}: SSL certificate verification failed. "
                    f"Use 'edit-server {server_name} --verify false' to disable verification for testing."
                )
            elif "unauthorized" in error_str or "401" in error_str or "403" in error_str or "forbidden" in error_str:
                raise ConnectionError(
                    f"Failed to connect to {server_name}: Authentication failed. "
                    f"Check your username and password in the configuration."
                )
            elif "expecting value" in error_str or "json" in error_str:
                # JSON parsing error could mean wrong credentials (server returned HTML error page)
                # or actual server issue. Check if we have credentials configured.
                if username and password:
                    raise ConnectionError(
                        f"Failed to connect to {server_name}: Server returned an invalid response. "
                        f"This usually means incorrect credentials. Please verify your username and password."
                    )
                else:
                    raise ConnectionError(
                        f"Failed to connect to {server_name}: Server is not responding correctly. "
                        f"It may be offline or the URL may be incorrect."
                    )
            elif "connection" in error_str or "refused" in error_str:
                raise ConnectionError(
                    f"Failed to connect to {server_name}: Server is unreachable. "
                    f"Check that the server is online and the URL is correct."
                )
            else:
                # Generic fallback
                raise ConnectionError(
                    f"Failed to connect to {server_name}: {e}\n" f"Verify the server URL and network connectivity."
                )

    def refresh_token(self) -> bool:
        """Refresh the authentication token. Returns True if successful."""
        if not self._current_server or not self._api or self._registration_mode:
            return False

        try:
            username, password = self.config.get_server_credentials(self._current_server)
            if not username or not password:
                return False

            # Update API credentials and re-login
            self._api.username = username
            self._api.password = password
            response = self._api.login()

            if response.get("status") != "success":
                return False

            # Update token and role
            self._token = self._api.token
            self._user_role = self._decode_role_from_token()
            return True

        except Exception:
            return False

    def disconnect(self) -> None:
        self._current_server = None
        self._api = None
        self._token = None
        self._username = None
        self._user_role = None
        self._registration_mode = False

    def get_available_servers(self) -> list[str]:
        return list(self.config.get_all_servers().keys())
