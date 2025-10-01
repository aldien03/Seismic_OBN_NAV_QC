"""
Unit tests for File Renamer Module

Tests file renaming logic, pattern matching, and error handling.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from configparser import ConfigParser
from file_renamer import FileRenamer


@pytest.fixture
def temp_test_dir():
    """Create temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config():
    """Create test configuration for file renaming"""
    config = ConfigParser()

    # Add RAW file renaming patterns
    config.add_section('Rename_Raw_Files')
    config.set('Rename_Raw_Files', 'raw_expected_extensions', '.p190, .p294, .S00, .p211')
    config.set('Rename_Raw_Files', 'raw_expected_file_number', '4')
    config.set('Rename_Raw_Files', 'already_compliant_pattern', r'^0256-\d{4}P\d{5}\.(p190|p294|S00|p211)$')
    config.set('Rename_Raw_Files', 'p190_pattern', r'^(\d{4}P\d)(\d{4})\.0\.p190$ -> 0256-\1\2.p190')
    config.set('Rename_Raw_Files', 'p294_pattern', r'^(\d{4}P\d)(\d{4})\.0\.p294$ -> 0256-\1\2.p294')
    config.set('Rename_Raw_Files', 's00_pattern', r'^(\d{4}P\d)(\d{4})\.S00$ -> 0256-\1\2.S00')
    config.set('Rename_Raw_Files', 'p211_pattern', r'^(\d{4}P\d)(\d{4})\.p211$ -> 0256-\1\2.p211')

    # Add Processed file renaming patterns
    config.add_section('Rename_Processed_Files')
    config.set('Rename_Processed_Files', 'processed_expected_extensions', '.csv, .S01')
    config.set('Rename_Processed_Files', 'processed_expected_file_number', '2')
    config.set('Rename_Processed_Files', 'already_compliant_pattern', r'^0256-\d{4}P\d{5}.*\.(csv|S01)$')
    config.set('Rename_Processed_Files', 'eol_csv_pattern', r'^seq\d+_\d+_(\d{4}P\d)(\d{4})_EOL_report\.csv$ -> 0256-\1\2_EOL_report.csv')
    config.set('Rename_Processed_Files', 's01_pattern', r'^(\d{4}P\d)(\d{4})\.S01$ -> 0256-\1\2.S01')

    return config


@pytest.fixture
def file_renamer(test_config):
    """Create FileRenamer instance with test config"""
    return FileRenamer(test_config)


class TestFileRenamerInit:
    """Test FileRenamer initialization"""

    def test_initialization(self, test_config):
        """Test FileRenamer initialization"""
        renamer = FileRenamer(test_config)

        assert renamer.config is not None
        assert renamer.rename_patterns == {}
        assert renamer.already_compliant_patterns == {}
        assert renamer.expected_extensions == {}
        assert 'renamed' in renamer.processed_files
        assert 'compliant' in renamer.processed_files
        assert 'missing' in renamer.processed_files
        assert 'errors' in renamer.processed_files


class TestLoadRenamePatterns:
    """Test pattern loading from configuration"""

    def test_load_raw_patterns_success(self, file_renamer):
        """Test loading RAW file patterns"""
        result = file_renamer._load_rename_patterns('Rename_Raw_Files')

        assert result is True
        assert 'Rename_Raw_Files' in file_renamer.rename_patterns
        assert len(file_renamer.rename_patterns['Rename_Raw_Files']) == 4
        assert 'Rename_Raw_Files' in file_renamer.already_compliant_patterns
        assert '.p190' in file_renamer.expected_extensions['Rename_Raw_Files']

    def test_load_processed_patterns_success(self, file_renamer):
        """Test loading Processed file patterns"""
        result = file_renamer._load_rename_patterns('Rename_Processed_Files')

        assert result is True
        assert 'Rename_Processed_Files' in file_renamer.rename_patterns
        assert len(file_renamer.rename_patterns['Rename_Processed_Files']) == 2

    def test_load_nonexistent_section(self, file_renamer):
        """Test loading patterns from nonexistent section"""
        result = file_renamer._load_rename_patterns('Nonexistent_Section')

        assert result is False

    def test_load_invalid_regex_pattern(self, test_config):
        """Test loading configuration with invalid regex"""
        config = ConfigParser()
        config.add_section('Rename_Test')
        config.set('Rename_Test', 'raw_expected_extensions', '.test')
        config.set('Rename_Test', 'raw_expected_file_number', '1')
        config.set('Rename_Test', 'bad_pattern', r'^[invalid( -> test')  # Invalid regex

        renamer = FileRenamer(config)
        result = renamer._load_rename_patterns('Rename_Test')

        assert result is False


