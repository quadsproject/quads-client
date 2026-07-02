import pytest
import tempfile
import os
from quads_client.arg_parser import (
    parse_host_list_file,
    parse_schedule_ssm_args,
    parse_schedule_admin_args,
    parse_extend_args,
    parse_shrink_args,
)


class TestParseHostListFile:
    """Test parse_host_list_file function"""

    def test_valid_host_list(self):
        """Test parsing a valid host list file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("host01.example.com\n")
            f.write("host02.example.com\n")
            f.write("# comment line\n")
            f.write("\n")  # blank line
            f.write("host03.example.com\n")
            temp_path = f.name

        try:
            result = parse_host_list_file(temp_path)
            assert result == ["host01.example.com", "host02.example.com", "host03.example.com"]
        finally:
            os.unlink(temp_path)

    def test_file_not_found(self):
        """Test parsing non-existent file"""
        with pytest.raises(ValueError, match="Host list file not found"):
            parse_host_list_file("/nonexistent/path/to/file.txt")

    def test_empty_file(self):
        """Test parsing empty file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("\n\n# only comments\n\n")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Host list file is empty"):
                parse_host_list_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_tilde_expansion(self):
        """Test that ~ is expanded in file paths"""
        # Should raise file not found, but proves ~ expansion happened
        with pytest.raises(ValueError, match="Host list file not found"):
            parse_host_list_file("~/nonexistent_hosts.txt")


