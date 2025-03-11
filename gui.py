import sys
import os
import asyncio
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, 
    QProgressBar, QMessageBox, QDesktopWidget, QLabel, QHBoxLayout,
    QFrame, QSplitter, QTextEdit, QCheckBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont
from downloader.updater import update_files
from logger import log_info, log_error

class PatcherThread(QThread):
    progress_updated = pyqtSignal(int, int)
    update_status = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.success = False
        self.error = ""

    def run(self):
        """Run the update process in a separate thread."""
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create a custom callback that emits signals
            def progress_callback(progress, total, error=None):
                if error:
                    self.error_occurred.emit(error)
                elif progress is not None and total is not None:
                    self.progress_updated.emit(progress, total)
                    
                    # Calculate percentage for log message if not at 100%
                    if progress < total:
                        percentage = int(progress / total * 100)
                        if percentage % 10 == 0:  # Log every 10%
                            self.log_message.emit(f"Download progress: {percentage}%")
            
            # Emit starting message
            self.log_message.emit("Starting update process...")
            
            # Run the update process
            status_report = loop.run_until_complete(update_files(callback=progress_callback))
            
            # Check for any failures
            if status_report['failed']:
                failed_count = len(status_report['failed'])
                self.log_message.emit(f"Warning: {failed_count} files failed to update")
            
            # Emit success message
            updated_count = len(status_report['updated'])
            skipped_count = len(status_report['skipped'])
            self.log_message.emit(f"Update complete: {updated_count} files updated, {skipped_count} files skipped")
            
            # Emit the status report
            self.update_status.emit(status_report)
            self.success = True
            
        except Exception as e:
            self.error = str(e)
            self.success = False
            self.error_occurred.emit(self.error)
            self.log_message.emit(f"Error during update: {self.error}")
        finally:
            loop.close()
            self.log_message.emit("Update process finished")

class PatcherGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Patcher')
        self.setMinimumSize(500, 400)
        self.initUI()
        
        # Apply some basic styling
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; }
            QPushButton { 
                background-color: #4a86e8; 
                color: white; 
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a76d8; }
            QPushButton:disabled { background-color: #cccccc; }
            QProgressBar {
                border: 1px solid #bbbbbb;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4a86e8;
                width: 1px;
            }
            QLabel { font-size: 14px; }
            QTextEdit { background-color: #ffffff; border: 1px solid #dddddd; }
        """)

    def initUI(self):
        """Initialize the user interface."""
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Header
        header_label = QLabel('Patcher - Update Manager')
        header_label.setFont(QFont('Arial', 16, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Add a separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout()
        
        # Download button
        self.download_button = QPushButton('Download Updates', self)
        self.download_button.setMinimumHeight(40)
        self.download_button.clicked.connect(self.start_patcher_thread)
        control_layout.addWidget(self.download_button)
        
        # Auto-close checkbox
        self.auto_close_checkbox = QCheckBox("Auto-close when complete")
        control_layout.addWidget(self.auto_close_checkbox)
        
        control_panel.setLayout(control_layout)
        main_layout.addWidget(control_panel)
        
        # Progress section
        progress_widget = QWidget()
        progress_layout = QVBoxLayout()
        
        progress_label = QLabel('Download Progress:')
        progress_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v of %m files")
        progress_layout.addWidget(self.progress_bar)
        
        progress_widget.setLayout(progress_layout)
        main_layout.addWidget(progress_widget)
        
        # Log area
        log_label = QLabel('Activity Log:')
        main_layout.addWidget(log_label)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(150)
        main_layout.addWidget(self.log_area)
        
        # Status bar
        self.status_label = QLabel('Ready')
        self.status_label.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self.status_label)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Center the window
        self.center()
        
        # Initialize a timer for auto-close
        self.auto_close_timer = QTimer()
        self.auto_close_timer.timeout.connect(self.close)
        
        # Add initial log message
        self.add_log_message("Application started. Ready to check for updates.")

    def start_patcher_thread(self):
        """Start the patcher thread to download updates."""
        self.download_button.setEnabled(False)
        self.status_label.setText('Downloading updates...')
        self.progress_bar.setValue(0)
        
        # Create and configure the thread
        self.patcher_thread = PatcherThread()
        self.patcher_thread.progress_updated.connect(self.update_progress_bar)
        self.patcher_thread.update_status.connect(self.display_update_status)
        self.patcher_thread.error_occurred.connect(self.display_error)
        self.patcher_thread.log_message.connect(self.add_log_message)
        self.patcher_thread.finished.connect(self.patcher_finished)
        
        # Start the thread
        self.patcher_thread.start()
        self.add_log_message("Update process started...")

    def update_progress_bar(self, progress, total):
        """Update the progress bar."""
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(progress)
            percentage = int(progress / total * 100)
            self.status_label.setText(f'Downloading: {percentage}%')

    def display_update_status(self, status_report):
        """Display the update status in a message box."""
        updated_files = '\n'.join(status_report['updated']) if status_report['updated'] else "None"
        skipped_files = '\n'.join(status_report['skipped']) if status_report['skipped'] else "None"
        failed_files = '\n'.join(status_report['failed']) if status_report['failed'] else "None"
        verified_files = '\n'.join(status_report['verification']['verified']) if status_report['verification']['verified'] else "None"
        corrupted_files = '\n'.join(status_report['verification']['corrupted']) if status_report['verification']['corrupted'] else "None"

        # Create a summary
        summary = (
            f"<b>Summary:</b><br>"
            f"- Updated: {len(status_report['updated'])} files<br>"
            f"- Skipped: {len(status_report['skipped'])} files<br>"
            f"- Failed: {len(status_report['failed'])} files<br>"
            f"- Verified: {len(status_report['verification']['verified'])} files<br>"
            f"- Corrupted: {len(status_report['verification']['corrupted'])} files<br>"
        )
        
        # Create detailed report
        details = (
            f"<b>Updated Files:</b><br>{updated_files}<br><br>"
            f"<b>Skipped Files:</b><br>{skipped_files}<br><br>"
        )
        
        if status_report['failed']:
            details += f"<b>Failed Files:</b><br>{failed_files}<br><br>"
        
        if status_report['verification']['corrupted']:
            details += f"<b>Corrupted Files:</b><br>{corrupted_files}<br><br>"
        
        # Show in message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('Update Status')
        msg_box.setText(summary)
        msg_box.setDetailedText(f"Updated Files:\n{updated_files}\n\n"
                              f"Skipped Files:\n{skipped_files}\n\n"
                              f"Failed Files:\n{failed_files}\n\n"
                              f"Verified Files:\n{verified_files}\n\n"
                              f"Corrupted Files:\n{corrupted_files}")
        
        # Determine icon based on results
        if status_report['failed'] or status_report['verification']['corrupted']:
            msg_box.setIcon(QMessageBox.Warning)
        else:
            msg_box.setIcon(QMessageBox.Information)
        
        msg_box.exec_()
        
        # Auto-close if checkbox is checked and update was successful
        if (self.auto_close_checkbox.isChecked() and 
            not status_report['failed'] and 
            not status_report['verification']['corrupted']):
            
            self.add_log_message("Auto-closing in 3 seconds...")
            self.auto_close_timer.start(3000)  # 3 seconds

    def display_error(self, error_message):
        """Display an error message."""
        QMessageBox.critical(self, 'Error', error_message)
        self.status_label.setText('Error occurred')

    def add_log_message(self, message):
        """Add a message to the log area."""
        self.log_area.append(f"{message}")
        # Auto-scroll to bottom
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def patcher_finished(self):
        """Handle thread completion."""
        if self.patcher_thread.success:
            self.status_label.setText('Update completed successfully')
            log_info('Files updated successfully')
        else:
            self.status_label.setText('Update failed')
            log_error(f'Error during patching: {self.patcher_thread.error}')
        
        self.download_button.setEnabled(True)

    def center(self):
        """Center the window on the screen."""
        screen_geometry = QDesktopWidget().availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

def run():
    """Run the application."""
    # Make sure we have a logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Start the application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a modern look
    
    window = PatcherGUI()
    window.show()
    
    sys.exit(app.exec_())