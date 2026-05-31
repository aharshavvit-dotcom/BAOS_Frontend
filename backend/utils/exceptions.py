"""Custom BAOS exceptions."""


class BAOSException(Exception):
    """Base exception for BAOS domain errors."""


class NotFoundError(BAOSException):
    """Raised when a requested entity is not found."""


class TrainingError(BAOSException):
    """Raised when model training fails."""


class InsufficientDataError(BAOSException):
    """Raised when a model or report lacks enough input data."""


class BerthCapacityError(BAOSException):
    """Raised when a berth cannot safely handle the requested vessel."""


class AuthError(BAOSException):
    """Raised for authentication or authorization failures."""


class SeedAlreadyRunError(BAOSException):
    """Raised when a seed operation is blocked by existing data."""
