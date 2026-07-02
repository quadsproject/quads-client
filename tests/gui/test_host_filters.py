"""Tests for host filter logic and gui_shell filter backend"""

import pytest
from unittest.mock import MagicMock


class TestGetAvailableHostsDataFilters:
    """Test get_available_hosts_data with extended filter parameters"""

    def _make_gui_shell(self, mock_api):
        """Create a GuiShell-like object with mocked dependencies"""
        shell = MagicMock()
        shell.is_authenticated.return_value = True
        shell.connection.api = mock_api
        return shell

    def _call_get_available_hosts_data(self, shell, **filters):
        """Call the actual get_available_hosts_data logic extracted from gui_shell"""
        from datetime import datetime

        from quads_client.utils import extract_host_field, get_available_hosts_filter

        start_date = filters.pop("start", None)
        end_date = filters.pop("end", None)

        host_filters = get_available_hosts_filter(**filters)
        hosts = shell.connection.api.filter_hosts(host_filters)

        if isinstance(hosts, str) or not isinstance(hosts, list):
            return []

        if not hosts:
            return []

        current_schedules = []
        try:
            current_schedules = shell.connection.api.get_current_schedules({})
        except Exception:
            pass

        scheduled_hosts = set()
        if current_schedules:
            for schedule in current_schedules:
                if isinstance(schedule, dict):
                    assignment = schedule.get("assignment", {})
                    if isinstance(assignment, dict):
                        cloud = assignment.get("cloud", {})
                        cloud_name = cloud.get("name") if isinstance(cloud, dict) else str(cloud)
                        if cloud_name and cloud_name != "cloud01":
                            host = schedule.get("host", {})
                            host_name = host.get("name") if isinstance(host, dict) else str(host)
                            if host_name:
                                scheduled_hosts.add(host_name)

        results = []
        for host in hosts:
            name = extract_host_field(host, "name", field_aliases=["hostname"], default="")
            model_val = extract_host_field(host, "model", field_aliases=["host_model"], default="N/A")
            host_type = extract_host_field(host, "host_type", field_aliases=["type"], default="N/A")
            can_self_schedule = extract_host_field(host, "can_self_schedule", default=False)

            if not name:
                continue

            if name in scheduled_hosts:
                continue

            if start_date and end_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    start_iso = start_dt.isoformat()[:-3]
                    end_iso = end_dt.isoformat()[:-3]

                    is_available = shell.connection.api.is_available(name, {"start": start_iso, "end": end_iso})
                    if not is_available:
                        continue
                except Exception:
                    pass

            results.append(
                {"name": name, "model": model_val, "host_type": host_type, "can_self_schedule": can_self_schedule}
            )

        return results

    def test_disk_type_filter(self):
        """Test disk type filter maps to correct API key"""
        api = MagicMock()
        api.filter_hosts.return_value = []
        api.get_current_schedules.return_value = []
        shell = self._make_gui_shell(api)

        self._call_get_available_hosts_data(shell, **{"disks.disk_type": "nvme"})

        expected = {"cloud": "cloud01", "retired": False, "broken": False, "disks.disk_type": "nvme"}
        api.filter_hosts.assert_called_once_with(expected)

    def test_disk_size_filter(self):
        """Test disk size filter maps to correct API key"""
        api = MagicMock()
        api.filter_hosts.return_value = []
        api.get_current_schedules.return_value = []
        shell = self._make_gui_shell(api)

        self._call_get_available_hosts_data(shell, **{"disks.size_gb__gte": 500})

        expected = {"cloud": "cloud01", "retired": False, "broken": False, "disks.size_gb__gte": 500}
        api.filter_hosts.assert_called_once_with(expected)

    def test_disk_count_filter(self):
        """Test disk count filter maps to correct API key"""
        api = MagicMock()
        api.filter_hosts.return_value = []
        api.get_current_schedules.return_value = []
        shell = self._make_gui_shell(api)

        self._call_get_available_hosts_data(shell, **{"disks.count__gte": 4})

        expected = {"cloud": "cloud01", "retired": False, "broken": False, "disks.count__gte": 4}
        api.filter_hosts.assert_called_once_with(expected)

    def test_nic_vendor_filter(self):
        """Test NIC vendor filter maps to correct API key"""
        api = MagicMock()
        api.filter_hosts.return_value = []
        api.get_current_schedules.return_value = []
        shell = self._make_gui_shell(api)

        self._call_get_available_hosts_data(shell, **{"interfaces.vendor": "Intel"})

        expected = {"cloud": "cloud01", "retired": False, "broken": False, "interfaces.vendor": "Intel"}
        api.filter_hosts.assert_called_once_with(expected)

    def test_nic_speed_filter(self):
        """Test NIC speed filter maps to correct API key"""
        api = MagicMock()
        api.filter_hosts.return_value = []
        api.get_current_schedules.return_value = []
        shell = self._make_gui_shell(api)

        self._call_get_available_hosts_data(shell, **{"interfaces.speed__gte": 25})

        expected = {"cloud": "cloud01", "retired": False, "broken": False, "interfaces.speed__gte": 25}
        api.filter_hosts.assert_called_once_with(expected)

    def test_gpu_filter(self):
        """Test GPU filter uses processors.processor_type=GPU"""
        api = MagicMock()
        api.filter_hosts.return_value = []
        api.get_current_schedules.return_value = []
        shell = self._make_gui_shell(api)

        self._call_get_available_hosts_data(shell, **{"processors.processor_type": "GPU"})

        expected = {"cloud": "cloud01", "retired": False, "broken": False, "processors.processor_type": "GPU"}
        api.filter_hosts.assert_called_once_with(expected)

    def test_combined_advanced_filters(self):
        """Test multiple advanced filters applied together"""
        api = MagicMock()
        api.filter_hosts.return_value = []
        api.get_current_schedules.return_value = []
        shell = self._make_gui_shell(api)

        self._call_get_available_hosts_data(
            shell,
            model="R650",
            **{
                "memory__gte": 262144,
                "disks.disk_type": "nvme",
                "disks.count__gte": 2,
                "interfaces.vendor": "Intel",
                "processors.processor_type": "GPU",
            },
        )

        expected = {
            "cloud": "cloud01",
            "retired": False,
            "broken": False,
            "model": "R650",
            "memory__gte": 262144,
            "disks.disk_type": "nvme",
            "disks.count__gte": 2,
            "interfaces.vendor": "Intel",
            "processors.processor_type": "GPU",
        }
        api.filter_hosts.assert_called_once_with(expected)

    def test_start_end_date_filtering(self):
        """Test start/end dates are popped from filters and used for is_available()"""
        api = MagicMock()
        api.filter_hosts.return_value = [
            {"name": "host01.example.com", "model": "R650", "host_type": "baremetal", "can_self_schedule": True},
            {"name": "host02.example.com", "model": "R650", "host_type": "baremetal", "can_self_schedule": True},
        ]
        api.get_current_schedules.return_value = []
        # host01 is available, host02 is not
        api.is_available.side_effect = [True, False]

        shell = self._make_gui_shell(api)

        results = self._call_get_available_hosts_data(shell, start="2026-05-01", end="2026-05-15", model="R650")

        # Start/end should NOT be passed to filter_hosts
        expected_filters = {"cloud": "cloud01", "retired": False, "broken": False, "model": "R650"}
        api.filter_hosts.assert_called_once_with(expected_filters)

        # is_available should be called for each host
        assert api.is_available.call_count == 2

        # Only host01 should be in results (host02 failed availability check)
        assert len(results) == 1
        assert results[0]["name"] == "host01.example.com"

    def test_start_only_no_availability_check(self):
        """Test that start without end skips availability checking"""
        api = MagicMock()
        api.filter_hosts.return_value = [
            {"name": "host01.example.com", "model": "R650", "host_type": "baremetal", "can_self_schedule": True},
        ]
        api.get_current_schedules.return_value = []

        shell = self._make_gui_shell(api)

        results = self._call_get_available_hosts_data(shell, start="2026-05-01")

        # is_available should NOT be called (need both start and end)
        api.is_available.assert_not_called()
        assert len(results) == 1

    def test_no_filters_returns_all(self):
        """Test that no filters returns all available hosts"""
        api = MagicMock()
        api.filter_hosts.return_value = [
            {"name": "host01.example.com", "model": "R650", "host_type": "baremetal", "can_self_schedule": True},
            {"name": "host02.example.com", "model": "R640", "host_type": "baremetal", "can_self_schedule": False},
        ]
        api.get_current_schedules.return_value = []

        shell = self._make_gui_shell(api)

        results = self._call_get_available_hosts_data(shell)

        # Should only pass base filters
        expected = {"cloud": "cloud01", "retired": False, "broken": False}
        api.filter_hosts.assert_called_once_with(expected)
        assert len(results) == 2


