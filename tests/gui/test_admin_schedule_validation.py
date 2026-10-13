"""Tests for hostname validation in admin schedule view"""

import unittest
from unittest.mock import Mock


class TestAdminScheduleValidation(unittest.TestCase):
    """Test hostname validation in admin schedule view"""

    def setUp(self):
        """Set up test fixtures"""
        self.api = Mock()

    def _validate_hosts_availability(self, hostnames, start_date, end_date):
        """Extracted validation logic from AdminScheduleView for testing"""
        errors = []

        for hostname in hostnames:
            hostname = hostname.strip()
            if not hostname:
                continue

            try:
                host = self.api.get_host(hostname)

                if not host:
                    errors.append(f"{hostname}: Host not found (typo?)")
                    continue

                if host.get("broken"):
                    errors.append(f"{hostname}: Host is marked as broken")
                    continue

                if host.get("retired"):
                    errors.append(f"{hostname}: Host is retired")
                    continue

                is_available = self.api.is_available(hostname, start_date, end_date)

                if not is_available:
                    errors.append(f"{hostname}: Not available for {start_date} to {end_date}")
                    continue

            except Exception as e:
                errors.append(f"{hostname}: Error checking availability ({str(e)})")

        return (len(errors) == 0, errors)

    def test_validate_hosts_availability_all_available(self):
        """Test validation passes when all hosts are available"""

        def mock_get_host(hostname):
            return {"name": hostname, "broken": False, "retired": False}

        self.api.get_host = mock_get_host
        self.api.is_available = Mock(return_value=True)

        hostnames = ["host01.example.com", "host02.example.com"]
        start = "2026-05-11 22:00"
        end = "2026-05-25 22:00"

        is_valid, errors = self._validate_hosts_availability(hostnames, start, end)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertEqual(self.api.is_available.call_count, 2)

    def test_validate_hosts_availability_not_found(self):
        """Test validation fails for non-existent hostname"""
        self.api.get_host = Mock(return_value=None)

        hostnames = ["bogus-host.example.com"]
        start = "2026-05-11 22:00"
        end = "2026-05-25 22:00"

        is_valid, errors = self._validate_hosts_availability(hostnames, start, end)

        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("bogus-host.example.com", errors[0])
        self.assertIn("not found", errors[0].lower())

    def test_validate_hosts_availability_broken(self):
        """Test validation fails for broken host"""
        self.api.get_host = Mock(return_value={"name": "broken-host.example.com", "broken": True, "retired": False})

        hostnames = ["broken-host.example.com"]
        start = "2026-05-11 22:00"
        end = "2026-05-25 22:00"

        is_valid, errors = self._validate_hosts_availability(hostnames, start, end)

        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("broken-host.example.com", errors[0])
        self.assertIn("broken", errors[0].lower())

    def test_validate_hosts_availability_retired(self):
        """Test validation fails for retired host"""
        self.api.get_host = Mock(return_value={"name": "retired-host.example.com", "broken": False, "retired": True})

        hostnames = ["retired-host.example.com"]
        start = "2026-05-11 22:00"
        end = "2026-05-25 22:00"

        is_valid, errors = self._validate_hosts_availability(hostnames, start, end)

        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("retired-host.example.com", errors[0])
        self.assertIn("retired", errors[0].lower())

    def test_validate_hosts_availability_not_available(self):
        """Test validation fails when host is not available for date range"""
        self.api.get_host = Mock(return_value={"name": "busy-host.example.com", "broken": False, "retired": False})
        self.api.is_available = Mock(return_value=False)

        hostnames = ["busy-host.example.com"]
        start = "2026-05-11 22:00"
        end = "2026-05-25 22:00"

        is_valid, errors = self._validate_hosts_availability(hostnames, start, end)

        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("busy-host.example.com", errors[0])
        self.assertIn("Not available", errors[0])
        self.assertIn("2026-05-11 22:00", errors[0])
        self.assertIn("2026-05-25 22:00", errors[0])

    def test_validate_hosts_availability_mixed_results(self):
        """Test validation with mix of available and unavailable hosts"""

        def mock_get_host(hostname):
            if hostname == "available-host.example.com":
                return {"name": hostname, "broken": False, "retired": False}
            elif hostname == "broken-host.example.com":
                return {"name": hostname, "broken": True, "retired": False}
            else:
                return None

        def mock_is_available(hostname, start, end):
            return hostname == "available-host.example.com"

        self.api.get_host = mock_get_host
        self.api.is_available = mock_is_available

        hostnames = ["available-host.example.com", "broken-host.example.com", "missing-host.example.com"]
        start = "2026-05-11 22:00"
        end = "2026-05-25 22:00"

        is_valid, errors = self._validate_hosts_availability(hostnames, start, end)

        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 2)

    def test_validate_hosts_availability_empty_list(self):
        """Test validation with empty hostname list"""
        hostnames = []
        start = "2026-05-11 22:00"
        end = "2026-05-25 22:00"

        is_valid, errors = self._validate_hosts_availability(hostnames, start, end)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_hosts_availability_api_exception(self):
        """Test validation handles API exceptions gracefully"""
        self.api.get_host = Mock(side_effect=Exception("API error"))

        hostnames = ["error-host.example.com"]
        start = "2026-05-11 22:00"
        end = "2026-05-25 22:00"

        is_valid, errors = self._validate_hosts_availability(hostnames, start, end)

        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("error-host.example.com", errors[0])
        self.assertIn("Error checking", errors[0])


