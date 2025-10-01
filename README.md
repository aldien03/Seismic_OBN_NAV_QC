# PXGEONavQC - Navigation Quality Control Tool

A PyQt5-based GUI application for navigation quality control (NAV QC) operations in seismic data acquisition for marine surveys.

**Version**: 2.4.0
**Author**: aldien03@gmail.com
**Project**: Petrobras Seismic Survey NAV QC

---

## Overview

PXGEONavQC is a comprehensive tool for quality control of navigation and source data in seismic surveys. The application provides:

- **File Management**: Automated file renaming with regex patterns
- **Shot Point Verification**: Count and validate shot points across multiple file types
- **Quality Control**: Comprehensive QC checks on navigation and source data
- **Data Merging**: Combine SPS, EOL reports, gun data, and SBS files
- **Line Log Updates**: Automatic updates to Excel line log files
- **Database Output**: Generate CSV database files with QC flags

---

## Features

### 1. File Renaming
- Rename RAW files (`.p190`, `.p294`, `.S00`, `.p211`, `.mfa`, `.pdf`, `.sbs`, `.sts`)
- Rename Processed files (`.csv`, `.pdf`, `.S01`, `.P111`, `.P190`)
- Configurable regex patterns via `config.ini`
- Standardized naming: `0256-YYYYPXXXXX.ext` format
- Skip already-compliant files

### 2. Shot Point Verification
- Count shot points in multiple file types
- Verify data completeness across files
- Report line counts for `.p190`, `.p294`, `.S00`, `.p211`
- Display verification results in GUI

### 3. Quality Control Checks
- **STI (Shot Time Interval)**: Error and warning thresholds
- **Gun Depth**: Min/max depth validation
- **Gun Pressure**: Pressure range checks
- **Sub-array Separation**: Minimum separation validation
- **COS (Center of Source)**: Distance thresholds for Dual/Triple source
- **Position Accuracy**: Crossline, radial, and SMA limits
- **Timing**: Warning and error thresholds
- **Consecutive Errors**: Flag sequences exceeding limit
- **Responsive UI**: Background threading keeps interface responsive during QC (Phase 5)

### 4. Data Processing
- Import and merge multiple data sources:
  - SPS files (`.S01`)
  - EOL reports (`.csv`)
  - Gun data (`.asc`)
  - SBS files (`.sbs`)
- Apply QC thresholds from configuration
- Generate comprehensive flags for each shot point
- Export merged data to database CSV

### 5. Reporting
- Update `.S01` files with extended QC flags
- Update Excel line log files (`.xlsm`) with:
  - Shot point ranges
  - First/last shot timestamps
  - QC compliance percentages
  - Acquisition comments
- Generate timestamped database CSV files

---

## Installation

### Requirements
- Python 3.12+
- PyQt5 ≥5.15.0
- pandas ≥1.3.0
- numpy ≥1.21.0
- openpyxl ≥3.0.9
- PyMuPDF ≥1.19.0

### Setup

1. **Clone or extract the project:**
   ```bash
   cd PXGEONavQC_Version23
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv pxgeo_venv
   source pxgeo_venv/bin/activate  # Linux/Mac
   # OR
   pxgeo_venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure settings:**
   Edit `config.ini` to set:
   - Source type (Dual or Triple)
   - QC thresholds
   - File naming patterns
   - Database output paths

---

## Building Standalone Executable

Create a standalone `.exe` file that can run without Python installed.

### Prerequisites

Install PyInstaller:
```bash
pip install pyinstaller
```

### Build Steps

1. **Using PyInstaller spec file (recommended):**

   The project includes a pre-configured `PXGEONavQC.spec` file with:
   - Icon configuration (`icon.png`)
   - Hidden imports (`config_manager`)
   - Data files (`config.ini`, `icon.png`)
   - Optimized build settings

   ```bash
   pyinstaller PXGEONavQC.spec
   ```

2. **Manual build command (alternative):**
   ```bash
   pyinstaller --onefile --windowed --icon=icon.png --name=PXGEONavQC --add-data "config.ini:." --hidden-import=config_manager PXGEONavQCTools_P211_Petrobras.py
   ```

   **Note**: On Linux/Mac, use `:` separator. On Windows, use `;` separator for `--add-data`

### Build Options Explained

- `--onefile`: Package everything into a single executable
- `--windowed`: No console window (GUI only)
- `--icon=icon.png`: Use icon.png as application icon
- `--name=PXGEONavQC`: Output executable name
- Can also use `--add-data` to include config.ini if needed

### Output Location

After building, the executable will be in:
```
dist/PXGEONavQC.exe  (Windows)
dist/PXGEONavQC      (Linux/Mac)
```

### Distribution Package

To distribute the application, include:
- `PXGEONavQC.exe` (from dist folder)
- `config.ini` (configuration file)
- `icon.png` (optional, for reference)

**Note**: The executable must be in the same directory as `config.ini` to run properly.

### Testing the Executable

1. Copy the executable from `dist/` folder
2. Place it in a folder with `config.ini`
3. Double-click to run (Windows) or execute from terminal (Linux/Mac)
4. Verify all features work as expected

---

## Usage

### Running the Application

**From Python:**
```bash
python PXGEONavQCTools_P211_Petrobras.py
```

**From Executable:**
```bash
# Windows
PXGEONavQC.exe

