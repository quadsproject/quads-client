"""Tests for unified schedule command and related features"""

import pytest
from unittest.mock import MagicMock, patch
from quads_client.commands.user import UserCommands
from quads_client.commands.schedule import ScheduleCommands


class TestUnifiedScheduleSSM:
    """Test SSM mode schedule command"""

    def test_schedule_ssm_count_success(self, mock_shell):
        """Test SSM schedule with count mode"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.return_value = [
            {"name": "host01.example.com"},
            {"name": "host02.example.com"},
            {"name": "host03.example.com"},
        ]
        mock_shell.connection.api.create_self_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "owner": "alice",
        }
        mock_shell.connection.api.create_schedule.return_value = {"id": 1}

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('3 description "Dev testing"')

        # Verify API calls per QUADS SSM spec
        mock_shell.connection.api.filter_available.assert_called_once()
        mock_shell.connection.api.create_self_assignment.assert_called_once()
        # Schedules created separately (3 calls for 3 hosts)
        assert mock_shell.connection.api.create_schedule.call_count == 3

    def test_schedule_ssm_hosts_comma_separated(self, mock_shell):
        """Test SSM schedule with comma-separated hosts"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.create_self_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "owner": "alice",
        }
        mock_shell.connection.api.create_schedule.return_value = {"id": 1}

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('host01,host02 description "CI pipeline"')

        # Verify API calls per QUADS SSM spec
        mock_shell.connection.api.create_self_assignment.assert_called_once()
        assert mock_shell.connection.api.create_schedule.call_count == 2

    def test_schedule_ssm_with_options(self, mock_shell):
        """Test SSM schedule with optional parameters"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.return_value = [
            {"name": "host01.example.com"},
            {"name": "host02.example.com"},
        ]
        mock_shell.connection.api.create_self_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "owner": "alice",
        }
        mock_shell.connection.api.create_schedule.return_value = {"id": 1}

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('2 description "Test" model r640 ram 64 vlan 1150 qinq 1 nowipe')

        # Verify assignment data includes optional params
        call_args = mock_shell.connection.api.create_self_assignment.call_args[0][0]
        assert call_args["wipe"] is False
        assert call_args["vlan"] == 1150
        assert call_args["qinq"] == 1

    def test_schedule_ssm_with_os(self, mock_shell):
        """Test SSM schedule with OS option"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.return_value = [
            {"name": "host01.example.com"},
        ]
        mock_shell.connection.api.create_self_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "owner": "alice",
        }
        mock_shell.connection.api.create_schedule.return_value = {"id": 1}

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('1 description "Test" os "RHEL 9.4"')

        call_args = mock_shell.connection.api.create_self_assignment.call_args[0][0]
        assert call_args["ostype"] == "RHEL 9.4"

    def test_schedule_ssm_insufficient_hosts(self, mock_shell):
        """Test SSM schedule with insufficient available hosts"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.return_value = [
            {"name": "host01.example.com"},
        ]

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('5 description "Test"')

        # Should error about insufficient hosts
        mock_shell.perror.assert_called()
        error_calls = [str(call) for call in mock_shell.perror.call_args_list]
        assert any("Not enough hosts available" in call for call in error_calls)

    def test_schedule_ssm_host_limit_exceeded(self, mock_shell):
        """Test SSM schedule exceeding ssm_host_limit"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.return_value = [
            {"name": f"host{i:02d}.example.com"} for i in range(15)
        ]
        mock_shell.connection.api.create_self_assignment.side_effect = Exception(
            "Host limit exceeded: requested 15, limit is 10"
        )

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('15 description "Test"')

        # Should handle error gracefully
        mock_shell.perror.assert_called()
        assert "SSM users can schedule max 10 hosts" in str(mock_shell.perror.call_args)

    def test_schedule_ssm_user_cloud_limit_exceeded(self, mock_shell):
        """Test SSM schedule exceeding ssm_user_cloud_limit"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.return_value = [
            {"name": "host01.example.com"},
            {"name": "host02.example.com"},
        ]
        mock_shell.connection.api.create_self_assignment.side_effect = Exception(
            "User cloud limit exceeded: you have 3 active assignments, limit is 3"
        )

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('2 description "Test"')

        # Should handle error gracefully with hints
        mock_shell.perror.assert_called()
        error_calls = [str(call) for call in mock_shell.perror.call_args_list]
        assert any("Terminate one first with 'terminate'" in call for call in error_calls)

    def test_schedule_ssm_missing_description(self, mock_shell):
        """Test SSM schedule without required description"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule("3")

        # Should error about missing description
        mock_shell.perror.assert_called()
        error_calls = [str(call) for call in mock_shell.perror.call_args_list]
        assert any("description is required" in call or "Invalid arguments" in call for call in error_calls)

    def test_schedule_ssm_with_disk_filters(self, mock_shell):
        """Test SSM schedule passes disk filters to filter_available"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.return_value = [
            {"name": "host01.example.com"},
        ]
        mock_shell.connection.api.create_self_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "owner": "alice",
        }
        mock_shell.connection.api.create_schedule.return_value = {"id": 1}

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('1 description "Test" disk-type nvme disk-size 500 disk-count 4')

        filters = mock_shell.connection.api.filter_available.call_args[0][0]
        assert filters["can_self_schedule"] is True
        assert filters["disks.disk_type"] == "nvme"
        assert filters["disks.size_gb__gte"] == 500
        assert filters["disks.count__gte"] == 4

    def test_schedule_ssm_with_gpu_filters(self, mock_shell):
        """Test SSM schedule passes GPU filters to filter_available"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.return_value = [
            {"name": "host01.example.com"},
        ]
        mock_shell.connection.api.create_self_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "owner": "alice",
        }
        mock_shell.connection.api.create_schedule.return_value = {"id": 1}

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('1 description "Test" gpu-vendor "NVIDIA Corporation" gpu-product "Tesla V100"')

        filters = mock_shell.connection.api.filter_available.call_args[0][0]
        assert filters["processors.vendor"] == "NVIDIA Corporation"
        assert filters["processors.product"] == "Tesla V100"

    def test_schedule_ssm_with_nic_filters(self, mock_shell):
        """Test SSM schedule passes NIC filters to filter_available"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.return_value = [
            {"name": "host01.example.com"},
        ]
        mock_shell.connection.api.create_self_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "owner": "alice",
        }
        mock_shell.connection.api.create_schedule.return_value = {"id": 1}

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('1 description "Test" nic-vendor Mellanox nic-speed 25')

        filters = mock_shell.connection.api.filter_available.call_args[0][0]
        assert filters["interfaces.vendor"] == "Mellanox"
        assert filters["interfaces.speed__gte"] == 25

    def test_schedule_ssm_with_interfaces_filter(self, mock_shell):
        """Test SSM schedule passes interface count filter to filter_available"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.return_value = [
            {"name": "host01.example.com"},
        ]
        mock_shell.connection.api.create_self_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud17"},
            "owner": "alice",
        }
        mock_shell.connection.api.create_schedule.return_value = {"id": 1}

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('1 description "Test" interfaces 4')

        filters = mock_shell.connection.api.filter_available.call_args[0][0]
        assert filters["interfaces.count__gte"] == 4


