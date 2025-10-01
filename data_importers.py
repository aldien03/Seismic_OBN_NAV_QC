"""
Data Importers Module

This module provides data import functionality for various file formats used in
seismic NAV QC operations.

Importers:
- SPSImporter: Import SPS (.S01) files
- SPSCompImporter: Import SPS comparison CSV files
- EOLImporter: Import EOL report CSV files
- ASCImporter: Import ASC gun data files
- SBSImporter: Import SBS source data files

Author: aldien03@gmail.com
Date: 2025-09-30
"""

import os
import re
import logging
import pandas as pd
from typing import Optional
from abc import ABC, abstractmethod
from config_manager import ConfigManager


class DataImporter(ABC):
    """Base class for all data importers"""

    def __init__(self, config: ConfigManager):
        """
        Initialize importer with configuration.

        Args:
            config: ConfigManager instance
        """
        self.config = config

    @abstractmethod
    def import_file(self, path: str) -> pd.DataFrame:
        """
        Import data from file.

        Args:
            path: File or folder path

        Returns:
            DataFrame with imported data, or empty DataFrame on error
        """
        pass


class SPSImporter(DataImporter):
    """Import SPS (.S01) files with fixed-width format"""

    def import_file(self, file_path: str) -> pd.DataFrame:
        """
        Import SPS data from a .S01 file with known formatting.

        Args:
            file_path: Path to the SPS file

        Returns:
            DataFrame with parsed SPS data
        """
        logging.info(f"Importing SPS data from {file_path}")

        try:
            if not os.path.exists(file_path):
                logging.error(f"SPS file not found: {file_path}")
                return pd.DataFrame()

            # Count header rows
            header_rows = 0
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith('H'):
                        header_rows += 1
                    else:
                        break

            logging.info(f"Detected {header_rows} header rows")

            # Read the data with fixed width format based on SPS specification
            df = pd.read_fwf(
                file_path,
                skiprows=header_rows,
                colspecs=[
                    (0, 1), (1, 11), (11, 21), (23, 24), (24, 26),
                    (26, 30), (30, 34), (34, 38), (38, 40), (40, 46),
                    (46, 55), (55, 65), (65, 71), (71, 74), (74, 80),
                    (87, 92), (92, 95), (95, 97), (97, 98), (98, 99),
                    (99, 100), (100, 101), (101, 102), (102, 107)
                ],
                names=[
                    'record_id', 'line_name', 'point_no', 'point_index',
                    'point_code', 'static_cor', 'point_depth', 'seismic_datum',
                    'uphole_time', 'water_depth', 'easting_m', 'northing_m',
                    'surface_elev', 'day_of_year', 'time_UTC', 'sequence',
                    'direction', 'year', 'gun_depth_flag', 'gun_timing_flag',
                    'gun_pressure_flag', 'repeatability_flag', 'sma_flag',
                    'shot_dither'
                ]
            )

            # Filter only shot records
            df = df[df['record_id'] == 'S'].copy()

            # Clean and convert numeric columns
            numeric_cols = [
                'line_name', 'point_no', 'point_depth', 'water_depth',
                'easting_m', 'northing_m', 'surface_elev', 'day_of_year',
                'sequence', 'year', 'gun_depth_flag', 'shot_dither'
            ]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Clean point_code
            df['point_code'] = df['point_code'].astype(str).str.strip()

            # Convert time to datetime
            df['datetime_UTC'] = pd.to_datetime(
                (df['year'] + 2000).astype(str) +
                df['day_of_year'].astype(str).str.zfill(3) +
                df['time_UTC'].astype(str).str.zfill(6),
                format='%Y%j%H%M%S',
                errors='coerce'
            )

            # Convert flag columns to nullable Int64 (supports NaN for missing flag detection)
            # DO NOT fillna here - we need to preserve NaN to detect missing Seispos flags
            flag_columns = [
                'gun_depth_flag', 'gun_timing_flag', 'gun_pressure_flag',
                'repeatability_flag', 'sma_flag'
            ]
            df[flag_columns] = df[flag_columns].astype('Int64')  # Int64 supports pd.NA

            # Rename columns
            df = df.rename(columns={
                'point_no': 'shot_point',
                'point_depth': 'average_gun_depth'
            })

            # Drop unnecessary columns
            columns_to_drop = [
                'record_id', 'static_cor', 'seismic_datum', 'uphole_time',
                'point_index', 'surface_elev'
            ]
            df = df.drop(columns=columns_to_drop)

            # Ensure shot_point is Int64
            df['shot_point'] = pd.to_numeric(df['shot_point'], errors='coerce').astype('Int64')

            logging.info(f"Successfully imported {len(df)} SPS records")
            logging.debug(f"SPS DataFrame - Columns: {list(df.columns)}, Shape: {df.shape}")

            return df

        except Exception as e:
            logging.error(f"Error importing SPS data: {str(e)}")
            return pd.DataFrame()


