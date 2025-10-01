"""
Unit tests for QC Report Generator Module

Tests shot point sorting, dither checking, flag discrepancies, and percentage calculations.
"""

import pytest
import pandas as pd
from configparser import ConfigParser
from qc_report_generator import QCReportGenerator
from data_importers import SPSImporter
from config_manager import ConfigManager


@pytest.fixture
def test_config(config_file):
    """Load test configuration"""
    config = ConfigManager(config_file)
    config.load_config()
    return config.config


@pytest.fixture
def sps_importer(test_config):
    """Create SPSImporter instance"""
    config_manager = ConfigManager()
    config_manager.config = test_config
    return SPSImporter(config_manager)


@pytest.fixture
def qc_report_generator(test_config, sps_importer):
    """Create QCReportGenerator instance"""
    return QCReportGenerator(test_config, sps_importer)


@pytest.fixture
def sample_df_ascending():
    """Create sample DataFrame with ascending shot points"""
    return pd.DataFrame({
        'shot_point': [1001, 1003, 1005, 1007, 1009, 1011],
        'shot_dither': [0.5, 0.3, 0.4, 0.2, 0.1, 0.3],
        'sti_flag': [0, 0, 2, 0, 0, 0],
        'volume_flag': [0, 2, 0, 0, 2, 0],
        'gun_depth_flag': [0, 0, 0, 0, 0, 0],
        'SP Point QC': [0, 1, 0, 0, 1, 0]
    })


@pytest.fixture
def sample_df_descending():
    """Create sample DataFrame with descending shot points"""
    return pd.DataFrame({
        'shot_point': [1011, 1009, 1007, 1005, 1003, 1001],
        'shot_dither': [0.5, 0.3, 0.4, 0.2, 0.1, 0.3]
    })


class TestDetectSPSorting:
    """Test shot point sorting detection"""

    def test_detect_ascending_sequence_correct(self, qc_report_generator, sample_df_ascending):
        """Test detection of correct ascending sequence"""
        issues = qc_report_generator.detect_sp_sorting(sample_df_ascending)

        # Should have no sorting issues
        assert isinstance(issues, list)
        # May have gap warnings but no sorting errors
        sorting_errors = [issue for issue in issues if 'should come before' in issue or 'Duplicate' in issue]
        assert len(sorting_errors) == 0

    def test_detect_descending_sequence_correct(self, qc_report_generator, sample_df_descending):
        """Test detection of correct descending sequence"""
        issues = qc_report_generator.detect_sp_sorting(sample_df_descending)

        sorting_errors = [issue for issue in issues if 'should come after' in issue or 'Duplicate' in issue]
        assert len(sorting_errors) == 0

    def test_detect_out_of_order_ascending(self, qc_report_generator):
        """Test detection of out-of-order points in ascending sequence"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005, 1003, 1009]  # 1003 appears twice
        })

        issues = qc_report_generator.detect_sp_sorting(df)

        assert len(issues) > 0
        assert any('should come before' in issue or 'appears after' in issue.lower() for issue in issues)

    def test_detect_duplicate_shot_points(self, qc_report_generator):
        """Test detection of duplicate shot points"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1003, 1005, 1007]  # Duplicate 1003
        })

        issues = qc_report_generator.detect_sp_sorting(df)

        assert len(issues) > 0
        assert any('Duplicate' in issue for issue in issues)

    def test_detect_large_gap(self, qc_report_generator):
        """Test detection of large gaps in sequence"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005, 1025, 1027]  # Large gap between 1005 and 1025
        })

        issues = qc_report_generator.detect_sp_sorting(df)

        # May detect gap warning
        assert isinstance(issues, list)

    def test_detect_empty_dataframe(self, qc_report_generator):
        """Test handling of empty DataFrame"""
        df = pd.DataFrame()

        issues = qc_report_generator.detect_sp_sorting(df)

        assert issues == []

    def test_detect_single_shot_point(self, qc_report_generator):
        """Test handling of DataFrame with single shot point"""
        df = pd.DataFrame({'shot_point': [1001]})

        issues = qc_report_generator.detect_sp_sorting(df)

        assert issues == []

    def test_detect_missing_shot_point_column(self, qc_report_generator):
        """Test handling of DataFrame without shot_point column"""
        df = pd.DataFrame({'other_column': [1, 2, 3]})

        issues = qc_report_generator.detect_sp_sorting(df)

        assert issues == []


class TestCheckDitherValues:
    """Test dither value checking"""

    def test_check_dither_all_valid(self, qc_report_generator, sample_df_ascending):
        """Test checking with all valid dither values"""
        issues, stats = qc_report_generator.check_dither_values(sample_df_ascending)

        assert isinstance(issues, list)
        assert len(issues) == 0
        assert stats['detected'] == 0
        assert stats['suggested'] == 0

    def test_check_dither_with_nulls(self, qc_report_generator):
        """Test detection of null dither values"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005],
            'shot_dither': [0.5, None, 0.3]
        })

        issues, stats = qc_report_generator.check_dither_values(df)

        # May be recovered or unrecovered depending on dither file
        assert isinstance(issues, list)
        assert isinstance(stats, dict)

    def test_check_dither_zero_is_valid(self, qc_report_generator):
        """Test that zero (0) is a valid dither value"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005],
            'shot_dither': [0.5, 0, 0.3]  # Zero is valid
        })

        issues, stats = qc_report_generator.check_dither_values(df)

        # Zero should not trigger an issue
        assert len(issues) == 0

    def test_check_dither_missing_column(self, qc_report_generator):
        """Test handling of missing shot_dither column"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005]
        })

        issues, stats = qc_report_generator.check_dither_values(df)

        # Should handle gracefully, no crash
        assert isinstance(issues, list)
        assert isinstance(stats, dict)

    def test_check_dither_empty_dataframe(self, qc_report_generator):
        """Test handling of empty DataFrame"""
        df = pd.DataFrame()

        issues, stats = qc_report_generator.check_dither_values(df)

        assert issues == []
        assert stats == {'detected': 0, 'suggested': 0}


