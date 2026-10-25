from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from core.models import Country, Currency, FxRate, Security, SecurityQuote

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ConflictError(Exception):
    pass


def save(session: Session, entity: object) -> object:
    session.add(entity)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        logger.warning("Persistence conflict while saving %s", type(entity).__name__)
        raise ConflictError(
            "resource conflicts with existing data or a missing reference"
        ) from error
    session.refresh(entity)
    return entity


def create_country(session: Session, code: str, name: str) -> Country:
    country = Country(code=code, name=name)
    if session.get(Country, country.code) is not None:
        raise ConflictError("country code already exists")
    return save(session, country)  # type: ignore[return-value]


def create_security(
    session: Session,
    *,
    isin: str,
    wkn: str,
    name: str,
    instrument_type: str,
    country_code: str,
) -> Security:
    security = Security(
        isin=isin,
        wkn=wkn,
        name=name,
        instrument_type=instrument_type,
        country_code=country_code,
    )
    duplicate = session.scalar(
        select(Security).where(
            or_(Security.isin == security.isin, Security.wkn == security.wkn)
        )
    )
    if duplicate is not None:
        raise ConflictError("ISIN or WKN already exists")
    return save(session, security)  # type: ignore[return-value]


def create_currency(session: Session, code: str, name: str) -> Currency:
    currency = Currency(code=code, name=name)
    if session.get(Currency, currency.code) is not None:
        raise ConflictError("currency code already exists")
    return save(session, currency)  # type: ignore[return-value]


def record_quote(
    session: Session,
    *,
    security_id: int,
    quote_date: date,
    exchange: str,
    closing_price: Decimal,
    currency_code: str,
    source: str | None = None,
) -> SecurityQuote:
    quote = SecurityQuote(
        security_id=security_id,
        quote_date=quote_date,
        exchange=exchange,
        closing_price=closing_price,
        currency_code=currency_code,
        source=source,
    )
    existing = session.scalar(
        select(SecurityQuote).where(
            SecurityQuote.security_id == security_id,
            SecurityQuote.quote_date == quote.quote_date,
            SecurityQuote.exchange == quote.exchange,
        )
    )
    if existing:
        if (
            existing.closing_price == closing_price
            and existing.currency_code == quote.currency_code
        ):
            return existing
        logger.warning(
            "Conflicting quote for security_id=%s date=%s exchange=%s "
            "existing=%s %s requested=%s %s",
            security_id,
            quote_date,
            quote.exchange,
            existing.closing_price,
            existing.currency_code,
            closing_price,
            quote.currency_code,
        )
        raise ConflictError(
            "conflicting quote already exists for security, date and exchange"
        )
    try:
        return save(session, quote)  # type: ignore[return-value]
    except ConflictError as error:
        existing = session.scalar(
            select(SecurityQuote).where(
                SecurityQuote.security_id == security_id,
                SecurityQuote.quote_date == quote.quote_date,
                SecurityQuote.exchange == quote.exchange,
            )
        )
        if (
            existing is not None
            and existing.closing_price == closing_price
            and existing.currency_code == quote.currency_code
        ):
            return existing
        if existing is None:
            raise error
        logger.warning(
            "Concurrent conflicting quote for security_id=%s date=%s exchange=%s "
            "existing=%s %s requested=%s %s",
            security_id,
            quote_date,
            quote.exchange,
            existing.closing_price,
            existing.currency_code,
            closing_price,
            quote.currency_code,
        )
        raise ConflictError(
            "conflicting quote already exists for security, date and exchange"
        )


def record_fx_rate(
    session: Session,
    *,
    currency_code: str,
    rate_date: date,
    rate: Decimal,
    source: str | None = None,
) -> FxRate:
    fx = FxRate(
        currency_code=currency_code, rate_date=rate_date, rate=rate, source=source
    )
    existing = session.scalar(
        select(FxRate).where(
            FxRate.currency_code == fx.currency_code, FxRate.rate_date == fx.rate_date
        )
    )
    if existing:
        if existing.rate == rate:
            return existing
        logger.warning(
            "Conflicting FX rate for currency=%s date=%s", fx.currency_code, rate_date
        )
        raise ConflictError("conflicting FX rate already exists for currency and date")
    try:
        return save(session, fx)  # type: ignore[return-value]
    except ConflictError as error:
        existing = session.scalar(
            select(FxRate).where(
                FxRate.currency_code == fx.currency_code,
                FxRate.rate_date == fx.rate_date,
            )
        )
        if existing is not None and existing.rate == rate:
            return existing
        if existing is None:
            raise error
        logger.warning(
            "Conflicting FX rate for currency=%s date=%s existing=%s requested=%s",
            fx.currency_code,
            rate_date,
            existing.rate,
            rate,
        )
        raise ConflictError("conflicting FX rate already exists for currency and date")