# Linux/Mac
./PXGEONavQC
```

### Workflow

#### 1. Browse Directories
- **Production Directory**: Select folder containing RAW and Processed subfolders
- **GunData Directory**: Select folder containing gun/source data (`.asc` files)

#### 2. Rename Files
- **Rename RAW Files**: Click to standardize RAW file names
- **Rename Processed Files**: Click to standardize Processed file names
- Review renaming report showing renamed, compliant, and missing files

#### 3. Verify Shot Points
- Click "Verify Shot Points" to count shot points in data files
- Review counts for `.p190`, `.p294`, `.S00`, `.p211` files
- Verify consistency across file types

#### 4. Run QC Checks
- Click "QC Files" to start quality control process
- Application will:
  1. Import SPS files (`.S01`)
  2. Import EOL reports (`.csv`)
  3. Import gun data (`.asc`)
  4. Import SBS files (`.sbs`)
  5. Merge all data sources
  6. Apply QC thresholds
  7. Generate flags for each shot point
  8. Calculate consecutive error sequences

#### 5. Review Results
- View QC summary in message dialogs
- Check generated database CSV in output directory
- Review updated line log files (`.xlsm`)
- Verify updated SPS files with extended flags

---

## Configuration

### config.ini Structure

The application is driven by `config.ini` with the following sections:

#### [General]
```ini
source_option = Triple  # or "Dual"
```

#### [QC_Thresholds]
Configure all QC limits:
- STI (Shot Time Interval) thresholds
- Gun depth and pressure ranges
- Sub-array separation minimum
- COS distance thresholds
- Position accuracy limits
- Timing thresholds
- Consecutive error limit

Example:
```ini
sti_error_threshold = 6.0
gun_depth_min = -8.0
gun_depth_max = -6.0
crossline_limit = 10.0
```

#### [Rename_Raw_Files] & [Rename_Processed_Files]
Define regex patterns for file renaming:
```ini
p190_pattern = ^(\d{4}[A-Z]\d)(\d{4})\.0\.p190$ -> 0256-\1\2.p190
```

#### [Database]
Set output paths:
```ini
primary_db_path = N:\30_SWAT_DBB
fallback_db_path = C:\SWAT_DB_Local
```

See `config.ini` for complete configuration options.

---

## File Structure

```
PXGEONavQC_Version23/
├── PXGEONavQCTools_P211_Petrobras.py  # Main application (GUI orchestrator - 882 lines)
│
├── Core Modules (Phase 4 Refactoring):
│   ├── config_manager.py              # Configuration management (89 lines)
│   ├── data_importers.py              # All data importers (445 lines)
│   ├── qc_validator.py                # QC validation engine (878 lines)
│   ├── file_renamer.py                # File renaming operations (257 lines)
│   ├── shot_point_verifier.py         # Shot point verification (153 lines)
│   ├── database_operations.py         # Database CSV output (216 lines)
│   ├── line_log_manager.py            # Excel line log operations (338 lines)
│   ├── qc_report_generator.py         # QC report generation (540 lines)
│   └── gui_helpers.py                 # GUI utilities and threading (Phase 5)
│
├── config.ini                          # Configuration file
├── requirements.txt                    # Python dependencies
├── README.md                           # This file
├── icon.png                            # Application icon
├── nav_qc.log                          # Runtime log
│
├── tests/                              # Test suite
│   ├── unit/                          # Unit tests
│   │   ├── test_config_manager.py    # Config tests (12 tests, 89.74% coverage)
│   │   └── test_data_importers.py    # Importer tests (20 tests, 85.96% coverage)
│   └── integration/                   # Integration tests (17 tests)
│
└── Sample/                            # Sample data
    ├── GunData/                       # Gun/source data
    └── Production/                    # Navigation data
