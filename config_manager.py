"""
Configuration Manager Module

This module provides configuration management functionality for the PXGEONavQC application.
It handles loading and validating configuration from config.ini files.

Author: aldien03@gmail.com
Date: 2025-09-30
"""

import os
import sys
import configparser
import logging
from typing import Optional
from PyQt5.QtWidgets import QMessageBox


class ConfigManager:
    """
    Loads and manages configuration data from config.ini.

    This class provides centralized configuration management, handling:
    - Configuration file loading and validation
    - Error handling with user feedback
    - Access to configuration sections and values

    Attributes:
        config_path (str): Path to the configuration file
        config (configparser.ConfigParser): The loaded configuration object
    """

    def __init__(self, config_path: str = "config.ini"):
        """
        Initialize the ConfigManager with the given config file path.

        Args:
            config_path: Path to the configuration file (default: config.ini)
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        logging.debug(f"ConfigManager initialized with path: {config_path}")

    def load_config(self) -> None:
        """
        Load the configuration from the specified config.ini file.

        Validates that the config file exists and is properly formatted.
        Displays error dialogs and exits the program if validation fails.

        Raises:
            SystemExit: If config file is not found or is invalid
        """
        if not os.path.exists(self.config_path):
            logging.error(f"Config file not found: {self.config_path}")
            QMessageBox.critical(
                None,
                "Error",
                f"Config file not found: {self.config_path}"
            )
            sys.exit(1)

        try:
            self.config.read(self.config_path)
            logging.info(f"Configuration loaded successfully from {self.config_path}")
        except configparser.MissingSectionHeaderError:
            logging.error(f"Invalid config file format: Missing section headers")
            QMessageBox.critical(
                None,
                "Error",
                f"Invalid config file format: {self.config_path}\nMissing section headers"
            )
            sys.exit(1)
        except configparser.ParsingError as e:
            logging.error(f"Invalid config file format: {e}")
            QMessageBox.critical(
                None,
                "Error",
                f"Invalid config file format: {self.config_path}\n{str(e)}"
            )
            sys.exit(1)

    def has_section(self, section: str) -> bool:
        """
        Check if a configuration section exists.

        Args:
            section: Name of the configuration section

        Returns:
            True if section exists, False otherwise
        """
        return self.config.has_section(section)

    def get(self, section: str, option: str, fallback: Optional[str] = None) -> str:
        """
        Get a configuration value.

        Args:
            section: Name of the configuration section
            option: Name of the configuration option
            fallback: Default value if option doesn't exist

        Returns:
            Configuration value as string
        """
        return self.config.get(section, option, fallback=fallback)

    def getfloat(self, section: str, option: str, fallback: Optional[float] = None) -> float:
        """
        Get a configuration value as float.

        Args:
            section: Name of the configuration section
            option: Name of the configuration option
            fallback: Default value if option doesn't exist

        Returns:
            Configuration value as float
        """
        return self.config.getfloat(section, option, fallback=fallback)

    def getint(self, section: str, option: str, fallback: Optional[int] = None) -> int:
        """
        Get a configuration value as integer.

        Args:
            section: Name of the configuration section
            option: Name of the configuration option
            fallback: Default value if option doesn't exist

        Returns:
            Configuration value as integer
        """
        return self.config.getint(section, option, fallback=fallback)

    def getboolean(self, section: str, option: str, fallback: Optional[bool] = None) -> bool:
        """
        Get a configuration value as boolean.

        Args:
            section: Name of the configuration section
            option: Name of the configuration option
            fallback: Default value if option doesn't exist

        Returns:
            Configuration value as boolean
        """
        return self.config.getboolean(section, option, fallback=fallback)

    def items(self, section: str):
        """
        Get all items from a configuration section.

        Args:
            section: Name of the configuration section

        Returns:
            List of (name, value) tuples for the section
        """
        return self.config.items(section)