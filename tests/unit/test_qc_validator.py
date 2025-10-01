"""
Unit tests for QC Validator Module

Tests threshold loading, validation logic, and flag generation for all QC checks.
"""

import pytest
import pandas as pd
import numpy as np
from qc_validator import QCValidator, QCThresholds
from config_manager import ConfigManager


@pytest.fixture
def qc_validator(config_file):
    """Create QCValidator instance with test config"""
    config = ConfigManager(config_file)
    config.load_config()
    return QCValidator(config)


@pytest.fixture
def sample_df():
    """Create sample DataFrame for testing"""
    return pd.DataFrame({
        'shot_point': [1001, 1003, 1005, 1007, 1009],
        'Shot Time (s)  sec': [6.175, 5.5, 6.3, 10.5, 5.0],
        'VOLUME': [3040, 3040, 2900, 3040, 3040],
        'Radial (m)': [2.0, 11.0, 3.0, 2.5, -12.0],
        'Gunarray301-Gunarray302 Position m': [37.5, 32.0, 38.0, 43.0, 37.5],
        'SOURCE SSTG1 towed by SST String 1 - 2 Crossline Separation All Shots ': [8.0, 6.0, 8.5, 10.0, 7.5],
        'SSTGM1D1_DPT (P) Shot Event m': [-7.0, -7.2, -8.5, -7.1, -5.5],
        'SSTGM1D2_DPT (P) Shot Event m': [-7.1, -7.0, -8.3, -7.2, -5.8],
        'SSTGM1P1_PRS (P) Shot Event  ': [2000, 1850, 2050, 2000, 2200],
        'SSTGM1P2_PRS (P) Shot Event  ': [2010, 1880, 2040, 2010, 2180],
        'String_1-Cluster_1-Gun_1': [0.5, 0.8, 1.2, 2.0, 0.3],
        'String_1-Cluster_1-Gun_2': [0.3, 90, 0.9, 1.8, 61],
        'Gunarray301 SMA m': [1.5, 2.0, 3.5, 1.8, 2.2],
        'point_code': ['A1', 'A1', 'A1', 'A1', 'A1']
    })


class TestQCThresholds:
    """Test QCThresholds dataclass"""

    def test_thresholds_loading(self, qc_validator):
        """Test that thresholds are loaded correctly"""
        thresholds = qc_validator.thresholds

        assert isinstance(thresholds, QCThresholds)
        assert thresholds.sti_error == 6.0
        assert thresholds.gun_depth_min == -8.0
        assert thresholds.gun_depth_max == -6.0
        assert thresholds.gun_pressure_min == 1900
        assert thresholds.gun_pressure_max == 2100
        assert thresholds.volume_nominal == 3040
        assert thresholds.crossline_limit == 10
        assert thresholds.radial_limit == 10
        assert thresholds.sma_limit == 3.0
        assert thresholds.consecutive_error_limit == 25


class TestSTIValidation:
    """Test Shot Time Interval validation"""

    def test_sti_error_flag(self, qc_validator, sample_df):
        """Test STI error flagging (< 6.0s)"""
        result = qc_validator.validate_sti(sample_df.copy())

        assert 'sti_flag' in result.columns
        # SP 1009 has STI = 5.0 (< 6.0, should be flagged)
        assert result.loc[result['shot_point'] == 1009, 'sti_flag'].iloc[0] == 2

    def test_sti_no_error(self, qc_validator, sample_df):
        """Test STI with no errors"""
        # Set all STI values > 6.0
        sample_df['Shot Time (s)  sec'] = [6.5, 7.0, 6.8, 10.0, 6.2]
        result = qc_validator.validate_sti(sample_df)

        assert result['sti_flag'].sum() == 0

    def test_sti_missing_column(self, qc_validator):
        """Test handling of missing STI column"""
        df = pd.DataFrame({'shot_point': [1001, 1003]})
        result = qc_validator.validate_sti(df)

        # Should return unchanged dataframe
        assert 'sti_flag' not in result.columns


