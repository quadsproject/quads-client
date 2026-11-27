import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from quads_client.commands.track import TrackCommands, _failed_retrying, _scheduled_move_hosts


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
    ] + [[] for _ in range(6)]
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
    completed = {"host": "host1", "status": "failed", "source_cloud": "cloud01", "target_cloud": "cloud03"}
    mock_shell.connection.api.get_move_status.side_effect = [
        initial,
        completed,
    ]
    mock_shell.connection.api.get_moves.return_value = []
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


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_no_active_moves_with_pending_transitions(mock_time, mock_live_cls, mock_shell):
    """Pending moves poll at 10s until active moves appear, then transition to live tracking"""
    pending = [{"host": "host1.example.com", "current": "cloud01", "new": "cloud02"}]
    active = [
        {
            "host": "host1.example.com",
            "source_cloud": "cloud01",
            "target_cloud": "cloud02",
            "status": "pending",
        }
    ]
    mock_shell.connection.api.get_all_move_status.side_effect = [
        [],
        active,
        active,
    ] + [[] for _ in range(6)]
    mock_shell.connection.api.get_moves.return_value = pending
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    assert mock_live_cls.call_count == 2


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_pending_ctrl_c_exits(mock_time, mock_live_cls, mock_shell):
    """Ctrl+C during pending polling exits cleanly"""
    pending = [{"host": "host1.example.com", "current": "cloud01", "new": "cloud02"}]
    mock_shell.connection.api.get_all_move_status.return_value = []
    mock_shell.connection.api.get_moves.return_value = pending
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_time.sleep.side_effect = KeyboardInterrupt

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    mock_shell.rich_console.console.print.assert_called()


def test_track_no_active_move_single(mock_shell):
    mock_shell.connection.api.get_move_status.return_value = None
    mock_shell.connection.api.get_moves.return_value = []

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1")

    mock_shell.rich_console.print_info.assert_called_once_with("No active or scheduled moves for host1")


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_single_pending_transitions(mock_time, mock_live_cls, mock_shell):
    """Single-host pending polling transitions to live tracking when move starts"""
    pending = [{"host": "host1", "current": "cloud01", "new": "cloud02"}]
    active = {
        "host": "host1",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
        "status": "failed",
    }
    mock_shell.connection.api.get_move_status.side_effect = [
        None,
        active,
        active,
    ]
    mock_shell.connection.api.get_moves.return_value = pending
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1")

    assert mock_live_cls.call_count == 2


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_pending_all_disappears(mock_time, mock_live_cls, mock_shell):
    """Pending moves disappear after one refresh cycle"""
    pending = [{"host": "host1.example.com", "current": "cloud01", "new": "cloud02"}]
    mock_shell.connection.api.get_all_move_status.return_value = []
    mock_shell.connection.api.get_moves.side_effect = [pending, pending, []]
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    mock_live_cls.assert_called_once()
    mock_live_instance.update.assert_called_once()


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_pending_single_disappears(mock_time, mock_live_cls, mock_shell):
    """Single-host pending move disappears after one refresh cycle"""
    pending = [{"host": "host1", "current": "cloud01", "new": "cloud02"}]
    mock_shell.connection.api.get_move_status.side_effect = [None, None, None]
    mock_shell.connection.api.get_moves.side_effect = [pending, pending, []]
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1")

    mock_live_cls.assert_called_once()
    mock_live_instance.update.assert_called_once()


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_pending_single_ctrl_c(mock_time, mock_live_cls, mock_shell):
    """Ctrl+C during single-host pending polling exits cleanly"""
    pending = [{"host": "host1", "current": "cloud01", "new": "cloud02"}]
    mock_shell.connection.api.get_move_status.return_value = None
    mock_shell.connection.api.get_moves.return_value = pending
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_time.sleep.side_effect = KeyboardInterrupt

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1")

    mock_shell.rich_console.console.print.assert_called()


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


