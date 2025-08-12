class MissingHeadersError(ValueError):
    """Exception raised for missing headers in the input file."""

    def __init__(self, missing: list[str]):
        self.missing = sorted(set(missing))
        message = f"Missing required headers: {', '.join(self.missing)}"
        super().__init__(message)