class SPSCompImporter(DataImporter):
    """Import SPS comparison CSV files"""

    def import_file(self, folder_path: str) -> pd.DataFrame:
        """
        Import SPS_Comp CSV from the 'Processed' folder.

        Args:
            folder_path: Path to folder containing SPS_Comp file

        Returns:
            DataFrame with SPS comparison data
        """
        try:
            # Ensure we're looking in Processed folder
            if not folder_path.endswith('Processed'):
                processed_folder = os.path.join(folder_path, "Processed")
            else:
                processed_folder = folder_path

            if not os.path.exists(processed_folder):
                logging.error(f"Processed folder not found: {processed_folder}")
                return pd.DataFrame()

            sps_comp_pattern = self.config.get(
                "Regex_Filenames", "sps_comp_file_pattern",
                fallback=r'^0256-\d{4}[A-Z]\d\d{4}_SPS_Comp\.csv$'
            )

            for filename in os.listdir(processed_folder):
                if re.match(sps_comp_pattern, filename):
                    file_path = os.path.join(processed_folder, filename)

                    # Find header row
                    header_row = 0
                    with open(file_path, 'r') as f:
                        for i, line in enumerate(f):
                            if 'Code,Line,Shot' in line:
                                header_row = i
                                break

                    # Read CSV
                    df = pd.read_csv(
                        file_path,
                        skiprows=header_row,
                        na_values=['', 'NaN', 'nan'],
                        keep_default_na=True
                    )

                    # Rename and select columns
                    df = df.rename(columns={'Shot': 'shot_point'})
                    required_columns = ['shot_point', 'Radial (m)', 'Crossline (m)', 'Inline (m)']
                    df = df[required_columns]

                    # Convert numeric columns
                    for col in required_columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                    df['shot_point'] = pd.to_numeric(df['shot_point'], errors='coerce').astype('Int64')

                    logging.info(f"Successfully imported {len(df)} SPS_Comp records")
                    return df

            logging.warning("No matching SPS_Comp file found")
            return pd.DataFrame()

        except Exception as e:
            logging.error(f"Error importing SPS_Comp data: {str(e)}")
            return pd.DataFrame()


class EOLImporter(DataImporter):
    """Import EOL report CSV files"""

    def import_file(self, folder_path: str) -> pd.DataFrame:
        """
        Import EOL report CSV from the 'Processed' folder.

        Args:
            folder_path: Path to folder containing EOL file

        Returns:
            DataFrame with EOL data
        """
        try:
            # Ensure we're looking in Processed folder
            if not folder_path.endswith('Processed'):
                processed_folder = os.path.join(folder_path, "Processed")
            else:
                processed_folder = folder_path

            if not os.path.exists(processed_folder):
                logging.error(f"Processed folder not found: {processed_folder}")
                return pd.DataFrame()

            eol_pattern = self.config.get(
                "Regex_Filenames", "eol_file_pattern",
                fallback=r'^0256-\d{4}[A-Z]\d\d{4}_EOL_report\.csv$'
            )

            for filename in os.listdir(processed_folder):
                if re.match(eol_pattern, filename):
                    file_path = os.path.join(processed_folder, filename)

                    # Try UTF-8 first, fallback to ISO-8859-1
                    try:
                        df = pd.read_csv(file_path, encoding='utf-8')
                    except UnicodeDecodeError:
                        df = pd.read_csv(file_path, encoding='iso-8859-1')

                    df = df.rename(columns={'SP': 'shot_point'})

                    logging.info(f"Successfully imported {len(df)} EOL records")
                    return df

            logging.warning("No matching EOL report file found")
            return pd.DataFrame()

        except Exception as e:
            logging.error(f"Error importing EOL report: {str(e)}")
            return pd.DataFrame()


