class CLIError(Exception):
    """Base exception for CLI-related errors."""

    def __init__(self, message: str, exit_code: int):
        self.message = message
        self.exit_code = exit_code
        super().__init__(message)


class InvalidArgumentsError(CLIError):
    """Exception for invalid CLI arguments."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=2)


class AllRowsDroppedError(CLIError):
    """Exception when all rows are dropped."""

    def __init__(self, message: str = "All rows were dropped after date parsing. Cannot generate report."):
        super().__init__(message, exit_code=3)


class ReportRenderError(CLIError):
    """Exception for failures during report rendering."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=4)


class FileIOError(CLIError):
    """Exception for file I/O errors."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=5)


class MissingHeadersError(InvalidArgumentsError):
    """Exception raised for missing headers in the input file."""

    def __init__(self, missing: list[str]):
        self.missing = sorted(set(missing))
        message = f"Missing required headers: {', '.join(self.missing)}"
        super().__init__(message)
