import pytest
from unittest.mock import MagicMock, patch
from quads_client.commands.connection import ConnectionCommands
from quads_client.connection import ConnectionError


def test_connect_list_servers(mock_shell):
    """Test connect command without args and no default server lists servers"""
    mock_shell.config.get_all_servers.return_value = {"server1": {}, "server2": {}}
    mock_shell.config.get_default_server.return_value = None

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_connect("")

    assert mock_shell.poutput.call_count >= 2
    mock_shell.session_manager.create_session.assert_not_called()


def test_connect_success(mock_shell, mock_api):
    """Test successful connection"""
    # Mock session creation and connection
    mock_session = MagicMock()
    mock_session.id = "2"
    mock_session.connection = MagicMock()
    mock_session.connection.connect = MagicMock()
    mock_session.connection.username = "test@example.com"
    mock_session.connection._registration_mode = False
    mock_shell.session_manager.create_session.return_value = mock_session

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_connect("test_server")

    mock_shell.session_manager.create_session.assert_called_once_with("test_server", None)
    mock_session.connection.connect.assert_called_once_with("test_server")
    mock_shell._update_prompt.assert_called_once()
    mock_shell.poutput.assert_called()


def test_connect_failure(mock_shell):
    """Test connection failure"""
    # Mock session with failing connection
    mock_session = MagicMock()
    mock_session.connection.connect.side_effect = ConnectionError("Connection failed")
    mock_shell.session_manager.create_session.return_value = mock_session

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_connect("test_server")

    mock_shell.perror.assert_called_once()


def test_connect_no_config(mock_shell):
    """Test connect when config not loaded"""
    mock_shell.session_manager = None

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_connect("test_server")

    mock_shell.perror.assert_called_with("Configuration not loaded")


def test_disconnect_success(mock_shell):
    """Test successful disconnection"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.current_server = "test_server"
    mock_shell.connection.disconnect = MagicMock()
    mock_shell._update_prompt = MagicMock()

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_disconnect("")

    mock_shell.connection.disconnect.assert_called_once()
    mock_shell._update_prompt.assert_called_once()
    mock_shell.poutput.assert_called()


def test_disconnect_not_connected(mock_shell):
    """Test disconnect when not connected"""
    mock_shell.connection.is_connected = False

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_disconnect("")

    mock_shell.pwarning.assert_called_with("Not connected to any server")


def test_status_connected(mock_shell):
    """Test status when connected"""
    # Mock active session
    mock_session = MagicMock()
    mock_session.id = "1"
    mock_session.label = "test_server"
    mock_session.connection.is_connected = True
    mock_session.connection.current_server = "test_server"
    mock_session.connection.username = "test@example.com"
    mock_session.get_version.return_value = "2.2.6"
    mock_shell.session_manager.active_session = mock_session
    mock_shell.session_manager.list_sessions.return_value = [mock_session]
    mock_shell.config.get_server_url.return_value = "https://test.example.com"
    mock_shell.config.get_server_verify.return_value = True

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_status("")

    assert mock_shell.poutput.call_count >= 3


def test_status_disconnected(mock_shell):
    """Test status when disconnected"""
    mock_shell.session_manager.active_session = None
    mock_shell.session_manager.list_sessions.return_value = []

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_status("")

    mock_shell.poutput.assert_any_call("Not connected")


def test_status_no_config(mock_shell):
    """Test status when config not loaded"""
    mock_shell.session_manager = None

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_status("")

    mock_shell.perror.assert_called_with("Configuration not loaded")


def test_connect_by_number_success(mock_shell):
    """Test connecting to server by number"""
    mock_shell.config.get_all_servers.return_value = {
        "server1": {},
        "server2": {},
        "server3": {},
    }
    # Mock session creation
    mock_session = MagicMock()
    mock_session.id = "2"
    mock_session.connection = MagicMock()
    mock_session.connection.connect = MagicMock()
    mock_session.connection.username = "test@example.com"
    mock_session.connection._registration_mode = False
    mock_shell.session_manager.create_session.return_value = mock_session

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_connect("2")

    # Should create session with server2 (index 1, but display as #2)
    mock_shell.session_manager.create_session.assert_called_once_with("server2", None)
    mock_session.connection.connect.assert_called_once_with("server2")


def test_connect_by_number_invalid_low(mock_shell):
    """Test connecting with invalid low number"""
    mock_shell.config.get_all_servers.return_value = {"server1": {}, "server2": {}}

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_connect("0")

    mock_shell.perror.assert_called()
    mock_shell.session_manager.create_session.assert_not_called()


def test_connect_by_number_invalid_high(mock_shell):
    """Test connecting with invalid high number"""
    mock_shell.config.get_all_servers.return_value = {"server1": {}, "server2": {}}

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_connect("5")

    mock_shell.perror.assert_called()
    mock_shell.session_manager.create_session.assert_not_called()


def test_connect_by_name_still_works(mock_shell):
    """Test that connecting by name still works"""
    # Mock session creation
    mock_session = MagicMock()
    mock_session.id = "2"
    mock_session.connection = MagicMock()
    mock_session.connection.connect = MagicMock()
    mock_session.connection.username = "test@example.com"
    mock_session.connection._registration_mode = False
    mock_shell.session_manager.create_session.return_value = mock_session

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_connect("server1")

    # Should still work with server name
    mock_shell.session_manager.create_session.assert_called_once_with("server1", None)
    mock_session.connection.connect.assert_called_once_with("server1")


def test_connect_registration_mode_suggests_token_login(mock_shell):
    """Test that registration mode message suggests both token-login and register"""
    mock_session = MagicMock()
    mock_session.id = "1"
    mock_session.connection = MagicMock()
    mock_session.connection.connect = MagicMock()
    mock_session.connection._registration_mode = True
    mock_shell.session_manager.create_session.return_value = mock_session
    mock_shell.quiet = False

    conn_cmd = ConnectionCommands(mock_shell)
    conn_cmd.cmd_connect("test_server")

    output = " ".join(str(c) for c in mock_shell.poutput.call_args_list)
    assert "token-login" in output
    assert "register" in output
