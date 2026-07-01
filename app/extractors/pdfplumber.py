# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""PDFPlumber-based PDF extractor."""

import re
from io import BytesIO
from typing import Any, Dict, List, Optional

from .base import BaseExtractor
from .utils import resolve_pages

# Tolerances in PDF points for tying an ORCID icon to its author's name: the
# icon sits on the name's text line, just past its right edge. Empirical, tuned
# on the sample papers.
_SAME_LINE_PT = 6  # max vertical gap counting word and icon as one line
_ICON_GAP_PT = 2  # max horizontal gap from the word's right edge to the icon


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
        affiliation marker, e.g. "Smith1,2"). Edits are collected and applied in
        a single pass.
        """
        words = None
        edits: list[tuple[int, str]] = []
        for annot in annots:
            orcid = self._extract_orcid_id(annot.get("uri") or "")
            if not orcid:
                continue
            if words is None:
                words = page.extract_words(x_tolerance=2)
            on_line = [
                i
                for i, w in enumerate(words)
                if abs(w["top"] - annot["top"]) < _SAME_LINE_PT
                and w["x1"] <= annot["x0"] + _ICON_GAP_PT
            ]
            if not on_line:
                continue
            idx = max(on_line, key=lambda i: words[i]["x1"])
            anchor = words[idx]["text"]
            # Match the anchor as a whole whitespace-bounded token at its own
            # occurrence, so a prefix like "Alex" can't land inside "Alexandra"
            # and marker-suffixed tokens (e.g. "Smith1,2") still match.
            ordinal = sum(1 for w in words[:idx] if w["text"] == anchor)
            occ = list(re.finditer(rf"(?<!\S){re.escape(anchor)}(?!\S)", text))
            if ordinal < len(occ):
                edits.append((occ[ordinal].end(), orcid))

        if not edits:
            return text
        edits.sort()
        parts, prev = [], 0
        for offset, orcid in edits:
            parts.append(text[prev:offset])
            parts.append(f" (ORCID: {orcid})")
            prev = offset
        parts.append(text[prev:])
        return "".join(parts)

    def _extract_orcid_id(self, url: str) -> str | None:
        """Extract ORCID ID from an orcid.org URL."""
        match = re.search(r"orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", url)
        return match.group(1) if match else None
