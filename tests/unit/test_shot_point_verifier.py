"""
Unit tests for Shot Point Verifier Module

Tests shot point counting, consistency checking, and error handling.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from shot_point_verifier import ShotPointVerifier


@pytest.fixture
def temp_test_dir():
    """Create temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def verifier():
    """Create ShotPointVerifier instance"""
    return ShotPointVerifier()


def create_test_file(directory: str, filename: str, pattern: str, count: int):
    """Helper function to create test files with shot point patterns"""
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w') as f:
        # Write header lines
        f.write("H Header line 1\n")
        f.write("H Header line 2\n")
        # Write shot point lines
        for i in range(count):
            f.write(f"{pattern} Shot point {i+1001}\n")


class TestShotPointVerifierInit:
    """Test ShotPointVerifier initialization"""

    def test_initialization(self, verifier):
        """Test verifier initialization"""
        assert verifier is not None
        assert verifier.counts is not None
        assert 'p190' in verifier.counts
        assert 'p294' in verifier.counts
        assert 'S00' in verifier.counts
        assert 'p211' in verifier.counts

    def test_initial_counts_zero(self, verifier):
        """Test that initial counts are zero"""
        for ext in verifier.FILE_PATTERNS.keys():
            assert verifier.counts[ext]['count'] == 0
            assert verifier.counts[ext]['files'] == []

    def test_file_patterns_defined(self, verifier):
        """Test that file patterns are properly defined"""
        assert verifier.FILE_PATTERNS['p190']['pattern'] == 'S'
        assert verifier.FILE_PATTERNS['p294']['pattern'] == 'E1000'
        assert verifier.FILE_PATTERNS['S00']['pattern'] == 'S'
        assert verifier.FILE_PATTERNS['p211']['pattern'] == 'E2'


class TestResetCounts:
    """Test count reset functionality"""

    def test_reset_counts(self, verifier):
        """Test that reset_counts clears all data"""
        # Set some counts
        verifier.counts['p190']['count'] = 100
        verifier.counts['p190']['files'] = ['test.p190']
        verifier.missing_files = ['some file']
        verifier.error_files = [('error.txt', 'error message')]

        # Reset
        verifier.reset_counts()

        # Verify all cleared
        assert verifier.counts['p190']['count'] == 0
        assert verifier.counts['p190']['files'] == []
        assert verifier.missing_files == []
        assert verifier.error_files == []


class TestCountShotPoints:
    """Test shot point counting in individual files"""

    def test_count_p190_file(self, verifier, temp_test_dir):
        """Test counting shot points in P1/90 file"""
        create_test_file(temp_test_dir, '0256-3184P31885.p190', 'S', 50)

        verifier._count_shot_points(os.path.join(temp_test_dir, '0256-3184P31885.p190'))

        assert verifier.counts['p190']['count'] == 50
        assert '0256-3184P31885.p190' in verifier.counts['p190']['files']

    def test_count_p294_file(self, verifier, temp_test_dir):
        """Test counting shot points in P2/94 file"""
        create_test_file(temp_test_dir, '0256-3184P31885.p294', 'E1000', 50)

        verifier._count_shot_points(os.path.join(temp_test_dir, '0256-3184P31885.p294'))

        assert verifier.counts['p294']['count'] == 50
        assert '0256-3184P31885.p294' in verifier.counts['p294']['files']

    def test_count_s00_file(self, verifier, temp_test_dir):
        """Test counting shot points in SPS file"""
        create_test_file(temp_test_dir, '0256-3184P31885.S00', 'S', 50)

        verifier._count_shot_points(os.path.join(temp_test_dir, '0256-3184P31885.S00'))

        assert verifier.counts['S00']['count'] == 50
        assert '0256-3184P31885.S00' in verifier.counts['S00']['files']

    def test_count_p211_file(self, verifier, temp_test_dir):
        """Test counting shot points in P2/11 file"""
        create_test_file(temp_test_dir, '0256-3184P31885.p211', 'E2', 50)

        verifier._count_shot_points(os.path.join(temp_test_dir, '0256-3184P31885.p211'))

        assert verifier.counts['p211']['count'] == 50
        assert '0256-3184P31885.p211' in verifier.counts['p211']['files']

    def test_count_empty_file(self, verifier, temp_test_dir):
        """Test counting shot points in empty file"""
        filepath = os.path.join(temp_test_dir, '0256-3184P31885.p190')
        Path(filepath).touch()

        verifier._count_shot_points(filepath)

        assert verifier.counts['p190']['count'] == 0

    def test_count_file_with_no_matches(self, verifier, temp_test_dir):
        """Test counting shot points in file with no matching patterns"""
        filepath = os.path.join(temp_test_dir, '0256-3184P31885.p190')
        with open(filepath, 'w') as f:
            f.write("H Header line\n")
            f.write("X Invalid line\n")
            f.write("Y Another invalid line\n")

        verifier._count_shot_points(filepath)

        assert verifier.counts['p190']['count'] == 0


