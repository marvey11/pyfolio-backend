from __future__ import annotations

from datetime import date  # noqa: TC003
from decimal import Decimal  # noqa: TC003

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from core.validation import (
    InstrumentType,
    normalise_country_code,
    normalise_currency_code,
    normalise_exchange,
    normalise_isin,
    normalise_text,
    normalise_wkn,
)


class Base(DeclarativeBase):
    pass


class Country(Base):
    __tablename__ = "countries"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_country_name_nonblank"),
    )
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    securities: Mapped[list[Security]] = relationship(back_populates="country")

    def __init__(self, *, code: str, name: str) -> None:
        self.code = normalise_country_code(code)
        self.name = normalise_text(name)


class Currency(Base):
    __tablename__ = "currencies"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_currency_name_nonblank"),
    )
    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    def __init__(self, *, code: str, name: str) -> None:
        self.code = normalise_currency_code(code)
        self.name = normalise_text(name)


class Security(Base):
    __tablename__ = "securities"
    __table_args__ = (
        UniqueConstraint("isin"),
        UniqueConstraint("wkn"),
        CheckConstraint("length(trim(name)) > 0", name="ck_security_name_nonblank"),
        CheckConstraint(
            "instrument_type IN ('stock', 'etf', 'bond', 'certificate', 'fund')",
            name="ck_security_instrument_type",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(String(12), nullable=False)
    wkn: Mapped[str] = mapped_column(String(6), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(32), nullable=False)
    country_code: Mapped[str] = mapped_column(
        ForeignKey("countries.code"), nullable=False
    )
    country: Mapped[Country] = relationship(back_populates="securities")
    quotes: Mapped[list[SecurityQuote]] = relationship(
        back_populates="security", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        *,
        isin: str,
        wkn: str,
        name: str,
        instrument_type: InstrumentType | str,
        country_code: str,
    ) -> None:
        self.isin = normalise_isin(isin)
        self.wkn = normalise_wkn(wkn)
        self.name = normalise_text(name)
        self.instrument_type = InstrumentType(instrument_type).value
        self.country_code = normalise_country_code(country_code)


class SecurityQuote(Base):
    __tablename__ = "security_quotes"
    __table_args__ = (
        UniqueConstraint(
            "security_id",
            "quote_date",
            "exchange",
            name="uq_quote_security_date_exchange",
        ),
        CheckConstraint("closing_price >= 0", name="ck_quote_price_nonnegative"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    security_id: Mapped[int] = mapped_column(
        ForeignKey("securities.id", ondelete="CASCADE"), nullable=False
    )
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    exchange: Mapped[str] = mapped_column(String(80), nullable=False)
    closing_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    currency_code: Mapped[str] = mapped_column(
        ForeignKey("currencies.code"), nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(255))
    security: Mapped[Security] = relationship(back_populates="quotes")

    def __init__(
        self,
        *,
        security_id: int,
        quote_date: date,
        exchange: str,
        closing_price: Decimal,
        currency_code: str,
        source: str | None = None,
    ) -> None:
        if closing_price < 0:
            raise ValueError("closing price must not be negative")
        self.security_id, self.quote_date = security_id, quote_date
        self.exchange, self.closing_price = normalise_exchange(exchange), closing_price
        self.currency_code = normalise_currency_code(currency_code)
        self.source = normalise_text(source) if source else None


class FxRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint("currency_code", "rate_date", name="uq_fx_currency_date"),
        CheckConstraint("rate > 0", name="ck_fx_rate_positive"),
        CheckConstraint("currency_code != 'EUR'", name="ck_fx_not_eur"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    currency_code: Mapped[str] = mapped_column(
        ForeignKey("currencies.code"), nullable=False
    )
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    source: Mapped[str | None] = mapped_column(String(255))

    def __init__(
        self,
        *,
        currency_code: str,
        rate_date: date,
        rate: Decimal,
        source: str | None = None,
    ) -> None:
        if currency_code.strip().upper() == "EUR":
            raise ValueError("EUR is implicit and must not have a stored FX rate")
        if rate <= 0:
            raise ValueError("FX rate must be positive")
        self.currency_code, self.rate_date, self.rate = (
            normalise_currency_code(currency_code),
            rate_date,
            rate,
        )
        self.source = normalise_text(source) if source else None