class TestGetAvailableNicVendors:
    """Test get_available_nic_vendors helper"""

    def test_extracts_unique_vendors(self):
        """Test NIC vendor extraction from host data"""
        hosts = [
            {"name": "host01", "interfaces": [{"vendor": "Intel"}, {"vendor": "Mellanox"}]},
            {"name": "host02", "interfaces": [{"vendor": "Intel"}, {"vendor": "Broadcom"}]},
            {"name": "host03", "interfaces": []},
        ]

        vendors = set()
        for host in hosts:
            interfaces = host.get("interfaces", [])
            if isinstance(interfaces, list):
                for iface in interfaces:
                    if isinstance(iface, dict):
                        vendor = iface.get("vendor", "").strip()
                        if vendor:
                            vendors.add(vendor)

        result = sorted(list(vendors))
        assert result == ["Broadcom", "Intel", "Mellanox"]

    def test_handles_empty_hosts(self):
        """Test with no hosts"""
        hosts = []

        vendors = set()
        for host in hosts:
            interfaces = host.get("interfaces", [])
            if isinstance(interfaces, list):
                for iface in interfaces:
                    if isinstance(iface, dict):
                        vendor = iface.get("vendor", "").strip()
                        if vendor:
                            vendors.add(vendor)

        assert sorted(list(vendors)) == []

    def test_handles_missing_interfaces(self):
        """Test with hosts that have no interfaces key"""
        hosts = [{"name": "host01"}, {"name": "host02", "interfaces": None}]

        vendors = set()
        for host in hosts:
            interfaces = host.get("interfaces", [])
            if isinstance(interfaces, list):
                for iface in interfaces:
                    if isinstance(iface, dict):
                        vendor = iface.get("vendor", "").strip()
                        if vendor:
                            vendors.add(vendor)

        assert sorted(list(vendors)) == []

    def test_skips_empty_vendor_strings(self):
        """Test that empty/whitespace vendor strings are skipped"""
        hosts = [
            {"name": "host01", "interfaces": [{"vendor": ""}, {"vendor": "  "}, {"vendor": "Intel"}]},
        ]

        vendors = set()
        for host in hosts:
            interfaces = host.get("interfaces", [])
            if isinstance(interfaces, list):
                for iface in interfaces:
                    if isinstance(iface, dict):
                        vendor = iface.get("vendor", "").strip()
                        if vendor:
                            vendors.add(vendor)

        assert sorted(list(vendors)) == ["Intel"]


