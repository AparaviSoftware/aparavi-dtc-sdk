"""
Custom exceptions for Aparavi SDK
"""


class AparaviError(Exception):
    """Base exception for Aparavi SDK"""
    pass


class AuthenticationError(AparaviError):
    """Raised when authentication fails"""
    pass


class ValidationError(AparaviError):
    """Raised when validation fails"""
    pass


class TaskNotFoundError(AparaviError):
    """Raised when a task is not found"""
    pass


class PipelineError(AparaviError):
    """Raised when pipeline operations fail"""
    pass