class TestSubArraySeparation:
    """Test sub-array separation validation"""

    def test_sub_array_separation_violations(self, qc_validator, sample_df):
        """Test sub-array separation flagging"""
        result = qc_validator.validate_sub_array_separation(sample_df.copy())

        assert 'sub_array_sep_flag' in result.columns
        # SP 1003 has 6.0m (< 6.8m min), SP 1007 has 10.0m (> 9.2m max)
        flagged = result[result['sub_array_sep_flag'] == 2]
        assert len(flagged) == 2
        assert 1003 in flagged['shot_point'].values
        assert 1007 in flagged['shot_point'].values

    def test_sub_array_separation_ok(self, qc_validator, sample_df):
        """Test sub-array separation with all values in range"""
        sample_df['SOURCE SSTG1 towed by SST String 1 - 2 Crossline Separation All Shots '] = [7.5, 8.0, 7.8, 8.2, 7.9]
        result = qc_validator.validate_sub_array_separation(sample_df)

        assert result['sub_array_sep_flag'].sum() == 0


class TestCOSSeparation:
    """Test Center of Source (COS) separation validation"""

    def test_cos_dual_source_violations(self, qc_validator, sample_df):
        """Test COS dual source flagging"""
        result = qc_validator.validate_cos_separation(sample_df.copy())

        assert 'cos_sep_flag' in result.columns
        # SP 1003 has 32.0 (< 33.75 min), SP 1007 has 43.0 (> 41.25 max)
        flagged = result[result['cos_sep_flag'] == 2]
        assert len(flagged) == 2

    def test_cos_dual_source_ok(self, qc_validator, sample_df):
        """Test COS with all values in range"""
        sample_df['Gunarray301-Gunarray302 Position m'] = [37.5, 38.0, 37.8, 38.5, 37.2]
        result = qc_validator.validate_cos_separation(sample_df)

        assert result['cos_sep_flag'].sum() == 0


class TestVolumeValidation:
    """Test volume validation"""

    def test_volume_violations(self, qc_validator, sample_df):
        """Test volume flagging (excluding misfires)"""
        result = qc_validator.validate_volume(sample_df.copy())

        assert 'volume_flag' in result.columns
        # SP 1005 has volume 2900 (not 3040), and no misfire
        flagged = result[result['volume_flag'] == 2]
        assert 1005 in flagged['shot_point'].values

    def test_volume_misfire_excluded(self, qc_validator):
        """Test that SP with misfires are not flagged for volume"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003],
            'VOLUME': [2900, 2900],
            'String_1-Cluster_1-Gun_1': [0.5, 90],  # Second SP has misfire
        })
        result = qc_validator.validate_volume(df)

        # Only first SP should be flagged (no misfire)
        assert (result['volume_flag'] == 2).sum() == 1


class TestGunDepthValidation:
    """Test gun depth validation"""

    def test_gun_depth_violations(self, qc_validator, sample_df):
        """Test gun depth flagging"""
        result = qc_validator.validate_gun_depth(sample_df.copy())

        assert 'gun_depth_flag' in result.columns
        assert 'average_gun_depth' in result.columns

        # SP 1005 has avg depth ~-8.4m (< -8.0 min)
        # SP 1009 has avg depth ~-5.65m (> -6.0 max)
        flagged = result[result['gun_depth_flag'] == 2]
        assert len(flagged) == 2

    def test_gun_depth_sensors_validation(self, qc_validator, sample_df):
        """Test individual gun depth sensor validation"""
        warnings = qc_validator.validate_gun_depth_sensors(sample_df)

        # With the sample data, sensors might be out of -7.5 to -6.5 range
        assert isinstance(warnings, list)


class TestGunPressureValidation:
    """Test gun pressure validation"""

    def test_gun_pressure_violations(self, qc_validator, sample_df):
        """Test gun pressure flagging by point_code"""
        result = qc_validator.validate_gun_pressure(sample_df.copy())

        assert 'gun_pressure_flag' in result.columns
        # SP 1003 has P1=1850 (< 1900 min)
        # SP 1009 has P1=2200 (> 2100 max)
        flagged = result[result['gun_pressure_flag'] == 2]
        assert len(flagged) >= 2

    def test_gun_pressure_fallback(self, qc_validator):
        """Test gun pressure validation without point_code"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003],
            'SSTGM1P1_PRS (P) Shot Event  ': [2000, 1800],
        })
        result = qc_validator.validate_gun_pressure(df)

        # Second SP should be flagged (1800 < 1900)
        assert (result['gun_pressure_flag'] == 2).sum() == 1


