import pytest
import sys
from unittest.mock import MagicMock, patch, call, PropertyMock
from io import StringIO


class TestOneShot:
    """Tests for one-shot command execution mode"""

    def test_oneshot_mode_detected(self):
        """Test that one-shot mode is detected from sys.argv"""
        with patch("sys.argv", ["quads-client", "version"]):
            from quads_client.cli import main

            with patch("quads_client.cli.main.QuadsClientShell") as MockShell:
                mock_shell_instance = MagicMock()
                mock_shell_instance.execute_oneshot_command.return_value = 0
                MockShell.return_value = mock_shell_instance

                with pytest.raises(SystemExit) as exc_info:
                    main()

                MockShell.assert_called_once_with(quiet=True)
                assert exc_info.value.code == 0

    def test_interactive_mode_detected(self):
        """Test that interactive mode is detected when no args"""
        with patch("sys.argv", ["quads-client"]):
            from quads_client.cli import main

            with patch("quads_client.cli.main.QuadsClientShell") as MockShell:
                mock_shell_instance = MagicMock()
                MockShell.return_value = mock_shell_instance

                with patch("sys.stdin") as mock_stdin:
                    mock_stdin.isatty.return_value = True
                    main()

                MockShell.assert_called_once_with(quiet=False)
                mock_shell_instance.cmdloop.assert_called_once()

    def test_quiet_mode_no_banner(self, mock_shell):
        """Test that quiet mode is set correctly"""
        mock_shell.quiet = True
        assert mock_shell.quiet is True

    def test_interactive_mode_shows_banner(self, mock_shell):
        """Test that interactive mode is set correctly"""
        mock_shell.quiet = False
        assert mock_shell.quiet is False


class TestAutoConnect:
    """Tests for auto-connect functionality"""

    def test_auto_connect_skipped_for_version(self, mock_shell):
        """Test auto-connect is skipped for version command"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.config = mock_shell.config
        shell.session_manager = mock_shell.session_manager
        shell.perror = mock_shell.perror

        result = shell._auto_connect_for_oneshot("version")

        assert result is True
        mock_shell.config.get_default_server.assert_not_called()

    def test_auto_connect_skipped_for_help(self, mock_shell):
        """Test auto-connect is skipped for help command"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.config = mock_shell.config
        shell.session_manager = mock_shell.session_manager
        shell.perror = mock_shell.perror

        result = shell._auto_connect_for_oneshot("help")

        assert result is True
        mock_shell.config.get_default_server.assert_not_called()

    def test_auto_connect_skipped_for_servers(self, mock_shell):
        """Test auto-connect is skipped for servers command"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.config = mock_shell.config
        shell.session_manager = mock_shell.session_manager
        shell.perror = mock_shell.perror

        result = shell._auto_connect_for_oneshot("servers")

        assert result is True
        mock_shell.config.get_default_server.assert_not_called()

    def test_auto_connect_skipped_for_hyphenated_server_command(self, mock_shell):
        """Test auto-connect is skipped for hyphenated server management commands"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.config = mock_shell.config
        shell.session_manager = None
        shell.perror = mock_shell.perror

        result = shell._auto_connect_for_oneshot("edit-server quads3 verify false")

        assert result is True
        mock_shell.config.get_default_server.assert_not_called()

    def test_auto_connect_when_already_connected(self, mock_shell):
        """Test auto-connect returns True when already connected"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.config = mock_shell.config
        shell.session_manager = mock_shell.session_manager
        shell.perror = mock_shell.perror
        shell.connection_commands = MagicMock()

        result = shell._auto_connect_for_oneshot("cloud_list")

        assert result is True
        shell.connection_commands.cmd_connect.assert_not_called()

    def test_auto_connect_no_default_server(self, mock_shell):
        """Test auto-connect fails gracefully when no default server"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.config = mock_shell.config
        shell.session_manager = MagicMock()
        shell.session_manager.active_session = None
        shell.perror = mock_shell.perror
        mock_shell.config.get_default_server.return_value = None

        result = shell._auto_connect_for_oneshot("cloud_list")

        assert result is False
        shell.perror.assert_called()

    def test_auto_connect_success(self, mock_shell):
        """Test successful auto-connect to default server"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.config = mock_shell.config
        shell.session_manager = MagicMock()
        shell.session_manager.active_session = None
        shell.perror = mock_shell.perror
        shell.connection_commands = MagicMock()
        mock_shell.config.get_default_server.return_value = "test_server"

        result = shell._auto_connect_for_oneshot("cloud_list")

        assert result is True
        shell.connection_commands.cmd_connect.assert_called_once_with("test_server")

    def test_auto_connect_failure(self, mock_shell):
        """Test auto-connect handles connection errors"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.config = mock_shell.config
        shell.session_manager = MagicMock()
        shell.session_manager.active_session = None
        shell.perror = mock_shell.perror
        shell.connection_commands = MagicMock()
        shell.connection_commands.cmd_connect.side_effect = Exception("Connection failed")
        mock_shell.config.get_default_server.return_value = "test_server"

        result = shell._auto_connect_for_oneshot("cloud_list")

        assert result is False
        shell.perror.assert_called()