def test_build_pending_table(mock_shell):
    cmd = TrackCommands(mock_shell)
    pending = [
        {"host": "host1.example.com", "current": "cloud01", "new": "cloud02"},
        {"host": "host2.example.com", "current": "cloud01", "new": "cloud03"},
    ]
    table = cmd._build_pending_table(pending)
    assert table.title == "Scheduled Moves (awaiting next move cycle)"
    assert "10s" in table.caption
    assert table.row_count == 2


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_all_completes_on_disappear(mock_time, mock_live_cls, mock_shell):
    """When all moves disappear from API after grace window, show completed 12/12"""
    move_data = {
        "host": "host1.example.com",
        "status": "post_install",
        "source_cloud": "cloud02",
        "target_cloud": "cloud03",
        "message": "Records updated",
    }
    mock_shell.connection.api.get_all_move_status.side_effect = [
        [move_data],
        [move_data],
    ] + [[] for _ in range(6)]
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    calls = mock_live_instance.update.call_args_list
    assert len(calls) >= 2
    mock_shell.rich_console.console.print.assert_called_once()
    msg = mock_shell.rich_console.console.print.call_args[0][0]
    assert "completed" in msg.lower()
    assert "1 host" in msg


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_single_completes_on_disappear(mock_time, mock_live_cls, mock_shell):
    """When single host move disappears (APINotFound) after grace, show completed"""
    initial = {
        "host": "host1.example.com",
        "status": "post_install",
        "source_cloud": "cloud02",
        "target_cloud": "cloud03",
        "message": "Records updated",
    }
    mock_shell.connection.api.get_move_status.side_effect = [initial, initial] + [
        Exception("No active move for host1.example.com") for _ in range(6)
    ]
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1.example.com")

    calls = mock_live_instance.update.call_args_list
    assert len(calls) >= 2
    msg = mock_shell.rich_console.console.print.call_args[0][0]
    assert "completed" in msg.lower()


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_single_api_error_during_poll(mock_time, mock_live_cls, mock_shell):
    """Generic exception during poll handled via grace window then completed"""
    initial = {
        "host": "host1.example.com",
        "status": "provisioning",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
        "message": "Provisioner ready",
    }
    mock_shell.connection.api.get_move_status.side_effect = [initial] + [
        ConnectionError("Connection refused") for _ in range(6)
    ]
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1.example.com")

    msg = mock_shell.rich_console.console.print.call_args[0][0]
    assert "completed" in msg.lower()


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_all_terminal_status_exit(mock_time, mock_live_cls, mock_shell):
    """All moves reaching failed status in API response trigger clean exit"""
    active = {
        "host": "host1.example.com",
        "status": "provisioning",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
    }
    done = {
        "host": "host1.example.com",
        "status": "failed",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
    }
    mock_shell.connection.api.get_all_move_status.side_effect = [
        [active],
        [done],
    ]
    mock_shell.connection.api.get_moves.return_value = []
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    msg = mock_shell.rich_console.console.print.call_args[0][0]
    assert "failed" in msg.lower()


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_all_transient_disappear_recovers(mock_time, mock_live_cls, mock_shell):
    """API returns empty for a few polls then data comes back -- no premature exit"""
    move_data = {
        "host": "host1.example.com",
        "status": "provisioning",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
        "message": "Provisioner ready",
    }
    done = {
        "host": "host1.example.com",
        "status": "failed",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
        "message": "Failed",
    }
    mock_shell.connection.api.get_all_move_status.side_effect = [
        [move_data],
        [],
        [],
        [move_data],
        [done],
    ]
    mock_shell.connection.api.get_moves.return_value = []
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    msg = mock_shell.rich_console.console.print.call_args[0][0]
    assert "failed" in msg.lower()
    assert mock_shell.connection.api.get_all_move_status.call_count == 5


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_single_transient_disappear_recovers(mock_time, mock_live_cls, mock_shell):
    """APINotFound for a few polls then data returns -- tracking resumes"""
    initial = {
        "host": "host1.example.com",
        "status": "provisioning",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
        "message": "Provisioner ready",
    }
    done = {
        "host": "host1.example.com",
        "status": "failed",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
        "message": "Failed",
    }
    mock_shell.connection.api.get_move_status.side_effect = [
        initial,
        Exception("No active move"),
        Exception("No active move"),
        initial,
        done,
    ]
    mock_shell.connection.api.get_moves.return_value = []
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1.example.com")

    msg = mock_shell.rich_console.console.print.call_args[0][0]
    assert "failed" in msg.lower()
    assert mock_shell.connection.api.get_move_status.call_count == 5