```

---

## Data Flow

```
Production Directory
    ├── RAW Files (.p190, .p294, .S00, .p211, etc.)
    └── Processed/
        ├── SPS Files (.S01)
        ├── EOL Reports (.csv)
        └── Other processed files

GunData Directory
    └── Gun data files (.asc)

                    ↓

            File Renaming
      (Standardize file names)

                    ↓

          Data Import & Merge
    SPSImporter → SPS files (.S01)
    SPSCompImporter → SPS comparison CSV
    EOLImporter → EOL reports (.csv)
    ASCImporter → Gun data (.asc)
    SBSImporter → Source data (.sbs)

                    ↓

           Apply QC Thresholds
         (Flag errors/warnings)

                    ↓

              Generate Outputs
    ├── Database CSV (merged data)
    ├── Updated SPS files (with flags)
    └── Updated Line Logs (summary)
```

---

## QC Flags

The application generates the following flags:

- **sti_flag**: Shot Time Interval violations
- **gun_depth_flag**: Gun depth out of range
- **gun_pressure_flag**: Gun pressure out of range
- **sub_array_sep_flag**: Sub-array separation too small
- **cos_flag**: Center of Source distance violations
- **crossline_flag**: Crossline offset exceeds limit
- **radial_flag**: Radial offset exceeds limit
- **sma_flag**: Semi-major axis exceeds limit
- **timing_flag**: Timing deviation warnings/errors
- **consecutive_error_flag**: Sequential errors exceed threshold

Each flag can be:
- **OK**: Within acceptable range
- **WARNING**: In warning range
- **ERROR**: Outside acceptable limits

---

## Output Files

### Database CSV
- **Location**: Configured in `[Database]` section
- **Format**: `0256-YYYYPXXXXX_DB_YYYYMMDD_HHMMSS.csv`
- **Contents**: Merged data with all QC flags and shot point information

### Updated SPS Files
- **Location**: Production/Processed directory
- **Format**: Same as input `.S01` files
- **Changes**: Extended flags column updated with QC results

### Updated Line Logs
- **Location**: Production directory
- **Format**: `.xlsm` Excel files
- **Updates**:
  - Shot point range
  - First/last shot timestamps
  - QC compliance percentages
  - Acquisition comments

---

## Logging

Application logs are written to `nav_qc.log` in the project directory.

Log level: **DEBUG**

Logs include:
- Configuration loading
- File operations
- Data import progress
- QC check results
- Error messages and warnings

---

## Troubleshooting

### Config file not found
**Error**: "Config file not found: config.ini"
**Solution**: Ensure `config.ini` exists in the project directory

### PyMuPDF import error
**Error**: "module 'fitz' has no attribute..."
**Solution**: Ensure PyMuPDF is properly installed:
```bash
pip uninstall PyMuPDF
pip install PyMuPDF
```

### File renaming issues
**Problem**: Files not being renamed
**Solution**:
- Check regex patterns in `config.ini`
- Verify files match expected naming convention
- Review log file for specific errors

### QC threshold violations
**Problem**: Too many error flags
**Solution**:
- Review and adjust thresholds in `[QC_Thresholds]` section
- Verify input data quality
- Check if thresholds match project specifications

### Database output not created
**Problem**: No CSV file generated
**Solution**:
- Check `primary_db_path` in `config.ini`
- Verify write permissions for output directory
- Check if fallback path is accessible

---

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_config_manager.py -v
```

### Code Structure

The application follows a clean modular architecture (Phase 4 Complete):

#### Core Modules
- **ConfigManager** (`config_manager.py`): Centralized configuration management
- **Data Importers** (`data_importers.py`): SPSImporter, SPSCompImporter, EOLImporter, ASCImporter, SBSImporter
- **QCValidator** (`qc_validator.py`): Comprehensive QC validation engine with 15+ checks
- **FileRenamer** (`file_renamer.py`): File renaming with regex patterns
- **ShotPointVerifier** (`shot_point_verifier.py`): Shot point counting and verification
- **DatabaseManager** (`database_operations.py`): Database CSV output with fallback
- **LineLogManager** (`line_log_manager.py`): Excel line log updates
- **QCReportGenerator** (`qc_report_generator.py`): QC report generation and analysis
- **MainWindow** (`PXGEONavQCTools_P211_Petrobras.py`): PyQt5 GUI orchestration