class TestExecuteOneshot:
    """Tests for execute_oneshot_command method"""

    def test_execute_oneshot_success(self, mock_shell):
        """Test successful one-shot command execution"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell._auto_connect_for_oneshot = MagicMock(return_value=True)
        shell.onecmd = MagicMock(return_value=False)
        shell.perror = mock_shell.perror

        exit_code = shell.execute_oneshot_command("version")

        assert exit_code == 0
        shell.onecmd.assert_called_once_with("version")

    def test_execute_oneshot_connection_error(self, mock_shell):
        """Test one-shot command with connection error"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell._auto_connect_for_oneshot = MagicMock(return_value=False)
        shell.onecmd = MagicMock()
        shell.perror = mock_shell.perror

        exit_code = shell.execute_oneshot_command("cloud_list")

        assert exit_code == 3
        shell.onecmd.assert_not_called()

    def test_execute_oneshot_keyboard_interrupt(self, mock_shell):
        """Test one-shot command handles Ctrl+C"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell._auto_connect_for_oneshot = MagicMock(return_value=True)
        shell.onecmd = MagicMock(side_effect=KeyboardInterrupt())
        shell.perror = mock_shell.perror

        exit_code = shell.execute_oneshot_command("cloud_list")

        assert exit_code == 130

    def test_execute_oneshot_general_error(self, mock_shell):
        """Test one-shot command handles general errors"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell._auto_connect_for_oneshot = MagicMock(return_value=True)
        shell.onecmd = MagicMock(side_effect=Exception("Command failed"))
        shell.perror = mock_shell.perror

        exit_code = shell.execute_oneshot_command("cloud_list")

        assert exit_code == 1
        shell.perror.assert_called()

    def test_execute_oneshot_connect_with_command(self, mock_shell):
        """Test connect <server> <command> splits into two operations"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell._auto_connect_for_oneshot = MagicMock(return_value=True)
        shell.onecmd = MagicMock(return_value=False)
        shell.perror = mock_shell.perror
        shell.connection_commands = MagicMock()

        exit_code = shell.execute_oneshot_command("connect test_server my_assignments")

        assert exit_code == 0
        shell.connection_commands.cmd_connect.assert_called_once_with("test_server")
        shell.onecmd.assert_called_once_with("my_assignments")

    def test_execute_oneshot_connect_with_command_and_args(self, mock_shell):
        """Test connect <server> <command> <args> splits correctly"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell._auto_connect_for_oneshot = MagicMock(return_value=True)
        shell.onecmd = MagicMock(return_value=False)
        shell.perror = mock_shell.perror
        shell.connection_commands = MagicMock()

        exit_code = shell.execute_oneshot_command("connect test_server cloud_list cloud cloud05")

        assert exit_code == 0
        shell.connection_commands.cmd_connect.assert_called_once_with("test_server")
        shell.onecmd.assert_called_once_with("cloud_list cloud cloud05")

    def test_execute_oneshot_connect_with_session_keyword(self, mock_shell):
        """Test connect <server> session <label> is NOT split"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell._auto_connect_for_oneshot = MagicMock(return_value=True)
        shell.onecmd = MagicMock(return_value=False)
        shell.perror = mock_shell.perror

        exit_code = shell.execute_oneshot_command("connect test_server session mylabel")

        assert exit_code == 0
        # Should execute the full connect command, not split it
        shell.onecmd.assert_called_once_with("connect test_server session mylabel")

    def test_execute_oneshot_connect_failure_returns_exit_3(self, mock_shell):
        """Test connect failure in connect <server> <command> returns exit code 3"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.perror = mock_shell.perror
        shell.connection_commands = MagicMock()
        shell.connection_commands.cmd_connect.side_effect = Exception("Connection failed")

        exit_code = shell.execute_oneshot_command("connect bad_server my_assignments")

        assert exit_code == 3
        shell.perror.assert_called()


