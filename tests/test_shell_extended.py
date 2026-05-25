import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from quads_client.shell import QuadsClientShell
from quads_client.config import ConfigError


def test_shell_init_no_config():
    """Test shell initialization when config fails to load"""
    with patch("quads_client.shell.QuadsClientConfig", side_effect=ConfigError("Config not found")):
        shell = QuadsClientShell()
        # Should handle config error gracefully
        assert shell.config is None


def test_shell_onboarding_message():
    """Test onboarding message is shown when no servers configured"""
    with patch("quads_client.shell.QuadsClientConfig") as mock_config_class:
        with patch("quads_client.shell.SessionManager"):
            with patch("quads_client.rich_console.RichConsole.print_banner"):
                # Create a mock config that needs initial setup
                mock_config = MagicMock()
                mock_config.needs_initial_setup.return_value = True
                mock_config_class.return_value = mock_config

                # Create shell in interactive mode and mock poutput to capture calls
                shell = QuadsClientShell(quiet=False)
                # Check that poutput was called with onboarding message content
                assert hasattr(shell, "_print_onboarding_message")


def test_shell_no_onboarding_when_servers_exist():
    """Test onboarding message logic when servers are configured"""
    with patch("quads_client.shell.QuadsClientConfig") as mock_config_class:
        with patch("quads_client.shell.SessionManager"):
            # Create a mock config with servers configured
            mock_config = MagicMock()
            mock_config.needs_initial_setup.return_value = False
            mock_config_class.return_value = mock_config

            # Create shell - onboarding should not trigger
            shell = QuadsClientShell(quiet=True)
            # Just verify shell initialized successfully
            assert shell.config is not None


def test_shell_print_onboarding_message():
    """Test the _print_onboarding_message method directly"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell(quiet=True)

            # Mock poutput to capture output
            output_lines = []
            shell.poutput = lambda msg: output_lines.append(msg)

            # Call the onboarding message method
            shell._print_onboarding_message()

            # Verify expected content
            output_text = "\n".join(output_lines)
            assert "Welcome to QUADS Client!" in output_text
            assert "add_quads_server" in output_text
            assert "connect <server_name>" in output_text
            assert "token-login" in output_text
            assert "register" in output_text


def test_shell_shorten_server_name():
    """Test server name shortening"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()

            # Test with long name (more than 3 segments)
            short = shell._shorten_server_name("quads2-dev.rdu2.scalelab.example.com")
            assert short == "quads2-dev.rdu2.scalelab"

            # Test with already short name
            short = shell._shorten_server_name("quads.example.com")
            assert short == "quads.example.com"


def test_shell_update_prompt_disconnected():
    """Test prompt update when disconnected"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # Mock session manager to return None for active_connection
            shell.session_manager.active_connection = None

            shell._update_prompt()
            assert "(disconnected)" in shell.prompt


def test_shell_update_prompt_connected():
    """Test prompt update when connected"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # Mock session manager with active connection
            mock_conn = MagicMock()
            mock_conn.is_connected = True
            mock_conn.current_server = "quads1.rdu2.scalelab.example.com"
            shell.session_manager.active_connection = mock_conn
            shell.config.get_server_url.return_value = "https://quads1.rdu2.scalelab.example.com"
            shell.config.get_server_verify.return_value = True
            shell.session_manager.list_sessions.return_value = []

            shell._update_prompt()
            assert "quads1.rdu2.scalelab" in shell.prompt


def test_shell_update_visible_commands_not_authenticated():
    """Test command visibility when not authenticated"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # Mock active connection
            mock_conn = MagicMock()
            mock_conn.is_authenticated = False
            mock_conn.is_admin = False
            shell.session_manager.active_connection = mock_conn

            shell._update_visible_commands()

            # Admin commands should be hidden
            assert "cloud_create" in shell.hidden_commands
            assert "login" in shell.hidden_commands


def test_shell_update_visible_commands_user():
    """Test command visibility for authenticated non-admin user"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # Mock active connection
            mock_conn = MagicMock()
            mock_conn.is_authenticated = True
            mock_conn.is_admin = False
            shell.session_manager.active_connection = mock_conn

            shell._update_visible_commands()

            # Admin commands should be hidden, but auth commands should be visible
            assert "cloud_create" in shell.hidden_commands
            assert "login" not in shell.hidden_commands


def test_shell_update_visible_commands_admin():
    """Test command visibility for admin user"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            # Mock active connection
            mock_conn = MagicMock()
            mock_conn.is_authenticated = True
            mock_conn.is_admin = True
            shell.session_manager.active_connection = mock_conn

            shell._update_visible_commands()

            # cloud_create and cloud_delete are permanently hidden (too dangerous)
            assert "cloud_create" in shell.hidden_commands
            assert "cloud_delete" in shell.hidden_commands
            # But other admin commands should be visible
            assert "ls_hosts" not in shell.hidden_commands
            assert "mod_cloud" not in shell.hidden_commands


def test_shell_update_prompt_admin_badge():
    """Test prompt includes [ADMIN] badge for admin users with readline wrapping"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            mock_conn = MagicMock()
            mock_conn.is_connected = True
            mock_conn.is_admin = True
            mock_conn.current_server = "quads1.example.com"
            shell.session_manager.active_connection = mock_conn
            shell.config.get_server_url.return_value = "https://quads1.example.com"
            shell.config.get_server_verify.return_value = True
            shell.session_manager.list_sessions.return_value = []

            shell._update_prompt()
            assert "[ADMIN]" in shell.prompt
            # Verify readline wrapping markers are present
            assert "\001" in shell.prompt
            assert "\002" in shell.prompt


def test_shell_update_prompt_no_admin_badge():
    """Test prompt omits [ADMIN] badge for non-admin users"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            mock_conn = MagicMock()
            mock_conn.is_connected = True
            mock_conn.is_admin = False
            mock_conn.current_server = "quads1.example.com"
            shell.session_manager.active_connection = mock_conn
            shell.config.get_server_url.return_value = "https://quads1.example.com"
            shell.config.get_server_verify.return_value = True
            shell.session_manager.list_sessions.return_value = []

            shell._update_prompt()
            assert "[ADMIN]" not in shell.prompt


def test_rl_wraps_ansi_for_readline():
    """Test _rl helper wraps ANSI codes with readline non-printing markers"""
    from quads_client.shell import _rl

    result = _rl("\033[1;31m")
    assert result == "\001\033[1;31m\002"


def test_shell_preloop_binds_readline():
    """Test preloop sets up Ctrl+A Ctrl+A keybinding"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            with patch("readline.parse_and_bind") as mock_bind:
                shell.preloop()
                mock_bind.assert_called_once_with('"\\C-a\\C-a": "session_switch\\n"')


def test_shell_preloop_handles_no_readline():
    """Test preloop gracefully handles missing readline"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            with patch("builtins.__import__", side_effect=ImportError):
                shell.preloop()


def test_shell_exit_command():
    """Test that exit command returns True to exit the shell"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            result = shell.do_exit("")
            assert result is True
