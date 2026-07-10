# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Tests for resolve_pages page-selection utility."""

import pytest

from app.extractors.errors import InvalidPageSelectionError
from app.extractors.utils import resolve_pages


@pytest.mark.parametrize(
    ("total_pages", "expected"),
    [
        (1, [0]),
        (2, [0, 1]),
        (5, [0, 1]),
    ],
)
def test_pages_none(total_pages, expected):
    """pages=None resolves to [1,2] for multi-page files and [1] for single-page."""
    assert resolve_pages(None, total_pages) == expected


@pytest.mark.parametrize(
    ("pages", "total_pages", "expected"),
    [
        ([1], 1, [0]),
        ([1, 2], 2, [0, 1]),
        ([1, 2], 5, [0, 1]),
        ([-1], 3, [2]),  # last page
        ([-2, -1], 3, [1, 2]),  # last two pages
    ],
)
def test_explicit_pages(pages, total_pages, expected):
    """Explicit pages passed should resolve correctly considering 1-based indexing."""
    assert resolve_pages(pages, total_pages) == expected


def test_explicit_out_of_range():
    """Explicit [1, 2] on a single-page file must raise."""
    with pytest.raises(InvalidPageSelectionError, match="out of range"):
        resolve_pages([1, 2], 1)


def test_zero_page():
    """Passing 0 in pages must raise, as 0 is not allowed."""
    with pytest.raises(InvalidPageSelectionError, match="1-based"):
        resolve_pages([0, 1], 3)


def test_empty_pdf():
    """Empty files raise an error."""
    with pytest.raises(InvalidPageSelectionError, match="no pages"):
        resolve_pages(None, 0)
