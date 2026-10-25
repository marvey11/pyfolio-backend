from __future__ import annotations

import re
from enum import StrEnum

import pycountry


class InstrumentType(StrEnum):
    STOCK = "stock"
    ETF = "etf"
    BOND = "bond"
    CERTIFICATE = "certificate"
    FUND = "fund"


def normalise_text(value: str) -> str:
    result = value.strip()
    if not result:
        raise ValueError("must not be blank")
    return result


def normalise_country_code(value: str) -> str:
    code = value.strip().upper()
    if (
        not re.fullmatch(r"[A-Z]{2}", code)
        or pycountry.countries.get(alpha_2=code) is None  # pyright: ignore[reportUnknownMemberType]
    ):
        raise ValueError("must be a valid ISO 3166-1 alpha-2 code")
    return code


def normalise_currency_code(value: str) -> str:
    code = value.strip().upper()
    if (
        not re.fullmatch(r"[A-Z]{3}", code)
        or pycountry.currencies.get(alpha_3=code) is None  # pyright: ignore[reportUnknownMemberType]
    ):
        raise ValueError("must be a valid ISO 4217 code")
    return code


def normalise_isin(value: str) -> str:
    isin = value.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
        raise ValueError("must be a valid ISIN")
    expanded = "".join(str(ord(char) - 55) if char.isalpha() else char for char in isin)
    checksum = 0
    for index, digit in enumerate(reversed(expanded)):
        doubled_digit = int(digit) * (2 if index % 2 else 1)
        checksum += doubled_digit // 10 + doubled_digit % 10
    if checksum % 10:
        raise ValueError("has an invalid ISIN checksum")
    return isin


def normalise_wkn(value: str) -> str:
    wkn = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{6}", wkn):
        raise ValueError("must contain exactly six letters or digits")
    return wkn


def normalise_exchange(value: str) -> str:
    return normalise_text(value).upper()