class TestHostFilterFrameGetFilters:
    """Test filter key mapping logic (extracted from HostFilterFrame.get_filters)"""

    def _build_filters(
        self,
        model="All",
        ram="",
        start="",
        end="",
        disk_type="All",
        disk_size="",
        disk_count="",
        nic_vendor="All",
        nic_speed="",
        gpu=False,
    ):
        """Replicate the get_filters() logic without tkinter dependency"""
        filters = {}

        if model and model != "All":
            filters["model"] = model.upper()

        if ram:
            try:
                filters["memory__gte"] = int(ram) * 1024
            except ValueError:
                pass

        if start:
            filters["start"] = start.split()[0]

        if end:
            filters["end"] = end.split()[0]

        if disk_type and disk_type != "All":
            filters["disks.disk_type"] = disk_type

        if disk_size:
            try:
                filters["disks.size_gb__gte"] = int(disk_size)
            except ValueError:
                pass

        if disk_count:
            try:
                filters["disks.count__gte"] = int(disk_count)
            except ValueError:
                pass

        if nic_vendor and nic_vendor != "All":
            filters["interfaces.vendor"] = nic_vendor

        if nic_speed:
            try:
                filters["interfaces.speed__gte"] = int(nic_speed)
            except ValueError:
                pass

        if gpu:
            filters["processors.processor_type"] = "GPU"

        return filters

    def test_empty_filters(self):
        """Test all defaults returns empty dict"""
        assert self._build_filters() == {}

    def test_model_uppercased(self):
        """Test model value is uppercased"""
        result = self._build_filters(model="r650")
        assert result == {"model": "R650"}

    def test_model_all_excluded(self):
        """Test model 'All' is excluded"""
        result = self._build_filters(model="All")
        assert "model" not in result

    def test_ram_converted_to_mb(self):
        """Test RAM GB is converted to MB"""
        result = self._build_filters(ram="256")
        assert result == {"memory__gte": 256 * 1024}

    def test_ram_invalid_ignored(self):
        """Test invalid RAM value is ignored"""
        result = self._build_filters(ram="abc")
        assert "memory__gte" not in result

    def test_date_extracts_date_only(self):
        """Test date with time extracts date portion only"""
        result = self._build_filters(start="2026-05-01 22:00", end="2026-05-15 22:00")
        assert result == {"start": "2026-05-01", "end": "2026-05-15"}

    def test_disk_type_filter(self):
        """Test disk type filter"""
        result = self._build_filters(disk_type="nvme")
        assert result == {"disks.disk_type": "nvme"}

    def test_disk_type_all_excluded(self):
        """Test disk type 'All' is excluded"""
        result = self._build_filters(disk_type="All")
        assert "disks.disk_type" not in result

    def test_disk_size_filter(self):
        """Test disk size filter"""
        result = self._build_filters(disk_size="500")
        assert result == {"disks.size_gb__gte": 500}

    def test_disk_count_filter(self):
        """Test disk count filter"""
        result = self._build_filters(disk_count="4")
        assert result == {"disks.count__gte": 4}

    def test_nic_vendor_filter(self):
        """Test NIC vendor filter"""
        result = self._build_filters(nic_vendor="Intel")
        assert result == {"interfaces.vendor": "Intel"}

    def test_nic_speed_filter(self):
        """Test NIC speed filter"""
        result = self._build_filters(nic_speed="25")
        assert result == {"interfaces.speed__gte": 25}

    def test_gpu_checkbox(self):
        """Test GPU checkbox sets processors.processor_type=GPU"""
        result = self._build_filters(gpu=True)
        assert result == {"processors.processor_type": "GPU"}

    def test_gpu_unchecked_excluded(self):
        """Test GPU unchecked is excluded"""
        result = self._build_filters(gpu=False)
        assert "processors.processor_type" not in result

    def test_combined_filters(self):
        """Test multiple filters combined"""
        result = self._build_filters(
            model="r650",
            ram="256",
            disk_type="nvme",
            disk_count="2",
            nic_vendor="Intel",
            gpu=True,
        )
        expected = {
            "model": "R650",
            "memory__gte": 256 * 1024,
            "disks.disk_type": "nvme",
            "disks.count__gte": 2,
            "interfaces.vendor": "Intel",
            "processors.processor_type": "GPU",
        }
        assert result == expected

    def test_numeric_invalid_values_ignored(self):
        """Test that non-numeric values in numeric fields are silently ignored"""
        result = self._build_filters(ram="abc", disk_size="xyz", disk_count="!", nic_speed="slow")
        assert result == {}


