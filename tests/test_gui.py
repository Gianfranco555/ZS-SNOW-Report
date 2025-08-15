import unittest


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
