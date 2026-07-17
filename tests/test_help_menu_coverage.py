import pytest
from unittest.mock import MagicMock, patch
from quads_client.shell import QuadsClientShell
from quads_client.commands.host import HostCommands
from quads_client.commands.cloud import CloudCommands
from quads_client.commands.session import SessionCommands


def _make_shell():
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
    return shell


def _make_connected_shell(is_admin=False):
    shell = _make_shell()
    mock_conn = MagicMock()
    mock_conn.is_authenticated = True
    mock_conn.is_admin = is_admin
    mock_conn.api.get_clouds.return_value = [
        {"name": "cloud01"},
        {"name": "cloud02"},
    ]
    mock_conn.api.get_hosts.return_value = [
        {"name": "host01"},
        {"name": "host02"},
    ]
    mock_conn.api.filter_hosts.return_value = [
        {"name": "host01"},
        {"name": "host02"},
    ]
    mock_conn.api.get_os_list.return_value = [
        {"Id": 1, "Title": "RHEL 9.4", "Release Name": "Plow", "Family": "RHEL"},
        {"Id": 2, "Title": "RHEL 8.10", "Release Name": "Ootpa", "Family": "RHEL"},
    ]
    mock_conn.api.get_free_vlans.return_value = [
        {"vlan_id": 1100},
        {"vlan_id": 1200},
    ]
    shell.session_manager.active_connection = mock_conn
    return shell


# --- help_schedule ---