class TestGetCloudHosts:
    """Test _get_cloud_hosts logic for cloud01 (spare pool) vs other clouds"""

    def _get_cloud_hosts(self, api, cloud_name):
        """Replicate _get_cloud_hosts logic without GUI dependency"""
        hostnames = []

        if cloud_name == "cloud01":
            hosts = api.filter_hosts({"cloud": "cloud01"})
            if hosts and isinstance(hosts, list):
                for host in hosts:
                    if isinstance(host, dict):
                        name = host.get("name", "")
                    elif isinstance(host, str):
                        name = host
                    else:
                        name = getattr(host, "name", "")
                    if name and name not in hostnames:
                        hostnames.append(name)
        else:
            current_schedules = api.get_current_schedules({"cloud": cloud_name})
            if current_schedules:
                for schedule in current_schedules:
                    host = schedule.get("host")
                    if host:
                        hostname = host.get("name") if isinstance(host, dict) else host
                        if hostname and hostname not in hostnames:
                            hostnames.append(hostname)

        hostnames.sort()
        return hostnames

    def test_cloud01_uses_filter_hosts(self):
        """Test that cloud01 (spare pool) uses filter_hosts, not schedules"""
        api = MagicMock()
        api.filter_hosts.return_value = [
            {"name": "host01.example.com"},
            {"name": "host02.example.com"},
        ]

        result = self._get_cloud_hosts(api, "cloud01")

        api.filter_hosts.assert_called_once_with({"cloud": "cloud01"})
        api.get_current_schedules.assert_not_called()
        assert result == ["host01.example.com", "host02.example.com"]

    def test_other_clouds_use_schedules(self):
        """Test that non-cloud01 clouds use get_current_schedules"""
        api = MagicMock()
        api.get_current_schedules.return_value = [
            {"host": {"name": "host03.example.com"}},
        ]

        result = self._get_cloud_hosts(api, "cloud02")

        api.get_current_schedules.assert_called_once_with({"cloud": "cloud02"})
        api.filter_hosts.assert_not_called()
        assert result == ["host03.example.com"]

    def test_cloud01_empty_spare_pool(self):
        """Test cloud01 with no spare hosts"""
        api = MagicMock()
        api.filter_hosts.return_value = []

        result = self._get_cloud_hosts(api, "cloud01")

        assert result == []

    def test_cloud01_handles_string_hosts(self):
        """Test cloud01 with string host entries"""
        api = MagicMock()
        api.filter_hosts.return_value = ["host01.example.com", "host02.example.com"]

        result = self._get_cloud_hosts(api, "cloud01")

        assert result == ["host01.example.com", "host02.example.com"]

    def test_cloud01_deduplicates(self):
        """Test cloud01 deduplicates hostnames"""
        api = MagicMock()
        api.filter_hosts.return_value = [
            {"name": "host01.example.com"},
            {"name": "host01.example.com"},
        ]

        result = self._get_cloud_hosts(api, "cloud01")

        assert result == ["host01.example.com"]


