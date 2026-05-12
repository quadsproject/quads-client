import pytest
from unittest.mock import MagicMock, patch
from quads_client.connection import ConnectionManager, ConnectionError


def test_connection_initial_state(mock_config):
    """Test ConnectionManager initial state"""
    conn = ConnectionManager(mock_config)
    assert not conn.is_connected
    assert conn.current_server is None
    assert conn.username is None


def test_connection_connect_success(mock_config, mock_api):
    """Test successful connection to server"""
    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")

        assert conn.is_connected
        assert conn.current_server == "test_server"
        assert conn.username == "test@example.com"
        assert conn._token == "test_token_123"
        mock_api.login.assert_called_once()


def test_connection_connect_invalid_server(mock_config):
    """Test connecting to unknown server"""
    conn = ConnectionManager(mock_config)
    with pytest.raises(ConnectionError, match="Unknown server"):
        conn.connect("nonexistent_server")


def test_connection_connect_missing_credentials(mock_config):
    """Test connecting with missing credentials enters registration mode"""
    mock_config.get_server_credentials.return_value = ("", "")

    with patch("quads_client.connection.QuadsApi"):
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")

        # Should connect in registration mode
        assert conn.is_connected
        assert conn._registration_mode is True
        assert conn.username is None


def test_connection_connect_login_failure(mock_config, mock_api):
    """Test connection when login fails"""
    mock_api.login.return_value = {"status": "failure"}

    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        with pytest.raises(ConnectionError, match="Login failed"):
            conn.connect("test_server")


def test_connection_api_property_when_disconnected(mock_config):
    """Test accessing API property when not connected"""
    conn = ConnectionManager(mock_config)
    with pytest.raises(ConnectionError, match="Not connected"):
        _ = conn.api


def test_connection_api_property_when_connected(mock_config, mock_api):
    """Test accessing API property when connected"""
    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")
        assert conn.api == mock_api


def test_connection_disconnect(mock_config, mock_api):
    """Test disconnecting from server"""
    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")
        assert conn.is_connected

        conn.disconnect()
        assert not conn.is_connected
        assert conn.current_server is None
        assert conn.username is None
        assert conn._token is None


def test_connection_get_available_servers(mock_config):
    """Test retrieving list of available servers"""
    conn = ConnectionManager(mock_config)
    servers = conn.get_available_servers()
    assert "test_server" in servers


def test_connection_uses_ssl_verification(mock_config, mock_api):
    """Test that connection uses SSL verification from config"""
    mock_config.get_server_verify.return_value = True

    with patch("quads_client.connection.QuadsApi") as mock_quads_api:
        mock_quads_api.return_value = mock_api
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")

        mock_quads_api.assert_called_once()
        call_kwargs = mock_quads_api.call_args[1]
        assert call_kwargs["verify"] is True


def test_connection_ssl_verification_disabled(mock_config, mock_api):
    """Test connection with SSL verification disabled"""
    mock_config.get_server_verify.return_value = False

    with patch("quads_client.connection.QuadsApi") as mock_quads_api:
        mock_quads_api.return_value = mock_api
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")

        mock_quads_api.assert_called_once()
        call_kwargs = mock_quads_api.call_args[1]
        assert call_kwargs["verify"] is False


def test_connection_uses_base_url_parameter(mock_config, mock_api):
    """Test that connection uses base_url parameter (not url)"""
    with patch("quads_client.connection.QuadsApi") as mock_quads_api:
        mock_quads_api.return_value = mock_api
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")

        mock_quads_api.assert_called_once()
        call_kwargs = mock_quads_api.call_args[1]
        assert "base_url" in call_kwargs
        assert "url" not in call_kwargs


def test_connection_refresh_token_success(mock_config, mock_api):
    """Test successful token refresh"""
    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")

        # Reset login call count
        mock_api.login.reset_mock()
        mock_api.login.return_value = {"status": "success"}
        mock_api.token = "new_token_456"

        # Refresh token
        result = conn.refresh_token()

        assert result is True
        assert conn._token == "new_token_456"
        mock_api.login.assert_called_once()


def test_connection_refresh_token_not_connected(mock_config):
    """Test refresh token when not connected"""
    conn = ConnectionManager(mock_config)
    result = conn.refresh_token()
    assert result is False