class TestUnifiedScheduleAdmin:
    """Test admin mode schedule command"""

    def test_schedule_admin_success(self, mock_shell):
        """Test admin schedule command"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud02"}]
        mock_shell.connection.api.get_active_cloud_assignment.return_value = {"id": 42}
        mock_shell.connection.api.create_schedules_batch.return_value = {
            "assignment_id": 42,
            "schedules_created": 3,
            "hostnames": ["host01", "host02", "host03"],
            "jira_updated": False,
        }

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_schedule_admin('cloud02 host01,host02,host03 "2026-05-11 22:00" "2026-06-11 22:00"')

        # Verify batch API call
        mock_shell.connection.api.filter_clouds.assert_called_once_with({"name": "cloud02"})
        mock_shell.connection.api.create_schedules_batch.assert_called_once()

    def test_schedule_admin_cloud_not_found(self, mock_shell):
        """Test admin schedule with non-existent cloud"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.filter_clouds.return_value = []

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_schedule_admin('cloud99 host01 "2026-05-11 22:00" "2026-06-11 22:00"')

        # Should error about cloud not found
        mock_shell.perror.assert_called_with("Cloud 'cloud99' not found")

    def test_schedule_admin_not_admin(self, mock_shell):
        """Test admin schedule when user is not admin"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_schedule_admin('cloud02 host01 "2026-05-11 22:00" "2026-06-11 22:00"')

        # Should deny permission
        mock_shell.perror.assert_called()
        assert "admin role" in str(mock_shell.perror.call_args).lower()


class TestExtendCommand:
    """Test cloud-based extend command"""

    def test_extend_cloud_by_weeks(self, mock_shell):
        """Test extending cloud by weeks"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.get_current_schedules.return_value = [
            {"id": 1, "host": {"name": "host01.example.com"}, "end": "2026-05-11T00:00:00Z"},
            {"id": 2, "host": {"name": "host02.example.com"}, "end": "2026-05-11T00:00:00Z"},
        ]
        mock_shell.connection.api.update_schedule.return_value = {"status": "success"}

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_extend("cloud02 weeks 2")

        # Verify API calls
        mock_shell.connection.api.get_current_schedules.assert_called_once_with({"cloud": "cloud02"})
        assert mock_shell.connection.api.update_schedule.call_count == 2

    def test_extend_cloud_by_date(self, mock_shell):
        """Test extending cloud by specific date"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.get_current_schedules.return_value = [
            {"id": 1, "host": {"name": "host01.example.com"}, "end": "2026-05-11T00:00:00Z"},
        ]
        mock_shell.connection.api.update_schedule.return_value = {"status": "success"}

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_extend('cloud02 date "2026-05-17 22:00"')

        # Verify API calls
        mock_shell.connection.api.get_current_schedules.assert_called_once_with({"cloud": "cloud02"})
        mock_shell.connection.api.update_schedule.assert_called_once()

    def test_extend_hostname_by_weeks(self, mock_shell):
        """Test extending specific hostname by weeks"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.get_current_schedules.return_value = [
            {"id": 1, "host": {"name": "host01.example.com"}, "end": "2026-05-11T00:00:00Z"},
        ]
        mock_shell.connection.api.update_schedule.return_value = {"status": "success"}

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_extend("host01.example.com weeks 1")

        # Verify API calls
        mock_shell.connection.api.get_current_schedules.assert_called_once_with({"host": "host01.example.com"})
        mock_shell.connection.api.update_schedule.assert_called_once()

    def test_extend_not_admin(self, mock_shell):
        """Test extend when user is not admin"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_extend("cloud02 weeks 2")

        # Should deny permission
        mock_shell.perror.assert_called()
        assert "admin role" in str(mock_shell.perror.call_args).lower()


class TestMyAssignments:
    """Test my-assignments command"""

    def test_my_assignments_success(self, mock_shell):
        """Test listing user's active assignments"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_assignments.return_value = [
            {
                "id": 42,
                "cloud": {"name": "cloud17"},
                "description": "Dev testing",
                "validated": True,
                "active": True,
            },
            {
                "id": 43,
                "cloud": {"name": "cloud18"},
                "description": "CI pipeline",
                "validated": False,
                "active": True,
            },
        ]

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_my_assignments("")

        # Verify API call with owner AND active filter
        mock_shell.connection.api.filter_assignments.assert_called_once_with({"owner": "alice", "active": True})
        mock_shell.poutput.assert_called()

    def test_my_assignments_empty(self, mock_shell):
        """Test my-assignments with no active assignments"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_assignments.return_value = []

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_my_assignments("")

        # Should show no active assignments message
        assert "No active assignments found" in str(mock_shell.poutput.call_args)


class TestTerminateCommand:
    """Test terminate command with ownership validation"""

    def test_terminate_entire_assignment(self, mock_shell):
        """Test terminating entire assignment"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_assignments.return_value = [
            {"id": 42, "cloud": {"name": "cloud17"}, "owner": "alice"}
        ]
        mock_shell.connection.api.terminate_assignment.return_value = {"status": "success"}

        with patch("builtins.input", return_value="y"):
            user_cmd = UserCommands(mock_shell)
            user_cmd.cmd_terminate("42")

        # Verify API calls
        mock_shell.connection.api.filter_assignments.assert_called_once()
        mock_shell.connection.api.terminate_assignment.assert_called_once_with(42)

    def test_terminate_ownership_denied(self, mock_shell):
        """Test terminate with ownership violation"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_assignments.return_value = [
            {"id": 42, "cloud": {"name": "cloud17"}, "owner": "bob"}  # Different owner
        ]

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_terminate("42")

        # Should deny permission
        mock_shell.perror.assert_called_with("Permission denied: You can only terminate your own assignments")

    def test_terminate_specific_host(self, mock_shell):
        """Test terminating specific host from assignment"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_assignments.return_value = [
            {"id": 42, "cloud": {"name": "cloud17"}, "owner": "alice"}
        ]
        mock_shell.connection.api.get_schedules.return_value = [{"id": 1}]
        mock_shell.connection.api.remove_schedule.return_value = {"status": "success"}

        with patch("builtins.input", return_value="y"):
            user_cmd = UserCommands(mock_shell)
            user_cmd.cmd_terminate("42 host03.example.com")

        # Verify API calls
        mock_shell.connection.api.remove_schedule.assert_called_once_with(1)


