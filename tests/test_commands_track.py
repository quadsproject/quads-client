import pytest
from unittest.mock import MagicMock, patch

from quads_client.commands.track import TrackCommands


@pytest.fixture(autouse=True)
def _ensure_rich_console(mock_shell):
    mock_shell.rich_console = MagicMock()


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_all_with_moves(mock_time, mock_live_cls, mock_shell):
    move_data = {"host": "host1", "status": "provisioning", "source_cloud": "cloud01", "target_cloud": "cloud02"}
    mock_shell.connection.api.get_all_move_status.side_effect = [
        [move_data],
        [move_data],
        [],
    ]
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    mock_live_cls.assert_called_once()
    mock_live_instance.update.assert_called()
    mock_shell.rich_console.console.print.assert_called()


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_single_host(mock_time, mock_live_cls, mock_shell):
    initial = {"host": "host1", "status": "hardware_prep", "source_cloud": "cloud01", "target_cloud": "cloud03"}
    completed = {"host": "host1", "status": "completed", "source_cloud": "cloud01", "target_cloud": "cloud03"}
    mock_shell.connection.api.get_move_status.side_effect = [
        initial,
        completed,
    ]
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1")

    mock_live_cls.assert_called_once()
    mock_live_instance.update.assert_called()


def test_track_no_active_moves_no_pending(mock_shell):
    mock_shell.connection.api.get_all_move_status.return_value = []
    mock_shell.connection.api.get_moves.return_value = []

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    mock_shell.rich_console.print_info.assert_called_once_with("No active or scheduled moves")


def test_track_no_active_moves_with_pending(mock_shell):
    mock_shell.connection.api.get_all_move_status.return_value = []
    mock_shell.connection.api.get_moves.return_value = [
        {"host": "host1.example.com", "current": "cloud01", "new": "cloud02"},
    ]

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    mock_shell.rich_console.console.print.assert_called_once()
    table = mock_shell.rich_console.console.print.call_args[0][0]
    assert table.title == "Scheduled Moves (awaiting next move cycle)"


def test_track_no_active_move_single(mock_shell):
    mock_shell.connection.api.get_move_status.return_value = None
    mock_shell.connection.api.get_moves.return_value = []

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1")

    mock_shell.rich_console.print_info.assert_called_once_with("No active or scheduled moves for host1")


def test_track_no_active_single_with_pending(mock_shell):
    mock_shell.connection.api.get_move_status.return_value = None
    mock_shell.connection.api.get_moves.return_value = [
        {"host": "host1", "current": "cloud01", "new": "cloud02"},
    ]

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1")

    mock_shell.rich_console.console.print.assert_called_once()


def test_track_cloud_filter(mock_shell):
    mock_shell.connection.api.get_all_move_status.return_value = []
    mock_shell.connection.api.get_moves.return_value = []

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("cloud03")

    mock_shell.connection.api.get_all_move_status.assert_called_with(cloud="cloud03")
    mock_shell.rich_console.print_info.assert_called_once_with("No active or scheduled moves for cloud03")


def test_track_pending_api_error(mock_shell):
    mock_shell.connection.api.get_all_move_status.return_value = []
    mock_shell.connection.api.get_moves.side_effect = Exception("Connection refused")

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    mock_shell.rich_console.print_info.assert_called_once_with("No active or scheduled moves")


def test_track_not_authenticated(mock_shell):
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_authenticated = False

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    mock_shell.perror.assert_called_once_with("Not authenticated. Use 'login' command first.")


def test_track_api_error(mock_shell):
    mock_shell.connection.api.get_all_move_status.side_effect = Exception("Connection refused")

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    mock_shell.perror.assert_any_call("Connection failed: Connection refused")


def test_track_not_found(mock_shell):
    mock_shell.connection.api.get_all_move_status.side_effect = Exception("404 Not Found")

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    mock_shell.rich_console.print_info.assert_called_once_with("Move tracking is not available on this server")


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_keyboard_interrupt(mock_time, mock_live_cls, mock_shell):
    mock_shell.connection.api.get_all_move_status.return_value = [
        {"host": "host1", "status": "pending", "source_cloud": "cloud01", "target_cloud": "cloud02"},
    ]
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_time.sleep.side_effect = KeyboardInterrupt

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    mock_shell.rich_console.console.print.assert_called()


def test_build_all_table(mock_shell):
    cmd = TrackCommands(mock_shell)
    moves = [
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
        {
            "host": "host3.example.com",
            "source_cloud": "cloud01",
            "target_cloud": "cloud02",
            "status": "completed",
            "message": "Done",
        },
    ]
    table = cmd._build_all_table(moves)
    assert table.title == "Live Move Progress"
    assert table.row_count == 3


def test_build_single_table(mock_shell):
    cmd = TrackCommands(mock_shell)
    data = {
        "host": "host1.example.com",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
        "status": "hardware_prep",
        "message": "Hardware prepared",
        "error_message": "",
        "started_at": "2026-06-09T10:00:00",
    }
    table = cmd._build_single_table(data)
    assert "host1.example.com" in table.title
    assert table.row_count >= 5


def test_build_single_table_with_error(mock_shell):
    cmd = TrackCommands(mock_shell)
    data = {
        "host": "host1.example.com",
        "source_cloud": "cloud01",
        "target_cloud": "cloud03",
        "status": "failed",
        "message": "",
        "error_message": "Failed at hardware_prep",
        "started_at": None,
    }
    table = cmd._build_single_table(data)
    assert table.row_count >= 6
