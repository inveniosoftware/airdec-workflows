# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

from datetime import timedelta
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel
from temporalio import activity
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from app.config import get_settings
from app.extractors import get_extractor
from app.extractors.errors import InvalidPageSelectionError

EXTRACT_PDF_TEXT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=1.0,
    maximum_interval=timedelta(seconds=1),
    maximum_attempts=2,
)


class ExtractPdfContentRequest(BaseModel):
    """Request to extract PDF content from a URL."""

    url: str
    extractor: str = "pdfplumber"  # Default to pdfplumber
    pages: list[int] | None = None  # Optional list of page numbers (1-indexed)


class ExtractPdfContentResponse(BaseModel):
    """Response containing extracted PDF text and page numbers."""

    text: str
    extractor: str
    pages_extracted: list[int]  # List of 1-indexed page numbers that were extracted


def _http_verify_for_pdf_url(url: str) -> bool:
    settings = get_settings()

    parsed_url = urlparse(url)
    hostname = (parsed_url.hostname or "").lower()

    if hostname in ("localhost", "127.0.0.1", "::1") or hostname.endswith(".localhost"):
        return False

    allowlist = {
        host.strip().lower()
        for host in (settings.pdf_http_allowlist or "").split(",")
        if host.strip()
    }

    if hostname not in allowlist:
        raise ValueError(f"PDF downloads from '{hostname}' are not allowed")

    return True


@activity.defn
async def extract_pdf_text(
    request: ExtractPdfContentRequest,
) -> ExtractPdfContentResponse:
    """Download PDF from a URL and extract its content using the specified extractor."""
    try:
        verify = _http_verify_for_pdf_url(request.url)
    except ValueError as e:
        raise ApplicationError(
            str(e),
            type="HostNotAllowed",
            non_retryable=True,
        ) from e

    async with httpx.AsyncClient(verify=verify) as client:
        response = await client.get(request.url)
        response.raise_for_status()
        pdf_bytes = response.content

    # Extract content using the extraction module
    try:
        extractor = get_extractor(request.extractor)
    except ValueError as e:
        # Convert ValueError to non-retryable ApplicationError for proper
        # Temporal error handling
        raise ApplicationError(
            str(e),
            type="InvalidExtractor",
            non_retryable=True,
        ) from e

    try:
        result = extractor.extract(pdf_bytes, request.pages)
    except InvalidPageSelectionError as e:
        raise ApplicationError(
            str(e),
            type="InvalidPageSelection",
            non_retryable=True,
        ) from e

    return ExtractPdfContentResponse(
        text=result["full_text"],
        pages_extracted=result["pages_extracted"],
        extractor=request.extractor,
    )