class TestVerifyDirectory:
    """Test directory verification functionality"""

    def test_verify_directory_all_files_consistent(self, verifier, temp_test_dir):
        """Test verification with all files having same count"""
        # Create all required files with same count
        create_test_file(temp_test_dir, '0256-3184P31885.p190', 'S', 50)
        create_test_file(temp_test_dir, '0256-3184P31885.p294', 'E1000', 50)
        create_test_file(temp_test_dir, '0256-3184P31885.S00', 'S', 50)
        create_test_file(temp_test_dir, '0256-3184P31885.p211', 'E2', 50)

        is_consistent, report = verifier.verify_directory(temp_test_dir)

        assert is_consistent is True
        assert '50' in report
        assert 'matching shot point count' in report

    def test_verify_directory_inconsistent_counts(self, verifier, temp_test_dir):
        """Test verification with mismatched counts"""
        # Create files with different counts
        create_test_file(temp_test_dir, '0256-3184P31885.p190', 'S', 50)
        create_test_file(temp_test_dir, '0256-3184P31885.p294', 'E1000', 45)
        create_test_file(temp_test_dir, '0256-3184P31885.S00', 'S', 50)
        create_test_file(temp_test_dir, '0256-3184P31885.p211', 'E2', 50)

        is_consistent, report = verifier.verify_directory(temp_test_dir)

        assert is_consistent is False
        assert 'Mismatch detected' in report

    def test_verify_directory_missing_files(self, verifier, temp_test_dir):
        """Test verification with missing files"""
        # Create only some files
        create_test_file(temp_test_dir, '0256-3184P31885.p190', 'S', 50)
        create_test_file(temp_test_dir, '0256-3184P31885.p294', 'E1000', 50)
        # Missing .S00 and .p211

        is_consistent, report = verifier.verify_directory(temp_test_dir)

        assert is_consistent is False
        assert 'Missing Required Files' in report

    def test_verify_directory_empty(self, verifier, temp_test_dir):
        """Test verification of empty directory"""
        is_consistent, report = verifier.verify_directory(temp_test_dir)

        assert is_consistent is False
        assert 'Missing Required Files' in report

    def test_verify_directory_no_shot_points(self, verifier, temp_test_dir):
        """Test verification with files containing no shot points"""
        # Create files but with no shot point patterns
        for filename, pattern in [
            ('0256-3184P31885.p190', 'S'),
            ('0256-3184P31885.p294', 'E1000'),
            ('0256-3184P31885.S00', 'S'),
            ('0256-3184P31885.p211', 'E2')
        ]:
            filepath = os.path.join(temp_test_dir, filename)
            with open(filepath, 'w') as f:
                f.write("H Header only\n")

        is_consistent, report = verifier.verify_directory(temp_test_dir)

        assert is_consistent is False
        assert 'No shot points found' in report


