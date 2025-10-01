"""
Unit tests for GUI Helper Module

Tests error dialogs, progress reporting, and worker thread functionality.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, MagicMock, patch, call
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QThread, Qt
from gui_helpers import ErrorDialog, ProgressDialog, QCWorkerThread

import sys
# Ensure QApplication exists for PyQt5 tests
if not QApplication.instance():
    app = QApplication(sys.argv)


@pytest.fixture
def qt_app():
    """Provide QApplication instance for tests"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def parent_widget(qt_app):
    """Create parent widget for dialog tests"""
    return QWidget()


@pytest.fixture
def temp_log_file():
    """Create temporary log file for testing"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')
    temp_file.write("Test log entry 1\n")
    temp_file.write("Test log entry 2\n")
    temp_file.close()
    yield temp_file.name
    if os.path.exists(temp_file.name):
        os.remove(temp_file.name)


class TestErrorDialogCritical:
    """Test ErrorDialog.show_critical functionality"""

    @patch('gui_helpers.QMessageBox')
    @patch('gui_helpers.logging')
    def test_show_critical_basic(self, mock_logging, mock_msgbox, parent_widget):
        """Test basic critical error dialog"""
        ErrorDialog.show_critical(parent_widget, "Test Error", "Error message")

        # Verify logging
        mock_logging.error.assert_called_once_with("Test Error: Error message")

        # Verify message box created
        mock_msgbox.assert_called_once_with(parent_widget)

    @patch('gui_helpers.QMessageBox')
    @patch('gui_helpers.logging')
    def test_show_critical_with_log_message(self, mock_logging, mock_msgbox, parent_widget):
        """Test critical error with custom log message"""
        ErrorDialog.show_critical(
            parent_widget,
            "Test Error",
            "User message",
            log_message="Detailed log message"
        )

        # Verify custom log message used
        mock_logging.error.assert_called_once_with("Detailed log message")

    @patch('gui_helpers.ErrorDialog._has_log_file', return_value=False)
    @patch('gui_helpers.QMessageBox')
    def test_show_critical_no_log_file(self, mock_msgbox, mock_has_log, parent_widget):
        """Test critical error when no log file exists"""
        mock_instance = MagicMock()
        mock_msgbox.return_value = mock_instance

        ErrorDialog.show_critical(parent_widget, "Test", "Message")

        # Should not add "View Log" button
        mock_instance.addButton.assert_not_called()
        mock_instance.exec_.assert_called_once()


class TestErrorDialogWarning:
    """Test ErrorDialog.show_warning functionality"""

    @patch('gui_helpers.QMessageBox')
    @patch('gui_helpers.logging')
    def test_show_warning_basic(self, mock_logging, mock_msgbox, parent_widget):
        """Test basic warning dialog"""
        ErrorDialog.show_warning(parent_widget, "Warning Title", "Warning message")

        # Verify logging
        mock_logging.warning.assert_called_once_with("Warning Title: Warning message")

    @patch('gui_helpers.QMessageBox')
    @patch('gui_helpers.logging')
    def test_show_warning_with_custom_log(self, mock_logging, mock_msgbox, parent_widget):
        """Test warning with custom log message"""
        ErrorDialog.show_warning(
            parent_widget,
            "Warning",
            "User warning",
            log_message="Custom log"
        )

        mock_logging.warning.assert_called_once_with("Custom log")


class TestErrorDialogInfo:
    """Test ErrorDialog.show_info functionality"""

    @patch('gui_helpers.QMessageBox.information')
    @patch('gui_helpers.logging')
    def test_show_info_basic(self, mock_logging, mock_msgbox, parent_widget):
        """Test basic info dialog"""
        ErrorDialog.show_info(parent_widget, "Info Title", "Info message")

        # Verify logging
        mock_logging.info.assert_called_once_with("Info Title: Info message")

        # Verify message box
        mock_msgbox.assert_called_once_with(parent_widget, "Info Title", "Info message")

    @patch('gui_helpers.QMessageBox.information')
    @patch('gui_helpers.logging')
    def test_show_info_with_custom_log(self, mock_logging, mock_msgbox, parent_widget):
        """Test info with custom log message"""
        ErrorDialog.show_info(
            parent_widget,
            "Info",
            "User info",
            log_message="Custom log info"
        )

        mock_logging.info.assert_called_once_with("Custom log info")


class TestErrorDialogLogViewer:
    """Test ErrorDialog log viewing functionality"""

    def test_has_log_file_exists(self, temp_log_file):
        """Test _has_log_file when log exists"""
        with patch('os.path.exists', return_value=True):
            assert ErrorDialog._has_log_file() is True

    def test_has_log_file_not_exists(self):
        """Test _has_log_file when log doesn't exist"""
        with patch('os.path.exists', return_value=False):
            assert ErrorDialog._has_log_file() is False


