# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Custom exceptions for PDF extractors."""


class InvalidPageSelectionError(ValueError):
    """Raised when a requested page selection is invalid for a PDF."""