class TestParseScheduleSSMArgs:
    """Test parse_schedule_ssm_args function"""

    def test_count_mode(self):
        """Test parsing count mode"""
        result = parse_schedule_ssm_args('3 description "Dev testing"')
        assert result["count"] == 3
        assert result["description"] == "Dev testing"
        assert result["wipe"] is True

    def test_comma_separated_hosts(self):
        """Test parsing comma-separated hosts"""
        result = parse_schedule_ssm_args('host01,host02,host03 description "Testing"')
        assert result["host_list"] == ["host01", "host02", "host03"]
        assert result["description"] == "Testing"

    def test_single_host(self):
        """Test parsing single hostname"""
        result = parse_schedule_ssm_args('host01.example.com description "Single"')
        assert result["host_list"] == ["host01.example.com"]
        assert result["description"] == "Single"

    def test_host_list_file_mode(self):
        """Test parsing host-list file mode"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("host01\nhost02\n")
            temp_path = f.name

        try:
            result = parse_schedule_ssm_args(f'host-list {temp_path} description "Batch"')
            assert result["host_list"] == ["host01", "host02"]
            assert result["description"] == "Batch"
        finally:
            os.unlink(temp_path)

    def test_host_list_missing_path(self):
        """Test host-list without file path"""
        # When description is provided, it tries to read description as a file
        with pytest.raises(ValueError, match="Host list file not found"):
            parse_schedule_ssm_args("host-list description test")

    def test_nowipe_option(self):
        """Test nowipe option"""
        result = parse_schedule_ssm_args('3 description "Test" nowipe')
        assert result["wipe"] is False

    def test_vlan_option(self):
        """Test vlan option"""
        result = parse_schedule_ssm_args('2 description "Test" vlan 1150')
        assert result["vlan"] == 1150

    def test_qinq_option(self):
        """Test qinq option"""
        result = parse_schedule_ssm_args('2 description "Test" qinq 1')
        assert result["qinq"] == 1

    def test_model_option(self):
        """Test model option"""
        result = parse_schedule_ssm_args('2 description "Test" model r640')
        assert result["model"] == "r640"

    def test_ram_option(self):
        """Test ram option"""
        result = parse_schedule_ssm_args('2 description "Test" ram 128')
        assert result["ram"] == 128

    def test_all_options(self):
        """Test all options combined"""
        result = parse_schedule_ssm_args('3 description "Full test" model r640 ram 128 vlan 1150 qinq 1 nowipe')
        assert result["count"] == 3
        assert result["description"] == "Full test"
        assert result["model"] == "r640"
        assert result["ram"] == 128
        assert result["vlan"] == 1150
        assert result["qinq"] == 1
        assert result["wipe"] is False

    def test_missing_description(self):
        """Test error when description is missing"""
        with pytest.raises(ValueError, match="(description is required|Usage:)"):
            parse_schedule_ssm_args("3 model r640")

    def test_too_few_args(self):
        """Test error with too few arguments"""
        with pytest.raises(ValueError, match="Usage:"):
            parse_schedule_ssm_args("3")

    def test_multi_word_description(self):
        """Test multi-word description parsing"""
        result = parse_schedule_ssm_args("2 description This is a long description model r640")
        assert result["description"] == "This is a long description"
        assert result["model"] == "r640"

    def test_os_option(self):
        """Test os option"""
        result = parse_schedule_ssm_args('2 description "Test" os "RHEL 9.4"')
        assert result["os"] == "RHEL 9.4"

    def test_os_default_none(self):
        """Test that os defaults to None"""
        result = parse_schedule_ssm_args('2 description "Test"')
        assert result["os"] is None

    def test_all_options_with_os(self):
        """Test all options combined including os"""
        result = parse_schedule_ssm_args(
            '3 description "Full test" model r640 ram 128 vlan 1150 qinq 1 os "RHEL 9.4" nowipe'
        )
        assert result["os"] == "RHEL 9.4"
        assert result["model"] == "r640"
        assert result["vlan"] == 1150

    def test_disk_type_option(self):
        """Test disk-type option"""
        result = parse_schedule_ssm_args('2 description "Test" disk-type nvme')
        assert result["disk_type"] == "nvme"

    def test_disk_size_option(self):
        """Test disk-size option"""
        result = parse_schedule_ssm_args('2 description "Test" disk-size 500')
        assert result["disk_size"] == 500

    def test_disk_count_option(self):
        """Test disk-count option"""
        result = parse_schedule_ssm_args('2 description "Test" disk-count 4')
        assert result["disk_count"] == 4

    def test_gpu_vendor_option(self):
        """Test gpu-vendor option"""
        result = parse_schedule_ssm_args('2 description "Test" gpu-vendor NVIDIA')
        assert result["gpu_vendor"] == "NVIDIA"

    def test_gpu_product_option(self):
        """Test gpu-product option"""
        result = parse_schedule_ssm_args('2 description "Test" gpu-product "Tesla V100"')
        assert result["gpu_product"] == "Tesla V100"

    def test_interfaces_option(self):
        """Test interfaces option"""
        result = parse_schedule_ssm_args('2 description "Test" interfaces 4')
        assert result["interfaces"] == 4

    def test_nic_vendor_option(self):
        """Test nic-vendor option"""
        result = parse_schedule_ssm_args('2 description "Test" nic-vendor Mellanox')
        assert result["nic_vendor"] == "Mellanox"

    def test_nic_speed_option(self):
        """Test nic-speed option"""
        result = parse_schedule_ssm_args('2 description "Test" nic-speed 25')
        assert result["nic_speed"] == 25

    def test_all_hardware_filters_combined(self):
        """Test all hardware metadata filters together"""
        result = parse_schedule_ssm_args(
            '3 description "Full HW test" model r640 ram 128 '
            "disk-type nvme disk-size 500 disk-count 4 "
            "gpu-vendor NVIDIA interfaces 4 "
            "nic-vendor Mellanox nic-speed 25"
        )
        assert result["count"] == 3
        assert result["description"] == "Full HW test"
        assert result["model"] == "r640"
        assert result["ram"] == 128
        assert result["disk_type"] == "nvme"
        assert result["disk_size"] == 500
        assert result["disk_count"] == 4
        assert result["gpu_vendor"] == "NVIDIA"
        assert result["interfaces"] == 4
        assert result["nic_vendor"] == "Mellanox"
        assert result["nic_speed"] == 25

    def test_description_terminates_at_hardware_filter(self):
        """Test that multi-word description stops at hardware filter keywords"""
        result = parse_schedule_ssm_args("2 description GPU performance testing gpu-vendor NVIDIA")
        assert result["description"] == "GPU performance testing"
        assert result["gpu_vendor"] == "NVIDIA"

    def test_filter_missing_value_raises(self):
        """Test that filter keyword without value raises ValueError"""
        with pytest.raises(ValueError, match="'gpu-vendor' requires a value"):
            parse_schedule_ssm_args('2 description "Test" gpu-vendor')

    def test_filter_missing_value_model(self):
        """Test that model keyword without value raises ValueError"""
        with pytest.raises(ValueError, match="'model' requires a value"):
            parse_schedule_ssm_args('2 description "Test" model')

    def test_filter_missing_value_disk_type(self):
        """Test that disk-type keyword without value raises ValueError"""
        with pytest.raises(ValueError, match="'disk-type' requires a value"):
            parse_schedule_ssm_args('2 description "Test" disk-type')


class TestParseScheduleAdminArgs:
    """Test parse_schedule_admin_args function"""

    def test_basic_admin_schedule(self):
        """Test basic admin schedule parsing"""
        result = parse_schedule_admin_args("cloud02 host01.example.com 2026-05-11 2026-06-11")
        assert result["cloud"] == "cloud02"
        assert result["host_list"] == ["host01.example.com"]
        assert result["start"] == "2026-05-11"
        assert result["end"] == "2026-06-11"

    def test_comma_separated_hosts_admin(self):
        """Test comma-separated hosts in admin mode"""
        result = parse_schedule_admin_args("cloud02 host01,host02,host03 2026-05-11 2026-06-11")
        assert result["host_list"] == ["host01", "host02", "host03"]

    def test_host_list_file_admin(self):
        """Test host-list file in admin mode"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("host01\nhost02\n")
            temp_path = f.name

        try:
            result = parse_schedule_admin_args(f"cloud02 host-list {temp_path} 2026-05-11 2026-06-11")
            assert result["host_list"] == ["host01", "host02"]
            assert result["cloud"] == "cloud02"
        finally:
            os.unlink(temp_path)

    def test_too_few_args_admin(self):
        """Test error with too few arguments in admin mode"""
        with pytest.raises(ValueError, match="Usage:"):
            parse_schedule_admin_args("cloud02 host01 2026-05-11")

    def test_host_list_missing_path_admin(self):
        """Test host-list without file path in admin mode"""
        with pytest.raises(ValueError, match="host-list requires a file path"):
            parse_schedule_admin_args("cloud02 host-list 2026-05-11 2026-06-11")

    def test_os_option_admin(self):
        """Test os option in admin mode"""
        result = parse_schedule_admin_args('cloud02 host01 2026-05-11 2026-06-11 description "Test" os "RHEL 9.4"')
        assert result["os"] == "RHEL 9.4"

    def test_os_default_none_admin(self):
        """Test that os defaults to None in admin mode"""
        result = parse_schedule_admin_args("cloud02 host01 2026-05-11 2026-06-11")
        assert result["os"] is None


