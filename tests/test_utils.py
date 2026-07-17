import pytest
from unittest.mock import MagicMock
from quads_client.utils import (
    AVAILABLE_HOSTS_BASE_FILTER,
    extract_assignment_id,
    extract_cloud_name,
    extract_cloud_number,
    extract_host_field,
    extract_hostname,
    format_schedule_datetime,
    get_available_hosts_filter,
    get_ssl_indicator,
    get_ssl_status_text,
    get_username_short,
    resolve_os,
    validate_cloud_exists,
)


def test_extract_hostname_from_string():
    """Test extracting hostname from plain string"""
    hostname = "host01.example.com"
    result = extract_hostname(hostname)
    assert result == "host01.example.com"


def test_extract_hostname_from_dict():
    """Test extracting hostname from dict with 'name' key"""
    host = {"name": "host01.example.com", "model": "r640"}
    result = extract_hostname(host)
    assert result == "host01.example.com"


def test_extract_hostname_from_dict_with_alias():
    """Test extracting hostname from dict with 'hostname' key"""
    host = {"hostname": "host01.example.com", "model": "r640"}
    result = extract_hostname(host)
    assert result == "host01.example.com"


def test_extract_hostname_from_object():
    """Test extracting hostname from object with name attribute"""

    class Host:
        def __init__(self):
            self.name = "host01.example.com"
            self.model = "r640"

    host = Host()
    result = extract_hostname(host)
    assert result == "host01.example.com"


def test_extract_hostname_from_object_with_alias():
    """Test extracting hostname from object with hostname attribute"""

    class Host:
        def __init__(self):
            self.hostname = "host01.example.com"
            self.model = "r640"

    host = Host()
    result = extract_hostname(host)
    assert result == "host01.example.com"


def test_extract_hostname_empty_dict():
    """Test extracting hostname from empty dict returns empty string"""
    host = {"model": "r640"}
    result = extract_hostname(host)
    assert result == ""


def test_extract_hostname_empty_object():
    """Test extracting hostname from object without name returns empty string"""

    class Host:
        def __init__(self):
            self.model = "r640"

    host = Host()
    result = extract_hostname(host)
    assert result == ""


def test_extract_host_field_string():
    """Test extract_host_field with string returns default for non-name fields"""
    hostname = "host01.example.com"
    result = extract_host_field(hostname, "model", default="N/A")
    assert result == "N/A"


def test_extract_host_field_from_dict():
    """Test extract_host_field from dict"""
    host = {"name": "host01.example.com", "model": "r640", "host_type": "baremetal"}
    assert extract_host_field(host, "model") == "r640"
    assert extract_host_field(host, "host_type") == "baremetal"


def test_extract_host_field_from_dict_with_alias():
    """Test extract_host_field from dict with alias"""
    host = {"host_model": "r640"}
    result = extract_host_field(host, "model", field_aliases=["host_model"])
    assert result == "r640"


def test_extract_host_field_from_object():
    """Test extract_host_field from object"""

    class Host:
        def __init__(self):
            self.name = "host01.example.com"
            self.model = "r640"
            self.host_type = "baremetal"

    host = Host()
    assert extract_host_field(host, "model") == "r640"
    assert extract_host_field(host, "host_type") == "baremetal"


def test_extract_host_field_from_object_with_alias():
    """Test extract_host_field from object with alias"""

    class Host:
        def __init__(self):
            self.host_model = "r640"

    host = Host()
    result = extract_host_field(host, "model", field_aliases=["host_model"])
    assert result == "r640"


def test_extract_host_field_default_value():
    """Test extract_host_field returns default when field not found"""
    host = {"name": "host01.example.com"}
    result = extract_host_field(host, "model", default="unknown")
    assert result == "unknown"


def test_extract_host_field_boolean():
    """Test extract_host_field with boolean values"""
    host = {"can_self_schedule": True}
    result = extract_host_field(host, "can_self_schedule", default=False)
    assert result is True

    host2 = {"can_self_schedule": False}
    result2 = extract_host_field(host2, "can_self_schedule", default=True)
    assert result2 is False


def test_extract_host_field_empty_string_for_name():
    """Test extract_host_field with empty string for name field"""
    result = extract_host_field("", "name", default="N/A")
    assert result == "N/A"