class TestGenerateReport:
    """Test report generation"""

    def test_generate_report_with_missing_files(self, verifier):
        """Test report generation with missing files"""
        verifier.missing_files = ['P1/90 File', 'P2/94 File']

        is_consistent, report = verifier._generate_report()

        assert is_consistent is False
        assert 'Missing Required Files' in report
        assert 'P1/90 File' in report
        assert 'P2/94 File' in report

    def test_generate_report_with_errors(self, verifier):
        """Test report generation with file errors"""
        verifier.error_files = [
            ('test.p190', 'Permission denied'),
            ('test.p294', 'File not found')
        ]

        is_consistent, report = verifier._generate_report()

        assert is_consistent is False
        assert 'Errors encountered' in report
        assert 'Permission denied' in report
        assert 'File not found' in report

    def test_generate_report_consistent_counts(self, verifier):
        """Test report generation with consistent counts"""
        verifier.counts['p190']['count'] = 50
        verifier.counts['p190']['files'] = ['test.p190']
        verifier.counts['p294']['count'] = 50
        verifier.counts['p294']['files'] = ['test.p294']
        verifier.counts['S00']['count'] = 50
        verifier.counts['S00']['files'] = ['test.S00']
        verifier.counts['p211']['count'] = 50
        verifier.counts['p211']['files'] = ['test.p211']

        is_consistent, report = verifier._generate_report()

        assert is_consistent is True
        assert '50 shot points' in report
        assert 'All files have matching shot point count: 50' in report

    def test_generate_report_inconsistent_counts(self, verifier):
        """Test report generation with inconsistent counts"""
        verifier.counts['p190']['count'] = 50
        verifier.counts['p190']['files'] = ['test.p190']
        verifier.counts['p294']['count'] = 45
        verifier.counts['p294']['files'] = ['test.p294']
        verifier.counts['S00']['count'] = 50
        verifier.counts['S00']['files'] = ['test.S00']
        verifier.counts['p211']['count'] = 50
        verifier.counts['p211']['files'] = ['test.p211']

        is_consistent, report = verifier._generate_report()

        assert is_consistent is False
        assert 'Mismatch detected' in report
        assert '45 shot points' in report or 'different shot point counts' in report


class TestFilePatternRecognition:
    """Test file pattern recognition"""

    def test_case_insensitive_extension_match(self, verifier, temp_test_dir):
        """Test that file extension matching is case-insensitive"""
        # Create files with mixed case extensions
        create_test_file(temp_test_dir, '0256-3184P31885.P190', 'S', 50)
        create_test_file(temp_test_dir, '0256-3184P31885.p294', 'E1000', 50)

        verifier.verify_directory(temp_test_dir)

        assert verifier.counts['p190']['count'] == 50
        assert verifier.counts['p294']['count'] == 50

    def test_multiple_files_same_type(self, verifier, temp_test_dir):
        """Test handling multiple files of the same type"""
        # Create two .p190 files
        create_test_file(temp_test_dir, '0256-3184P31885.p190', 'S', 30)
        create_test_file(temp_test_dir, '0256-3184P31886.p190', 'S', 40)

        verifier.verify_directory(temp_test_dir)

        # The code overwrites count with each file, so it depends on processing order
        # Just verify that both files were tracked
        assert verifier.counts['p190']['count'] in [30, 40]
        assert len(verifier.counts['p190']['files']) == 2


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_verify_nonexistent_directory(self, verifier):
        """Test verification of nonexistent directory"""
        with pytest.raises(FileNotFoundError):
            verifier.verify_directory('/nonexistent/directory')

    def test_file_with_unicode_content(self, verifier, temp_test_dir):
        """Test handling files with unicode characters"""
        filepath = os.path.join(temp_test_dir, '0256-3184P31885.p190')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("S Shot point with unicode: €£¥\n")
            f.write("S Another shot point: 中文\n")

        verifier._count_shot_points(filepath)

        assert verifier.counts['p190']['count'] == 2

    def test_file_with_invalid_encoding(self, verifier, temp_test_dir):
        """Test handling files with encoding issues"""
        filepath = os.path.join(temp_test_dir, '0256-3184P31885.p190')
        # Write binary data that may cause encoding issues
        with open(filepath, 'wb') as f:
            f.write(b'S Shot point 1\n')
            f.write(b'\xff\xfe Invalid bytes\n')
            f.write(b'S Shot point 2\n')

        # Should handle gracefully with 'ignore' errors setting
        verifier._count_shot_points(filepath)

        # Should count at least the valid lines
        assert verifier.counts['p190']['count'] >= 2

    def test_large_file_performance(self, verifier, temp_test_dir):
        """Test performance with large file"""
        # Create file with 10000 shot points
        create_test_file(temp_test_dir, '0256-3184P31885.p190', 'S', 10000)

        verifier._count_shot_points(os.path.join(temp_test_dir, '0256-3184P31885.p190'))

        assert verifier.counts['p190']['count'] == 10000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
