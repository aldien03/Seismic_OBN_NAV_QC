"""
Unit tests for data_importers module
"""

import os
import pytest
import pandas as pd
from unittest.mock import Mock, patch, mock_open
from data_importers import (
    DataImporter,
    SPSImporter,
    SPSCompImporter,
    EOLImporter,
    ASCImporter,
    SBSImporter
)
from config_manager import ConfigManager


@pytest.fixture
def config_manager():
    """Create a ConfigManager instance with test config"""
    config = ConfigManager()
    config.load_config()
    return config


@pytest.fixture
def mock_sps_file_content():
    """Mock SPS file content with header and data rows"""
    # SPS format: 107 characters per line with specific column positions
    # Column positions match SPSImporter colspecs
    return """H
H Header line 1
H Header line 2
S      3184      1885  1D     0 7.0   0  0  10.0  123456.0  7654321.0  10.0001123456     27025000000    0
S      3184      1886  1D     0 7.5   0  0  10.5  123457.0  7654322.0  10.5001123500     27025000000    0
"""


@pytest.fixture
def mock_sps_comp_content():
    """Mock SPS_Comp CSV content"""
    return """Line,Code,Shot,Radial (m),Crossline (m),Inline (m)
3184P,D,1885,5.2,3.1,2.0
3184P,D,1886,4.8,2.9,1.8
"""


@pytest.fixture
def mock_eol_content():
    """Mock EOL report CSV content"""
    return """SP,Gun Depth,Pressure
1885,-7.0,2000
1886,-7.2,1950
"""


@pytest.fixture
def mock_asc_content():
    """Mock ASC gun data file content"""
    return """Header line 1
Header line 2
Header line 3
Header line 4
SHOTPOINT AIM_POINT_TIME GUN_DEPTH GUN_PRESSURE
001885 123456 -7.0 2000
001886 123500 -7.2 1950
"""


@pytest.fixture
def mock_sbs_content():
    """Mock SBS file content"""
    return """# Comment line
Shot\tTime\tDate\tRaw Time
1885\t12:34:56\t2025-01-15\t45296.0
1886\t12:35:02\t2025-01-15\t45302.0
"""


class TestSPSImporter:
    """Test cases for SPSImporter"""

    def test_import_file_success(self, config_manager, tmp_path, mock_sps_file_content):
        """Test successful SPS file import"""
        # Create temporary SPS file
        sps_file = tmp_path / "test.S01"
        sps_file.write_text(mock_sps_file_content)

        importer = SPSImporter(config_manager)
        df = importer.import_file(str(sps_file))

        assert not df.empty
        assert 'shot_point' in df.columns
        assert 'easting_m' in df.columns
        assert 'northing_m' in df.columns
        assert len(df) == 2
        assert df['shot_point'].iloc[0] == 1885

    def test_import_file_not_found(self, config_manager):
        """Test handling of missing SPS file"""
        importer = SPSImporter(config_manager)
        df = importer.import_file("/nonexistent/path/file.S01")

        assert df.empty

    def test_header_row_detection(self, config_manager, tmp_path, mock_sps_file_content):
        """Test correct detection of header rows"""
        sps_file = tmp_path / "test.S01"
        sps_file.write_text(mock_sps_file_content)

        importer = SPSImporter(config_manager)
        df = importer.import_file(str(sps_file))

        # Should skip 3 header lines (H lines)
        assert len(df) == 2

    def test_data_type_conversion(self, config_manager, tmp_path, mock_sps_file_content):
        """Test proper data type conversion"""
        sps_file = tmp_path / "test.S01"
        sps_file.write_text(mock_sps_file_content)

        importer = SPSImporter(config_manager)
        df = importer.import_file(str(sps_file))

        assert df['shot_point'].dtype == 'Int64'
        assert pd.api.types.is_float_dtype(df['easting_m'])
        assert pd.api.types.is_float_dtype(df['northing_m'])

    def test_shot_dither_included(self, config_manager, tmp_path, mock_sps_file_content):
        """Test that shot_dither column is included in output"""
        sps_file = tmp_path / "test.S01"
        sps_file.write_text(mock_sps_file_content)

        importer = SPSImporter(config_manager)
        df = importer.import_file(str(sps_file))

        assert 'shot_dither' in df.columns
        assert pd.api.types.is_numeric_dtype(df['shot_dither'])


class TestSPSCompImporter:
    """Test cases for SPSCompImporter"""

    def test_import_file_success(self, config_manager, tmp_path, mock_sps_comp_content):
        """Test successful SPS_Comp file import"""
        # Create Processed folder with SPS_Comp file
        processed_folder = tmp_path / "Processed"
        processed_folder.mkdir()
        comp_file = processed_folder / "0256-3184P31885_SPS_Comp.csv"
        comp_file.write_text(mock_sps_comp_content)

        importer = SPSCompImporter(config_manager)
        df = importer.import_file(str(processed_folder))

        assert not df.empty
        assert 'shot_point' in df.columns
        assert 'Radial (m)' in df.columns
        assert 'Crossline (m)' in df.columns
        assert 'Inline (m)' in df.columns
        assert len(df) == 2

    def test_import_file_no_processed_folder(self, config_manager, tmp_path):
        """Test handling when Processed folder doesn't exist"""
        importer = SPSCompImporter(config_manager)
        df = importer.import_file(str(tmp_path / "Processed"))

        assert df.empty

    def test_import_file_no_matching_file(self, config_manager, tmp_path):
        """Test handling when no matching SPS_Comp file found"""
        processed_folder = tmp_path / "Processed"
        processed_folder.mkdir()

        importer = SPSCompImporter(config_manager)
        df = importer.import_file(str(processed_folder))

        assert df.empty