def test_extract_host_field_none_aliases():
    """Test extract_host_field with None aliases (default parameter)"""
    host = {"model": "r640"}
    result = extract_host_field(host, "model")
    assert result == "r640"


# Tests for get_username_short()
def test_get_username_short_with_email():
    """Test extracting username from email address"""
    result = get_username_short("testuser@example.com")
    assert result == "testuser"


def test_get_username_short_with_complex_email():
    """Test extracting username from email with subdomain"""
    result = get_username_short("john.doe@mail.example.com")
    assert result == "john.doe"


def test_get_username_short_without_domain():
    """Test extracting username when already short"""
    result = get_username_short("testuser")
    assert result == "testuser"


def test_get_username_short_with_multiple_at_signs():
    """Test extracting username with multiple @ signs (takes first part)"""
    result = get_username_short("user@domain@extra")
    assert result == "user"


# Tests for get_available_hosts_filter()
def test_get_available_hosts_filter_no_additional():
    """Test getting base filter without additional filters"""
    result = get_available_hosts_filter()
    expected = {"cloud": "cloud01", "retired": False, "broken": False}
    assert result == expected


def test_get_available_hosts_filter_with_model():
    """Test getting filter with model addition"""
    result = get_available_hosts_filter(model="R640")
    expected = {"cloud": "cloud01", "retired": False, "broken": False, "model": "R640"}
    assert result == expected


def test_get_available_hosts_filter_with_multiple_additions():
    """Test getting filter with multiple additional filters"""
    result = get_available_hosts_filter(model="R640", memory__gte=262144)
    expected = {"cloud": "cloud01", "retired": False, "broken": False, "model": "R640", "memory__gte": 262144}
    assert result == expected


def test_get_available_hosts_filter_does_not_modify_original():
    """Test that adding filters doesn't modify the base constant"""
    original_base = AVAILABLE_HOSTS_BASE_FILTER.copy()
    get_available_hosts_filter(model="R640", extra_field="value")
    assert AVAILABLE_HOSTS_BASE_FILTER == original_base


def test_get_available_hosts_filter_override_base():
    """Test that additional filters can override base filters"""
    result = get_available_hosts_filter(cloud="cloud99", retired=True)
    assert result["cloud"] == "cloud99"
    assert result["retired"] is True
    assert result["broken"] is False


# Tests for extract_cloud_name()
def test_extract_cloud_name_from_dict():
    """Test extracting cloud name from dict assignment"""
    assignment = {"id": 1, "cloud": {"name": "cloud02"}}
    result = extract_cloud_name(assignment)
    assert result == "cloud02"


def test_extract_cloud_name_from_dict_with_default():
    """Test extracting cloud name with custom default"""
    assignment = {"id": 1}
    result = extract_cloud_name(assignment, default="unknown")
    assert result == "unknown"


def test_extract_cloud_name_from_dict_empty_cloud():
    """Test extracting cloud name when cloud dict is empty"""
    assignment = {"id": 1, "cloud": {}}
    result = extract_cloud_name(assignment)
    assert result == "N/A"


def test_extract_cloud_name_from_dict_cloud_is_string():
    """Test extracting cloud name when cloud is already a string"""
    assignment = {"id": 1, "cloud": "cloud02"}
    result = extract_cloud_name(assignment)
    assert result == "cloud02"


def test_extract_cloud_name_from_dict_cloud_is_none():
    """Test extracting cloud name when cloud is None"""
    assignment = {"id": 1, "cloud": None}
    result = extract_cloud_name(assignment)
    assert result == "N/A"


def test_extract_cloud_name_from_object():
    """Test extracting cloud name from object assignment"""

    class Cloud:
        def __init__(self):
            self.name = "cloud03"

    class Assignment:
        def __init__(self):
            self.id = 1
            self.cloud = Cloud()

    assignment = Assignment()
    result = extract_cloud_name(assignment)
    assert result == "cloud03"


def test_extract_cloud_name_from_object_no_cloud():
    """Test extracting cloud name from object without cloud attribute"""

    class Assignment:
        def __init__(self):
            self.id = 1

    assignment = Assignment()
    result = extract_cloud_name(assignment)
    assert result == "N/A"