class TestProgressDialog:
    """Test ProgressDialog functionality"""

    def test_initialization(self, parent_widget):
        """Test ProgressDialog initialization"""
        progress = ProgressDialog(parent_widget, "Test Operation", max_value=100)

        assert progress is not None
        assert progress.dialog is not None
        assert progress._cancelled is False

    def test_initialization_with_custom_max(self, parent_widget):
        """Test ProgressDialog with custom max value"""
        progress = ProgressDialog(parent_widget, "Test", max_value=50)

        # Verify range set correctly
        assert progress.dialog.maximum() == 50
        assert progress.dialog.minimum() == 0

    def test_update_progress(self, parent_widget):
        """Test updating progress value"""
        progress = ProgressDialog(parent_widget, "Test", max_value=100)

        progress.update(50, "Processing...")

        assert progress.dialog.value() == 50
        assert progress.dialog.labelText() == "Processing..."

    def test_update_without_message(self, parent_widget):
        """Test updating progress without message"""
        progress = ProgressDialog(parent_widget, "Test")

        progress.update(75)

        assert progress.dialog.value() == 75

    def test_set_message_only(self, parent_widget):
        """Test setting message without changing progress"""
        progress = ProgressDialog(parent_widget, "Test")
        initial_value = progress.dialog.value()

        progress.set_message("New message")

        assert progress.dialog.value() == initial_value
        assert progress.dialog.labelText() == "New message"

    def test_is_cancelled_initial(self, parent_widget):
        """Test initial cancelled state"""
        progress = ProgressDialog(parent_widget, "Test")

        assert progress.is_cancelled() is False

    def test_cancel_operation(self, parent_widget):
        """Test cancelling operation"""
        progress = ProgressDialog(parent_widget, "Test")

        progress._on_cancel()

        assert progress.is_cancelled() is True

    def test_update_after_cancel(self, parent_widget):
        """Test that updates are ignored after cancel"""
        progress = ProgressDialog(parent_widget, "Test")
        progress._on_cancel()

        initial_value = progress.dialog.value()
        progress.update(50, "Should be ignored")

        # Value should not change after cancellation
        assert progress.dialog.value() == initial_value

    def test_close_dialog(self, parent_widget):
        """Test closing the progress dialog"""
        progress = ProgressDialog(parent_widget, "Test")

        # Should not raise exception
        progress.close()


