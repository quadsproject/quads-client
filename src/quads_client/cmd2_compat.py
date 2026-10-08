"""Compatibility helpers so quads-client runs on cmd2 3.x and 4.x.

cmd2 4.x replaced GNU Readline with prompt-toolkit for the REPL (see the
upgrade guide at https://cmd2.readthedocs.io/en/latest/upgrades/). The
rest of the API surface this client uses - history kwargs,
basic_complete/path_complete, statement attribution, and default() - is
stable across those majors: the full test suite passes on both cmd2 3.5.1
and 4.2.4. The supported floor is cmd2 3.0 (3.x and 4.x are the tested,
supported majors).

The one interactive behavior that differs is the Ctrl-A Ctrl-A shortcut
for session_switch: on cmd2 3.x it is a readline macro, on cmd2 4.x it has
to be registered as a prompt-toolkit key binding.
"""

from __future__ import annotations

import cmd2

# Major version of the installed cmd2, e.g. 2, 3, or 4.
CMD2_MAJOR = int(cmd2.__version__.split(".", 1)[0])


def bind_session_switch(shell: object) -> None:
    """Bind Ctrl-A Ctrl-A to the session_switch command.

    On cmd2 < 4 the REPL reads input through GNU Readline, so the classic
    parse_and_bind macro keeps working. On cmd2 >= 4 the REPL reads input
    through prompt-toolkit, so the macro does nothing there: register the
    same double key on the session instead and submit the command, exactly
    like the readline macro did.
    """
    if CMD2_MAJOR < 4:
        try:
            import readline

            readline.parse_and_bind('"\\C-a\\C-a": "session_switch\\n"')
        except (ImportError, OSError):
            pass
        return

    session = getattr(shell, "main_session", None)
    key_bindings = getattr(session, "key_bindings", None)
    if key_bindings is None:
        return

    @key_bindings.add("c-a", "c-a")
    def _switch_session(event) -> None:
        event.current_buffer.insert_text("session_switch")
        event.current_buffer.validate_and_handle()