def test_extract_cloud_name_from_object_cloud_no_name():
    """Test extracting cloud name from object where cloud has no name"""

    class Cloud:
        def __init__(self):
            self.id = 2

    class Assignment:
        def __init__(self):
            self.id = 1
            self.cloud = Cloud()

    assignment = Assignment()
    result = extract_cloud_name(assignment, default="missing")
    assert result == "missing"


def test_extract_cloud_name_from_object_cloud_is_none():
    """Test extracting cloud name from object where cloud is None"""

    class Assignment:
        def __init__(self):
            self.id = 1
            self.cloud = None

    assignment = Assignment()
    result = extract_cloud_name(assignment)
    assert result == "N/A"


# Tests for extract_cloud_number()
def test_extract_cloud_number_standard():
    assert extract_cloud_number("cloud06") == 6
    assert extract_cloud_number("cloud21") == 21
    assert extract_cloud_number("cloud01") == 1


def test_extract_cloud_number_no_digits():
    result = extract_cloud_number("nodigits")
    assert result == float("inf")


def test_extract_cloud_number_empty():
    result = extract_cloud_number("")
    assert result == float("inf")


# Tests for extract_assignment_id()
def test_extract_assignment_id_from_dict():
    """Test extracting assignment ID from dict"""
    assignment = {"id": 42, "owner": "test"}
    result = extract_assignment_id(assignment)
    assert result == 42


def test_extract_assignment_id_from_dict_with_default():
    """Test extracting assignment ID with custom default"""
    assignment = {"owner": "test"}
    result = extract_assignment_id(assignment, default="unknown")
    assert result == "unknown"


def test_extract_assignment_id_from_dict_zero_id():
    """Test extracting assignment ID when ID is 0 (valid ID)"""
    assignment = {"id": 0, "owner": "test"}
    result = extract_assignment_id(assignment)
    assert result == 0


def test_extract_assignment_id_from_object():
    """Test extracting assignment ID from object"""

    class Assignment:
        def __init__(self):
            self.id = 99
            self.owner = "test"

    assignment = Assignment()
    result = extract_assignment_id(assignment)
    assert result == 99


def test_extract_assignment_id_from_object_no_id():
    """Test extracting assignment ID from object without id attribute"""

    class Assignment:
        def __init__(self):
            self.owner = "test"

    assignment = Assignment()
    result = extract_assignment_id(assignment)
    assert result == "N/A"


def test_extract_assignment_id_from_object_custom_default():
    """Test extracting assignment ID from object with custom default"""

    class Assignment:
        def __init__(self):
            self.owner = "test"

    assignment = Assignment()
    result = extract_assignment_id(assignment, default=-1)
    assert result == -1


# Tests for get_ssl_indicator()
def test_get_ssl_indicator_https_verified():
    """Test SSL indicator for HTTPS with verification"""
    symbol, color = get_ssl_indicator("https://example.com", True)
    assert symbol == "✓"
    assert color == "\033[1;32m"


def test_get_ssl_indicator_https_unverified():
    """Test SSL indicator for HTTPS without verification"""
    symbol, color = get_ssl_indicator("https://example.com", False)
    assert symbol == "!"
    assert color == "\033[1;32m"


def test_get_ssl_indicator_http():
    """Test SSL indicator for HTTP"""
    symbol, color = get_ssl_indicator("http://example.com", True)
    assert symbol == "✗"
    assert color == "\033[1;33m"


def test_get_ssl_indicator_http_unverified():
    """Test SSL indicator for HTTP (verify flag doesn't matter)"""
    symbol, color = get_ssl_indicator("http://example.com", False)
    assert symbol == "✗"
    assert color == "\033[1;33m"


# Tests for get_ssl_status_text()
def test_get_ssl_status_text_https_verified():
    """Test SSL status text for HTTPS with verification"""
    result = get_ssl_status_text("https://example.com", True)
    assert result == "HTTPS (verified)"


def test_get_ssl_status_text_https_unverified():
    """Test SSL status text for HTTPS without verification"""
    result = get_ssl_status_text("https://example.com", False)
    assert result == "HTTPS (unverified)"


