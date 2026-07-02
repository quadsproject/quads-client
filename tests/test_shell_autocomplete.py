import pytest
from unittest.mock import MagicMock, patch
from quads_client.shell import QuadsClientShell


def test_complete_connect_all_servers():
    """Test autocomplete for connect command shows all servers"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # Mock active connection
            mock_conn = MagicMock()
            mock_conn.get_available_servers.return_value = ["server1", "server2", "server3"]
            shell.session_manager.active_connection = mock_conn

            completions = shell.complete_connect("", "connect ", 8, 8)

            assert completions == ["server1", "server2", "server3"]


def test_complete_connect_filtered():
    """Test autocomplete for connect command filters by prefix"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # Mock active connection
            mock_conn = MagicMock()
            mock_conn.get_available_servers.return_value = ["server1", "server2", "staging"]
            shell.session_manager.active_connection = mock_conn

            completions = shell.complete_connect("ser", "connect ser", 8, 11)

            assert completions == ["server1", "server2"]


def test_complete_connect_no_connection_with_config():
    """Test autocomplete when not connected falls back to config servers"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # No active connection
            shell.session_manager.active_connection = None
            # But config has servers
            mock_config = MagicMock()
            mock_config.get_all_servers.return_value = {"server1": {}, "server2": {}}
            shell.config = mock_config

            completions = shell.complete_connect("", "connect ", 8, 8)

            assert sorted(completions) == ["server1", "server2"]


def test_complete_connect_no_connection_no_config():
    """Test autocomplete when not connected and no config returns empty"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # No active connection
            shell.session_manager.active_connection = None
            shell.config = None

            completions = shell.complete_connect("", "connect ", 8, 8)

            assert completions == []


def test_complete_connect_no_connection_filtered():
    """Test autocomplete when not connected filters by prefix from config"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            shell.session_manager.active_connection = None
            mock_config = MagicMock()
            mock_config.get_all_servers.return_value = {"server1": {}, "staging": {}, "server2": {}}
            shell.config = mock_config

            completions = shell.complete_connect("ser", "connect ser", 8, 11)

            assert sorted(completions) == ["server1", "server2"]


def test_complete_connect_exact_match():
    """Test autocomplete with exact server prefix"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # Mock active connection
            mock_conn = MagicMock()
            mock_conn.get_available_servers.return_value = ["production", "prod-backup"]
            shell.session_manager.active_connection = mock_conn

            completions = shell.complete_connect("prod", "connect prod", 8, 12)

            assert "production" in completions
            assert "prod-backup" in completions


def test_complete_connect_no_match():
    """Test autocomplete with no matching servers"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # Mock active connection
            mock_conn = MagicMock()
            mock_conn.get_available_servers.return_value = ["server1", "server2"]
            shell.session_manager.active_connection = mock_conn

            completions = shell.complete_connect("xyz", "connect xyz", 8, 11)

            assert completions == []


def test_complete_ls_available_all_keywords():
    """Test autocomplete for ls_available shows all filter keywords"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()

            completions = shell.complete_ls_available("", "ls_available ", 13, 13)

            assert "model" in completions
            assert "ram" in completions
            assert "gpu-vendor" in completions
            assert "gpu-product" in completions
            assert "disk-type" in completions
            assert "disk-size" in completions
            assert "disk-count" in completions
            assert "interfaces" in completions
            assert "nic-vendor" in completions
            assert "nic-speed" in completions
            assert "start" in completions
            assert "end" in completions


def test_complete_ls_available_filtered():
    """Test autocomplete for ls_available filters by prefix"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()

            completions = shell.complete_ls_available("disk", "ls_available disk", 13, 17)

            assert "disk-type" in completions
            assert "disk-size" in completions
            assert "disk-count" in completions
            assert "model" not in completions


def test_complete_ls_available_no_match():
    """Test autocomplete for ls_available with no matching keywords"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()

            completions = shell.complete_ls_available("xyz", "ls_available xyz", 13, 16)

            assert completions == []
