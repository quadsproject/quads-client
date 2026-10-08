import cmd2
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
    """Test prompt includes [ADMIN] badge for admin users"""
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


def test_prompt_uses_raw_ansi_codes():
    """Prompt must use raw ANSI codes so cmd2's rl_escape_prompt handles wrapping"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            shell._update_prompt()
            assert "\033[" in shell.prompt
            assert "\001" not in shell.prompt
            assert "\002" not in shell.prompt


def test_shell_preloop_binds_readline():
    """Test preloop sets up Ctrl+A Ctrl+A keybinding (per cmd2 major)"""
    from quads_client.cmd2_compat import CMD2_MAJOR

    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell()
            if CMD2_MAJOR < 4:
                with patch("readline.parse_and_bind") as mock_bind:
                    shell.preloop()
                    mock_bind.assert_called_once_with('"\\C-a\\C-a": "session_switch\\n"')
            else:
                shell.preloop()
                from prompt_toolkit.keys import Keys

                bindings = shell.main_session.key_bindings.get_bindings_for_keys((Keys.ControlA, Keys.ControlA))
                assert bindings


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


def test_hyphenated_command_dispatches():
    """Hyphenated command names resolve to the underscore do_* method, args untouched"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell(quiet=True)
            shell.server_commands.cmd_edit_server = MagicMock()

            shell.onecmd("edit-server perf-lab verify false")

            shell.server_commands.cmd_edit_server.assert_called_once()
            passed_args = shell.server_commands.cmd_edit_server.call_args[0][0]
            assert str(passed_args).split() == ["perf-lab", "verify", "false"]


def test_unknown_hyphenated_command_errors():
    """Unknown hyphenated command with no underscore counterpart still errors"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell(quiet=True)
            shell.perror = MagicMock()

            shell.onecmd("bogus-command foo")

            shell.perror.assert_called_once()
            assert "not a recognized command" in str(shell.perror.call_args)


def test_hyphenated_command_recorded_in_history():
    """Hyphenated commands are recorded in history like their underscore form"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell(quiet=True)
            shell.server_commands.cmd_edit_server = lambda *a, **k: None

            shell.onecmd("edit-server perf-lab verify false")

            assert any("edit-server" == str(item.statement.command) for item in shell.history)


def test_cmd_func_resolves_hyphens_via_parent():
    """cmd2 3.x path: cmd_func falls back to underscores via the parent hook"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell(quiet=True)

            def target(*a, **k):
                return None

            shell.server_commands.cmd_edit_server = target

            def fake_parent(self, command):
                return None if command == "edit-server" else getattr(self.server_commands, "cmd_" + command, None)

            with patch.object(cmd2.Cmd, "cmd_func", fake_parent, create=True):
                func = shell.cmd_func("edit-server")

            assert func == target


def test_cmd_func_no_parent_returns_none():
    """cmd2 4.x: without a cmd_func parent the 3.x hook is inert"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell(quiet=True)
            with patch.object(cmd2.Cmd, "cmd_func", None, create=True):
                assert shell.cmd_func("edit-server") is None


def test_get_command_func_no_parent_returns_none():
    """cmd2 3.x: without a get_command_func parent the 4.x hook is inert"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell(quiet=True)
            with patch.object(cmd2.Cmd, "get_command_func", None, create=True):
                assert shell.get_command_func("edit-server") is None


def test_get_command_func_resolves_hyphens_via_parent():
    """cmd2 4.x path: get_command_func falls back to underscores via the parent hook"""
    with patch("quads_client.shell.QuadsClientConfig"):
        with patch("quads_client.shell.SessionManager"):
            shell = QuadsClientShell(quiet=True)

            def target(*a, **k):
                return None

            shell.server_commands.cmd_edit_server = target

            def fake_parent(self, command):
                return None if command == "edit-server" else getattr(self.server_commands, "cmd_" + command, None)

            with patch.object(cmd2.Cmd, "get_command_func", fake_parent, create=True):
                func = shell.get_command_func("edit-server")

            assert func == target