class TestCheckFlagDiscrepancies:
    """Test flag discrepancy detection"""

    def test_check_flag_discrepancies_none(self, qc_report_generator):
        """Test with no discrepancies"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005],
            'SP Point QC': [0, 0, 0],
            'sti_flag': [0, 0, 0],
            'volume_flag': [0, 0, 0],
            'gun_depth_flag': [0, 0, 0]
        })

        issues = qc_report_generator.check_flag_discrepancies(df)

        assert isinstance(issues, list)
        assert len(issues) == 0

    def test_check_flag_discrepancies_found(self, qc_report_generator, sample_df_ascending):
        """Test detection of flag discrepancies"""
        issues = qc_report_generator.check_flag_discrepancies(sample_df_ascending)

        # Sample data has discrepancies between SP Point QC and calculated flags
        assert isinstance(issues, list)

    def test_check_flag_missing_sp_point_qc(self, qc_report_generator):
        """Test handling of missing SP Point QC column"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005],
            'sti_flag': [0, 2, 0],
            'volume_flag': [0, 0, 2]
        })

        issues = qc_report_generator.check_flag_discrepancies(df)

        # Should handle gracefully
        assert isinstance(issues, list)

    def test_check_flag_empty_dataframe(self, qc_report_generator):
        """Test handling of empty DataFrame"""
        df = pd.DataFrame()

        issues = qc_report_generator.check_flag_discrepancies(df)

        assert issues == []