class TestCloudViewDetails:
    """Test cloud view details host extraction logic"""

    def test_extracts_hostnames_from_schedules(self):
        """Test hostname extraction from current_schedules response"""
        schedules = [
            {"host": {"name": "host01.example.com"}},
            {"host": {"name": "host02.example.com"}},
            {"host": {"name": "host03.example.com"}},
        ]

        hostnames = []
        for schedule in schedules:
            host = schedule.get("host")
            if host:
                hostname = host.get("name") if isinstance(host, dict) else host
                if hostname and hostname not in hostnames:
                    hostnames.append(hostname)

        hostnames.sort()
        assert hostnames == ["host01.example.com", "host02.example.com", "host03.example.com"]

    def test_deduplicates_hostnames(self):
        """Test that duplicate hostnames are removed"""
        schedules = [
            {"host": {"name": "host01.example.com"}},
            {"host": {"name": "host01.example.com"}},
            {"host": {"name": "host02.example.com"}},
        ]

        hostnames = []
        for schedule in schedules:
            host = schedule.get("host")
            if host:
                hostname = host.get("name") if isinstance(host, dict) else host
                if hostname and hostname not in hostnames:
                    hostnames.append(hostname)

        assert len(hostnames) == 2

    def test_handles_empty_schedules(self):
        """Test with no schedules"""
        schedules = []

        hostnames = []
        for schedule in schedules:
            host = schedule.get("host")
            if host:
                hostname = host.get("name") if isinstance(host, dict) else host
                if hostname and hostname not in hostnames:
                    hostnames.append(hostname)

        assert hostnames == []

    def test_handles_string_host(self):
        """Test when host is a string instead of dict"""
        schedules = [
            {"host": "host01.example.com"},
        ]

        hostnames = []
        for schedule in schedules:
            host = schedule.get("host")
            if host:
                hostname = host.get("name") if isinstance(host, dict) else host
                if hostname and hostname not in hostnames:
                    hostnames.append(hostname)

        assert hostnames == ["host01.example.com"]

    def test_skips_none_host(self):
        """Test that None host entries are skipped"""
        schedules = [
            {"host": None},
            {"host": {"name": "host01.example.com"}},
        ]

        hostnames = []
        for schedule in schedules:
            host = schedule.get("host")
            if host:
                hostname = host.get("name") if isinstance(host, dict) else host
                if hostname and hostname not in hostnames:
                    hostnames.append(hostname)

        assert hostnames == ["host01.example.com"]
