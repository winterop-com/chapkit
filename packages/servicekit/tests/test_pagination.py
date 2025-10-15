"""Tests for pagination utilities."""

from typing import Any

from servicekit.core import PaginatedResponse
from servicekit.core.api.pagination import PaginationParams, create_paginated_response


def test_pagination_params_is_paginated_both_set() -> None:
    """Test is_paginated returns True when both page and size are set."""
    params = PaginationParams(page=1, size=20)
    assert params.is_paginated() is True


def test_pagination_params_is_paginated_only_page() -> None:
    """Test is_paginated returns False when only page is set."""
    params = PaginationParams(page=1, size=None)
    assert params.is_paginated() is False


def test_pagination_params_is_paginated_only_size() -> None:
    """Test is_paginated returns False when only size is set."""
    params = PaginationParams(page=None, size=20)
    assert params.is_paginated() is False


def test_pagination_params_is_paginated_neither_set() -> None:
    """Test is_paginated returns False when neither page nor size are set."""
    params = PaginationParams(page=None, size=None)
    assert params.is_paginated() is False


def test_pagination_params_defaults() -> None:
    """Test PaginationParams defaults to None for both fields."""
    params = PaginationParams()
    assert params.page is None
    assert params.size is None
    assert params.is_paginated() is False


def test_create_paginated_response() -> None:
    """Test create_paginated_response creates proper response object."""
    items = [{"id": "1", "name": "test"}]
    response = create_paginated_response(items, total=100, page=1, size=10)

    assert response.items == items
    assert response.total == 100
    assert response.page == 1
    assert response.size == 10
    assert response.pages == 10  # 100 / 10


def test_create_paginated_response_partial_page() -> None:
    """Test create_paginated_response calculates pages correctly for partial pages."""
    items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
    response = create_paginated_response(items, total=25, page=1, size=10)

    assert response.total == 25
    assert response.size == 10
    assert response.pages == 3  # ceil(25 / 10) = 3


def test_create_paginated_response_empty() -> None:
    """Test create_paginated_response handles empty results."""
    response: PaginatedResponse[Any] = create_paginated_response([], total=0, page=1, size=10)

    assert response.items == []
    assert response.total == 0
    assert response.page == 1
    assert response.size == 10
    assert response.pages == 0
