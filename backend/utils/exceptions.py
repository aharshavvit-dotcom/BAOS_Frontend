"""Custom BAOS exceptions."""


class BAOSException(Exception):
    """Base exception for BAOS domain errors."""


class NotFoundError(BAOSException):
    """Raised when a requested entity is not found."""


class TrainingError(BAOSException):
    """Raised when model training fails."""


class InsufficientDataError(BAOSException):
    """Raised when a model or report lacks enough input data."""
