import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from types import SimpleNamespace

from zn_report.cli import run_report_workflow, setup_logging
from zn_report.exceptions import CLIError

# Set up logging to capture messages from the workflow
setup_logging("INFO")
logger = logging.getLogger(__name__)


class ReportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZN Report Generator")
        self.root.geometry("400x170")
        self.root.resizable(False, False)

        self.csv_path = tk.StringVar()
        self.result_queue = queue.Queue()

        # Frame for better organization
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # File selection
        select_button = tk.Button(
            main_frame, text="Select CSV File", command=self.select_file
        )
        select_button.pack(pady=5)

        self.path_label = tk.Label(main_frame, textvariable=self.csv_path, wraplength=380)
        self.path_label.pack(pady=5)
        self.csv_path.set("No file selected")

        # Report generation
        self.generate_button = tk.Button(
            main_frame, text="Generate Report", command=self.generate_report
        )
        self.generate_button.pack(pady=10)

        self.status_label = tk.Label(main_frame, text="")
        self.status_label.pack(pady=5)

    def select_file(self):
        filepath = filedialog.askopenfilename(
            title="Select a ServiceNow CSV file",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if filepath:
            self.csv_path.set(filepath)

    def generate_report(self):
        csv_file = self.csv_path.get()
        if not csv_file or csv_file == "No file selected":
            messagebox.showerror("Error", "Please select a CSV file first.")
            return

        self.generate_button.config(state=tk.DISABLED)
        self.status_label.config(text="Generating report...")

        thread = threading.Thread(
            target=self._worker_generate_report, args=(csv_file,), daemon=True
        )
        thread.start()
        self.root.after(100, self._check_queue)

    def _worker_generate_report(self, csv_file):
        try:
            # TODO: Consider making this configurable
            output_path = Path.home() / "Downloads" / "ZS_SNOW_Report.pdf"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            args = SimpleNamespace(
                csv=csv_file,
                out=str(output_path),
                start=None,
                end=None,
                fmt="pdf",
                tz="UTC",
                config=None,
                title=None,
                log_level="INFO",
                chunksize=None,
                ai_summarizer="none",
                summary_max_chars=700,
            )
            logger.info(f"Starting report generation for '{csv_file}'...")
            run_report_workflow(args)
            self.result_queue.put(("success", output_path))
        except (CLIError, Exception) as e:
            self.result_queue.put(("error", e))

    def _check_queue(self):
        try:
            result = self.result_queue.get_nowait()
            self.generate_button.config(state=tk.NORMAL)
            self.status_label.config(text="")

            status, payload = result
            if status == "success":
                messagebox.showinfo(
                    "Success", f"Report successfully generated at:\n{payload}"
                )
                logger.info("Report generation successful.")
            else:
                e = payload
                logger.error(f"An error occurred: {e}", exc_info=True)
                messagebox.showerror(
                    "Error", f"Failed to generate report:\n{getattr(e, 'message', e)}"
                )
        except queue.Empty:
            self.root.after(100, self._check_queue)


def main():
    root = tk.Tk()
    app = ReportApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
