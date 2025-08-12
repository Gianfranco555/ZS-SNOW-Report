class MissingHeadersError(ValueError):
    """Exception raised for missing headers in the input file."""

    def __init__(self, missing: list[str]):
        self.missing = sorted(list(set(missing)))
        message = f"Missing required headers: {', '.join(self.missing)}"
        super().__init__(message)

    def __str__(self) -> str:
        return ",".join(self.missing)