def test_failed_retrying():
    failed = {"status": "failed", "host": "host1.example.com"}
    fresh = datetime.now()
    expired = datetime.now() - timedelta(hours=3)
    assert _failed_retrying(failed, {"host1.example.com", "host2.example.com"})
    assert not _failed_retrying(failed, {"host2.example.com"})
    assert _failed_retrying(failed, None)
    assert _failed_retrying(failed, None, fresh)
    assert _failed_retrying(failed, {"host1.example.com"}, fresh)
    assert not _failed_retrying(failed, {"host1.example.com"}, expired)
    assert not _failed_retrying({"status": "pending", "host": "host1.example.com"}, {"host1.example.com"})


def test_scheduled_move_hosts(mock_shell):
    api = mock_shell.connection.api
    api.get_moves.return_value = [
        {"host": "host1.example.com", "new": "cloud02"},
        {"host": "host2.example.com", "new": "cloud03"},
    ]
    assert _scheduled_move_hosts(api) == {"host1.example.com", "host2.example.com"}
    assert _scheduled_move_hosts(api, cloud="cloud02") == {"host1.example.com"}
    api.get_moves.side_effect = Exception("connection refused")
    assert _scheduled_move_hosts(api) is None


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_single_failed_scheduled_keeps_polling_then_completes(mock_time, mock_live_cls, mock_shell):
    """A failed move still listed by /moves stays in progress; completes when the record disappears"""
    failed = {
        "host": "host1.example.com",
        "status": "failed",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
    }
    mock_shell.connection.api.get_move_status.side_effect = [failed, failed, failed] + [
        Exception("No active move") for _ in range(6)
    ]
    mock_shell.connection.api.get_moves.side_effect = [
        [{"host": "host1.example.com"}],
        [{"host": "host1.example.com"}],
        [{"host": "host1.example.com"}],
    ]
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1.example.com")

    assert mock_shell.connection.api.get_move_status.call_count == 9
    assert mock_shell.connection.api.get_moves.call_count == 3
    assert mock_live_instance.update.call_count >= 3
    msg = mock_shell.rich_console.console.print.call_args[0][0]
    assert "completed" in msg.lower()


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_single_failed_unscheduled_exits(mock_time, mock_live_cls, mock_shell):
    """A failed move the server no longer lists for a move is terminal"""
    initial = {"host": "host1.example.com", "status": "hardware_prep"}
    failed = {"host": "host1.example.com", "status": "failed"}
    mock_shell.connection.api.get_move_status.side_effect = [initial, failed]
    mock_shell.connection.api.get_moves.return_value = []
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("host1.example.com")

    assert mock_shell.connection.api.get_move_status.call_count == 2
    msg = mock_shell.rich_console.console.print.call_args[0][0]
    assert "failed" in msg.lower()


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_all_failed_scheduled_keeps_polling_then_completes(mock_time, mock_live_cls, mock_shell):
    """All-failed rows still listed by /moves keep the live view polling until they disappear"""
    failed = {
        "host": "host1.example.com",
        "status": "failed",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
    }
    mock_shell.connection.api.get_all_move_status.side_effect = [[failed], [failed], [failed]] + [[] for _ in range(6)]
    mock_shell.connection.api.get_moves.side_effect = [
        [{"host": "host1.example.com"}],
        [{"host": "host1.example.com"}],
        [{"host": "host1.example.com"}],
    ]
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    assert mock_shell.connection.api.get_all_move_status.call_count == 9
    assert mock_shell.connection.api.get_moves.call_count == 3
    assert mock_live_instance.update.call_count >= 3
    msg = mock_shell.rich_console.console.print.call_args[0][0]
    assert "completed" in msg.lower()


