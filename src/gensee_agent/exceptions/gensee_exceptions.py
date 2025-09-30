class GenseeError(Exception):
    """Base exception for Gensee-related errors."""
    def __init__(self, message: str, retryable: bool):
        super().__init__(message)
        self.message = message
        self.retryable = retryable

    def __str__(self):
        return f"{self.message} (Retryable: {self.retryable})"

class ImplementationError(GenseeError):
    """Custom exception for errors in implementation."""

class ToolExecutionError(GenseeError):
    """Custom exception for errors during tool execution."""

class ToolParsingError(GenseeError):
    """Custom exception for errors during tool parsing."""