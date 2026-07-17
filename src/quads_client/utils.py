"""Utility functions for quads-client"""

import re

AVAILABLE_HOSTS_BASE_FILTER = {
    "cloud": "cloud01",
    "retired": False,
    "broken": False,
}


def get_username_short(full_username: str) -> str:
    """Extract username without email domain.

    Args:
        full_username: Email address (e.g., "user@example.com")

    Returns:
        Username without domain (e.g., "user")
    """
    return full_username.split("@")[0]


def get_available_hosts_filter(**additional_filters):
    """Get base filter for available hosts with optional additions.

    Args:
        **additional_filters: Additional filter key-value pairs

    Returns:
        Combined filter dict for available hosts
    """
    base_filter = AVAILABLE_HOSTS_BASE_FILTER.copy()
    base_filter.update(additional_filters)
    return base_filter


def extract_cloud_name(assignment, default="N/A"):
    """Extract cloud name from assignment (dict or object).

    Args:
        assignment: Assignment dict or object
        default: Default value if cloud name not found

    Returns:
        Cloud name string
    """
    if isinstance(assignment, dict):
        cloud = assignment.get("cloud", {})
        if isinstance(cloud, dict):
            return cloud.get("name", default)
        return cloud or default
    else:
        cloud = getattr(assignment, "cloud", None)
        if cloud:
            return getattr(cloud, "name", default)
        return default


def extract_cloud_number(cloud_name):
    match = re.search(r"(\d+)$", cloud_name)
    return int(match.group(1)) if match else float("inf")


def extract_assignment_id(assignment, default="N/A"):
    """Extract assignment ID from assignment (dict or object).

    Args:
        assignment: Assignment dict or object
        default: Default value if ID not found

    Returns:
        Assignment ID (int or default)
    """
    if isinstance(assignment, dict):
        return assignment.get("id", default)
    return getattr(assignment, "id", default)


def extract_host_field(host, field_name, field_aliases=None, default=""):
    """
    Extract a field from a host that could be a string, dict, or object.

    Args:
        host: The host data (string, dict, or object)
        field_name: Primary field name to extract
        field_aliases: List of alternative field names to try
        default: Default value if field not found

    Returns:
        The extracted field value or default
    """
    if field_aliases is None:
        field_aliases = []

    # If host is a plain string and we're asking for 'name', return it
    # But only if it's not empty
    if isinstance(host, str):
        if field_name in ("name", "hostname"):
            return host if host else default
        else:
            return default

    # If host is a dict, try to get the field
    if isinstance(host, dict):
        if field_name in host:
            value = host[field_name]
            # Return value even if False (for booleans), but not if empty string
            if value is False or value:
                return value
        # Try aliases
        for alias in field_aliases:
            if alias in host:
                value = host[alias]
                if value is False or value:
                    return value
        return default

    # If host is an object, try attribute access
    if hasattr(host, field_name):
        value = getattr(host, field_name)
        # Return value even if False (for booleans), but not if empty string
        if value is False or value:
            return value
    # Try aliases
    for alias in field_aliases:
        if hasattr(host, alias):
            value = getattr(host, alias)
            if value is False or value:
                return value

    return default


def extract_hostname(host):
    """
    Extract hostname from a host that could be a string, dict, or object.

    Args:
        host: The host data (string, dict, or object)

    Returns:
        The hostname string or empty string if not found
    """
    return extract_host_field(host, "name", field_aliases=["hostname"], default="")


def get_ssl_indicator(url: str, verify: bool) -> tuple[str, str]:
    """
    Get SSL security indicator symbol and ANSI color for prompt display.

    Args:
        url: Server URL (http:// or https://)
        verify: Whether SSL verification is enabled

    Returns:
        tuple: (symbol, ansi_color_code)
            - ✓ (green) for HTTPS with verification
            - ! (green) for HTTPS without verification
            - ✗ (yellow) for HTTP
    """
    if url.startswith("https://"):
        if verify:
            return "✓", "\033[1;32m"
        else:
            return "!", "\033[1;32m"
    else:
        return "✗", "\033[1;33m"


def get_ssl_status_text(url: str, verify: bool) -> str:
    """
    Get SSL status text for table display.

    Args:
        url: Server URL (http:// or https://)
        verify: Whether SSL verification is enabled

    Returns:
        str: SSL status description
            - "HTTPS (verified)" for HTTPS with verification
            - "HTTPS (unverified)" for HTTPS without verification
            - "HTTP" for plain HTTP
    """
    if url.startswith("https://"):
        if verify:
            return "HTTPS (verified)"
        else:
            return "HTTPS (unverified)"
    else:
        return "HTTP"


def parse_api_datetime(datetime_str: str):
    """
    Parse datetime string from API responses, handling multiple formats.
    All times are assumed UTC. Returns a naive datetime (no tzinfo).

    The API returns different formats depending on the endpoint:
      - ISO: "2026-05-07T13:00:00.000Z"
      - RFC 2822: "Sun, 31 May 2026 22:00:00 GMT"
      - Display: "2026-05-07 22:00"

    Args:
        datetime_str: Datetime string from API

    Returns:
        naive datetime object (UTC assumed)

    Raises:
        ValueError: If format is not recognized
    """
    from datetime import datetime
    from email.utils import parsedate_to_datetime

    if not datetime_str:
        raise ValueError("Empty datetime string")

    dt = None

    # Try RFC 2822 first (e.g. "Sun, 31 May 2026 22:00:00 GMT")
    try:
        dt = parsedate_to_datetime(datetime_str)
    except (ValueError, TypeError):
        pass

    # Try ISO format (e.g. "2026-05-07T13:00:00.000Z")
    if dt is None:
        try:
            cleaned = datetime_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
        except ValueError:
            pass

    # Try display format (e.g. "2026-05-07 22:00")
    if dt is None:
        try:
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            pass

    if dt is None:
        raise ValueError(f"Unrecognized datetime format: '{datetime_str}'")

    return dt.replace(tzinfo=None)


def format_schedule_datetime(datetime_str: str) -> str:
    """
    Format schedule datetime from API format to display format.

    Args:
        datetime_str: ISO datetime from API (e.g., "2026-05-07T13:00:00.000Z")

    Returns:
        Formatted datetime (e.g., "2026-05-07 13:00")
    """
    return datetime_str.replace("T", " ").replace(":00.000Z", "").replace("Z", "").replace("GMT", "UTC")


def validate_cloud_exists(api, cloud_name: str) -> bool:
    """
    Check if a cloud exists.

    Args:
        api: QuadsApi instance
        cloud_name: Name of cloud to check

    Returns:
        True if cloud exists, False otherwise
    """
    clouds = api.filter_clouds({"name": cloud_name})
    return bool(clouds)


def resolve_os(api, os_input: str):
    """
    Validate and resolve an OS selection against the server's OS list.

    Matches by Title (case-insensitive) or by numeric Id.
    Returns (canonical_title, None) on success, (None, error_string) on failure.
    """
    os_list = api.get_os_list()
    if not os_list:
        return None, f"OS '{os_input}' not found"

    os_lower = os_input.lower()
    for entry in os_list:
        title = entry.get("Title", "")
        if title.lower() == os_lower:
            return title, None

    if os_input.isdigit():
        os_id = int(os_input)
        for entry in os_list:
            if entry.get("Id") == os_id:
                return entry.get("Title"), None

    available = ", ".join(entry.get("Title", "") for entry in os_list if entry.get("Title"))
    error = f"OS '{os_input}' not found"
    if available:
        error += f"\nAvailable: {available}"
    return None, error
