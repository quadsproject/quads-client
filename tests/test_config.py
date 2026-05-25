import pytest
import tempfile
import yaml
from pathlib import Path
from quads_client.config import QuadsClientConfig, ConfigError


def test_config_load_valid_yaml(tmp_path):
    """Test loading valid YAML configuration"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {
        "servers": {
            "test_server": {"url": "https://test.example.com", "username": "test@example.com", "password": "testpass"}
        },
        "default_server": "test_server",
    }
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    assert config.get_default_server() == "test_server"
    assert config.get_server_url("test_server") == "https://test.example.com"
    username, password = config.get_server_credentials("test_server")
    assert username == "test@example.com"
    assert password == "testpass"


def test_config_missing_file():
    """Test handling of missing config file"""
    with pytest.raises(ConfigError, match="not found"):
        QuadsClientConfig(config_path="/nonexistent/path/config.yml")


def test_config_invalid_yaml(tmp_path):
    """Test handling of invalid YAML"""
    config_file = tmp_path / "quads-client.yml"
    config_file.write_text("invalid: yaml: content: {{")

    with pytest.raises(ConfigError):
        QuadsClientConfig(config_path=str(config_file))


def test_config_get_all_servers(tmp_path):
    """Test retrieving all server configurations"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {
        "servers": {
            "server1": {"url": "https://server1.example.com", "username": "user1", "password": "pass1"},
            "server2": {"url": "https://server2.example.com", "username": "user2", "password": "pass2"},
        }
    }
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    servers = config.get_all_servers()
    assert "server1" in servers
    assert "server2" in servers
    assert len(servers) == 2


def test_config_unknown_server(tmp_path):
    """Test accessing unknown server"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com"}}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    with pytest.raises(ConfigError, match="not found in configuration"):
        config.get_server_url("nonexistent_server")


def test_config_missing_credentials(tmp_path):
    """Test server with missing credentials"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com"}}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    username, password = config.get_server_credentials("test_server")
    # Returns empty strings when credentials are missing
    assert username == ""
    assert password == ""


def test_get_server_verify_default(tmp_path):
    """Test retrieving server verify defaults to True"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com"}}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    verify = config.get_server_verify("test_server")
    assert verify is True


def test_get_server_verify_true(tmp_path):
    """Test retrieving server verify when set to true"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {
        "servers": {"test_server": {"url": "https://test.example.com", "username": "test@example.com", "verify": True}}
    }
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    verify = config.get_server_verify("test_server")
    assert verify is True


def test_get_server_verify_false(tmp_path):
    """Test retrieving server verify when set to false"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {
        "servers": {
            "test_server": {"url": "https://test.example.com", "username": "test@example.com", "verify": False}
        }
    }
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    verify = config.get_server_verify("test_server")
    assert verify is False


def test_get_server_verify_invalid_path(tmp_path):
    """Test that custom CA paths are rejected"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {
        "servers": {
            "test_server": {
                "url": "https://test.example.com",
                "username": "test@example.com",
                "verify": "/etc/ssl/certs/custom-ca.crt",
            }
        }
    }
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    with pytest.raises(ConfigError, match="verify must be true or false"):
        config.get_server_verify("test_server")


def test_config_missing_servers_dict(tmp_path):
    """Test config without 'servers' key"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"default_server": "test"}
    config_file.write_text(yaml.dump(config_data))

    with pytest.raises(ConfigError, match="must contain 'servers' dictionary"):
        QuadsClientConfig(config_path=str(config_file))


def test_config_empty_servers(tmp_path):
    """Test config with empty servers dict"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    assert config.needs_initial_setup() is True
    assert config.get_all_servers() == {}


def test_config_no_default_server(tmp_path):
    """Test get_default_server when no default is configured"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com"}}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    assert config.get_default_server() is None


def test_update_server_credentials(tmp_path):
    """Test updating server credentials"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {
        "servers": {
            "test_server": {"url": "https://test.example.com", "username": "old@example.com", "password": "old"}
        }
    }
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    config.update_server_credentials("test_server", "new@example.com", "newpass")

    # Verify credentials were updated in memory
    username, password = config.get_server_credentials("test_server")
    assert username == "new@example.com"
    assert password == "newpass"

    # Verify credentials were written to file
    with open(config_file, "r") as f:
        saved_data = yaml.safe_load(f)
    assert saved_data["servers"]["test_server"]["username"] == "new@example.com"
    assert saved_data["servers"]["test_server"]["password"] == "newpass"


def test_update_server_credentials_unknown_server(tmp_path):
    """Test updating credentials for non-existent server"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com"}}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    with pytest.raises(ConfigError, match="not found in configuration"):
        config.update_server_credentials("nonexistent", "user", "pass")


def test_config_read_error(tmp_path, monkeypatch):
    """Test handling of file read errors"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com"}}}
    config_file.write_text(yaml.dump(config_data))

    # Make the file unreadable
    import os

    os.chmod(config_file, 0o000)

    try:
        with pytest.raises(ConfigError, match="Error reading config file"):
            QuadsClientConfig(config_path=str(config_file))
    finally:
        # Restore permissions for cleanup
        os.chmod(config_file, 0o644)