class ASCImporter(DataImporter):
    """Import ASC gun data files"""

    def import_file(self, folder_path: str) -> pd.DataFrame:
        """
        Import ASC file from GunData directory.

        Args:
            folder_path: Path to GunData folder

        Returns:
            DataFrame with gun data
        """
        try:
            if not os.path.exists(folder_path):
                logging.error(f"GunData folder not found: {folder_path}")
                return pd.DataFrame()

            for filename in os.listdir(folder_path):
                if filename.lower().endswith('.asc'):
                    file_path = os.path.join(folder_path, filename)

                    # Try UTF-8 first, fallback to ISO-8859-1
                    try:
                        df = pd.read_csv(file_path, skiprows=4, sep=r'\s+', encoding='utf-8')
                    except UnicodeDecodeError:
                        df = pd.read_csv(file_path, skiprows=4, sep=r'\s+', encoding='iso-8859-1')

                    if 'SHOTPOINT' in df.columns:
                        # Convert SHOTPOINT to numeric
                        if not pd.api.types.is_string_dtype(df['SHOTPOINT']):
                            df['SHOTPOINT'] = df['SHOTPOINT'].astype(str)
                        df['SHOTPOINT'] = pd.to_numeric(
                            df['SHOTPOINT'].str.lstrip('0'),
                            errors='coerce'
                        ).astype('Int64')
                        df = df.rename(columns={'SHOTPOINT': 'shot_point'})

                        # Drop unnecessary columns
                        if 'AIM_POINT_TIME' in df.columns:
                            df = df.drop(columns=['AIM_POINT_TIME'])

                        logging.info(f"Successfully imported {len(df)} ASC records")
                        return df

            logging.warning("No matching ASC file found")
            return pd.DataFrame()

        except Exception as e:
            logging.error(f"Error importing ASC file: {str(e)}")
            return pd.DataFrame()


class SBSImporter(DataImporter):
    """Import SBS source data files"""

    def import_file(self, folder_path: str) -> pd.DataFrame:
        """
        Import SBS data from the main directory.

        Args:
            folder_path: Path to folder containing SBS file

        Returns:
            DataFrame with SBS data
        """
        try:
            # If path ends with 'Processed', go up one level
            if folder_path.endswith('Processed'):
                folder_path = os.path.dirname(folder_path)

            if not os.path.exists(folder_path):
                logging.error(f"Directory not found: {folder_path}")
                return pd.DataFrame()

            sbs_pattern = self.config.get(
                "Regex_Filenames", "sbs_file_pattern",
                fallback=r'^0256-\d{4}[A-Z]\d\d{4}\.sbs$'
            )

            for filename in os.listdir(folder_path):
                if re.match(sbs_pattern, filename):
                    file_path = os.path.join(folder_path, filename)

                    # Read and process the file
                    header_groups = {}
                    current_header = None

                    with open(file_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("#") or line.startswith("Page") or line == "":
                                continue
                            elif line.startswith("Shot"):
                                current_header = line
                                header_groups[current_header] = []
                            else:
                                # Split by tab and clean values
                                values = [v.strip().replace('\x05', '') for v in line.split("\t")]
                                header_groups[current_header].append(values)

                    # Create DataFrames for each header group
                    df_list = []
                    for header, data in header_groups.items():
                        columns = [col.strip().replace('\x05', '') for col in header.split("\t")]
                        df_temp = pd.DataFrame(data, columns=columns)
                        df_list.append(df_temp)

                    df = pd.concat(df_list, axis=1)

                    # Remove duplicate columns
                    df = df.loc[:,~df.columns.duplicated()]

                    # Rename 'Shot' to 'shot_point'
                    df = df.rename(columns={'Shot': 'shot_point'})

                    # Convert numeric columns
                    for col in df.columns:
                        if col != 'shot_point':
                            df[col] = pd.to_numeric(df[col], errors='coerce')

                    df['shot_point'] = pd.to_numeric(df['shot_point'], errors='coerce').astype('Int64')

                    logging.info(f"Successfully imported {len(df)} SBS records")
                    return df

            logging.warning("No matching SBS file found")
            return pd.DataFrame()

        except Exception as e:
            logging.error(f"Error importing SBS data: {str(e)}")
            return pd.DataFrame()