import tkinter as tk
import unittest
from unittest.mock import MagicMock

from zn_report.gui import ReportApp


class TestGui(unittest.TestCase):
    def test_import_gui(self):
        """Test that the GUI module can be imported and has a main function."""
        try:
            from zn_report import gui
        except ImportError as e:
            self.fail(f"Failed to import zn_report.gui: {e}")

        self.assertTrue(
            hasattr(gui, "main"), "The gui module should have a 'main' function."
        )

    def test_app_instantiation(self):
        """Test that the ReportApp class can be instantiated correctly."""
        # A real Tk root is needed for Tkinter variables like StringVar
        root = tk.Tk()
        # Prevent the window from appearing during tests
        root.withdraw()

        app = ReportApp(root)

        # Check that the root window is configured as expected
        self.assertEqual(root.title(), "ZN Report Generator")
        # Geometry and resizable are harder to assert reliably across platforms,
        # but we can check that the app object itself is configured.
        self.assertIsInstance(app, ReportApp)
        self.assertIsNotNone(app.csv_path)
        self.assertIsNotNone(app.result_queue)

        # Clean up the root window
        root.destroy()