def test_get_ssl_status_text_http():
    """Test SSL status text for HTTP"""
    result = get_ssl_status_text("http://example.com", True)
    assert result == "HTTP"


def test_get_ssl_status_text_http_unverified():
    """Test SSL status text for HTTP (verify flag doesn't matter)"""
    result = get_ssl_status_text("http://example.com", False)
    assert result == "HTTP"


def test_format_schedule_datetime_with_milliseconds():
    """Test format_schedule_datetime with ISO format including milliseconds"""
    result = format_schedule_datetime("2026-05-07T13:00:00.000Z")
    assert result == "2026-05-07 13:00"


def test_format_schedule_datetime_without_milliseconds():
    """Test format_schedule_datetime with ISO format without milliseconds"""
    result = format_schedule_datetime("2026-05-07T13:00:00Z")
    assert result == "2026-05-07 13:00:00"


def test_format_schedule_datetime_plain():
    """Test format_schedule_datetime with already formatted string"""
    result = format_schedule_datetime("2026-05-07 13:00")
    assert result == "2026-05-07 13:00"


def test_validate_cloud_exists_true():
    """Test validate_cloud_exists when cloud exists"""
    mock_api = MagicMock()
    mock_api.filter_clouds.return_value = [{"name": "cloud02"}]

    result = validate_cloud_exists(mock_api, "cloud02")

    assert result is True
    mock_api.filter_clouds.assert_called_once_with({"name": "cloud02"})


def test_validate_cloud_exists_false():
    """Test validate_cloud_exists when cloud does not exist"""
    mock_api = MagicMock()
    mock_api.filter_clouds.return_value = []

    result = validate_cloud_exists(mock_api, "cloud99")

    assert result is False
    mock_api.filter_clouds.assert_called_once_with({"name": "cloud99"})


OS_LIST = [
    {"Id": 1, "Title": "Rocky Linux 9.8", "Release Name": "", "Family": "Redhat"},
    {"Id": 2, "Title": "Fedora 42", "Release Name": "", "Family": "Redhat"},
    {"Id": 3, "Title": "RHEL 10.0", "Release Name": "", "Family": "Redhat"},
]


def test_resolve_os_exact_title():
    mock_api = MagicMock()
    mock_api.get_os_list.return_value = OS_LIST
    title, error = resolve_os(mock_api, "RHEL 10.0")
    assert title == "RHEL 10.0"
    assert error is None


def test_resolve_os_case_insensitive():
    mock_api = MagicMock()
    mock_api.get_os_list.return_value = OS_LIST
    title, error = resolve_os(mock_api, "rhel 10.0")
    assert title == "RHEL 10.0"
    assert error is None
    title, error = resolve_os(mock_api, "fedora 42")
    assert title == "Fedora 42"
    assert error is None


def test_resolve_os_by_id():
    mock_api = MagicMock()
    mock_api.get_os_list.return_value = OS_LIST
    title, error = resolve_os(mock_api, "2")
    assert title == "Fedora 42"
    assert error is None
    title, error = resolve_os(mock_api, "3")
    assert title == "RHEL 10.0"
    assert error is None


def test_resolve_os_no_match():
    mock_api = MagicMock()
    mock_api.get_os_list.return_value = OS_LIST
    title, error = resolve_os(mock_api, "--help")
    assert title is None
    assert "not found" in error
    assert "Available:" in error


def test_resolve_os_no_match_shows_available():
    mock_api = MagicMock()
    mock_api.get_os_list.return_value = OS_LIST
    title, error = resolve_os(mock_api, "Windows 11")
    assert title is None
    assert "Rocky Linux 9.8" in error
    assert "Fedora 42" in error
    assert "RHEL 10.0" in error


def test_resolve_os_empty_list():
    mock_api = MagicMock()
    mock_api.get_os_list.return_value = []
    title, error = resolve_os(mock_api, "RHEL 10.0")
    assert title is None
    assert "not found" in error


def test_resolve_os_none_list():
    mock_api = MagicMock()
    mock_api.get_os_list.return_value = None
    title, error = resolve_os(mock_api, "RHEL 10.0")
    assert title is None
    assert "not found" in error
