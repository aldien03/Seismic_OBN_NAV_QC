"""
Unit tests for ConfigManager module

Tests configuration loading, validation, and accessor methods.
"""

import pytest
import os
import tempfile
import configparser
from config_manager import ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager class"""

    def test_init_default_path(self):
        """Test ConfigManager initialization with default path"""
        manager = ConfigManager()
        assert manager.config_path == "config.ini"
        assert isinstance(manager.config, configparser.ConfigParser)

    def test_init_custom_path(self):
        """Test ConfigManager initialization with custom path"""
        custom_path = "/path/to/custom/config.ini"
        manager = ConfigManager(custom_path)
        assert manager.config_path == custom_path

    def test_load_config_success(self, config_file):
        """Test successful config loading"""
        manager = ConfigManager(config_file)
        manager.load_config()
        assert manager.config.has_section("General")

    def test_load_config_file_not_found(self, qapp):
        """Test error handling when config file doesn't exist"""
        manager = ConfigManager("nonexistent.ini")
        with pytest.raises(SystemExit):
            manager.load_config()

    def test_load_config_invalid_format(self, qapp):
        """Test error handling with invalid config format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("Invalid config without section headers\n")
            f.write("key = value\n")
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            with pytest.raises(SystemExit):
                manager.load_config()
        finally:
            os.unlink(temp_path)

    def test_has_section(self, config_file):
        """Test has_section method"""
        manager = ConfigManager(config_file)
        manager.load_config()
        assert manager.has_section("General") is True
        assert manager.has_section("NonExistentSection") is False

    def test_get_value(self, config_file):
        """Test get method for retrieving config values"""
        manager = ConfigManager(config_file)
        manager.load_config()
        # Assuming config has [General] section with source_option
        value = manager.get("General", "source_option", fallback="Dual")
        assert value in ["Dual", "Triple"]

    def test_get_with_fallback(self, config_file):
        """Test get method with fallback value"""
        manager = ConfigManager(config_file)
        manager.load_config()
        value = manager.get("General", "nonexistent_key", fallback="default")
        assert value == "default"

    def test_getfloat(self, config_file):
        """Test getfloat method"""
        manager = ConfigManager(config_file)
        manager.load_config()
        # Test with a known float value from config
        if manager.has_section("QC_Thresholds"):
            sti_threshold = manager.getfloat("QC_Thresholds", "sti_error_threshold", fallback=6.0)
            assert isinstance(sti_threshold, float)
            assert sti_threshold > 0

    def test_getint(self, config_file):
        """Test getint method"""
        manager = ConfigManager(config_file)
        manager.load_config()
        # Test with fallback
        int_value = manager.getint("General", "some_int_key", fallback=100)
        assert isinstance(int_value, int)

    def test_getboolean(self, config_file):
        """Test getboolean method"""
        manager = ConfigManager(config_file)
        manager.load_config()
        # Test with fallback
        bool_value = manager.getboolean("General", "some_bool_key", fallback=True)
        assert isinstance(bool_value, bool)

    def test_items(self, config_file):
        """Test items method to get all section items"""
        manager = ConfigManager(config_file)
        manager.load_config()
        items = manager.items("General")
        assert isinstance(items, list)
        assert len(items) > 0
        # Each item should be a tuple (key, value)
        for item in items:
            assert isinstance(item, tuple)
            assert len(item) == 2


@pytest.fixture
def config_file(project_root):
    """Fixture providing path to actual config.ini file"""
    config_path = os.path.join(project_root, "config.ini")
    if not os.path.exists(config_path):
        pytest.skip("config.ini not found")
    return config_path