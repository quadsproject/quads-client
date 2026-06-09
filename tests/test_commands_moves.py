import pytest
from unittest.mock import MagicMock
from quads_client.commands.moves import MoveCommands
from quads_client.progress import (
    ProgressTracker,
    format_progress_str,
    stage_of,
    TOTAL_STAGES,
)


@pytest.fixture
def move_commands(mock_shell):
    mock_shell.rich_console = MagicMock()
    return MoveCommands(mock_shell)


def test_move_status_not_connected(move_commands, mock_shell):
    mock_shell.connection.is_connected = False

    move_commands.cmd_move_status("")

    mock_shell.perror.assert_called_once_with("Not connected to any server")


def test_move_status_not_authenticated(move_commands, mock_shell):
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = False

    move_commands.cmd_move_status("")

    mock_shell.perror.assert_called_once_with("Not authenticated. Use 'login' command first.")


def test_move_status_all_no_moves(move_commands, mock_shell):
    mock_shell.connection.api.get_all_move_status.return_value = []

    move_commands.cmd_move_status("")

    mock_shell.rich_console.print_info.assert_called_once_with("No active moves")


def test_move_status_all_with_moves(move_commands, mock_shell):
    mock_shell.connection.api.get_all_move_status.return_value = [
        {
            "host": "host1.example.com",
            "source_cloud": "cloud01",
            "target_cloud": "cloud02",
            "status": "provisioning",
            "message": "Provisioner ready",
        },
        {
            "host": "host2.example.com",
            "source_cloud": "cloud01",
            "target_cloud": "cloud03",
            "status": "failed",
            "message": "",
        },
    ]

    move_commands.cmd_move_status("")

    mock_shell.rich_console.print_table.assert_called_once()
    call_args = mock_shell.rich_console.print_table.call_args
    headers = call_args[0][0]
    rows = call_args[0][1]
    assert headers == ["Host", "From", "To", "Progress", "Status", "Message"]
    assert len(rows) == 2
    assert rows[0][0] == "host1.example.com"
    assert rows[0][3] == "6/12"
    assert rows[1][3] == "FAILED"


def test_move_status_single_host(move_commands, mock_shell):
    mock_shell.connection.api.get_move_status.return_value = {
        "host": "host1.example.com",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
        "status": "hardware_prep",
        "message": "Hardware prepared",
        "error_message": "",
    }

    move_commands.cmd_move_status("host1.example.com")

    mock_shell.rich_console.print_table.assert_called_once()
    call_args = mock_shell.rich_console.print_table.call_args
    rows = call_args[0][1]
    assert any("host1.example.com" in str(r) for r in rows)


def test_move_status_single_host_not_found(move_commands, mock_shell):
    mock_shell.connection.api.get_move_status.return_value = None

    move_commands.cmd_move_status("nonexistent.example.com")

    mock_shell.rich_console.print_info.assert_called_once_with("No active move for nonexistent.example.com")


def test_move_status_api_error(move_commands, mock_shell):
    mock_shell.connection.api.get_all_move_status.side_effect = Exception("Connection refused")

    move_commands.cmd_move_status("")

    mock_shell.perror.assert_any_call("Connection failed: Connection refused")


def test_move_status_not_found_all(move_commands, mock_shell):
    mock_shell.connection.api.get_all_move_status.side_effect = Exception("Resource not found")

    move_commands.cmd_move_status("")

    mock_shell.rich_console.print_info.assert_called_once_with("Move tracking is not available on this server")


def test_move_status_not_found_single(move_commands, mock_shell):
    mock_shell.connection.api.get_move_status.side_effect = Exception("404 Resource not found")

    move_commands.cmd_move_status("host1.example.com")

    mock_shell.rich_console.print_info.assert_called_once_with("Move tracking is not available on this server")


class TestProgressTracker:
    def test_get_move_status(self):
        api = MagicMock()
        api.get_move_status.return_value = {"status": "provisioning", "host": "host1"}
        tracker = ProgressTracker(api)

        result = tracker.get_move_status("host1")

        assert result["status"] == "provisioning"
        api.get_move_status.assert_called_once_with("host1")

    def test_get_move_status_not_found(self):
        api = MagicMock()
        api.get_move_status.side_effect = Exception("404")
        tracker = ProgressTracker(api)

        result = tracker.get_move_status("host1")

        assert result is None

    def test_get_all_active_moves(self):
        api = MagicMock()
        api.get_all_move_status.return_value = [{"host": "host1"}, {"host": "host2"}]
        tracker = ProgressTracker(api)

        result = tracker.get_all_active_moves()

        assert len(result) == 2

    def test_get_all_active_moves_error(self):
        api = MagicMock()
        api.get_all_move_status.side_effect = Exception("error")
        tracker = ProgressTracker(api)

        result = tracker.get_all_active_moves()

        assert result == []

    def test_format_stage_progress_pending(self):
        api = MagicMock()
        api.get_move_status.return_value = {"status": "pending"}
        tracker = ProgressTracker(api)

        result = tracker.format_stage_progress("host1")

        assert result == "1/12"

    def test_format_stage_progress_failed(self):
        api = MagicMock()
        api.get_move_status.return_value = {"status": "failed"}
        tracker = ProgressTracker(api)

        result = tracker.format_stage_progress("host1")

        assert "FAILED" in result

    def test_format_stage_progress_completed(self):
        api = MagicMock()
        api.get_move_status.return_value = {"status": "completed"}
        tracker = ProgressTracker(api)

        result = tracker.format_stage_progress("host1")

        assert result == "12/12"

    def test_format_stage_progress_no_data(self):
        api = MagicMock()
        api.get_move_status.side_effect = Exception("404")
        tracker = ProgressTracker(api)

        result = tracker.format_stage_progress("host1")

        assert result == ""


class TestFormatProgressStr:
    def test_pending(self):
        assert format_progress_str("pending") == "1/12"

    def test_provisioning(self):
        assert format_progress_str("provisioning") == "6/12"

    def test_failed(self):
        assert format_progress_str("failed") == "FAILED"

    def test_completed(self):
        assert format_progress_str("completed") == "12/12"

    def test_released(self):
        assert format_progress_str("released") == "12/12"


class TestStageOf:
    def test_pending(self):
        assert stage_of("pending") == 1

    def test_provisioning(self):
        assert stage_of("provisioning") == 6

    def test_released(self):
        assert stage_of("released") == 12

    def test_completed(self):
        assert stage_of("completed") == TOTAL_STAGES

    def test_failed(self):
        assert stage_of("failed") == TOTAL_STAGES

    def test_unknown(self):
        assert stage_of("bogus") == 0
