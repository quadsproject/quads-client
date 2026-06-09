import pytest
from unittest.mock import MagicMock, patch
from quads_client.commands.user import UserCommands


# Tests for 'available' command removed - command has been deprecated
# Use 'ls_available' or 'ls_hosts' instead


def test_schedule_success(mock_shell):
    """Test schedule command success - superseded by test_commands_unified_schedule.py"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "test@example.com"
    mock_shell.connection.api.filter_available.return_value = [{"name": "host01.example.com"}]
    mock_shell.connection.api.create_self_assignment.return_value = {
        "id": 42,
        "cloud": {"name": "cloud17"},
    }
    mock_shell.connection.api.create_schedule.return_value = {"id": 1}

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('host01.example.com description "Test"')

    mock_shell.poutput.assert_called()


def test_schedule_missing_args(mock_shell):
    """Test schedule with missing arguments - superseded by test_commands_unified_schedule.py"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule("host01.example.com")

    mock_shell.perror.assert_called()


def test_schedule_forbidden(mock_shell):
    """Test schedule when user lacks permission - superseded by test_commands_unified_schedule.py"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "test@example.com"
    mock_shell.connection.api.filter_available.return_value = [{"name": "host01.example.com"}]
    mock_shell.connection.api.create_self_assignment.side_effect = Exception("403 Forbidden")

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('host01.example.com description "Test"')

    mock_shell.perror.assert_called()


def test_my_hosts_success(mock_shell):
    """Test my_hosts command success - updated for unified schedule"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "test@example.com"
    mock_shell.connection.api.filter_assignments.return_value = [
        {"id": 1, "owner": "test", "cloud": {"name": "cloud02"}, "description": "Test assignment"}
    ]
    mock_shell.connection.api.get_schedules.return_value = [
        {"id": 1, "host": {"name": "host01.example.com"}, "start": "2026-05-01", "end": "2026-05-15"}
    ]

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_my_hosts("")

    mock_shell.connection.api.filter_assignments.assert_called_once_with({"owner": "test", "active": True})
    mock_shell.connection.api.get_schedules.assert_called_once_with({"assignment_id": 1})
    assert mock_shell.poutput.call_count >= 2


def test_my_hosts_no_schedules(mock_shell):
    """Test my_hosts with no schedules"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "test@example.com"
    mock_shell.connection.api.filter_assignments.return_value = []

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_my_hosts("")

    mock_shell.poutput.assert_called_with("No active hosts scheduled by test")


def test_my_hosts_not_authenticated(mock_shell):
    """Test my_hosts when not authenticated"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = False

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_my_hosts("")

    mock_shell.perror.assert_called_with("Not authenticated. Use 'login' command first.")


def test_my_hosts_duplicate_hosts_across_assignments(mock_shell):
    """Test my_hosts deduplicates hosts that appear in multiple assignments"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "test@example.com"

    # Three assignments with same 3 hosts in each (simulating the user's bug report)
    mock_shell.connection.api.filter_assignments.return_value = [
        {"id": 138, "owner": "test", "cloud": {"name": "cloud02"}, "description": "SSM QUADS Client Test2"},
        {"id": 139, "owner": "test", "cloud": {"name": "cloud03"}, "description": "SSM QUADS Client Test3"},
        {"id": 140, "owner": "test", "cloud": {"name": "cloud04"}, "description": "SSM QUADS Client Test4"},
    ]

    # Each assignment has the same 3 hosts (simulating duplicate schedules)
    def mock_get_schedules(filters):
        return [
            {
                "id": 1,
                "host": {"name": "e28-h26-000-r650.stage.rdu2.scalelab.example.com"},
                "end": "Sun, 10 May 2026 21:00:00 GMT",
            },
            {
                "id": 2,
                "host": {"name": "f07-h36-000-1029u.stage.rdu2.scalelab.example.com"},
                "end": "Sun, 10 May 2026 21:00:00 GMT",
            },
            {
                "id": 3,
                "host": {"name": "f18-h29-000-1029p.stage.rdu2.scalelab.example.com"},
                "end": "Sun, 10 May 2026 21:00:00 GMT",
            },
        ]

    mock_shell.connection.api.get_schedules.side_effect = mock_get_schedules

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_my_hosts("")

    # Verify we queried for assignments
    mock_shell.connection.api.filter_assignments.assert_called_once_with({"owner": "test", "active": True})

    # Verify poutput was called (for header, table, and total)
    assert mock_shell.poutput.call_count >= 3

    # Verify the last call shows "Total unique hosts: 3" (not 9)
    last_call = str(mock_shell.poutput.call_args_list[-1])
    assert "Total unique hosts: 3" in last_call


def test_my_hosts_validated_shows_completed_progress(mock_shell):
    """Test my_hosts shows 12/12 progress for validated assignments"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "test@example.com"
    mock_shell.connection.api.filter_assignments.return_value = [
        {
            "id": 1,
            "owner": "test",
            "cloud": {"name": "cloud02"},
            "description": "Test",
            "validated": True,
        }
    ]
    mock_shell.connection.api.get_schedules.return_value = [
        {"id": 1, "host": {"name": "host01.example.com"}, "end": "2026-06-15"}
    ]
    mock_shell.connection.api.get_all_move_status.return_value = []

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_my_hosts("")

    output = " ".join(str(c) for c in mock_shell.poutput.call_args_list)
    assert "Active" in output
    assert "12/12" in output