class TestGunTimingValidation:
    """Test gun timing validation"""

    def test_gun_timing_warnings_and_errors(self, qc_validator, sample_df):
        """Test gun timing flagging (warnings and errors)"""
        df = sample_df.copy()
        df['gun_timing_flag'] = 0  # Initialize flag column
        result = qc_validator.validate_gun_timing(df)

        assert 'gun_timing_flag' in result.columns
        # SP 1005 has Gun_1 = 1.2ms (warning: 1.0 < x <= 1.5)
        # SP 1007 has Gun_1 = 2.0ms (error: > 1.5)
        warnings = (result['gun_timing_flag'] == 1).sum()
        errors = (result['gun_timing_flag'] == 2).sum()
        assert warnings >= 1
        assert errors >= 1

    def test_gun_timing_excludes_special_codes(self, qc_validator):
        """Test that special codes (63, 61, 90) don't set timing flags"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005, 1007],
            'String_1-Cluster_1-Gun_1': [63, 61, 90, 0.5],
            'gun_timing_flag': [0, 0, 0, 0]
        })
        result = qc_validator.validate_gun_timing(df)

        # Only last SP should have timing flag (0.5ms is OK)
        assert result['gun_timing_flag'].sum() == 0


class TestRadialValidation:
    """Test radial/crossline validation"""

    def test_radial_violations(self, qc_validator, sample_df):
        """Test radial flagging"""
        result = qc_validator.validate_radial(sample_df.copy())

        assert 'repeatability_flag' in result.columns
        # SP 1003 has 11.0m (> 10m limit), SP 1009 has -12.0m (< -10m limit)
        flagged = result[result['repeatability_flag'] == 1]
        assert len(flagged) == 2


class TestSMAValidation:
    """Test Semi-Major Axis (SMA) validation"""

    def test_sma_violations(self, qc_validator, sample_df):
        """Test SMA flagging"""
        result = qc_validator.validate_sma(sample_df.copy())

        assert 'sma_flag' in result.columns
        # SP 1005 has SMA 3.5m (> 3.0m limit)
        flagged = result[result['sma_flag'] == 2]
        assert len(flagged) == 1
        assert 1005 in flagged['shot_point'].values


class TestValidateData:
    """Test complete validation workflow"""

    def test_validate_data_complete(self, qc_validator, sample_df):
        """Test that validate_data runs all checks"""
        result = qc_validator.validate_data(sample_df.copy())

        # Check that all flag columns are created
        expected_flags = [
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

        for flag in expected_flags:
            assert flag in result.columns
            assert result[flag].dtype in [int, 'Int64']

    def test_validate_data_preserves_columns(self, qc_validator, sample_df):
        """Test that original columns are preserved"""
        original_cols = sample_df.columns.tolist()
        result = qc_validator.validate_data(sample_df.copy())

        for col in original_cols:
            assert col in result.columns


class TestConsecutiveErrors:
    """Test consecutive error detection"""

    def test_check_consecutive_errors(self, qc_validator):
        """Test consecutive error detection"""
        df = pd.DataFrame({
            'shot_point': list(range(1001, 1051)),  # 50 shot points
            'volume_flag': [2] * 30 + [0] * 20,  # 30 consecutive volume errors
            'gun_depth_flag': [0] * 50,
            'gun_pressure_flag': [0] * 50,
            'gun_timing_flag': [0] * 50,
            'sub_array_sep_flag': [0] * 50,
            'cos_sep_flag': [0] * 50,
            'repeatability_flag': [0] * 50,
            'sma_flag': [0] * 50,
        })

        consecutive_errors = qc_validator.check_consecutive_errors(df)

        # Should detect consecutive errors (> 25 limit)
        assert len(consecutive_errors) > 0
        assert consecutive_errors[0][2] == 30  # Count of consecutive errors

    def test_check_consecutive_errors_no_violations(self, qc_validator):
        """Test consecutive error detection with no violations"""
        df = pd.DataFrame({
            'shot_point': list(range(1001, 1021)),  # 20 shot points
            'volume_flag': [0] * 20,
            'gun_depth_flag': [0] * 20,
            'gun_pressure_flag': [0] * 20,
            'gun_timing_flag': [0] * 20,
            'sub_array_sep_flag': [0] * 20,
            'cos_sep_flag': [0] * 20,
            'repeatability_flag': [0] * 20,
            'sma_flag': [0] * 20,
        })

        consecutive_errors = qc_validator.check_consecutive_errors(df)
        assert len(consecutive_errors) == 0


class TestMissingShotPoints:
    """Test missing shot point detection"""

    def test_check_missing_shot_points(self, qc_validator):
        """Test missing shot point detection"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005, 1009, 1011]  # Missing 1007
        })

        missed_sp = qc_validator.check_missing_shot_points(df)

        # Should detect missing shot points
        assert len(missed_sp) > 0
        assert 1002 in missed_sp  # 1001 -> 1003 (missing 1002)
        assert 1004 in missed_sp  # 1003 -> 1005 (missing 1004)
        assert 1006 in missed_sp  # 1005 -> 1009 (missing 1006, 1007, 1008)
        assert 1007 in missed_sp
        assert 1008 in missed_sp
        assert 1010 in missed_sp  # 1009 -> 1011 (missing 1010)

    def test_check_missing_shot_points_none(self, qc_validator):
        """Test with no missing shot points"""
        df = pd.DataFrame({
            'shot_point': [1001, 1002, 1003, 1004, 1005]  # Consecutive sequence (gap of 1)
        })

        missed_sp = qc_validator.check_missing_shot_points(df)
        assert len(missed_sp) == 0


