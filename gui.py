import tkinter as tk
from tkinter import messagebox, ttk
from threading import Thread
from downloader.updater import update_files
from logger import log_info, log_error

class PatcherGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Patcher GUI')
        self.geometry('400x200')
        self.initialize_gui()
        self.is_updating = False

    def initialize_gui(self):
        self.download_button = tk.Button(self, text='Download Updates', command=self.start_patcher_thread)
        self.download_button.pack(pady=20)
        
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)

    def update_progress_bar(self, progress, total):
        def task():
            self.progress_bar["value"] = progress
            self.progress_bar["maximum"] = total
        self.after(100, task)

    def run_patcher(self):
        self.download_button.config(state='disabled')
        try:
            update_files(callback=self.update_progress_bar)
            messagebox.showinfo('Success', 'Files have been updated successfully.')
            log_info('Files updated successfully.')
        except Exception as e:
            messagebox.showerror('Error', str(e))
            log_error(f'Error during patching: {e}')
        finally:
            self.download_button.config(state='normal')
            self.progress_bar["value"] = 0

    def start_patcher_thread(self):
        if not self.is_updating:
            self.is_updating = True
            patcher_thread = Thread(target=self.run_patcher_wrapper)
            patcher_thread.start()

    def run_patcher_wrapper(self):
        self.run_patcher()
        self.is_updating = False

def run():
    app = PatcherGUI()
    app.mainloop()