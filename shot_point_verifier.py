"""
Shot Point Verifier Module

This module provides shot point verification functionality across multiple file types.
It counts shot points in .p190, .p294, .S00, and .p211 files and verifies consistency.

Classes:
- ShotPointVerifier: Main class for handling shot point verification operations

Author: PXGEONavQC Development Team
Date: 2025-09-30
"""

import os
import logging
from typing import Dict, List, Tuple


class ShotPointVerifier:
    """
    Class for verifying shot points across different file types.

    Supports:
    - P1/90 files (.p190) - Pattern: 'S'
    - P2/94 files (.p294) - Pattern: 'E1000'
    - SPS files (.S00) - Pattern: 'S'
    - P2/11 files (.p211) - Pattern: 'E2'
    - Consistency checking across all files
    - Missing file detection
    - Error handling and reporting
    """

    FILE_PATTERNS = {
        'p190': {'pattern': 'S', 'desc': 'P1/90 File'},
        'p294': {'pattern': 'E1000', 'desc': 'P2/94 File'},
        'S00': {'pattern': 'S', 'desc': 'SPS File'},
        'p211': {'pattern': 'E2', 'desc': 'P2/11 File'}
    }

    def __init__(self):
        """Initialize the ShotPointVerifier."""
        self.reset_counts()

    def reset_counts(self):
        """Reset all shot point counts."""
        self.counts = {ext: {'count': 0, 'files': []} for ext in self.FILE_PATTERNS.keys()}
        self.missing_files = []
        self.error_files = []

    def verify_directory(self, directory: str) -> Tuple[bool, str]:
        """
        Verify shot points in all relevant files within a directory.

        Args:
            directory: Path to the directory containing the files

        Returns:
            Tuple of (is_consistent, report_message)
                - is_consistent: True if all files have matching shot point counts
                - report_message: Detailed report of the verification
        """
        self.reset_counts()

        # Check for required files
        all_files = os.listdir(directory)
        for ext in self.FILE_PATTERNS.keys():
            matching_files = [f for f in all_files if f.lower().endswith(ext.lower())]
            if not matching_files:
                self.missing_files.append(self.FILE_PATTERNS[ext]['desc'])
            else:
                for file_name in matching_files:
                    self._count_shot_points(os.path.join(directory, file_name))

        # Generate report
        return self._generate_report()

    def _count_shot_points(self, file_path: str) -> None:
        """
        Count shot points in a single file.

        Args:
            file_path: Path to the file to count shot points in
        """
        file_name = os.path.basename(file_path)
        file_ext = next((ext for ext in self.FILE_PATTERNS.keys()
                        if file_name.lower().endswith(ext.lower())), None)

        if not file_ext:
            return

        try:
            count = 0
            pattern = self.FILE_PATTERNS[file_ext]['pattern']

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith(pattern):
                        count += 1

            self.counts[file_ext]['count'] = count
            self.counts[file_ext]['files'].append(file_name)

        except Exception as exc:
            logging.error(f"Error reading {file_name}: {exc}")
            self.error_files.append((file_name, str(exc)))

    def _generate_report(self) -> Tuple[bool, str]:
        """
        Generate a detailed, user-friendly report of the verification results.

        Returns:
            Tuple of (is_consistent, report_message)
        """
        report = []

        # Header
        report.append("=" * 60)
        report.append("  SHOT POINT VERIFICATION REPORT")
        report.append("=" * 60)
        report.append("")

        # Handle missing files
        if self.missing_files:
            report.append("✗ STATUS: MISSING FILES")
            report.append("")
            report.append("─" * 60)
            report.append("MISSING REQUIRED FILES:")
            report.append("─" * 60)
            for f in self.missing_files:
                report.append(f"  ✗ {f}")
            report.append("")
            report.append("=" * 60)
            report.append("Action Required: Please ensure all required files are present.")
            report.append("=" * 60)
            return False, "\n".join(report)

        # Handle errors
        if self.error_files:
            report.append("✗ STATUS: ERRORS ENCOUNTERED")
            report.append("")
            report.append("─" * 60)
            report.append("ERRORS READING FILES:")
            report.append("─" * 60)
            for name, error in self.error_files:
                report.append(f"  ✗ {name}")
                report.append(f"     Error: {error}")
                report.append("")
            report.append("=" * 60)
            report.append("Action Required: Fix file issues and retry verification.")
            report.append("=" * 60)
            return False, "\n".join(report)

        # Get non-zero counts
        valid_counts = {ext: data['count'] for ext, data in self.counts.items()
                       if data['count'] > 0}

        if not valid_counts:
            report.append("⚠ STATUS: NO DATA FOUND")
            report.append("")
            report.append("No shot points found in any files.")
            report.append("")
            report.append("=" * 60)
            report.append("Action Required: Check that files contain valid data.")
            report.append("=" * 60)
            return False, "\n".join(report)

        # Check if all counts match
        first_count = next(iter(valid_counts.values()))
        is_consistent = all(count == first_count for count in valid_counts.values())

        # Status Summary
        if is_consistent:
            report.append("✓ STATUS: ALL FILES CONSISTENT")
        else:
            report.append("✗ STATUS: MISMATCH DETECTED")

        report.append("")
        report.append(f"Total Shot Points: {first_count:,}" if is_consistent else "Total Shot Points: VARIES (see below)")
        report.append(f"Files Verified: {len(valid_counts)}")
        report.append("")

        # Detailed File Counts
        report.append("─" * 60)
        report.append("FILE-BY-FILE BREAKDOWN:")
        report.append("─" * 60)

        for ext, data in self.counts.items():
            if data['count'] > 0:
                desc = self.FILE_PATTERNS[ext]['desc']
                count = data['count']
                files = ', '.join(data['files'])

                # Mark consistency
                if is_consistent:
                    icon = "✓"
                elif count == first_count:
                    icon = "✓"
                else:
                    icon = "✗"

                report.append(f"  {icon} {desc}:")
                report.append(f"     Shot Points: {count:,}")
                report.append(f"     Files: {files}")
                report.append("")

        # Summary Section
        report.append("─" * 60)
        if is_consistent:
            report.append("VERIFICATION RESULT:")
            report.append("─" * 60)
            report.append(f"✓ All files have matching shot point count: {first_count:,}")
            report.append("")
            report.append("=" * 60)
            report.append("Status: Data consistency verified successfully")
            report.append("=" * 60)
        else:
            report.append("MISMATCH DETAILS:")
            report.append("─" * 60)
            report.append("The following files have different shot point counts:")
            report.append("")
            for ext, data in self.counts.items():
                if data['count'] > 0 and data['count'] != first_count:
                    desc = self.FILE_PATTERNS[ext]['desc']
                    diff = data['count'] - first_count
                    sign = "+" if diff > 0 else ""
                    report.append(f"  ✗ {desc}: {data['count']:,} shot points ({sign}{diff:,})")
            report.append("")
            report.append("=" * 60)
            report.append("Action Required: Investigate count discrepancies")
            report.append("=" * 60)

        return is_consistent, "\n".join(report)