def test_my_hosts_provisioning_with_move_progress(mock_shell):
    """Test my_hosts shows real move progress for provisioning hosts"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "test@example.com"
    mock_shell.connection.api.filter_assignments.return_value = [
        {
            "id": 1,
            "owner": "test",
            "cloud": {"name": "cloud03"},
            "description": "Test",
            "validated": False,
        }
    ]
    mock_shell.connection.api.get_schedules.return_value = [
        {"id": 1, "host": {"name": "host01.example.com"}, "end": "2026-06-15"}
    ]
    mock_shell.connection.api.get_all_move_status.return_value = [
        {"host": "host01.example.com", "status": "hardware_prep"},
    ]

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_my_hosts("")

    output = " ".join(str(c) for c in mock_shell.poutput.call_args_list)
    assert "Hardware Prep" in output
    assert "4/12" in output


def test_my_hosts_failed_move(mock_shell):
    """Test my_hosts shows Failed status when move has failed"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "test@example.com"
    mock_shell.connection.api.filter_assignments.return_value = [
        {
            "id": 1,
            "owner": "test",
            "cloud": {"name": "cloud03"},
            "description": "Test",
            "validated": False,
        }
    ]
    mock_shell.connection.api.get_schedules.return_value = [
        {"id": 1, "host": {"name": "host01.example.com"}, "end": "2026-06-15"}
    ]
    mock_shell.connection.api.get_all_move_status.return_value = [
        {"host": "host01.example.com", "status": "failed"},
    ]

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_my_hosts("")

    output = " ".join(str(c) for c in mock_shell.poutput.call_args_list)
    assert "Failed" in output
    assert "FAILED" in output


def test_my_hosts_scheduled_no_move_data(mock_shell):
    """Test my_hosts shows Scheduled status when not validated and no move data"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "test@example.com"
    mock_shell.connection.api.filter_assignments.return_value = [
        {
            "id": 1,
            "owner": "test",
            "cloud": {"name": "cloud03"},
            "description": "Test",
            "validated": False,
        }
    ]
    mock_shell.connection.api.get_schedules.return_value = [
        {"id": 1, "host": {"name": "host01.example.com"}, "end": "2026-06-15"}
    ]
    mock_shell.connection.api.get_all_move_status.return_value = []

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_my_hosts("")

    output = " ".join(str(c) for c in mock_shell.poutput.call_args_list)
    assert "Scheduled" in output
    assert "Awaiting move" in output


def test_my_hosts_move_status_api_error(mock_shell):
    """Test my_hosts handles move status API errors gracefully"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.username = "test@example.com"
    mock_shell.connection.api.filter_assignments.return_value = [
        {
            "id": 1,
            "owner": "test",
            "cloud": {"name": "cloud02"},
            "description": "Test",
            "validated": True,
        }
    ]
    mock_shell.connection.api.get_schedules.return_value = [
        {"id": 1, "host": {"name": "host01.example.com"}, "end": "2026-06-15"}
    ]
    mock_shell.connection.api.get_all_move_status.side_effect = Exception("Connection refused")

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_my_hosts("")

    output = " ".join(str(c) for c in mock_shell.poutput.call_args_list)
    assert "host01.example.com" in output


def test_schedule_not_authenticated(mock_shell):
    """Test schedule when not authenticated"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = False

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule("host01.example.com cloud02")

    mock_shell.perror.assert_called_with("Not authenticated. Use 'login' command first.")


def test_schedule_count_with_dict_hosts(mock_shell):
    """Test schedule with count mode when API returns dicts"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "test@example.com"

    # API returns list of dicts
    mock_shell.connection.api.filter_available.return_value = [
        {"name": "host01.example.com"},
        {"name": "host02.example.com"},
    ]
    mock_shell.connection.api.create_self_assignment.return_value = {
        "id": 42,
        "cloud": {"name": "cloud17"},
    }
    mock_shell.connection.api.create_schedule.return_value = {"id": 1}

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('2 description "Test"')

    # Should create schedule for 2 hosts
    assert mock_shell.connection.api.create_schedule.call_count == 2


