import sys
import pytest
from unittest.mock import MagicMock, Mock

# Mock quads_lib before any imports
sys.modules["quads_lib"] = MagicMock()
sys.modules["quads_lib.quads"] = MagicMock()


@pytest.fixture
def mock_config():
    """Mock QuadsClientConfig"""
    config = MagicMock()
    config.get_all_servers.return_value = {
        "test_server": {"url": "https://test.example.com", "username": "test@example.com"}
    }
    config.get_server_url.return_value = "https://test.example.com"
    config.get_server_credentials.return_value = ("test@example.com", "testpass")
    config.get_default_server.return_value = "test_server"
    config.get_server_verify.return_value = True
    config.get_server_api_token.return_value = ""
    return config


@pytest.fixture
def mock_api():
    """Mock QuadsApi"""
    api = MagicMock()
    api.login.return_value = {"status": "success", "auth_token": "test_token_123"}
    api.token = "test_token_123"
    api.get_clouds.return_value = [{"name": "cloud01"}, {"name": "cloud02"}]
    api.create_cloud.return_value = {"status": "success"}
    api.remove_cloud.return_value = {"status": "success"}
    api.filter_hosts.return_value = [
        {"name": "host01.example.com", "can_self_schedule": True},
        {"name": "host02.example.com", "can_self_schedule": True},
    ]
    api.create_schedule.return_value = {"id": 1, "status": "success"}
    api.filter_assignments.return_value = [{"id": 1, "owner": "test@example.com", "cloud": "cloud02"}]
    api.get_schedules.return_value = [
        {"id": 1, "host": {"name": "host01.example.com"}, "start": "2026-05-01", "end": "2026-05-15"}
    ]
    return api


@pytest.fixture
def mock_connection_manager(mock_config, mock_api):
    """Mock ConnectionManager with QuadsApi"""
    conn = MagicMock()
    conn.config = mock_config
    conn.is_connected = True
    conn.is_authenticated = True
    conn.user_role = "user"
    conn.is_admin = False
    conn.current_server = "test_server"
    conn.username = "test@example.com"
    conn.api = mock_api
    conn._token = "test_token_123"
    conn._user_role = "user"
    conn.get_available_servers.return_value = ["test_server"]
    conn.connect = MagicMock()
    conn.disconnect = MagicMock()
    conn._decode_role_from_token = MagicMock(return_value="user")
    return conn


@pytest.fixture
def mock_session_manager(mock_config, mock_connection_manager):
    """Mock SessionManager"""
    from datetime import datetime

    # Mock session
    mock_session = MagicMock()
    mock_session.id = "1"
    mock_session.server_name = "test_server"
    mock_session.label = "test_server"
    mock_session.connection = mock_connection_manager
    mock_session.created_at = datetime.now()
    mock_session.last_active = datetime.now()
    mock_session.get_version.return_value = "2.2.6"

    # Mock session manager
    session_manager = MagicMock()
    session_manager.config = mock_config
    session_manager.sessions = {"1": mock_session}
    session_manager.active_session_id = "1"
    session_manager.active_connection = mock_connection_manager
    session_manager.active_session = mock_session
    session_manager.list_sessions.return_value = [mock_session]
    session_manager.get_session.return_value = mock_session
    session_manager.create_session.return_value = mock_session
    return session_manager


@pytest.fixture
def mock_shell(mock_config, mock_connection_manager, mock_session_manager):
    """Mock QuadsClientShell"""
    shell = MagicMock()
    shell.config = mock_config
    shell.session_manager = mock_session_manager
    shell.connection = mock_connection_manager  # Backward compatibility
    shell.poutput = MagicMock()
    shell.perror = MagicMock()
    shell.pwarning = MagicMock()
    shell._update_prompt = MagicMock()
    shell._update_visible_commands = MagicMock()
    shell.rich_console = None  # Rich console disabled in tests (use fallback)
    shell.quiet = False  # Default to interactive mode (not quiet)
    return shell
