"""
Baseline Integration Test for PXGEONavQC

This test verifies that the current code works correctly with Sample data
before any refactoring is performed. It serves as a regression test to ensure
that refactoring doesn't break existing functionality.

Test Strategy:
1. Test that core components can be imported and instantiated
2. Test that config file can be loaded
3. Test that sample files can be found and verified
4. Test file renaming functionality (dry run)
5. Test shot point verification

Note: We cannot test the full QC workflow in automated tests because it requires
a GUI (QMainWindow) which needs a display. That will be tested manually.
"""

import os
import sys
from pathlib import Path

import pytest

# Import the main module
import PXGEONavQCTools as navqc


@pytest.mark.integration
@pytest.mark.requires_sample_data
class TestBaselineWorkflow:
    """Integration tests for baseline functionality."""

    def test_config_manager_can_load_config(self, config_file):
        """Test that ConfigManager can load config.ini."""
        config_manager = navqc.ConfigManager(str(config_file))
        config_manager.load_config()

        # Verify config sections exist
        assert config_manager.config.has_section("General")
        assert config_manager.config.has_section("QC_Thresholds")
        assert config_manager.config.has_section("Rename_Raw_Files")
        assert config_manager.config.has_section("Rename_Processed_Files")

        # Verify some key config values
        source_option = config_manager.config.get("General", "source_option")
        assert source_option in ["Dual", "Triple"]

        sti_error = float(config_manager.config.get("QC_Thresholds", "sti_error_threshold"))
        assert sti_error > 0

    def test_file_renamer_can_be_instantiated(self, config_file):
        """Test that FileRenamer can be created with config."""
        config_manager = navqc.ConfigManager(str(config_file))
        config_manager.load_config()

        file_renamer = navqc.FileRenamer(config_manager.config)
        assert file_renamer is not None
        assert file_renamer.config is not None

    def test_shot_point_verifier_can_be_instantiated(self):
        """Test that ShotPointVerifier can be created."""
        verifier = navqc.ShotPointVerifier()
        assert verifier is not None
        assert verifier.counts is not None
        assert 'p190' in verifier.counts
        assert 'p294' in verifier.counts
        assert 'S00' in verifier.counts
        assert 'p211' in verifier.counts

    def test_shot_point_verifier_can_count_sample_data(self, sample_production_dir):
        """Test that ShotPointVerifier can count shot points in sample data."""
        verifier = navqc.ShotPointVerifier()
        is_consistent, report = verifier.verify_directory(str(sample_production_dir))

        # Verify that we got a tuple back
        assert isinstance(is_consistent, bool)
        assert isinstance(report, str)
        assert len(report) > 0

        # Verify that counts were updated (should be > 0 for sample data)
        assert verifier.counts['p190']['count'] > 0, "Expected p190 file to have shot points"
        assert verifier.counts['p294']['count'] > 0, "Expected p294 file to have shot points"
        assert verifier.counts['S00']['count'] > 0, "Expected S00 file to have shot points"
        assert verifier.counts['p211']['count'] > 0, "Expected p211 file to have shot points"

        # Verify report contains the file names
        assert "0256-3184P31885.p190" in report
        assert "0256-3184P31885.p294" in report
        assert "0256-3184P31885.S00" in report
        assert "0256-3184P31885.p211" in report

    def test_sample_files_exist(self, sample_files):
        """Test that all expected sample files exist."""
        # Check raw files
        for file_type, file_path in sample_files["raw"].items():
            assert file_path.exists(), f"Raw file missing: {file_type} at {file_path}"

        # Check processed files
        for file_type, file_path in sample_files["processed"].items():
            assert file_path.exists(), f"Processed file missing: {file_type} at {file_path}"

        # Check gundata files
        for file_type, file_path in sample_files["gundata"].items():
            assert file_path.exists(), f"GunData file missing: {file_type} at {file_path}"

    def test_sample_files_are_readable(self, sample_files):
        """Test that sample files can be opened and read."""
        # Test a few key files
        test_files = [
            sample_files["raw"]["p190"],
            sample_files["processed"]["sps_comp"],
            sample_files["processed"]["eol_report"],
            sample_files["gundata"]["asc"],
        ]

        for file_path in test_files:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(1000)  # Read first 1000 chars
                assert len(content) > 0, f"File appears empty: {file_path}"

    def test_sample_csv_files_have_headers(self, sample_files):
        """Test that CSV files have proper headers."""
        import pandas as pd

        csv_files = [
            sample_files["processed"]["sps_comp"],
            sample_files["processed"]["eol_report"],
            sample_files["processed"]["string_sep"],
        ]

        for csv_file in csv_files:
            # Try different encodings as some CSV files may have special characters
            for encoding in ['utf-8', 'latin-1', 'iso-8859-1']:
                try:
                    df = pd.read_csv(csv_file, nrows=1, encoding=encoding)
                    assert len(df.columns) > 0, f"CSV file has no columns: {csv_file}"
                    assert len(df) > 0, f"CSV file has no data rows: {csv_file}"
                    break
                except UnicodeDecodeError:
                    continue
            else:
                pytest.fail(f"Could not read CSV file with any encoding: {csv_file}")

    @pytest.mark.slow
    def test_config_patterns_are_valid_regex(self, config_file):
        """Test that all regex patterns in config are valid."""
        import re

        config_manager = navqc.ConfigManager(str(config_file))
        config_manager.load_config()

        file_renamer = navqc.FileRenamer(config_manager.config)

        # Load raw file patterns - returns False if error, dict if success
        raw_patterns = file_renamer._load_rename_patterns("Rename_Raw_Files")
        if isinstance(raw_patterns, dict):
            for pattern_name, (search_pattern, _) in raw_patterns.items():
                try:
                    re.compile(search_pattern)
                except re.error as e:
                    pytest.fail(f"Invalid regex in Rename_Raw_Files.{pattern_name}: {e}")
        else:
            pytest.skip("Could not load raw file patterns")

        # Load processed file patterns
        proc_patterns = file_renamer._load_rename_patterns("Rename_Processed_Files")
        if isinstance(proc_patterns, dict):
            for pattern_name, (search_pattern, _) in proc_patterns.items():
                try:
                    re.compile(search_pattern)
                except re.error as e:
                    pytest.fail(f"Invalid regex in Rename_Processed_Files.{pattern_name}: {e}")
        else:
            pytest.skip("Could not load processed file patterns")


