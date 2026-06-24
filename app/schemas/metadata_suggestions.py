# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Typed metadata suggestions returned by the workflow."""

# from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


class Creator(BaseModel):
    """A structured creator/author."""

    name: str = Field(
        description="Full name in '<family>, <given>' format",
        examples=["Smith, John"],
    )
    affiliation: str | None = None
    orcid: str | None = None

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
    """Flat schema the LLM fills; converted to ``MetadataSuggestions``.

    Smaller models handle a flat object far better than the discriminated union.
    """

    title: str | None = Field(default=None, description="Document title")
    description: str | None = Field(default=None, description="Abstract or summary")
    creators: list[Creator] = Field(
        default_factory=list, description="Authors or creators"
    )
    doi: str | None = Field(default=None, description="The Digital Object Identifier")
    publication_date: str | None = Field(
        default=None,
        description=(
            "Publication date in ISO 8601, at the precision known: 'YYYY-MM-DD', "
            "'YYYY-MM', or 'YYYY'. Normalize written dates: '17 July 2023' -> "
            "'2023-07-17', 'July 2023' -> '2023-07', '2023' -> '2023'."
        ),
        examples=["2014-07-17", "2014-07", "2014"],
    )

    def to_suggestions(self) -> MetadataSuggestions:
        """Build the typed suggestions, dropping null/empty fields."""
        suggestions: list[MetadataSuggestion] = []
        if self.title:
            suggestions.append(TitleSuggestion(value=self.title))
        if self.description:
            suggestions.append(DescriptionSuggestion(value=self.description))
        if self.creators:
            creators = CreatorsSuggestion(value=self.creators)
            if creators.value:
                suggestions.append(creators)
        if self.doi:
            suggestions.append(DoiSuggestion(value=self.doi))
        if self.publication_date:
            suggestions.append(PublicationDateSuggestion(value=self.publication_date))
        return MetadataSuggestions(suggestions=suggestions)
