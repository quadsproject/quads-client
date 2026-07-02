"""Argument parsing utilities for QUADS Client"""

import os
import shlex


def parse_host_list_file(file_path):
    """
    Parse a host list file and return list of hostnames.

    Matches QUADS core behavior: reads entire file and splits by whitespace.
    This allows hosts to be on one line or multiple lines.
    Filters out comment lines (starting with #) and blank lines.

    Args:
        file_path: Path to file containing hostnames (whitespace-separated)

    Returns:
        List of hostnames

    Raises:
        ValueError: If file cannot be read or is empty
    """
    expanded_path = os.path.expanduser(file_path)
    if not os.path.exists(expanded_path):
        raise ValueError(f"Host list file not found: {file_path}")

    try:
        with open(expanded_path, "r") as f:
            # Read lines, filter out comments and blank lines, then join and split by whitespace
            lines = f.readlines()
            # Filter out comment lines and blank lines
            filtered_lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]
            host_list_stream = " ".join(filtered_lines)
    except IOError as e:
        raise ValueError(f"Could not read file: {file_path}. {e}")

    # Split by whitespace (matches QUADS core CLI behavior)
    hosts = host_list_stream.split()

    if not hosts:
        raise ValueError(f"Host list file is empty: {file_path}")

    return hosts


def parse_schedule_ssm_args(args):
    """
    Parse SSM schedule command arguments

    Syntax: schedule <count|hostname[,hostname]|host-list path> description <desc> [OPTIONS]

    Args:
        args: Command arguments string

    Returns:
        dict with keys: count, host_list, description, wipe, vlan, qinq, model, ram,
        disk_type, disk_size, disk_count, gpu_vendor, gpu_product, interfaces,
        nic_vendor, nic_speed

    Raises:
        ValueError: If arguments are invalid
    """
    parts = shlex.split(args)
    if len(parts) < 3:
        raise ValueError("Usage: schedule <count|hostname[,hostname...]|host-list path> description <desc> [options]")

    result = {
        "count": None,
        "host_list": None,
        "description": None,
        "wipe": True,  # Default: wipe enabled
        "vlan": None,
        "qinq": None,  # Optional: only set if user specifies
        "os": None,
        "model": None,
        "ram": None,
        "disk_type": None,
        "disk_size": None,
        "disk_count": None,
        "gpu_vendor": None,
        "gpu_product": None,
        "interfaces": None,
        "nic_vendor": None,
        "nic_speed": None,
    }

    # Parse first positional argument (count/hosts/host-list)
    first_arg = parts[0]
    if first_arg.isdigit():
        # Count mode
        result["count"] = int(first_arg)
    elif first_arg == "host-list":
        # Host-list mode
        if len(parts) < 2:
            raise ValueError("host-list requires a file path")
        result["host_list"] = parse_host_list_file(parts[1])
        parts = parts[1:]  # Consume the file path
    elif "," in first_arg:
        # Comma-separated hosts
        result["host_list"] = [h.strip() for h in first_arg.split(",") if h.strip()]
    else:
        # Single host
        result["host_list"] = [first_arg]

    # Parse remaining arguments
    i = 1
    while i < len(parts):
        if parts[i] == "description" and i + 1 < len(parts):
            # Collect description until next keyword
            desc_parts = []
            i += 1
            while i < len(parts) and parts[i] not in [
                "nowipe",
                "vlan",
                "qinq",
                "os",
                "model",
                "ram",
                "disk-type",
                "disk-size",
                "disk-count",
                "gpu-vendor",
                "gpu-product",
                "interfaces",
                "nic-vendor",
                "nic-speed",
            ]:
                desc_parts.append(parts[i])
                i += 1
            result["description"] = " ".join(desc_parts)
        elif parts[i] == "nowipe":
            result["wipe"] = False
            i += 1
        elif parts[i] == "vlan" and i + 1 < len(parts):
            result["vlan"] = int(parts[i + 1])
            i += 2
        elif parts[i] == "qinq" and i + 1 < len(parts):
            result["qinq"] = int(parts[i + 1])
            i += 2
        elif parts[i] == "os" and i + 1 < len(parts):
            result["os"] = parts[i + 1]
            i += 2
        elif parts[i] == "model" and i + 1 < len(parts):
            result["model"] = parts[i + 1]
            i += 2
        elif parts[i] == "ram" and i + 1 < len(parts):
            result["ram"] = int(parts[i + 1])
            i += 2
        elif parts[i] == "disk-type" and i + 1 < len(parts):
            result["disk_type"] = parts[i + 1]
            i += 2
        elif parts[i] == "disk-size" and i + 1 < len(parts):
            result["disk_size"] = int(parts[i + 1])
            i += 2
        elif parts[i] == "disk-count" and i + 1 < len(parts):
            result["disk_count"] = int(parts[i + 1])
            i += 2
        elif parts[i] == "gpu-vendor" and i + 1 < len(parts):
            result["gpu_vendor"] = parts[i + 1]
            i += 2
        elif parts[i] == "gpu-product" and i + 1 < len(parts):
            result["gpu_product"] = parts[i + 1]
            i += 2
        elif parts[i] == "interfaces" and i + 1 < len(parts):
            result["interfaces"] = int(parts[i + 1])
            i += 2
        elif parts[i] == "nic-vendor" and i + 1 < len(parts):
            result["nic_vendor"] = parts[i + 1]
            i += 2
        elif parts[i] == "nic-speed" and i + 1 < len(parts):
            result["nic_speed"] = int(parts[i + 1])
            i += 2
        else:
            value_keywords = [
                "vlan",
                "qinq",
                "os",
                "model",
                "ram",
                "disk-type",
                "disk-size",
                "disk-count",
                "gpu-vendor",
                "gpu-product",
                "interfaces",
                "nic-vendor",
                "nic-speed",
            ]
            if parts[i] in value_keywords:
                raise ValueError(f"'{parts[i]}' requires a value")
            i += 1

    if not result["description"]:
        raise ValueError("description is required")

    return result