class TestQCWorkerThread:
    """Test QCWorkerThread functionality"""

    def test_initialization(self, qt_app):
        """Test QCWorkerThread initialization"""
        mock_function = Mock(return_value={'result': 'success'})

        worker = QCWorkerThread(mock_function, arg1='value1', arg2='value2')

        assert worker is not None
        assert worker.qc_function == mock_function
        assert worker.kwargs == {'arg1': 'value1', 'arg2': 'value2'}
        assert worker._is_cancelled is False

    def test_is_cancelled_initial(self, qt_app):
        """Test initial cancellation state"""
        worker = QCWorkerThread(Mock())

        assert worker.is_cancelled() is False

    def test_cancel_operation(self, qt_app):
        """Test cancellation request"""
        worker = QCWorkerThread(Mock())

        worker.cancel()

        assert worker.is_cancelled() is True

    def test_run_success(self, qt_app):
        """Test successful worker execution"""
        mock_function = Mock(return_value={'data': 'test_data'})
        worker = QCWorkerThread(mock_function)

        # Mock signals
        finished_signal = Mock()
        worker.finished.connect(finished_signal)

        # Run worker
        worker.run()

        # Verify function called
        mock_function.assert_called_once()

        # Verify finished signal emitted with success
        finished_signal.assert_called_once_with(True, {'data': 'test_data'})

    def test_run_with_args(self, qt_app):
        """Test worker execution with arguments"""
        mock_function = Mock(return_value={'result': 'ok'})
        worker = QCWorkerThread(mock_function, 'arg1', 'arg2', kwarg1='value1')

        worker.run()

        # Verify function called with correct arguments (worker_thread is added automatically)
        assert mock_function.call_count == 1
        call_args, call_kwargs = mock_function.call_args
        assert call_args == ('arg1', 'arg2')
        assert call_kwargs['kwarg1'] == 'value1'
        assert 'worker_thread' in call_kwargs
        assert call_kwargs['worker_thread'] is worker

    def test_run_cancelled(self, qt_app):
        """Test worker execution when cancelled"""
        mock_function = Mock(return_value={'data': 'test'})
        worker = QCWorkerThread(mock_function)

        finished_signal = Mock()
        worker.finished.connect(finished_signal)

        # Cancel before completion
        worker.cancel()
        worker.run()

        # Should emit finished with failure
        finished_signal.assert_called_once_with(False, {})

    def test_run_with_exception(self, qt_app):
        """Test worker handling of exceptions"""
        mock_function = Mock(side_effect=ValueError("Test error"))
        worker = QCWorkerThread(mock_function)

        error_signal = Mock()
        finished_signal = Mock()
        worker.error.connect(error_signal)
        worker.finished.connect(finished_signal)

        worker.run()

        # Verify error signal emitted
        error_signal.assert_called_once()
        error_msg = error_signal.call_args[0][0]
        assert "Test error" in error_msg

        # Verify finished with failure
        finished_signal.assert_called_once_with(False, {})

    def test_progress_signal_emission(self, qt_app):
        """Test that progress signal can be emitted"""
        def mock_qc_function():
            # Simulate progress updates
            return {'status': 'complete'}

        worker = QCWorkerThread(mock_qc_function)

        # Verify progress signal exists
        assert hasattr(worker, 'progress')

        # Test manual progress emission
        progress_signal = Mock()
        worker.progress.connect(progress_signal)
        worker.progress.emit(50, "Halfway done")

        progress_signal.assert_called_once_with(50, "Halfway done")

    def test_multiple_signal_connections(self, qt_app):
        """Test connecting multiple handlers to signals"""
        worker = QCWorkerThread(Mock(return_value={}))

        handler1 = Mock()
        handler2 = Mock()

        worker.finished.connect(handler1)
        worker.finished.connect(handler2)

        worker.run()

        # Both handlers should be called
        handler1.assert_called_once()
        handler2.assert_called_once()


class TestQCWorkerThreadIntegration:
    """Integration tests for QCWorkerThread with ProgressDialog"""

    def test_worker_with_progress_dialog(self, qt_app, parent_widget):
        """Test QCWorkerThread integrated with ProgressDialog"""
        def mock_qc_operation(worker_thread=None):
            return {'lines_processed': 100}

        worker = QCWorkerThread(mock_qc_operation)
        progress = ProgressDialog(parent_widget, "Running QC", max_value=100)

        # Connect worker progress to dialog
        def update_progress(value, message):
            progress.update(value, message)

        worker.progress.connect(update_progress)

        # Connect finished signal
        finished_handler = Mock()
        worker.finished.connect(finished_handler)

        # Run worker
        worker.run()

        # Verify completion
        finished_handler.assert_called_once_with(True, {'lines_processed': 100})

    def test_worker_cancellation_through_progress(self, qt_app, parent_widget):
        """Test cancelling worker through progress dialog"""
        worker = QCWorkerThread(Mock(return_value={}))
        progress = ProgressDialog(parent_widget, "Test")

        # Connect cancel from progress to worker using lambda (Qt signal pattern)
        progress.dialog.canceled.connect(lambda: worker.cancel())

        # Trigger cancel signal
        progress.dialog.canceled.emit()

        # Worker should be cancelled
        assert worker.is_cancelled() is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