class TestSourceErrorWindows:
    """Test source error window detection"""

    def test_check_source_error_windows_7_consecutive(self, qc_validator):
        """Test detection of 7 consecutive source errors"""
        df = pd.DataFrame({
            'shot_point': list(range(1001, 1021)),
            'volume_flag': [2] * 8 + [0] * 12,  # 8 consecutive errors
            'gun_depth_flag': [0] * 20,
            'gun_pressure_flag': [0] * 20,
            'gun_timing_flag': [0] * 20,
            'sma_flag': [0] * 20,
        })

        results = qc_validator.check_source_error_windows(df)

        assert results['consec_7']
        assert len(results['consec_7']) >= 1

    def test_check_source_error_windows_12_of_24(self, qc_validator):
        """Test detection of 12 errors in 24 SP window"""
        # Create pattern: 12 errors scattered in first 24 SP
        flags = [2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0] + [0] * 16
        df = pd.DataFrame({
            'shot_point': list(range(1001, 1041)),
            'volume_flag': flags,
            'gun_depth_flag': [0] * 40,
            'gun_pressure_flag': [0] * 40,
            'gun_timing_flag': [0] * 40,
            'sma_flag': [0] * 40,
        })

        results = qc_validator.check_source_error_windows(df)

        assert results['window_12_of_24']

    def test_check_source_error_windows_percent_3(self, qc_validator):
        """Test detection of >3% total source errors"""
        df = pd.DataFrame({
            'shot_point': list(range(1001, 1101)),  # 100 SP
            'volume_flag': [2] * 5 + [0] * 95,  # 5% errors (> 3% threshold)
            'gun_depth_flag': [0] * 100,
            'gun_pressure_flag': [0] * 100,
            'gun_timing_flag': [0] * 100,
            'sma_flag': [0] * 100,
        })

        results = qc_validator.check_source_error_windows(df)

        assert results['percent_3_total']


class TestLineLogReport:
    """Test line log report generation"""

    def test_generate_line_log_report(self, qc_validator, sample_df):
        """Test line log report generation"""
        # Run validation first
        validated_df = qc_validator.validate_data(sample_df.copy())

        percentages = {
            'sti_percent': 5.0,
            'volume_percent': 10.0,
        }
        missed_sp = [1002, 1004]

        log_data = qc_validator.generate_line_log_report(validated_df, percentages, missed_sp)

        # Check that log_data contains expected keys
        assert isinstance(log_data, dict)
        assert 'log_volume_flag' in log_data
        assert 'log_gun_depth_flag' in log_data

        # Check that flagged shot points are logged
        assert len(log_data['log_volume_flag']) > 0

    def test_generate_line_log_report_with_timing(self, qc_validator):
        """Test line log report with timing warnings/errors"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005],
            'String_1-Cluster_1-Gun_1': [1.2, 2.0, 0.5],  # Warning, error, OK
            'String_1-Cluster_1-Gun_2': [0.3, 0.5, 0.4],
        })

        # Initialize flags
        df['sti_flag'] = 0
        df['sub_array_sep_flag'] = 0
        df['cos_sep_flag'] = 0
        df['volume_flag'] = 0
        df['gun_depth_flag'] = 0
        df['gun_pressure_flag'] = 0
        df['gun_timing_flag'] = 0
        df['repeatability_flag'] = 0
        df['sma_flag'] = 0

        # Run timing validation
        validated_df = qc_validator.validate_gun_timing(df.copy())

        log_data = qc_validator.generate_line_log_report(validated_df, {}, [])

        # Should have timing warning and/or error logs
        assert 'log_timing_warning' in log_data or 'log_timing_error' in log_data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
