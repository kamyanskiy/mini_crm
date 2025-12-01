"""Custom exceptions for the CRM application."""

from fastapi import status


class CRMException(Exception):
    """Base exception for all CRM-related errors."""

    def __init__(
        self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class PermissionDenied(CRMException):
    """Raised when user doesn't have permission to access/modify a resource."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class ResourceNotFound(CRMException):
    """Raised when a resource is not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class BusinessRuleViolation(CRMException):
    """Raised when a business rule is violated."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)


class InvalidOrganizationContext(CRMException):
    """Raised when organization context is invalid or missing."""

    def __init__(self, message: str = "Invalid organization context") -> None:
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class AuthenticationError(CRMException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class ConflictError(CRMException):
    """Raised when operation conflicts with current state."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)
