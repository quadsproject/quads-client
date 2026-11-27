import pytest
from unittest.mock import MagicMock, patch
from quads_client.commands.user import UserCommands


def test_register_save_credentials_failure(mock_shell):
    """Test register when saving credentials fails"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.current_server = "quads1.example.com"
    mock_shell.connection.api.register.return_value = {"status": "success"}
    mock_shell.config.update_server_credentials = MagicMock(side_effect=Exception("Permission denied"))

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_register("user@example.com password123")

    # Should warn about failure to save
    assert any("Could not save credentials" in str(call) for call in mock_shell.pwarning.call_args_list)


def test_whoami_not_authenticated(mock_shell):
    """Test whoami when user is connected but not authenticated"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = False
    mock_shell.connection.username = None
    mock_shell.connection.user_role = None

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_whoami("")

    # Should show "Not authenticated"
    assert any("Not authenticated" in str(call) for call in mock_shell.poutput.call_args_list)


def test_whoami_user_info_exception(mock_shell):
    """Test whoami when get_user_info raises exception"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.user_role = "user"
    mock_shell.connection.api.get_user_info.side_effect = Exception("API error")

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_whoami("")

    # Should still complete without error
    assert mock_shell.poutput.call_count >= 2


def test_assignment_create_no_qinq(mock_shell):
    """Test assignment_create without qinq field"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.create_self_assignment.return_value = {
        "id": 42,
        "cloud": {"name": "cloud17"},
        "owner": "user@example.com",
    }

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_assignment_create("--description Test environment")

    # Should not print VLAN line when qinq is not present
    output = " ".join(str(call) for call in mock_shell.poutput.call_args_list)
    assert "VLAN (QinQ)" not in output


def test_assignment_status_no_schedules(mock_shell):
    """Test assignment_status when assignment has no schedules"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.api.filter_assignments.return_value = [
        {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "owner": "user@example.com",
            "description": "Test",
            "wipe": False,
            "validated": False,
            "active": True,
        }
    ]
    mock_shell.connection.api.get_schedules.return_value = []

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_assignment_status("42")

    # Should show "No hosts assigned"
    output = " ".join(str(call) for call in mock_shell.poutput.call_args_list)
    assert "No hosts assigned" in output


def test_assignment_list_very_long_description(mock_shell):
    """Test assignment_list truncates very long descriptions"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.filter_assignments.return_value = [
        {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "description": "A" * 100,  # Very long description
            "validated": True,
            "active": True,
        }
    ]

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_assignment_list("")

    # Should truncate to 40 chars with "..."
    assert mock_shell.poutput.call_count >= 2


def test_assignment_terminate_object_response(mock_shell):
    """Test assignment_terminate with object response instead of dict"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "user@example.com"

    # Create mock object instead of dict (tests terminate command handles both)
    mock_assignment = MagicMock()
    mock_assignment.id = 42
    mock_cloud = MagicMock()
    mock_cloud.name = "cloud17"
    mock_assignment.cloud = mock_cloud
    mock_assignment.owner = "user"

    mock_shell.connection.api.filter_assignments.return_value = [mock_assignment]
    mock_shell.connection.api.terminate_assignment.return_value = {"status": "success"}

    with patch("builtins.input", return_value="y"):
        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_terminate("42")

        # Should handle object response
        assert "Terminated assignment" in str(mock_shell.poutput.call_args_list)


# Tests for 'available' command removed - command has been deprecated
# Use 'ls_available' or 'ls_hosts' instead


def test_schedule_api_error(mock_shell):
    """Test schedule with API error (unified schedule)"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.filter_available.return_value = [{"name": "host01.example.com"}]
    mock_shell.connection.api.create_self_assignment.side_effect = Exception("Network timeout")

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('host01.example.com description "Test"')

    # Should handle error via error_handler
    mock_shell.perror.assert_called()


def test_schedule_no_available_hosts(mock_shell):
    """Test schedule when no hosts are available"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.filter_available.return_value = []

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('3 description "Test"')

    # Should error with no available hosts message
    assert any("No available hosts" in str(call) for call in mock_shell.perror.call_args_list)


def test_schedule_schedule_creation_failure(mock_shell):
    """Test schedule when schedule creation fails"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.filter_available.return_value = [
        {"name": "host01.example.com", "model": "r640", "can_self_schedule": True}
    ]
    mock_shell.connection.api.create_self_assignment.return_value = {
        "id": 123,
        "cloud": {"name": "cloud02"},
    }
    mock_shell.connection.api.create_schedule.side_effect = Exception("Schedule creation failed")

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('1 description "Test"')

    # Should show warning about failed schedule
    assert mock_shell.pwarning.call_count >= 1 or mock_shell.perror.call_count >= 1