class TestEOLImporter:
    """Test cases for EOLImporter"""

    def test_import_file_success(self, config_manager, tmp_path, mock_eol_content):
        """Test successful EOL report import"""
        processed_folder = tmp_path / "Processed"
        processed_folder.mkdir()
        eol_file = processed_folder / "0256-3184P31885_EOL_report.csv"
        eol_file.write_text(mock_eol_content)

        importer = EOLImporter(config_manager)
        df = importer.import_file(str(processed_folder))

        assert not df.empty
        assert 'shot_point' in df.columns
        assert len(df) == 2

    def test_import_file_no_matching_file(self, config_manager, tmp_path):
        """Test handling when no EOL file found"""
        processed_folder = tmp_path / "Processed"
        processed_folder.mkdir()

        importer = EOLImporter(config_manager)
        df = importer.import_file(str(processed_folder))

        assert df.empty


class TestASCImporter:
    """Test cases for ASCImporter"""

    def test_import_file_success(self, config_manager, tmp_path, mock_asc_content):
        """Test successful ASC file import"""
        gundata_folder = tmp_path / "GunData"
        gundata_folder.mkdir()
        asc_file = gundata_folder / "gundata.asc"
        asc_file.write_text(mock_asc_content)

        importer = ASCImporter(config_manager)
        df = importer.import_file(str(gundata_folder))

        assert not df.empty
        assert 'shot_point' in df.columns
        assert len(df) == 2
        # Verify leading zeros are stripped
        assert df['shot_point'].iloc[0] == 1885

    def test_import_file_no_asc_file(self, config_manager, tmp_path):
        """Test handling when no ASC file found"""
        gundata_folder = tmp_path / "GunData"
        gundata_folder.mkdir()

        importer = ASCImporter(config_manager)
        df = importer.import_file(str(gundata_folder))

        assert df.empty

    def test_drops_aim_point_time(self, config_manager, tmp_path, mock_asc_content):
        """Test that AIM_POINT_TIME column is dropped"""
        gundata_folder = tmp_path / "GunData"
        gundata_folder.mkdir()
        asc_file = gundata_folder / "gundata.asc"
        asc_file.write_text(mock_asc_content)

        importer = ASCImporter(config_manager)
        df = importer.import_file(str(gundata_folder))

        assert 'AIM_POINT_TIME' not in df.columns


class TestSBSImporter:
    """Test cases for SBSImporter"""

    def test_import_file_success(self, config_manager, tmp_path, mock_sbs_content):
        """Test successful SBS file import"""
        sbs_file = tmp_path / "0256-3184P31885.sbs"
        sbs_file.write_text(mock_sbs_content)

        importer = SBSImporter(config_manager)
        df = importer.import_file(str(tmp_path))

        assert not df.empty
        assert 'shot_point' in df.columns
        assert len(df) == 2

    def test_import_file_from_processed_folder(self, config_manager, tmp_path, mock_sbs_content):
        """Test import when called from Processed subfolder"""
        # Create Processed subfolder
        processed_folder = tmp_path / "Processed"
        processed_folder.mkdir()

        # Put SBS file in parent directory
        sbs_file = tmp_path / "0256-3184P31885.sbs"
        sbs_file.write_text(mock_sbs_content)

        importer = SBSImporter(config_manager)
        # Call with Processed folder path - should go up one level
        df = importer.import_file(str(processed_folder))

        assert not df.empty
        assert 'shot_point' in df.columns

    def test_import_file_no_matching_file(self, config_manager, tmp_path):
        """Test handling when no SBS file found"""
        importer = SBSImporter(config_manager)
        df = importer.import_file(str(tmp_path))

        assert df.empty

    def test_column_renaming(self, config_manager, tmp_path, mock_sbs_content):
        """Test that 'Shot' column is renamed to 'shot_point'"""
        sbs_file = tmp_path / "0256-3184P31885.sbs"
        sbs_file.write_text(mock_sbs_content)

        importer = SBSImporter(config_manager)
        df = importer.import_file(str(tmp_path))

        assert 'shot_point' in df.columns
        assert 'Shot' not in df.columns


class TestDataImporterBase:
    """Test cases for base DataImporter class"""

    def test_cannot_instantiate_abstract_class(self, config_manager):
        """Test that DataImporter cannot be instantiated directly"""
        with pytest.raises(TypeError):
            DataImporter(config_manager)

    def test_all_importers_have_import_file_method(self, config_manager):
        """Test that all importer classes implement import_file method"""
        importers = [
            SPSImporter(config_manager),
            SPSCompImporter(config_manager),
            EOLImporter(config_manager),
            ASCImporter(config_manager),
            SBSImporter(config_manager)
        ]

        for importer in importers:
            assert hasattr(importer, 'import_file')
            assert callable(getattr(importer, 'import_file'))

    def test_all_importers_return_dataframe(self, config_manager, tmp_path):
        """Test that all importers return DataFrame objects"""
        # Create necessary directories
        processed_folder = tmp_path / "Processed"
        processed_folder.mkdir()

        importers = [
            SPSImporter(config_manager),
            SPSCompImporter(config_manager),
            EOLImporter(config_manager),
            ASCImporter(config_manager),
            SBSImporter(config_manager)
        ]

        for importer in importers:
            result = importer.import_file(str(tmp_path))
            assert isinstance(result, pd.DataFrame)