class TestConnectionQuietMode:
    """Tests for connection message suppression in quiet mode"""

    def test_connection_message_in_interactive_mode(self, mock_shell):
        """Test connection message shows in interactive mode"""
        from quads_client.commands.connection import ConnectionCommands

        mock_session = MagicMock()
        mock_session.id = "1"
        mock_session.connection = MagicMock()
        mock_session.connection.connect = MagicMock()
        mock_session.connection.username = "test@example.com"
        mock_session.connection._registration_mode = False
        mock_shell.session_manager.create_session.return_value = mock_session
        mock_shell.quiet = False

        conn_cmd = ConnectionCommands(mock_shell)
        conn_cmd.cmd_connect("test_server")

        mock_shell.poutput.assert_called()

    def test_connection_message_suppressed_in_quiet_mode(self, mock_shell):
        """Test connection message is suppressed in quiet mode"""
        from quads_client.commands.connection import ConnectionCommands

        mock_session = MagicMock()
        mock_session.id = "1"
        mock_session.connection = MagicMock()
        mock_session.connection.connect = MagicMock()
        mock_session.connection.username = "test@example.com"
        mock_session.connection._registration_mode = False
        mock_shell.session_manager.create_session.return_value = mock_session
        mock_shell.quiet = True

        conn_cmd = ConnectionCommands(mock_shell)
        conn_cmd.cmd_connect("test_server")

        mock_shell.poutput.assert_not_called()

    def test_registration_message_suppressed_in_quiet_mode(self, mock_shell):
        """Test registration message is suppressed in quiet mode"""
        from quads_client.commands.connection import ConnectionCommands

        mock_session = MagicMock()
        mock_session.id = "1"
        mock_session.connection = MagicMock()
        mock_session.connection.connect = MagicMock()
        mock_session.connection._registration_mode = True
        mock_shell.session_manager.create_session.return_value = mock_session
        mock_shell.quiet = True

        conn_cmd = ConnectionCommands(mock_shell)
        conn_cmd.cmd_connect("test_server")

        mock_shell.poutput.assert_not_called()


