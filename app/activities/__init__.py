"""Activities for the Orcha application."""

from .extract_metadata import extract_metadata_with_llm
from .extract_pdf_content import extract_pdf_text
from .store_workflow_result import store_workflow_result

REGISTERED_ACTIVITIES = [
    extract_pdf_text,
    extract_metadata_with_llm,
    store_workflow_result,
]

__all__ = [
    "REGISTERED_ACTIVITIES",
    "extract_pdf_text",
    "extract_metadata_with_llm",
    "store_workflow_result",
]
