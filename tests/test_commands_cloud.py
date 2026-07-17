import pytest
from unittest.mock import MagicMock, call
from quads_client.commands.cloud import CloudCommands


def test_cloud_list_success(mock_shell):
    """Test cloud-list command success"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.get_clouds.return_value = [{"name": "cloud01"}, {"name": "cloud02"}]

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_list("")

    mock_shell.connection.api.get_clouds.assert_called_once()
    # Enhanced cloud-list now uses tabulate, so only one poutput call with the table
    assert mock_shell.poutput.call_count == 1


def test_cloud_list_no_clouds(mock_shell):
    """Test cloud-list with no clouds"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.get_clouds.return_value = []

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_list("")

    mock_shell.poutput.assert_called_with("No clouds found")


def test_cloud_list_not_connected(mock_shell):
    """Test cloud-list when not connected"""
    mock_shell.connection.is_connected = False

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_list("")

    mock_shell.perror.assert_called_with("Not connected to any server")


def test_cloud_create_success(mock_shell):
    """Test cloud-create command success"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.create_cloud.return_value = {"status": "success"}

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_create("test_cloud")

    mock_shell.connection.api.create_cloud.assert_called_once_with({"cloud": "test_cloud"})
    mock_shell.poutput.assert_called()


def test_cloud_create_no_name(mock_shell):
    """Test cloud-create without providing name"""
    mock_shell.connection.is_connected = True

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_create("")

    mock_shell.perror.assert_called_with("Usage: cloud-create <name>")


def test_cloud_create_forbidden(mock_shell):
    """Test cloud-create when user lacks permission"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.create_cloud.side_effect = Exception("403 Forbidden")

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_create("test_cloud")

    mock_shell.perror.assert_called_with("Error: This command requires admin role")


def test_cloud_delete_success(mock_shell):
    """Test cloud-delete command success"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.remove_cloud.return_value = {"status": "success"}

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_delete("test_cloud")

    mock_shell.connection.api.remove_cloud.assert_called_once_with("test_cloud")
    mock_shell.poutput.assert_called()


def test_cloud_delete_no_name(mock_shell):
    """Test cloud-delete without providing name"""
    mock_shell.connection.is_connected = True

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_delete("")

    mock_shell.perror.assert_called_with("Usage: cloud-delete <name>")


def test_cloud_delete_forbidden(mock_shell):
    """Test cloud-delete when user lacks permission"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.remove_cloud.side_effect = Exception("Forbidden")

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_delete("test_cloud")

    mock_shell.perror.assert_called_with("Error: This command requires admin role")


def test_cloud_delete_not_connected(mock_shell):
    """Test cloud-delete when not connected"""
    mock_shell.connection.is_connected = False

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_delete("test_cloud")

    mock_shell.perror.assert_called_with("Not connected to any server")


def test_cloud_only_cloud01_uses_filter_hosts(mock_shell):
    """cloud01 is the spare pool -- cloud_only should use filter_hosts"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud01"}]
    mock_shell.connection.api.filter_hosts.return_value = [
        {"name": "host01.example.com"},
        {"name": "host02.example.com"},
    ]

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_only("cloud01")

    mock_shell.connection.api.filter_hosts.assert_called_once_with({"cloud": "cloud01"})
    mock_shell.connection.api.get_current_schedules.assert_not_called()
    assert mock_shell.poutput.call_count == 3
    mock_shell.poutput.assert_any_call("  host01.example.com")
    mock_shell.poutput.assert_any_call("  host02.example.com")


def test_cloud_only_cloud01_empty(mock_shell):
    """cloud01 with no hosts should show 'no hosts' message"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud01"}]
    mock_shell.connection.api.filter_hosts.return_value = []

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_only("cloud01")

    mock_shell.poutput.assert_called_with("No hosts currently assigned to cloud01")


def test_cloud_only_other_cloud_uses_schedules(mock_shell):
    """Non-cloud01 clouds should use get_current_schedules"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.filter_clouds.return_value = [{"name": "cloud02"}]
    mock_shell.connection.api.get_current_schedules.return_value = [
        {"host": {"name": "host03.example.com"}},
        {"host": {"name": "host04.example.com"}},
    ]

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_only("cloud02")

    mock_shell.connection.api.get_current_schedules.assert_called_once_with({"cloud": "cloud02"})
    mock_shell.connection.api.filter_hosts.assert_not_called()
    assert mock_shell.poutput.call_count == 3
    mock_shell.poutput.assert_any_call("  host03.example.com")
    mock_shell.poutput.assert_any_call("  host04.example.com")


def test_cloud_only_not_connected(mock_shell):
    """cloud_only should fail when not connected"""
    mock_shell.connection.is_connected = False

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_only("cloud01")

    mock_shell.perror.assert_called_with("Not connected to any server")


def test_cloud_only_no_args(mock_shell):
    """cloud_only with no arguments should show usage"""
    mock_shell.connection.is_connected = True

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_cloud_only("")


def test_os_list_success(mock_shell):
    """Test os-list command with available OS images"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.get_os_list.return_value = [
        {"Id": 1, "Title": "RHEL 9.4", "Release Name": "Plow", "Family": "rhel"},
        {"Id": 2, "Title": "RHEL 8.10", "Release Name": "Ootpa", "Family": "rhel"},
    ]

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_os_list("")

    mock_shell.connection.api.get_os_list.assert_called_once()
    mock_shell.poutput.assert_called_once()


def test_os_list_empty(mock_shell):
    """Test os-list when no OS images available"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.get_os_list.return_value = []

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_os_list("")

    mock_shell.poutput.assert_called_with("No available operating systems")


def test_os_list_not_connected(mock_shell):
    """Test os-list when not connected"""
    mock_shell.connection.is_connected = False

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_os_list("")

    mock_shell.perror.assert_called_with("Not connected to any server")


def test_os_list_api_error(mock_shell):
    """Test os-list when API call fails"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.get_os_list.side_effect = Exception("Connection error")

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_os_list("")

    mock_shell.perror.assert_called()


def test_mod_cloud_with_os(mock_shell):
    """Test mod-cloud with os option"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.get_active_cloud_assignment.return_value = {"id": 42}
    mock_shell.connection.api.update_assignment.return_value = {"status": "success"}
    mock_shell.connection.api.get_os_list.return_value = [
        {"Id": 1, "Title": "RHEL 9.4", "Release Name": "", "Family": "Redhat"},
    ]

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_mod_cloud('cloud05 os "RHEL 9.4"')

    mock_shell.connection.api.update_assignment.assert_called_once_with(42, {"ostype": "RHEL 9.4"})


def test_mod_cloud_with_invalid_os(mock_shell):
    """Test mod-cloud rejects invalid OS and does not call API"""
    mock_shell.connection.is_connected = True
    mock_shell.connection.api.get_active_cloud_assignment.return_value = {"id": 42}
    mock_shell.connection.api.get_os_list.return_value = [
        {"Id": 1, "Title": "RHEL 9.4", "Release Name": "", "Family": "Redhat"},
    ]

    cloud_cmd = CloudCommands(mock_shell)
    cloud_cmd.cmd_mod_cloud('cloud05 os "Windows 11"')

    mock_shell.connection.api.update_assignment.assert_not_called()
    mock_shell.perror.assert_called()
    error_msg = mock_shell.perror.call_args[0][0]
    assert "not found" in error_msg
