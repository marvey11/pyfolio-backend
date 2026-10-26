from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.validation import (
    InstrumentType,
    normalise_country_code,
    normalise_isin,
    normalise_text,
    normalise_wkn,
)


class CountryInput(BaseModel):
    code: str
    name: str = Field(min_length=1, max_length=120)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return normalise_country_code(value)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalise_text(value)


class CountryPatch(BaseModel):
    code: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        return normalise_country_code(value) if value is not None else None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return normalise_text(value) if value is not None else None


class CountryOut(CountryInput):
    model_config = ConfigDict(from_attributes=True)


class SecurityInput(BaseModel):
    isin: str
    wkn: str
    name: str = Field(min_length=1, max_length=255)
    instrument_type: InstrumentType
    country_code: str

    @field_validator("isin")
    @classmethod
    def validate_isin(cls, value: str) -> str:
        return normalise_isin(value)

    @field_validator("wkn")
    @classmethod
    def validate_wkn(cls, value: str) -> str:
        return normalise_wkn(value)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalise_text(value)

    @field_validator("country_code")
    @classmethod
    def validate_country(cls, value: str) -> str:
        return normalise_country_code(value)


class SecurityPatch(BaseModel):
    isin: str | None = None
    wkn: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    instrument_type: InstrumentType | None = None
    country_code: str | None = None

    @field_validator("isin")
    @classmethod
    def validate_isin(cls, value: str | None) -> str | None:
        return normalise_isin(value) if value is not None else None

    @field_validator("wkn")
    @classmethod
    def validate_wkn(cls, value: str | None) -> str | None:
        return normalise_wkn(value) if value is not None else None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return normalise_text(value) if value is not None else None

    @field_validator("country_code")
    @classmethod
    def validate_country(cls, value: str | None) -> str | None:
        return normalise_country_code(value) if value is not None else None


class SecurityOut(SecurityInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PaginationOut(BaseModel):
    page: int
    page_size: int = Field(alias="pageSize")
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")
    has_previous_page: bool = Field(alias="hasPreviousPage")
    has_next_page: bool = Field(alias="hasNextPage")


class CountryListOut(BaseModel):
    items: list[CountryOut]
    pagination: PaginationOut


class SecurityListOut(BaseModel):
    items: list[SecurityOut]
    pagination: PaginationOut
