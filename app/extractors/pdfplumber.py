# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""PDFPlumber-based PDF extractor."""

import re
from io import BytesIO
from typing import Any, Dict, List, Optional

from .base import BaseExtractor
from .utils import resolve_pages


class PdfplumberExtractor(BaseExtractor):
    """Extract content using pdfplumber."""

    def extract(
        self, pdf_bytes: bytes, pages: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Extract content from PDF using pdfplumber."""
        import pdfplumber

        full_text_parts = []
        tables = []
        hyperlinks = []

        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)

            resolved_pages = resolve_pages(pages, page_count)
            page_indices = resolved_pages if resolved_pages else range(page_count)

            for page_num in page_indices:
                page = pdf.pages[page_num]
                page_annots = page.annots or []
                # x_tolerance=2: the default (3) merges spaced words like "PhilipBull"
                text = page.extract_text(x_tolerance=2) or ""
                # ORCIDs live only in link annotations. Splice each one next to its
                # author so the pairing survives; a bare list misaligns when some
                # authors have no ORCID.
                text = self._inline_orcids(page, text, page_annots)
                full_text_parts.append(text)

                page_tables = page.extract_tables()
                for table in page_tables:
                    if table:
                        tables.append(
                            {
                                "page": page_num + 1,
                                "rows": len(table),
                                "data": table,
                            }
                        )

                for annot in page_annots:
                    uri = annot.get("uri")
                    if uri:
                        link_type = self._classify_link(uri)
                        hyperlinks.append(
                            {
                                "url": uri,
                                "page": page_num + 1,
                                "type": link_type,
                            }
                        )

        # Tables go in `extra`, not `full_text`; the page text already holds each
        # cell in reading order.
        full_text = "\n\n".join(full_text_parts)

        return {
            "full_text": full_text,
            "page_count": page_count,
            "pages_extracted": (
                [i + 1 for i in page_indices]
                if resolved_pages
                else list(range(1, page_count + 1))
            ),
            "extra": {
                "hyperlinks": hyperlinks,
                "tables": tables,
            },
        }

    def _inline_orcids(self, page, text: str, annots: list) -> str:
        """Splice each ORCID inline after the author its icon is anchored to.

        The icon sits just right of the author on the same line, so the word
        ending nearest left of it is that author's token (name plus any
        affiliation marker, e.g. "Bull1,2"). The first text match is the author
        block near the top of the page.
        """
        words = None
        for annot in annots:
            orcid = self._extract_orcid_id(annot.get("uri") or "")
            if not orcid:
                continue
            if words is None:
                words = page.extract_words(x_tolerance=2)
            on_line = [
                w
                for w in words
                if abs(w["top"] - annot["top"]) < 6 and w["x1"] <= annot["x0"] + 2
            ]
            if not on_line:
                continue
            anchor = max(on_line, key=lambda w: w["x1"])["text"].strip(" ,;")
            if anchor and anchor in text:
                text = text.replace(anchor, f"{anchor} (ORCID: {orcid})", 1)
        return text

    def _extract_orcid_id(self, url: str) -> str | None:
        """Extract ORCID ID from an orcid.org URL."""
        match = re.search(r"orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", url)
        return match.group(1) if match else None