def test_config_data_property(tmp_path):
    """Test config_data property returns internal config dict"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {
        "servers": {"test_server": {"url": "https://test.example.com", "username": "test@example.com"}},
        "default_server": "test_server",
    }
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    data = config.config_data

    assert isinstance(data, dict)
    assert "servers" in data
    assert "test_server" in data["servers"]
    assert data["default_server"] == "test_server"


def test_save_config_basic(tmp_path):
    """Test save_config() method writes to file"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com"}}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))

    # Modify config via config_data property
    config.config_data["default_server"] = "test_server"

    # Save changes
    config.save_config()

    # Verify changes were written to file
    with open(config_file, "r") as f:
        saved_data = yaml.safe_load(f)
    assert saved_data["default_server"] == "test_server"


def test_save_config_gui_preferences(tmp_path):
    """Test saving GUI preferences via config_data"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com"}}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))

    # Add GUI preferences
    gui_prefs = {
        "auto_refresh_interval": 30,
        "auto_refresh_my_hosts": True,
        "confirm_terminate": True,
        "font_size": "large",
    }
    config.config_data["gui_preferences"] = gui_prefs

    # Save changes
    config.save_config()

    # Verify preferences were written to file
    with open(config_file, "r") as f:
        saved_data = yaml.safe_load(f)
    assert "gui_preferences" in saved_data
    assert saved_data["gui_preferences"]["font_size"] == "large"
    assert saved_data["gui_preferences"]["auto_refresh_interval"] == 30


def test_save_config_preserves_gui_preferences(tmp_path):
    """Test that GUI preferences persist across loads"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {
        "servers": {"test_server": {"url": "https://test.example.com"}},
        "gui_preferences": {"font_size": "medium", "confirm_terminate": False},
    }
    config_file.write_text(yaml.dump(config_data))

    # Load config
    config = QuadsClientConfig(config_path=str(config_file))

    # Verify preferences loaded
    assert config.config_data["gui_preferences"]["font_size"] == "medium"

    # Modify preferences
    config.config_data["gui_preferences"]["font_size"] = "large"
    config.save_config()

    # Reload config
    config2 = QuadsClientConfig(config_path=str(config_file))

    # Verify changes persisted
    assert config2.config_data["gui_preferences"]["font_size"] == "large"
    assert config2.config_data["gui_preferences"]["confirm_terminate"] is False


def test_get_server_api_token_default(tmp_path):
    """Test api_token defaults to empty string when not set"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com"}}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    assert config.get_server_api_token("test_server") == ""


def test_get_server_api_token_set(tmp_path):
    """Test retrieving a configured api_token"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {
        "servers": {
            "test_server": {
                "url": "https://test.example.com",
                "api_token": "qat_test123",
            }
        }
    }
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    assert config.get_server_api_token("test_server") == "qat_test123"


def test_update_server_api_token(tmp_path):
    """Test updating server with api_token clears password"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {
        "servers": {
            "test_server": {
                "url": "https://test.example.com",
                "username": "old@example.com",
                "password": "oldpass",
            }
        }
    }
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    config.update_server_api_token("test_server", "new@example.com", "qat_newtoken")

    assert config.get_server_api_token("test_server") == "qat_newtoken"
    username, password = config.get_server_credentials("test_server")
    assert username == "new@example.com"
    assert password == ""

    # Verify persisted to file
    with open(config_file, "r") as f:
        saved_data = yaml.safe_load(f)
    assert saved_data["servers"]["test_server"]["api_token"] == "qat_newtoken"
    assert saved_data["servers"]["test_server"]["password"] == ""


def test_normalize_server_fields_includes_api_token(tmp_path):
    """Test that _normalize_server_fields includes api_token"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com", "username": "u", "password": "p"}}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))
    config.save_config()

    with open(config_file, "r") as f:
        saved_data = yaml.safe_load(f)
    assert "api_token" in saved_data["servers"]["test_server"]


def test_save_config_write_error(tmp_path):
    """Test save_config() error handling"""
    config_file = tmp_path / "quads-client.yml"
    config_data = {"servers": {"test_server": {"url": "https://test.example.com"}}}
    config_file.write_text(yaml.dump(config_data))

    config = QuadsClientConfig(config_path=str(config_file))

    # Make directory unwritable
    import os

    os.chmod(tmp_path, 0o444)

    try:
        with pytest.raises(ConfigError, match="Failed to save config file"):
            config.save_config()
    finally:
        # Restore permissions for cleanup
        os.chmod(tmp_path, 0o755)