def parse_schedule_admin_args(args):
    """
    Parse admin schedule command arguments

    Syntax: schedule <cloud> <hosts|host-list path> <start> <end> [options]

    Options:
      description <text>       Assignment description (required for new assignments)
      cloud-owner <user>       Cloud owner username
      cloud-ticket <id>        Ticket ID (required for new assignments)
      cc-users <user1,user2>   Comma-separated CC users
      vlan <id>                VLAN ID number
      qinq <0|1>              QinQ setting (default 0)
      nowipe                   Disable host wiping (default: wipe enabled)

    Args:
        args: Command arguments string

    Returns:
        dict with keys: cloud, host_list, start, end, description, cloud_owner, cc_users,
        cloud_ticket, vlan, qinq, nowipe

    Raises:
        ValueError: If arguments are invalid
    """
    parts = shlex.split(args)
    if len(parts) < 4:
        raise ValueError(
            "Usage: schedule <cloud> <hosts|host-list path> <start> <end> [description <text>] "
            "[cloud-owner <user>] [cloud-ticket <id>] [cc-users <users>] "
            "[vlan <id>] [qinq <0|1>] [os <title>] [nowipe]"
        )

    result = {
        "cloud": parts[0],
        "host_list": None,
        "start": None,
        "end": None,
        "description": None,
        "cloud_owner": None,
        "cc_users": None,
        "cloud_ticket": None,
        "vlan": None,
        "qinq": None,
        "os": None,
        "wipe": True,  # Default: wipe enabled (systems wiped before new tenants)
        "nowipe": False,
    }

    # Parse hosts argument (between cloud and dates)
    if parts[1] == "host-list":
        if len(parts) < 5:
            raise ValueError("host-list requires a file path")
        result["host_list"] = parse_host_list_file(parts[2])
        params_start = 3  # Start looking for dates after file path
    elif "," in parts[1]:
        # Comma-separated hosts
        result["host_list"] = [h.strip() for h in parts[1].split(",") if h.strip()]
        params_start = 2
    else:
        # Single host
        result["host_list"] = [parts[1]]
        params_start = 2

    # Extract start/end dates (must come before optional keywords)
    keywords = ["description", "cloud-owner", "cc-users", "cloud-ticket", "vlan", "qinq", "os", "nowipe"]
    if params_start + 2 <= len(parts):
        # Check if next items are dates or keywords
        if parts[params_start] not in keywords:
            result["start"] = parts[params_start]
            if params_start + 1 < len(parts) and parts[params_start + 1] not in keywords:
                result["end"] = parts[params_start + 1]
                params_start += 2
            else:
                params_start += 1

    # Parse optional keyword parameters
    i = params_start
    while i < len(parts):
        if parts[i] == "description" and i + 1 < len(parts):
            # Collect description until next keyword
            desc_parts = []
            i += 1
            while i < len(parts) and parts[i] not in keywords:
                desc_parts.append(parts[i])
                i += 1
            result["description"] = " ".join(desc_parts)
        elif parts[i] == "cloud-owner" and i + 1 < len(parts):
            result["cloud_owner"] = parts[i + 1]
            i += 2
        elif parts[i] == "cc-users" and i + 1 < len(parts):
            result["cc_users"] = parts[i + 1]
            i += 2
        elif parts[i] == "cloud-ticket" and i + 1 < len(parts):
            result["cloud_ticket"] = parts[i + 1]
            i += 2
        elif parts[i] == "vlan" and i + 1 < len(parts):
            try:
                result["vlan"] = int(parts[i + 1])
            except ValueError:
                raise ValueError(f"VLAN must be a number, got: {parts[i + 1]}")
            i += 2
        elif parts[i] == "qinq" and i + 1 < len(parts):
            try:
                qinq_val = int(parts[i + 1])
                if qinq_val not in [0, 1]:
                    raise ValueError(f"QinQ must be 0 or 1, got: {parts[i + 1]}")
                result["qinq"] = qinq_val
            except ValueError as e:
                raise ValueError(f"Invalid QinQ value: {e}")
            i += 2
        elif parts[i] == "os" and i + 1 < len(parts):
            result["os"] = parts[i + 1]
            i += 2
        elif parts[i] == "nowipe":
            result["wipe"] = False  # Disable wiping
            result["nowipe"] = True
            i += 1
        else:
            i += 1

    return result


