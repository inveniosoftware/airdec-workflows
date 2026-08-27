# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Resolved metadata fields."""

from pydantic import BaseModel, Field


class ResolvedFunder(BaseModel):
    """A funding organization resolved against the funders vocabulary."""

    id: str = Field(
        description="ROR identifier",
        examples=["00k4n6c32", "01cwqze88"],
    )
    name: str = Field(
        description="Funder name",
        examples=["European Commission", "National Institutes of Health"],
    )


class ResolvedAward(BaseModel):
    """An award or grant, resolved against the awards vocabulary."""

    id: str | None = Field(
        default=None,
        description="Award identifier (funder::number); None for unresolved awards",
        examples=["00k4n6c32::101058509", "01cwqze88::5K01HL130704-03"],
    )
    number: str | None = Field(default=None, examples=["101058509", "5K01HL130704-03"])
    title: str | None = Field(
        default=None,
        examples=["SCOAP3", "Intersensory Perception of Social Events"],
    )


class ResolvedFunding(BaseModel):
    """A funding entry with a funder and an award."""

    funder: ResolvedFunder | None = None
    award: ResolvedAward | None = None


class ResolvedLicense(BaseModel):
    """A license resolved against the Invenio licenses vocabulary."""

    id: str = Field(description="SPDX identifier", examples=["cc-by-4.0", "mit"])
    title: str | None = Field(
        default=None,
        examples=["Creative Commons Attribution 4.0 International", "MIT License"],
    )
    description: str | None = None
    link: str | None = Field(
        default=None,
        examples=[
            "https://creativecommons.org/licenses/by/4.0/legalcode",
            "https://opensource.org/licenses/MIT",
        ],
    )