#### Architecture Benefits
- **Separation of Concerns**: Each module has a single, well-defined responsibility
- **Testability**: Modules can be tested independently
- **Maintainability**: Easy to locate and modify specific functionality
- **Code Reduction**: Main application reduced from 2472 to 882 lines (-64.3%)

### Adding New Features

1. Update `config.ini` with new settings
2. Add business logic to appropriate class/module
3. Update GUI in `MainWindow` class
4. Write unit tests for new functionality
5. Update this README

---

## Version History

### Version 2.4 (Current)
- **Phase 5: GUI Improvements (Complete)**
  - **Threading & Responsiveness**: QC operations now run in background threads
    - UI remains fully responsive during processing
    - Progress bars update smoothly without freezing
    - Cancel operation support (graceful termination)
  - **Progress Dialogs**: Real-time feedback for long-running operations
    - File renaming progress with file counts
    - QC processing stages (import → merge → validate → report)
    - Percentage-based progress tracking
  - **Enhanced Error Handling**:
    - Detailed error dialogs with user-friendly messages
    - Graceful fallback for database path failures
    - Qt signal/slot pattern for thread-safe GUI updates
  - **GUI Helper Module**: New `gui_helpers.py` module (Phase 5.2)
    - `ProgressDialog` class with cancel support
    - `QCWorkerThread` for background QC operations
    - `show_error_dialog()` and `show_info_dialog()` utilities
  - **Bug Fixes**:
    - Fixed database path configuration (Phase 5 hotfix)
    - Fixed Qt threading violations causing crashes (Phase 5 hotfix)
    - Enhanced debug logging for troubleshooting

- **Phase 8: Performance Analysis (Complete)**
  - Comprehensive profiling of QC validation performance
  - Results: **774,800 rows/second** throughput (excellent)
  - Conclusion: No optimization needed - performance exceeds requirements by 1.5-8x
  - Created `profile_performance.py` for future performance monitoring

- **Phase 7: Testing Infrastructure (Complete)**
  - 190 total tests (55 unit + 135 integration tests)
  - Test coverage: 51.49% overall
    - config_manager.py: 89.74%
    - data_importers.py: 85.96%
    - gui_helpers.py: 90.00%
  - Integration tests for full QC workflows

### Version 2.3
- **Phase 4 Modularization (Complete)**: Full architectural refactoring
  - Extracted 8 specialized modules from monolithic main file
  - Main application reduced from 2472 to 882 lines (-64.3%)
  - Modules created:
    1. `config_manager.py` - Configuration management (89 lines, 89.74% test coverage)
    2. `data_importers.py` - All data importers (445 lines, 85.96% test coverage)
    3. `qc_validator.py` - QC validation engine (878 lines)
    4. `file_renamer.py` - File renaming (257 lines)
    5. `shot_point_verifier.py` - Shot point verification (153 lines)
    6. `database_operations.py` - Database operations (216 lines)
    7. `line_log_manager.py` - Line log management (338 lines)
    8. `qc_report_generator.py` - Report generation (540 lines)
  - Enhanced QC specifications:
    - Sub-array separation with percentage and average checks
    - Gun depth sensor validation (dynamic sensor discovery)
    - Consecutive error pattern detection (sliding windows: 7, 12/24, 16/40, 3% total)
  - Benefits: Improved testability, maintainability, and code clarity

- **Phase 3**: Removed dead code (19% reduction)
- Improved config.ini clarity and organization
- Fixed PyMuPDF import compatibility
- Fixed shot_dither column conversion bug
- Added comprehensive test suite (49 tests: 20 importer + 12 config + 17 integration)
- Improved documentation (CLAUDE.md, README.md)

### Version 2.2
- Added test infrastructure (pytest, coverage)
- Removed FTP fetch functionality
- Code cleanup and optimization

### Version 2.0
- Refactored from monolithic to modular design
- Configuration-driven architecture
- Improved error handling

---

## License

Internal tool for Petrobras seismic survey operations.

---

## Support

For issues or questions:
- Email: aldien03@gmail.com
- Check `nav_qc.log` for detailed error messages
- Review `CLAUDE.md` for developer guidance

---

## Acknowledgments

- Developed for Petrobras marine seismic survey operations
- Built with PyQt5, pandas, and numpy

- Refactored with assistance from Claude Code (Anthropic)
