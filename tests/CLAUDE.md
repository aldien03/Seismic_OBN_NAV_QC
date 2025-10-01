# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PXGEONavQC** is a PyQt5-based GUI application for navigation quality control (NAV QC) operations in seismic data acquisition. The tool handles file fetching from FTP servers, file renaming, shot point verification, and comprehensive QC checks on navigation and source data for marine seismic surveys (specifically Petrobras projects).

## Environment Setup

### Python Virtual Environment
The project uses Python 3.12 with a virtual environment:

```bash
# Activate virtual environment (choose based on which is active)
source pxgeo_venv/bin/activate   # OR
source sanco_venv/Scripts/activate  # Windows-style venv
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

**Core Dependencies:**
- PyQt5 ≥5.15.0 (GUI framework)
- pandas ≥1.3.0 (data processing)
- numpy ≥1.21.0 (numerical operations)
- openpyxl ≥3.0.9 (Excel file operations)
- PyMuPDF ≥1.19.0 (PDF processing - imported as `pymupdf` in newer versions)

### Running the Application
```bash
python PXGEONavQCTools_P211_Petrobras.py
```

### Building Executable (PyInstaller)
```bash
pyinstaller PXGEONavQC.spec
```

## Architecture

### Modular Design (Phase 4 Refactoring - Complete)
The application follows a clean modular architecture with separation of concerns. The main application (882 lines) serves as a GUI orchestrator, delegating all business logic to specialized modules.

### Configuration-Driven Design
The entire application is driven by `config.ini`, which centralizes:
- File renaming regex patterns (RAW and Processed files)
- QC thresholds (shot timing intervals, gun depths, crossline limits, etc.)
- Database output paths
- Line log update settings
- Data import configurations
- Dither reference file path (for missing dither detection and suggestion)

**Critical:** All threshold values, regex patterns, and paths are in `config.ini`. Never hardcode these values in the Python code.

### Core Modules

#### 1. **ConfigManager** (`config_manager.py` - 89 lines)
   - Loads and validates `config.ini`
   - Central access point for all configuration
   - Helper methods: get(), getfloat(), getint(), getboolean(), items()
   - Test coverage: 89.74%

#### 2. **Data Importers** (`data_importers.py` - 445 lines)
   - **SPSImporter**: Import SPS (.S01) files with fixed-width format (194 header rows)
   - **SPSCompImporter**: Import SPS comparison CSV files
   - **EOLImporter**: Import EOL report CSV files
   - **ASCImporter**: Import ASC gun data files (gun timing/depth/pressure)
   - **SBSImporter**: Import SBS source data files
   - **Base class**: DataImporter(ABC) for common functionality
   - Test coverage: 85.96%

#### 3. **QCValidator** (`qc_validator.py` - 878 lines)
   - Comprehensive QC validation engine
   - Validates: STI, sub-array separation, COS distance, volume, gun depth, gun pressure, gun timing, position accuracy, SMA
   - Advanced checks: Gun depth sensors, consecutive error windows (7, 12/24, 16/40), percentage thresholds
   - Generates comprehensive line log reports
   - Supports both Dual and Triple source configurations

#### 4. **FileRenamer** (`file_renamer.py` - 257 lines)
   - Renames RAW files (.p190, .p294, .S00, .p211, .mfa, .pdf, .sbs, .sts)
   - Renames Processed files (.csv, .pdf, .S01, .P111, .P190)
   - Pattern validation and error handling
   - Tracks renamed, compliant, and missing files
   - Uses regex patterns from `[Rename_Raw_Files]` and `[Rename_Processed_Files]` sections

#### 5. **ShotPointVerifier** (`shot_point_verifier.py` - 153 lines)
   - Counts shot points across multiple file types
   - Verifies data consistency (.p190, .p294, .S00, .p211)
   - Pattern-based counting (S, E1000, E2)
   - Missing file detection and reporting

#### 6. **DatabaseManager** (`database_operations.py` - 216 lines)
   - Handles database CSV output generation
   - Primary and fallback path resolution
   - Sequence and line name extraction from DataFrame
   - File verification (existence, size)
   - Comprehensive error handling

#### 7. **LineLogManager** (`line_log_manager.py` - 338 lines)
   - Excel (.xlsm) line log operations
   - File discovery with regex pattern matching
   - Workbook operations with retry logic for locked files
   - Date and FGSP/LGSP updates
   - QC comments generation and formatting
   - Label mapping for all QC check types

#### 8. **QCReportGenerator** (`qc_report_generator.py` - 607 lines)
   - Shot point sorting validation (ascending/descending sequences)
   - Dither value checking with pattern-matching suggestions from reference file
   - Missing dither detection and suggested correct values (non-modifying)
   - Flag discrepancy detection (Seispos vs script-generated)
   - Missing Seispos flags detection
   - Error percentage calculations for all QC flags
   - Comprehensive shot point logging with gun details
   - Concise popup reports (limits output for bad lines)
   - Marker timing validation (FGSP, LGSP, FOSP, LOSP - FASP excluded)

#### 9. **MainWindow** (GUI) (`PXGEONavQCTools_P211_Petrobras.py` - 882 lines)
   - PyQt5-based interface
   - Orchestrates all operations
   - Delegates to specialized modules
   - Key actions:
     - Browse directories (Production/GunData)
     - Rename RAW/Processed files (FileRenamer)
     - Run QC checks (QCValidator)
     - Verify shot points (ShotPointVerifier)
     - Generate reports (QCReportGenerator)
     - Update line logs (LineLogManager)
     - Save to database (DatabaseManager)

### Data Flow

```
User browses directories via MainWindow (GUI)
    ↓
