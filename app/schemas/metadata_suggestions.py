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


class Funding(BaseModel):
    """A structured funding/grant."""

    funder: str | None = Field(
        default=None,
        description="Name of the funding organization or agency",
        examples=["European Commission", "NSF", "Wellcome Trust"],
    )
    award_number: str | None = Field(
        default=None,
        description="Number of the grant agreement",
        examples=["101058509", "2410342"],
    )
    award_title: str | None = Field(
        default=None,
        description="Name of funding award, project or grant",
        examples=["SCOAP3", "ObsSea4Clim", "European Citizen Science"],
    )


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


class LicenseSuggestion(BaseModel):
    """Suggestion for `license` ."""

    field: Literal["license"] = "license"
    value: list[str]

    @field_validator("value")
    @classmethod
    def lowercase_licenses(cls, licenses: list[str]) -> list[str]:
        """Set SPDX id of licenses to lowercase."""
        return [lic.lower() for lic in licenses]


class FundingSuggestion(BaseModel):
    """Suggestion for `funding` (awards/grants)."""

    field: Literal["funding"] = "funding"
    value: list[Funding]


class CopyrightSuggestion(BaseModel):
    """Suggestion for `copyright` ."""

    field: Literal["copyright"] = "copyright"
    value: str


MetadataSuggestion = Annotated[
    TitleSuggestion
    | DescriptionSuggestion
    | CreatorsSuggestion
    | DoiSuggestion
    | PublicationDateSuggestion
    | LicenseSuggestion
    | FundingSuggestion
    | CopyrightSuggestion,
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
        description=(
            "Abstract or executive summary of the document, copied word-for-word, "
            "complete and unchanged; never paraphrase, shorten, or write a new "
            "summary. Null if the document has no abstract or summary."
        ),
        examples=["The abstract of the document, word for word."],
    )
    creators: list[str] = Field(
        default_factory=list,
        description=(
            "Creator full names in '<family>, <given>' format, in order. Include "
            "every author named in the document; never truncate the list or use "
            "et al."
        ),
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
            "Affiliation per creator, parallel to `creators`; empty string when "
            "unknown. Affiliations are often marked with numbers or symbols after "
            "author names; resolve each author's marker to its affiliation. Copy "
            "the affiliation as written, including any department or institute, "
            "but leave out the marker and any street address, city, postal code, "
            "or country: 'CERN, Geneva, Switzerland' -> 'CERN'. If an author has "
            "several affiliations, give the first."
        ),
        examples=[["CERN", "Department of Physics, University of Oxford"]],
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
    license: list[str] = Field(
        default_factory=list,
        description=(
            "SPDX id of the license. Might be preceded by 'licensed under'. Translate "
            "license names to the SPDX id. For example, 'Creative Commons Attribution "
            "4.0 International' should be returned as 'cc-by-4.0'."
        ),
        examples=[["mit", "apache-2.0", "cc-by-4.0", "gpl-3.0-only"]],
    )
    funding: list[str] = Field(
        default_factory=list,
        description=(
            "Name of funding awards or projects financing the research. Strip "
            "any surrounding phrases ('funded by', 'funded under', 'with support "
            "from', etc.) and trailing punctuation. Prefer this field over `funder` "
            "unless only a funding organization with no specific project is available."
        ),
        examples=[["SCOAP3", "ObsSea4Clim", "European Citizen Science (ECS)"]],
    )
    funding_funders: list[str] = Field(
        default_factory=list,
        description=(
            "Funding organization or agency names, parallel to `funding` so "
            "funding_funders[i] is the funder of funding[i]; empty string if "
            "the funder is not stated. Only set this when there is a distinct "
            "funding body separate and different from the award."
        ),
        examples=[["European Commission", "NSF", ""]],
    )
    funding_numbers: list[str] = Field(
        default_factory=list,
        description=(
            "List of funding numbers or grant agreements, parallel to `funding` so "
            "funding_numbers[i] is the grant agreement of funding[i]; empty string "
            "if there is no grant agreement stated. Might be preceded by expressions "
            "such as 'grant agreement' or 'GA nr.' or 'project no.'."
        ),
        examples=[["101058509", "2410342", "801954"]],
    )
    copyright: str | None = Field(
        default=None,
        description=(
            "Copyright statement. Often follows '© Copyright' and might include a "
            "year, which should also be returned. Do not include the © symbol, the "
            "word 'Copyright' itself, or any '(cid:N)' sequences."
        ),
        examples=["2025 CERN", "The Authors", "2020 Jane Doe", "The Authors 1999"],
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
        if self.license:
            suggestions.append(LicenseSuggestion(value=self.license))
        if self.funding or self.funding_funders or self.funding_numbers:
            size = max(
                len(self.funding), len(self.funding_funders), len(self.funding_numbers)
            )
            value = []
            for i in range(size):
                title = self._at(self.funding, i)
                funder = self._at(self.funding_funders, i)
                number = self._at(self.funding_numbers, i)
                entry = Funding(
                    funder=funder or None,
                    award_title=title or None,
                    award_number=number or None,
                )
                if entry.funder or entry.award_title or entry.award_number:
                    value.append(entry)
            fundings = FundingSuggestion(value=value)
            if fundings.value:
                suggestions.append(fundings)
        if self.copyright:
            suggestions.append(CopyrightSuggestion(value=self.copyright))
        return MetadataSuggestions(suggestions=suggestions)
