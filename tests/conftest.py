"""
pytest configuration and fixtures for PXGEONavQC tests.

This module provides shared fixtures for all tests.
"""

import os
import sys
from pathlib import Path

import pytest

# Add parent directory to path so we can import the main module
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def sample_data_dir(project_root):
    """Return the Sample data directory path."""
    sample_dir = project_root / "Sample"
    assert sample_dir.exists(), f"Sample directory not found: {sample_dir}"
    return sample_dir


@pytest.fixture(scope="session")
def sample_production_dir(sample_data_dir):
    """Return the Sample production directory with sequence 3184P31885."""
    prod_dir = sample_data_dir / "Production" / "3184P31885"
    assert prod_dir.exists(), f"Production directory not found: {prod_dir}"
    return prod_dir


@pytest.fixture(scope="session")
def sample_processed_dir(sample_production_dir):
    """Return the Sample processed files directory."""
    proc_dir = sample_production_dir / "Processed"
    assert proc_dir.exists(), f"Processed directory not found: {proc_dir}"
    return proc_dir


@pytest.fixture(scope="session")
def sample_gundata_dir(sample_data_dir):
    """Return the Sample GunData directory."""
    gun_dir = sample_data_dir / "GunData" / "3184P31885"
    assert gun_dir.exists(), f"GunData directory not found: {gun_dir}"
    return gun_dir


@pytest.fixture(scope="session")
def config_file(project_root):
    """Return the config.ini file path."""
    config_path = project_root / "config.ini"
    assert config_path.exists(), f"Config file not found: {config_path}"
    return config_path


@pytest.fixture(scope="session")
def sample_files(sample_production_dir, sample_processed_dir, sample_gundata_dir):
    """
    Return a dictionary of all sample file paths organized by type.

    Returns:
        dict: File paths organized by category
    """
    return {
        "raw": {
            "p190": sample_production_dir / "0256-3184P31885.p190",
            "p294": sample_production_dir / "0256-3184P31885.p294",
            "s00": sample_production_dir / "0256-3184P31885.S00",
            "p211": sample_production_dir / "0256-3184P31885.p211",
            "mfa": sample_production_dir / "0256-3184P31885.mfa",
            "sbs": sample_production_dir / "0256-3184P31885.sbs",
            "sts": sample_production_dir / "0256-3184P31885.sts",
        },
        "processed": {
            "s01": sample_processed_dir / "0256-3184P31885.S01",
            "s01_alt": sample_processed_dir / "0256-3184P31885.0.S01",
            "p190": sample_processed_dir / "0256-3184P31885.P190",
            "p111": sample_processed_dir / "0256-3184P31885.P111",
            "sps_comp": sample_processed_dir / "0256-3184P31885_SPS_Comp.csv",
            "eol_report": sample_processed_dir / "0256-3184P31885_EOL_report.csv",
            "string_sep": sample_processed_dir / "0256-3184P31885_String_Sep_SPR.csv",
            "sps_point_depth": sample_processed_dir / "0256-3184P31885_SPS_Point_Depth.csv",
        },
        "gundata": {
            "asc": sample_gundata_dir / "0256-3184P31885.asc",
        },
    }


@pytest.fixture(scope="function")
def qapp(qapp_args):
    """
    Fixture that provides a QApplication instance for GUI tests.

    Uses pytest-qt's qapp fixture with custom arguments.
    """
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(qapp_args)

    yield app

    # Cleanup
    app.processEvents()


@pytest.fixture(scope="function")
def qapp_args():
    """Arguments for QApplication."""
    return []


@pytest.fixture(autouse=True)
def reset_qapp_state(qapp):
    """Reset QApplication state before each test."""
    if qapp:
        qapp.processEvents()
    yield
    if qapp:
        qapp.processEvents()


# Markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests for full workflows")
    config.addinivalue_line("markers", "slow: Tests that take significant time to run")
    config.addinivalue_line("markers", "requires_gui: Tests that require GUI/display")
    config.addinivalue_line("markers", "requires_sample_data: Tests that use Sample directory data")