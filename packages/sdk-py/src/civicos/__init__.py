"""
CivicOS Python SDK — pip package ``civicos``.

Usage::

    import civicos

    client = civicos.Client(base_url="https://api.example.com")
    programs = client.programs.list(city="boston", category="housing")
    boston = client.cities.get("boston")
    results = client.search("rental assistance")
"""

from __future__ import annotations

from typing import Any

import httpx

__version__ = "0.1.0"
__all__ = ["CivicOSError", "Client"]


class CivicOSError(Exception):
    """Raised when the CivicOS API returns an error."""


def _check_response(response: httpx.Response) -> dict[str, Any]:
    """Raise CivicOSError on non-2xx, otherwise return JSON body."""
    if not response.is_success:
        ct = response.headers.get("content-type", "")
        detail = response.json() if ct.startswith("application/json") else response.text
        raise CivicOSError(f"HTTP {response.status_code}: {detail}")
    return response.json()


class _ProgramsMixin:
    """Mixin providing program-related API calls."""

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def list(
        self,
        city: str | None = None,
        category: str | None = None,
        language: str | None = None,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List programs with optional filters.

        Args:
            city: City slug (e.g. ``"boston"``).
            category: Category slug (e.g. ``"housing"``).
            language: Language code (e.g. ``"es"``).
            status: ``"active"``, ``"inactive"``, or ``"all"``.
            page: Page number (1-indexed).
            limit: Results per page (max 100).
        """
        params: dict[str, Any] = {"page": page, "limit": limit}
        if city:
            params["city"] = city
        if category:
            params["category"] = category
        if language:
            params["language"] = language
        if status:
            params["status"] = status
        return self._get("/v1/programs", **params)

    def get(self, program_id: str) -> dict[str, Any]:
        """Get a single program by ID."""
        return self._get(f"/v1/programs/{program_id}")

    def history(self, program_id: str) -> dict[str, Any]:
        """Get version history for a program."""
        return self._get(f"/v1/programs/{program_id}/history")


class _CitiesMixin:
    """Mixin providing city-related API calls."""

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def list(self, page: int = 1, limit: int = 50) -> dict[str, Any]:
        """List cities covered by CivicOS."""
        return self._get("/v1/cities", page=page, limit=limit)

    def get(self, slug: str) -> dict[str, Any]:
        """Get a city by slug."""
        return self._get(f"/v1/cities/{slug}")

    def programs(
        self,
        slug: str,
        category: str | None = None,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List programs for a specific city."""
        params: dict[str, Any] = {"page": page, "limit": limit}
        if category:
            params["category"] = category
        if status:
            params["status"] = status
        return self._get(f"/v1/cities/{slug}/programs", **params)


class _CategoriesMixin:
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def list(self) -> list[dict[str, Any]]:
        """List all program categories."""
        return self._get("/v1/categories")


class _SearchMixin:
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def search(self, q: str, page: int = 1, limit: int = 20) -> dict[str, Any]:
        """Full-text search across programs."""
        return self._get("/v1/search", q=q, page=page, limit=limit)


class Programs(_ProgramsMixin):
    def __init__(self, client: Client):
        self._client = client

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        return self._client._get(path, **params)


class Cities(_CitiesMixin):
    def __init__(self, client: Client):
        self._client = client

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        return self._client._get(path, **params)


class Categories(_CategoriesMixin):
    def __init__(self, client: Client):
        self._client = client

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        return self._client._get(path, **params)


class Search(_SearchMixin):
    def __init__(self, client: Client):
        self._client = client

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        return self._client._get(path, **params)


class Client:
    """CivicOS API client.

    Args:
        base_url: Base URL of the CivicOS API (e.g. ``"http://localhost:8000"``).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

        self.programs = Programs(self)
        self.cities = Cities(self)
        self.categories = Categories(self)
        self.search = Search(self)

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        """Internal GET request with error handling."""
        # Remove None params
        clean_params = {k: v for k, v in params.items() if v is not None}
        response = self._client.get(f"{self._base_url}{path}", params=clean_params)
        return _check_response(response)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