class TestRenameRAWFiles:
    """Test RAW file renaming"""

    def test_rename_raw_files_success(self, file_renamer, temp_test_dir):
        """Test successful renaming of RAW files"""
        # Create test files with old naming convention
        test_files = [
            '3184P31885.0.p190',
            '3184P31885.0.p294',
            '3184P31885.S00',
            '3184P31885.p211'
        ]

        for filename in test_files:
            filepath = os.path.join(temp_test_dir, filename)
            Path(filepath).touch()

        # Rename files
        renamed, compliant, missing, errors = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        # Check results
        assert renamed == 4
        assert compliant == 0
        assert len(errors) == 0

        # Verify renamed files exist
        expected_names = [
            '0256-3184P31885.p190',
            '0256-3184P31885.p294',
            '0256-3184P31885.S00',
            '0256-3184P31885.p211'
        ]

        for expected in expected_names:
            assert os.path.exists(os.path.join(temp_test_dir, expected))

    def test_rename_already_compliant_files(self, file_renamer, temp_test_dir):
        """Test handling of already compliant files"""
        # Create files that are already properly named
        test_files = [
            '0256-3184P31885.p190',
            '0256-3184P31885.p294'
        ]

        for filename in test_files:
            filepath = os.path.join(temp_test_dir, filename)
            Path(filepath).touch()

        renamed, compliant, missing, errors = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        assert renamed == 0
        assert compliant == 2
        assert len(errors) == 0

    def test_rename_with_existing_target(self, file_renamer, temp_test_dir):
        """Test renaming when target file already exists"""
        # Create source file
        source = '3184P31885.0.p190'
        target = '0256-3184P31885.p190'

        Path(os.path.join(temp_test_dir, source)).touch()
        Path(os.path.join(temp_test_dir, target)).touch()

        renamed, compliant, missing, errors = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        # Both files are processed:
        # - Target file is already compliant (counted as compliant)
        # - Source file attempts rename but fails (error + treated as compliant)
        assert renamed == 0
        assert compliant == 2  # Both files end up as "compliant"
        assert len(errors) > 0
        assert 'already exists' in errors[0]

    def test_rename_missing_directory(self, file_renamer):
        """Test renaming in nonexistent directory"""
        renamed, compliant, missing, errors = file_renamer.rename_files_in_directory(
            '/nonexistent/directory', 'Rename_Raw_Files'
        )

        assert renamed == 0
        assert len(errors) > 0
        assert 'not found' in errors[0].lower()


class TestRenameProcessedFiles:
    """Test Processed file renaming"""

    def test_rename_processed_files_success(self, file_renamer, temp_test_dir):
        """Test successful renaming of Processed files"""
        test_files = [
            'seq0256_027_3184P31885_EOL_report.csv',
            '3184P31885.S01'
        ]

        for filename in test_files:
            filepath = os.path.join(temp_test_dir, filename)
            Path(filepath).touch()

        renamed, compliant, missing, errors = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Processed_Files'
        )

        assert renamed == 2
        assert compliant == 0
        assert len(errors) == 0

        # Verify renamed files
        assert os.path.exists(os.path.join(temp_test_dir, '0256-3184P31885_EOL_report.csv'))
        assert os.path.exists(os.path.join(temp_test_dir, '0256-3184P31885.S01'))

    def test_rename_processed_already_compliant(self, file_renamer, temp_test_dir):
        """Test handling of already compliant processed files"""
        test_files = [
            '0256-3184P31885_EOL_report.csv',
            '0256-3184P31885.S01'
        ]

        for filename in test_files:
            filepath = os.path.join(temp_test_dir, filename)
            Path(filepath).touch()

        renamed, compliant, missing, errors = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Processed_Files'
        )

        assert renamed == 0
        assert compliant == 2
        assert len(errors) == 0


class TestMissingFileDetection:
    """Test missing file type detection"""

    def test_detect_missing_extensions(self, file_renamer, temp_test_dir):
        """Test detection of missing file types"""
        # Create only some of the expected files
        test_files = [
            '3184P31885.0.p190',
            '3184P31885.0.p294'
            # Missing .S00 and .p211
        ]

        for filename in test_files:
            filepath = os.path.join(temp_test_dir, filename)
            Path(filepath).touch()

        renamed, compliant, missing, errors = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        assert len(file_renamer.processed_files['missing_extensions']) == 2
        assert '.s00' in file_renamer.processed_files['missing_extensions']
        assert '.p211' in file_renamer.processed_files['missing_extensions']


