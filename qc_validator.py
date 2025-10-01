"""
QC Validator Module

This module provides quality control validation functionality for seismic NAV QC operations.

Classes:
- QCValidator: Apply QC thresholds and generate flags for navigation and source data

Author: PXGEONavQC Development Team
Date: 2025-09-30
"""

import logging
import re
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from config_manager import ConfigManager


@dataclass
class QCThresholds:
    """Data class to store QC threshold values"""
    # STI thresholds
    sti_warning_lower: float
    sti_warning_upper: float
    sti_error: float

    # Separation thresholds
    sub_array_sep_min: float
    sub_array_sep_max: float
    sub_array_sep_percent_threshold: float
    sub_array_sep_avg_min: float
    sub_array_sep_avg_max: float

    dual_cos_min: float
    dual_cos_max: float
    triple_cos_min: float
    triple_cos_max: float

    # Volume and depth thresholds
    volume_nominal: float
    gun_depth_min: float
    gun_depth_max: float
    gun_depth_nominal: float
    gun_depth_sensor_min: float
    gun_depth_sensor_max: float
    gun_depth_nominal_tolerance: float
    gun_depth_avg_tolerance: float

    # Pressure thresholds
    gun_pressure_min: float
    gun_pressure_max: float
    gun_pressure_nominal: float

    # Timing thresholds
    timing_warning: float
    timing_error: float

    # Other limits
    crossline_limit: float
    radial_limit: float
    sma_limit: float
    shot_increment: int
    consecutive_error_limit: int

    # Advanced consecutive error detection
    consec_error_window_7: int
    consec_error_window_24: int
    consec_error_threshold_12_of_24: int
    consec_error_window_40: int
    consec_error_threshold_16_of_40: int
    consec_error_percent_total: float


