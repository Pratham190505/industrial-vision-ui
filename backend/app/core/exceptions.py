import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class WarehouseVisionException(Exception):
    """Base exception for all application-specific errors."""

    def __init__(self, message: str = "An unexpected error occurred."):
        self.message = message
        super().__init__(self.message)


class EntityNotFoundError(WarehouseVisionException):
    """Raised when a requested resource was not found."""

    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(f"{entity_name} with id '{entity_id}' not found.")
        self.entity_name = entity_name
        self.entity_id = entity_id


class DatabaseConnectionError(WarehouseVisionException):
    """Raised when MongoDB connection fails or is unavailable."""

    def __init__(self, message: str = "Database service is temporarily unavailable."):
        super().__init__(message)


class FileValidationError(WarehouseVisionException):
    """Raised when uploaded file violates validation rules."""

    def __init__(self, message: str):
        super().__init__(message)


class FileSizeExceededError(FileValidationError):
    """Raised when uploaded file exceeds maximum allowed size (HTTP 413)."""

    def __init__(self, message: str):
        super().__init__(message)


class AuthenticationError(WarehouseVisionException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Could not validate credentials."):
        super().__init__(message)


class AuthorizationError(WarehouseVisionException):
    """Raised when user lacks permission for action."""

    def __init__(self, message: str = "Permission denied."):
        super().__init__(message)


def setup_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers with the FastAPI application."""

    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.message, "error_type": "entity_not_found"},
        )

    @app.exception_handler(FileValidationError)
    async def file_validation_handler(request: Request, exc: FileValidationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.message, "error_type": "file_validation_error"},
        )

    @app.exception_handler(FileSizeExceededError)
    async def file_size_exceeded_handler(request: Request, exc: FileSizeExceededError):
        return JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={"detail": exc.message, "error_type": "file_size_exceeded"},
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.message, "error_type": "authentication_error"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": exc.message, "error_type": "authorization_error"},
        )

    @app.exception_handler(DatabaseConnectionError)
    async def database_connection_handler(request: Request, exc: DatabaseConnectionError):
        logger.error("Database connection exception encountered: %s", exc.message)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Database service is temporarily unavailable.", "error_type": "database_error"},
        )