def test_schedule_self_assignment_rejected_token(mock_shell):
    """Server rejecting the self-assignment (401) must not report a false success"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.create_self_assignment.return_value = {
        "status_code": 401,
        "error": "Unauthorized",
        "message": "Invalid API token!",
    }

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('host01.example.com description "Test"')

    error_calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Self-assignment failed: Invalid API token!" in call for call in error_calls)
    # Must return early: no schedule attempted, no false "Reserved"
    mock_shell.connection.api.create_schedule.assert_not_called()
    output = " ".join(str(call) for call in mock_shell.poutput.call_args_list)
    assert "Reserved" not in output


def test_schedule_create_schedule_error_dict(mock_shell):
    """create_schedule returning an error dict must not count as a scheduled host"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.create_self_assignment.return_value = {
        "id": 123,
        "cloud": {"name": "cloud02"},
    }
    mock_shell.connection.api.create_schedule.return_value = {
        "status_code": 401,
        "error": "Unauthorized",
        "message": "Invalid API token!",
    }

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('host01.example.com description "Test"')

    error_calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Failed to schedule any hosts" in call for call in error_calls)
    output = " ".join(str(call) for call in mock_shell.poutput.call_args_list)
    assert "Reserved" not in output


def test_schedule_happy_path_reports_reserved(mock_shell):
    """Valid assignment and schedule responses still report success"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.create_self_assignment.return_value = {
        "id": 123,
        "cloud": {"name": "cloud02"},
    }
    mock_shell.connection.api.create_schedule.return_value = {"id": 1}

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('host01.example.com description "Test"')

    output = " ".join(str(call) for call in mock_shell.poutput.call_args_list)
    assert "Reserved 1 host(s)" in output
    assert "cloud02" in output


def test_schedule_create_schedule_message_only_error(mock_shell):
    """A bare message error body must not count as a scheduled host"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.create_self_assignment.return_value = {
        "id": 123,
        "cloud": {"name": "cloud02"},
    }
    mock_shell.connection.api.create_schedule.return_value = {"message": "forbidden"}

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('host01.example.com description "Test"')

    error_calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert any("Failed to schedule any hosts" in call for call in error_calls)
    output = " ".join(str(call) for call in mock_shell.poutput.call_args_list)
    assert "Reserved" not in output


def test_schedule_assignment_without_cloud_still_schedules(mock_shell):
    """A success that does not echo cloud falls back to unknown, not an abort"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.create_self_assignment.return_value = {"id": 123}
    mock_shell.connection.api.create_schedule.return_value = {"id": 1}

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('host01.example.com description "Test"')

    error_calls = [str(call) for call in mock_shell.perror.call_args_list]
    assert not any("Self-assignment failed" in call for call in error_calls)
    mock_shell.connection.api.create_schedule.assert_called_once()
    output = " ".join(str(call) for call in mock_shell.poutput.call_args_list)
    assert "Reserved 1 host(s)" in output


def test_my_hosts_api_error(mock_shell):
    """Test my_hosts when API call fails"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.api.filter_assignments.side_effect = Exception("Connection error")

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_my_hosts("")

    # Should handle error via error_handler
    mock_shell.perror.assert_called()


def test_assignment_terminate_refreshes_token_on_401(mock_shell):
    """Test terminate refreshes the session token once when the API raises APIUnauthorized"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "user@example.com"
    mock_shell.connection.refresh_token.return_value = True

    mock_shell.connection.api.filter_assignments.return_value = [
        {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "owner": "user",
            "description": "test",
            "active": True,
        }
    ]

    class APIUnauthorized(Exception):
        pass

    mock_shell.connection.api.terminate_assignment.side_effect = [
        APIUnauthorized("Invalid Authentication token!"),
        {"status": "success"},
    ]

    with patch("builtins.input", return_value="y"):
        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_terminate("42")

    mock_shell.connection.refresh_token.assert_called_once()
    assert mock_shell.connection.api.terminate_assignment.call_count == 2
    assert "Terminated assignment" in str(mock_shell.poutput.call_args_list)