class QCValidator:
    """Apply QC thresholds and generate flags for navigation and source data"""

    def __init__(self, config: ConfigManager):
        """
        Initialize QC validator with configuration.

        Args:
            config: ConfigManager instance
        """
        self.config = config
        self.thresholds = self._load_thresholds()

    def _load_thresholds(self) -> QCThresholds:
        """
        Load QC thresholds from config.

        Returns:
            QCThresholds dataclass with all threshold values
        """
        logging.info("Loading QC thresholds from config...")

        try:
            thresholds = QCThresholds(
                # STI thresholds
                sti_warning_lower=self.config.getfloat('QC_Thresholds', 'sti_warning_lower', fallback=6.25),
                sti_warning_upper=self.config.getfloat('QC_Thresholds', 'sti_warning_upper', fallback=10.0),
                sti_error=self.config.getfloat('QC_Thresholds', 'sti_error_threshold', fallback=6.0),

                # Separation thresholds
                sub_array_sep_min=self.config.getfloat('QC_Thresholds', 'sub_array_sep_min', fallback=6.8),
                sub_array_sep_max=self.config.getfloat('QC_Thresholds', 'sub_array_sep_max', fallback=9.2),
                sub_array_sep_percent_threshold=self.config.getfloat('QC_Thresholds', 'sub_array_sep_percent_threshold', fallback=15.0),
                sub_array_sep_avg_min=self.config.getfloat('QC_Thresholds', 'sub_array_sep_avg_min', fallback=7.2),
                sub_array_sep_avg_max=self.config.getfloat('QC_Thresholds', 'sub_array_sep_avg_max', fallback=8.8),

                dual_cos_min=self.config.getfloat('QC_Thresholds', 'dual_cos_min', fallback=33.75),
                dual_cos_max=self.config.getfloat('QC_Thresholds', 'dual_cos_max', fallback=41.25),
                triple_cos_min=self.config.getfloat('QC_Thresholds', 'triple_cos_min', fallback=33.75),
                triple_cos_max=self.config.getfloat('QC_Thresholds', 'triple_cos_max', fallback=41.25),

                # Volume and depth thresholds
                volume_nominal=self.config.getfloat('QC_Thresholds', 'volume_nominal', fallback=3040),
                gun_depth_min=self.config.getfloat('QC_Thresholds', 'gun_depth_min', fallback=-8.0),
                gun_depth_max=self.config.getfloat('QC_Thresholds', 'gun_depth_max', fallback=-6.0),
                gun_depth_nominal=self.config.getfloat('QC_Thresholds', 'gun_depth_nominal', fallback=-7.0),
                gun_depth_sensor_min=self.config.getfloat('QC_Thresholds', 'gun_depth_sensor_min', fallback=-7.5),
                gun_depth_sensor_max=self.config.getfloat('QC_Thresholds', 'gun_depth_sensor_max', fallback=-6.5),
                gun_depth_nominal_tolerance=self.config.getfloat('QC_Thresholds', 'gun_depth_nominal_tolerance', fallback=1.0),
                gun_depth_avg_tolerance=self.config.getfloat('QC_Thresholds', 'gun_depth_avg_tolerance', fallback=0.5),

                # Pressure thresholds
                gun_pressure_min=self.config.getfloat('QC_Thresholds', 'gun_pressure_min', fallback=1900),
                gun_pressure_max=self.config.getfloat('QC_Thresholds', 'gun_pressure_max', fallback=2100),
                gun_pressure_nominal=self.config.getfloat('QC_Thresholds', 'gun_pressure_nominal', fallback=2000),

                # Timing thresholds
                timing_warning=self.config.getfloat('QC_Thresholds', 'timing_warning', fallback=1.0),
                timing_error=self.config.getfloat('QC_Thresholds', 'timing_error', fallback=1.5),

                # Other limits
                crossline_limit=self.config.getfloat('QC_Thresholds', 'crossline_limit', fallback=10),
                radial_limit=self.config.getfloat('QC_Thresholds', 'radial_limit', fallback=10),
                sma_limit=self.config.getfloat('QC_Thresholds', 'sma_limit', fallback=3.0),
                shot_increment=self.config.getint('QC_Thresholds', 'shot_increment', fallback=2),
                consecutive_error_limit=self.config.getint('QC_Thresholds', 'consecutive_error_limit', fallback=25),

                # Advanced consecutive error detection
                consec_error_window_7=self.config.getint('QC_Thresholds', 'consec_error_window_7', fallback=7),
                consec_error_window_24=self.config.getint('QC_Thresholds', 'consec_error_window_24', fallback=24),
                consec_error_threshold_12_of_24=self.config.getint('QC_Thresholds', 'consec_error_threshold_12_of_24', fallback=12),
                consec_error_window_40=self.config.getint('QC_Thresholds', 'consec_error_window_40', fallback=40),
                consec_error_threshold_16_of_40=self.config.getint('QC_Thresholds', 'consec_error_threshold_16_of_40', fallback=16),
                consec_error_percent_total=self.config.getfloat('QC_Thresholds', 'consec_error_percent_total', fallback=3.0)
            )

            logging.info("Loaded thresholds from config:")
            for field in thresholds.__dataclass_fields__:
                value = getattr(thresholds, field)
                logging.info(f"  {field}: {value}")

            return thresholds

        except Exception as e:
            logging.error(f"Error loading thresholds from config: {str(e)}")
            raise

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all QC validations to DataFrame.

        Args:
            df: DataFrame with navigation and source data

        Returns:
            DataFrame with QC flag columns added
        """
        logging.info("Starting QC data validation...")

        # Initialize all flag columns
        flag_columns = [
            'sti_flag',
            'sub_array_sep_flag',
            'cos_sep_flag',
            'volume_flag',
            'gun_depth_flag',
            'gun_pressure_flag',
            'gun_timing_flag',
            'repeatability_flag',
            'sma_flag'
        ]
        for col in flag_columns:
            df[col] = 0

        try:
            # Run all validation checks
            df = self.validate_sti(df)
            df = self.validate_sub_array_separation(df)
            df = self.validate_cos_separation(df)
            df = self.validate_volume(df)
            df = self.validate_gun_depth(df)
            df = self.validate_gun_pressure(df)
            df = self.validate_gun_timing(df)
            df = self.validate_radial(df)
            df = self.validate_sma(df)

            # Ensure all flag columns are integer type
            for col in flag_columns:
                df[col] = df[col].astype(int)

            # Log flagged records
            for flag_col in flag_columns:
                flag_count = df[flag_col].sum()
                if flag_count > 0:
                    flagged = df[df[flag_col] > 0]
                    logging.warning(
                        f"{flag_count} records flagged for {flag_col}: "
                        f"Shot points: {flagged['shot_point'].tolist()}"
                    )

            logging.info("QC data validation completed")
            logging.debug(f"Flags set: {df[flag_columns].sum().to_dict()}")

        except Exception as e:
            logging.error(f"Error during QC validation: {str(e)}")
            raise

        return df

    def validate_sti(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate Shot Time Interval (STI)"""
        sti_col = 'Shot Time (s)  sec'
        if sti_col not in df.columns:
            logging.warning(f"Missing STI column: {sti_col}")
            return df

        df.loc[df[sti_col].fillna(0) < self.thresholds.sti_error, 'sti_flag'] = 2
        return df

    def validate_sub_array_separation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enhanced sub-array separation validation with two checks:
        1. Individual SP: Flag if outside sub_array_sep_min to sub_array_sep_max range
        2. Percentage check: Log if >15% of SP are flagged
        3. Sequence average: Check if average is within sub_array_sep_avg_min to sub_array_sep_avg_max
        """
        separation_columns = [
            'SOURCE SSTG1 towed by SST String 1 - 2 Crossline Separation All Shots ',
            'SOURCE SSTG2 towed by SST String 1 - 2 Crossline Separation All Shots ',
            'SOURCE SSTG3 towed by SST String 1 - 2 Crossline Separation All Shots '
        ]
        existing_sep_cols = [col for col in separation_columns if col in df.columns]

        if not existing_sep_cols:
            logging.warning("No sub-array separation columns found")
            return df

        logging.info(f"Using separation columns: {existing_sep_cols}")

        # Check 1: Individual SP violations (outside min-max range)
        for col in existing_sep_cols:
            df.loc[(df[col].fillna(0) < self.thresholds.sub_array_sep_min) |
                  (df[col].fillna(0) > self.thresholds.sub_array_sep_max), 'sub_array_sep_flag'] = 2

        # Check 2: Calculate percentage of violations
        violations_count = (df['sub_array_sep_flag'] == 2).sum()
        total_sp = len(df)
        percent_violations = (violations_count / total_sp * 100) if total_sp > 0 else 0

        logging.info(f"Sub-array separation violations: {violations_count}/{total_sp} ({percent_violations:.2f}%)")

        if percent_violations > self.thresholds.sub_array_sep_percent_threshold:
            logging.warning(f"Sub-array separation violations exceed {self.thresholds.sub_array_sep_percent_threshold}% threshold")

        # Check 3: Sequence average validation
        all_separations = []
        for col in existing_sep_cols:
            all_separations.extend(df[col].dropna().tolist())

        if all_separations:
            sequence_avg = np.mean(all_separations)
            logging.info(f"Sub-array separation sequence average: {sequence_avg:.2f}m")

            if sequence_avg < self.thresholds.sub_array_sep_avg_min or sequence_avg > self.thresholds.sub_array_sep_avg_max:
                logging.warning(
                    f"Sequence average sub-array separation {sequence_avg:.2f}m "
                    f"outside acceptable range ({self.thresholds.sub_array_sep_avg_min}-{self.thresholds.sub_array_sep_avg_max}m)"
                )

        return df

    def validate_cos_separation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate Center of Source (COS) separation"""
        cos_cols = {
            'dual': 'Gunarray301-Gunarray302 Position m',
            'triple': ['Gunarray301-Gunarray302 Position m', 'Gunarray302-Gunarray303 Position m']
        }

        if cos_cols['dual'] in df.columns:  # Dual source
            df.loc[(df[cos_cols['dual']].fillna(0) < self.thresholds.dual_cos_min) |
                  (df[cos_cols['dual']].fillna(0) > self.thresholds.dual_cos_max), 'cos_sep_flag'] = 2
        else:  # Check for triple source
            triple_cols = [col for col in cos_cols['triple'] if col in df.columns]
            if triple_cols:
                for col in triple_cols:
                    df.loc[(df[col].fillna(0) < self.thresholds.triple_cos_min) |
                          (df[col].fillna(0) > self.thresholds.triple_cos_max), 'cos_sep_flag'] = 2

        return df

    def validate_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate volume (exclude shot points with misfires)"""
        if 'VOLUME' not in df.columns:
            logging.warning("Missing VOLUME column")
            return df

        # Identify shot points with misfires (timing_value = 90)
        timing_cols = [col for col in df.columns if
                     col.startswith('String') and 'Cluster' in col and 'Gun' in col and
                     not col.endswith('-Depth') and not col.endswith('-Pressure')]

        # Create a boolean mask for shot points with misfires
        misfire_mask = pd.Series(False, index=df.index)
        for col in timing_cols:
            misfire_mask |= (df[col].fillna(0).abs() == 90)

        # Only flag volume issues for shot points WITHOUT misfires
        volume_condition = (df['VOLUME'].fillna(0) != self.thresholds.volume_nominal) & (~misfire_mask)
        df.loc[volume_condition, 'volume_flag'] = 2

        return df

    def validate_gun_depth(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate gun depths"""
        gun_depth_cols = [col for col in df.columns if col.startswith('SSTGM1') and 'DPT (P) Shot Event m' in col]

        if not gun_depth_cols:
            logging.warning("No gun depth columns found")
            return df

        df['average_gun_depth'] = df[gun_depth_cols].mean(axis=1)
        df.loc[(df['average_gun_depth'].fillna(0) < self.thresholds.gun_depth_min) |
              (df['average_gun_depth'].fillna(0) > self.thresholds.gun_depth_max), 'gun_depth_flag'] = 2

        return df

    def validate_gun_depth_sensors(self, df: pd.DataFrame) -> List[str]:
        """
        Validate individual gun depth sensors.
        Dynamically finds all gun depth sensor columns in the dataframe.
        Check if each sensor's average over entire sequence is within -7.5m to -6.5m.

        Returns:
            List of warning messages for sensors that failed QC
        """
        # Dynamically find all gun depth sensor columns
        # Pattern: SSTGM1D<number>_DPT (P) Shot Event m
        gun_depth_sensor_cols = [
            col for col in df.columns
            if col.startswith('SSTGM1D') and 'DPT (P) Shot Event m' in col
        ]

        if not gun_depth_sensor_cols:
            logging.warning("No gun depth sensor columns found in dataframe")
            return []

        logging.info(f"Found {len(gun_depth_sensor_cols)} gun depth sensors: {gun_depth_sensor_cols}")

        sensor_warnings = []

        for sensor_col in gun_depth_sensor_cols:
            # Calculate average for this sensor over entire sequence
            sensor_avg = df[sensor_col].mean()

            # Extract sensor number from column name (e.g., 'SSTGM1D1_DPT' -> '1')
            # Find the digit after 'D'
            try:
                import re
                match = re.search(r'SSTGM1D(\d+)_DPT', sensor_col)
                if match:
                    sensor_number = match.group(1)
                else:
                    sensor_number = sensor_col[7]  # Fallback to position 7
            except:
                sensor_number = sensor_col[7]  # Fallback

            # Check if outside acceptable range (-7.5m to -6.5m)
            if sensor_avg < self.thresholds.gun_depth_sensor_min or sensor_avg > self.thresholds.gun_depth_sensor_max:
                warning_msg = f"Gun Depth Sensor {sensor_number} avg = {abs(sensor_avg):.1f} meters"
                sensor_warnings.append(warning_msg)
                logging.warning(warning_msg)
            else:
                logging.info(f"Gun Depth Sensor {sensor_number} avg = {abs(sensor_avg):.1f} meters (OK)")

        return sensor_warnings

    def validate_gun_pressure(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate gun pressure based on point_code"""
        point_code_pressure_mapping = {
            'A1': ['SSTGM1P1_PRS (P) Shot Event  ', 'SSTGM1P2_PRS (P) Shot Event  '],
            'A2': ['SSTGM1P3_PRS (P) Shot Event  ', 'SSTGM1P4_PRS (P) Shot Event  '],
            'A3': ['SSTGM1P5_PRS (P) Shot Event  ', 'SSTGM1P6_PRS (P) Shot Event  ']
        }

        if 'point_code' in df.columns:
            # Process each unique point_code in the data
            for point_code, pressure_cols in point_code_pressure_mapping.items():
                point_code_rows = df['point_code'] == point_code

                if point_code_rows.any():
                    existing_cols = [col for col in pressure_cols if col in df.columns]
                    if existing_cols:
                        for col in existing_cols:
                            df.loc[
                                point_code_rows &
                                ((df[col].fillna(0) < self.thresholds.gun_pressure_min) |
                                 (df[col].fillna(0) > self.thresholds.gun_pressure_max)),
                                'gun_pressure_flag'
                            ] = 2
        else:
            # Fallback to default pressure check if point_code is not available
            pressure_cols = [col for col in df.columns if col.startswith('SSTGM1') and 'PRS (P) Shot Event' in col]
            for col in pressure_cols:
                df.loc[(df[col].fillna(0) < self.thresholds.gun_pressure_min) |
                      (df[col].fillna(0) > self.thresholds.gun_pressure_max), 'gun_pressure_flag'] = 2

        return df

    def validate_gun_timing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate gun timing"""
        logging.debug("Starting gun timing validation...")

        # Find gun timing columns
        base_pattern = r'^String_\d+-Cluster_\d+-Gun_\d+$'
        timing_cols = []
        for col in df.columns:
            if re.match(base_pattern, col) and not col.endswith('-Depth') and not col.endswith('-Pressure'):
                timing_cols.append(col)

        logging.info(f"Found {len(timing_cols)} gun timing columns")
        if len(timing_cols) == 0:
            logging.warning("No gun timing columns found matching the pattern")
            return df

        logging.info(f"Timing thresholds - Warning: {self.thresholds.timing_warning}, Error: {self.thresholds.timing_error}")

        for col in timing_cols:
            # Only set gun_timing_flag for ACTUAL timing issues
            # Exclude special codes: 63 (unknown), 61 (disabled), 90 (misfire)
            df.loc[(df[col] != 63) & (df[col] != 61) & (df[col] != 90) &
                  ((df[col] < -self.thresholds.timing_warning) |
                   (df[col] > self.thresholds.timing_warning)), 'gun_timing_flag'] = np.maximum(df['gun_timing_flag'], 1)
            df.loc[(df[col] != 63) & (df[col] != 61) & (df[col] != 90) &
                  ((df[col] < -self.thresholds.timing_error) |
                   (df[col] > self.thresholds.timing_error)), 'gun_timing_flag'] = 2

        # Log misfire and disabled gun counts
        misfire_count = sum((df[col].abs() == 90).sum() for col in timing_cols)
        disabled_count = sum((df[col].abs() == 61).sum() for col in timing_cols)
        logging.info(f"Total misfire (90) occurrences: {misfire_count}")
        logging.info(f"Total disabled gun (61) occurrences: {disabled_count}")

        # Debug logging
        warning_count = (df['gun_timing_flag'] == 1).sum()
        error_count = (df['gun_timing_flag'] == 2).sum()
        logging.info(f"Records with timing warnings: {warning_count}")
        logging.info(f"Records with timing errors: {error_count}")

        return df

    def validate_radial(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate radial offset"""
        radial_col = 'Radial (m)'
        if radial_col not in df.columns:
            logging.warning(f"Missing radial column: {radial_col}")
            return df

        df.loc[(df[radial_col].fillna(0) < -self.thresholds.radial_limit) |
               (df[radial_col].fillna(0) > self.thresholds.radial_limit), 'repeatability_flag'] = 1

        return df

    def validate_sma(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate Semi-Major Axis (SMA)"""
        sma_cols = [col for col in df.columns if 'Gunarray' in col and 'SMA m' in col]

        if not sma_cols:
            logging.warning("No SMA columns found")
            return df

        for col in sma_cols:
            df.loc[df[col].fillna(0) > self.thresholds.sma_limit, 'sma_flag'] = 2

        return df

    def check_consecutive_errors(self, df: pd.DataFrame) -> List[Tuple[int, int, int]]:
        """
        Check for consecutive errors.

        Args:
            df: DataFrame containing QC flag columns

        Returns:
            List of tuples containing (start, end, count) of consecutive errors
        """
        logging.info("Checking for consecutive errors...")

        try:
            flag_columns = [
                'sub_array_sep_flag',
                'cos_sep_flag',
                'volume_flag',
                'gun_depth_flag',
                'gun_pressure_flag',
                'gun_timing_flag',
                'repeatability_flag',
                'sma_flag'
            ]

            consecutive_errors = []

            for flag in flag_columns:
                if flag not in df.columns:
                    logging.warning(f"Flag column {flag} not found in dataframe")
                    continue

                flagged_records = df[df[flag].fillna(0) > 0]

                if not flagged_records.empty:
                    start = flagged_records['shot_point'].iloc[0]
                    end = flagged_records['shot_point'].iloc[-1]
                    count = len(flagged_records)

                    if count > self.thresholds.consecutive_error_limit:
                        consecutive_errors.append((start, end, count))

            return consecutive_errors

        except Exception as e:
            logging.error(f"Error checking consecutive errors: {str(e)}")
            raise

    def check_missing_shot_points(self, df: pd.DataFrame) -> List[int]:
        """
        Check for missing shot points by scanning for large gaps.

        Args:
            df: DataFrame containing shot_point column

        Returns:
            List of missing shot point numbers
        """
        if 'shot_point' not in df.columns:
            logging.warning("No shot_point column found in dataframe")
            return []

        shot_points = sorted(df['shot_point'].tolist())
        missed_sp = []

        for i in range(len(shot_points) - 1):
            current = shot_points[i]
            next_ = shot_points[i+1]

            # If there's a gap > 1, report missing shot points
            if next_ - current > 1:
                for missing in range(int(current) + 1, int(next_)):
                    missed_sp.append(missing)

        if missed_sp:
            logging.warning(f"Found {len(missed_sp)} missing shot points")

        return missed_sp

    def check_source_error_windows(self, df: pd.DataFrame) -> Dict[str, List]:
        """
        Check for consecutive source error patterns using sliding windows.
        A "source error" is any SP where volume_flag OR gun_depth_flag OR
        gun_pressure_flag OR gun_timing_flag OR sma_flag = 2.

        Checks:
        1. 7 consecutive SP with source errors
        2. 12 SP with errors in any 24 SP window
        3. 16 SP with errors in any 40 SP window
        4. More than 3% of total SP with source errors

        Returns:
            Dict with keys: 'consec_7', 'window_12_of_24', 'window_16_of_40', 'percent_3_total'
        """
        logging.info("Checking for source error patterns...")

        # Create combined source error flag
        source_error_flags = (
            (df['volume_flag'] == 2) |
            (df['gun_depth_flag'] == 2) |
            (df['gun_pressure_flag'] == 2) |
            (df['gun_timing_flag'] == 2) |
            (df['sma_flag'] == 2)
        ).astype(int)

        total_sp = len(df)
        error_sp_count = source_error_flags.sum()
        error_percent = (error_sp_count / total_sp * 100) if total_sp > 0 else 0

        logging.info(f"Total SP with source errors: {error_sp_count}/{total_sp} ({error_percent:.2f}%)")

        results = {
            'consec_7': [],
            'window_12_of_24': [],
            'window_16_of_40': [],
            'percent_3_total': error_percent >= self.thresholds.consec_error_percent_total
        }

        if 'shot_point' not in df.columns:
            logging.warning("No shot_point column found")
            return results

        shot_points = df['shot_point'].tolist()

        # Check 1: 7 consecutive SP with errors
        consec_count = 0
        consec_start = None
        for i, (sp, has_error) in enumerate(zip(shot_points, source_error_flags)):
            if has_error:
                if consec_count == 0:
                    consec_start = sp
                consec_count += 1
                if consec_count >= self.thresholds.consec_error_window_7:
                    # Found 7 consecutive errors
                    if not results['consec_7'] or results['consec_7'][-1][1] != sp:
                        results['consec_7'].append((consec_start, sp, consec_count))
            else:
                consec_count = 0
                consec_start = None

        # Check 2: 12 in 24 window (sliding window)
        window_size = self.thresholds.consec_error_window_24
        threshold = self.thresholds.consec_error_threshold_12_of_24
        results['window_12_of_24'] = self._sliding_window_check(
            source_error_flags, shot_points, window_size, threshold
        )

        # Check 3: 16 in 40 window (sliding window)
        window_size = self.thresholds.consec_error_window_40
        threshold = self.thresholds.consec_error_threshold_16_of_40
        results['window_16_of_40'] = self._sliding_window_check(
            source_error_flags, shot_points, window_size, threshold
        )

        # Log results
        if results['consec_7']:
            logging.warning(f"Found {len(results['consec_7'])} instances of 7+ consecutive source errors")
        if results['window_12_of_24']:
            logging.warning(f"Found {len(results['window_12_of_24'])} instances of 12+ errors in 24 SP window")
        if results['window_16_of_40']:
            logging.warning(f"Found {len(results['window_16_of_40'])} instances of 16+ errors in 40 SP window")
        if results['percent_3_total']:
            logging.warning(f"Source errors exceed 3% threshold: {error_percent:.2f}%")

        return results

    def _sliding_window_check(self, flags: pd.Series, shot_points: List,
                             window_size: int, threshold: int) -> List[Tuple[int, int]]:
        """
        Helper method: Check sliding window for error threshold violations.

        Args:
            flags: Series of boolean flags (1 = error, 0 = OK)
            shot_points: List of shot point numbers
            window_size: Size of the sliding window (e.g., 24 or 40)
            threshold: Number of errors required to trigger (e.g., 12 or 16)

        Returns:
            List of tuples (start_sp, end_sp) where threshold is exceeded
        """
        violations = []
        flags_list = flags.tolist()

        for i in range(len(flags_list) - window_size + 1):
            window_flags = flags_list[i:i+window_size]
            error_count = sum(window_flags)

            if error_count >= threshold:
                start_sp = shot_points[i]
                end_sp = shot_points[i+window_size-1]
                # Avoid duplicate consecutive windows
                if not violations or violations[-1][1] != end_sp:
                    violations.append((start_sp, end_sp))

        return violations
    def generate_line_log_report(self, df: pd.DataFrame, percentages: Dict,
                                 missed_sp: List[int]) -> Dict:
        """
        Generate comprehensive line log report with all QC findings.
        This method consolidates all log_data generation into the QC validator.

        Args:
            df: DataFrame with QC flags
            percentages: Dict with percentage calculations
            missed_sp: List of missing shot points

        Returns:
            Dict with all log_* keys formatted for line log
        """
        logging.info("Generating line log report...")

        try:
            flag_columns = [
                'sub_array_sep_flag',
                'cos_sep_flag',
                'volume_flag',
                'gun_depth_flag',
                'gun_pressure_flag',
                'gun_timing_flag',
                'repeatability_flag',
                'sma_flag'
            ]

            # Initialize log dictionary
            log_data = {}
            for flag in flag_columns:
                log_data[f"log_{flag}"] = []

            # Log shot points for each flag
            for flag in flag_columns:
                if flag not in df.columns:
                    logging.warning(f"Flag column {flag} not found in dataframe")
                    continue

                flagged_records = df[df[flag].fillna(0) > 0]

                for index, row in flagged_records.iterrows():
                    if flag == 'gun_timing_flag':
                        # Handle gun timing separately (warnings vs errors)
                        timing_error_level = row[flag]

                        timing_cols = [col for col in df.columns if
                                     col.startswith('String') and 'Cluster' in col and 'Gun' in col and
                                     not col.endswith('-Depth') and not col.endswith('-Pressure')]

                        if timing_error_level == 1:  # Warning
                            log_key = 'log_timing_warning'
                            min_threshold = 1.0
                            max_threshold = 1.5
                        elif timing_error_level == 2:  # Error
                            log_key = 'log_timing_error'
                            min_threshold = 1.5
                            max_threshold = float('inf')
                        else:
                            continue

                        matching_guns = []
                        for col in timing_cols:
                            timing_value = abs(row[col]) if pd.notna(row[col]) else 0
                            # Exclude special codes: 63, 61, 90
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

            # Check ALL rows for misfires and disabled guns
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

                    if timing_value == 90:  # Misfire
                        gun_parts = col.split('-')
                        if len(gun_parts) >= 3:
                            gun_info = f"{gun_parts[0].replace('_', ' ')} {gun_parts[1].replace('_', ' ')} {gun_parts[2].replace('_', ' ')}"
                            misfire_guns.append(gun_info)
                    elif timing_value == 61:  # Gun disabled
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

            # Log suspected autofires
            log_data['log_autofires'] = []
            if 'Raw: SST_GUN1 #Autofires' in df.columns:
                for index, row in df.iterrows():
                    if pd.notna(row['Raw: SST_GUN1 #Autofires']) and row['Raw: SST_GUN1 #Autofires'] > 0:
                        log_data['log_autofires'].append(row['shot_point'])
            else:
                logging.info("Column 'Raw: SST_GUN1 #Autofires' not found, skipping autofire check")

            # NEW: Add enhanced QC checks to log_data

            # 1. Sub-array separation percentage check
            violations_count = (df['sub_array_sep_flag'] == 2).sum()
            total_sp = len(df)
            percent_violations = (violations_count / total_sp * 100) if total_sp > 0 else 0

            if percent_violations > self.thresholds.sub_array_sep_percent_threshold:
                log_data['log_sub_array_sep_percent_violation'] = f"{percent_violations:.1f}% of SP outside 6.8-9.2m range (>{self.thresholds.sub_array_sep_percent_threshold}% threshold)"

            # 2. Sub-array separation sequence average check
            separation_columns = [
                'SOURCE SSTG1 towed by SST String 1 - 2 Crossline Separation All Shots ',
                'SOURCE SSTG2 towed by SST String 1 - 2 Crossline Separation All Shots ',
                'SOURCE SSTG3 towed by SST String 1 - 2 Crossline Separation All Shots '
            ]
            existing_sep_cols = [col for col in separation_columns if col in df.columns]
            if existing_sep_cols:
                all_separations = []
                for col in existing_sep_cols:
                    all_separations.extend(df[col].dropna().tolist())
                if all_separations:
                    sequence_avg = np.mean(all_separations)
                    if sequence_avg < self.thresholds.sub_array_sep_avg_min or sequence_avg > self.thresholds.sub_array_sep_avg_max:
                        log_data['log_sub_array_sep_avg_violation'] = f"Sequence average {sequence_avg:.2f}m outside acceptable range ({self.thresholds.sub_array_sep_avg_min}-{self.thresholds.sub_array_sep_avg_max}m)"

            # 3. Gun depth sensor validation
            gun_depth_sensor_warnings = self.validate_gun_depth_sensors(df)
            if gun_depth_sensor_warnings:
                log_data['log_gun_depth_sensor_violation'] = gun_depth_sensor_warnings

            # 4. Source error window checks
            source_error_results = self.check_source_error_windows(df)

            if source_error_results['consec_7']:
                log_data['log_consec_7_source_errors'] = [
                    f"SP {start}-{end} ({count} consecutive)" 
                    for start, end, count in source_error_results['consec_7']
                ]

            if source_error_results['window_12_of_24']:
                log_data['log_window_12_of_24_source_errors'] = [
                    f"SP {start}-{end}" 
                    for start, end in source_error_results['window_12_of_24']
                ]

            if source_error_results['window_16_of_40']:
                log_data['log_window_16_of_40_source_errors'] = [
                    f"SP {start}-{end}" 
                    for start, end in source_error_results['window_16_of_40']
                ]

            if source_error_results['percent_3_total']:
                error_sp_count = (
                    (df['volume_flag'] == 2) |
                    (df['gun_depth_flag'] == 2) |
                    (df['gun_pressure_flag'] == 2) |
                    (df['gun_timing_flag'] == 2) |
                    (df['sma_flag'] == 2)
                ).sum()
                error_percent = (error_sp_count / total_sp * 100) if total_sp > 0 else 0
                log_data['log_percent_3_total_source_errors'] = f"{error_percent:.2f}% of SP have source errors (>3% threshold)"

            logging.info(f"Generated line log report with {len(log_data)} entries")
            return log_data

        except Exception as e:
            logging.error(f"Error generating line log report: {str(e)}")
            raise
