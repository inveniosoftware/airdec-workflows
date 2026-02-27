from io import BytesIO

import httpx
import pdfplumber
from pydantic import BaseModel
from temporalio import activity


class ExtractPdfContentRequest(BaseModel):
    """Request to extract PDF content from a URL."""

    url: str


class ExtractPdfContentResponse(BaseModel):
    """Response containing extracted PDF text and page count."""

    text: str
    num_pages: int


@activity.defn
async def create(request: ExtractPdfContentRequest) -> ExtractPdfContentResponse:
    """Download a PDF from a URL and extract its text content using pdfplumber."""
    async with httpx.AsyncClient() as client:
        response = await client.get(request.url)
        response.raise_for_status()
        pdf_bytes = response.content

    pages_text: list[str] = []
    num_pages = 0
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        num_pages = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

    full_text = "\n\n".join(pages_text)

    return ExtractPdfContentResponse(
        text=full_text,
        num_pages=num_pages,
    )