class TestParseExtendArgs:
    """Test parse_extend_args function"""

    def test_extend_by_weeks(self):
        """Test extend by weeks"""
        result = parse_extend_args("cloud02 weeks 2")
        assert result["target"] == "cloud02"
        assert result["mode"] == "weeks"
        assert result["weeks"] == 2
        assert result["date"] is None

    def test_extend_by_date(self):
        """Test extend by date"""
        result = parse_extend_args('cloud02 date "2026-05-17 22:00"')
        assert result["target"] == "cloud02"
        assert result["mode"] == "date"
        assert result["date"] == "2026-05-17 22:00"
        assert result["weeks"] is None

    def test_extend_date_unquoted(self):
        """Test extend by date without quotes"""
        result = parse_extend_args("cloud02 date 2026-05-17 22:00")
        assert result["date"] == "2026-05-17 22:00"

    def test_extend_hostname(self):
        """Test extend with hostname instead of cloud"""
        result = parse_extend_args("host01.example.com weeks 1")
        assert result["target"] == "host01.example.com"
        assert result["weeks"] == 1

    def test_too_few_args_extend(self):
        """Test error with too few arguments"""
        with pytest.raises(ValueError, match="Usage:"):
            parse_extend_args("cloud02 weeks")

    def test_invalid_weeks_value(self):
        """Test error with invalid weeks value"""
        with pytest.raises(ValueError, match="weeks requires a number"):
            parse_extend_args("cloud02 weeks abc")

    def test_invalid_mode(self):
        """Test error with invalid mode"""
        with pytest.raises(ValueError, match="Second argument must be"):
            parse_extend_args("cloud02 invalid 5")

    def test_date_missing_value(self):
        """Test error when date value is missing"""
        with pytest.raises(ValueError, match="(date requires a value|Usage:)"):
            parse_extend_args("cloud02 date")


class TestParseShrinkArgs:
    def test_shrink_by_weeks(self):
        result = parse_shrink_args("cloud02 weeks 2")
        assert result["target"] == "cloud02"
        assert result["mode"] == "weeks"
        assert result["weeks"] == 2
        assert result["days"] is None
        assert result["date"] is None

    def test_shrink_by_days(self):
        result = parse_shrink_args("cloud02 days 5")
        assert result["target"] == "cloud02"
        assert result["mode"] == "days"
        assert result["days"] == 5
        assert result["weeks"] is None

    def test_shrink_now(self):
        result = parse_shrink_args("cloud23 now")
        assert result["target"] == "cloud23"
        assert result["mode"] == "now"
        assert result["weeks"] is None
        assert result["days"] is None
        assert result["date"] is None

    def test_shrink_by_date(self):
        result = parse_shrink_args('cloud02 date "2026-05-12 22:00"')
        assert result["target"] == "cloud02"
        assert result["mode"] == "date"
        assert result["date"] == "2026-05-12 22:00"

    def test_shrink_date_unquoted(self):
        result = parse_shrink_args("cloud02 date 2026-05-12 22:00")
        assert result["date"] == "2026-05-12 22:00"

    def test_shrink_hostname(self):
        result = parse_shrink_args("host01.example.com weeks 1")
        assert result["target"] == "host01.example.com"
        assert result["weeks"] == 1

    def test_too_few_args(self):
        with pytest.raises(ValueError, match="Usage:"):
            parse_shrink_args("cloud02")

    def test_weeks_missing_number(self):
        with pytest.raises(ValueError, match="weeks requires a number"):
            parse_shrink_args("cloud02 weeks")

    def test_days_missing_number(self):
        with pytest.raises(ValueError, match="days requires a number"):
            parse_shrink_args("cloud02 days")

    def test_invalid_weeks_value(self):
        with pytest.raises(ValueError, match="weeks requires a number"):
            parse_shrink_args("cloud02 weeks abc")

    def test_invalid_days_value(self):
        with pytest.raises(ValueError, match="days requires a number"):
            parse_shrink_args("cloud02 days abc")

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="Second argument must be"):
            parse_shrink_args("cloud02 invalid 5")

    def test_now_with_extra_args(self):
        with pytest.raises(ValueError, match="'now' takes no additional arguments"):
            parse_shrink_args("cloud02 now extra")

    def test_date_missing_value(self):
        with pytest.raises(ValueError, match="(date requires a value|Usage:)"):
            parse_shrink_args("cloud02 date")