class TestAdminScheduleFreeClouds(unittest.TestCase):
    """Test free cloud selection in admin schedule view"""

    def setUp(self):
        """Set up test fixtures"""
        self.api = Mock()

    def _get_free_clouds(self):
        """Extracted free cloud logic from AdminScheduleView for testing"""
        from quads_client.utils import extract_cloud_number

        try:
            names = [cloud.get("name") for cloud in (self.api.get_free_clouds() or [])]
            return sorted(names, key=extract_cloud_number)
        except Exception:
            return []

    def test_free_clouds_sorted_numerically(self):
        """Free clouds are sorted by cloud number, not lexically"""
        self.api.get_free_clouds = Mock(return_value=[{"name": "cloud10"}, {"name": "cloud2"}, {"name": "cloud1"}])

        result = self._get_free_clouds()

        self.assertEqual(result, ["cloud1", "cloud2", "cloud10"])

    def test_free_clouds_first_is_next_free(self):
        """First entry is the lowest-numbered free cloud (next free for ssm)"""
        self.api.get_free_clouds = Mock(return_value=[{"name": "cloud09"}, {"name": "cloud03"}])

        result = self._get_free_clouds()

        self.assertEqual(result[0], "cloud03")

    def test_free_clouds_empty(self):
        """No free clouds returns an empty list"""
        self.api.get_free_clouds = Mock(return_value=[])

        self.assertEqual(self._get_free_clouds(), [])

    def test_free_clouds_none_response(self):
        """A None response is treated as no free clouds"""
        self.api.get_free_clouds = Mock(return_value=None)

        self.assertEqual(self._get_free_clouds(), [])


class TestAdminScheduleUtilsImports(unittest.TestCase):
    """Guard the helpers AdminScheduleView imports at module load"""

    def test_required_utils_helpers_exist(self):
        """extract_assignment_id, extract_cloud_name, extract_cloud_number import"""
        from quads_client.utils import (
            extract_assignment_id,
            extract_cloud_name,
            extract_cloud_number,
        )

        self.assertTrue(callable(extract_assignment_id))
        self.assertTrue(callable(extract_cloud_name))
        self.assertTrue(callable(extract_cloud_number))


class TestAdminScheduleLoad(unittest.TestCase):
    """Test the schedule fetch/display mapping in admin schedule view"""

    def _build_rows(self, assignments):
        """Extracted on_loaded row-building from AdminScheduleView for testing

        Mirrors the view method (tkinter is unavailable headless) while
        exercising the real extract_assignment_id / extract_cloud_name helpers.
        """
        from quads_client.utils import extract_assignment_id, extract_cloud_name

        rows = []
        if not assignments:
            return rows

        for assignment in assignments:
            if isinstance(assignment, dict):
                assignment_id = extract_assignment_id(assignment)
                cloud_name = extract_cloud_name(assignment)
                description = assignment.get("description", "No description")
                owner = assignment.get("owner", "N/A")
                validated = "✓" if assignment.get("validated") else "○"
                rows.append((assignment_id, cloud_name, description, owner, validated))

        return rows

    def test_load_maps_assignments_to_rows(self):
        """Fetched assignments are mapped to display rows"""
        assignments = [
            {"id": 7, "cloud": {"name": "cloud03"}, "description": "demo", "owner": "alice", "validated": True},
        ]

        rows = self._build_rows(assignments)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], 7)
        self.assertEqual(rows[0][1], "cloud03")
        self.assertEqual(rows[0][2], "demo")
        self.assertEqual(rows[0][3], "alice")
        self.assertEqual(rows[0][4], "✓")

    def test_load_uses_defaults_for_missing_fields(self):
        """Missing optional fields fall back to defaults"""
        rows = self._build_rows([{"id": 1, "cloud": {"name": "cloud01"}}])

        self.assertEqual(rows[0][2], "No description")
        self.assertEqual(rows[0][3], "N/A")
        self.assertEqual(rows[0][4], "○")

    def test_load_empty_assignments(self):
        """No assignments produces no rows"""
        self.assertEqual(self._build_rows([]), [])
        self.assertEqual(self._build_rows(None), [])


if __name__ == "__main__":
    unittest.main()
