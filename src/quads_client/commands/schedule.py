from datetime import datetime, timedelta
from tabulate import tabulate

from quads_client.arg_parser import parse_extend_args, parse_schedule_admin_args, parse_shrink_args
from quads_client.error_handler import handle_api_error, require_admin, require_connection
from quads_client.utils import format_schedule_datetime, parse_api_datetime, resolve_os


def parse_flexible_datetime(date_str):
    """
    Parse date string in format YYYY-MM-DD HH:MM

    Args:
        date_str: Date string to parse

    Returns:
        datetime object

    Raises:
        ValueError: If date_str doesn't match the required format
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError(
            f"Invalid date format: '{date_str}'. "
            f"Expected 'YYYY-MM-DD HH:MM' (e.g., '2026-05-15 22:00') or use 'now' for immediate start"
        )


class ScheduleCommands:
    def __init__(self, shell):
        self.shell = shell
        self.rich_console = shell.rich_console if hasattr(shell, "rich_console") else None

    def _require_connection(self):
        return require_connection(self.shell)

    def cmd_ls_schedule(self, args):
        """List schedules. Usage: ls-schedule [host <hostname>] [cloud <cloudname>]

        For single host: shows default cloud, current cloud, current schedule, and full history.
        For multiple/no filter: shows schedules in table format.
        """
        if not self._require_connection():
            return

        parts = args.split()
        filters = {}
        hostname = None

        i = 0
        while i < len(parts):
            if parts[i] == "host" and i + 1 < len(parts):
                hostname = parts[i + 1]
                filters["host"] = hostname
                i += 2
            elif parts[i] == "cloud" and i + 1 < len(parts):
                filters["cloud"] = parts[i + 1]
                i += 2
            else:
                i += 1

        try:
            schedules = self.shell.connection.api.get_schedules(filters)
            if not schedules:
                self.shell.poutput("No schedules found")
                return

            # Special handling for single host query - show host details and full history
            if hostname and not filters.get("cloud"):
                # Get host details for default/current cloud info
                try:
                    host_info = self.shell.connection.api.get_host(hostname)
                    default_cloud = host_info.get("default_cloud", {}).get("name", "cloud01")
                    current_cloud = host_info.get("cloud", {}).get("name", default_cloud)

                    # Find current schedule
                    current_schedule_id = None
                    now = datetime.now()
                    for sched in schedules:
                        start_str = sched.get("start", "")
                        end_str = sched.get("end", "")
                        if start_str and end_str:
                            try:
                                start = parse_api_datetime(start_str)
                                end = parse_api_datetime(end_str)
                                if start <= now <= end:
                                    current_schedule_id = sched.get("id")
                                    break
                            except (ValueError, AttributeError):
                                pass

                    # Show host summary
                    self.shell.poutput(f"Default cloud: {default_cloud}")
                    self.shell.poutput(f"Current cloud: {current_cloud}")
                    if current_schedule_id:
                        self.shell.poutput(f"Current schedule: {current_schedule_id}")

                    # Build schedule table (ID | start | end | cloud format)
                    table_data = []
                    for sched in sorted(schedules, key=lambda x: x.get("start", "")):
                        schedule_id = sched.get("id", "")
                        start = format_schedule_datetime(sched.get("start", ""))
                        end = format_schedule_datetime(sched.get("end", ""))
                        assignment = sched.get("assignment", {})
                        cloud = assignment.get("cloud", {}).get("name", "")

                        table_data.append([schedule_id, start, end, cloud])

                    if self.rich_console:
                        self.rich_console.print_table(
                            ["ID", "Start", "End", "Cloud"], table_data, title=f"Schedule History for {hostname}"
                        )
                    else:
                        self.shell.poutput(
                            tabulate(table_data, headers=["ID", "Start", "End", "Cloud"], tablefmt="simple")
                        )
                    return
                except Exception as e:
                    # Fall through to regular table display if host info fails
                    self.shell.perror(f"Warning: Could not fetch host details: {e}")

            # Regular table display for multiple hosts or cloud filter
            table_data = []
            for sched in schedules:
                host_name = sched.get("host", {}).get("name", "")
                assignment = sched.get("assignment", {})
                cloud_name = assignment.get("cloud", {}).get("name", "")
                owner = assignment.get("owner", "")

                table_data.append(
                    [
                        sched.get("id", ""),
                        host_name,
                        cloud_name,
                        owner,
                        sched.get("start", "").replace("GMT", "UTC"),
                        sched.get("end", "").replace("GMT", "UTC"),
                    ]
                )

            headers = ["ID", "Host", "Cloud", "Owner", "Start", "End"]
            if self.rich_console:
                self.rich_console.print_table(headers, table_data, title="Schedules")
            else:
                self.shell.poutput(tabulate(table_data, headers=headers, tablefmt="simple"))

        except Exception as e:
            self.shell.perror(f"Failed to list schedules: {e}")

    def cmd_schedule_admin(self, args):
        """
        Admin Mode: Schedule hosts with explicit dates and cloud parameters

        Unified command that combines assignment creation and host scheduling.
        If the cloud has no active assignment, one will be created automatically.

        Usage: schedule <cloud> <hosts|host-list path> <start> <end> [options]

        Options:
          description <text>       Assignment description (required for new assignments)
          cloud-owner <username>   Cloud owner username (required for new assignments)
          cloud-ticket <ticket_id> Ticket ID (required for new assignments)
          cc-users <user1,user2>   Comma-separated CC users
          vlan <vlan_id>           VLAN ID number
          qinq <0|1>              QinQ setting (default 0)
          os <title>               OS for provisioning (see os-list)
          nowipe                   Disable host wiping (default: wipe enabled)

        Examples:
          schedule cloud02 host01,host02 2026-05-11 2026-06-11 description "Test Env" \\
            cloud-owner jdoe cloud-ticket 123
          schedule cloud17 host-list ~/hosts.txt now 2026-07-01 \\
            description "OpenStack Testing" cloud-owner alice cloud-ticket 456
          schedule cloud05 host03 2026-05-15 2026-06-01 description "Performance Test" \\
            cloud-owner jdoe cloud-ticket 789 vlan 1234 qinq 1 nowipe
        """
        if not require_admin(self.shell):
            return

        try:
            # Parse arguments
            parsed = parse_schedule_admin_args(args)

            # Validate dates (unless start is "now")
            if parsed["start"] and parsed["start"] != "now":
                try:
                    start_date = parse_flexible_datetime(parsed["start"])
                    end_date = parse_flexible_datetime(parsed["end"])

                    if start_date >= end_date:
                        self.shell.perror("Error: Start date must be before end date")
                        return
                except ValueError as date_err:
                    self.shell.perror(f"Invalid date format: {date_err}")
                    return

            # Verify cloud exists
            clouds = self.shell.connection.api.filter_clouds({"name": parsed["cloud"]})
            if not clouds:
                self.shell.perror(f"Cloud '{parsed['cloud']}' not found")
                return

            # Pre-check host availability BEFORE creating assignment
            # This prevents creating orphaned assignments when hosts are unavailable
            unavailable = []
            if parsed["start"] != "now":
                start_iso = parse_flexible_datetime(parsed["start"]).isoformat()[:-3]
                end_iso = parse_flexible_datetime(parsed["end"]).isoformat()[:-3]

                for hostname in parsed["host_list"]:
                    is_available = self.shell.connection.api.is_available(
                        hostname, {"start": start_iso, "end": end_iso}
                    )
                    if not is_available:
                        unavailable.append(hostname)

                if unavailable:
                    self.shell.perror("The following hosts are unavailable for the specified date range:")
                    for host in unavailable:
                        self.shell.perror(f"  {host}")
                    self.shell.perror("Remove these from your host list and try again.")
                    return

            # Create schedules using batch endpoint
            # Batch endpoint handles assignment creation if parameters provided
            batch_data = {
                "cloud": parsed["cloud"],
                "hostnames": parsed["host_list"],
                "start": parsed["start"],
                "end": parsed["end"],
            }

            # Check if user provided assignment parameters
            should_create_new = parsed["cloud_ticket"] or (parsed["description"] and parsed["cloud_owner"])

            if should_create_new:
                # Validate required fields
                if not parsed["description"]:
                    self.shell.perror("description is required when creating a new assignment")
                    return

                if not parsed["cloud_owner"]:
                    self.shell.perror("cloud-owner is required when creating a new assignment")
                    return

                if not parsed["cloud_ticket"]:
                    self.shell.perror("cloud-ticket is required when creating a new assignment")
                    return

                # Pass assignment parameters to batch endpoint
                batch_data["description"] = parsed["description"]
                batch_data["owner"] = parsed["cloud_owner"]
                batch_data["ticket"] = parsed["cloud_ticket"]
                batch_data["wipe"] = parsed.get("wipe", True)
                if parsed["cc_users"]:
                    batch_data["ccuser"] = parsed["cc_users"]
                if parsed["vlan"]:
                    batch_data["vlan"] = parsed["vlan"]
                if parsed["qinq"] is not None:
                    batch_data["qinq"] = parsed["qinq"]
                if parsed.get("os"):
                    resolved_os, os_error = resolve_os(self.shell.connection.api, parsed["os"])
                    if os_error:
                        self.shell.perror(os_error)
                        return
                    batch_data["ostype"] = resolved_os

            try:
                result = self.shell.connection.api.create_schedules_batch(batch_data)

                created_count = result.get("schedules_created", 0)
                assignment_id = result.get("assignment_id")
                jira_updated = result.get("jira_updated", False)

                # Show assignment creation if new
                if should_create_new:
                    if self.rich_console:
                        self.rich_console.print_success(
                            f"Assignment created - ID: {assignment_id}, Cloud: {parsed['cloud']}"
                        )
                    else:
                        self.shell.poutput(f"Assignment created - ID: {assignment_id}, Cloud: {parsed['cloud']}")

                # Show JIRA update status
                if jira_updated:
                    if self.rich_console:
                        self.rich_console.print_success("JIRA ticket updated")
                    else:
                        self.shell.poutput("JIRA ticket updated")

                # Show scheduled hosts
                for hostname in result.get("hostnames", []):
                    if self.rich_console:
                        self.rich_console.print_success(f"  {hostname}")
                    else:
                        self.shell.poutput(f"  {hostname}")

                # Show summary
                if self.rich_console:
                    self.rich_console.print_success(
                        f"\nCreated {created_count}/{len(parsed['host_list'])} schedule(s)"
                    )
                else:
                    self.shell.poutput(f"Created {created_count}/{len(parsed['host_list'])} schedule(s)")
            except Exception as e:
                handle_api_error(self.shell, e, "Batch scheduling")

        except ValueError as e:
            self.shell.perror(f"Invalid arguments: {e}")
        except ConnectionError:
            self.shell.perror("Connection failed: unable to reach QUADS server")
            self.shell.perror("Hint: Check 'status' or run 'connect <server>'")
        except Exception as e:
            handle_api_error(self.shell, e, "Scheduling")

    def cmd_mod_schedule(self, args):
        """Modify a schedule. Usage: mod-schedule id <schedule_id> [start <YYYY-MM-DD>] [end <YYYY-MM-DD>]"""
        if not self._require_connection():
            return

        parts = args.split()
        schedule_id = None
        updates = {}

        i = 0
        while i < len(parts):
            if parts[i] == "id" and i + 1 < len(parts):
                schedule_id = parts[i + 1]
                i += 2
            elif parts[i] == "start" and i + 1 < len(parts):
                updates["start"] = parts[i + 1]
                i += 2
            elif parts[i] == "end" and i + 1 < len(parts):
                updates["end"] = parts[i + 1]
                i += 2
            else:
                i += 1

        if not schedule_id:
            self.shell.perror("Usage: mod-schedule id <schedule_id> [start <YYYY-MM-DD>] [end <YYYY-MM-DD>]")
            return

        if not updates:
            self.shell.perror("No updates specified")
            return

        try:
            self.shell.connection.api.update_schedule(schedule_id, updates)
            self.shell.poutput(f"Schedule {schedule_id} updated successfully")
        except Exception as e:
            self.shell.perror(f"Failed to update schedule: {e}")

    def cmd_extend(self, args):
        """
        Extend cloud or host schedules (admin only - HIDDEN from SSM users)
        Usage: extend <cloud|hostname> weeks <N>
               extend <cloud|hostname> date <YYYY-MM-DD HH:MM>

        Examples:
          extend cloud02 weeks 2
          extend cloud02 date "2026-05-17 22:00"
          extend host01.example.com weeks 1
        """
        # Failsafe check (command should be hidden from SSM users via _update_visible_commands)
        if not require_admin(self.shell):
            return

        try:
            # Parse arguments
            parsed = parse_extend_args(args)

            # Determine if target is cloud or hostname
            if parsed["target"].startswith("cloud"):
                # Cloud mode: extend all current schedules in cloud
                schedules = self.shell.connection.api.get_current_schedules({"cloud": parsed["target"]})

                if not schedules:
                    if self.rich_console:
                        self.rich_console.print_error(f"No current schedules found for {parsed['target']}")
                    else:
                        self.shell.perror(f"No current schedules found for {parsed['target']}")
                    return

                if self.rich_console:
                    self.rich_console.print_info(f"Extending {len(schedules)} schedule(s) in {parsed['target']}...")
                else:
                    self.shell.poutput(f"Extending {len(schedules)} schedule(s) in {parsed['target']}...")

                for schedule in schedules:
                    if parsed["weeks"]:
                        current_end = parse_api_datetime(schedule["end"])
                        end_date = current_end + timedelta(weeks=parsed["weeks"])
                    else:
                        end_date = parse_flexible_datetime(parsed["date"])

                    self.shell.connection.api.update_schedule(
                        schedule["id"], {"end": end_date.strftime("%Y-%m-%dT%H:%M")}
                    )
                    if self.rich_console:
                        self.rich_console.print_success(schedule["host"]["name"])
                    else:
                        self.shell.poutput(f"  OK: {schedule['host']['name']}")

                if parsed["weeks"]:
                    if self.rich_console:
                        self.rich_console.print_success(f"Extended {parsed['target']} by {parsed['weeks']} week(s)")
                    else:
                        self.shell.poutput(f"OK: Extended {parsed['target']} by {parsed['weeks']} week(s)")
                else:
                    if self.rich_console:
                        self.rich_console.print_success(f"Extended {parsed['target']} to {parsed['date']}")
                    else:
                        self.shell.poutput(f"OK: Extended {parsed['target']} to {parsed['date']}")

            else:
                # Hostname mode: extend specific host's current schedule
                schedules = self.shell.connection.api.get_current_schedules({"host": parsed["target"]})

                if not schedules:
                    self.shell.perror(f"No current schedule found for {parsed['target']}")
                    return

                schedule = schedules[0]

                if parsed["weeks"]:
                    current_end = parse_api_datetime(schedule["end"])
                    end_date = current_end + timedelta(weeks=parsed["weeks"])
                else:
                    end_date = parse_flexible_datetime(parsed["date"])

                self.shell.connection.api.update_schedule(schedule["id"], {"end": end_date.strftime("%Y-%m-%dT%H:%M")})

                if parsed["weeks"]:
                    self.shell.poutput(f"OK: Extended {parsed['target']} by {parsed['weeks']} week(s)")
                else:
                    self.shell.poutput(f"OK: Extended {parsed['target']} to {parsed['date']}")

        except ValueError as e:
            self.shell.perror(f"Invalid arguments: {e}")
            self.shell.perror(
                "Usage: extend <cloud|hostname> weeks <N> OR extend <cloud|hostname> date <YYYY-MM-DD HH:MM>"
            )
        except Exception as e:
            handle_api_error(self.shell, e, "Extending schedule")

    def cmd_shrink(self, args):
        """
        Shrink cloud or host schedules (admin only)
        Usage: shrink <cloud|hostname> weeks <N>
               shrink <cloud|hostname> days <N>
               shrink <cloud|hostname> now
               shrink <cloud|hostname> date <YYYY-MM-DD HH:MM>

        Examples:
          shrink cloud02 weeks 2
          shrink cloud02 days 5
          shrink cloud23 now
          shrink host01.example.com date "2026-05-12 22:00"
        """
        if not require_admin(self.shell):
            return

        usage = "Usage: shrink <cloud|hostname> weeks <N> | days <N> | now | date <YYYY-MM-DD HH:MM>"

        try:
            parsed = parse_shrink_args(args)
        except ValueError as e:
            self.shell.perror(f"Invalid arguments: {e}")
            self.shell.perror(usage)
            return

        target = parsed["target"]

        try:
            if target.startswith("cloud"):
                schedules = self.shell.connection.api.get_current_schedules({"cloud": target})
            else:
                schedules = self.shell.connection.api.get_current_schedules({"host": target})

            if not schedules:
                self.shell.perror(f"No current schedules found for {target}")
                return

            if target.startswith("cloud"):
                host_count = len(schedules)
                self.shell.poutput(f"\nFound {host_count} active schedule(s) in {target}")
                if parsed["mode"] == "now":
                    self.shell.poutput("This will set all schedules to end now")
                elif parsed["mode"] == "weeks":
                    self.shell.poutput(f"This will shrink all schedules by {parsed['weeks']} week(s)")
                elif parsed["mode"] == "days":
                    self.shell.poutput(f"This will shrink all schedules by {parsed['days']} day(s)")
                else:
                    self.shell.poutput(f"This will set all schedule end dates to {parsed['date']}")

                try:
                    response = input("Continue? [y/N]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    self.shell.poutput("\nCancelled")
                    return

                if response not in ["y", "yes"]:
                    self.shell.poutput("Cancelled")
                    return

                updated_count = 0
                for schedule in schedules:
                    try:
                        new_end = self._compute_shrink_end(schedule, parsed)
                        new_end_str = new_end.strftime("%Y-%m-%dT%H:%M")
                        self.shell.connection.api.update_schedule(schedule["id"], {"end": new_end_str})
                        updated_count += 1

                        host_name = schedule.get("host", {}).get("name", "unknown")
                        if self.rich_console:
                            self.rich_console.print_success(f"  {host_name}")
                        else:
                            self.shell.poutput(f"  OK: {host_name}")
                    except Exception as e:
                        host_name = schedule.get("host", {}).get("name", "unknown")
                        if self.rich_console:
                            self.rich_console.print_error(f"  {host_name}: {e}")
                        else:
                            self.shell.perror(f"  Failed: {host_name}: {e}")

                summary = self._shrink_summary(target, parsed, updated_count, host_count)
                if self.rich_console:
                    self.rich_console.print_success(f"\n{summary}")
                else:
                    self.shell.poutput(f"OK: {summary}")
            else:
                schedule = schedules[0]
                new_end = self._compute_shrink_end(schedule, parsed)
                new_end_str = new_end.strftime("%Y-%m-%dT%H:%M")
                self.shell.connection.api.update_schedule(schedule["id"], {"end": new_end_str})
                self.shell.poutput(f"OK: Shrunk schedule for {target} to {new_end_str}")

        except ValueError as e:
            self.shell.perror(f"Invalid arguments: {e}")
            self.shell.perror(usage)
        except Exception as e:
            handle_api_error(self.shell, e, "Shrinking schedule")

    def _compute_shrink_end(self, schedule, parsed):
        if parsed["mode"] == "now":
            return datetime.now()
        elif parsed["mode"] == "weeks":
            current_end = parse_api_datetime(schedule["end"])
            return current_end - timedelta(weeks=parsed["weeks"])
        elif parsed["mode"] == "days":
            current_end = parse_api_datetime(schedule["end"])
            return current_end - timedelta(days=parsed["days"])
        else:
            return parse_flexible_datetime(parsed["date"])

    @staticmethod
    def _shrink_summary(target, parsed, updated_count, host_count):
        if parsed["mode"] == "now":
            return f"Shrunk {updated_count}/{host_count} schedule(s) in {target} to now"
        elif parsed["mode"] == "weeks":
            return f"Shrunk {updated_count}/{host_count} schedule(s) in {target} by {parsed['weeks']} week(s)"
        elif parsed["mode"] == "days":
            return f"Shrunk {updated_count}/{host_count} schedule(s) in {target} by {parsed['days']} day(s)"
        else:
            return f"Shrunk {updated_count}/{host_count} schedule(s) in {target} to {parsed['date']}"