class TestProcessedFilesTracking:
    """Test tracking of processed files"""

    def test_processed_files_reset(self, file_renamer, temp_test_dir):
        """Test that processed_files is reset between operations"""
        # First operation
        Path(os.path.join(temp_test_dir, '3184P31885.0.p190')).touch()
        file_renamer.rename_files_in_directory(temp_test_dir, 'Rename_Raw_Files')

        first_renamed = len(file_renamer.processed_files['renamed'])
        assert first_renamed == 1

        # Second operation (new directory)
        temp_dir2 = tempfile.mkdtemp()
        try:
            Path(os.path.join(temp_dir2, '3184P31886.0.p190')).touch()
            file_renamer.rename_files_in_directory(temp_dir2, 'Rename_Raw_Files')

            # Should only have second operation's file
            assert len(file_renamer.processed_files['renamed']) == 1
            assert '3184P31886.0.p190' in file_renamer.processed_files['renamed'][0][0]
        finally:
            shutil.rmtree(temp_dir2)

    def test_track_renamed_files(self, file_renamer, temp_test_dir):
        """Test tracking of renamed files"""
        Path(os.path.join(temp_test_dir, '3184P31885.0.p190')).touch()

        file_renamer.rename_files_in_directory(temp_test_dir, 'Rename_Raw_Files')

        assert len(file_renamer.processed_files['renamed']) == 1
        old_name, new_name = file_renamer.processed_files['renamed'][0]
        assert old_name == '3184P31885.0.p190'
        assert new_name == '0256-3184P31885.p190'

    def test_track_compliant_files(self, file_renamer, temp_test_dir):
        """Test tracking of already compliant files"""
        Path(os.path.join(temp_test_dir, '0256-3184P31885.p190')).touch()

        file_renamer.rename_files_in_directory(temp_test_dir, 'Rename_Raw_Files')

        assert len(file_renamer.processed_files['compliant']) == 1
        assert '0256-3184P31885.p190' in file_renamer.processed_files['compliant']

    def test_track_errors(self, file_renamer, temp_test_dir):
        """Test tracking of errors during renaming"""
        # Create source and target file (collision)
        source_file = os.path.join(temp_test_dir, '3184P31885.0.p190')
        target_file = os.path.join(temp_test_dir, '0256-3184P31885.p190')

        Path(source_file).touch()
        Path(target_file).touch()

        file_renamer.rename_files_in_directory(temp_test_dir, 'Rename_Raw_Files')

        # Should have error for collision
        assert len(file_renamer.processed_files['errors']) > 0
        assert any('already exists' in error for error in file_renamer.processed_files['errors'])


class TestPatternMatching:
    """Test regex pattern matching"""

    def test_p190_pattern_match(self, file_renamer, temp_test_dir):
        """Test P190 file pattern matching"""
        Path(os.path.join(temp_test_dir, '3184P31885.0.p190')).touch()

        renamed, _, _, _ = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        assert renamed == 1
        assert os.path.exists(os.path.join(temp_test_dir, '0256-3184P31885.p190'))

    def test_p294_pattern_match(self, file_renamer, temp_test_dir):
        """Test P294 file pattern matching"""
        Path(os.path.join(temp_test_dir, '3184P31885.0.p294')).touch()

        renamed, _, _, _ = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        assert renamed == 1
        assert os.path.exists(os.path.join(temp_test_dir, '0256-3184P31885.p294'))

    def test_s00_pattern_match(self, file_renamer, temp_test_dir):
        """Test S00 file pattern matching"""
        Path(os.path.join(temp_test_dir, '3184P31885.S00')).touch()

        renamed, _, _, _ = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        assert renamed == 1
        assert os.path.exists(os.path.join(temp_test_dir, '0256-3184P31885.S00'))

    def test_unmatched_file_treated_as_compliant(self, file_renamer, temp_test_dir):
        """Test that unmatched files are treated as already compliant"""
        # Create file that doesn't match any pattern
        Path(os.path.join(temp_test_dir, 'random_file.p190')).touch()

        renamed, compliant, _, errors = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        assert renamed == 0
        assert compliant == 1
        assert len(errors) == 0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_directory(self, file_renamer, temp_test_dir):
        """Test renaming in empty directory"""
        renamed, compliant, missing, errors = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        assert renamed == 0
        assert compliant == 0

    def test_directory_with_subdirectories(self, file_renamer, temp_test_dir):
        """Test that subdirectories are ignored"""
        # Create subdirectory
        subdir = os.path.join(temp_test_dir, 'subdir')
        os.makedirs(subdir)

        # Create file in subdirectory (should be ignored)
        Path(os.path.join(subdir, '3184P31885.0.p190')).touch()

        renamed, compliant, _, _ = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        assert renamed == 0
        assert compliant == 0

    def test_files_with_wrong_extensions(self, file_renamer, temp_test_dir):
        """Test that files with wrong extensions are ignored"""
        Path(os.path.join(temp_test_dir, '3184P31885.txt')).touch()
        Path(os.path.join(temp_test_dir, '3184P31885.doc')).touch()

        renamed, compliant, _, _ = file_renamer.rename_files_in_directory(
            temp_test_dir, 'Rename_Raw_Files'
        )

        assert renamed == 0
        assert compliant == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
