import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QProgressBar, QMessageBox, QDesktopWidget
from PyQt5.QtCore import QThread, pyqtSignal
import asyncio
from downloader.updater import update_files
from logger import log_info, log_error

class PatcherThread(QThread):
    progress_updated = pyqtSignal(int, int)
    update_status = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.success = False
        self.error = ""

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            status_report = loop.run_until_complete(update_files(callback=self.update_progress_bar))
            self.update_status.emit(status_report)
            self.success = True
        except Exception as e:
            self.error = str(e)
            self.success = False
            self.error_occurred.emit(self.error)
        finally:
            loop.close()

    def update_progress_bar(self, progress, total, error=None):
        if error:
            self.error_occurred.emit(error)
        else:
            self.progress_updated.emit(progress, total)

class PatcherGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Patcher GUI')
        self.setGeometry(100, 100, 400, 200)
        self.initUI()

    def initUI(self):
        self.download_button = QPushButton('Download Updates', self)
        self.download_button.clicked.connect(self.start_patcher_thread)
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximum(100)
        
        layout = QVBoxLayout()
        layout.addWidget(self.download_button)
        layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.center()

    def update_progress_bar(self, progress, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(progress)

    def display_update_status(self, status_report):
        updated_files = '\n'.join(status_report['updated'])
        skipped_files = '\n'.join(status_report['skipped'])
        failed_files = '\n'.join(status_report['failed'])
        verified_files = '\n'.join(status_report['verification']['verified'])
        corrupted_files = '\n'.join(status_report['verification']['corrupted'])

        message = f"Updated:\n{updated_files}\n\nSkipped:\n{skipped_files}\n\nFailed:\n{failed_files}"
        if verified_files or corrupted_files:
            message += f"\n\nVerified:\n{verified_files}\n\nCorrupted:\n{corrupted_files}"
        QMessageBox.information(self, 'Update Status', message)

    def patcher_finished(self):
        if self.patcher_thread.success:
            QMessageBox.information(self, 'Success', 'Files have been updated successfully.')
            log_info('Files updated successfully.')
        else:
            QMessageBox.critical(self, 'Error', self.patcher_thread.error)
            log_error(f'Error during patching: {self.patcher_thread.error}')
        self.download_button.setEnabled(True)
        self.progress_bar.setValue(0)

    def start_patcher_thread(self):
        self.download_button.setEnabled(False)
        self.patcher_thread = PatcherThread()
        self.patcher_thread.progress_updated.connect(self.update_progress_bar)
        self.patcher_thread.update_status.connect(self.display_update_status)
        self.patcher_thread.finished.connect(self.patcher_finished)
        self.patcher_thread.start()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

def run():
    app = QApplication(sys.argv)
    window = PatcherGUI()
    window.show()
    sys.exit(app.exec_())