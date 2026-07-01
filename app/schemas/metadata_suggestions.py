# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Typed metadata suggestions returned by the workflow."""

# from __future__ import annotations

from typing import Annotated, Literal

from idutils.normalizers import normalize_orcid
from idutils.validators import is_orcid
from pydantic import BaseModel, Field, field_validator


class Creator(BaseModel):
    """A structured creator/author."""

    name: str = Field(
        description="Full name in '<family>, <given>' format",
        examples=["Doe, Jane", "van der Berg, A."],
    )
    affiliation: str | None = Field(
        default=None,
        description="Institution or organization the creator is affiliated with",
        examples=["CERN", "University of Cambridge"],
    )
    orcid: str | None = Field(
        default=None,
        description=(
            "ORCID identifier as the bare 16-digit ID (four groups of four, "
            "final character may be 'X'), without the orcid.org URL prefix"
        ),
        examples=["0000-0002-1111-1115", "0000-0002-6789-012X"],
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize names to the canonical 'Family, Given' format."""
        cleaned = " ".join(v.split()).strip()
        if not cleaned:
            return cleaned
        if "," in cleaned:
            return cleaned
        parts = cleaned.split(" ")
        if len(parts) == 1:
            return f"{parts[0]},"
        family = parts[-1]
        given = " ".join(parts[:-1])
        return f"{family}, {given}"


class TitleSuggestion(BaseModel):
    """Suggestion for `title`."""

    field: Literal["title"] = "title"
    value: str


class DescriptionSuggestion(BaseModel):
    """Suggestion for `description` (abstract)."""

    field: Literal["description"] = "description"
    value: str


class CreatorsSuggestion(BaseModel):
    """Suggestion for `creators`."""

    field: Literal["creators"] = "creators"
    value: list[Creator]

    @field_validator("value")
    @classmethod
    def filter_empty_names(cls, v: list[Creator]) -> list[Creator]:
        """Filter out creators with empty names."""
        return [c for c in v if c.name]


class DoiSuggestion(BaseModel):
    """Suggestion for `doi`."""

    field: Literal["doi"] = "doi"
    value: str


class PublicationDateSuggestion(BaseModel):
    """Suggestion for `publication_date` ."""

    field: Literal["publication_date"] = "publication_date"
    value: str

    @field_validator("value")
    @classmethod
    def normalize_publication_date(cls, v: str) -> str:
        """Collapse whitespace; ISO 8601 date, year-month, and year are all kept."""
        return " ".join(v.split()).strip()


MetadataSuggestion = Annotated[
    TitleSuggestion
    | DescriptionSuggestion
    | CreatorsSuggestion
    | DoiSuggestion
    | PublicationDateSuggestion,
    Field(discriminator="field"),
]


class MetadataSuggestions(BaseModel):
    """Container for all metadata suggestions from a workflow run."""

    suggestions: list[MetadataSuggestion]


class ExtractedMetadata(BaseModel):
    """Flat schema the LLM fills, converted to ``MetadataSuggestions``.

    Creators are parallel lists, not nested objects. gpt-oss-20b fills flat
    top-level lists in a tool call but drops a field nested under each creator,
    so a per-creator ``orcid`` gets lost. ``creator_orcids[i]`` and
    ``creator_affiliations[i]`` belong to ``creators[i]``.
    """

    title: str | None = Field(
        default=None,
        description="Document title",
        examples=["A Concise Title Describing the Work"],
    )
    description: str | None = Field(
        default=None,
        description="Abstract or summary",
        examples=["A short summary of the document's purpose, methods, and findings."],
    )
    creators: list[str] = Field(
        default_factory=list,
        description="Creator full names in '<family>, <given>' format, in order",
        examples=[["Doe, Jane", "van der Berg, A."]],
    )
    creator_orcids: list[str] = Field(
        default_factory=list,
        description=(
            "ORCID iD per creator, parallel to `creators` so creator_orcids[i] "
            "is the ORCID of creators[i]; empty string when an author has none. "
            "Bare 16-digit form (four groups of four, last may be 'X'), no URL."
        ),
        examples=[["0000-0002-1111-1115", ""]],
    )
    creator_affiliations: list[str] = Field(
        default_factory=list,
        description=(
            "Affiliation per creator, parallel to `creators`; empty string when unknown"
        ),
        examples=[["CERN", "University of Cambridge"]],
    )
    doi: str | None = Field(
        default=None,
        description="The Digital Object Identifier, as a bare DOI without a URL prefix",
        examples=["10.1234/example.5678"],
    )
    publication_date: str | None = Field(
        default=None,
        description=(
            "Publication date in ISO 8601, at the precision known: 'YYYY-MM-DD', "
            "'YYYY-MM', or 'YYYY'. Normalize written dates: '17 July 2023' -> "
            "'2023-07-17', 'July 2023' -> '2023-07', '2023' -> '2023'."
        ),
        examples=["2014-07-17", "2014-07", "2014"],
    )

    @staticmethod
    def _at(values: list[str], i: int) -> str:
        """Return the i-th parallel value, or '' when the list is shorter."""
        return values[i] if i < len(values) else ""

    def to_suggestions(self) -> MetadataSuggestions:
        """Build the typed suggestions, dropping null/empty fields."""
        suggestions: list[MetadataSuggestion] = []
        if self.title:
            suggestions.append(TitleSuggestion(value=self.title))
        if self.description:
            suggestions.append(DescriptionSuggestion(value=self.description))
        if self.creators:
            value = []
            for i, name in enumerate(self.creators):
                # Validate/normalize here, not on the LLM output schema, where a
                # fed-back error would make the model invent a valid-looking fake.
                orcid = self._at(self.creator_orcids, i)
                orcid = normalize_orcid(orcid).upper() if is_orcid(orcid) else None
                value.append(
                    Creator(
                        name=name,
                        orcid=orcid,
                        affiliation=self._at(self.creator_affiliations, i) or None,
                    )
                )
            creators = CreatorsSuggestion(value=value)
            if creators.value:
                suggestions.append(creators)
        if self.doi:
            suggestions.append(DoiSuggestion(value=self.doi))
        if self.publication_date:
            suggestions.append(PublicationDateSuggestion(value=self.publication_date))
        return MetadataSuggestions(suggestions=suggestions)
