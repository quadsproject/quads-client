import pytest
from unittest.mock import MagicMock
from quads_client.commands.available import AvailableCommands


@pytest.fixture
def available_commands(mock_shell):
    return AvailableCommands(mock_shell)


def test_ls_available_success(available_commands, mock_shell):
    """Test listing available hosts successfully"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = [
        {
            "name": "host01.example.com",
            "model": "R630",
            "host_type": "baremetal",
            "can_self_schedule": True,
        },
        {
            "name": "host02.example.com",
            "model": "R640",
            "host_type": "baremetal",
            "can_self_schedule": False,
        },
    ]

    available_commands.cmd_ls_available("")

    expected_filters = {"cloud": "cloud01", "retired": False, "broken": False, "can_self_schedule": True}
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)
    mock_shell.poutput.assert_called()


def test_ls_available_admin_sees_all(available_commands, mock_shell):
    """Test that admin users see all available hosts (no self-schedule filter)"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_admin = True
    mock_shell.connection.api.filter_hosts.return_value = [
        {"name": "host01.example.com", "model": "R630", "host_type": "baremetal", "can_self_schedule": True},
        {"name": "host02.example.com", "model": "R640", "host_type": "baremetal", "can_self_schedule": False},
    ]

    available_commands.cmd_ls_available("")

    expected_filters = {"cloud": "cloud01", "retired": False, "broken": False}
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)
    mock_shell.poutput.assert_called()


def test_ls_available_non_admin_filters_self_schedule(available_commands, mock_shell):
    """Test that non-admin users only see self-schedulable hosts"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.is_admin = False
    mock_shell.connection.api.filter_hosts.return_value = [
        {"name": "host01.example.com", "model": "R630", "host_type": "baremetal", "can_self_schedule": True},
    ]

    available_commands.cmd_ls_available("")

    expected_filters = {"cloud": "cloud01", "retired": False, "broken": False, "can_self_schedule": True}
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)
    mock_shell.poutput.assert_called()


def test_ls_available_with_filters(available_commands, mock_shell):
    """Test listing available hosts with filters including date range"""
    mock_shell.connection.is_connected = True
    # Return hosts that filter_hosts would return (before availability check)
    mock_shell.connection.api.filter_hosts.return_value = [
        {
            "name": "host01.example.com",
            "model": "R630",
            "host_type": "baremetal",
            "can_self_schedule": True,
        },
    ]
    # Mock is_available to return True (host passes availability check)
    mock_shell.connection.api.is_available.return_value = True

    available_commands.cmd_ls_available("start 2026-05-01 end 2026-05-15 model R630")

    # Start/end are extracted and used for is_available(), not passed to filter_hosts
    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "model": "R630",  # Uppercased to match QUADS storage
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)
    # Verify is_available was called with the host and date range
    mock_shell.connection.api.is_available.assert_called_once()


def test_ls_available_empty(available_commands, mock_shell):
    """Test ls-available with no available hosts"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("")

    mock_shell.poutput.assert_called_with("No available hosts found")


def test_ls_available_not_connected(available_commands, mock_shell):
    """Test ls-available when not connected"""
    mock_shell.connection.is_connected = False

    available_commands.cmd_ls_available("")

    mock_shell.perror.assert_called_with("Not connected to any server")


def test_ls_available_api_error(available_commands, mock_shell):
    """Test ls-available when API call fails"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.side_effect = Exception("API Error")

    available_commands.cmd_ls_available("")

    mock_shell.perror.assert_called_with("Failed to list available hosts: API Error")


def test_ls_available_start_filter_only(available_commands, mock_shell):
    """Test ls-available with only start date filter (no availability check without end date)"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("start 2026-05-01")

    # Start without end - won't trigger availability check, just shows hosts in cloud01
    expected_filters = {"cloud": "cloud01", "retired": False, "broken": False, "can_self_schedule": True}
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_end_filter_only(available_commands, mock_shell):
    """Test ls-available with only end date filter (no availability check without start date)"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("end 2026-05-15")

    # End without start - won't trigger availability check, just shows hosts in cloud01
    expected_filters = {"cloud": "cloud01", "retired": False, "broken": False, "can_self_schedule": True}
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_model_filter_only(available_commands, mock_shell):
    """Test ls-available with only model filter"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("model R630")

    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "model": "R630",
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_string_error(available_commands, mock_shell):
    """Test ls-available when API returns error string"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = "Database connection failed"

    available_commands.cmd_ls_available("")

    mock_shell.perror.assert_called_with("API error: Database connection failed")


def test_ls_available_unexpected_type(available_commands, mock_shell):
    """Test ls-available when API returns unexpected type"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = 12345  # int instead of list

    available_commands.cmd_ls_available("")

    mock_shell.perror.assert_called_with("Unexpected response type: <class 'int'>")


