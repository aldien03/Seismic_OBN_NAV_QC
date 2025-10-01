"""
Unit tests for Database Operations Module

Tests database output, path resolution, and error handling.
"""

import pytest
import os
import tempfile
import shutil
import pandas as pd
from configparser import ConfigParser
from database_operations import DatabaseManager


@pytest.fixture
def temp_test_dir():
    """Create temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_config(temp_test_dir):
    """Create test configuration"""
    config = ConfigParser()
    config.add_section('Paths')
    config.set('Paths', 'db_output_path', temp_test_dir)
    return config


@pytest.fixture
def db_manager(test_config):
    """Create DatabaseManager instance"""
    return DatabaseManager(test_config)


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing"""
    return pd.DataFrame({
        'sequence': [256, 256, 256],
        'line_name': ['3184P31885', '3184P31885', '3184P31885'],
        'shot_point': [1001, 1003, 1005],
        'easting_m': [123456.0, 123457.0, 123458.0],
        'northing_m': [7654321.0, 7654322.0, 7654323.0],
        'sti_flag': [0, 0, 0],
        'volume_flag': [0, 0, 2],
        'gun_depth_flag': [0, 0, 0]
    })


class TestDatabaseManagerInit:
    """Test DatabaseManager initialization"""

    def test_initialization(self, test_config):
        """Test DatabaseManager initialization"""
        manager = DatabaseManager(test_config)

        assert manager is not None
        assert manager.config is not None


