# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Activities for the Orcha application."""

from .extract_metadata import extract_metadata_with_llm
from .extract_pdf_content import extract_pdf_text
from .update_workflow import update_workflow

REGISTERED_ACTIVITIES = [
    extract_pdf_text,
    extract_metadata_with_llm,
    update_workflow,
]

__all__ = [
    "REGISTERED_ACTIVITIES",
    "extract_pdf_text",
    "extract_metadata_with_llm",
    "update_workflow",
]