def test_connection_refresh_token_registration_mode(mock_config, mock_api):
    """Test refresh token when in registration mode"""
    mock_config.get_server_credentials.return_value = ("", "")

    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")

        # Should be in registration mode
        assert conn._registration_mode is True

        # Refresh should fail
        result = conn.refresh_token()
        assert result is False


def test_connection_refresh_token_no_credentials(mock_config, mock_api):
    """Test refresh token when credentials are missing"""
    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")

        # Change credentials to empty
        mock_config.get_server_credentials.return_value = ("", "")

        # Refresh should fail
        result = conn.refresh_token()
        assert result is False


def test_connection_refresh_token_login_failed(mock_config, mock_api):
    """Test refresh token when login fails"""
    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")

        # Make login fail on refresh
        mock_api.login.return_value = {"status": "failure"}

        # Refresh should fail
        result = conn.refresh_token()
        assert result is False


def test_connection_refresh_token_exception(mock_config, mock_api):
    """Test refresh token when an exception occurs"""
    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")

        # Make login raise exception on refresh
        mock_api.login.side_effect = Exception("Network error")

        # Refresh should fail gracefully
        result = conn.refresh_token()
        assert result is False


def test_connection_error_json_parsing(mock_config, mock_api):
    """Test connection error handling for JSON parsing errors with credentials"""
    mock_api.login.side_effect = Exception("Expecting value: line 1 column 1 (char 0)")

    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        # With credentials configured, JSON parsing error suggests wrong credentials
        with pytest.raises(ConnectionError, match="incorrect credentials"):
            conn.connect("test_server")


def test_connection_error_ssl_certificate(mock_config, mock_api):
    """Test connection error handling for SSL certificate errors"""
    mock_api.login.side_effect = Exception("SSL certificate verify failed")

    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        with pytest.raises(ConnectionError, match="SSL certificate verification failed"):
            conn.connect("test_server")


def test_connection_error_connection_refused(mock_config, mock_api):
    """Test connection error handling for connection refused"""
    mock_api.login.side_effect = Exception("Connection refused")

    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        with pytest.raises(ConnectionError, match="Server is unreachable"):
            conn.connect("test_server")


def test_connection_error_unauthorized(mock_config, mock_api):
    """Test connection error handling for 401 unauthorized"""
    mock_api.login.side_effect = Exception("401 Unauthorized")

    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        with pytest.raises(ConnectionError, match="Authentication failed"):
            conn.connect("test_server")


def test_connection_error_timeout(mock_config, mock_api):
    """Test connection error handling for timeout"""
    mock_api.login.side_effect = Exception("Connection timeout")

    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn = ConnectionManager(mock_config)
        with pytest.raises(ConnectionError, match="Connection timed out"):
            conn.connect("test_server")


def test_connection_truststore_inject_on_darwin(mock_config, mock_api):
    """Test that truststore.inject_into_ssl() is called on macOS"""
    mock_truststore = MagicMock()

    with (
        patch("quads_client.connection.QuadsApi", return_value=mock_api),
        patch("quads_client.connection.sys") as mock_sys,
        patch("quads_client.connection._has_truststore", True),
        patch("quads_client.connection.truststore", mock_truststore, create=True),
    ):
        mock_sys.platform = "darwin"
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")
        mock_truststore.inject_into_ssl.assert_called_once()


def test_connection_truststore_skip_on_linux(mock_config, mock_api):
    """Test that truststore is not injected on Linux"""
    with (
        patch("quads_client.connection.QuadsApi", return_value=mock_api),
        patch("quads_client.connection.sys") as mock_sys,
    ):
        mock_sys.platform = "linux"
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")


def test_connection_truststore_missing_on_darwin(mock_config, mock_api):
    """Test that missing truststore on macOS still connects"""
    with (
        patch("quads_client.connection.QuadsApi", return_value=mock_api),
        patch("quads_client.connection.sys") as mock_sys,
        patch("quads_client.connection._has_truststore", False),
    ):
        mock_sys.platform = "darwin"
        conn = ConnectionManager(mock_config)
        conn.connect("test_server")
        assert conn.is_connected