def test_ls_available_object_response(available_commands, mock_shell):
    """Test ls-available with object responses instead of dicts"""
    mock_shell.connection.is_connected = True

    # Create mock objects with attributes instead of dicts
    mock_host = MagicMock()
    mock_host.name = "host03.example.com"
    mock_host.model = "R650"
    mock_host.host_type = "baremetal"
    mock_host.can_self_schedule = True

    mock_shell.connection.api.filter_hosts.return_value = [mock_host]

    available_commands.cmd_ls_available("")

    # Should handle object responses by using getattr
    mock_shell.poutput.assert_called()


def test_ls_available_unknown_flag(available_commands, mock_shell):
    """Test ls-available ignores unknown flags"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    # unknown is not a valid flag, should be ignored
    available_commands.cmd_ls_available("unknown value model R630")

    # Should still process the valid model flag (uppercased)
    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "model": "R630",
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_ram_filter(available_commands, mock_shell):
    """Test ls-available with RAM filter"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("ram 256")

    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "memory__gte": 256 * 1024,
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_gpu_filters(available_commands, mock_shell):
    """Test ls-available with GPU vendor and product filters"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("gpu-vendor NVIDIA gpu-product V100")

    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "processors.vendor": "NVIDIA",
        "processors.product": "V100",
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_disk_filters(available_commands, mock_shell):
    """Test ls-available with disk filters"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("disk-size 500 disk-type nvme disk-count 2")

    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "disks.size_gb__gte": 500,
        "disks.disk_type": "nvme",
        "disks.count__gte": 2,
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_interface_filter(available_commands, mock_shell):
    """Test ls-available with network interface filter"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("interfaces 4")

    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "interfaces.count__gte": 4,
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_combined_filters(available_commands, mock_shell):
    """Test ls-available with multiple filter types"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("model r650 ram 128 disk-type nvme interfaces 4")

    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "model": "R650",  # Uppercased
        "memory__gte": 128 * 1024,
        "disks.disk_type": "nvme",
        "interfaces.count__gte": 4,
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_help(available_commands, mock_shell):
    """Test ls-available help with ?"""
    mock_shell.connection.is_connected = True

    available_commands.cmd_ls_available("?")

    # Should print help, not call API
    help_output = " ".join(str(call) for call in mock_shell.poutput.call_args_list)
    assert "Usage:" in help_output
    assert "nic-vendor" in help_output
    assert "nic-speed" in help_output
    mock_shell.connection.api.filter_hosts.assert_not_called()


def test_ls_available_help_dash_h(available_commands, mock_shell):
    """Test ls-available help with -h"""
    mock_shell.connection.is_connected = True

    available_commands.cmd_ls_available("-h")

    # Should print help, not call API
    assert any("Usage:" in str(call) for call in mock_shell.poutput.call_args_list)
    mock_shell.connection.api.filter_hosts.assert_not_called()


def test_ls_available_help_help_flag(available_commands, mock_shell):
    """Test ls-available help with --help"""
    mock_shell.connection.is_connected = True

    available_commands.cmd_ls_available("--help")

    # Should print help, not call API
    assert any("Usage:" in str(call) for call in mock_shell.poutput.call_args_list)
    mock_shell.connection.api.filter_hosts.assert_not_called()


def test_ls_available_nic_vendor_filter(available_commands, mock_shell):
    """Test ls-available with NIC vendor filter"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("nic-vendor Intel")

    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "interfaces.vendor": "Intel",
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_nic_speed_filter(available_commands, mock_shell):
    """Test ls-available with NIC speed filter"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("nic-speed 25")

    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "interfaces.speed__gte": 25,
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_nic_combined_filters(available_commands, mock_shell):
    """Test ls-available with NIC vendor and speed filters combined"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    available_commands.cmd_ls_available("nic-vendor Mellanox nic-speed 100")

    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "interfaces.vendor": "Mellanox",
        "interfaces.speed__gte": 100,
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)


def test_ls_available_case_insensitive_model(available_commands, mock_shell):
    """Test ls-available with case-insensitive model matching"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_hosts.return_value = []

    # User types lowercase, should be uppercased to match QUADS storage
    available_commands.cmd_ls_available("model r650")

    # Should uppercase the model value
    expected_filters = {
        "cloud": "cloud01",
        "retired": False,
        "broken": False,
        "model": "R650",
        "can_self_schedule": True,
    }
    mock_shell.connection.api.filter_hosts.assert_called_once_with(expected_filters)
