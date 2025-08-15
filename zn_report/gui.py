import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from types import SimpleNamespace

from zn_report.cli import run_report_workflow, setup_logging
from zn_report.exceptions import CLIError

# Set up logging to capture messages from the workflow
DEFAULT_LOG_LEVEL = "INFO"
setup_logging(DEFAULT_LOG_LEVEL)
logger = logging.getLogger(__name__)


class ReportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZN Report Generator")
        self.root.geometry("400x150")
        self.root.resizable(False, False)

        self.csv_path = tk.StringVar()

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
        generate_button = tk.Button(
            main_frame, text="Generate Report", command=self.generate_report
        )
        generate_button.pack(pady=10)

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

        output_path = Path.home() / "ZS_SNOW_Report.pdf"

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
            auto_dates=True, # Not a real arg, but reflects the logic
        )

        try:
            logger.info(f"Starting report generation for '{csv_file}'...")
            run_report_workflow(args)
            messagebox.showinfo(
                "Success", f"Report successfully generated at:\n{output_path}"
            )
            logger.info("Report generation successful.")
        except CLIError as e:
            logger.error(f"A known error occurred: {e.message}")
            messagebox.showerror("Error", f"Failed to generate report:\n{e.message}")
        except Exception as e:
            logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
            messagebox.showerror(
                "Critical Error", f"An unexpected error occurred:\n{e}"
            )


def main():
    root = tk.Tk()
    app = ReportApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
