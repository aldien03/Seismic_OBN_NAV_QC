"""
Database Operations Module

This module provides database output functionality for QC results.
It handles path resolution, CSV generation, and fallback mechanisms.

Classes:
- DatabaseManager: Main class for handling database operations

Author: aldien03@gmail.com
Date: 2025-09-30
"""

import os
import logging
import pandas as pd
from typing import Optional, Dict
from configparser import ConfigParser


class DatabaseManager:
    """
    Class for managing database output operations.

    Supports:
    - Primary and fallback database path resolution
    - CSV output generation with validation
    - Sequence and line name extraction
    - File existence and size verification
    - Comprehensive error handling
    """

    def __init__(self, config: ConfigParser):
        """
        Initialize DatabaseManager with configuration.

        Args:
            config: ConfigParser instance containing database paths
        """
        self.config = config

    def save_to_database(self, results: Dict, sps_file: str) -> Optional[str]:
        """
        Save QC results to database in CSV format.

        Args:
            results: Dictionary containing QC results with 'merged_df' key
            sps_file: Path to SPS file (for reference/logging)

        Returns:
            Path to saved file if successful, None otherwise

        Edge cases handled:
        - Invalid or missing DataFrame
        - Invalid sequence or line_name values
        - Missing or invalid output directory in config
        - Insufficient permissions
        - File already exists (overwrites)
        - Network path unavailable (uses fallback)
        """
        try:
            # Validate input
            if not isinstance(results, dict):
                logging.error("Invalid results: expected dict, got %s", type(results))
                return None

            merged_df = results.get('merged_df')
            if merged_df is None or not isinstance(merged_df, pd.DataFrame):
                logging.error("Invalid or missing DataFrame in results")
                return None

            if merged_df.empty:
                logging.error("DataFrame is empty")
                return None

            required_columns = ['sequence', 'line_name']
            missing_columns = [col for col in required_columns if col not in merged_df.columns]
            if missing_columns:
                logging.error("Missing required columns: %s", missing_columns)
                return None

            # Extract and validate sequence
            try:
                sequence = str(int(merged_df['sequence'].iloc[0])).zfill(4)
                logging.debug("Extracted sequence: %s", sequence)
            except (ValueError, IndexError, TypeError) as e:
                logging.error("Failed to extract sequence: %s", str(e))
                return None

            # Extract and validate line name
            try:
                line_name = merged_df['line_name'].iloc[0]
                if pd.isna(line_name):
                    logging.error("Line name is NA/null")
                    return None

                if isinstance(line_name, (int, float)):
                    llll = str(int(line_name)).zfill(4)
                else:
                    llll = ''.join(filter(str.isdigit, str(line_name)))[:4]
                    if not llll:
                        logging.error("Could not extract digits from line name: %s", line_name)
                        return None
                logging.debug("Extracted line name: %s -> %s", line_name, llll)
            except (ValueError, IndexError, TypeError) as e:
                logging.error("Failed to extract line name: %s", str(e))
                return None

            # Generate output filename
            output_filename = f"{sequence}_{llll}_DB.csv"
            logging.debug("Generated filename: %s", output_filename)

            # Try primary location
            primary_path = self._try_save_primary(merged_df, output_filename)
            if primary_path:
                return primary_path

            # Try fallback location
            fallback_path = self._try_save_fallback(merged_df, output_filename)
            if fallback_path:
                return fallback_path

            logging.error("Failed to save to both primary and fallback locations")
            return None

        except Exception as e:
            logging.error("Error saving results to database: %s", str(e))
            return None

    def _try_save_primary(self, df: pd.DataFrame, filename: str) -> Optional[str]:
        """
        Attempt to save to primary database location.

        Args:
            df: DataFrame to save
            filename: Output filename

        Returns:
            Path to saved file if successful, None otherwise
        """
        try:
            # Try new [Database] section first, then fall back to legacy [Paths] section
            output_dir = None

            # Try [Database] section (preferred)
            if self.config.has_section('Database'):
                output_dir = self.config.get('Database', 'primary_db_path', fallback=None)
                if output_dir:
                    logging.debug("Using primary_db_path from [Database] section: %s", output_dir)

            # Fall back to legacy [Paths] section
            if not output_dir and self.config.has_section('Paths'):
                output_dir = self.config.get('Paths', 'db_output_path', fallback=None)
                if output_dir:
                    logging.debug("Using db_output_path from [Paths] section (legacy): %s", output_dir)

            # Final fallback to default
            if not output_dir:
                output_dir = r'C:\SWAT_DB_Default'
                logging.warning("No database path configured, using default: %s", output_dir)

            logging.info("Using output directory: %s", output_dir)

            # Create directory if it doesn't exist
            try:
                os.makedirs(output_dir, exist_ok=True)
                logging.debug("Ensured directory exists: %s", output_dir)
            except Exception as e:
                logging.warning("Failed to create directory %s: %s", output_dir, str(e))
                return None

            # Construct full file path
            output_path = os.path.join(output_dir, filename)
            logging.info("Attempting to save to: %s", output_path)

            # Check if file exists
            if os.path.exists(output_path):
                logging.warning("File already exists, will overwrite: %s", output_path)

            # Save the file
            df.to_csv(output_path, index=False)
            logging.info("Results saved to: %s", output_path)

            # Verify file was created
            if not os.path.exists(output_path):
                logging.error("File was not created: %s", output_path)
                return None

            # Verify file size
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                logging.error("Created file is empty: %s", output_path)
                return None
            logging.debug("File size: %d bytes", file_size)

            return output_path

        except Exception as e:
            logging.warning("Failed to save to primary location: %s", str(e))
            return None

    def _try_save_fallback(self, df: pd.DataFrame, filename: str) -> Optional[str]:
        """
        Attempt to save to fallback location (current working directory).

        Args:
            df: DataFrame to save
            filename: Output filename

        Returns:
            Path to saved file if successful, None otherwise
        """
        try:
            fallback_path = os.path.join(os.getcwd(), filename)
            logging.info("Attempting fallback save to: %s", fallback_path)

            df.to_csv(fallback_path, index=False)

            # Verify fallback file
            if not os.path.exists(fallback_path) or os.path.getsize(fallback_path) == 0:
                logging.error("Fallback file verification failed")
                return None

            logging.info("Successfully saved to fallback location: %s", fallback_path)
            return fallback_path

        except Exception as e:
            logging.error("Error saving to fallback location: %s", str(e))
            return None
