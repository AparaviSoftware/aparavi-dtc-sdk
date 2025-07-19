"""
Aparavi SDK - Python client library for Aparavi Web Services API
"""

from .client import AparaviClient
from .models import ResultBase, Result, ValidationError
from .exceptions import AparaviError, AuthenticationError, ValidationError as SDKValidationError

__version__ = "0.1.0"
__all__ = [
    "AparaviClient",
    "ResultBase", 
    "Result",
    "ValidationError",
    "AparaviError",
    "AuthenticationError",
    "SDKValidationError"
]