def test_schedule_count_with_object_hosts(mock_shell):
    """Test schedule with count mode when API returns objects"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "test@example.com"

    # API returns list of objects with name attribute
    class HostObj:
        def __init__(self, name):
            self.name = name

    mock_shell.connection.api.filter_available.return_value = [
        HostObj("host01.example.com"),
        HostObj("host02.example.com"),
    ]
    mock_shell.connection.api.create_self_assignment.return_value = {
        "id": 42,
        "cloud": {"name": "cloud17"},
    }
    mock_shell.connection.api.create_schedule.return_value = {"id": 1}

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('2 description "Test"')

    # Should create schedule for 2 hosts
    assert mock_shell.connection.api.create_schedule.call_count == 2


def test_terminate_help(mock_shell):
    """Test terminate command with help flag"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_terminate("?")

    # Should print usage, not error
    assert any("Usage:" in str(call) for call in mock_shell.poutput.call_args_list)


def test_terminate_help_dash_h(mock_shell):
    """Test terminate command with -h flag"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_terminate("-h")

    # Should print usage, not error
    assert any("Usage:" in str(call) for call in mock_shell.poutput.call_args_list)


def test_terminate_help_help_flag(mock_shell):
    """Test terminate command with --help flag"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_terminate("--help")

    # Should print usage, not error
    assert any("Usage:" in str(call) for call in mock_shell.poutput.call_args_list)


def test_schedule_count_with_string_hosts(mock_shell):
    """Test schedule with count mode when API returns plain strings"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.username = "test@example.com"

    # API returns list of plain hostname strings (new behavior)
    mock_shell.connection.api.filter_available.return_value = [
        "host01.example.com",
        "host02.example.com",
    ]
    mock_shell.connection.api.create_self_assignment.return_value = {
        "id": 42,
        "cloud": {"name": "cloud17"},
    }
    mock_shell.connection.api.create_schedule.return_value = {"id": 1}

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_schedule('2 description "Test"')

    # Should create schedule for 2 hosts
    assert mock_shell.connection.api.create_schedule.call_count == 2


def test_assignment_list_sorted_by_cloud_number(mock_shell):
    """Test that assignment_list output is sorted by cloud number"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection.is_admin = True
    mock_shell.connection.username = "admin@example.com"
    mock_shell.connection.api.filter_assignments.return_value = [
        {
            "id": 264,
            "cloud": {"name": "cloud21"},
            "owner": "user1",
            "description": "Test A",
            "validated": True,
        },
        {
            "id": 252,
            "cloud": {"name": "cloud06"},
            "owner": "user2",
            "description": "Test B",
            "validated": False,
        },
        {
            "id": 16,
            "cloud": {"name": "cloud20"},
            "owner": "user3",
            "description": "Test C",
            "validated": True,
        },
    ]

    user_commands = UserCommands(mock_shell)
    user_commands.cmd_assignment_list("")

    output_calls = mock_shell.poutput.call_args_list
    table_output = output_calls[-1][0][0]
    cloud06_pos = table_output.find("cloud06")
    cloud20_pos = table_output.find("cloud20")
    cloud21_pos = table_output.find("cloud21")
    assert cloud06_pos < cloud20_pos < cloud21_pos


def test_token_login_programmatic_success(mock_shell):
    """Test successful SSO token login"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = False
    mock_shell.connection.current_server = "test_server"
    mock_shell.connection._detect_role_from_api = MagicMock(return_value="user")
    mock_shell.config.get_server_url.return_value = "https://test.example.com"
    mock_shell.config.get_server_verify.return_value = True

    mock_api = MagicMock()
    mock_api.get_version.return_value = {"version": "2.2.6"}

    user_cmd = UserCommands(mock_shell)

    with patch("quads_lib.QuadsApi", return_value=mock_api):
        success, message, role = user_cmd.token_login_programmatic("bob@example.com", "qat_test_token_123")

    assert success is True
    assert "SSO token" in message
    assert mock_shell.connection._token == "qat_test_token_123"
    assert mock_shell.connection._username == "bob@example.com"
    assert mock_shell.connection._registration_mode is False


def test_token_login_programmatic_invalid_prefix(mock_shell):
    """Test token login rejects tokens without qat_ prefix"""
    mock_shell.connection.is_connected = True

    user_cmd = UserCommands(mock_shell)
    success, message, role = user_cmd.token_login_programmatic("bob@example.com", "invalid_token_no_prefix")

    assert success is False
    assert "qat_" in message


def test_token_login_programmatic_not_connected(mock_shell):
    """Test token login when not connected"""
    mock_shell.connection = None

    user_cmd = UserCommands(mock_shell)
    success, message, role = user_cmd.token_login_programmatic("bob@example.com", "qat_some_token")

    assert success is False
    assert "Not connected" in message


def test_token_login_programmatic_invalid_token(mock_shell):
    """Test token login with a revoked/invalid token"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.current_server = "test_server"
    mock_shell.config.get_server_url.return_value = "https://test.example.com"
    mock_shell.config.get_server_verify.return_value = True

    mock_api = MagicMock()
    mock_api.get_version.side_effect = Exception("401 Unauthorized")

    user_cmd = UserCommands(mock_shell)

    with patch("quads_lib.QuadsApi", return_value=mock_api):
        success, message, role = user_cmd.token_login_programmatic("bob@example.com", "qat_revoked_token")

    assert success is False
    assert "revoked" in message.lower() or "invalid" in message.lower()


