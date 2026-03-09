class HyaenaError(Exception):
    """Base for all Hyaena SDK errors."""


class HyaenaNotInitializedError(HyaenaError):
    """Raised when the SDK is used before hyaena.init() is called."""


class HyaenaConfigError(HyaenaError):
    """Raised when SDK configuration is invalid."""
