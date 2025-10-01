#!/usr/bin/env python3
"""
PXGEONavQC - Navigation Quality Control Tool

A PyQt5-based GUI application for navigation quality control operations in seismic data acquisition.

Main Features:
- File renaming with configurable regex patterns
- Shot point verification and counting
- Comprehensive NAV QC checks (STI, gun depth, pressure, position accuracy)
- Data merging (SPS, EOL, gun data, SBS files)
- Line log updates and database output

Author: aldien03@gmail.com
Version: 2.4.0
Project: Petrobras Seismic Survey NAV QC

For detailed documentation, see README.md and USER_MANUAL.md
For developer guidance, see CLAUDE.md
For configuration help, see config.ini
"""

import sys
import os
import re
import logging
import shutil
import time
import datetime
import configparser
import pymupdf as fitz
import pandas as pd
import openpyxl
import numpy as np
from io import StringIO
from config_manager import ConfigManager
from data_importers import (
    SPSImporter, SPSCompImporter, EOLImporter,
    ASCImporter, SBSImporter
)
from qc_validator import QCValidator
from file_renamer import FileRenamer
from shot_point_verifier import ShotPointVerifier
from database_operations import DatabaseManager
from line_log_manager import LineLogManager
from qc_report_generator import QCReportGenerator
from openpyxl.styles import Alignment
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QFileDialog, QLabel, QFrame, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ftplib import FTP
from gui_helpers import ErrorDialog, ProgressDialog, QCWorkerThread


# -----------------------------------------------------------------------------
# Utility Classes/Functions
# -----------------------------------------------------------------------------

# FileRenamer class has been extracted to file_renamer.py module
# ShotPointVerifier class has been extracted to shot_point_verifier.py module