FileRenamer standardizes filenames → 0256-YYYYPXXXXX.ext format
    ↓
QC Process (orchestrated by MainWindow):
    1. Import SPS files (.S01) → SPSImporter (data_importers.py)
    2. Import SPS comparison CSV → SPSCompImporter (data_importers.py)
    3. Import EOL reports (.csv) → EOLImporter (data_importers.py)
    4. Import ASC files (.asc from GunData) → ASCImporter (data_importers.py)
    5. Import SBS files (.sbs) → SBSImporter (data_importers.py)
    6. Merge into single DataFrame → MainWindow
    7. Apply QC validation → QCValidator (qc_validator.py)
       - Validates all thresholds from config.ini
       - Flags errors/warnings (STI, gun depth, crossline, etc.)
       - Generates line log report data
    8. Calculate error percentages → QCReportGenerator (qc_report_generator.py)
    9. Generate QC reports → QCReportGenerator (qc_report_generator.py)
       - Shot point sorting validation
       - Dither value checking
       - Flag discrepancy detection
    10. Save to database CSV → DatabaseManager (database_operations.py)
    11. Update line log .xlsm → LineLogManager (line_log_manager.py)
    ↓
Output: N:\30_SWAT_DB\XXXX_XXXX_DB.csv
```

### File Naming Conventions

**RAW Files:**
- Input: `YYYYPXNNNN.0.p190` → Output: `0256-YYYYPXNNNN.p190`
- Input: `SNNNN.YYYYPXNNNN.000.pdf` → Output: `0256-YYYYPXNNNN_EOL_gator.pdf`

**Processed Files:**
- Input: `seqNNNN_NNN_YYYYPXNNNN_EOL_report.csv` → Output: `0256-YYYYPXNNNN_EOL_report.csv`
- Input: `YYYYPXNNNN.P190` → Output: `0256-YYYYPXNNNN.P190`

Where:
- `YYYY` = 4-digit identifier
- `P` = Letter code
- `X` = Single digit
- `NNNN` = 4-digit sequence number

### QC Thresholds (from config.ini)

Key thresholds read from `[QC_Thresholds]`:
- STI (Shot Time Interval): Error < 6.0s, Warning 6.175-10.0s
- Sub-array separation: Min 6.8m
- Gun depth: -8.0m to -6.0m
- Gun pressure: 1900-2100 PSI
- Volume nominal: 3040 cu.in
- Crossline/Radial limits: 10.0m
- SMA limit: 3.0m
- Consecutive error limit: 25 shot points

Source mode (Dual/Triple) is set in `[General] → source_option`

### Directory Structure

```
PXGEONavQC_Version23/
├── PXGEONavQCTools_P211_Petrobras.py  # Main application (GUI orchestrator - 882 lines)
├── config.ini                          # Configuration file
├── requirements.txt                    # Python dependencies
├── PXGEONavQC.spec                    # PyInstaller spec
├── icon.png                           # Application icon
├── nav_qc.log                         # Runtime log file
│
├── Core Modules (Phase 4 Refactoring):
│   ├── config_manager.py              # Configuration management (89 lines)
│   ├── data_importers.py              # All data importers (445 lines)
│   ├── qc_validator.py                # QC validation engine (878 lines)
│   ├── file_renamer.py                # File renaming operations (257 lines)
│   ├── shot_point_verifier.py         # Shot point verification (153 lines)
│   ├── database_operations.py         # Database CSV output (216 lines)
│   ├── line_log_manager.py            # Excel line log operations (338 lines)
│   └── qc_report_generator.py         # QC report generation (540 lines)
│
├── pxgeo_venv/                        # Python virtual environment
├── sanco_venv/                        # Alternative virtual environment
└── Sample/                            # Sample data structure
    ├── GunData/                       # Gun/source data (.asc, PDFs)
    │   └── 3184P31885/
    └── Production/                    # Navigation data
        └── 3184P31885/
            ├── (RAW files: .p190, .p294, .S00, .p211, .mfa, .pdf, .sbs, .sts)
            ├── 0256-XXXX_Nav_LineLog.xlsm
            └── Processed/
                ├── (Processed SPS: .S01, .P111, .P190)
                └── (Reports: _EOL_report.csv, _SPS_Comp.csv, etc.)