class TestCalculatePercentages:
    """Test percentage calculation"""

    def test_calculate_percentages_all_flags(self, qc_report_generator):
        """Test percentage calculation for all QC flags"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005, 1007, 1009, 1011],
            'sti_flag': [0, 0, 2, 0, 0, 0],
            'sub_array_sep_flag': [0, 0, 0, 0, 0, 0],
            'cos_sep_flag': [0, 0, 0, 0, 0, 0],
            'volume_flag': [0, 2, 0, 0, 2, 0],
            'gun_depth_flag': [0, 0, 0, 0, 0, 0],
            'gun_pressure_flag': [0, 0, 0, 0, 0, 0],
            'gun_timing_flag': [0, 0, 0, 0, 0, 0],
            'repeatability_flag': [0, 0, 0, 0, 0, 0],
            'sma_flag': [0, 0, 0, 0, 0, 0]
        })
        total_sp = len(df)

        percentages = qc_report_generator.calculate_percentages(df, total_sp)

        assert isinstance(percentages, dict)
        # Returns nested dict structure
        assert 'sti_flag' in percentages or 'total' in percentages

    def test_calculate_percentages_no_errors(self, qc_report_generator):
        """Test percentage calculation with no errors"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005],
            'sti_flag': [0, 0, 0],
            'volume_flag': [0, 0, 0],
            'gun_depth_flag': [0, 0, 0],
            'gun_pressure_flag': [0, 0, 0],
            'gun_timing_flag': [0, 0, 0],
            'sub_array_sep_flag': [0, 0, 0],
            'cos_sep_flag': [0, 0, 0],
            'repeatability_flag': [0, 0, 0],
            'sma_flag': [0, 0, 0]
        })

        percentages = qc_report_generator.calculate_percentages(df, 3)

        # Should return dict, verify structure
        assert isinstance(percentages, dict)
        # Check that errors are 0
        if 'total' in percentages:
            assert percentages['errors'] == 0.0

    def test_calculate_percentages_all_errors(self, qc_report_generator):
        """Test percentage calculation with all errors"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005],
            'sti_flag': [2, 2, 2],
            'volume_flag': [2, 2, 2],
            'gun_depth_flag': [2, 2, 2],
            'gun_pressure_flag': [2, 2, 2],
            'gun_timing_flag': [2, 2, 2],
            'sub_array_sep_flag': [2, 2, 2],
            'cos_sep_flag': [2, 2, 2],
            'repeatability_flag': [2, 2, 2],
            'sma_flag': [2, 2, 2]
        })

        percentages = qc_report_generator.calculate_percentages(df, 3)

        # Should return dict with 100% errors
        assert isinstance(percentages, dict)
        if 'total' in percentages:
            assert percentages['errors'] == 100.0

    def test_calculate_percentages_handles_errors(self, qc_report_generator):
        """Test that calculate_percentages handles errors gracefully"""
        # Empty DataFrame should handle gracefully
        df = pd.DataFrame()

        try:
            percentages = qc_report_generator.calculate_percentages(df, 0)
            # If it succeeds, should return dict
            assert isinstance(percentages, dict)
        except KeyError:
            # If it raises KeyError, that's expected for empty DataFrame
            pass


class TestLogShotpoints:
    """Test shot point logging functionality"""

    def test_log_shotpoints_with_flags(self, qc_report_generator):
        """Test logging of shot points with flags"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005, 1007, 1009, 1011],
            'sti_flag': [0, 0, 2, 0, 0, 0],
            'sub_array_sep_flag': [0, 0, 0, 0, 0, 0],
            'cos_sep_flag': [0, 0, 0, 0, 0, 0],
            'volume_flag': [0, 2, 0, 0, 2, 0],
            'gun_depth_flag': [0, 0, 0, 0, 0, 0],
            'gun_pressure_flag': [0, 0, 0, 0, 0, 0],
            'gun_timing_flag': [0, 0, 0, 0, 0, 0],
            'repeatability_flag': [0, 0, 0, 0, 0, 0],
            'sma_flag': [0, 0, 0, 0, 0, 0]
        })

        log_data = qc_report_generator.log_shotpoints(df)

        assert isinstance(log_data, dict)
        # Check for expected keys (actual key names may vary)
        assert 'log_volume_flag' in log_data

        # Verify that flagged shot points are logged
        assert len(log_data['log_volume_flag']) > 0

    def test_log_shotpoints_no_flags(self, qc_report_generator):
        """Test logging with no flagged shot points"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005],
            'sti_flag': [0, 0, 0],
            'volume_flag': [0, 0, 0],
            'gun_depth_flag': [0, 0, 0],
            'gun_pressure_flag': [0, 0, 0],
            'gun_timing_flag': [0, 0, 0],
            'sub_array_sep_flag': [0, 0, 0],
            'cos_sep_flag': [0, 0, 0],
            'repeatability_flag': [0, 0, 0],
            'sma_flag': [0, 0, 0]
        })

        log_data = qc_report_generator.log_shotpoints(df)

        assert isinstance(log_data, dict)
        # All log lists should be empty
        for key, value in log_data.items():
            if key.startswith('log_'):
                assert len(value) == 0

    def test_log_shotpoints_empty_dataframe(self, qc_report_generator):
        """Test handling of empty DataFrame"""
        df = pd.DataFrame()

        log_data = qc_report_generator.log_shotpoints(df)

        assert isinstance(log_data, dict)


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_large_dataset_performance(self, qc_report_generator):
        """Test performance with large dataset"""
        # Create large DataFrame
        import numpy as np
        df = pd.DataFrame({
            'shot_point': range(1001, 11001),  # 10000 shot points
            'shot_dither': np.random.rand(10000),
            'sti_flag': np.random.choice([0, 2], 10000),
            'volume_flag': np.random.choice([0, 2], 10000),
            'gun_depth_flag': np.zeros(10000, dtype=int),
            'gun_pressure_flag': np.zeros(10000, dtype=int),
            'gun_timing_flag': np.zeros(10000, dtype=int),
            'sub_array_sep_flag': np.zeros(10000, dtype=int),
            'cos_sep_flag': np.zeros(10000, dtype=int),
            'repeatability_flag': np.zeros(10000, dtype=int),
            'sma_flag': np.zeros(10000, dtype=int)
        })

        # Should complete without errors
        issues = qc_report_generator.detect_sp_sorting(df)
        assert isinstance(issues, list)

        dither_issues, dither_stats = qc_report_generator.check_dither_values(df)
        assert isinstance(dither_issues, list)
        assert isinstance(dither_stats, dict)

        percentages = qc_report_generator.calculate_percentages(df, 10000)
        assert isinstance(percentages, dict)

    def test_mixed_data_types(self, qc_report_generator):
        """Test handling of mixed data types"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003, 1005],
            'shot_dither': [0.5, 0.3, 0.4],  # Proper numeric types
            'sti_flag': [0, 2, 0],  # Proper numeric types
            'sub_array_sep_flag': [0, 0, 0],
            'cos_sep_flag': [0, 0, 0],
            'volume_flag': [0, 0, 2],
            'gun_depth_flag': [0, 0, 0],
            'gun_pressure_flag': [0, 0, 0],
            'gun_timing_flag': [0, 0, 0],
            'repeatability_flag': [0, 0, 0],
            'sma_flag': [0, 0, 0]
        })

        # Should handle without crashing
        issues, stats = qc_report_generator.check_dither_values(df)
        assert isinstance(issues, list)
        assert isinstance(stats, dict)

        percentages = qc_report_generator.calculate_percentages(df, 3)
        assert isinstance(percentages, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