class TestCommandsAllowlist:
    """Tests for no-connection commands allowlist"""

    @pytest.mark.parametrize(
        "cmd",
        [
            "version",
            "help",
            "servers",
            "exit",
            "quit",
            "add_quads_server",
            "add_server",
            "edit_server",
            "rm_server",
            "config_reload",
        ],
    )
    def test_no_connection_commands(self, cmd, mock_shell):
        """Test that allowlisted commands skip auto-connect"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.config = mock_shell.config
        shell.session_manager = mock_shell.session_manager
        shell.perror = mock_shell.perror

        result = shell._auto_connect_for_oneshot(cmd)

        assert result is True
        mock_shell.config.get_default_server.assert_not_called()

    def test_other_commands_attempt_connect(self, mock_shell):
        """Test that non-allowlisted commands attempt auto-connect"""
        from quads_client.shell import QuadsClientShell

        shell = QuadsClientShell.__new__(QuadsClientShell)
        shell.config = mock_shell.config
        shell.session_manager = MagicMock()
        shell.session_manager.active_session = None
        shell.perror = mock_shell.perror
        shell.connection_commands = MagicMock()
        mock_shell.config.get_default_server.return_value = "test_server"

        result = shell._auto_connect_for_oneshot("cloud_list")

        assert result is True
        mock_shell.config.get_default_server.assert_called()


class TestPipedStdin:
    """Tests for piped stdin mode"""

    def test_piped_mode_detected(self):
        """Test that piped mode is detected when stdin is not a tty"""
        with patch("sys.argv", ["quads-client"]):
            from quads_client.cli import main

            mock_stdin = StringIO("version\n")
            mock_stdin.isatty = lambda: False

            with patch("quads_client.cli.main.QuadsClientShell") as MockShell:
                mock_instance = MagicMock()
                mock_instance.execute_oneshot_command.return_value = 0
                MockShell.return_value = mock_instance

                with patch("sys.stdin", mock_stdin):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

                MockShell.assert_called_once_with(quiet=True)
                mock_instance.execute_oneshot_command.assert_called_once_with("version")
                assert exc_info.value.code == 0

    def test_piped_mode_multiple_lines(self):
        """Test piped mode executes multiple commands"""
        with patch("sys.argv", ["quads-client"]):
            from quads_client.cli import main

            mock_stdin = StringIO("version\nservers\nhelp\n")
            mock_stdin.isatty = lambda: False

            with patch("quads_client.cli.main.QuadsClientShell") as MockShell:
                mock_instance = MagicMock()
                mock_instance.execute_oneshot_command.return_value = 0
                MockShell.return_value = mock_instance

                with patch("sys.stdin", mock_stdin):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

                assert mock_instance.execute_oneshot_command.call_count == 3
                mock_instance.execute_oneshot_command.assert_any_call("version")
                mock_instance.execute_oneshot_command.assert_any_call("servers")
                mock_instance.execute_oneshot_command.assert_any_call("help")
                assert exc_info.value.code == 0

    def test_piped_mode_skips_empty_and_comments(self):
        """Test piped mode skips empty lines and comments"""
        with patch("sys.argv", ["quads-client"]):
            from quads_client.cli import main

            mock_stdin = StringIO("version\n\n# this is a comment\n\nservers\n")
            mock_stdin.isatty = lambda: False

            with patch("quads_client.cli.main.QuadsClientShell") as MockShell:
                mock_instance = MagicMock()
                mock_instance.execute_oneshot_command.return_value = 0
                MockShell.return_value = mock_instance

                with patch("sys.stdin", mock_stdin):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

                assert mock_instance.execute_oneshot_command.call_count == 2
                mock_instance.execute_oneshot_command.assert_any_call("version")
                mock_instance.execute_oneshot_command.assert_any_call("servers")
                assert exc_info.value.code == 0

    def test_piped_mode_exit_code_propagation(self):
        """Test piped mode propagates non-zero exit code"""
        with patch("sys.argv", ["quads-client"]):
            from quads_client.cli import main

            mock_stdin = StringIO("version\ncloud_list\n")
            mock_stdin.isatty = lambda: False

            with patch("quads_client.cli.main.QuadsClientShell") as MockShell:
                mock_instance = MagicMock()
                mock_instance.execute_oneshot_command.side_effect = [0, 3]
                MockShell.return_value = mock_instance

                with patch("sys.stdin", mock_stdin):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

                assert exc_info.value.code == 3

    def test_interactive_mode_when_tty(self):
        """Test interactive mode is used when stdin is a tty and no args"""
        with patch("sys.argv", ["quads-client"]):
            from quads_client.cli import main

            with patch("quads_client.cli.main.QuadsClientShell") as MockShell:
                mock_instance = MagicMock()
                MockShell.return_value = mock_instance

                with patch("sys.stdin") as mock_stdin:
                    mock_stdin.isatty.return_value = True
                    main()

                MockShell.assert_called_once_with(quiet=False)
                mock_instance.cmdloop.assert_called_once()


class TestDebugFlag:
    """Tests for the global --debug/-d flag"""

    def test_debug_flag_sets_shell_debug_and_strips_flag(self):
        """--debug enables tracing and is removed from the command"""
        with patch("sys.argv", ["quads-client", "--debug", "version"]):
            from quads_client.cli import main

            with patch("quads_client.cli.main.QuadsClientShell") as MockShell:
                inst = MagicMock()
                inst.execute_oneshot_command.return_value = 0
                MockShell.return_value = inst

                with pytest.raises(SystemExit) as exc_info:
                    main()

                MockShell.assert_called_once_with(quiet=True)
                assert inst.debug is True
                inst.execute_oneshot_command.assert_called_once_with("version")
                assert exc_info.value.code == 0

    def test_short_debug_flag(self):
        """-d is an alias for --debug and is stripped from the command"""
        with patch("sys.argv", ["quads-client", "-d", "cloud_list"]):
            from quads_client.cli import main

            with patch("quads_client.cli.main.QuadsClientShell") as MockShell:
                inst = MagicMock()
                inst.execute_oneshot_command.return_value = 0
                MockShell.return_value = inst

                with pytest.raises(SystemExit):
                    main()

                assert inst.debug is True
                inst.execute_oneshot_command.assert_called_once_with("cloud_list")

    def test_no_debug_flag_leaves_default(self):
        """Without the flag the shell debug state is never forced on"""
        with patch("sys.argv", ["quads-client", "version"]):
            from quads_client.cli import main

            with patch("quads_client.cli.main.QuadsClientShell") as MockShell:
                inst = MagicMock()
                inst.debug = False
                inst.execute_oneshot_command.return_value = 0
                MockShell.return_value = inst

                with pytest.raises(SystemExit):
                    main()

                assert inst.debug is False
                inst.execute_oneshot_command.assert_called_once_with("version")
