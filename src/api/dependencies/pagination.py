"""Pagination dependency."""

from fastapi import Query


class PaginationParams:
    """Pagination parameters with validation."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (starts from 1)"),
        page_size: int = Query(100, ge=1, le=100, description="Number of items per page"),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def skip(self) -> int:
        """Calculate skip offset for database queries."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.page_size