# -----------------------------------------------------------------------------
# Main GUI Class
# -----------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """
    Main GUI Window class for PXGEONavQCTools.
    Includes integrated functionality for:
    - Config management
    - FTP fetching & verifying shot points
    - Renaming RAW & Processed files
    - QC checks (merging data & updating line logs)
    """

    def __init__(self):
        """Initialize the MainWindow and load configuration."""
        super().__init__()

        # Setup logging for debugging
        logging.basicConfig(
            filename='nav_qc.log',
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Load config
        self.config_manager = ConfigManager()
        self.config_manager.load_config()
        self.config = self.config_manager.config

        # Create components
        self.file_renamer = FileRenamer(self.config)
        self.shot_point_verifier = ShotPointVerifier()
        self.database_manager = DatabaseManager(self.config)
        self.line_log_manager = LineLogManager(self.config)

        # Create data importers
        self.sps_importer = SPSImporter(self.config_manager)
        self.sps_comp_importer = SPSCompImporter(self.config_manager)
        self.eol_importer = EOLImporter(self.config_manager)
        self.asc_importer = ASCImporter(self.config_manager)
        self.sbs_importer = SBSImporter(self.config_manager)

        # Create QC validator
        self.qc_validator = QCValidator(self.config_manager)

        # Create QC report generator
        self.qc_report_generator = QCReportGenerator(self.config, self.sps_importer)

        self.setWindowTitle("Version 3.0 / chnav.star@sanco.no")
        self.setup_ui()

    # -------------------------------------------------------------------------
    # Setup UI
    # -------------------------------------------------------------------------
    def setup_ui(self):
        """
        Initialize the main layout and widgets, and connect signals to slots.
        """
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel("PXGEO/SANCO NAV QC Tools")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Setup Configuration Button
        setup_config_button = QPushButton("Setup Configuration")
        setup_config_button.clicked.connect(self.open_config_in_editor)
        main_layout.addWidget(setup_config_button)

        # Directory Selection
        dir_layout = QVBoxLayout()

        self.prod_dir_label = QLabel("No directory selected")
        browse_prod_dir_button = QPushButton("Browse Prod Dir")
        browse_prod_dir_button.clicked.connect(self.browse_prod_dir)
        prod_layout = QHBoxLayout()
        prod_layout.addWidget(browse_prod_dir_button)
        prod_layout.addWidget(self.prod_dir_label)
        dir_layout.addLayout(prod_layout)

        self.gundata_dir_label = QLabel("No directory selected")
        browse_gundata_dir_button = QPushButton("Browse GunData Dir")
        browse_gundata_dir_button.clicked.connect(self.browse_gundata_dir)
        gundata_layout = QHBoxLayout()
        gundata_layout.addWidget(browse_gundata_dir_button)
        gundata_layout.addWidget(self.gundata_dir_label)
        dir_layout.addLayout(gundata_layout)

        clear_path_button = QPushButton("Clear Path")
        clear_path_button.clicked.connect(self.clear_paths)
        dir_layout.addWidget(clear_path_button)

        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        dir_layout.addWidget(line1)

        main_layout.addLayout(dir_layout)

        # line2 = QFrame()
        # line2.setFrameShape(QFrame.HLine)
        # line2.setFrameShadow(QFrame.Sunken)
        # main_layout.addWidget(line2)

        # Rename Buttons
        batch_layout = QVBoxLayout()
        verify_shot_points_button = QPushButton("1 - Verify Shot Points Count")
        verify_shot_points_button.clicked.connect(self._verify_shot_points)

        rename_raw_button = QPushButton("2 - Rename RAW files")
        rename_raw_button.clicked.connect(self.rename_raw_files)


        rename_processed_button = QPushButton("3 - Rename Processed files")
        rename_processed_button.clicked.connect(self.rename_processed_files)

        batch_layout.addWidget(verify_shot_points_button)
        batch_layout.addWidget(rename_raw_button)
        batch_layout.addWidget(rename_processed_button)

        main_layout.addLayout(batch_layout)

        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line3)

        # QC Files
        qc_files_button = QPushButton("4 - QC Files")
        qc_files_button.clicked.connect(self.nav_files_qc)
        main_layout.addWidget(qc_files_button)



        # Footer
        footer_label = QLabel("Sanco Star - 2025")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_font = QFont()
        footer_font.setItalic(True)
        footer_label.setFont(footer_font)
        main_layout.addWidget(footer_label)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    # -------------------------------------------------------------------------
    # UI Actions
    # -------------------------------------------------------------------------
    def open_config_in_editor(self):
        """
        Open the config.ini file in the default system editor.
        """
        config_path = os.path.abspath(self.config_manager.config_path)
        if os.path.isfile(config_path):
            try:
                if sys.platform.startswith('win'):
                    os.startfile(config_path)
                elif sys.platform.startswith('darwin'):
                    os.system(f"open '{config_path}'")
                else:
                    os.system(f"xdg-open '{config_path}'")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        else:
            QMessageBox.warning(self, "Not Found", "config.ini not found.")

    def browse_prod_dir(self):
        """
        Open a directory dialog to select the production directory.
        """
        logging.debug("Opening production directory selection dialog")
        dir_path = QFileDialog.getExistingDirectory(self, "Select Prod Directory")
        
        if dir_path:
            logging.info(f"Production directory selected: {dir_path}")
            # Get sequence number from last 4 digits of directory path
            sequence_number = dir_path[-4:]
            
            # Validate directory contents
            try:
                files = os.listdir(dir_path)
                logging.debug(f"Production directory contains {len(files)} items")
                
                # Validate sequence number format (must be 4 digits)
                if not sequence_number or not sequence_number.isdigit() or len(sequence_number) != 4:
                    QMessageBox.warning(self, "Invalid Directory",
                        "The selected directory must end with a valid 4-digit sequence number.")
                    return
                    
                self.sequence_number = sequence_number  # Store for later use
                self.prod_dir_label.setText(dir_path)
                logging.info(f"Sequence number extracted and stored: {sequence_number}")
                
            except PermissionError:
                logging.error(f"Permission denied accessing production directory: {dir_path}")
                QMessageBox.warning(self, "Access Error", "Permission denied accessing the selected directory.")
                return
            except Exception as e:
                logging.error(f"Error accessing production directory {dir_path}: {e}")
                QMessageBox.warning(self, "Error", f"Error accessing the selected directory: {str(e)}")
                return
        else:
            # Clear sequence number if no directory selected
            if hasattr(self, 'sequence_number'):
                delattr(self, 'sequence_number')
            self.prod_dir_label.setText("No directory selected")
            
        logging.debug(f"Production directory label updated to: {self.prod_dir_label.text()}")

    def browse_gundata_dir(self):
        """
        Open a directory dialog to select the GunData directory.
        """
        logging.debug("Opening GunData directory selection dialog")
        dir_path = QFileDialog.getExistingDirectory(self, "Select GunData Directory")
        
        if dir_path:
            logging.info(f"GunData directory selected: {dir_path}")
            # Validate directory contents
            try:
                files = os.listdir(dir_path)
                logging.debug(f"GunData directory contains {len(files)} items")
            except PermissionError:
                logging.error(f"Permission denied accessing GunData directory: {dir_path}")
                QMessageBox.warning(self, "Access Error", "Permission denied accessing the selected directory.")
                return
            except Exception as e:
                logging.error(f"Error accessing GunData directory {dir_path}: {e}")
                QMessageBox.warning(self, "Error", f"Error accessing the selected directory: {str(e)}")
                return
        
        # Update label even if cancelled (will show "No directory selected")
        self.gundata_dir_label.setText(dir_path if dir_path else "No directory selected")
        logging.debug(f"GunData directory label updated to: {self.gundata_dir_label.text()}")

    def clear_paths(self):
        """
        Clear any previously selected paths.
        """
        self.prod_dir_label.setText("No directory selected")
        self.gundata_dir_label.setText("No directory selected")

    # -------------------------------------------------------------------------
    # Fetch Files & Verify
    # -------------------------------------------------------------------------
    def _verify_shot_points(self):
        """
        Verify shot points in the production directory using ShotPointVerifier.
        """
        if not hasattr(self, 'prod_dir_label') or self.prod_dir_label.text() == "No directory selected":
            QMessageBox.warning(self, "Error", "Please select a production directory first.")
            return

        prod_dir = self.prod_dir_label.text()
        if not os.path.isdir(prod_dir):
            QMessageBox.warning(self, "Error", "Selected production directory does not exist.")
            return

        try:
            is_consistent, report = self.shot_point_verifier.verify_directory(prod_dir)
            
            # Show results with appropriate icon
            icon = QMessageBox.Information if is_consistent else QMessageBox.Warning
            QMessageBox.information(self, "Shot Point Verification", report)

        except Exception as e:
            logging.error(f"Shot point verification failed: {str(e)}")
            QMessageBox.critical(self, "Error", 
                f"Failed to verify shot points: {str(e)}\n\n"
                f"Please check the log file for details.")

    # -------------------------------------------------------------------------
    # Rename RAW & Processed
    # -------------------------------------------------------------------------
    def rename_raw_files(self):
        """
        Rename RAW files in the selected production directory using config patterns.
        """
        folder_path = self.prod_dir_label.text()
        if folder_path == "No directory selected" or not os.path.isdir(folder_path):
            QMessageBox.warning(self, "Warning", "Please select a valid Prod directory first.")
            return

        result = self.file_renamer.rename_files_in_directory(
            folder_path, "Rename_Raw_Files"
        )
        self._show_rename_result("RAW", *result)

    def rename_processed_files(self):
        """
        Rename Processed files in the 'Processed' sub-folder using config patterns.
        Also runs extra tasks like PDF page extraction and SPS copy.
        """
        folder_path = self.prod_dir_label.text()
        if folder_path == "No directory selected" or not os.path.isdir(folder_path):
            QMessageBox.warning(self, "Warning", "Please select a valid Prod directory first.")
            return

        processed_folder_path = os.path.join(folder_path, "Processed")
        if not os.path.exists(processed_folder_path) or not os.path.isdir(processed_folder_path):
            QMessageBox.warning(self, "Warning", "The 'Processed' sub-directory does not exist or is not valid.")
            return

        # Initialize tracking for extra files created
        self._extra_files_created = []

        result = self.file_renamer.rename_files_in_directory(
            processed_folder_path, "Rename_Processed_Files"
        )

        # Extra tasks - track created files
        try:
            created_file = self.extract_pdf_page_as_png(processed_folder_path, show_message=False)
            if created_file:
                self._extra_files_created.append(f"PDF Page 2 Extract: {os.path.basename(created_file)}")
        except Exception as e:
            logging.debug(f"Error in extract_pdf_page_as_png: {e}")

        try:
            created_file = self.copy_SPS_file_and_remove_headers(processed_folder_path, show_message=False)
            if created_file:
                self._extra_files_created.append(f"SPS Copy (no headers): {os.path.basename(created_file)}")
        except Exception as e:
            logging.debug(f"Error in copy_SPS_file_and_remove_headers: {e}")

        # Show combined result with extra files
        self._show_rename_result("Processed", *result)

    def _show_rename_result(self, label, renamed_count, already_compliant, missing_files, error_files):
        """
        Helper to display rename results in a formatted, user-friendly QMessageBox.

        Args:
            label (str): "RAW" or "Processed" for the UI title.
            renamed_count (int): Number of renamed files.
            already_compliant (int): Number of files that matched patterns but needed no rename.
            missing_files (list): Files that have recognized extensions but no matching regex pattern.
            error_files (list): Files that caused rename errors.
        """
        message_parts = []

        # Header with summary
        total_processed = renamed_count + already_compliant
        message_parts.append("=" * 60)
        message_parts.append(f"  {label} FILE RENAMING SUMMARY")
        message_parts.append("=" * 60)
        message_parts.append("")

        # Status summary with icons
        status_lines = []
        if renamed_count > 0:
            status_lines.append(f"✓ Renamed:           {renamed_count} file(s)")
        if already_compliant > 0:
            status_lines.append(f"✓ Already Compliant: {already_compliant} file(s)")
        if missing_files:
            status_lines.append(f"⚠ Not Matching:      {len(missing_files)} file(s)")
        if self.file_renamer.processed_files['missing_extensions']:
            status_lines.append(f"⚠ Missing Types:     {len(self.file_renamer.processed_files['missing_extensions'])} type(s)")
        if error_files:
            status_lines.append(f"✗ Errors:            {len(error_files)} file(s)")

        if status_lines:
            message_parts.extend(status_lines)
            message_parts.append("")

        # Section 1: Successfully renamed files
        if renamed_count > 0:
            message_parts.append("─" * 60)
            message_parts.append("RENAMED FILES:")
            message_parts.append("─" * 60)
            for old_name, new_name in self.file_renamer.processed_files['renamed']:
                message_parts.append(f"  {old_name}")
                message_parts.append(f"    → {new_name}")
                message_parts.append("")

        # Section 2: Already compliant files
        if already_compliant > 0:
            message_parts.append("─" * 60)
            message_parts.append("ALREADY COMPLIANT (No Action Needed):")
            message_parts.append("─" * 60)
            for filename in self.file_renamer.processed_files['compliant']:
                message_parts.append(f"  ✓ {filename}")
            message_parts.append("")

        # Section 3: Files not matching patterns (potential issues)
        if missing_files:
            message_parts.append("─" * 60)
            message_parts.append("FILES NOT MATCHING PATTERNS:")
            message_parts.append("─" * 60)
            message_parts.append("These files were found but don't match any configured pattern.")
            message_parts.append("Review config.ini if these should be renamed.")
            message_parts.append("")
            for filename in missing_files:
                message_parts.append(f"  ⚠ {filename}")
            message_parts.append("")

        # Section 4: Missing expected file types
        if self.file_renamer.processed_files['missing_extensions']:
            message_parts.append("─" * 60)
            message_parts.append("MISSING EXPECTED FILE TYPES:")
            message_parts.append("─" * 60)
            message_parts.append("These file types are configured but not found in directory:")
            message_parts.append("")
            for ext in sorted(self.file_renamer.processed_files['missing_extensions']):
                message_parts.append(f"  ⚠ {ext}")
            message_parts.append("")

        # Section 5: Errors (critical issues)
        if error_files:
            message_parts.append("─" * 60)
            message_parts.append("ERRORS OCCURRED:")
            message_parts.append("─" * 60)
            for error in error_files:
                message_parts.append(f"  ✗ {error}")
            message_parts.append("")

        # Section 6: Additional files created (for Processed files only)
        if label == "Processed" and hasattr(self, '_extra_files_created'):
            if self._extra_files_created:
                message_parts.append("─" * 60)
                message_parts.append("ADDITIONAL FILES CREATED:")
                message_parts.append("─" * 60)
                for file_info in self._extra_files_created:
                    message_parts.append(f"  + {file_info}")
                message_parts.append("")
                # Reset for next operation
                self._extra_files_created = []

        # Footer
        if not renamed_count and not already_compliant and not missing_files and not error_files:
            message_parts.append("No files were processed in this directory.")
        else:
            message_parts.append("=" * 60)
            if error_files or missing_files:
                message_parts.append("Status: Completed with warnings")
            else:
                message_parts.append("Status: All operations completed successfully")
            message_parts.append("=" * 60)

        # Determine dialog icon based on results
        if error_files:
            QMessageBox.warning(self, f"{label} Files - Renaming Complete", "\n".join(message_parts))
        else:
            QMessageBox.information(self, f"{label} Files - Renaming Complete", "\n".join(message_parts))

    # -------------------------------------------------------------------------
    # Extra Steps after Renaming
    # -------------------------------------------------------------------------
    def extract_pdf_page_as_png(self, folder_path, show_message=True):
        """
        Extract the second page of a PDF (matching sps_qc_pdf_pattern from config)
        as a PNG snapshot. Saves it to the same folder.

        Args:
            folder_path (str): The directory to search for PDFs.
            show_message (bool): Whether to show a message if no PDF found or page missing.

        Returns:
            str: Path to created PNG file, or None if no file created.
        """
        sps_qc_pattern = self.config.get("Regex_Filenames", "sps_qc_pdf_pattern", fallback="")
        png_suffix = self.config.get("Regex_Filenames", "png_suffix", fallback="_A1-A3vsPP_Snapshot.png")

        pdf_found = False
        created_file = None
        for filename in os.listdir(folder_path):
            if sps_qc_pattern and re.match(sps_qc_pattern, filename):
                pdf_found = True
                pdf_path = os.path.join(folder_path, filename)
                try:
                    pdf_document = fitz.Document(pdf_path)
                    if pdf_document.page_count < 2:
                        if show_message:
                            QMessageBox.warning(self, "Warning", f"{filename} does not have a second page.")
                        continue
                    page = pdf_document.load_page(1)  # second page
                    pix = page.get_pixmap()
                    output_filename = re.sub(r'\.pdf$', png_suffix, filename)
                    output_path = os.path.join(folder_path, output_filename)
                    pix.save(output_path)
                    created_file = output_path
                    logging.info(f"Created PNG extract: {output_filename}")
                except Exception as e:
                    logging.error(f"Failed to extract PDF page from {filename}: {e}")
                    if show_message:
                        QMessageBox.warning(self, "Error", f"Failed to process {filename}: {str(e)}")

        if not pdf_found and show_message:
            QMessageBox.warning(self, "No PDF Found", "No matching SPS_QC.pdf file found.")

        return created_file

    def copy_SPS_file_and_remove_headers(self, folder_path, show_message=True):
        """
        Copy a .S01 file to .0.S01 and remove the first N header rows
        (configured in [SPS_Import] header_rows).

        Args:
            folder_path (str): The directory to search for .S01 files.
            show_message (bool): Whether to display completion info as a message box.

        Returns:
            str: Path to created .0.S01 file, or None if no file created.
        """
        header_rows = self.config.getint("SPS_Import", "header_rows", fallback=194)
        sps_file_pattern = self.config.get("Regex_Filenames", "sps_file_pattern", fallback="")

        created_file = None
        for filename in os.listdir(folder_path):
            if sps_file_pattern and re.match(sps_file_pattern, filename):
                input_path = os.path.join(folder_path, filename)
                output_filename = re.sub(r'\.S01$', '.0.S01', filename)
                output_path = os.path.join(folder_path, output_filename)

                shutil.copy2(input_path, output_path)
                with open(output_path, 'r') as infile:
                    lines = infile.readlines()

                with open(output_path, 'w') as outfile:
                    outfile.writelines(lines[header_rows:])

                created_file = output_path
                logging.info(f"Created SPS copy: {output_filename} (removed {header_rows} header rows)")

                if show_message:
                    QMessageBox.information(
                        self, "S01 File Processed",
                        f"Copy created and header rows removed in {output_filename}."
                    )

        return created_file

    # -------------------------------------------------------------------------
    # NAV QC
    # -------------------------------------------------------------------------
    def _qc_worker_function(self, prod_dir, gundata_dir, sps_file, processed_folder, worker_thread=None):
        """
        Worker function that performs QC operations in background thread.

        Args:
            prod_dir: Production directory path
            gundata_dir: Gun data directory path
            sps_file: SPS file path
            processed_folder: Processed folder path
            worker_thread: QCWorkerThread instance for emitting progress signals

        Returns:
            dict with results including merged_df, log_data, percentages, etc.
        """
        results = {}

        try:
            # Import SPS data (10% progress)
            if worker_thread:
                worker_thread.progress.emit(10, "Importing SPS data...")
            logging.info("[QC Worker] Starting SPS data import from: %s", sps_file)
            sps_df = self.sps_importer.import_file(sps_file)
            if sps_df.empty:
                raise ValueError("SPS file contains no valid data")
            logging.info(f"[QC Worker] Successfully imported {len(sps_df)} SPS records")

            # Import SPS_Comp data (20% progress)
            if worker_thread:
                worker_thread.progress.emit(20, "Importing SPS comparison data...")
            logging.info("[QC Worker] Importing SPS_Comp data...")
            try:
                sps_comp_df = self.sps_comp_importer.import_file(processed_folder)
                if not sps_comp_df.empty:
                    logging.info(f"Successfully imported {len(sps_comp_df)} SPS_Comp records")
                else:
                    logging.warning("SPS_Comp DataFrame is empty")
            except Exception as e:
                logging.error(f"Error importing SPS_Comp data: {str(e)}")
                sps_comp_df = pd.DataFrame()

            # Import EOL report (30% progress)
            if worker_thread:
                worker_thread.progress.emit(30, "Importing EOL report...")
            logging.info("Importing EOL report...")
            try:
                eol_df = self.eol_importer.import_file(processed_folder)
                if not eol_df.empty:
                    logging.info(f"Successfully imported {len(eol_df)} EOL records")
                else:
                    logging.warning("EOL DataFrame is empty")
            except Exception as e:
                logging.error(f"Error importing EOL report: {str(e)}")
                eol_df = pd.DataFrame()

            # Import ASC data (40% progress)
            if worker_thread:
                worker_thread.progress.emit(40, "Importing ASC gun data...")
            logging.info("Importing ASC data...")
            try:
                asc_df = self.asc_importer.import_file(gundata_dir)
                if not asc_df.empty:
                    logging.info(f"Successfully imported {len(asc_df)} ASC records")
                else:
                    logging.warning("ASC DataFrame is empty")
            except Exception as e:
                logging.error(f"Error importing ASC data: {str(e)}")
                asc_df = pd.DataFrame()

            # Import SBS data (50% progress)
            if worker_thread:
                worker_thread.progress.emit(50, "Importing SBS source data...")
            logging.info("Importing SBS data...")
            try:
                sbs_df = self.sbs_importer.import_file(prod_dir)
                if not sbs_df.empty:
                    logging.info(f"Successfully imported {len(sbs_df)} SBS records")
                else:
                    logging.warning("SBS DataFrame is empty")
            except Exception as e:
                logging.error(f"Error importing SBS data: {str(e)}")
                sbs_df = pd.DataFrame()

            # Merge all dataframes (60% progress)
            if worker_thread:
                worker_thread.progress.emit(60, "Merging data frames...")
            logging.info("Merging all data frames...")
            merged_df = sps_df.copy()
            merged_df['shot_point'] = merged_df['shot_point'].astype(str).str.zfill(4)

            merge_dfs = [
                ('comp', sps_comp_df),
                ('eol', eol_df),
                ('asc', asc_df),
                ('sbs', sbs_df)
            ]

            for name, df in merge_dfs:
                if not df.empty and 'shot_point' in df.columns:
                    try:
                        df['shot_point'] = pd.to_numeric(df['shot_point'], errors='coerce').astype('Int64')
                        merged_df['shot_point'] = pd.to_numeric(merged_df['shot_point'], errors='coerce').astype('Int64')
                        df['shot_point'] = df['shot_point'].astype(str).str.zfill(4)
                        merged_df['shot_point'] = merged_df['shot_point'].astype(str).str.zfill(4)
                        merged_df = pd.merge(
                            merged_df, df,
                            on='shot_point',
                            how='left',
                            suffixes=('', f'_{name}')
                        )
                        merged_df['shot_point'] = pd.to_numeric(merged_df['shot_point'], errors='coerce').astype('Int64')
                        logging.debug(f"Successfully merged {name} data")
                    except Exception as e:
                        logging.error(f"Error merging {name} data: {str(e)}")
                        continue

            logging.info("Successfully merged all available data frames")

            # Check for missing shot points (65% progress)
            if worker_thread:
                worker_thread.progress.emit(65, "Checking for missing shot points...")
            logging.info("Checking for missing shot points...")
            missed_sp = self.check_sp(merged_df)
            if missed_sp:
                logging.warning(f"Found {len(missed_sp)} missing shot points")

            # Apply QC checks (75% progress)
            if worker_thread:
                worker_thread.progress.emit(75, "Applying QC validation checks...")
            logging.info("Applying QC checks...")
            merged_df = self.qc_validator.validate_data(merged_df)
            logging.info("QC checks completed successfully")

            # Extract shot point markers for production filtering (80% progress)
            parent_dir = self.prod_dir_label.text()
            line_log_path = self.line_log_manager.find_line_log_file(parent_dir)
            fgsp, lgsp, fosp, losp = None, None, None, None

            if line_log_path:
                logging.info(f"Extracting shot point markers from line log: {line_log_path}")
                line_info = self.line_log_manager.extract_line_info(line_log_path)
                if line_info['markers']['FGSP']:
                    fgsp = line_info['markers']['FGSP']['sp']
                if line_info['markers']['LGSP']:
                    lgsp = line_info['markers']['LGSP']['sp']
                if line_info['markers']['FOSP']:
                    fosp = line_info['markers']['FOSP']['sp']
                if line_info['markers']['LOSP']:
                    losp = line_info['markers']['LOSP']['sp']
                logging.info(f"Extracted markers: FGSP={fgsp}, LGSP={lgsp}, FOSP={fosp}, LOSP={losp}")

            # Calculate percentages (85% progress)
            if worker_thread:
                worker_thread.progress.emit(85, "Calculating error percentages...")
            logging.info("Calculating error percentages...")
            total_sp = len(merged_df)
            percentages = self.qc_report_generator.calculate_percentages(merged_df, total_sp, fgsp, lgsp)
            logging.info(f"Calculated percentages: {percentages}")

            # Generate line log report (90% progress)
            if worker_thread:
                worker_thread.progress.emit(90, "Generating line log report...")
            logging.info("Generating line log report...")
            log_data = self.qc_validator.generate_line_log_report(merged_df, percentages, missed_sp)
            logging.info(f"Generated line log report with {len(log_data)} entries")

            # Check for consecutive errors (95% progress)
            if worker_thread:
                worker_thread.progress.emit(95, "Checking consecutive errors...")
            logging.info("Checking for consecutive errors...")
            try:
                consecutive_errors = self.qc_validator.check_consecutive_errors(merged_df)
                if consecutive_errors:
                    logging.warning(f"Found {len(consecutive_errors)} sequences of consecutive errors")
            except Exception as e:
                logging.error(f"Error checking consecutive errors: {str(e)}")
                consecutive_errors = []

            # Save results to DB (98% progress)
            if worker_thread:
                worker_thread.progress.emit(98, "Saving results to database...")
            logging.info("Saving results to database...")
            try:
                db_results = {'merged_df': merged_df}
                output_path = self.database_manager.save_to_database(db_results, sps_file)
                if output_path:
                    logging.info(f"Results saved to {output_path}")
                    results['output_path'] = output_path
                else:
                    logging.warning("Failed to save results to database")
            except Exception as e:
                logging.error(f"Error saving results to database: {str(e)}")

            # Complete (100% progress)
            if worker_thread:
                worker_thread.progress.emit(100, "QC process complete")

            # Package all results
            results['merged_df'] = merged_df
            results['log_data'] = log_data
            results['percentages'] = percentages
            results['missed_sp'] = missed_sp
            results['consecutive_errors'] = consecutive_errors
            results['sps_file'] = sps_file

            # Add markers and line log info for update_line_log and qc_report
            results['line_log_path'] = line_log_path
            results['line_info'] = line_info if line_log_path else None
            results['fgsp'] = fgsp
            results['lgsp'] = lgsp
            results['fosp'] = fosp
            results['losp'] = losp

            return results

        except Exception as e:
            logging.error(f"Error in QC worker function: {str(e)}")
            raise

    # -------------------------------------------------------------------------
    def nav_files_qc(self):
        """
        Perform the main QC process by merging SPS, comp, EOL, ASC, SBS data,
        running checks, and updating line logs. This code is heavily dependent
        on config thresholds and patterns.

        Now uses threading for non-blocking UI during long operations.
        """
        logging.info("Starting NAV QC process...")
        try:
            # Validate production directory
            if not hasattr(self, 'prod_dir_label') or self.prod_dir_label.text() == "No directory selected":
                logging.error("Production directory not set")
                ErrorDialog.show_critical(self, "Error", "Please select a production directory first.")
                return
                return

            processed_folder = os.path.join(self.prod_dir_label.text(), "Processed")
            if not os.path.exists(processed_folder):
                logging.error(f"Processed folder not found: {processed_folder}")
                ErrorDialog.show_critical(self, "Error", "Processed folder not found in production directory.")
                return

            # Find SPS file
            sps_file = self.find_sps_file(processed_folder)
            if not sps_file:
                logging.error("No valid SPS file found")
                ErrorDialog.show_critical(self, "Error", "No valid SPS file found in Processed folder.")
                return

            # Get directory paths
            prod_dir = self.prod_dir_label.text()
            if prod_dir.endswith('Processed'):
                prod_dir = os.path.dirname(prod_dir)
            gundata_dir = self.gundata_dir_label.text()

            # Create progress dialog
            self.progress = ProgressDialog(self, "NAV QC Process", max_value=100)
            logging.info("[GUI] Created progress dialog")

            # Create worker thread - pass self reference to worker function
            self.qc_worker = QCWorkerThread(
                self._qc_worker_function,
                prod_dir, gundata_dir, sps_file, processed_folder
            )
            logging.info("[GUI] Created QC worker thread")

            # Connect worker signals
            self.qc_worker.finished.connect(self._on_qc_finished)
            self.qc_worker.error.connect(self._on_qc_error)
            self.qc_worker.progress.connect(lambda val, msg: self.progress.update(val, msg))
            self.progress.dialog.canceled.connect(lambda: self.qc_worker.cancel())
            logging.info("[GUI] Connected worker signals")

            # Start worker thread
            logging.info("[GUI] Starting QC worker thread...")
            self.qc_worker.start()

        except Exception as e:
            logging.error(f"Unexpected error in nav_files_qc: {str(e)}")
            ErrorDialog.show_critical(self, "Error", f"An unexpected error occurred: {str(e)}")

    def _on_qc_finished(self, success, results):
        """
        Slot called when QC worker thread finishes.

        Args:
            success: True if QC completed successfully
            results: Dictionary containing QC results
        """
        # Close progress dialog
        if hasattr(self, 'progress'):
            self.progress.close()

        if not success:
            logging.warning("QC process was cancelled or failed")
            return

        try:
            # Extract results
            merged_df = results.get('merged_df')
            log_data = results.get('log_data', {})
            percentages = results.get('percentages', {})
            missed_sp = results.get('missed_sp', [])
            consecutive_errors = results.get('consecutive_errors', [])

            # Extract markers and line info for update_line_log and qc_report
            line_log_path = results.get('line_log_path')
            line_info = results.get('line_info')
            fgsp = results.get('fgsp')
            lgsp = results.get('lgsp')
            fosp = results.get('fosp')
            losp = results.get('losp')
            logging.info(f"Extracted from results: line_log_path={line_log_path}, FGSP={fgsp}, LGSP={lgsp}, FOSP={fosp}, LOSP={losp}")

            # Show QC report popup
            parent_dir = self.prod_dir_label.text()
            if parent_dir and merged_df is not None:
                # Pass markers to QC report for timing validation
                markers_dict = None
                if line_info and 'markers' in line_info:
                    markers_dict = line_info['markers']
                    logging.info(f"Passing markers to QC report: {list(markers_dict.keys())}")

                success_report, report_content = self.qc_report_generator.generate_qc_report(parent_dir, merged_df, markers_dict)
                if success_report:
                    QMessageBox.information(self, "QC Report", report_content)
                else:
                    QMessageBox.warning(self, "QC Report Error", report_content)

            # Prompt user to update line log
            reply = QMessageBox.question(
                self, 'Check Line Log',
                'Update the Line Log? (Close it first.)',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # line_log_path and markers extracted from results dictionary
                if not line_log_path:
                    ErrorDialog.show_warning(self, "File Not Found", "Line Log file not found in the parent directory.")
                else:
                    success_update = self.line_log_manager.update_line_log(
                        line_log_path, merged_df, log_data, missed_sp, percentages, consecutive_errors,
                        fgsp, lgsp, fosp, losp
                    )

                    if not success_update:
                        ErrorDialog.show_critical(
                            self, "Error",
                            "Failed to update the Line Log. The file might be open. Please close it and try again."
                        )
                    else:
                        # Generate QC report after line log update
                        try:
                            logging.info("Starting QC report generation...")
                            success_qc, report_content = self.qc_report_generator.generate_qc_report(parent_dir, merged_df)
                            if not success_qc:
                                logging.warning(f"QC report generation had issues: {report_content}")
                        except Exception as e:
                            logging.error(f"Failed to generate QC report: {str(e)}")

                        ErrorDialog.show_info(self, "Success", "NAV QC process completed successfully!")

            else:
                ErrorDialog.show_info(self, "Success", "NAV QC process completed successfully!")

        except Exception as e:
            logging.error(f"Error in QC finish handler: {str(e)}")
            ErrorDialog.show_critical(self, "Error", f"Failed to process QC results: {str(e)}")

    def _on_qc_error(self, error_message):
        """
        Slot called when QC worker thread encounters an error.

        Args:
            error_message: Error message from worker
        """
        # Close progress dialog
        if hasattr(self, 'progress'):
            self.progress.close()

        logging.error(f"QC worker error: {error_message}")
        ErrorDialog.show_critical(
            self, "QC Error",
            f"An error occurred during QC processing:\n{error_message}"
        )

    # -------------------------------------------------------------------------
    # Data Import Helpers
    # -------------------------------------------------------------------------
    def find_sps_file(self, folder_path):
        """
        Locate an SPS file in the 'Processed' folder matching the sps_file_pattern
        from config, ignoring those that match sps_file_noheader.

        Args:
            folder_path (str): The production directory.

        Returns:
            str or None: The full path to the SPS file if found, else None.
        """
        sps_file_pat = self.config.get("Regex_Filenames", "sps_file_pattern", fallback="")
        sps_nohdr_pat = self.config.get("Regex_Filenames", "sps_file_noheader", fallback="")

        for filename in os.listdir(folder_path):
            if sps_file_pat and re.match(sps_file_pat, filename):
                if sps_nohdr_pat and re.match(sps_nohdr_pat, filename):
                    continue
                return os.path.join(folder_path, filename)
        return None

    # -------------------------------------------------------------------------
    # QC Checking
    # -------------------------------------------------------------------------
    def check_sp(self, merged_df):
        """
        Check for missed shot points by scanning for large gaps.
        
        Args:
            merged_df (pd.DataFrame): DataFrame containing shot point data
            
        Returns:
            tuple: (total_sp, missed_sp)
                - total_sp (int): Total number of shot points
                - missed_sp (list): List of missing shot point numbers
        """

        total_sp = len(merged_df)
        shot_points = sorted(merged_df['shot_point'].tolist())
        missed_sp = []

        for i in range(len(shot_points) - 1):
            current = shot_points[i]
            next_ = shot_points[i+1]
            diff = next_ - current
            if abs(diff) > 2:
                if diff > 0:
                    missed = list(range(current+2, next_, 2))
                    missed_sp.extend(missed)
                    logging.info(f"Missing shot points between {current} and {next_}: {missed}")
                else:
                    missed = list(range(current-2, next_, -2))
                    missed_sp.extend(missed)
                    logging.info(f"Missing shot points between {current} and {next_}: {missed}")
        
        if missed_sp:
            logging.warning(f"Found {len(missed_sp)} missing shot points: {sorted(missed_sp)}")
            
        return missed_sp



# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())