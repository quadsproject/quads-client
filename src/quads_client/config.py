from pathlib import Path
from typing import Any, Optional

import yaml


class ConfigError(Exception):
    pass


class QuadsClientConfig:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = "~/.config/quads/quads-client.yml"
        self.config_path = Path(config_path).expanduser()
        self._config: dict[str, Any] = {}
        self._load_config()

    def _normalize_server_fields(self, server: dict[str, Any]) -> dict[str, Any]:
        """Normalize server dict fields to consistent order"""
        return {
            "url": server.get("url", ""),
            "username": server.get("username", ""),
            "password": server.get("password", ""),
            "api_token": server.get("api_token", ""),
            "verify": server.get("verify", True),
        }

    def _load_config(self):
        if not self.config_path.exists():
            # Create skeleton config file with empty servers dict
            self._create_skeleton_config()

        try:
            with open(self.config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ConfigError(f"Error reading config file: {e}")

        if "servers" not in self._config or not isinstance(self._config["servers"], dict):
            raise ConfigError("Config must contain 'servers' dictionary")

    def _create_skeleton_config(self):
        """Create a skeleton config file with empty servers dict"""
        skeleton_config = {"servers": {}}

        # Create parent directory if it doesn't exist
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            raise ConfigError(f"Config file not found: {self.config_path} (Cannot create: {e})")

        try:
            with open(self.config_path, "w") as f:
                yaml.dump(skeleton_config, f, default_flow_style=False)
        except Exception as e:
            raise ConfigError(f"Failed to create skeleton config: {e}")

    def get_server(self, name: str) -> dict[str, Any]:
        servers = self._config.get("servers", {})
        if name not in servers:
            raise ConfigError(f"Server '{name}' not found in configuration")
        return servers[name]

    def get_all_servers(self) -> dict[str, dict[str, Any]]:
        return self._config.get("servers", {})

    def get_default_server(self) -> Optional[str]:
        return self._config.get("default_server")

    def needs_initial_setup(self) -> bool:
        """Check if config needs initial setup (no servers configured)"""
        return not self._config.get("servers")

    def get_server_url(self, name: str) -> str:
        server = self.get_server(name)
        if "url" not in server:
            raise ConfigError(f"Server '{name}' missing 'url' field")
        return server["url"]

    def get_server_credentials(self, name: str) -> tuple[str, str]:
        server = self.get_server(name)
        username = server.get("username", "")
        password = server.get("password", "")
        return username, password

    def get_server_verify(self, name: str) -> bool:
        server = self.get_server(name)
        verify = server.get("verify", True)
        if not isinstance(verify, bool):
            raise ConfigError(f"Server '{name}' verify must be true or false, not a path")
        return verify

    def get_server_api_token(self, name: str) -> str:
        server = self.get_server(name)
        return server.get("api_token", "")

    def update_server_api_token(self, name: str, username: str, api_token: str) -> None:
        """Update server with API token auth, clearing password credentials"""
        server = self.get_server(name)
        server["username"] = username
        server["password"] = ""
        server["api_token"] = api_token
        self._config["servers"][name] = self._normalize_server_fields(server)
        self.save_config()

    def update_server_credentials(self, name: str, username: str, password: str) -> None:
        """Update server credentials in config file"""
        server = self.get_server(name)  # Validates server exists

        # Update server dict with credentials, clearing api_token
        server["username"] = username
        server["password"] = password
        server["api_token"] = ""

        # Normalize field order before writing
        self._config["servers"][name] = self._normalize_server_fields(server)

        # Normalize all servers to maintain consistent ordering
        normalized_servers = {
            server_name: self._normalize_server_fields(server_config)
            for server_name, server_config in self._config["servers"].items()
        }
        self._config["servers"] = normalized_servers

        # Write to file
        self.save_config()

    def save_config(self) -> None:
        """Save current config to file"""
        # Normalize all servers to maintain consistent ordering
        if "servers" in self._config:
            normalized_servers = {
                server_name: self._normalize_server_fields(server_config)
                for server_name, server_config in self._config["servers"].items()
            }
            self._config["servers"] = normalized_servers

        # Write to file
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise ConfigError(f"Failed to save config file: {e}")

    @property
    def config_data(self) -> dict[str, Any]:
        """Access to the raw config data for GUI preferences, etc."""
        return self._config
