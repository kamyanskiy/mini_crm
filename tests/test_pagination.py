"""Tests for pagination dependency."""

import pytest
from fastapi import status
from httpx import AsyncClient

from models.organization import Organization


@pytest.mark.asyncio
class TestPaginationValidation:
    """Test pagination parameter validation."""

    async def test_negative_page_rejected(
        self, client: AsyncClient, organization: Organization, owner_headers: dict
    ):
        """Test that negative page number is rejected."""
        headers = {**owner_headers, "X-Organization-ID": str(organization.id)}

        response = await client.get(
            "/api/v1/contacts",
            params={"page": -1},
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_zero_page_rejected(
        self, client: AsyncClient, organization: Organization, owner_headers: dict
    ):
        """Test that page 0 is rejected."""
        headers = {**owner_headers, "X-Organization-ID": str(organization.id)}

        response = await client.get(
            "/api/v1/contacts",
            params={"page": 0},
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_negative_page_size_rejected(
        self, client: AsyncClient, organization: Organization, owner_headers: dict
    ):
        """Test that negative page_size is rejected."""
        headers = {**owner_headers, "X-Organization-ID": str(organization.id)}

        response = await client.get(
            "/api/v1/contacts",
            params={"page_size": -10},
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_zero_page_size_rejected(
        self, client: AsyncClient, organization: Organization, owner_headers: dict
    ):
        """Test that page_size 0 is rejected."""
        headers = {**owner_headers, "X-Organization-ID": str(organization.id)}

        response = await client.get(
            "/api/v1/contacts",
            params={"page_size": 0},
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_excessive_page_size_rejected(
        self, client: AsyncClient, organization: Organization, owner_headers: dict
    ):
        """Test that page_size > 100 is rejected."""
        headers = {**owner_headers, "X-Organization-ID": str(organization.id)}

        response = await client.get(
            "/api/v1/contacts",
            params={"page_size": 101},
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_valid_pagination_accepted(
        self, client: AsyncClient, organization: Organization, owner_headers: dict
    ):
        """Test that valid pagination parameters work."""
        headers = {**owner_headers, "X-Organization-ID": str(organization.id)}

        response = await client.get(
            "/api/v1/contacts",
            params={"page": 1, "page_size": 50},
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_pagination_works_for_deals(
        self, client: AsyncClient, organization: Organization, owner_headers: dict
    ):
        """Test that pagination dependency works for deals endpoint."""
        headers = {**owner_headers, "X-Organization-ID": str(organization.id)}

        # Negative page
        response = await client.get(
            "/api/v1/deals",
            params={"page": -1},
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Valid pagination
        response = await client.get(
            "/api/v1/deals",
            params={"page": 1, "page_size": 20},
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
