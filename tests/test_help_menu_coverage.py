import pytest
from unittest.mock import MagicMock, patch
from quads_client.shell import QuadsClientShell
from quads_client.commands.host import HostCommands
from quads_client.commands.cloud import CloudCommands
from quads_client.commands.session import SessionCommands
from tests.helpers import completions_to_list as _to_list


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
    mock_conn.is_connected = True
    mock_conn.current_server = "test_server"
    mock_conn.username = "testuser@example.com"
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
    mock_conn.api.filter_assignments.return_value = [
        {"id": 1},
        {"id": 2},
    ]
    mock_conn.api.get_schedules.return_value = [
        {"id": 10, "host": {"name": "host01"}},
        {"id": 11, "host": {"name": "host02"}},
    ]
    mock_conn.api.get_current_schedules.return_value = [
        {"host": {"name": "host01"}},
        {"host": {"name": "host02"}},
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
        assert _to_list(shell.complete_schedule("", "schedule ", 9, 9)) == []

    def test_not_authenticated(self):
        shell = _make_connected_shell()
        shell.connection.is_authenticated = False
        assert _to_list(shell.complete_schedule("", "schedule ", 9, 9)) == []

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
        assert _to_list(result) == []

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
        assert _to_list(shell.complete_cloud_only("", "cloud_only ", 11, 11)) == []

    def test_not_authenticated(self):
        shell = _make_connected_shell()
        shell.connection.is_authenticated = False
        assert _to_list(shell.complete_cloud_only("", "cloud_only ", 11, 11)) == []

    def test_all_clouds(self):
        shell = _make_connected_shell()
        result = shell.complete_cloud_only("", "cloud_only ", 11, 11)
        assert "cloud01" in result
        assert "cloud02" in result

    def test_filtered(self):
        shell = _make_connected_shell()
        result = shell.complete_cloud_only("cloud01", "cloud_only cloud01", 11, 18)
        assert _to_list(result) == ["cloud01"]

    def test_api_exception(self):
        shell = _make_connected_shell()
        shell.connection.api.get_clouds.side_effect = Exception("fail")
        assert _to_list(shell.complete_cloud_only("", "cloud_only ", 11, 11)) == []


# --- complete_move_status ---


class TestCompleteMoveStatus:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert _to_list(shell.complete_move_status("", "move_status ", 12, 12)) == []

    def test_not_authenticated(self):
        shell = _make_connected_shell()
        shell.connection.is_authenticated = False
        assert _to_list(shell.complete_move_status("", "move_status ", 12, 12)) == []

    def test_all_hosts(self):
        shell = _make_connected_shell()
        result = shell.complete_move_status("", "move_status ", 12, 12)
        assert "host01" in result
        assert "host02" in result

    def test_filtered(self):
        shell = _make_connected_shell()
        result = shell.complete_move_status("host01", "move_status host01", 12, 18)
        assert _to_list(result) == ["host01"]

    def test_api_exception(self):
        shell = _make_connected_shell()
        shell.connection.api.get_hosts.side_effect = Exception("fail")
        assert _to_list(shell.complete_move_status("", "move_status ", 12, 12)) == []


# --- complete_track ---


class TestCompleteTrack:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert _to_list(shell.complete_track("", "track ", 6, 6)) == []

    def test_not_authenticated(self):
        shell = _make_connected_shell()
        shell.connection.is_authenticated = False
        assert _to_list(shell.complete_track("", "track ", 6, 6)) == []

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
        assert _to_list(shell.complete_track("", "track ", 6, 6)) == []


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
        assert _to_list(result) == ["server1"]

    def test_no_config(self):
        shell = _make_shell()
        shell.config = None
        result = shell.complete_session_create("", "session_create ", 15, 15)
        assert _to_list(result) == []


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
        assert _to_list(result) == ["1"]

    def test_no_session_manager(self):
        shell = _make_shell()
        shell.session_manager = None
        result = shell.complete_session_switch("", "session_switch ", 15, 15)
        assert _to_list(result) == []


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
        assert _to_list(result) == ["dev"]

    def test_no_session_manager(self):
        shell = _make_shell()
        shell.session_manager = None
        result = shell.complete_session("", "session ", 8, 8)
        assert _to_list(result) == []


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
        assert _to_list(result) == ["2"]

    def test_no_session_manager(self):
        shell = _make_shell()
        shell.session_manager = None
        result = shell.complete_session_close("", "session_close ", 14, 14)
        assert _to_list(result) == []


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


# --- complete_terminate ---


class TestCompleteTerminate:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_terminate("", "terminate ", 10, 10) == []

    def test_not_authenticated(self):
        shell = _make_connected_shell()
        shell.connection.is_authenticated = False
        assert shell.complete_terminate("", "terminate ", 10, 10) == []

    def test_first_arg_assignment_ids(self):
        shell = _make_connected_shell()
        result = shell.complete_terminate("", "terminate ", 10, 10)
        assert "1" in result
        assert "2" in result

    def test_second_arg_hostnames(self):
        shell = _make_connected_shell()
        result = shell.complete_terminate("h", "terminate 1 h", 12, 13)
        assert "host01" in result
        assert "host02" in result

    def test_assignment_ids_sorted_numerically(self):
        shell = _make_connected_shell()
        shell.connection.api.filter_assignments.return_value = [
            {"id": 10},
            {"id": 11},
            {"id": 8},
        ]
        result = shell.complete_terminate("", "terminate ", 10, 10)
        assert result == ["8", "10", "11"]

    def test_api_exception(self):
        shell = _make_connected_shell()
        shell.connection.api.filter_assignments.side_effect = Exception("fail")
        assert shell.complete_terminate("", "terminate ", 10, 10) == []


# --- complete_extend ---


class TestCompleteExtend:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_extend("", "extend ", 7, 7) == []

    def test_not_admin(self):
        shell = _make_connected_shell(is_admin=False)
        assert shell.complete_extend("", "extend ", 7, 7) == []

    def test_first_arg_clouds_and_hosts(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_extend("", "extend ", 7, 7)
        assert "cloud01" in result
        assert "host01" in result

    def test_second_arg_keywords(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_extend("w", "extend cloud01 w", 15, 16)
        assert "weeks" in result

    def test_api_exception(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.get_clouds.side_effect = Exception("fail")
        assert shell.complete_extend("", "extend ", 7, 7) == []


# --- complete_shrink ---


class TestCompleteShrink:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_shrink("", "shrink ", 7, 7) == []

    def test_not_admin(self):
        shell = _make_connected_shell(is_admin=False)
        assert shell.complete_shrink("", "shrink ", 7, 7) == []

    def test_first_arg_clouds_and_hosts(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_shrink("", "shrink ", 7, 7)
        assert "cloud01" in result
        assert "host01" in result

    def test_second_arg_weeks(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_shrink("w", "shrink cloud01 w", 15, 16)
        assert "weeks" in result

    def test_second_arg_date(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_shrink("d", "shrink cloud01 d", 15, 16)
        assert "days" in result
        assert "date" in result

    def test_api_exception(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.get_clouds.side_effect = Exception("fail")
        assert shell.complete_shrink("", "shrink ", 7, 7) == []


# --- complete_cloud_delete ---


class TestCompleteCloudDelete:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_cloud_delete("", "cloud_delete ", 13, 13) == []

    def test_not_admin(self):
        shell = _make_connected_shell(is_admin=False)
        assert shell.complete_cloud_delete("", "cloud_delete ", 13, 13) == []

    def test_all_clouds(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_cloud_delete("", "cloud_delete ", 13, 13)
        assert "cloud01" in result
        assert "cloud02" in result

    def test_api_exception(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.get_clouds.side_effect = Exception("fail")
        assert shell.complete_cloud_delete("", "cloud_delete ", 13, 13) == []


# --- complete_mod_cloud ---


class TestCompleteModCloud:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_mod_cloud("", "mod_cloud ", 10, 10) == []

    def test_not_admin(self):
        shell = _make_connected_shell(is_admin=False)
        assert shell.complete_mod_cloud("", "mod_cloud ", 10, 10) == []

    def test_first_arg_cloud_names(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_mod_cloud("", "mod_cloud ", 10, 10)
        assert "cloud01" in result
        assert "cloud02" in result

    def test_later_args_keywords(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_mod_cloud("c", "mod_cloud cloud01 c", 18, 19)
        assert "cloud-owner" in result
        assert "cloud-ticket" in result
        assert "cc-users" in result

    def test_api_exception(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.get_clouds.side_effect = Exception("fail")
        assert shell.complete_mod_cloud("", "mod_cloud ", 10, 10) == []


# --- complete_cloud_list ---


class TestCompleteCloudList:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_cloud_list("", "cloud_list ", 11, 11) == []

    def test_keywords(self):
        shell = _make_connected_shell()
        result = shell.complete_cloud_list("", "cloud_list ", 11, 11)
        assert "cloud" in result
        assert "detail" in result

    def test_cloud_names_after_keyword(self):
        shell = _make_connected_shell()
        result = shell.complete_cloud_list("c", "cloud_list cloud c", 17, 18)
        assert "cloud01" in result
        assert "cloud02" in result

    def test_api_exception(self):
        shell = _make_connected_shell()
        shell.connection.api.get_clouds.side_effect = Exception("fail")
        assert _to_list(shell.complete_cloud_list("c", "cloud_list cloud c", 17, 18)) == []


# --- complete_mark_broken ---


class TestCompleteMarkBroken:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_mark_broken("", "mark_broken ", 12, 12) == []

    def test_not_admin(self):
        shell = _make_connected_shell(is_admin=False)
        assert shell.complete_mark_broken("", "mark_broken ", 12, 12) == []

    def test_non_broken_hosts(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.get_hosts.return_value = [
            {"name": "host01", "broken": False},
            {"name": "host02", "broken": True},
        ]
        result = shell.complete_mark_broken("", "mark_broken ", 12, 12)
        assert "host01" in result
        assert "host02" not in result

    def test_api_exception(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.get_hosts.side_effect = Exception("fail")
        assert shell.complete_mark_broken("", "mark_broken ", 12, 12) == []


# --- complete_mark_repaired ---


class TestCompleteMarkRepaired:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_mark_repaired("", "mark_repaired ", 14, 14) == []

    def test_not_admin(self):
        shell = _make_connected_shell(is_admin=False)
        assert shell.complete_mark_repaired("", "mark_repaired ", 14, 14) == []

    def test_broken_hosts(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_mark_repaired("", "mark_repaired ", 14, 14)
        assert "host01" in result
        assert "host02" in result

    def test_api_exception(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.filter_hosts.side_effect = Exception("fail")
        assert shell.complete_mark_repaired("", "mark_repaired ", 14, 14) == []


# --- complete_retire ---


class TestCompleteRetire:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_retire("", "retire ", 7, 7) == []

    def test_not_admin(self):
        shell = _make_connected_shell(is_admin=False)
        assert shell.complete_retire("", "retire ", 7, 7) == []

    def test_non_retired_hosts(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.get_hosts.return_value = [
            {"name": "host01", "retired": False},
            {"name": "host02", "retired": True},
        ]
        result = shell.complete_retire("", "retire ", 7, 7)
        assert "host01" in result
        assert "host02" not in result

    def test_api_exception(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.get_hosts.side_effect = Exception("fail")
        assert shell.complete_retire("", "retire ", 7, 7) == []


# --- complete_unretire ---


class TestCompleteUnretire:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_unretire("", "unretire ", 9, 9) == []

    def test_not_admin(self):
        shell = _make_connected_shell(is_admin=False)
        assert shell.complete_unretire("", "unretire ", 9, 9) == []

    def test_retired_hosts(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_unretire("", "unretire ", 9, 9)
        assert "host01" in result
        assert "host02" in result

    def test_api_exception(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.filter_hosts.side_effect = Exception("fail")
        assert shell.complete_unretire("", "unretire ", 9, 9) == []


# --- complete_ls_schedule ---


class TestCompleteLsSchedule:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_ls_schedule("", "ls_schedule ", 12, 12) == []

    def test_keywords(self):
        shell = _make_connected_shell()
        result = shell.complete_ls_schedule("", "ls_schedule ", 12, 12)
        assert "host" in result
        assert "cloud" in result

    def test_hostnames_after_host_keyword(self):
        shell = _make_connected_shell()
        result = shell.complete_ls_schedule("h", "ls_schedule host h", 17, 18)
        assert "host01" in result
        assert "host02" in result

    def test_cloud_names_after_cloud_keyword(self):
        shell = _make_connected_shell()
        result = shell.complete_ls_schedule("c", "ls_schedule cloud c", 18, 19)
        assert "cloud01" in result
        assert "cloud02" in result

    def test_api_exception(self):
        shell = _make_connected_shell()
        shell.connection.api.get_hosts.side_effect = Exception("fail")
        assert _to_list(shell.complete_ls_schedule("h", "ls_schedule host h", 17, 18)) == []


# --- complete_mod_schedule ---


class TestCompleteModSchedule:
    def test_no_connection(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell.complete_mod_schedule("", "mod_schedule ", 13, 13) == []

    def test_not_admin(self):
        shell = _make_connected_shell(is_admin=False)
        assert shell.complete_mod_schedule("", "mod_schedule ", 13, 13) == []

    def test_keywords(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_mod_schedule("", "mod_schedule ", 13, 13)
        assert "id" in result
        assert "start" in result
        assert "end" in result

    def test_schedule_ids_after_id_keyword(self):
        shell = _make_connected_shell(is_admin=True)
        result = shell.complete_mod_schedule("1", "mod_schedule id 1", 16, 17)
        assert "10" in result
        assert "11" in result

    def test_api_exception(self):
        shell = _make_connected_shell(is_admin=True)
        shell.connection.api.get_schedules.side_effect = Exception("fail")
        assert _to_list(shell.complete_mod_schedule("1", "mod_schedule id 1", 16, 17)) == []


# --- complete_edit_server ---


class TestCompleteEditServer:
    def test_no_config(self):
        shell = _make_shell()
        shell.config = None
        assert shell.complete_edit_server("", "edit_server ", 12, 12) == []

    def test_first_arg_server_names(self):
        shell = _make_shell()
        mock_config = MagicMock()
        mock_config.get_all_servers.return_value = {"server1": {}, "server2": {}}
        shell.config = mock_config
        result = shell.complete_edit_server("", "edit_server ", 12, 12)
        assert "server1" in result
        assert "server2" in result

    def test_later_args_keywords(self):
        shell = _make_shell()
        mock_config = MagicMock()
        mock_config.get_all_servers.return_value = {"server1": {}}
        shell.config = mock_config
        result = shell.complete_edit_server("u", "edit_server server1 u", 20, 21)
        assert "url" in result
        assert "username" in result

    def test_exception(self):
        shell = _make_shell()
        mock_config = MagicMock()
        mock_config.get_all_servers.side_effect = Exception("fail")
        shell.config = mock_config
        assert shell.complete_edit_server("", "edit_server ", 12, 12) == []


# --- complete_rm_server ---


class TestCompleteRmServer:
    def test_no_config(self):
        shell = _make_shell()
        shell.config = None
        assert shell.complete_rm_server("", "rm_server ", 10, 10) == []

    def test_excludes_connected_server(self):
        shell = _make_connected_shell()
        mock_config = MagicMock()
        mock_config.get_all_servers.return_value = {
            "test_server": {},
            "other_server": {},
        }
        shell.config = mock_config
        result = shell.complete_rm_server("", "rm_server ", 10, 10)
        assert "other_server" in result
        assert "test_server" not in result

    def test_exception(self):
        shell = _make_shell()
        mock_config = MagicMock()
        mock_config.get_all_servers.side_effect = Exception("fail")
        shell.config = mock_config
        assert shell.complete_rm_server("", "rm_server ", 10, 10) == []


# --- postcmd ---


class TestPostcmd:
    def test_returns_stop_and_updates_prompt(self):
        shell = _make_shell()
        shell._update_prompt = MagicMock()
        result = shell.postcmd(True, "some_command")
        assert result is True
        shell._update_prompt.assert_called_once()

    def test_returns_false(self):
        shell = _make_shell()
        shell._update_prompt = MagicMock()
        result = shell.postcmd(False, "some_command")
        assert result is False


# --- _get_activity_indicator ---


class TestGetActivityIndicator:
    def test_not_authenticated(self):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        assert shell._get_activity_indicator() == ""

    def test_active_moves(self):
        shell = _make_connected_shell()
        shell._last_activity_check = 0
        shell.connection.api.get_all_move_status.return_value = [{"host": "host01"}]
        result = shell._get_activity_indicator()
        assert "⚡" in result

    def test_no_moves(self):
        shell = _make_connected_shell()
        shell._last_activity_check = 0
        shell.connection.api.get_all_move_status.return_value = []
        result = shell._get_activity_indicator()
        assert result == ""

    def test_api_exception(self):
        shell = _make_connected_shell()
        shell._last_activity_check = 0
        shell.connection.api.get_all_move_status.side_effect = Exception("fail")
        result = shell._get_activity_indicator()
        assert result == ""

    def test_cached_within_30s(self):
        import time

        shell = _make_connected_shell()
        shell._last_activity_check = time.time()
        shell._cached_activity_indicator = "cached"
        result = shell._get_activity_indicator()
        assert result == "cached"


# --- _get_session_indicators ---


class TestGetSessionIndicators:
    def test_no_session_manager(self):
        shell = _make_shell()
        shell.session_manager = None
        assert shell._get_session_indicators() == ""

    def test_single_session(self):
        shell = _make_shell()
        s1 = MagicMock()
        s1.id = "1"
        s1.label = "dev"
        shell.session_manager.list_sessions.return_value = [s1]
        assert shell._get_session_indicators() == ""

    def test_multiple_sessions(self):
        shell = _make_shell()
        s1 = MagicMock()
        s1.id = "1"
        s1.label = "dev"
        s2 = MagicMock()
        s2.id = "2"
        s2.label = "prod"
        shell.session_manager.active_session_id = "1"
        shell.session_manager.list_sessions.return_value = [s1, s2]
        result = shell._get_session_indicators()
        assert "1:dev*" in result
        assert "2:prod" in result

    def test_overflow_more_than_4(self):
        shell = _make_shell()
        sessions = []
        for i in range(6):
            s = MagicMock()
            s.id = str(i)
            s.label = f"s{i}"
            sessions.append(s)
        shell.session_manager.active_session_id = "0"
        shell.session_manager.list_sessions.return_value = sessions
        result = shell._get_session_indicators()
        assert "+2" in result


# --- do_* delegates ---


class TestDoCommandDelegates:
    @pytest.mark.parametrize(
        "method,command_group,command_method",
        [
            ("do_version", "version_commands", "cmd_version"),
            ("do_connect", "connection_commands", "cmd_connect"),
            ("do_disconnect", "connection_commands", "cmd_disconnect"),
            ("do_status", "connection_commands", "cmd_status"),
            ("do_cloud_list", "cloud_commands", "cmd_cloud_list"),
            ("do_find_free_cloud", "cloud_commands", "cmd_find_free_cloud"),
            ("do_cloud_only", "cloud_commands", "cmd_cloud_only"),
            ("do_ls_vlan", "cloud_commands", "cmd_ls_vlan"),
            ("do_os_list", "cloud_commands", "cmd_os_list"),
            ("do_cloud_create", "cloud_commands", "cmd_cloud_create"),
            ("do_cloud_delete", "cloud_commands", "cmd_cloud_delete"),
            ("do_register", "user_commands", "cmd_register"),
            ("do_login", "user_commands", "cmd_login"),
            ("do_token_login", "user_commands", "cmd_token_login"),
            ("do_whoami", "user_commands", "cmd_whoami"),
            ("do_assignment_create", "user_commands", "cmd_assignment_create"),
            ("do_assignment_list", "user_commands", "cmd_assignment_list"),
            ("do_assignment_status", "user_commands", "cmd_assignment_status"),
            ("do_my_hosts", "user_commands", "cmd_my_hosts"),
            ("do_my_assignments", "user_commands", "cmd_my_assignments"),
            ("do_terminate", "user_commands", "cmd_terminate"),
            ("do_ls_hosts", "host_commands", "cmd_ls_hosts"),
            ("do_mark_broken", "host_commands", "cmd_mark_broken"),
            ("do_mark_repaired", "host_commands", "cmd_mark_repaired"),
            ("do_retire", "host_commands", "cmd_retire"),
            ("do_unretire", "host_commands", "cmd_unretire"),
            ("do_ls_broken", "host_commands", "cmd_ls_broken"),
            ("do_ls_retired", "host_commands", "cmd_ls_retired"),
            ("do_ls_schedule", "schedule_commands", "cmd_ls_schedule"),
            ("do_mod_schedule", "schedule_commands", "cmd_mod_schedule"),
            ("do_extend", "schedule_commands", "cmd_extend"),
            ("do_shrink", "schedule_commands", "cmd_shrink"),
            ("do_ls_available", "available_commands", "cmd_ls_available"),
            ("do_move_status", "move_commands", "cmd_move_status"),
            ("do_track", "track_commands", "cmd_track"),
            ("do_activity", "move_commands", "cmd_activity"),
            ("do_servers", "server_commands", "cmd_servers"),
            ("do_add_server", "server_commands", "cmd_add_server"),
            ("do_add_quads_server", "server_commands", "cmd_add_quads_server"),
            ("do_edit_server", "server_commands", "cmd_edit_server"),
            ("do_rm_server", "server_commands", "cmd_rm_server"),
            ("do_config_reload", "server_commands", "cmd_config_reload"),
            ("do_session_create", "session_commands", "cmd_session_create"),
            ("do_session_switch", "session_commands", "cmd_session_switch"),
            ("do_session", "session_commands", "cmd_session"),
            ("do_session_list", "session_commands", "cmd_session_list"),
            ("do_session_close", "session_commands", "cmd_session_close"),
            ("do_session_close_all", "session_commands", "cmd_session_close_all"),
            ("do_mod_cloud", "cloud_commands", "cmd_mod_cloud"),
        ],
    )
    def test_delegate(self, method, command_group, command_method):
        shell = _make_shell()
        mock_group = MagicMock()
        setattr(shell, command_group, mock_group)
        getattr(shell, method)("test_args")
        getattr(mock_group, command_method).assert_called_once_with("test_args")


# --- do_debug_admin ---


class TestDoDebugAdmin:
    def test_with_connection(self, capsys):
        shell = _make_connected_shell()
        shell.do_debug_admin("")
        output = capsys.readouterr().out
        assert "Connected:" in output
        assert "Authenticated:" in output

    def test_without_connection(self, capsys):
        shell = _make_shell()
        shell.session_manager.active_connection = None
        shell.do_debug_admin("")
        output = capsys.readouterr().out
        assert "No connection" in output