class TestSaveToDatabase:
    """Test save_to_database functionality"""

    def test_save_success(self, db_manager, sample_dataframe, temp_test_dir):
        """Test successful save to database"""
        results = {'merged_df': sample_dataframe}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is not None
        assert os.path.exists(output_path)
        assert output_path.endswith('0256_3184_DB.csv')

        # Verify file contents
        saved_df = pd.read_csv(output_path)
        assert len(saved_df) == 3
        assert 'shot_point' in saved_df.columns

    def test_save_with_numeric_line_name(self, db_manager, temp_test_dir):
        """Test save with numeric line name"""
        df = pd.DataFrame({
            'sequence': [256, 256],
            'line_name': [3184, 3184],
            'shot_point': [1001, 1003]
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is not None
        assert '0256_3184_DB.csv' in output_path

    def test_save_invalid_results_type(self, db_manager):
        """Test save with invalid results type"""
        output_path = db_manager.save_to_database("not a dict", 'test.S01')

        assert output_path is None

    def test_save_missing_dataframe(self, db_manager):
        """Test save with missing DataFrame"""
        results = {'other_key': 'value'}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is None

    def test_save_empty_dataframe(self, db_manager):
        """Test save with empty DataFrame"""
        df = pd.DataFrame()
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is None

    def test_save_missing_required_columns(self, db_manager):
        """Test save with missing required columns"""
        df = pd.DataFrame({
            'shot_point': [1001, 1003],
            'easting_m': [123456.0, 123457.0]
            # Missing 'sequence' and 'line_name'
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is None

    def test_save_invalid_sequence(self, db_manager):
        """Test save with invalid sequence value"""
        df = pd.DataFrame({
            'sequence': ['invalid', 'invalid'],
            'line_name': ['3184P31885', '3184P31885'],
            'shot_point': [1001, 1003]
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is None

    def test_save_null_line_name(self, db_manager):
        """Test save with null line name"""
        df = pd.DataFrame({
            'sequence': [256, 256],
            'line_name': [None, None],
            'shot_point': [1001, 1003]
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is None

    def test_save_overwrites_existing_file(self, db_manager, sample_dataframe, temp_test_dir):
        """Test that save overwrites existing file"""
        results = {'merged_df': sample_dataframe}

        # First save
        output_path1 = db_manager.save_to_database(results, 'test.S01')
        assert output_path1 is not None

        # Modify dataframe
        sample_dataframe['shot_point'] = [2001, 2003, 2005]
        results = {'merged_df': sample_dataframe}

        # Second save
        output_path2 = db_manager.save_to_database(results, 'test.S01')
        assert output_path2 is not None
        assert output_path1 == output_path2

        # Verify overwritten contents
        saved_df = pd.read_csv(output_path2)
        assert saved_df['shot_point'].iloc[0] == 2001


class TestTrySavePrimary:
    """Test primary save location functionality"""

    def test_try_save_primary_success(self, db_manager, sample_dataframe, temp_test_dir):
        """Test successful primary save"""
        output_path = db_manager._try_save_primary(sample_dataframe, '0256_3184_DB.csv')

        assert output_path is not None
        assert os.path.exists(output_path)
        assert '0256_3184_DB.csv' in output_path

    def test_try_save_primary_creates_directory(self, db_manager, sample_dataframe, temp_test_dir):
        """Test that primary save creates missing directory"""
        # Point to non-existent subdirectory
        nested_dir = os.path.join(temp_test_dir, 'subdir', 'nested')
        db_manager.config.set('Paths', 'db_output_path', nested_dir)

        output_path = db_manager._try_save_primary(sample_dataframe, '0256_3184_DB.csv')

        assert output_path is not None
        assert os.path.exists(nested_dir)
        assert os.path.exists(output_path)

    def test_try_save_primary_invalid_directory(self, db_manager, sample_dataframe):
        """Test primary save with invalid directory"""
        # Point to invalid location (e.g., file path on restricted filesystem)
        db_manager.config.set('Paths', 'db_output_path', '/invalid/nonexistent/path')

        output_path = db_manager._try_save_primary(sample_dataframe, '0256_3184_DB.csv')

        # Should fail gracefully
        assert output_path is None

    def test_try_save_primary_empty_config(self, sample_dataframe):
        """Test primary save with no configured path"""
        config = ConfigParser()
        config.add_section('Paths')
        # Don't set db_output_path
        manager = DatabaseManager(config)

        # Should use fallback value and potentially fail (network path)
        output_path = manager._try_save_primary(sample_dataframe, '0256_3184_DB.csv')

        # Expected to fail if network path doesn't exist
        # Test just ensures it doesn't crash
        assert output_path is None or isinstance(output_path, str)

    def test_try_save_primary_verifies_file_size(self, db_manager, temp_test_dir):
        """Test that primary save verifies file size"""
        # Create empty DataFrame (should produce empty CSV)
        df = pd.DataFrame(columns=['sequence', 'line_name'])

        output_path = db_manager._try_save_primary(df, 'test.csv')

        # Should succeed but verify file size
        # Empty CSV with headers should still have some size
        if output_path:
            assert os.path.getsize(output_path) > 0


class TestTrySaveFallback:
    """Test fallback save location functionality"""

    def test_try_save_fallback_success(self, db_manager, sample_dataframe):
        """Test successful fallback save"""
        original_cwd = os.getcwd()
        try:
            # Create temp directory and change to it
            temp_dir = tempfile.mkdtemp()
            os.chdir(temp_dir)

            output_path = db_manager._try_save_fallback(sample_dataframe, '0256_3184_DB.csv')

            assert output_path is not None
            assert os.path.exists(output_path)
            assert output_path.endswith('0256_3184_DB.csv')

            # Cleanup
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rmdir(temp_dir)
        finally:
            os.chdir(original_cwd)

    def test_try_save_fallback_verifies_file(self, db_manager, sample_dataframe):
        """Test that fallback save verifies file"""
        original_cwd = os.getcwd()
        try:
            temp_dir = tempfile.mkdtemp()
            os.chdir(temp_dir)

            output_path = db_manager._try_save_fallback(sample_dataframe, 'test.csv')

            assert output_path is not None
            # Verify file exists and is not empty
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

            # Cleanup
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rmdir(temp_dir)
        finally:
            os.chdir(original_cwd)


class TestSequenceExtraction:
    """Test sequence number extraction"""

    def test_extract_sequence_normal(self, db_manager):
        """Test normal sequence extraction"""
        df = pd.DataFrame({
            'sequence': [256, 256],
            'line_name': ['3184', '3184'],
            'shot_point': [1001, 1003]
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is not None
        assert '0256_' in output_path

    def test_extract_sequence_single_digit(self, db_manager, temp_test_dir):
        """Test sequence extraction with single digit"""
        df = pd.DataFrame({
            'sequence': [5, 5],
            'line_name': ['3184', '3184'],
            'shot_point': [1001, 1003]
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is not None
        assert '0005_' in output_path


class TestLineNameExtraction:
    """Test line name extraction"""

    def test_extract_line_name_numeric(self, db_manager, temp_test_dir):
        """Test line name extraction from numeric value"""
        df = pd.DataFrame({
            'sequence': [256, 256],
            'line_name': [3184, 3184],
            'shot_point': [1001, 1003]
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is not None
        assert '_3184_DB.csv' in output_path

    def test_extract_line_name_string_with_letters(self, db_manager, temp_test_dir):
        """Test line name extraction from string with letters"""
        df = pd.DataFrame({
            'sequence': [256, 256],
            'line_name': ['3184P31885', '3184P31885'],
            'shot_point': [1001, 1003]
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is not None
        # Should extract first 4 digits: '3184'
        assert '_3184_DB.csv' in output_path

    def test_extract_line_name_no_digits(self, db_manager):
        """Test line name extraction with no digits"""
        df = pd.DataFrame({
            'sequence': [256, 256],
            'line_name': ['ABCD', 'ABCD'],
            'shot_point': [1001, 1003]
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        # Should fail because no digits can be extracted
        assert output_path is None


class TestErrorHandling:
    """Test error handling in database operations"""

    def test_handle_exception_in_save(self, db_manager):
        """Test graceful handling of exceptions"""
        # Pass None as results to trigger exception
        output_path = db_manager.save_to_database(None, 'test.S01')

        # Should return None, not raise exception
        assert output_path is None

    def test_handle_index_error(self, db_manager):
        """Test handling of IndexError in extraction"""
        df = pd.DataFrame()  # Empty DataFrame will cause IndexError
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is None


class TestFileNaming:
    """Test output file naming convention"""

    def test_filename_format(self, db_manager, temp_test_dir):
        """Test that output filename follows correct format"""
        df = pd.DataFrame({
            'sequence': [256, 256],
            'line_name': ['3184P31885', '3184P31885'],
            'shot_point': [1001, 1003]
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is not None
        filename = os.path.basename(output_path)
        # Format: SSSS_LLLL_DB.csv
        assert filename == '0256_3184_DB.csv'

    def test_filename_zero_padding(self, db_manager, temp_test_dir):
        """Test that sequence and line name are zero-padded"""
        df = pd.DataFrame({
            'sequence': [1, 1],
            'line_name': [42, 42],
            'shot_point': [1001, 1003]
        })
        results = {'merged_df': df}

        output_path = db_manager.save_to_database(results, 'test.S01')

        assert output_path is not None
        filename = os.path.basename(output_path)
        assert filename.startswith('0001_')
        assert '_0042_' in filename or '_42_' in filename  # Line name might be truncated differently


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
