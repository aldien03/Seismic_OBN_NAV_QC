"""
QC Report Generator Module

This module provides QC report generation and validation functionality.
It handles shot point sorting checks, dither validation, flag discrepancy detection,
percentage calculations, and comprehensive report generation.

Classes:
- QCReportGenerator: Main class for handling QC report operations

Author: aldien03@gmail.com
Date: 2025-09-30
"""

import os
import re
import logging
import pandas as pd
from typing import Dict, List, Tuple, Optional
from configparser import ConfigParser


class QCReportGenerator:
    """
    Class for generating comprehensive QC reports.

    Supports:
    - Shot point sorting validation (ascending/descending sequences)
    - Dither value checking (null/missing detection)
    - Flag discrepancy detection (Seispos vs script-generated)
    - Error percentage calculations for all QC flags
    - Shot point logging with flag details
    - Comprehensive report generation with popup display
    """

    def __init__(self, config: ConfigParser, sps_importer):
        """
        Initialize QCReportGenerator with configuration and SPS importer.

        Args:
            config: ConfigParser instance containing regex patterns
            sps_importer: SPSImporter instance for re-importing SPS files
        """
        self.config = config
        self.sps_importer = sps_importer
        self.dither_values = None  # Cache for dither file values

    def detect_sp_sorting(self, df: pd.DataFrame) -> List[str]:
        """
        Check for non-sequential shot point sorting in DataFrame.
        Handles both ascending and descending sequences, detecting out-of-order points.

        Args:
            df: DataFrame with 'shot_point' column

        Returns:
            List of sorting issues found
        """
        issues = []

        if 'shot_point' in df.columns and len(df) > 2:
            # Get shot points maintaining their original order
            shot_points = df['shot_point'].dropna().reset_index(drop=True)

            if len(shot_points) < 3:
                return issues

            # Determine the expected direction (ascending or descending) based on first few points
            differences = []
            for i in range(min(5, len(shot_points) - 1)):
                diff = shot_points.iloc[i + 1] - shot_points.iloc[i]
                if diff != 0:  # Ignore duplicates
                    differences.append(diff)

            if not differences:
                return issues

            # Determine if sequence should be ascending or descending
            ascending = sum(1 for d in differences if d > 0) >= sum(1 for d in differences if d < 0)

            # Determine the typical step size (usually 2 for seismic data)
            abs_differences = [abs(d) for d in differences if d != 0]
            if abs_differences:
                typical_step = min(abs_differences)  # Usually 2
                max_allowed_gap = typical_step * 3  # Allow some flexibility for gaps
            else:
                typical_step = 2
                max_allowed_gap = 6

            # Check for sorting issues - single comprehensive loop
            seen_sps = set()  # Track shot points to detect duplicates

            for i in range(len(shot_points) - 1):
                current_sp = shot_points.iloc[i]
                next_sp = shot_points.iloc[i + 1]

                # Check for duplicates
                if next_sp == current_sp:
                    if current_sp not in seen_sps:
                        issues.append(f"Duplicate SP {int(current_sp)} detected")
                        seen_sps.add(current_sp)
                    continue  # Skip further checks for duplicate

                # Check for wrong sequence direction
                if ascending:
                    if next_sp < current_sp:
                        issues.append(f"SP {int(next_sp)} appears after SP {int(current_sp)} (should be ascending)")
                    elif next_sp - current_sp > max_allowed_gap:
                        # Large gap - may indicate missing shot points
                        gap_size = int(next_sp - current_sp)
                        issues.append(f"Large gap detected: SP {int(current_sp)} to {int(next_sp)} (gap: {gap_size})")
                else:  # descending
                    if next_sp > current_sp:
                        issues.append(f"SP {int(next_sp)} appears after SP {int(current_sp)} (should be descending)")
                    elif current_sp - next_sp > max_allowed_gap:
                        # Large gap - may indicate missing shot points
                        gap_size = int(current_sp - next_sp)
                        issues.append(f"Large gap detected: SP {int(current_sp)} to {int(next_sp)} (gap: {gap_size})")

        return issues

    def load_dither_file(self) -> Optional[List[float]]:
        """
        Load dither values from the dither file specified in config.ini.

        Returns:
            List of dither values in seconds (e.g., -0.091, -0.044, etc.)
            Returns None if file not found or error occurs
        """
        if self.dither_values is not None:
            return self.dither_values

        try:
            dither_file_path = self.config.get('LineLog', 'dither_file', fallback=None)
            if not dither_file_path or not os.path.exists(dither_file_path):
                logging.warning(f"Dither file not found at: {dither_file_path}")
                return None

            dither_values = []
            with open(dither_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            dither_values.append(float(line))
                        except ValueError:
                            logging.warning(f"Skipping invalid dither value: {line}")
                            continue

            if dither_values:
                logging.info(f"Loaded {len(dither_values)} dither values from {dither_file_path}")
                self.dither_values = dither_values
                return dither_values
            else:
                logging.warning(f"No valid dither values found in {dither_file_path}")
                return None

        except Exception as e:
            logging.error(f"Error loading dither file: {e}")
            return None

    def convert_dither_format(self, dither_seconds: float) -> int:
        """
        Convert dither value from seconds to milliseconds format used in SPS.

        Dither file format: -0.11, -0.058, -0.023, 0.011, 0.073, -0.011 (seconds)
        SPS format: -110, -58, -23, 11, 73, -11 (milliseconds)

        The conversion formula: milliseconds = round(seconds * 1000)

        Args:
            dither_seconds: Dither value in seconds

        Returns:
            Dither value in SPS format (milliseconds)
        """
        # Convert seconds to milliseconds
        # Formula: -0.11s * 1000 → -110ms, -0.058s * 1000 → -58ms
        return round(dither_seconds * 1000)

    def find_dither_pattern_match(self, previous_dithers: List[int], reference_dithers: List[float], tolerance: int = 2) -> Optional[int]:
        """
        Find the next dither value by pattern matching with previous 5 dither values.

        Args:
            previous_dithers: Last 5 (or fewer) valid dither values from SPS (in SPS format)
            reference_dithers: Full list of reference dither values from file (in seconds)
            tolerance: Allowed difference for pattern matching (default: 2)

        Returns:
            Next dither value in SPS format, or None if no match found
        """
        if not reference_dithers or not previous_dithers:
            return None

        # Convert reference dithers to SPS format
        reference_sps_format = [self.convert_dither_format(d) for d in reference_dithers]

        # Look for pattern match in reference sequence
        pattern_length = len(previous_dithers)

        for i in range(len(reference_sps_format) - pattern_length):
            # Check if the pattern matches (with tolerance)
            match = True
            for j in range(pattern_length):
                diff = abs(reference_sps_format[i + j] - previous_dithers[j])
                if diff > tolerance:
                    match = False
                    break

            # If pattern matches and there's a next value, return it
            if match and (i + pattern_length) < len(reference_sps_format):
                next_dither = reference_sps_format[i + pattern_length]
                logging.debug(f"Found pattern match at index {i}, next dither: {next_dither}")
                return next_dither

        return None

    def check_dither_values(self, df: pd.DataFrame) -> Tuple[List[str], Dict[str, int]]:
        """
        Check for missing or null dither values and suggest correct values from dither file.
        Note: Zero (0) is a valid dither value and should not be flagged.
        IMPORTANT: This method does NOT modify the DataFrame - it only reports issues.

        Args:
            df: DataFrame with 'shot_dither' and 'shot_point' columns

        Returns:
            Tuple of (issues_list, detection_stats)
            - issues_list: List of dither issues with suggested correct values
            - detection_stats: Dict with 'detected' (missing count) and 'suggested' (found correct value) counts
        """
        issues = []
        detected_count = 0
        suggested_count = 0
        detection_stats = {'detected': 0, 'suggested': 0}

        if 'shot_dither' not in df.columns or 'shot_point' not in df.columns:
            return issues, detection_stats

        # Load dither reference file
        reference_dithers = self.load_dither_file()

        try:
            previous_valid_dithers = []  # Track last 5 valid dithers

            for idx in df.index:
                dither_val = df.at[idx, 'shot_dither']
                shot_point = df.at[idx, 'shot_point']
                dither_str = str(dither_val)

                is_missing = False

                # Check if dither is missing
                if pd.isna(dither_val) or pd.isnull(dither_val):
                    is_missing = True
                elif isinstance(dither_val, str):
                    # String values - check if empty or whitespace only
                    if dither_str.strip() == '' or dither_str.strip().lower() in ['nan', 'none']:
                        is_missing = True
                elif dither_str.strip() == '' or dither_str.strip().lower() in ['nan', 'none']:
                    is_missing = True

                if is_missing:
                    detected_count += 1

                    # Try to suggest correct dither value using pattern matching
                    if reference_dithers and len(previous_valid_dithers) > 0:
                        # Use last 5 valid dithers for pattern matching
                        pattern = previous_valid_dithers[-5:] if len(previous_valid_dithers) >= 5 else previous_valid_dithers
                        suggested_dither = self.find_dither_pattern_match(pattern, reference_dithers)

                        if suggested_dither is not None:
                            # Found suggested dither value - report to user
                            suggested_count += 1
                            issues.append(f"Dither Check: SP {shot_point} may not have dither value applied. Correct Dither Value: '{suggested_dither}'")
                            logging.info(f"Detected missing dither for SP {shot_point}, suggested value: {suggested_dither}")
                            # Add suggested value to tracking for next pattern match
                            previous_valid_dithers.append(suggested_dither)
                        else:
                            # Could not find match - try with more lenient tolerance
                            lenient_suggested = self.find_dither_pattern_match(
                                pattern,
                                reference_dithers,
                                tolerance=5
                            )
                            if lenient_suggested is not None:
                                suggested_count += 1
                                issues.append(f"Dither Check: SP {shot_point} may not have dither value applied. Correct Dither Value: '{lenient_suggested}' (uncertain)")
                                previous_valid_dithers.append(lenient_suggested)
                            else:
                                issues.append(f"Dither Check: SP {shot_point} may not have dither value applied. Correct Dither Value: 'Unknown'")
                    else:
                        # No reference file or insufficient previous dithers
                        issues.append(f"Dither Check: SP {shot_point} may not have dither value applied. Correct Dither Value: 'Unknown'")
                else:
                    # Valid dither - add to tracking list
                    try:
                        dither_int = int(float(dither_val))
                        previous_valid_dithers.append(dither_int)
                    except (ValueError, TypeError):
                        logging.warning(f"Could not convert dither value to int at SP {shot_point}: {dither_val}")

            # Update detection stats
            detection_stats['detected'] = detected_count
            detection_stats['suggested'] = suggested_count

            if detected_count > 0:
                logging.info(f"Dither detection summary: {detected_count} missing detected, {suggested_count} suggestions provided")

        except Exception as e:
            logging.error(f"Error in dither checking: {e}")
            # Fallback to basic check
            missing_dither = df[df['shot_dither'].isna()]
            for _, row in missing_dither.iterrows():
                shot_point = row['shot_point']
                issues.append(f"Dither Check: SP {shot_point} may not have dither value applied. Correct Dither Value: 'Unknown'")
                detection_stats['detected'] += 1

        return issues, detection_stats

    def check_flag_discrepancies(self, df: pd.DataFrame) -> List[str]:
        """
        Check for discrepancies between Seispos flags and script-generated flags.

        Args:
            df: DataFrame containing both sets of flags with suffixes

        Returns:
            List of flag discrepancies found
        """
        issues = []

        flag_mappings = [
            ('gun_timing_flag_sps', 'gun_timing_flag_script', 'Gun Timing Edit Flag'),
            ('gun_pressure_flag_sps', 'gun_pressure_flag_script', 'Gun Pressure Edit Flag'),
            ('repeatability_flag_sps', 'repeatability_flag_script', 'Source repeatability flag'),
            ('sma_flag_sps', 'sma_flag_script', 'Source position accuracy flag')
        ]

        for seispos_col, script_col, description in flag_mappings:
            if seispos_col in df.columns and script_col in df.columns and 'shot_point' in df.columns:
                df_clean = df.copy()
                df_clean[seispos_col] = df_clean[seispos_col].fillna(0)
                df_clean[script_col] = df_clean[script_col].fillna(0)

                discrepancies = df_clean[df_clean[seispos_col] != df_clean[script_col]]

                for _, row in discrepancies.iterrows():
                    shot_point = row['shot_point']
                    seispos_val = row[seispos_col]
                    script_val = row[script_col]
                    issues.append(
                        f"Flag Discrepancy: SP {shot_point} - {description} "
                        f"(Seispos: {seispos_val}, Script: {script_val})"
                    )

        return issues

    def detect_missing_seispos_flags(self, sps_df: pd.DataFrame) -> Dict:
        """
        Detect missing/null Seispos flags and report consecutive ranges.

        Seispos sometimes outputs null/empty flags for consecutive shot points.
        This method detects these ranges and identifies which flags are missing.

        SPS Flag Columns (from H26 header):
        - gun_depth_flag (column 98)
        - gun_timing_flag (column 99)
        - gun_pressure_flag (column 100)
        - repeatability_flag (column 101)
        - sma_flag (column 102)

        Args:
            sps_df: DataFrame from SPS import containing Seispos flags

        Returns:
            Dictionary with missing flag ranges:
            {
                'has_missing': bool,
                'summary': {'total_flags': int, 'missing_flags': int},
                'details': [
                    {
                        'flag': 'gun_depth_flag',
                        'ranges': ['6800-6820', '6850-6870'],
                        'count': 35
                    },
                    ...
                ],
                'report_text': str
            }
        """
        from line_log_manager import LineLogManager

        # Flag columns to check (from Seispos output)
        flag_columns = {
            'gun_depth_flag': 'Gun Depth',
            'gun_timing_flag': 'Gun Timing',
            'gun_pressure_flag': 'Gun Pressure',
            'repeatability_flag': 'Repeatability',
            'sma_flag': 'SMA (Position Accuracy)'
        }

        results = {
            'has_missing': False,
            'summary': {'total_flags': 0, 'missing_flags': 0},
            'details': [],
            'report_text': ''
        }

        if sps_df.empty:
            return results

        # Create a temporary LineLogManager for range detection
        from configparser import ConfigParser
        temp_config = ConfigParser()
        temp_config.add_section('LineLog')
        temp_config.set('LineLog', 'shot_increment', '2')
        llm = LineLogManager(temp_config)

        report_lines = []
        total_missing = 0

        for flag_col, flag_name in flag_columns.items():
            if flag_col not in sps_df.columns:
                logging.warning(f"Flag column {flag_col} not found in SPS DataFrame")
                continue

            # Find shot points where flag is null/NaN/pd.NA/empty
            # Consider 0 as valid (no error), so check for null/NaN/pd.NA only
            # Int64 dtype uses pd.NA for missing values
            missing_mask = sps_df[flag_col].isna()  # This detects both NaN and pd.NA
            missing_count = missing_mask.sum()

            logging.debug(f"Checking {flag_col}: Found {missing_count} missing values (NaN/pd.NA)")
            logging.debug(f"  dtype: {sps_df[flag_col].dtype}")

            # Show sample values (both missing and non-missing)
            sample_df = sps_df[['shot_point', flag_col]].head(30)
            logging.debug(f"  Sample SP and {flag_col}:")
            for idx, row in sample_df.iterrows():
                val = row[flag_col]
                is_missing = pd.isna(val)
                logging.debug(f"    SP {row['shot_point']}: {val} (missing={is_missing})")

            missing_sp = sps_df.loc[missing_mask, 'shot_point'].tolist()

            if missing_sp:
                logging.info(f"Found {len(missing_sp)} missing {flag_col} values at SP: {missing_sp[:10]}...")
                results['has_missing'] = True
                total_missing += len(missing_sp)

                # Detect consecutive ranges
                ranges_str = llm.detect_range(missing_sp)

                # Add to details
                results['details'].append({
                    'flag': flag_col,
                    'flag_name': flag_name,
                    'ranges': ranges_str if isinstance(ranges_str, list) else [ranges_str],
                    'count': len(missing_sp)
                })

                # Format for report - keep concise
                # Show count only, not full ranges
                report_lines.append(f"  • {flag_name}: {len(missing_sp)} SP missing")

        # Update summary
        results['summary']['total_flags'] = len(flag_columns)
        results['summary']['missing_flags'] = len(results['details'])

        # Generate report text - limit to first 3 flags
        if report_lines:
            if len(report_lines) > 3:
                limited_lines = report_lines[:3]
                limited_lines.append(f"  ... and {len(report_lines) - 3} more flag type(s)")
                results['report_text'] = '\n'.join(limited_lines)
            else:
                results['report_text'] = '\n'.join(report_lines)
        else:
            results['report_text'] = "✓ All flags present"

        return results

    def detect_actual_first_sp(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect the actual first shot point from SPS data.

        Args:
            df: DataFrame containing SPS data with shot_point and time columns

        Returns:
            Dictionary with first SP info:
            {
                'sp': int,
                'time': str (HH:MM format),
                'time_full': str (HH:MM:SS format),
                'datetime': datetime object
            }
            Returns None if no valid data found
        """
        from datetime import datetime
        import pandas as pd

        if df.empty or 'shot_point' not in df.columns:
            return None

        # Get the first row (should be first shot point)
        first_row = df.iloc[0]
        first_sp = first_row['shot_point']

        # Extract time
        sps_time_full = None
        sps_datetime = None

        # Try time_UTC first
        if 'time_UTC' in df.columns:
            time_val = first_row['time_UTC']
            if pd.notna(time_val):
                sps_time_full = str(time_val)

        # Try datetime_UTC
        if not sps_time_full and 'datetime_UTC' in df.columns:
            datetime_val = first_row['datetime_UTC']
            if pd.notna(datetime_val):
                if hasattr(datetime_val, 'strftime'):
                    sps_time_full = datetime_val.strftime('%H:%M:%S')
                    sps_datetime = datetime_val
                else:
                    sps_time_full = str(datetime_val).split()[-1] if ' ' in str(datetime_val) else str(datetime_val)

        if not sps_time_full:
            return None

        # Extract HH:MM format
        sps_time_hhmm = sps_time_full[:5] if len(sps_time_full) >= 5 else sps_time_full

        return {
            'sp': int(first_sp),
            'time': sps_time_hhmm,
            'time_full': sps_time_full,
            'datetime': sps_datetime
        }

    def validate_marker_timing(self, merged_df: pd.DataFrame, markers: Dict) -> Dict:
        """
        Validate timing discrepancy between line log manual entry and SPS data.

        Compares the time recorded in line log (manual entry) with actual time
        from SPS data for marker shot points (FASP, FGSP, LGSP, FOSP, LOSP).

        Args:
            merged_df: DataFrame containing SPS data with shot_point and time columns
            markers: Dictionary of markers from extract_shot_point_markers()
                    Format: {'FASP': {'time': str, 'sp': int, ...}, ...}

        Returns:
            Dictionary with validation results:
            {
                'summary': {'ok': int, 'warnings': int, 'errors': int},
                'details': [
                    {
                        'marker': 'FGSP',
                        'sp': 6823,
                        'linelog_time': '08:39',
                        'sps_time': '08:39',
                        'diff_minutes': 0,
                        'status': 'OK'  # or 'WARNING' or 'ERROR'
                    },
                    ...
                ],
                'report_text': str  # Formatted report for display
            }
        """
        from datetime import datetime, time
        import pandas as pd

        # Get thresholds from config
        warning_threshold = self.config.getint('LineLog', 'marker_time_warning_threshold', fallback=5)
        error_threshold = self.config.getint('LineLog', 'marker_time_error_threshold', fallback=10)

        results = {
            'summary': {'ok': 0, 'warnings': 0, 'errors': 0},
            'details': [],
            'report_text': '',
            'fasp_correction': None  # Will store FASP correction info if needed
        }

        report_lines = []

        # Marker order for reporting
        # Note: FASP is excluded as it's removed in final SPS
        marker_order = ['FOSP', 'LOSP', 'FGSP', 'LGSP', 'LSP']

        for marker_name in marker_order:

            marker_data = markers.get(marker_name)

            # Skip if marker not found or None
            if not marker_data:
                continue

            sp = marker_data.get('sp')
            linelog_time_str = marker_data.get('time')

            # Skip if SP or time is None
            if sp is None or not linelog_time_str:
                continue

            # Find matching SP in DataFrame
            sp_row = merged_df[merged_df['shot_point'] == sp]

            if sp_row.empty:
                # SP not found in SPS data
                report_lines.append(f"{marker_name} (SP {sp}): Not found in SPS data ⚠")
                results['details'].append({
                    'marker': marker_name,
                    'sp': sp,
                    'linelog_time': linelog_time_str,
                    'sps_time': None,
                    'diff_seconds': None,
                    'status': 'NOT_FOUND'
                })
                results['summary']['warnings'] += 1
                continue

            # Extract SPS time
            # Try time_UTC first, then datetime_UTC
            sps_time = None
            if 'time_UTC' in sp_row.columns:
                sps_time_val = sp_row['time_UTC'].iloc[0]
                if pd.notna(sps_time_val):
                    if isinstance(sps_time_val, str):
                        sps_time = sps_time_val
                    else:
                        sps_time = str(sps_time_val)

            if not sps_time and 'datetime_UTC' in sp_row.columns:
                datetime_val = sp_row['datetime_UTC'].iloc[0]
                if pd.notna(datetime_val):
                    if hasattr(datetime_val, 'strftime'):
                        sps_time = datetime_val.strftime('%H:%M:%S')
                    else:
                        sps_time = str(datetime_val).split()[-1] if ' ' in str(datetime_val) else str(datetime_val)

            if not sps_time:
                report_lines.append(f"{marker_name} (SP {sp}): No time data in SPS ⚠")
                results['details'].append({
                    'marker': marker_name,
                    'sp': sp,
                    'linelog_time': linelog_time_str,
                    'sps_time': None,
                    'diff_seconds': None,
                    'status': 'NO_TIME'
                })
                results['summary']['warnings'] += 1
                continue

            # Parse times and calculate difference
            try:
                # Parse line log time (format: HH:MM, H:MM, HHMMSS as integer, or HH:MM:SS)
                linelog_time_str_original = str(linelog_time_str)
                linelog_time_str = str(linelog_time_str).strip()

                # Handle integer format from Excel (e.g., 104150 = 10:41:50)
                if ':' not in linelog_time_str and linelog_time_str.isdigit():
                    logging.debug(f"Converting integer time format for {marker_name}: {linelog_time_str}")
                    if len(linelog_time_str) == 6:  # HHMMSS
                        linelog_time_str = f"{linelog_time_str[:2]}:{linelog_time_str[2:4]}"
                    elif len(linelog_time_str) == 5:  # HMMSS
                        linelog_time_str = f"0{linelog_time_str[0]}:{linelog_time_str[1:3]}"
                    elif len(linelog_time_str) == 4:  # HHMM
                        linelog_time_str = f"{linelog_time_str[:2]}:{linelog_time_str[2:]}"
                    elif len(linelog_time_str) == 3:  # HMM
                        linelog_time_str = f"0{linelog_time_str[0]}:{linelog_time_str[1:]}"

                # Handle both HH:MM and HH:MM:SS formats
                if linelog_time_str.count(':') == 2:
                    # Has seconds, extract only HH:MM
                    linelog_time_str = ':'.join(linelog_time_str.split(':')[:2])
                elif linelog_time_str.count(':') == 0:
                    # No colon at all, might be unusual format
                    logging.warning(f"Unusual time format for line log: {linelog_time_str}")

                if len(linelog_time_str.split(':')[0]) == 1:
                    linelog_time_str = '0' + linelog_time_str  # Pad single digit hour

                logging.debug(f"{marker_name} LineLog time: {linelog_time_str_original} -> {linelog_time_str}")
                linelog_time = datetime.strptime(linelog_time_str, '%H:%M').time()

                # Parse SPS time - extract HH:MM only
                sps_time_original = str(sps_time)
                sps_time = str(sps_time).strip()

                # Handle integer format from Excel (e.g., 104150 = 10:41:50)
                if ':' not in sps_time and sps_time.isdigit():
                    logging.debug(f"Converting integer time format for SPS: {sps_time}")
                    if len(sps_time) == 6:  # HHMMSS
                        sps_time = f"{sps_time[:2]}:{sps_time[2:4]}"
                    elif len(sps_time) == 5:  # HMMSS
                        sps_time = f"0{sps_time[0]}:{sps_time[1:3]}"
                    elif len(sps_time) == 4:  # HHMM
                        sps_time = f"{sps_time[:2]}:{sps_time[2:]}"
                    elif len(sps_time) == 3:  # HMM
                        sps_time = f"0{sps_time[0]}:{sps_time[1:]}"

                if sps_time.count(':') == 2:
                    sps_time = ':'.join(sps_time.split(':')[:2])  # Extract HH:MM only

                if ':' in sps_time and len(sps_time.split(':')[0]) == 1:
                    sps_time = '0' + sps_time

                logging.debug(f"{marker_name} SPS time: {sps_time_original} -> {sps_time}")
                sps_time_obj = datetime.strptime(sps_time, '%H:%M').time()

                # Calculate time difference in minutes
                linelog_minutes = linelog_time.hour * 60 + linelog_time.minute
                sps_minutes = sps_time_obj.hour * 60 + sps_time_obj.minute
                diff_minutes = abs(linelog_minutes - sps_minutes)

                # Determine status (thresholds in minutes)
                if diff_minutes <= warning_threshold:
                    status = 'OK'
                    symbol = '✓'
                    results['summary']['ok'] += 1
                elif diff_minutes <= error_threshold:
                    status = 'WARNING'
                    symbol = '⚠'
                    results['summary']['warnings'] += 1
                else:
                    status = 'ERROR'
                    symbol = '✗'
                    results['summary']['errors'] += 1

                # Format report line
                report_lines.append(
                    f"{marker_name} (SP {sp}): LineLog={linelog_time_str}, SPS={sps_time}, "
                    f"Diff={diff_minutes}min {symbol}"
                )

                # Add to details
                results['details'].append({
                    'marker': marker_name,
                    'sp': sp,
                    'linelog_time': linelog_time_str,
                    'sps_time': sps_time,
                    'diff_minutes': diff_minutes,
                    'status': status
                })

            except Exception as e:
                logging.error(f"Error parsing times for {marker_name}: {str(e)}")
                report_lines.append(f"{marker_name} (SP {sp}): Time parsing error ⚠")
                results['details'].append({
                    'marker': marker_name,
                    'sp': sp,
                    'linelog_time': linelog_time_str,
                    'sps_time': sps_time,
                    'diff_seconds': None,
                    'status': 'PARSE_ERROR'
                })
                results['summary']['warnings'] += 1

        # Add summary
        report_lines.append("")
        report_lines.append(
            f"Summary: {results['summary']['ok']} OK, "
            f"{results['summary']['warnings']} warnings, "
            f"{results['summary']['errors']} errors"
        )

        results['report_text'] = '\n'.join(report_lines)
        return results

    def generate_qc_report(self, parent_dir: str, merged_df: pd.DataFrame,
                          markers: Dict = None) -> Tuple[bool, str]:
        """
        Generate QC report with sorting, dither, flag checks, and marker timing validation.

        Args:
            parent_dir: Directory containing the sequence data
            merged_df: Merged DataFrame containing both SPS and script-generated data
            markers: Dictionary of shot point markers (optional, for timing validation)
                    Format: {'FASP': {'time': str, 'sp': int, ...}, ...}

        Returns:
            Tuple of (success, report_content_string)
        """
        try:
            logging.info(f"Generating QC report for directory: {parent_dir}")
            logging.info(f"Merged DataFrame shape: {merged_df.shape if not merged_df.empty else 'Empty'}")

            if not parent_dir or not os.path.exists(parent_dir):
                logging.error(f"Invalid directory path: {parent_dir}")
                return False, f"Invalid directory path: {parent_dir}"

            # Find SPS file
            processed_dir = os.path.join(parent_dir, "Processed")
            sps_pattern = self.config.get("Regex_Filenames", "sps_file_pattern",
                                         fallback=r'^0256-\d{4}[A-Z]\d\d{4}\.S01$')

            sps_files = []
            sps_file_path = None

            if os.path.exists(processed_dir):
                try:
                    processed_files = os.listdir(processed_dir)
                    sps_files = [f for f in processed_files if re.match(sps_pattern, f)]
                    if sps_files:
                        sps_file_path = os.path.join(processed_dir, sps_files[0])
                except Exception as e:
                    logging.error(f"Error listing Processed directory: {e}")

            if not sps_files:
                try:
                    main_files = os.listdir(parent_dir)
                    sps_files = [f for f in main_files if re.match(sps_pattern, f)]
                    if sps_files:
                        sps_file_path = os.path.join(parent_dir, sps_files[0])
                except Exception as e:
                    logging.error(f"Error listing main directory: {e}")

            if not sps_files:
                logging.warning("No SPS file found for QC report")
                return False, (
                    f"QC REPORT (No SPS File Found)\n\n"
                    f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Source directory: {parent_dir}\n"
                    f"Processed directory: {processed_dir}\n\n"
                    f"ERROR: No SPS file found matching pattern {sps_pattern}\n"
                    f"Searched in both main directory and Processed subdirectory.\n"
                    f"Please check that the SPS file exists and follows the naming convention."
                )

            # Re-import SPS data
            logging.info(f"Importing SPS data from: {sps_file_path}")
            sps_df = self.sps_importer.import_file(sps_file_path)

            if sps_df.empty:
                logging.warning("No data imported from SPS file for QC report")
                return False, "No data could be imported from the SPS file."

            # Perform QC checks
            logging.info("Starting SP sorting check...")
            sorting_issues = self.detect_sp_sorting(sps_df)

            logging.info("Starting dither check...")
            dither_issues, dither_recovery_stats = self.check_dither_values(sps_df)

            # Check for missing Seispos flags
            logging.info("Checking for missing Seispos flags...")
            missing_flags_results = self.detect_missing_seispos_flags(sps_df)

            # Check flag discrepancies
            flag_issues = []
            if 'shot_point' in sps_df.columns and 'shot_point' in merged_df.columns:
                sps_flags = sps_df[['shot_point'] + [col for col in sps_df.columns if col.endswith('_flag')]]
                merged_flags = merged_df[['shot_point'] + [col for col in merged_df.columns if col.endswith('_flag')]]

                if not sps_flags.empty and not merged_flags.empty:
                    comparison_df = sps_flags.merge(merged_df, on='shot_point', how='inner', suffixes=('_sps', '_script'))
                    flag_issues = self.check_flag_discrepancies(comparison_df)

            # Marker timing validation (if markers provided)
            timing_results = None
            if markers:
                logging.info("Validating marker timing...")
                timing_results = self.validate_marker_timing(merged_df, markers)

            # Generate enhanced report content
            report_content = []

            # Header
            report_content.append("=" * 60)
            report_content.append("  QC REPORT SUMMARY")
            report_content.append("=" * 60)
            report_content.append("")

            # Overall Status
            total_issues = len(sorting_issues) + len(dither_issues) + len(flag_issues)

            # Add timing issues if validation was performed
            timing_issues = 0
            if timing_results:
                timing_issues = timing_results['summary']['warnings'] + timing_results['summary']['errors']
                total_issues += timing_issues

            # Add missing flags count (count flags with missing data, not total missing SP)
            missing_flags_count = 0
            if missing_flags_results['has_missing']:
                missing_flags_count = missing_flags_results['summary']['missing_flags']
                total_issues += missing_flags_count

            if total_issues == 0:
                report_content.append("✓ STATUS: ALL CHECKS PASSED")
            else:
                report_content.append("⚠ STATUS: ISSUES DETECTED")

            report_content.append("")
            report_content.append(f"Total Issues Found: {total_issues}")
            report_content.append(f"  • Sorting Issues: {len(sorting_issues)}")
            report_content.append(f"  • Dither Issues: {len(dither_issues)}")
            report_content.append(f"  • Flag Discrepancies: {len(flag_issues)}")
            if missing_flags_results['has_missing']:
                report_content.append(f"  • Missing Seispos Flags: {missing_flags_count} flag type(s)")
            if timing_results:
                report_content.append(f"  • Marker Timing Issues: {timing_issues}")
            report_content.append("")

            # Section 1: Shot Point Sorting
            report_content.append("─" * 60)
            report_content.append("SHOT POINT SORTING CHECK:")
            report_content.append("─" * 60)
            if sorting_issues:
                report_content.append(f"✗ Found {len(sorting_issues)} issue(s)")
                report_content.append("")
                # Show first 3 issues only
                for issue in sorting_issues[:3]:
                    report_content.append(f"  • {issue}")
                if len(sorting_issues) > 3:
                    report_content.append(f"  ... and {len(sorting_issues) - 3} more issue(s)")
                report_content.append("")
            else:
                report_content.append("✓ No issues")
                report_content.append("")

            # Section 2: Dither Values
            report_content.append("─" * 60)
            report_content.append("DITHER VALUE CHECK:")
            report_content.append("─" * 60)

            if dither_issues:
                # Show first 5 issues with suggested values
                for issue in dither_issues[:5]:
                    report_content.append(f"  • {issue}")
                if len(dither_issues) > 5:
                    report_content.append(f"  ... and {len(dither_issues) - 5} more issue(s)")
                report_content.append("")
            else:
                report_content.append("✓ No issues")
                report_content.append("")

            # Section 3: Flag Discrepancies
            report_content.append("─" * 60)
            report_content.append("FLAG DISCREPANCY CHECK:")
            report_content.append("─" * 60)
            if flag_issues:
                report_content.append(f"✗ Found {len(flag_issues)} discrepancy(ies)")
                report_content.append("")
                # Show first 3 issues
                for issue in flag_issues[:3]:
                    report_content.append(f"  • {issue}")
                if len(flag_issues) > 3:
                    report_content.append(f"  ... and {len(flag_issues) - 3} more")
                report_content.append("")
            else:
                report_content.append("✓ No discrepancies")
                report_content.append("")

            # Section 4: Missing Seispos Flags
            report_content.append("─" * 60)
            report_content.append("MISSING SEISPOS FLAGS:")
            report_content.append("─" * 60)
            if missing_flags_results['has_missing']:
                report_content.append(f"✗ Missing in {missing_flags_count} flag type(s)")
                report_content.append("")
                report_content.append(missing_flags_results['report_text'])
                report_content.append("")
            else:
                report_content.append(missing_flags_results['report_text'])
                report_content.append("")

            # Section 5: Marker Timing Validation (if markers provided)
            if timing_results:
                report_content.append("─" * 60)
                report_content.append("TIMING VALIDATION:")
                report_content.append("─" * 60)
                report_content.append("")
                report_content.append(timing_results['report_text'])
                report_content.append("")

            # Footer
            report_content.append("=" * 60)
            if total_issues == 0:
                report_content.append("QC Status: All quality checks passed successfully")
            else:
                report_content.append(f"QC Status: {total_issues} issue(s) require attention")
            report_content.append("=" * 60)

            logging.info("QC report analysis completed successfully")
            return True, '\n'.join(report_content)

        except Exception as e:
            logging.error(f"Error generating QC report: {str(e)}", exc_info=True)
            return False, f"Failed to generate QC report: {str(e)}"

    def calculate_percentages(self, df: pd.DataFrame, total_sp: int = None,
                            fgsp: int = None, lgsp: int = None) -> Dict:
        """
        Calculate error percentages for each QC flag.

        If FGSP and LGSP are provided, calculates percentages based only on
        production shots (FGSP to LGSP range), excluding approach and overlap shots.

        Args:
            df: DataFrame containing QC flag columns
            total_sp: Total number of shot points (deprecated, auto-calculated if not provided)
            fgsp: First Good Shot Point (optional, for production-only calculation)
            lgsp: Last Good Shot Point (optional, for production-only calculation)

        Returns:
            Dictionary containing error percentages for each flag
        """
        logging.info("Calculating error percentages...")

        # Filter DataFrame to production shots if FGSP/LGSP provided
        if fgsp is not None and lgsp is not None:
            min_sp = min(fgsp, lgsp)
            max_sp = max(fgsp, lgsp)
            production_df = df[(df['shot_point'] >= min_sp) & (df['shot_point'] <= max_sp)]
            total_sp = len(production_df)
            logging.info(f"Filtering to production shots: FGSP={fgsp}, LGSP={lgsp}, Production SP count={total_sp}")
        else:
            production_df = df
            if total_sp is None:
                total_sp = len(production_df)
            logging.info(f"Using all shot points, Total SP count={total_sp}")

        try:
            flag_columns = [
                'sti_flag', 'sub_array_sep_flag', 'cos_sep_flag', 'volume_flag',
                'gun_depth_flag', 'gun_pressure_flag', 'gun_timing_flag',
                'repeatability_flag', 'sma_flag'
            ]

            percentages = {}
            for flag in flag_columns:
                if flag not in production_df.columns:
                    logging.warning(f"Flag column {flag} not found in dataframe")
                    continue

                flagged_records = (production_df[flag].fillna(0) > 0).sum()
                error_records = (production_df[flag] == 2).sum()
                warning_records = (production_df[flag] == 1).sum()

                total_percent = (flagged_records / total_sp) * 100
                error_percent = (error_records / total_sp) * 100
                warning_percent = (warning_records / total_sp) * 100

                percentages[flag] = {
                    'total': total_percent,
                    'errors': error_percent,
                    'warnings': warning_percent,
                    'total_count': flagged_records,
                    'error_count': error_records,
                    'warning_count': warning_records
                }

                logging.info(f"{flag}: Total={flagged_records} ({total_percent:.2f}%), Errors={error_records}, Warnings={warning_records}")

            # Extract specific percentages
            if 'repeatability_flag' in percentages:
                percent_radial = percentages['repeatability_flag']['total']
            else:
                percent_radial = 0
                logging.warning("Repeatability Flag not found in the DataFrame.")

            if 'gun_depth_flag' in percentages:
                percent_gd_errors = percentages['gun_depth_flag']['total']
            else:
                percent_gd_errors = 0
                logging.warning("gun_depth_flag not found in the DataFrame.")

            percentages['percent_radial'] = percent_radial
            percentages['percent_gd_errors'] = percent_gd_errors

            # Calculate overall statistics
            total_flags = sum(df[flag_columns].sum())
            total_errors = sum((df[flag_columns] == 2).sum())
            total_warnings = sum((df[flag_columns] == 1).sum())

            percentages['overall'] = {
                'total': (total_flags / (total_sp * len(flag_columns))) * 100,
                'errors': (total_errors / (total_sp * len(flag_columns))) * 100,
                'warnings': (total_warnings / (total_sp * len(flag_columns))) * 100,
                'total_count': total_flags,
                'error_count': total_errors,
                'warning_count': total_warnings
            }

            logging.info("Overall QC Statistics:")
            logging.info(f"  Total Records: {total_sp}, Total Flags: {total_flags}")
            logging.info(f"  Error Rate: {percentages['overall']['errors']:.2f}%")

            return percentages

        except Exception as e:
            logging.error(f"Error calculating percentages: {str(e)}")
            raise

    def log_shotpoints(self, df: pd.DataFrame) -> Dict:
        """
        Log shot points with flags.

        Args:
            df: DataFrame containing QC flag columns

        Returns:
            Dictionary with shot points for each flag
        """
        logging.info("Logging flagged shot points...")

        try:
            flag_columns = [
                'sub_array_sep_flag', 'cos_sep_flag', 'volume_flag',
                'gun_depth_flag', 'gun_pressure_flag', 'gun_timing_flag',
                'repeatability_flag', 'sma_flag'
            ]

            log_data = {}
            for flag in flag_columns:
                log_data[f"log_{flag}"] = []

            for flag in flag_columns:
                if flag not in df.columns:
                    logging.warning(f"Flag column {flag} not found in dataframe")
                    continue

                flagged_records = df[df[flag].fillna(0) > 0]

                for index, row in flagged_records.iterrows():
                    if flag == 'gun_timing_flag':
                        timing_error_level = row[flag]

                        timing_cols = [col for col in df.columns if
                                     col.startswith('String') and 'Cluster' in col and 'Gun' in col and
                                     not col.endswith('-Depth') and not col.endswith('-Pressure')]

                        if timing_error_level == 1:
                            log_key = 'log_timing_warning'
                            min_threshold = 1.0
                            max_threshold = 1.5
                        elif timing_error_level == 2:
                            log_key = 'log_timing_error'
                            min_threshold = 1.5
                            max_threshold = float('inf')
                        else:
                            continue

                        matching_guns = []
                        for col in timing_cols:
                            timing_value = abs(row[col]) if pd.notna(row[col]) else 0
                            if timing_value not in [63, 61, 90] and min_threshold < timing_value <= max_threshold:
                                gun_parts = col.split('-')
                                if len(gun_parts) >= 3:
                                    gun_info = f"{gun_parts[0].replace('_', ' ')} {gun_parts[1].replace('_', ' ')} {gun_parts[2].replace('_', ' ')}"
                                    matching_guns.append(gun_info)

                        if log_key not in log_data:
                            log_data[log_key] = []

                        if matching_guns:
                            log_data[log_key].append((row['shot_point'], matching_guns))
                    else:
                        log_data[f"log_{flag}"].append(row['shot_point'])

            # Check for misfires and disabled guns
            timing_cols = [col for col in df.columns if
                         col.startswith('String') and 'Cluster' in col and 'Gun' in col and
                         not col.endswith('-Depth') and not col.endswith('-Pressure')]

            log_data['log_misfire_flag'] = []
            log_data['log_gun_disabled_flag'] = []

            for index, row in df.iterrows():
                misfire_guns = []
                disabled_guns = []

                for col in timing_cols:
                    timing_value = abs(row[col]) if pd.notna(row[col]) else 0

                    if timing_value == 90:
                        gun_parts = col.split('-')
                        if len(gun_parts) >= 3:
                            gun_info = f"{gun_parts[0].replace('_', ' ')} {gun_parts[1].replace('_', ' ')} {gun_parts[2].replace('_', ' ')}"
                            misfire_guns.append(gun_info)
                    elif timing_value == 61:
                        gun_parts = col.split('-')
                        if len(gun_parts) >= 3:
                            gun_info = f"{gun_parts[0].replace('_', ' ')} {gun_parts[1].replace('_', ' ')} {gun_parts[2].replace('_', ' ')}"
                            disabled_guns.append(gun_info)

                if misfire_guns:
                    shot_point_entry = (row['shot_point'], misfire_guns)
                    if shot_point_entry not in log_data['log_misfire_flag']:
                        log_data['log_misfire_flag'].append(shot_point_entry)

                if disabled_guns:
                    shot_point_entry = (row['shot_point'], disabled_guns)
                    if shot_point_entry not in log_data['log_gun_disabled_flag']:
                        log_data['log_gun_disabled_flag'].append(shot_point_entry)

            # Log autofires
            log_data['log_autofires'] = []
            if 'Raw: SST_GUN1 #Autofires' in df.columns:
                for index, row in df.iterrows():
                    if pd.notna(row['Raw: SST_GUN1 #Autofires']) and row['Raw: SST_GUN1 #Autofires'] > 0:
                        log_data['log_autofires'].append(row['shot_point'])
            else:
                logging.info("Column 'Raw: SST_GUN1 #Autofires' not found, skipping autofire check")

            return log_data

        except Exception as e:
            logging.error(f"Error logging shot points: {str(e)}")
            raise