@patch("quads_client.commands.track.Live")
@patch("quads_client.commands.track.time")
def test_track_all_failed_unscheduled_exits(mock_time, mock_live_cls, mock_shell):
    """All-failed rows the server no longer lists for a move exit as terminal"""
    failed = {
        "host": "host1.example.com",
        "status": "failed",
        "source_cloud": "cloud01",
        "target_cloud": "cloud02",
    }
    mock_shell.connection.api.get_all_move_status.side_effect = [[failed], [failed]]
    mock_shell.connection.api.get_moves.return_value = []
    mock_live_instance = MagicMock()
    mock_live_cls.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_cls.return_value.__exit__ = MagicMock(return_value=False)

    cmd = TrackCommands(mock_shell)
    cmd.cmd_track("")

    assert mock_shell.connection.api.get_all_move_status.call_count == 2
    msg = mock_shell.rich_console.console.print.call_args[0][0]
    assert "failed" in msg.lower()


def test_build_all_table_retrying_shows_error(mock_shell):
    cmd = TrackCommands(mock_shell)
    moves = [
        {
            "host": "host1.example.com",
            "source_cloud": "cloud01",
            "target_cloud": "cloud02",
            "status": "failed",
            "message": "IPMI credentials configured and verified",
            "error_message": "Failed at hardware_prep",
        },
        {
            "host": "host2.example.com",
            "source_cloud": "cloud01",
            "target_cloud": "cloud02",
            "status": "failed",
            "message": "done",
            "error_message": "Failed at power_on",
        },
    ]
    table = cmd._build_all_table(moves, {"host1.example.com"})
    assert list(table.columns[3].cells) == ["Retrying", "FAILED"]
    assert table.rows[0].style == "yellow"
    assert table.rows[1].style == "red"
    assert list(table.columns[6].cells) == ["Failed at hardware_prep", "Failed at power_on"]


def test_build_all_table_retry_window_expired(mock_shell):
    cmd = TrackCommands(mock_shell)
    moves = [
        {
            "host": "host1.example.com",
            "source_cloud": "cloud01",
            "target_cloud": "cloud02",
            "status": "failed",
            "message": "IPMI credentials configured and verified",
            "error_message": "Failed at hardware_prep",
        }
    ]
    expired = datetime.now() - timedelta(hours=3)
    table = cmd._build_all_table(moves, {"host1.example.com"}, {"host1.example.com": expired})
    assert list(table.columns[3].cells) == ["FAILED"]
    assert table.rows[0].style == "red"


def test_build_single_table_retrying(mock_shell):
    cmd = TrackCommands(mock_shell)
    data = {
        "host": "host1.example.com",
        "source_cloud": "cloud01",
        "target_cloud": "cloud03",
        "status": "failed",
        "message": "IPMI credentials configured and verified",
        "error_message": "Failed at hardware_prep",
    }
    table = cmd._build_single_table(data, {"host1.example.com"})
    values = list(table.columns[1].cells)
    assert "[yellow]Retrying[/yellow]" in values
    assert any("Failed at hardware_prep" in v for v in values)


def test_build_single_table_unknown_scheduled_retries(mock_shell):
    cmd = TrackCommands(mock_shell)
    data = {"host": "host1.example.com", "status": "failed"}
    table = cmd._build_single_table(data)
    assert "[yellow]Retrying[/yellow]" in list(table.columns[1].cells)