def parse_extend_args(args):
    """
    Parse extend command arguments

    Syntax: extend <cloud|hostname> weeks <N>
            extend <cloud|hostname> date <YYYY-MM-DD HH:MM>

    Args:
        args: Command arguments string

    Returns:
        dict with keys: target, mode, weeks, date

    Raises:
        ValueError: If arguments are invalid
    """
    parts = shlex.split(args)
    if len(parts) < 3:
        raise ValueError("Usage: extend <cloud|hostname> weeks <N> OR extend <cloud|hostname> date <YYYY-MM-DD HH:MM>")

    result = {
        "target": parts[0],
        "mode": parts[1],
        "weeks": None,
        "date": None,
    }

    if parts[1] == "weeks":
        try:
            result["weeks"] = int(parts[2])
        except (ValueError, IndexError):
            raise ValueError("weeks requires a number")
    elif parts[1] == "date":
        # Handle quoted date: date "2026-05-17 22:00" or date 2026-05-17 22:00
        date_str = " ".join(parts[2:]).strip('"')
        if not date_str:
            raise ValueError("date requires a value in format YYYY-MM-DD HH:MM")
        result["date"] = date_str
    else:
        raise ValueError("Second argument must be 'weeks' or 'date'")

    return result


def parse_shrink_args(args):
    """
    Parse shrink command arguments.

    Syntax: shrink <cloud|hostname> weeks <N>
            shrink <cloud|hostname> days <N>
            shrink <cloud|hostname> now
            shrink <cloud|hostname> date <YYYY-MM-DD HH:MM>

    Returns:
        dict with keys: target, mode, weeks, days, date

    Raises:
        ValueError: If arguments are invalid
    """
    parts = shlex.split(args)
    if len(parts) < 2:
        raise ValueError("Usage: shrink <cloud|hostname> weeks <N> | days <N> | now | date <YYYY-MM-DD HH:MM>")

    result = {
        "target": parts[0],
        "mode": parts[1],
        "weeks": None,
        "days": None,
        "date": None,
    }

    if parts[1] == "now":
        if len(parts) > 2:
            raise ValueError("'now' takes no additional arguments")
    elif parts[1] == "weeks":
        if len(parts) < 3:
            raise ValueError("weeks requires a number")
        try:
            result["weeks"] = int(parts[2])
        except ValueError:
            raise ValueError("weeks requires a number")
    elif parts[1] == "days":
        if len(parts) < 3:
            raise ValueError("days requires a number")
        try:
            result["days"] = int(parts[2])
        except ValueError:
            raise ValueError("days requires a number")
    elif parts[1] == "date":
        date_str = " ".join(parts[2:]).strip('"')
        if not date_str:
            raise ValueError("date requires a value in format YYYY-MM-DD HH:MM")
        result["date"] = date_str
    else:
        raise ValueError("Second argument must be 'weeks', 'days', 'now', or 'date'")

    return result