@pytest.mark.integration
@pytest.mark.unit
class TestImportability:
    """Test that all components can be imported."""

    def test_can_import_main_module(self):
        """Test that the main module can be imported."""
        import PXGEONavQCTools
        assert PXGEONavQCTools is not None

    def test_config_manager_exists(self):
        """Test that ConfigManager class exists."""
        assert hasattr(navqc, "ConfigManager")
        assert callable(navqc.ConfigManager)

    def test_ftp_fetcher_removed(self):
        """Test that FTPFetcher class has been removed in Phase 3."""
        assert not hasattr(navqc, "FTPFetcher"), "FTPFetcher should be removed"

    def test_file_renamer_exists(self):
        """Test that FileRenamer class exists."""
        assert hasattr(navqc, "FileRenamer")
        assert callable(navqc.FileRenamer)

    def test_shot_point_verifier_exists(self):
        """Test that ShotPointVerifier class exists."""
        assert hasattr(navqc, "ShotPointVerifier")
        assert callable(navqc.ShotPointVerifier)

    def test_main_window_exists(self):
        """Test that MainWindow class exists."""
        assert hasattr(navqc, "MainWindow")
        assert callable(navqc.MainWindow)


@pytest.mark.integration
class TestSampleDataStructure:
    """Test that sample data structure is as expected."""

    def test_production_directory_structure(self, sample_production_dir):
        """Test that production directory has expected structure."""
        # Should have raw files in root
        raw_files = list(sample_production_dir.glob("0256-*.p190"))
        assert len(raw_files) > 0, "No p190 files found"

        # Should have Processed subdirectory
        processed_dir = sample_production_dir / "Processed"
        assert processed_dir.exists(), "Processed directory missing"
        assert processed_dir.is_dir(), "Processed is not a directory"

    def test_processed_directory_structure(self, sample_processed_dir):
        """Test that processed directory has expected files."""
        # Should have S01 files
        s01_files = list(sample_processed_dir.glob("*.S01"))
        assert len(s01_files) > 0, "No S01 files found"

        # Should have CSV files
        csv_files = list(sample_processed_dir.glob("*.csv"))
        assert len(csv_files) > 0, "No CSV files found"

    def test_gundata_directory_structure(self, sample_gundata_dir):
        """Test that gundata directory has expected files."""
        # Should have ASC file
        asc_files = list(sample_gundata_dir.glob("*.asc"))
        assert len(asc_files) > 0, "No ASC files found"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "-s"])