def test_register_programmatic_403_disabled(mock_shell):
    """Test register_programmatic returns clean message when server returns 403"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.register.return_value = {
        "status_code": 403,
        "status": "fail",
        "message": "Self-registration is disabled.",
    }

    user_cmd = UserCommands(mock_shell)
    success, message, role = user_cmd.register_programmatic("new@example.com", "password123")

    assert success is False
    assert "disabled" in message.lower()
    assert "SSO Token" in message


def test_cmd_register_403_guides_to_token_login(mock_shell):
    """Test cmd_register shows SSO token guidance when server returns 403"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.register.return_value = {
        "status_code": 403,
        "status": "fail",
        "message": "Self-registration is disabled.",
    }

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_register("new@example.com password123")

    error_calls = [str(c) for c in mock_shell.perror.call_args_list]
    output_calls = [str(c) for c in mock_shell.poutput.call_args_list]
    all_output = " ".join(error_calls + output_calls)
    assert "disabled" in all_output.lower()
    assert "token-login" in all_output


def test_cmd_token_login_success(mock_shell):
    """Test interactive token-login command with valid token"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.current_server = "test_server"
    mock_shell.connection._detect_role_from_api = MagicMock(return_value="user")
    mock_shell.config.get_server_url.return_value = "https://test.example.com"
    mock_shell.config.get_server_verify.return_value = True

    mock_api = MagicMock()
    mock_api.get_version.return_value = {"version": "2.2.6"}

    user_cmd = UserCommands(mock_shell)

    with patch("builtins.input", return_value="bob@example.com"):
        with patch("getpass.getpass", return_value="qat_valid_token_123"):
            with patch("quads_lib.QuadsApi", return_value=mock_api):
                user_cmd.cmd_token_login("")

    mock_shell.config.update_server_api_token.assert_called_once_with(
        "test_server", "bob@example.com", "qat_valid_token_123"
    )
    mock_shell.poutput.assert_any_call("OK: Token saved to configuration")


def test_cmd_token_login_empty_email(mock_shell):
    """Test token-login rejects empty email"""
    mock_shell.connection.is_connected = True

    user_cmd = UserCommands(mock_shell)

    with patch("builtins.input", return_value=""):
        user_cmd.cmd_token_login("")

    mock_shell.perror.assert_called_with("Email is required")


def test_cmd_token_login_empty_token(mock_shell):
    """Test token-login rejects empty token"""
    mock_shell.connection.is_connected = True

    user_cmd = UserCommands(mock_shell)

    with patch("builtins.input", return_value="bob@example.com"):
        with patch("getpass.getpass", return_value=""):
            user_cmd.cmd_token_login("")

    mock_shell.perror.assert_called_with("Token is required")


def test_cmd_token_login_not_connected(mock_shell):
    """Test token-login when not connected"""
    mock_shell.connection.is_connected = False

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_token_login("")

    mock_shell.perror.assert_called()


def test_cmd_login_already_authenticated_via_token(mock_shell):
    """Test login command when already authenticated via qat_ token"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = True
    mock_shell.connection._token = "qat_existing_token"
    mock_shell.connection.username = "bob@example.com"

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_login("")

    output = str(mock_shell.poutput.call_args_list)
    assert "Already authenticated via SSO token" in output


def test_cmd_login_no_credentials_suggests_token_login(mock_shell):
    """Test login with no credentials suggests token-login"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = False
    mock_shell.connection._token = None
    mock_shell.connection.api.username = ""
    mock_shell.connection.api.password = ""

    user_cmd = UserCommands(mock_shell)
    user_cmd.cmd_login("")

    error_output = str(mock_shell.perror.call_args_list)
    assert "No credentials" in error_output
    output = str(mock_shell.poutput.call_args_list)
    assert "token-login" in output
