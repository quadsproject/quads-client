# CHANGELOG


## v0.8.7 (2026-07-02)

### Bug Fixes

- Add additional test coverage
  ([`bfbe21a`](https://github.com/quadsproject/quads-client/commit/bfbe21a01215f2f2ffd3816335e946e796ac8238))

- Add nic-vendor and nic-speed filters to CLI.
  ([`71e910b`](https://github.com/quadsproject/quads-client/commit/71e910ba040b289598615df3e23c8f088faaa2ff))

- Add rest of hw filters and mappings.
  ([`1d3a44d`](https://github.com/quadsproject/quads-client/commit/1d3a44db2c165a91e76cc75c869e55fa1bd06c24))

- arg_parser.py -- Added 8 new filter keywords (disk-type, disk-size, disk-count, gpu-vendor,
  gpu-product, interfaces, nic-vendor, nic-speed) to the SSM schedule parser: result dict,
  description terminator list, and elif parsing branches - user.py -- Added 8 filter mappings in
  cmd_schedule() count mode, passing correct API keys to filter_available() (e.g., disks.disk_type,
  processors.vendor, interfaces.speed__gte) - shell.py -- Added 8 new keywords to
  complete_schedule() tab completion - gui/views/schedule.py -- Added 5 reverse-mappings in the
  command builder so GUI advanced filters pass through to the CLI schedule command -
  test_arg_parser.py -- 11 new tests (8 individual filters + combined + description terminator) -
  test_commands_unified_schedule.py -- 4 new tests verifying filter_available receives correct API
  filter dicts

Assisted-by: claude

- Add Tab completion for ls-available and sched.
  ([`776837c`](https://github.com/quadsproject/quads-client/commit/776837c3d6d6bbbfa5bb66c102709d10953f9aaf))

- Fix black formatting
  ([`b50ee97`](https://github.com/quadsproject/quads-client/commit/b50ee97ef5576e204292ce76fdd0f3630fb580d1))

- Has-gpu and gpu-product/vendor
  ([`0d3c69e`](https://github.com/quadsproject/quads-client/commit/0d3c69e94bf2fa1830bfdfabeaee077482aa1f00))

* We weren't correctly filtering GPU product and vendor. * Has GPU in quads-client-gui not filtering
  correctly.

### Chores

- Update RPM spec version to 0.8.6
  ([`cafafbe`](https://github.com/quadsproject/quads-client/commit/cafafbe12d29f3c63c44a77764ea0bc35c42ac1b))


## v0.8.6 (2026-06-27)

### Bug Fixes

- Remove some dead code paths in track.py
  ([`f3ddfd9`](https://github.com/quadsproject/quads-client/commit/f3ddfd904a58a65a415f72c56d08babd161834b6))

### Chores

- Update RPM spec version to 0.8.5
  ([`57a33ba`](https://github.com/quadsproject/quads-client/commit/57a33ba92ccb7ddc9851d2cc0002ca9f3b7ae722))


## v0.8.5 (2026-06-26)

### Bug Fixes

- Add more resilience to tracking move stages.
  ([`4c783cc`](https://github.com/quadsproject/quads-client/commit/4c783cc802dbcc35e4891adde33d7ec5e0abc3fb))

* Add further resilience to CLI activity tracking.

related-to: https://github.com/quadsproject/quads/issues/692

fixes: https://github.com/quadsproject/quads-client/issues/141

### Chores

- Update image
  ([`a514671`](https://github.com/quadsproject/quads-client/commit/a514671ebb6b539b08fcf0c39cb4e30ca0b5f20a))

- Update RPM spec version to 0.8.4
  ([`9ec3fa4`](https://github.com/quadsproject/quads-client/commit/9ec3fa4c55fedebb5411ddbc4d4ada3f3940f1df))


## v0.8.4 (2026-06-10)

### Bug Fixes

- Simplify startup CLI banner
  ([`39750d5`](https://github.com/quadsproject/quads-client/commit/39750d501f729232ee8d196f9cdc355056478afb))

### Chores

- Update RPM spec version to 0.8.3
  ([`86d4bd8`](https://github.com/quadsproject/quads-client/commit/86d4bd8a6917080b44f2a413f8790e3da79e3a24))


## v0.8.3 (2026-06-10)

### Bug Fixes

- Default_server should be set by CLI onboarding.
  ([`c472e81`](https://github.com/quadsproject/quads-client/commit/c472e810d25d488bf388005588857b709d9c01fc))

### Chores

- Update onboard docs
  ([`7b1f927`](https://github.com/quadsproject/quads-client/commit/7b1f9274d82c8b72a848bed1c387a289e24d15d4))

- Update RPM spec version to 0.8.2
  ([`9ef98a1`](https://github.com/quadsproject/quads-client/commit/9ef98a199c2dc7175f26739bbd20b4501f966dfe))


## v0.8.2 (2026-06-09)

### Bug Fixes

- Clear previous tracking CLI elements.
  ([`4de998e`](https://github.com/quadsproject/quads-client/commit/4de998e06d543266d3117340dfefe1d5987ce35e))

When transitioning from the "waiting room" pre-move to actual polling/status API move status we
  inherently leave the previous views on the screen.

### Chores

- Update RPM spec version to 0.8.1
  ([`012a978`](https://github.com/quadsproject/quads-client/commit/012a978348aad419ddccbd0fbdda75cfb928d422))


## v0.8.1 (2026-06-09)

### Bug Fixes

- Add proper awareness for awaiting_move
  ([`3ab4575`](https://github.com/quadsproject/quads-client/commit/3ab4575db7a84642677545376df9350839c07b47))

This was done in CLI but not everywhere and not done in the GUI.

- Refactor for interim move statuses.
  ([`187747d`](https://github.com/quadsproject/quads-client/commit/187747d77c5205a5381adfed2d872856ccec0487))

- _show_pending_moves refactored into _get_pending_moves (returns the list instead of printing) -
  _wait_for_active_all and _wait_for_active_single -- new methods that show a live Rich table of
  scheduled moves, poll every 10s, and return active move data once the server's move cycle starts
  (or None on Ctrl+C) - _build_pending_table -- builds the Rich table with caption showing "Last
  check: HH:MM:SS | Refresh: 10s | Ctrl+C to stop" - Both _track_single and _track_all now: get
  pending -> wait for active (live polling) -> seamlessly transition into the existing 5s live
  tracking loop

Assisted-by: claude

### Chores

- Fix test coverage
  ([`9806cc0`](https://github.com/quadsproject/quads-client/commit/9806cc0704ba761244309c9bf96625c6054bbd2e))

- Update doc descriptions
  ([`630b423`](https://github.com/quadsproject/quads-client/commit/630b42369959bf4b71d1f2c3dbb4488936b03b3c))

- Update RPM spec version to 0.8.0
  ([`a3b022f`](https://github.com/quadsproject/quads-client/commit/a3b022f507a467236be39d0103f668f8d83df530))


## v0.8.0 (2026-06-09)

### Bug Fixes

- Add additional code surface.
  ([`0266d56`](https://github.com/quadsproject/quads-client/commit/0266d56e44c38e1e0c98b83e6e964970b3a2350e))

### Chores

- Update RPM spec version to 0.7.2
  ([`d751d22`](https://github.com/quadsproject/quads-client/commit/d751d22faed57a7e74da2e26f2649e40c8d31a78))

### Features

- Add ack for future actions, docs.
  ([`f64132d`](https://github.com/quadsproject/quads-client/commit/f64132d00c31dc406e86174e529c0269ec10b6e5))

fixes: https://github.com/quadsproject/quads-client/issues/125

- Add activity and tracking to CLI.
  ([`b43a6aa`](https://github.com/quadsproject/quads-client/commit/b43a6aaa01ae01ddaf1b9bd7370f62d38698cc9d))

Feature A: track command (src/quads_client/commands/track.py) - track -- live-refreshing Rich table
  of all active moves (5s poll) - track hostname -- single-host detailed tracking - track cloud03 --
  filter by target cloud - Ctrl+C exits cleanly, auto-exits when all moves complete or fail

Feature B: Prompt activity indicator (shell.py) - postcmd() hook refreshes the prompt after every
  command - _get_activity_indicator() checks for active moves with 30s cache TTL - Shows ⚡ in yellow
  between server name and admin badge when moves are active

Feature C: activity command (src/quads_client/commands/moves.py) - One-shot cloud-grouped summary
  with icons, stage names, and progress - Format: "Active Operations: N move(s) across M cloud(s)"
  with per-cloud host listings

Assisted-by: claude


## v0.7.2 (2026-06-09)

### Bug Fixes

- Failed moves don't get tracked, fix my_hosts view
  ([`f21647c`](https://github.com/quadsproject/quads-client/commit/f21647c73c7135735ffadd7b6e5142702edc1f97))

related-to: https://github.com/quadsproject/quads/issues/663

- Ui progress bar/views.
  ([`6b36c4a`](https://github.com/quadsproject/quads-client/commit/6b36c4a26b280d488fde7cd92cf662728add6d3e))

* Ensure views were reflecting move status * Fix stale rendering.

- Use move_status everywhere.
  ([`cd985d1`](https://github.com/quadsproject/quads-client/commit/cd985d1a4faef465382f1b3b4e749fc1a5a65922))

We were not properly using move_status for move stage descriptions in a few places, namely the GUI.

Assisted-by: claude

### Chores

- Fix tests
  ([`db7bc9c`](https://github.com/quadsproject/quads-client/commit/db7bc9c684758cfbba9974a1457675b5f9ee3a8f))

- Update RPM spec version to 0.7.1
  ([`6c34e59`](https://github.com/quadsproject/quads-client/commit/6c34e596d7626c98042c3104fd194424bf658490))


## v0.7.1 (2026-06-08)

### Bug Fixes

- Handle edge case for old QUADS servers.
  ([`a24744c`](https://github.com/quadsproject/quads-client/commit/a24744c0d6b98e7e62a90199a3883f7fcf413aa3))

### Chores

- Update RPM spec version to 0.7.0
  ([`ad4e469`](https://github.com/quadsproject/quads-client/commit/ad4e469629e74e4151051301aa8d1fabc57b8072))


## v0.7.0 (2026-06-08)

### Bug Fixes

- Re-align with MoveStatus enum refactor
  ([`44d0be6`](https://github.com/quadsproject/quads-client/commit/44d0be6487ad8014d1ee86ceb66c48659ee44f77))

- Refactor for dropping MoveProgress DB structure
  ([`2442bc7`](https://github.com/quadsproject/quads-client/commit/2442bc7208aa2ff1815f75fe1b542d22af27e995))

- Thread Safety on GUI Teardown
  ([`2a2013b`](https://github.com/quadsproject/quads-client/commit/2a2013be380da2a7cbbc9b706447bf96db72afa7))

### Chores

- Fix test linting
  ([`d34f91b`](https://github.com/quadsproject/quads-client/commit/d34f91bf5bc98488a7cb6e324b60eee54a177e1b))

- Update docs
  ([`88c93d4`](https://github.com/quadsproject/quads-client/commit/88c93d4d0f71b0c6963bb33f787c612dc81258ca))

- Update RPM spec version to 0.6.0
  ([`75a7caf`](https://github.com/quadsproject/quads-client/commit/75a7caff1b8905bf87afc463c0a131f8b001c85f))

### Features

- Add support for polling/status API.
  ([`0e650d1`](https://github.com/quadsproject/quads-client/commit/0e650d1d1f37c32c3cf42d29733782d1fabb10a1))

related-to: https://github.com/quadsproject/quads/issues/661


## v0.6.0 (2026-05-25)

### Bug Fixes

- Don't call api.login() when using api_token.
  ([`2cf6807`](https://github.com/quadsproject/quads-client/commit/2cf68078fcf51e20c4c462422c71a07b70751c0d))

Removed api.login() call from the connect() token path. The flow is now: 1.
  QuadsApi.__init__(api_token=...) sets Bearer header on session 2. api.get_version() verifies
  server is reachable 3. _detect_role_from_api() calls /users/{email} to get role

- Regressions and login() usage
  ([`b9ef915`](https://github.com/quadsproject/quads-client/commit/b9ef9152b22ba30eed9ded1a74aa7ff36623813f))

### Chores

- Fix codecov coverage complaints
  ([`ffa3b86`](https://github.com/quadsproject/quads-client/commit/ffa3b8629f6357693b86b52b9b8c3570eacd81e7))

Assisted-by: claude

- Fix tests
  ([`5f50d62`](https://github.com/quadsproject/quads-client/commit/5f50d624736bf52d5cb1b1bbabd73b9193aa80f1))

Assisted-by: claude

- Update docs for token mgmt
  ([`a69ce62`](https://github.com/quadsproject/quads-client/commit/a69ce6262957f5a72af90a5de0efa2d09c0a7a48))

- Update RPM spec version to 0.5.4
  ([`bb545a5`](https://github.com/quadsproject/quads-client/commit/bb545a5f70ecda0aebf8087ca3aff86ce9fa16ff))

### Features

- Support qat_ SSO tokens for QUADS 3.x
  ([`19a4732`](https://github.com/quadsproject/quads-client/commit/19a4732ca748d336f03959cbbb5bc9e6e0f2e94d))

* Prioritize permanent SSO Token workflows (preferred) * Still support legacy workflows * Properly
  support 40x API returns when admins have strict auth settings enabled disallowing legacy / anon
  register/login workflows.


## v0.5.4 (2026-05-16)

### Bug Fixes

- Missing UI buttons, use unicode blocks for compat
  ([`a72ffbf`](https://github.com/quadsproject/quads-client/commit/a72ffbfb4e86ac93c7fa50827faaca573dfe6fe0))

### Chores

- Docs update
  ([`14377a7`](https://github.com/quadsproject/quads-client/commit/14377a7a48813c948146fac39eb4640a931fe762))

- Update RPM spec version to 0.5.3
  ([`f147b1c`](https://github.com/quadsproject/quads-client/commit/f147b1c38057ba3765f48d6f0f0b6c0a55d46975))


## v0.5.3 (2026-05-16)

### Bug Fixes

- Cli session title caching, session hotkeys
  ([`ea461d9`](https://github.com/quadsproject/quads-client/commit/ea461d9fc9a970d970a80a670c170f32c5e5b608))

fix: CLI session title caching, session hotkeys

- Cli session title caching, session hotkeys
  ([`0bf618e`](https://github.com/quadsproject/quads-client/commit/0bf618e65b2453d9039abb85b92e665638a7e930))

* Fix session title caching * Implement control + a control + a to toggle between sessions * docs
  cleanup

Assisted-by: claude

- Orphaned commands, readme
  ([`e6af005`](https://github.com/quadsproject/quads-client/commit/e6af0058bb2eabd6a487a3995c972966d0df1d0b))

### Chores

- Update RPM spec version to 0.5.2
  ([`fb9a71c`](https://github.com/quadsproject/quads-client/commit/fb9a71c8027ab61e7ad373d44d43cb78d4d9430e))

- Update tests
  ([`04c53e6`](https://github.com/quadsproject/quads-client/commit/04c53e6e7871a08853bbbf8020496948d97d1db1))


## v0.5.2 (2026-05-15)

### Bug Fixes

- Date and color picker backgrounds for add schedule.
  ([`ea906e1`](https://github.com/quadsproject/quads-client/commit/ea906e17246c07a16e9c42b83a05e30e0a5931c4))

* We need better consistent dark/light theme backgrounds for date picker.

- My hosts view in GUI for large assignments.
  ([`c602af7`](https://github.com/quadsproject/quads-client/commit/c602af778f8d15e59cef222880d2d1bdfc969735))

* We needed an outer scrollbar in the my hosts area for normal users. * We need to fix os list
  dropdown and qinq for admin scheduling.

Assisted-by: claude

- Os, qinq drop-downs, assignment view outer accessibility, color theme fixes
  ([`f2307a5`](https://github.com/quadsproject/quads-client/commit/f2307a5fdf3b20e2cea531eaab0093a22dd82057))

fix: os, qinq drop-downs, assignment view outer accessibility, color theme fixes

### Chores

- Update RPM spec version to 0.5.1
  ([`6314cbd`](https://github.com/quadsproject/quads-client/commit/6314cbdb8640746c1bd40f80667f877e31f7a80d))


## v0.5.1 (2026-05-15)

### Bug Fixes

- Big performance increases/fixes
  ([`36cdef4`](https://github.com/quadsproject/quads-client/commit/36cdef42463189d7d7d6a4adce45dbc7d894a633))

1. gui/views/schedule.py — Deferred all API calls out of _create_ui(). VLAN/OS dropdowns now render
  with placeholders and populate via _load_metadata_async() in a background thread.
  _load_available_hosts() also converted from synchronous to threaded. 2.
  gui/widgets/host_filters.py — Model and NIC vendor dropdowns now start empty, populated via new
  populate_metadata_async() method using background thread. Both Schedule and Available views use
  this. 3. gui/controllers/gui_shell.py — Added shared _get_cached_hosts() with TTL so
  get_available_models() and get_available_nic_vendors() share a single get_hosts() API call instead
  of two separate ones. 4. gui/views/available.py — Calls populate_metadata_async() on its filter
  frame too

Assisted-by: claude

- Remove/hide commands, sort assignments, fixes
  ([`e573e85`](https://github.com/quadsproject/quads-client/commit/e573e85a3f581ad3799bf3c2fef75abcf0642dae))

* sort assignments list by cloud * eof, set, ipy, py — added to permanently_hidden (hidden from all
  users) * debug_admin — added to admin_commands (hidden from normal users, whoami is sufficient) *
  terminate — added to auth_required_commands

related-to: https://github.com/quadsproject/quads-client/issues/93

### Chores

- Update RPM spec version to 0.5.0
  ([`d6afd7f`](https://github.com/quadsproject/quads-client/commit/d6afd7fd7ac00d5c63681e86f8c681dba36734e5))

- Update tests
  ([`ac1acd9`](https://github.com/quadsproject/quads-client/commit/ac1acd904f754dd0aeaf86b0406cbab92c3265bb))


## v0.5.0 (2026-05-14)

### Chores

- Fix flake8 CI
  ([`c874ab9`](https://github.com/quadsproject/quads-client/commit/c874ab9ba9410bb22cef78450bdb1825454ee5f2))

- Update RPM spec version to 0.4.12
  ([`8a920d5`](https://github.com/quadsproject/quads-client/commit/8a920d58c8a9bfc6c3a1e78c1847e3f44400d556))

### Features

- Add support for os_list in CLI and GUI.
  ([`e725ad9`](https://github.com/quadsproject/quads-client/commit/e725ad9dac780e1827553bdea5e0c8a5c979f92b))

* Adds command os_list to CLI * Adds drop-down query for OS API endpoint via QuadsAPI (via
  quads-lib) in admin and normal user GUI areas.

Assisted-by: claude


## v0.4.12 (2026-05-14)

### Bug Fixes

- Add_quads_server in first run, fix echo one-shot
  ([`b1b2032`](https://github.com/quadsproject/quads-client/commit/b1b20323bda40f345ed6beaa66da117ad06c5784))

### Chores

- Fix black formatting
  ([`5e994de`](https://github.com/quadsproject/quads-client/commit/5e994de2c8e168d7250bd78f267d74430010c058))

- Update RPM spec version to 0.4.11
  ([`a0e0e4d`](https://github.com/quadsproject/quads-client/commit/a0e0e4d572c83f86acbb6f3ec21605af8a87eecf))


## v0.4.11 (2026-05-13)

### Bug Fixes

- Use getpass to hide pw input on add server
  ([`a8563cd`](https://github.com/quadsproject/quads-client/commit/a8563cd90a9fcb8078e68b9d4fabba22ce649dc1))

### Chores

- Update RPM spec version to 0.4.10
  ([`1d60342`](https://github.com/quadsproject/quads-client/commit/1d60342ce9e75e9743acdc7fe54cabf772dc0b3a))


## v0.4.10 (2026-05-13)

### Bug Fixes

- Edit-server, simplify onboard flows for CLI
  ([`9cc226d`](https://github.com/quadsproject/quads-client/commit/9cc226d0ab719303ebed8ffb7ced4b6ffd38b0fc))

- Show create/expire date on my_assignments in TUI
  ([`4380b78`](https://github.com/quadsproject/quads-client/commit/4380b783e0b46e341e9a84cacddf7c9a30a859ba))

### Chores

- Update RPM spec version to 0.4.9
  ([`939e590`](https://github.com/quadsproject/quads-client/commit/939e5902030c93b11a0edbc2917f7fbd8483fb9a))


## v0.4.9 (2026-05-12)

### Bug Fixes

- My_hosts should show cloud, assignment id
  ([`a0b45df`](https://github.com/quadsproject/quads-client/commit/a0b45df668c72e0602d4799fa999d586f20ad0a2))

### Chores

- Update RPM spec version to 0.4.8
  ([`970f714`](https://github.com/quadsproject/quads-client/commit/970f714f1c0d4db9a686af603ebe920f345f851d))


## v0.4.8 (2026-05-12)

### Bug Fixes

- My_hosts not returning correctly for SSM user
  ([`29d975b`](https://github.com/quadsproject/quads-client/commit/29d975b881db8ad5e4e90925572f7ebbb67eed4d))

### Chores

- Update RPM spec version to 0.4.7
  ([`d684321`](https://github.com/quadsproject/quads-client/commit/d684321ed8d651f9d1c1d6c965bf52f950664c4b))


## v0.4.7 (2026-05-12)

### Bug Fixes

- Use truststore for darwin users
  ([`10294a1`](https://github.com/quadsproject/quads-client/commit/10294a1273c9ca06bb5ae7fbd53a75417d3bc748))

This allows for the SSL verify to remain checked, and use the system trust store on darwin. This can
  also be done on linux, though some distributions may not have python3-truststore bundled and users
  may not wish to pip install into a venv.

- Use truststore for Mac Users
  ([`270d67f`](https://github.com/quadsproject/quads-client/commit/270d67fe6967a3e9e91cddfcb4c1603f8bca50fb))

fix: use truststore for Mac Users for TLS verification using pip instal

### Chores

- Update RPM spec version to 0.4.6
  ([`d2cd9e3`](https://github.com/quadsproject/quads-client/commit/d2cd9e33a1cac7ad81d69c19cb33ea6e81a3bb2b))


## v0.4.6 (2026-05-12)

### Bug Fixes

- Modify cloud
  ([`adea977`](https://github.com/quadsproject/quads-client/commit/adea97742d0ef6f9b1ee0ea2cc830c8cbe2037ad))

- Server refresh, register on new, fonts
  ([`b472b1f`](https://github.com/quadsproject/quads-client/commit/b472b1fa43ede03e1aebe3c9c23f9fb5f25eacd7))

### Chores

- Extend dialogue boxes slightly
  ([`0c7b75e`](https://github.com/quadsproject/quads-client/commit/0c7b75ee787e4cdcc7ee93bf884de861accae7b4))

- Make error windows slightly larger
  ([`b2cf00d`](https://github.com/quadsproject/quads-client/commit/b2cf00db49072ebcc24bd3b9d7f6d0d1ba99764f))

- Update RPM spec version to 0.4.5
  ([`86659f1`](https://github.com/quadsproject/quads-client/commit/86659f191bf2b0205e1bbcb2ef549a9102030d05))

- Updates tests
  ([`aa07564`](https://github.com/quadsproject/quads-client/commit/aa0756495f34bce7bcdfde5e9452effc7a7cd8d3))


## v0.4.5 (2026-05-12)

### Bug Fixes

- Extend cloud for quads-client-gui, helper method
  ([`d3b8baf`](https://github.com/quadsproject/quads-client/commit/d3b8bafd15793f0e062150467f68988b355ff56a))

- Extend/shrink, refactor with helper method
  ([`4e74034`](https://github.com/quadsproject/quads-client/commit/4e74034079f18fb0fcd85858ea81522b5a160445))

fix: extend/shrink, refactor with helper method

### Chores

- Update RPM spec version to 0.4.4
  ([`afc7f72`](https://github.com/quadsproject/quads-client/commit/afc7f726fa66ed94796a4ac7ebb47e16dc571322))


## v0.4.4 (2026-05-12)

### Bug Fixes

- Performance refactor, lazyload, caching, fixes
  ([`fd35d0c`](https://github.com/quadsproject/quads-client/commit/fd35d0c4cfc7e4766484b490c35ebf1d6c251f87))

- Test fixtures
  ([`4903a45`](https://github.com/quadsproject/quads-client/commit/4903a45980aa3ec6579bb60b23db07bf3a4d8b76))

### Chores

- Fix tests
  ([`d7f7101`](https://github.com/quadsproject/quads-client/commit/d7f71015299518ce26bed12a8c65804a92605291))

- Update RPM spec version to 0.4.3
  ([`48ac1af`](https://github.com/quadsproject/quads-client/commit/48ac1afba660be800236c2c1924e2b4b95fd786c))

- Update RPM spec version to 0.4.3
  ([`027404d`](https://github.com/quadsproject/quads-client/commit/027404ddef174837b078f1fcfa79d6bfea4a059a))


## v0.4.3 (2026-05-12)

### Bug Fixes

- Add tab complete to connect
  ([`0a43dde`](https://github.com/quadsproject/quads-client/commit/0a43dde269aa917a6f263a41047e6c208c409236))

- Filter by SSM capable for normal user views
  ([`ea4fd20`](https://github.com/quadsproject/quads-client/commit/ea4fd20b2357eba2f8d77a441bf1bc8da8935faf))

- Tab complete for connect, only show SSM for non-admin users
  ([`60385c6`](https://github.com/quadsproject/quads-client/commit/60385c6d959be25320f02d1527dc959e437cb9a3))

fix: tab complete for connect, only show SSM for non-admin users

### Chores

- Update RPM spec version to 0.4.2
  ([`9fa44ee`](https://github.com/quadsproject/quads-client/commit/9fa44eec293d18d166db072f5f7c45ab38549b37))


## v0.4.2 (2026-05-12)

### Bug Fixes

- Allow cloud_only to return cloud01 hosts too in CLI
  ([`2ea38c5`](https://github.com/quadsproject/quads-client/commit/2ea38c5f459bc630344174289f8c43132f4eae88))

- Available filters, view hosts details, mac styling
  ([`7e05994`](https://github.com/quadsproject/quads-client/commit/7e05994d5faf1ed9988c2ea6171eaad6682b3a63))

* Work around OSX ignoring dark mode in some modal shading hopefully * Adding rest of search
  filters: GPU, interfaces, disks * Adding/fixing view cloud host details (equivalent of quads
  --cloud-only * quads-client allow listing cloud_only cloud01

- Black theme on osx
  ([`5811caa`](https://github.com/quadsproject/quads-client/commit/5811caa7cccf7e18d2abc820467df5a5178cd492))

- Remove extraneous status string
  ([`985e586`](https://github.com/quadsproject/quads-client/commit/985e586bc0bf05582da44a609ea48e5361a0e530))

- Remove hardcoded colors and use theme manager.
  ([`52179f6`](https://github.com/quadsproject/quads-client/commit/52179f6e91f956ba43f5f147111636b1b6e30087))

- Rest of search filters, view details
  ([`63ef61a`](https://github.com/quadsproject/quads-client/commit/63ef61a95dfaa7b3310730ad5bdcd5b42f90df7e))

### Chores

- Black formatting
  ([`5a10dbb`](https://github.com/quadsproject/quads-client/commit/5a10dbbbeb2b0f59a25fdac6c757331218270aa1))

- Fix tests
  ([`c1bb1e1`](https://github.com/quadsproject/quads-client/commit/c1bb1e1f922550182a6284ef95ddb52027a8c763))

- Update docs
  ([`d869973`](https://github.com/quadsproject/quads-client/commit/d869973d97f9c9378d50408e9b3be57693e3d278))

- Update docs
  ([`f592698`](https://github.com/quadsproject/quads-client/commit/f59269866ed8f0654dfbc726dcb335fd2e525f54))

- Update RPM spec version to 0.4.1
  ([`16df70a`](https://github.com/quadsproject/quads-client/commit/16df70a38a6180325cb706a9945c090863448b21))


## v0.4.1 (2026-05-11)

### Bug Fixes

- Admin fixes, datepicker, more rails.
  ([`6b53206`](https://github.com/quadsproject/quads-client/commit/6b532068f5f216fb8c3d5fbee33d83caa1875b1c))

- Available filter being too aggressive
  ([`d4dbf60`](https://github.com/quadsproject/quads-client/commit/d4dbf60b7b47c03f84167b9572dd396af4d8e425))

- Bind_all not releasing on widget view
  ([`d6ae39a`](https://github.com/quadsproject/quads-client/commit/d6ae39ad48c3ebca146ae2f221c5f8fdcade5bc2))

- Last issues hopefully
  ([`8a25a4b`](https://github.com/quadsproject/quads-client/commit/8a25a4bad359cb7c3df26ae0e7cd4dbd580c4fdb))

- More adm fixes
  ([`cb88fe5`](https://github.com/quadsproject/quads-client/commit/cb88fe5294c8e3b51324146b50bc3a5bdbed4128))

- More admin fixes
  ([`bdda8c0`](https://github.com/quadsproject/quads-client/commit/bdda8c0663cae87bce1b27906ec971093e5935fc))

- More admin fixes, add proper native mac support
  ([`a7e3c4c`](https://github.com/quadsproject/quads-client/commit/a7e3c4c1ae38ccc1045e72357832a7b7e54aa91f))

fix: more admin fixes, add proper native mac support

- More admin fixes, add proper native mac support.
  ([`44c144a`](https://github.com/quadsproject/quads-client/commit/44c144a061b5bcd3a3e19afeae4070df24773e3c))

- Overhaul and fix sessions
  ([`bb32cb2`](https://github.com/quadsproject/quads-client/commit/bb32cb2509a01a8717358542191124c77f60f914))

- Refactor, fix found bugs
  ([`459f161`](https://github.com/quadsproject/quads-client/commit/459f161fb371583bf3ddb398e0b58e2026ef3fe2))

### Chores

- Doc update
  ([`8ab81b8`](https://github.com/quadsproject/quads-client/commit/8ab81b85bc245d7bfaa6c5f81e45a185cc950440))

- Fix last bits of CI hopefully
  ([`43e6bda`](https://github.com/quadsproject/quads-client/commit/43e6bda6561023202db6193f412722a98c2b30fb))

- Fix tests
  ([`cb4044b`](https://github.com/quadsproject/quads-client/commit/cb4044b61165f414d3dcd8167713235f020f1536))

- Fix tests
  ([`4ac041d`](https://github.com/quadsproject/quads-client/commit/4ac041def5aeb7b124582153d508dab8918db014))

- More admin/ui fixes
  ([`eaafbeb`](https://github.com/quadsproject/quads-client/commit/eaafbebe54ee679e150d507132a31b782544c760))

- Update RPM spec version to 0.4.0
  ([`ee5853b`](https://github.com/quadsproject/quads-client/commit/ee5853b6a922d8fd8fbb857ae6a4ac7d04dae8cb))


## v0.4.0 (2026-05-11)

### Chores

- Absolve GUI from tests
  ([`7aba36b`](https://github.com/quadsproject/quads-client/commit/7aba36b13ae7c1cb4d9d28e3ff0c3c732786728a))

related-to: https://github.com/quadsproject/quads-client/issues/57

- Black styling for tests
  ([`d385eda`](https://github.com/quadsproject/quads-client/commit/d385edad034144e8c3d79d32db9793c0b42c647e))

- Fix tests
  ([`c643966`](https://github.com/quadsproject/quads-client/commit/c643966752f9dda824ebc7d7e7182ee3119f8e6c))

- Update RPM spec version to 0.3.5
  ([`27856a9`](https://github.com/quadsproject/quads-client/commit/27856a9e9327a0423ea9a28ee59150ed10ebee07))

### Features

- Add quads-client tkinter UI beginnings.
  ([`c565580`](https://github.com/quadsproject/quads-client/commit/c565580019bebd0d11c0b8f60f6e9fbe231daa8e))

* No tests yet * Still needs testing

- Fully tested SSM workflows, refactor.
  ([`ea1eae9`](https://github.com/quadsproject/quads-client/commit/ea1eae9f0248c6d6d67837d67427490647c87c1e))

* ready to use for SSM * RPM sub-package for quads-client-gui * proper desktop structure, icon.

- More UI fixes/testing
  ([`c0b0820`](https://github.com/quadsproject/quads-client/commit/c0b08206d64df996219871b9c323e0469627b9d2))

- Quads CLIENT GUI, native python tkinter
  ([`137dde1`](https://github.com/quadsproject/quads-client/commit/137dde1d415b9b75e934cc4670a494e1abbd90a6))

feat: QUADS CLIENT GUI, native python tkinter

- Quads-client GUI MVP, tested for SSM
  ([`cc999a4`](https://github.com/quadsproject/quads-client/commit/cc999a4cee9e60a0d29eea554ebefde4ea351504))

feat: quads-client GUI MVP, tested for SSM

fixes: https://github.com/quadsproject/quads-client/issues/57

- Quads-client GUI MVP, tested for SSM.
  ([`79aa90e`](https://github.com/quadsproject/quads-client/commit/79aa90ec6ac247cdba4040faed8af7da3f19707e))

* Tested onboarding wizard * Tested SSM * TODO: testing admin mode.


## v0.3.5 (2026-05-08)

### Bug Fixes

- Black formatting
  ([`e889c80`](https://github.com/quadsproject/quads-client/commit/e889c80c5c7c7d41dc4b1e179baebf61256492f1))

- Black formatting line length
  ([`9e24ba3`](https://github.com/quadsproject/quads-client/commit/9e24ba30ec4afbb60a1e1b3113f71bb78ffbfb25))

- Further fixes on admin scheduling with JIRA functionality
  ([`b12f233`](https://github.com/quadsproject/quads-client/commit/b12f23353ae550741f4632eb0f31896a8d2df037))

fix: further fixes on admin scheduling with JIRA functionality

### Chores

- Update RPM spec version to 0.3.4
  ([`345b5f5`](https://github.com/quadsproject/quads-client/commit/345b5f5f2c9a611a475eec76d2152e4d9cc80fa1))

### Refactoring

- Use batch endpoint for schedule creation
  ([`80a45bc`](https://github.com/quadsproject/quads-client/commit/80a45bcc18862a4de30bf577f6aec7b32da97fff))

### Testing

- Migrate schedule tests to use batch creation endpoint
  ([`0749e24`](https://github.com/quadsproject/quads-client/commit/0749e2499a8ba4ac2cf95e9343bcfb8337b60bac))


## v0.3.4 (2026-05-08)

### Bug Fixes

- Incorrect entry point
  ([`bbd0265`](https://github.com/quadsproject/quads-client/commit/bbd026516f382a37c13e5e22a9c3ff15c341ab87))

### Chores

- Update RPM spec version to 0.3.3
  ([`5940499`](https://github.com/quadsproject/quads-client/commit/5940499e2e8ff913c0e81cb25af06ce523557cbf))


## v0.3.3 (2026-05-07)

### Bug Fixes

- Fully test and fix admin scheduling mode.
  ([`768780a`](https://github.com/quadsproject/quads-client/commit/768780a22719e26eb7912243a1851dd37ae850c4))

* Admin scheduling fully tested * Major refactor * Relied on changes to python-quads-lib and quads.

- Improve onboard first time xp, tests
  ([`bc83a1e`](https://github.com/quadsproject/quads-client/commit/bc83a1e8f2fa94224737f098a63b77921d1038ef))

- User onboarding fixes, tests
  ([`162ec5a`](https://github.com/quadsproject/quads-client/commit/162ec5aab0d573f981029ed396f36a0ed9522ded))

### Chores

- Add images
  ([`3842218`](https://github.com/quadsproject/quads-client/commit/38422183613350b9ee30042fc36bbf06685780c7))

- Add SSM and admin scheduling images, tests
  ([`276af50`](https://github.com/quadsproject/quads-client/commit/276af508f8dd3b770465c67531cf420add4e3bd5))

- Fix tests
  ([`d43b7e2`](https://github.com/quadsproject/quads-client/commit/d43b7e2878581ed12833f1d858ea828f41ec3995))

- Fix tests
  ([`5451ffa`](https://github.com/quadsproject/quads-client/commit/5451ffa7fd8e8c15f7f418865087d44ccb68e4a1))

- Flake8
  ([`4bc75c8`](https://github.com/quadsproject/quads-client/commit/4bc75c8755783ec43432fd4a8686af6f54f89083))

- Harden RPM spec update
  ([`ad884a9`](https://github.com/quadsproject/quads-client/commit/ad884a946e1ef6909dde07a645545faa5fa70a4f))

- Last bit of codecov tests
  ([`300dfb0`](https://github.com/quadsproject/quads-client/commit/300dfb07686c6b62f5151fc07ffc6fd2f6d5cdd1))

- Last of tests
  ([`d2d6863`](https://github.com/quadsproject/quads-client/commit/d2d68633257d08f79116f9e665f613802c0d6142))

- More tests
  ([`f8154ca`](https://github.com/quadsproject/quads-client/commit/f8154cac815a1b6ace757644615713a284b17114))

- Update RPM spec version to 0.3.2
  ([`ce47f23`](https://github.com/quadsproject/quads-client/commit/ce47f2334bf787837f10b1ac56751d4176706607))


## v0.3.2 (2026-05-06)

### Bug Fixes

- Make sure one-shot commands work.
  ([`b17d07a`](https://github.com/quadsproject/quads-client/commit/b17d07ad0f119016c1e96b3436b38cb35c690c65))

* fixes: https://github.com/quadsproject/quads-client/issues/45

- One-shot connections to non-default server
  ([`16abb6e`](https://github.com/quadsproject/quads-client/commit/16abb6e4453ba5b37cf0b1cdacb35b9896c7c838))

### Chores

- Update RPM spec version to 0.3.1
  ([`5753a9f`](https://github.com/quadsproject/quads-client/commit/5753a9f11184557d76b925947adaa3e23fedb27e))


## v0.3.1 (2026-05-06)

### Bug Fixes

- Ls_available returning N/A, filtering.
  ([`9f9a450`](https://github.com/quadsproject/quads-client/commit/9f9a450ede50a083bdc24cdee4a59c18b21db15b))

* Changed from filter_available (returns hostnames only) to filter_hosts (returns full objects) *
  Fixed ls_available from not matching properly.

- Major refactor
  ([`20bdf4b`](https://github.com/quadsproject/quads-client/commit/20bdf4b85f5bbe9ecda66a77766e223a806d9616))

### Chores

- Fix black formatting
  ([`b00272d`](https://github.com/quadsproject/quads-client/commit/b00272d3529fcbdb26fb15edd71ea87a07a877b9))

- Update readme
  ([`f84eecc`](https://github.com/quadsproject/quads-client/commit/f84eeccff798499d8098769a74b86adefbc51eb7))

- Update RPM spec version to 0.3.0
  ([`9c35ffa`](https://github.com/quadsproject/quads-client/commit/9c35ffacd5899a3ebeeba455e0765b81eae45123))


## v0.3.0 (2026-05-06)

### Chores

- Fix further tests relating to sessionmanager
  ([`692f78a`](https://github.com/quadsproject/quads-client/commit/692f78aa1dafcc4d355b1e2a6f4461255a82b6bf))

- Fix tests, add session UI image
  ([`0f48015`](https://github.com/quadsproject/quads-client/commit/0f480154f862df73e13d4d30b84402d623652ca0))

- Update RPM %post install steps
  ([`2a52feb`](https://github.com/quadsproject/quads-client/commit/2a52feb37eaa18b4de02ca69210302a7f44903b6))

- Update RPM spec version to 0.2.1
  ([`8c664ba`](https://github.com/quadsproject/quads-client/commit/8c664ba3e34479614aab2b891120e8e4e25cef4d))

### Features

- Multi-server session management implementation
  ([`7000f20`](https://github.com/quadsproject/quads-client/commit/7000f2098c4cd73fa9394ef225187d9a2ed2ebbb))

- Session manager fixes, docs
  ([`cd2cc6d`](https://github.com/quadsproject/quads-client/commit/cd2cc6df22f35d8447e9da953d63f06ce39e3fbc))


## v0.2.1 (2026-05-06)

### Bug Fixes

- Settr issue with RPM only.
  ([`0d337b8`](https://github.com/quadsproject/quads-client/commit/0d337b89b3034011213d5bbc26d836c04df6ea66))

### Chores

- Update RPM spec version to 0.2.0
  ([`f9ee277`](https://github.com/quadsproject/quads-client/commit/f9ee277480945dd086d0d1366e6972b28500f529))


## v0.2.0 (2026-05-06)

### Chores

- Update RPM spec version to 0.1.2
  ([`1e8f7c0`](https://github.com/quadsproject/quads-client/commit/1e8f7c0c25f69ae884374992bda8f4deeb781c60))

### Features

- Further TLS/SSL awareness, features, checks.
  ([`50af215`](https://github.com/quadsproject/quads-client/commit/50af21511ff42251858f84f2bf7d6dc70c6f034e))

* Fixes: https://github.com/quadsproject/quads-client/issues/33


## v0.1.2 (2026-05-05)

### Bug Fixes

- Break out contrib, release becomes terminate
  ([`a7cb34e`](https://github.com/quadsproject/quads-client/commit/a7cb34e474d295ed02800c0c54ec682e3455a91b))

### Chores

- Add tests for rich_console
  ([`eeab940`](https://github.com/quadsproject/quads-client/commit/eeab940731980bdaa06d8fdfc96050c2299b0f78))

- Add version, sync-back for RPM spec
  ([`62bc9e9`](https://github.com/quadsproject/quads-client/commit/62bc9e973f7466ea1e14c34d4facbb6246b026ca))

- Change release to terminate
  ([`5260ac4`](https://github.com/quadsproject/quads-client/commit/5260ac4e91729959cdfbf3c56d63c8cc1157aa3e))

- Update RPM spec version to 0.1.1
  ([`9c9b7e6`](https://github.com/quadsproject/quads-client/commit/9c9b7e6734aa18466d83e535884465b3b5b2df36))


## v0.1.1 (2026-05-05)

### Bug Fixes

- Regression in schedule command for SSM
  ([`1a2bce7`](https://github.com/quadsproject/quads-client/commit/1a2bce74d029c7045657ea497be50fafe1dd2f49))

### Chores

- Add CI/CD to development branch too
  ([`bf66a3b`](https://github.com/quadsproject/quads-client/commit/bf66a3bcc82079291814756e637f0c20806121e0))

- Docs update
  ([`6ff7a8d`](https://github.com/quadsproject/quads-client/commit/6ff7a8d403cc743ecd6d5b7f6b206e2e5fe16cc9))

- Fix codecov for development branch
  ([`02326d9`](https://github.com/quadsproject/quads-client/commit/02326d939e82f8cf62054e17831f7fcb8c7ed54a))

- Fix tests
  ([`d2ab3f0`](https://github.com/quadsproject/quads-client/commit/d2ab3f0571968434e4e12499ebcfe22ee9f4963c))

- Small doc update
  ([`b48e8d0`](https://github.com/quadsproject/quads-client/commit/b48e8d0321d2ccfce5c60de08ff76ae0dd83f3f8))


## v0.1.0 (2026-05-05)

### Bug Fixes

- Add full cmdset, TLS fixes
  ([`c9fab83`](https://github.com/quadsproject/quads-client/commit/c9fab83ce63f8fc99aaf5c9f922032505e7c4e2e))

- Black formatting for tests
  ([`80be7a7`](https://github.com/quadsproject/quads-client/commit/80be7a788aba0895141564f41fdd130cb347fd5e))

- Black neuroticism
  ([`7de1424`](https://github.com/quadsproject/quads-client/commit/7de1424bed01bcce10df03c5dec387ba5d17952f))

- Connection / register loop logic
  ([`17e897b`](https://github.com/quadsproject/quads-client/commit/17e897b542f150758c68204b8dfa7e615059b77f))

- Early connection failure and auto-complete
  ([`32d5091`](https://github.com/quadsproject/quads-client/commit/32d509175d833690ddfde2be942c1bf280c771df))

- Fix black styling
  ([`c15819b`](https://github.com/quadsproject/quads-client/commit/c15819b75d7182584c49a26c615626802682df3b))

- Jwt token tests, docs
  ([`10c1ce0`](https://github.com/quadsproject/quads-client/commit/10c1ce0724a114d222e4a8c6800a2603123ab269))

- Ls_available, filters, additional GHA
  ([`82a9329`](https://github.com/quadsproject/quads-client/commit/82a932915ed86f1b26d8a687c12cf747687f355f))

- Register and login, test steps
  ([`b0e72de`](https://github.com/quadsproject/quads-client/commit/b0e72ded64a27ce90dd19d4e0019f8b04da23220))

- Register positional error
  ([`e6be7d5`](https://github.com/quadsproject/quads-client/commit/e6be7d556498286e10f8884a4797589efc801b03))

- Tests structure hopefully
  ([`f84bbb4`](https://github.com/quadsproject/quads-client/commit/f84bbb42b009122d7a65d03fd160ee4aae4e2bbe))

### Chores

- Add manifest entry
  ([`a351df8`](https://github.com/quadsproject/quads-client/commit/a351df8ef598971c6b5b1e116af4a3e0bcd51c82))

- Add more test coverage
  ([`3df4622`](https://github.com/quadsproject/quads-client/commit/3df4622cca16244c0d13d43cd92b4df352693730))

- Black linting
  ([`d8e0f47`](https://github.com/quadsproject/quads-client/commit/d8e0f4718c3de02678aedd1516284a37f46be685))

- Docs
  ([`5702dee`](https://github.com/quadsproject/quads-client/commit/5702dee830af0bb4296a146e332811f796111e0e))

- Emoji are ok if in TUI or logger
  ([`6681558`](https://github.com/quadsproject/quads-client/commit/6681558c88edffa5f0651910801506f06080e69e))

- Fix black linting
  ([`0438050`](https://github.com/quadsproject/quads-client/commit/04380506c8aa27e8974cf4652feccc6fe23bbbe2))

- Fix GHA
  ([`0a94768`](https://github.com/quadsproject/quads-client/commit/0a94768b3fd9d8988239d9d7fee2157109f4f326))

- Fix rpm spec
  ([`53262d2`](https://github.com/quadsproject/quads-client/commit/53262d2f0780728e14c11331823a6d6f0aa564bc))

- Fix tests
  ([`047ef90`](https://github.com/quadsproject/quads-client/commit/047ef9088e3cacdac6bc77442881a2df3fd3c1fb))

- Fix tests
  ([`58ca610`](https://github.com/quadsproject/quads-client/commit/58ca610a3d812f8b7b2472b439a76a341a9589f2))

- Further codecov fixes
  ([`4423c41`](https://github.com/quadsproject/quads-client/commit/4423c41c11ab06280f21b2b595293fe9f4bc862a))

- Hopefully fix GHA
  ([`7f8e1d9`](https://github.com/quadsproject/quads-client/commit/7f8e1d928d60d333f0ef4fe8d57142d065f724ab))

- Image dimension
  ([`bc5187b`](https://github.com/quadsproject/quads-client/commit/bc5187b1c6338e4c27a44da7a55563ba9a4a8203))

- Last commits and ready to test, with spec and pkgs
  ([`9f148a8`](https://github.com/quadsproject/quads-client/commit/9f148a85fd36dc9e805ace42fbeaa7335639e4a4))

- Make rpm spec more copr-like
  ([`112eb73`](https://github.com/quadsproject/quads-client/commit/112eb73aeb00408e100c09ab23498a5c1cb86258))

- More test coverage complaints
  ([`491b79d`](https://github.com/quadsproject/quads-client/commit/491b79dbe7f5a78df42b5022fac30e697a29ec77))

- More test jiggering
  ([`cd56193`](https://github.com/quadsproject/quads-client/commit/cd561939d7b5c6313066cc391975ce5e3b1f2ac0))

- Test coverage
  ([`41f406c`](https://github.com/quadsproject/quads-client/commit/41f406c68c154d11eef884dcbc907efe30c9fc06))

- Try to fix test coverage
  ([`dc06f2b`](https://github.com/quadsproject/quads-client/commit/dc06f2bd3df4e7c22d808702b711b52a4b87e16a))

### Features

- Add all ls-available, update docs
  ([`0332142`](https://github.com/quadsproject/quads-client/commit/0332142e853ac1801321a75ddd32ce6767d10e1b))

- Add rest of SSM commands, tests
  ([`64ca034`](https://github.com/quadsproject/quads-client/commit/64ca0348073ac86a04d00c8f033696d334f009e4))

- Choose server by number, ssm fixes, docs
  ([`d60fabb`](https://github.com/quadsproject/quads-client/commit/d60fabb04d26605c6148fa4ff7dd996a324a2ea7))

- Full command complete, token auto-refresh, server capacity
  ([`7639277`](https://github.com/quadsproject/quads-client/commit/7639277fff26e8a7233540ea720a6723c9c2e499))

- Initial scaffolding for quads-client
  ([`c4345ec`](https://github.com/quadsproject/quads-client/commit/c4345eca8d192c51f36170f3e359ae18071a2160))

- Major refactor, no ssm_ prefix, fixes
  ([`b28fd3f`](https://github.com/quadsproject/quads-client/commit/b28fd3fab6601a43c2bcb49a093578d77ffe9140))

- Role abstraction fixes, rich, workflow.
  ([`bed1b2a`](https://github.com/quadsproject/quads-client/commit/bed1b2ac93b4821326cca8216f15204bf8f500b4))
