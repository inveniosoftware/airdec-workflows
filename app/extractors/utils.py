# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Utility functions for PDF extractors."""

from typing import List, Optional

from .errors import InvalidPageSelectionError


def resolve_pages(pages: Optional[List[int]], total_pages: int) -> Optional[List[int]]:
    """Resolve page list with negative indices to 0-based page numbers."""
    if total_pages < 1:
        raise InvalidPageSelectionError("Cannot select pages from a PDF with no pages")

    if pages is None:
        pages = [1, 2] if total_pages >= 2 else [1]

    resolved = set()
    for p in pages:
        if p == 0:
            raise InvalidPageSelectionError(
                "Page numbers are 1-based; 0 is not allowed"
            )

        if p > 0:
            if p > total_pages:
                raise InvalidPageSelectionError(
                    f"Page {p} is out of range for a PDF with {total_pages} pages"
                )
            idx = p - 1
        else:
            if p < -total_pages:
                raise InvalidPageSelectionError(
                    f"Page {p} is out of range for a PDF with {total_pages} pages"
                )
            idx = total_pages + p

        resolved.add(idx)
    return sorted(resolved)