class TestHelpSchedule:
    def test_admin_help(self):
        shell = _make_connected_shell(is_admin=True)
        shell.poutput = MagicMock()
        shell.help_schedule()
        calls = [str(c) for c in shell.poutput.call_args_list]
        assert any("admin mode" in c.lower() for c in calls)
        assert any("cloud-owner" in c for c in calls)

    def test_ssm_help(self):
        shell = _make_connected_shell(is_admin=False)
        shell.poutput = MagicMock()
        shell.help_schedule()
        calls = [str(c) for c in shell.poutput.call_args_list]
        assert any("ssm mode" in c.lower() for c in calls)
        assert any("model" in c for c in calls)

    def test_no_connection_shows_ssm(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        shell.poutput = MagicMock()
        shell.help_schedule()
        calls = [str(c) for c in shell.poutput.call_args_list]
        assert any("ssm mode" in c.lower() for c in calls)


# --- do_schedule help flags ---


class TestDoScheduleHelp:
    @pytest.mark.parametrize("flag", ["?", "-h", "--help"])
    def test_help_flags_show_help(self, flag):
        shell = _make_connected_shell(is_admin=False)
        shell.poutput = MagicMock()
        shell.do_schedule(flag)
        assert shell.poutput.call_count >= 1

    def test_normal_args_route_to_ssm(self):
        shell = _make_connected_shell(is_admin=False)
        shell.user_commands = MagicMock()
        shell.do_schedule("3 description test")
        shell.user_commands.cmd_schedule.assert_called_once()

    def test_admin_args_route_to_admin(self):
        shell = _make_connected_shell(is_admin=True)
        shell.schedule_commands = MagicMock()
        shell.do_schedule("cloud02 host01 2026-08-01 2026-08-15")
        shell.schedule_commands.cmd_schedule_admin.assert_called_once()


# --- complete_schedule ---


class TestCompleteSchedule:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_schedule("", "schedule ", 9, 9) == []

    def test_not_authenticated(self):
        shell = _make_connected_shell()
        shell.connection.is_authenticated = False
        assert shell.complete_schedule("", "schedule ", 9, 9) == []

    def test_admin_first_arg_clouds(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule("", "schedule ", 9, 9)
        assert "cloud01" in result
        assert "cloud02" in result

    def test_admin_first_arg_filtered(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule("cloud0", "schedule cloud0", 9, 15)
        assert "cloud01" in result
        assert "cloud02" in result

    def test_admin_position2_hosts_and_host_list(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule("", "schedule cloud02 ", 18, 18)
        assert "host01" in result
        assert "host02" in result
        assert "host-list" in result
        assert "cloud01" not in result
        assert "description" not in result

    def test_admin_position2_filtered(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule("host", "schedule cloud02 host", 18, 22)
        assert "host01" in result
        assert "host02" in result
        assert "host-list" in result

    def test_admin_no_cloud_at_position2(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule("cloud", "schedule cloud02 cloud", 18, 23)
        assert result == []

    def test_admin_date_positions_empty(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule("", "schedule cloud02 host01 ", 24, 24)
        assert result == []

    def test_admin_date_position4_empty(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule("", "schedule cloud02 host01 2026-08-01 ", 35, 35)
        assert result == []

    def test_admin_options_keywords_only(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule(
            "",
            "schedule cloud02 host01 2026-08-01 2026-08-15 ",
            47,
            47,
        )
        assert "description" in result
        assert "cloud-owner" in result
        assert "nowipe" in result
        assert "host01" not in result

    def test_admin_options_filtered(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule(
            "cl",
            "schedule cloud02 host01 2026-08-01 2026-08-15 cl",
            47,
            49,
        )
        assert "cloud-owner" in result
        assert "cloud-ticket" in result
        assert "cc-users" not in result
        assert "description" not in result

    def test_admin_value_keyword_suppresses_completions(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule(
            "",
            "schedule cloud02 host01 2026-08-01 2026-08-15 cloud-owner ",
            59,
            59,
        )
        assert result == []

    def test_admin_host_list_date_positions(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule("", "schedule cloud02 host-list ~/hosts.txt ", 40, 40)
        assert result == []

    def test_admin_host_list_options(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule(
            "",
            "schedule cloud02 host-list ~/hosts.txt 2026-08-01 2026-08-15 ",
            62,
            62,
        )
        assert "description" in result
        assert "host01" not in result

    def test_admin_os_value_completion(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule(
            "",
            "schedule cloud02 host01 2026-08-01 2026-08-15 os ",
            50,
            50,
        )
        assert "RHEL 9.4" in result
        assert "RHEL 8.10" in result

    def test_admin_vlan_value_completion(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_schedule(
            "",
            "schedule cloud02 host01 2026-08-01 2026-08-15 vlan ",
            51,
            51,
        )
        assert "1100" in result
        assert "1200" in result

    def test_admin_api_exception_fallback(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.get_clouds.side_effect = Exception("fail")
        result = shell.complete_schedule("", "schedule ", 9, 9)
        assert "description" in result

    def test_ssm_first_arg_hosts_and_counts(self):
        shell = _make_connected_shell(is_admin=False)
        result = shell.complete_schedule("", "schedule ", 9, 9)
        assert "host01" in result
        assert "1" in result
        assert "host-list" in result

    def test_ssm_first_arg_filtered(self):
        shell = _make_connected_shell(is_admin=False)
        result = shell.complete_schedule("host", "schedule host", 9, 13)
        assert "host01" in result
        assert "1" not in result

    def test_ssm_later_args_keywords(self):
        shell = _make_connected_shell(is_admin=False)
        result = shell.complete_schedule("", "schedule 3 description test ", 29, 29)
        assert "nowipe" in result
        assert "model" in result
        assert "vlan" in result

    def test_ssm_later_args_filtered(self):
        shell = _make_connected_shell(is_admin=False)
        result = shell.complete_schedule("disk", "schedule 3 description test disk", 33, 37)
        assert "disk-type" in result
        assert "disk-size" in result
        assert "model" not in result

    def test_ssm_value_keyword_suppresses_completions(self):
        shell = _make_connected_shell(is_admin=False)
        result = shell.complete_schedule("", "schedule 3 description ", 22, 22)
        assert result == []

    def test_ssm_os_value_completion(self):
        shell = _make_connected_shell(is_admin=False)
        result = shell.complete_schedule("", "schedule 3 description test os ", 31, 31)
        assert "RHEL 9.4" in result
        assert "RHEL 8.10" in result

    def test_ssm_vlan_value_completion(self):
        shell = _make_connected_shell(is_admin=False)
        result = shell.complete_schedule("", "schedule 3 description test vlan ", 33, 33)
        assert "1100" in result
        assert "1200" in result

    def test_ssm_api_exception_fallback(self):
        shell = _make_connected_shell(is_admin=False)
        shell.connection.api.filter_hosts.side_effect = Exception("fail")
        result = shell.complete_schedule("", "schedule ", 9, 9)
        assert "description" in result


# --- complete_cloud_only ---


class TestCompleteCloudOnly:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_cloud_only("", "cloud_only ", 11, 11) == []

    def test_not_authenticated(self):
        shell = _make_connected_shell()
        shell.connection.is_authenticated = False
        assert shell.complete_cloud_only("", "cloud_only ", 11, 11) == []

    def test_all_clouds(self):
        shell = _make_connected_shell()
        result = shell.complete_cloud_only("", "cloud_only ", 11, 11)
        assert "cloud01" in result
        assert "cloud02" in result

    def test_filtered(self):
        shell = _make_connected_shell()
        result = shell.complete_cloud_only("cloud01", "cloud_only cloud01", 11, 18)
        assert result == ["cloud01"]

    def test_api_exception(self):
        shell = _make_connected_shell()
        shell.connection.api.get_clouds.side_effect = Exception("fail")
        assert shell.complete_cloud_only("", "cloud_only ", 11, 11) == []


# --- complete_move_status ---


class TestCompleteMoveStatus:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_move_status("", "move_status ", 12, 12) == []

    def test_not_authenticated(self):
        shell = _make_connected_shell()
        shell.connection.is_authenticated = False
        assert shell.complete_move_status("", "move_status ", 12, 12) == []

    def test_all_hosts(self):
        shell = _make_connected_shell()
        result = shell.complete_move_status("", "move_status ", 12, 12)
        assert "host01" in result
        assert "host02" in result

    def test_filtered(self):
        shell = _make_connected_shell()
        result = shell.complete_move_status("host01", "move_status host01", 12, 18)
        assert result == ["host01"]

    def test_api_exception(self):
        shell = _make_connected_shell()
        shell.connection.api.get_hosts.side_effect = Exception("fail")
        assert shell.complete_move_status("", "move_status ", 12, 12) == []


# --- complete_track ---


class TestCompleteTrack:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_track("", "track ", 6, 6) == []

    def test_not_authenticated(self):
        shell = _make_connected_shell()
        shell.connection.is_authenticated = False
        assert shell.complete_track("", "track ", 6, 6) == []

    def test_all_hosts_and_clouds(self):
        shell = _make_connected_shell()
        result = shell.complete_track("", "track ", 6, 6)
        assert "host01" in result
        assert "cloud01" in result

    def test_filtered(self):
        shell = _make_connected_shell()
        result = shell.complete_track("cloud", "track cloud", 6, 11)
        assert "cloud01" in result
        assert "cloud02" in result
        assert "host01" not in result

    def test_api_exception(self):
        shell = _make_connected_shell()
        shell.connection.api.get_hosts.side_effect = Exception("fail")
        assert shell.complete_track("", "track ", 6, 6) == []


# --- complete_session_create ---


class TestCompleteSessionCreate:
    def test_with_config(self):
        shell = _make_shell()
        mock_config = MagicMock()
        mock_config.get_all_servers.return_value = {
            "server1": {},
            "server2": {},
        }
        shell.config = mock_config
        result = shell.complete_session_create("", "session_create ", 15, 15)
        assert "server1" in result
        assert "server2" in result

    def test_filtered(self):
        shell = _make_shell()
        mock_config = MagicMock()
        mock_config.get_all_servers.return_value = {
            "server1": {},
            "staging": {},
        }
        shell.config = mock_config
        result = shell.complete_session_create("ser", "session_create ser", 15, 18)
        assert result == ["server1"]

    def test_no_config(self):
        shell = _make_shell()
        shell.config = None
        result = shell.complete_session_create("", "session_create ", 15, 15)
        assert result == []


# --- complete_session_switch ---


class TestCompleteSessionSwitch:
    def test_with_sessions(self):
        shell = _make_shell()
        mock_session = MagicMock()
        mock_session.id = "1"
        shell.session_manager.list_sessions.return_value = [mock_session]
        result = shell.complete_session_switch("", "session_switch ", 15, 15)
        assert "1" in result

    def test_filtered(self):
        shell = _make_shell()
        s1 = MagicMock()
        s1.id = "1"
        s2 = MagicMock()
        s2.id = "2"
        shell.session_manager.list_sessions.return_value = [s1, s2]
        result = shell.complete_session_switch("1", "session_switch 1", 15, 16)
        assert result == ["1"]

    def test_no_session_manager(self):
        shell = _make_shell()
        shell.session_manager = None
        result = shell.complete_session_switch("", "session_switch ", 15, 15)
        assert result == []


# --- complete_session ---


class TestCompleteSession:
    def test_ids_and_labels(self):
        shell = _make_shell()
        mock_session = MagicMock()
        mock_session.id = "1"
        mock_session.label = "dev"
        shell.session_manager.list_sessions.return_value = [mock_session]
        result = shell.complete_session("", "session ", 8, 8)
        assert "1" in result
        assert "dev" in result

    def test_filtered_by_label(self):
        shell = _make_shell()
        s1 = MagicMock()
        s1.id = "1"
        s1.label = "dev"
        s2 = MagicMock()
        s2.id = "2"
        s2.label = "prod"
        shell.session_manager.list_sessions.return_value = [s1, s2]
        result = shell.complete_session("dev", "session dev", 8, 11)
        assert result == ["dev"]

    def test_no_session_manager(self):
        shell = _make_shell()
        shell.session_manager = None
        result = shell.complete_session("", "session ", 8, 8)
        assert result == []


# --- complete_session_close ---


class TestCompleteSessionClose:
    def test_with_sessions(self):
        shell = _make_shell()
        mock_session = MagicMock()
        mock_session.id = "1"
        shell.session_manager.list_sessions.return_value = [mock_session]
        result = shell.complete_session_close("", "session_close ", 14, 14)
        assert "1" in result

    def test_filtered(self):
        shell = _make_shell()
        s1 = MagicMock()
        s1.id = "1"
        s2 = MagicMock()
        s2.id = "2"
        shell.session_manager.list_sessions.return_value = [s1, s2]
        result = shell.complete_session_close("2", "session_close 2", 14, 15)
        assert result == ["2"]

    def test_no_session_manager(self):
        shell = _make_shell()
        shell.session_manager = None
        result = shell.complete_session_close("", "session_close ", 14, 14)
        assert result == []


# --- host command help flags ---


class TestHostHelpFlags:
    @pytest.fixture
    def host_cmd(self, mock_shell):
        mock_shell.connection.is_connected = True
        return HostCommands(mock_shell)

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_mark_broken_help(self, host_cmd, mock_shell, flag):
        host_cmd.cmd_mark_broken(flag)
        mock_shell.perror.assert_called_with("Usage: mark-broken <hostname>")

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_mark_repaired_help(self, host_cmd, mock_shell, flag):
        host_cmd.cmd_mark_repaired(flag)
        mock_shell.perror.assert_called_with("Usage: mark-repaired <hostname>")

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_retire_help(self, host_cmd, mock_shell, flag):
        host_cmd.cmd_retire(flag)
        mock_shell.perror.assert_called_with("Usage: retire <hostname>")

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_unretire_help(self, host_cmd, mock_shell, flag):
        host_cmd.cmd_unretire(flag)
        mock_shell.perror.assert_called_with("Usage: unretire <hostname>")


# --- cloud command help flags ---


class TestCloudHelpFlags:
    @pytest.fixture
    def cloud_cmd(self, mock_shell):
        mock_shell.connection.is_connected = True
        return CloudCommands(mock_shell)

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_cloud_create_help(self, cloud_cmd, mock_shell, flag):
        cloud_cmd.cmd_cloud_create(flag)
        mock_shell.perror.assert_called_with("Usage: cloud-create <name>")

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_cloud_only_help(self, cloud_cmd, mock_shell, flag):
        cloud_cmd.cmd_cloud_only(flag)
        mock_shell.perror.assert_called_with("Usage: cloud_only <cloud_name>")


# --- session command help flags ---


class TestSessionHelpFlags:
    @pytest.fixture
    def session_cmd(self, mock_shell):
        return SessionCommands(mock_shell)

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_session_help_flags(self, session_cmd, mock_shell, flag):
        session_cmd.cmd_session(flag)
        assert mock_shell.poutput.call_count >= 1
        assert any("Usage:" in str(c) for c in mock_shell.poutput.call_args_list)
