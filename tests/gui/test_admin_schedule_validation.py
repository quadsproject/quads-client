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

if __name__ == "__main__":
    unittest.main()