```

## Key Configuration Points

### Adding New Regex Patterns
Edit `config.ini` sections `[Rename_Raw_Files]` or `[Rename_Processed_Files]`:
```ini
new_pattern = ^regex_search$ -> replacement_pattern
```

### Adjusting QC Thresholds
Modify values in `[QC_Thresholds]` section without touching Python code.

### FTP Server Configuration
Two servers configured in `[Server1]` and `[Server2]`:
```ini
[Server1]
host = 192.168.73.31
raw_p190_path = /remote/path -> .p190
```

### Database Output
Primary: `N:\30_SWAT_DBB` (network)
Fallback: `C:\SWAT_DB_Local` (local)

## Logging

Application logs to `nav_qc.log` in project root with DEBUG level.

## Important Notes

- The application is designed for read-only FTP access with specific exemptions
- All file operations are logged extensively
- The tool handles both Dual and Triple source configurations
- Line log updates require `.xlsm` files and preserve existing data
- Database CSV files are timestamped and contain comprehensive QC flags
- Sample data is provided in `Sample/` directory showing expected file structure

## Development History

### Phase 4: Modularization (Complete)
- **Objective**: Extract all business logic from main application into dedicated modules
- **Result**: Main application reduced from 2472 lines to 882 lines (-64.3%)
- **Modules Created**: 8 specialized modules for different concerns
- **Benefits**:
  - Improved testability and maintainability
  - Clear separation of concerns
  - Easier to understand and modify
  - Main app focuses on GUI orchestration only

### Known Issues & Fixes

#### PyMuPDF Import (Fixed in Phase 3)
- **Issue**: PyMuPDF 1.26.4+ changed import from `import fitz` to `import pymupdf`
- **Fix**: Use `import pymupdf as fitz` to maintain backward compatibility
- **Location**: Main application file

## Testing

### Module Import Test
All 8 core modules have been tested for successful import:
```bash
python3 << 'EOF'
modules = ['config_manager', 'data_importers', 'qc_validator',
           'file_renamer', 'shot_point_verifier', 'database_operations',
           'line_log_manager', 'qc_report_generator']
for module in modules:
    __import__(module)
    print(f"✓ {module}")
EOF
```

### Test Coverage
- **ConfigManager**: 89.74%
- **Data Importers**: 85.96%
- Other modules: Tests to be added