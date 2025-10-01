"""
GUI Helper Module

Provides standardized dialogs, progress reporting, and error handling for the GUI.

Classes:
- ErrorDialog: Standardized error message dialogs with log viewing
- ProgressDialog: Progress bar with cancellation support
- QCWorkerThread: Background thread for long-running QC operations

Author: aldien03@gmail.com
Date: 2025-10-01
"""

import logging
from typing import Callable, Optional
from PyQt5.QtWidgets import (
    QMessageBox, QProgressDialog, QDialog, QVBoxLayout,
    QTextEdit, QPushButton, QHBoxLayout, QLabel
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont


class ErrorDialog:
    """
    Standardized error dialog helper with consistent styling and log viewing capability.

    Provides three severity levels:
    - critical: Fatal errors that stop execution
    - warning: Non-fatal issues that allow continuation
    - information: Success messages or informational alerts
    """

    @staticmethod
    def show_critical(parent, title: str, message: str, log_message: Optional[str] = None):
        """
        Show critical error dialog (fatal error).

        Args:
            parent: Parent widget
            title: Dialog title
            message: User-friendly error message
            log_message: Optional detailed message to log
        """
        if log_message:
            logging.error(log_message)
        else:
            logging.error(f"{title}: {message}")

        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)

        # Add "View Log" button if log file exists
        if ErrorDialog._has_log_file():
            view_log_btn = msg_box.addButton("View Log", QMessageBox.ActionRole)
            msg_box.exec_()
            if msg_box.clickedButton() == view_log_btn:
                ErrorDialog._show_log_viewer(parent)
        else:
            msg_box.exec_()

    @staticmethod
    def show_warning(parent, title: str, message: str, log_message: Optional[str] = None):
        """
        Show warning dialog (non-fatal issue).

        Args:
            parent: Parent widget
            title: Dialog title
            message: User-friendly warning message
            log_message: Optional detailed message to log
        """
        if log_message:
            logging.warning(log_message)
        else:
            logging.warning(f"{title}: {message}")

        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)

        if ErrorDialog._has_log_file():
            view_log_btn = msg_box.addButton("View Log", QMessageBox.ActionRole)
            msg_box.exec_()
            if msg_box.clickedButton() == view_log_btn:
                ErrorDialog._show_log_viewer(parent)
        else:
            msg_box.exec_()

    @staticmethod
    def show_info(parent, title: str, message: str, log_message: Optional[str] = None):
        """
        Show information dialog (success or general info).

        Args:
            parent: Parent widget
            title: Dialog title
            message: Informational message
            log_message: Optional detailed message to log
        """
        if log_message:
            logging.info(log_message)
        else:
            logging.info(f"{title}: {message}")

        QMessageBox.information(parent, title, message)

    @staticmethod
    def _has_log_file() -> bool:
        """Check if log file exists"""
        import os
        return os.path.exists('nav_qc.log')

    @staticmethod
    def _show_log_viewer(parent):
        """Show log viewer dialog"""
        dialog = QDialog(parent)
        dialog.setWindowTitle("Application Log")
        dialog.resize(800, 600)

        layout = QVBoxLayout()

        # Read log file
        try:
            with open('nav_qc.log', 'r') as f:
                log_content = f.read()
        except Exception as e:
            log_content = f"Error reading log file: {str(e)}"

        # Text edit for log display
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Courier", 9))
        text_edit.setText(log_content)

        # Scroll to bottom
        text_edit.verticalScrollBar().setValue(
            text_edit.verticalScrollBar().maximum()
        )

        layout.addWidget(text_edit)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec_()


class ProgressDialog:
    """
    Progress dialog with cancellation support for long-running operations.

    Features:
    - Cancellable progress bar
    - Status message updates
    - Automatic cleanup
    """

    def __init__(self, parent, title: str, max_value: int = 100):
        """
        Initialize progress dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            max_value: Maximum progress value (default 100)
        """
        self.dialog = QProgressDialog(parent)
        self.dialog.setWindowTitle(title)
        self.dialog.setWindowModality(Qt.WindowModal)
        self.dialog.setMinimumDuration(500)  # Show after 500ms
        self.dialog.setRange(0, max_value)
        self.dialog.setValue(0)
        self.dialog.setAutoClose(True)
        self.dialog.setAutoReset(True)
        self._cancelled = False

        # Connect cancel button
        self.dialog.canceled.connect(self._on_cancel)

    def _on_cancel(self):
        """Handle cancellation"""
        self._cancelled = True
        logging.info("Operation cancelled by user")

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled"""
        return self._cancelled

    def update(self, value: int, message: str = ""):
        """
        Update progress value and message.

        Args:
            value: Current progress value
            message: Status message to display
        """
        if not self._cancelled:
            self.dialog.setValue(value)
            if message:
                self.dialog.setLabelText(message)

    def set_message(self, message: str):
        """Update status message without changing progress"""
        if not self._cancelled:
            self.dialog.setLabelText(message)

    def close(self):
        """Close the progress dialog"""
        self.dialog.close()


class QCWorkerThread(QThread):
    """
    Background worker thread for QC operations.

    Signals:
        progress: (int, str) - Progress value and status message
        finished: (bool, dict) - Success flag and results dict
        error: (str) - Error message if operation fails
    """

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, dict)
    error = pyqtSignal(str)

    def __init__(self, qc_function: Callable, *args, **kwargs):
        """
        Initialize worker thread.

        Args:
            qc_function: Function to run in background
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function
        """
        super().__init__()
        self.qc_function = qc_function
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False

    def cancel(self):
        """Request cancellation of the operation"""
        self._is_cancelled = True
        logging.info("Worker thread cancellation requested")

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested"""
        return self._is_cancelled

    def run(self):
        """Run the QC operation in background thread"""
        try:
            logging.info("Starting QC worker thread")

            # Execute the QC function, passing self as worker_thread parameter
            # This allows the worker function to emit progress signals
            results = self.qc_function(*self.args, worker_thread=self, **self.kwargs)

            if self._is_cancelled:
                logging.info("Worker thread was cancelled")
                self.finished.emit(False, {})
            else:
                logging.info("Worker thread completed successfully")
                self.finished.emit(True, results)

        except Exception as e:
            error_msg = f"Error in worker thread: {str(e)}"
            logging.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            self.finished.emit(False, {})
