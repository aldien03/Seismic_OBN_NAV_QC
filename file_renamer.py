"""
File Renamer Module

This module provides file renaming functionality based on regex patterns configured
in config.ini. It handles both RAW and Processed seismic data file renaming.

Classes:
- FileRenamer: Main class for handling file renaming operations

Author: aldien03@gmail.com
Date: 2025-09-30
"""

import os
import re
import logging
from typing import Dict, List, Tuple, Set
from configparser import ConfigParser


class FileRenamer:
    """
    Class for handling file renaming based on regex patterns from configuration.

    Supports:
    - RAW file renaming (.p190, .p294, .S00, .p211, .mfa, .pdf, .sbs, .sts)
    - Processed file renaming (.csv, .pdf, .S01, .P111, .P190)
    - Pattern validation and error handling
    - Compliant file detection (already properly named)
    - Missing file type detection
    """

    def __init__(self, config: ConfigParser):
        """
        Initialize FileRenamer with configuration.

        Args:
            config: ConfigParser instance containing rename patterns
        """
        self.config = config
        self.rename_patterns: Dict[str, Dict[str, Tuple[str, str]]] = {}
        self.already_compliant_patterns: Dict[str, str] = {}
        self.expected_extensions: Dict[str, List[str]] = {}
        self.expected_file_numbers: Dict[str, int] = {}
        self.processed_files: Dict[str, List] = {
            'renamed': [],
            'compliant': [],
            'missing': [],
            'errors': [],
            'missing_extensions': set()
        }

    def _load_rename_patterns(self, config_section: str) -> bool:
        """
        Load rename patterns from configuration section.

        Args:
            config_section: Section name in config.ini (e.g., 'Rename_Raw_Files')

        Returns:
            bool: True if patterns loaded successfully, False otherwise
        """
        if not self.config.has_section(config_section):
            logging.error(f"Config section {config_section} not found")
            return False

        try:
            # Determine extension and file number keys based on section type
            if config_section == "Rename_Raw_Files":
                extensions_key = "raw_expected_extensions"
                file_number_key = "raw_expected_file_number"
            else:
                extensions_key = "processed_expected_extensions"
                file_number_key = "processed_expected_file_number"

            logging.debug(f"Loading config for section {config_section}")
            logging.debug(f"Using extensions key: {extensions_key}")
            logging.debug(f"Using file number key: {file_number_key}")

            # Load expected extensions
            extensions_str = self.config.get(config_section, extensions_key, fallback="")
            self.expected_extensions[config_section] = [ext.strip() for ext in extensions_str.split(",") if ext.strip()]
            logging.debug(f"Loaded extensions: {self.expected_extensions[config_section]}")

            # Load expected file number
            self.expected_file_numbers[config_section] = self.config.getint(config_section, file_number_key, fallback=0)
            logging.debug(f"Loaded expected file number: {self.expected_file_numbers[config_section]}")

            # Load already compliant pattern if it exists
            already_compliant_pattern = self.config.get(config_section, "already_compliant_pattern", fallback="")
            if already_compliant_pattern:
                try:
                    re.compile(already_compliant_pattern)
                    self.already_compliant_patterns[config_section] = already_compliant_pattern
                    logging.debug(f"Loaded already compliant pattern: {already_compliant_pattern}")
                except re.error as e:
                    logging.error(f"Invalid already_compliant_pattern regex: {e}")
                    return False

            # Load rename patterns
            self.rename_patterns[config_section] = {}
            pattern_count = 0
            for key, value in self.config.items(config_section):
                if key.endswith("_pattern") and key != "already_compliant_pattern":
                    try:
                        if "->" not in value:
                            logging.warning(f"Skipping {key} as it doesn't contain '->' separator")
                            continue

                        pattern, replacement = value.split("->")
                        pattern = pattern.strip()
                        replacement = replacement.strip()
                        re.compile(pattern)  # Validate pattern
                        self.rename_patterns[config_section][key] = (pattern, replacement)
                        pattern_count += 1
                    except (ValueError, re.error) as e:
                        logging.error(f"Invalid regex pattern in {key}: {e}")
                        return False

            logging.debug(f"Loaded {pattern_count} rename patterns")

            if not self.rename_patterns[config_section]:
                logging.error(f"No valid rename patterns found in {config_section}")
                return False

            return True

        except Exception as e:
            logging.error(f"Error loading rename patterns: {e}")
            return False

    def rename_files_in_directory(self, directory: str, config_section: str) -> Tuple[int, int, List[str], List[str]]:
        """
        Rename files in directory according to patterns in config section.

        Args:
            directory: Path to directory containing files to rename
            config_section: Config section name ('Rename_Raw_Files' or 'Rename_Processed_Files')

        Returns:
            Tuple of (renamed_count, already_compliant, missing_files, error_files)
        """
        # Reset processed files for new operation
        self.processed_files = {
            'renamed': [],
            'compliant': [],
            'missing': [],
            'errors': [],
            'missing_extensions': set()
        }

        if not os.path.exists(directory):
            error_msg = f"Directory not found: {directory}"
            logging.error(error_msg)
            self.processed_files['errors'].append(error_msg)
            return 0, 0, [], [error_msg]

        # Load patterns
        if not self._load_rename_patterns(config_section):
            error_msg = f"Failed to load patterns from {config_section}"
            logging.error(error_msg)
            self.processed_files['errors'].append(error_msg)
            return 0, 0, [], [error_msg]

        # Log expected file numbers for debugging
        logging.debug(f"Config section: {config_section}")
        logging.debug(f"Expected file numbers: {self.expected_file_numbers}")
        logging.debug(f"Expected extensions: {self.expected_extensions}")

        renamed_count = 0
        already_compliant = 0
        missing_files = []
        error_files = []

        try:
            files = os.listdir(directory)
            logging.debug(f"Found {len(files)} files in directory {directory}")

            # Check for missing file types based on extensions
            found_extensions = {os.path.splitext(f)[1].lower() for f in files}
            expected_extensions = {ext.lower() for ext in self.expected_extensions[config_section]}
            self.processed_files['missing_extensions'] = expected_extensions - found_extensions

            if self.processed_files['missing_extensions']:
                logging.warning(f"Missing file types: {', '.join(self.processed_files['missing_extensions'])}")

            # Process existing files
            for filename in files:
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in expected_extensions:
                    continue

                filepath = os.path.join(directory, filename)
                if not os.path.isfile(filepath):
                    continue

                # Check if file is already compliant
                if config_section in self.already_compliant_patterns:
                    if re.match(self.already_compliant_patterns[config_section], filename):
                        already_compliant += 1
                        self.processed_files['compliant'].append(filename)
                        continue

                # Try to match and rename file
                matched = False
                for pattern_name, (pattern, replacement) in self.rename_patterns[config_section].items():
                    try:
                        match = re.match(pattern, filename)
                        if match:
                            new_name = match.expand(replacement)
                            new_path = os.path.join(directory, new_name)

                            if os.path.exists(new_path) and new_path != filepath:
                                error_msg = f"Cannot rename {filename} to {new_name} - target file already exists"
                                logging.error(error_msg)
                                error_files.append(error_msg)
                                self.processed_files['errors'].append(error_msg)
                                break

                            try:
                                logging.debug(f"Renaming {filename} to {new_name} using pattern {pattern_name}")
                                os.rename(filepath, new_path)
                                renamed_count += 1
                                self.processed_files['renamed'].append((filename, new_name))
                                matched = True
                                break
                            except PermissionError as e:
                                error_msg = f"Permission denied renaming {filename}: {e}"
                                logging.error(error_msg)
                                error_files.append(error_msg)
                                self.processed_files['errors'].append(error_msg)
                                break
                            except Exception as e:
                                error_msg = f"Error renaming {filename}: {e}"
                                logging.error(error_msg)
                                error_files.append(error_msg)
                                self.processed_files['errors'].append(error_msg)
                                break
                    except re.error as e:
                        error_msg = f"Invalid regex pattern for {filename}: {e}"
                        logging.error(error_msg)
                        error_files.append(error_msg)
                        self.processed_files['errors'].append(error_msg)
                        break

                if not matched and filename not in error_files:
                    # Treat unmatched files as already compliant
                    already_compliant += 1
                    self.processed_files['compliant'].append(filename)

            return renamed_count, already_compliant, missing_files, error_files

        except Exception as e:
            error_msg = f"Error processing directory: {e}"
            logging.error(error_msg)
            self.processed_files['errors'].append(error_msg)
            return 0, 0, [], [error_msg]
