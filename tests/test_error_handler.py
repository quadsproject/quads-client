import pytest
from unittest.mock import MagicMock, patch
from quads_client.error_handler import auto_refresh_on_auth_error, handle_api_error


def test_auto_refresh_on_auth_error_success():
    """Test auto_refresh wrapper when API call succeeds"""
    mock_shell = MagicMock()
    api_func = MagicMock(return_value={"status": "success"})

    result = auto_refresh_on_auth_error(mock_shell, api_func, "arg1", kwarg="value")

    assert result == {"status": "success"}
    api_func.assert_called_once_with("arg1", kwarg="value")
    # Should not attempt refresh
    mock_shell.connection.refresh_token.assert_not_called()


def test_auto_refresh_on_auth_error_401_error():
    """Test auto_refresh wrapper handles 401 error and retries"""
    mock_shell = MagicMock()
    mock_shell.connection.refresh_token.return_value = True

    # First call raises 401, second call succeeds
    api_func = MagicMock(side_effect=[Exception("401 Unauthorized"), {"status": "success"}])

    result = auto_refresh_on_auth_error(mock_shell, api_func)

    assert result == {"status": "success"}
    assert api_func.call_count == 2
    mock_shell.connection.refresh_token.assert_called_once()


def test_auto_refresh_on_auth_error_unauthorized_error():
    """Test auto_refresh wrapper handles unauthorized error"""
    mock_shell = MagicMock()
    mock_shell.connection.refresh_token.return_value = True

    api_func = MagicMock(side_effect=[Exception("Unauthorized access"), {"status": "success"}])

    result = auto_refresh_on_auth_error(mock_shell, api_func)

    assert result == {"status": "success"}
    assert api_func.call_count == 2
    mock_shell.connection.refresh_token.assert_called_once()


def test_auto_refresh_on_auth_error_token_expired():
    """Test auto_refresh wrapper handles token expired error"""
    mock_shell = MagicMock()
    mock_shell.connection.refresh_token.return_value = True

    api_func = MagicMock(side_effect=[Exception("Token has expired"), {"status": "success"}])

    result = auto_refresh_on_auth_error(mock_shell, api_func)

    assert result == {"status": "success"}
    assert api_func.call_count == 2
    mock_shell.connection.refresh_token.assert_called_once()


def test_auto_refresh_on_auth_error_refresh_failed():
    """Test auto_refresh wrapper when token refresh fails"""
    mock_shell = MagicMock()
    mock_shell.connection.refresh_token.return_value = False

    api_func = MagicMock(side_effect=Exception("401 Unauthorized"))

    with pytest.raises(Exception, match="401 Unauthorized"):
        auto_refresh_on_auth_error(mock_shell, api_func)

    api_func.assert_called_once()
    mock_shell.connection.refresh_token.assert_called_once()


def test_auto_refresh_on_auth_error_retry_failed():
    """Test auto_refresh wrapper when retry still fails after refresh"""
    mock_shell = MagicMock()
    mock_shell.connection.refresh_token.return_value = True

    # Both calls fail
    api_func = MagicMock(side_effect=[Exception("401 Unauthorized"), Exception("Still unauthorized")])

    with pytest.raises(Exception, match="Still unauthorized"):
        auto_refresh_on_auth_error(mock_shell, api_func)

    assert api_func.call_count == 2
    mock_shell.connection.refresh_token.assert_called_once()


def test_auto_refresh_on_auth_error_non_auth_error():
    """Test auto_refresh wrapper with non-authentication error"""
    mock_shell = MagicMock()

    api_func = MagicMock(side_effect=Exception("Network error"))

    with pytest.raises(Exception, match="Network error"):
        auto_refresh_on_auth_error(mock_shell, api_func)

    api_func.assert_called_once()
    # Should not attempt refresh for non-auth errors
    mock_shell.connection.refresh_token.assert_not_called()


def test_handle_api_error_host_limit():
    """Test handle_api_error for host limit errors"""
    mock_shell = MagicMock()
    error = Exception("host limit exceeded")

    handle_api_error(mock_shell, error, "Scheduling")

    assert mock_shell.perror.call_count >= 2
    calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Server limit" in str(call) for call in calls)


def test_handle_api_error_cloud_limit():
    """Test handle_api_error for cloud limit errors"""
    mock_shell = MagicMock()
    error = Exception("user cloud limit exceeded")

    handle_api_error(mock_shell, error, "Scheduling")

    assert mock_shell.perror.call_count >= 2
    calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Server limit" in str(call) for call in calls)


def test_handle_api_error_401():
    """Test handle_api_error for authentication errors"""
    mock_shell = MagicMock()
    error = Exception("401 Unauthorized")

    handle_api_error(mock_shell, error, "API call")

    assert mock_shell.perror.call_count >= 2
    calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Authentication failed" in str(call) for call in calls)


def test_handle_api_error_403():
    """Test handle_api_error for permission errors"""
    mock_shell = MagicMock()
    error = Exception("403 Forbidden")

    handle_api_error(mock_shell, error, "API call")

    mock_shell.perror.assert_called_once()
    call = str(mock_shell.perror.call_args)
    assert "Permission denied" in call