class TestErrorHandling:
    """Test error handling for various scenarios"""

    def test_handle_401_unauthorized(self, mock_shell):
        """Test handling 401 Unauthorized error"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.side_effect = Exception("401 Unauthorized")

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('3 description "Test"')

        # Should suggest login
        error_calls = [str(call) for call in mock_shell.perror.call_args_list]
        assert any("Run 'login'" in call for call in error_calls)

    def test_handle_connection_error(self, mock_shell):
        """Test handling connection errors"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = False
        mock_shell.connection.username = "alice@example.com"
        mock_shell.connection.api.filter_available.side_effect = ConnectionError("Connection refused")

        user_cmd = UserCommands(mock_shell)
        user_cmd.cmd_schedule('3 description "Test"')

        # Should show connection error with hint
        error_calls = [str(call) for call in mock_shell.perror.call_args_list]
        assert any("Connection failed" in call for call in error_calls)


class TestBatchScheduleEndpoint:
    """Test batch schedule endpoint integration"""

    def test_schedule_admin_batch_success(self, mock_shell):
        """Test admin schedule using batch endpoint"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud02"}]
        mock_shell.connection.api.get_active_cloud_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud02"},
        }
        mock_shell.connection.api.create_schedules_batch.return_value = {
            "assignment_id": 42,
            "schedules_created": 2,
            "hostnames": ["host01.example.com", "host02.example.com"],
            "jira_updated": True,
        }

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_schedule_admin('cloud02 host01,host02 "2026-05-11 22:00" "2026-06-11 22:00"')

        # Verify batch API was called instead of individual schedule calls
        mock_shell.connection.api.create_schedules_batch.assert_called_once()
        batch_data = mock_shell.connection.api.create_schedules_batch.call_args[0][0]
        assert batch_data["cloud"] == "cloud02"
        assert batch_data["hostnames"] == ["host01", "host02"]
        assert batch_data["start"] == "2026-05-11 22:00"
        assert batch_data["end"] == "2026-06-11 22:00"

    def test_schedule_admin_batch_now_keyword(self, mock_shell):
        """Test batch schedule with 'now' keyword"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud02"}]
        mock_shell.connection.api.get_active_cloud_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud02"},
        }
        mock_shell.connection.api.create_schedules_batch.return_value = {
            "assignment_id": 42,
            "schedules_created": 2,
            "hostnames": ["host01.example.com", "host02.example.com"],
            "jira_updated": True,
        }

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_schedule_admin('cloud02 host01,host02 now "2026-06-11 22:00"')

        # Verify 'now' is passed to API
        batch_data = mock_shell.connection.api.create_schedules_batch.call_args[0][0]
        assert batch_data["start"] == "now"

    def test_schedule_admin_batch_with_assignment_params(self, mock_shell):
        """Test batch schedule with new assignment creation"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud02"}]
        mock_shell.connection.api.get_active_cloud_assignment.return_value = None
        mock_shell.connection.api.create_schedules_batch.return_value = {
            "assignment_id": 158,
            "schedules_created": 2,
            "hostnames": ["host01.example.com", "host02.example.com"],
            "jira_updated": True,
        }

        schedule_cmd = ScheduleCommands(mock_shell)
        cmd = (
            'cloud02 host01,host02 "2026-05-11 22:00" "2026-06-11 22:00" '
            'description "Testing" cloud-owner jdoe cloud-ticket 123 '
            "cc-users wfoster vlan 1234 qinq 1"
        )
        schedule_cmd.cmd_schedule_admin(cmd)

        # Verify assignment parameters in batch call
        batch_data = mock_shell.connection.api.create_schedules_batch.call_args[0][0]
        assert batch_data["description"] == "Testing"
        assert batch_data["owner"] == "jdoe"
        assert batch_data["ticket"] == "123"
        assert batch_data["ccuser"] == "wfoster"
        assert batch_data["vlan"] == 1234
        assert batch_data["qinq"] == 1

    def test_schedule_admin_batch_jira_updated(self, mock_shell):
        """Test batch schedule with JIRA update confirmation"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud02"}]
        mock_shell.connection.api.get_active_cloud_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud02"},
        }
        mock_shell.connection.api.create_schedules_batch.return_value = {
            "assignment_id": 42,
            "schedules_created": 3,
            "hostnames": ["host01.example.com", "host02.example.com", "host03.example.com"],
            "jira_updated": True,
        }

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_schedule_admin('cloud02 host01,host02,host03 "2026-05-11 22:00" "2026-06-11 22:00"')

        # Verify JIRA update is acknowledged
        output_calls = [str(call) for call in mock_shell.poutput.call_args_list]
        assert any("JIRA ticket updated" in call for call in output_calls)

    def test_schedule_admin_batch_host_list_file(self, mock_shell, tmp_path):
        """Test batch schedule with host-list file"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud02"}]
        mock_shell.connection.api.get_active_cloud_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud02"},
        }
        mock_shell.connection.api.create_schedules_batch.return_value = {
            "assignment_id": 42,
            "schedules_created": 3,
            "hostnames": ["host01.example.com", "host02.example.com", "host03.example.com"],
            "jira_updated": True,
        }

        # Create temporary host-list file
        host_file = tmp_path / "hosts.txt"
        host_file.write_text("host01.example.com\nhost02.example.com\nhost03.example.com\n")

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_schedule_admin(f'cloud02 host-list {host_file} "2026-05-11 22:00" "2026-06-11 22:00"')

        # Verify batch call includes all hosts from file
        batch_data = mock_shell.connection.api.create_schedules_batch.call_args[0][0]
        assert len(batch_data["hostnames"]) == 3
        assert "host01.example.com" in batch_data["hostnames"]
        assert "host02.example.com" in batch_data["hostnames"]
        assert "host03.example.com" in batch_data["hostnames"]

    def test_schedule_admin_batch_failure_handling(self, mock_shell):
        """Test batch schedule failure handling"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud02"}]
        mock_shell.connection.api.get_active_cloud_assignment.return_value = {
            "id": 42,
            "cloud": {"name": "cloud02"},
        }
        mock_shell.connection.api.create_schedules_batch.side_effect = Exception("Host unavailable")

        schedule_cmd = ScheduleCommands(mock_shell)
        schedule_cmd.cmd_schedule_admin('cloud02 host01,host02 "2026-05-11 22:00" "2026-06-11 22:00"')

        # Should show error
        mock_shell.perror.assert_called()
        error_calls = [str(call) for call in mock_shell.perror.call_args_list]
        assert any("Host unavailable" in call for call in error_calls)

    def test_schedule_admin_batch_with_os(self, mock_shell):
        """Test batch schedule with OS option"""
        mock_shell.connection.is_connected = True
        mock_shell.connection.is_authenticated = True
        mock_shell.connection.is_admin = True
        mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud02"}]
        mock_shell.connection.api.create_schedules_batch.return_value = {
            "assignment_id": 42,
            "schedules_created": 1,
            "hostnames": ["host01.example.com"],
        }

        schedule_cmd = ScheduleCommands(mock_shell)
        cmd = (
            'cloud02 host01 "2026-05-11 22:00" "2026-06-11 22:00" '
            'description "Test" cloud-owner jdoe cloud-ticket 123 os "RHEL 9.4"'
        )
        schedule_cmd.cmd_schedule_admin(cmd)

        batch_data = mock_shell.connection.api.create_schedules_batch.call_args[0][0]
        assert batch_data["ostype"] == "RHEL 9.4"