def test_handle_api_error_connection():
    """Test handle_api_error for connection errors"""
    mock_shell = MagicMock()
    error = Exception("connection timeout")

    handle_api_error(mock_shell, error, "API call")

    assert mock_shell.perror.call_count >= 2
    calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Connection failed" in str(call) for call in calls)


def test_require_connection_connected():
    """Test require_connection when connected"""
    from quads_client.error_handler import require_connection

    mock_shell = MagicMock()
    mock_shell.connection.is_connected = True

    result = require_connection(mock_shell)

    assert result is True
    mock_shell.perror.assert_not_called()


def test_require_connection_not_connected():
    """Test require_connection when not connected"""
    from quads_client.error_handler import require_connection

    mock_shell = MagicMock()
    mock_shell.connection = None

    result = require_connection(mock_shell)

    assert result is False
    mock_shell.perror.assert_called_with("Not connected to any server")


def test_require_connection_connection_exists_but_not_connected():
    """Test require_connection when connection exists but is_connected is False"""
    from quads_client.error_handler import require_connection

    mock_shell = MagicMock()
    mock_shell.connection.is_connected = False

    result = require_connection(mock_shell)

    assert result is False
    mock_shell.perror.assert_called_with("Not connected to any server")


def test_require_auth_authenticated():
    """Test require_auth when authenticated"""
    from quads_client.error_handler import require_auth

    mock_shell = MagicMock()
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True

    result = require_auth(mock_shell)

    assert result is True


def test_require_auth_not_authenticated():
    """Test require_auth when not authenticated"""
    from quads_client.error_handler import require_auth

    mock_shell = MagicMock()
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = False

    result = require_auth(mock_shell)

    assert result is False
    mock_shell.perror.assert_called_with("Not authenticated. Use 'login' command first.")


def test_require_admin_is_admin():
    """Test require_admin when user is admin"""
    from quads_client.error_handler import require_admin

    mock_shell = MagicMock()
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = True

    result = require_admin(mock_shell)

    assert result is True


def test_require_admin_not_admin():
    """Test require_admin when user is not admin"""
    from quads_client.error_handler import require_admin

    mock_shell = MagicMock()
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False

    result = require_admin(mock_shell)

    assert result is False
    mock_shell.perror.assert_called_with("Permission denied: This command requires admin role")


def test_handle_api_error_jira_not_configured():
    """Test handle_api_error for Jira not configured"""
    mock_shell = MagicMock()
    error = Exception("Ticketing system not configured")

    handle_api_error(mock_shell, error, "Scheduling")

    assert mock_shell.perror.call_count >= 5
    calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Server configuration issue" in str(call) for call in calls)
    assert any("ssm_jira_create_ticket: false" in str(call) for call in calls)


def test_handle_api_error_missing_ticket():
    """Test handle_api_error for missing ticket"""
    mock_shell = MagicMock()
    error = Exception("Missing Jira ticket number")

    handle_api_error(mock_shell, error, "Scheduling")

    assert mock_shell.perror.call_count >= 3
    calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Server configuration issue" in str(call) for call in calls)
    assert any("ssm_jira_create_ticket: true" in str(call) for call in calls)


def test_handle_api_error_404():
    """Test handle_api_error for 404 not found errors"""
    mock_shell = MagicMock()
    error = Exception("404 Not Found")

    handle_api_error(mock_shell, error, "Fetching resource")

    mock_shell.perror.assert_called_once()
    assert "Not found" in str(mock_shell.perror.call_args)


def test_handle_api_error_500():
    """Test handle_api_error for 500 server errors"""
    mock_shell = MagicMock()
    error = Exception("500 Internal Server Error")

    handle_api_error(mock_shell, error, "API call")

    assert mock_shell.perror.call_count >= 2
    calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Server error" in str(call) for call in calls)
    assert any("administrator" in str(call) for call in calls)


def test_handle_api_error_generic():
    """Test handle_api_error for generic errors"""
    mock_shell = MagicMock()
    error = Exception("Something went wrong")

    handle_api_error(mock_shell, error, "Custom operation")

    mock_shell.perror.assert_called_once()
    assert "Custom operation failed" in str(mock_shell.perror.call_args)


def test_handle_api_error_api_unauthorized_exception():
    """Test handle_api_error for quads-lib APIUnauthorized exceptions"""
    mock_shell = MagicMock()

    class APIUnauthorized(Exception):
        pass

    error = APIUnauthorized("Invalid Authentication token!")

    handle_api_error(mock_shell, error, "Terminate")

    calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Authentication failed" in str(call) for call in calls)
    assert any("Run 'login' to refresh your session" in str(call) for call in calls)


def test_auto_refresh_on_auth_error_unauthorized_class():
    """Test auto_refresh wrapper refreshes for APIUnauthorized even when the message is not auth-shaped"""
    mock_shell = MagicMock()
    mock_shell.connection.refresh_token.return_value = True

    class APIUnauthorized(Exception):
        pass

    api_func = MagicMock(side_effect=[APIUnauthorized("Failed to parse response"), {"status": "success"}])

    result = auto_refresh_on_auth_error(mock_shell, api_func)

    assert result == {"status": "success"}
    assert api_func.call_count == 2
    mock_shell.connection.refresh_token.assert_called_once()
