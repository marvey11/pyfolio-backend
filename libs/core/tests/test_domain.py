from collections.abc import Generator  # noqa: TC003
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.database import configure_engine
from core.models import Base, Country, Currency, FxRate, Security
from core.services import (
    ConflictError,
    create_country,
    create_currency,
    create_security,
    record_fx_rate,
    record_quote,
    save,
)
from core.validation import (
    normalise_country_code,
    normalise_currency_code,
    normalise_isin,
    normalise_wkn,
)


@pytest.fixture
def session() -> Generator[Session]:
    engine = configure_engine(create_engine("sqlite://"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_normalisers_and_invalid_identifiers() -> None:
    assert normalise_country_code(" de ") == "DE"
    assert normalise_currency_code("eur") == "EUR"
    assert normalise_isin(" us0378331005 ") == "US0378331005"
    assert normalise_wkn(" 865985 ") == "865985"
    with pytest.raises(ValueError):
        normalise_isin("US0378331006")
    with pytest.raises(ValueError):
        normalise_wkn("12345")


def test_domain_validation() -> None:
    with pytest.raises(ValueError):
        Country(code="ZZ", name="No country")
    with pytest.raises(ValueError):
        Currency(code="EURO", name="Euro")
    with pytest.raises(ValueError):
        Security(
            isin="bad",
            wkn="865985",
            name="Apple",
            instrument_type="stock",
            country_code="DE",
        )


def test_crud_services_and_constraints(session: Session) -> None:
    country = create_country(session, "de", " Germany ")
    assert country.name == "Germany"
    security = create_security(
        session,
        isin="US0378331005",
        wkn="865985",
        name=" Apple ",
        instrument_type="stock",
        country_code="DE",
    )
    assert security.name == "Apple"
    with pytest.raises(ConflictError):
        create_country(session, "DE", "Duplicate")
    create_currency(session, "EUR", "Euro")
    with pytest.raises(ConflictError):
        create_currency(session, "EUR", "Duplicate")
    with pytest.raises(ConflictError):
        save(session, Currency(code="EUR", name="Duplicate"))
    assert session.get(Currency, "EUR") is not None


def test_quote_and_fx_idempotency_and_conflicts(session: Session) -> None:
    create_country(session, "DE", "Germany")
    create_currency(session, "EUR", "Euro")
    create_currency(session, "USD", "US dollar")
    security = create_security(
        session,
        isin="US0378331005",
        wkn="865985",
        name="Apple",
        instrument_type="stock",
        country_code="DE",
    )
    first = record_quote(
        session,
        security_id=security.id,
        quote_date=date(2026, 1, 2),
        exchange=" xetra ",
        closing_price=Decimal("10"),
        currency_code="EUR",
    )
    assert (
        record_quote(
            session,
            security_id=security.id,
            quote_date=date(2026, 1, 2),
            exchange="XETRA",
            closing_price=Decimal("10"),
            currency_code="EUR",
        ).id
        == first.id
    )
    with pytest.raises(ConflictError):
        record_quote(
            session,
            security_id=security.id,
            quote_date=date(2026, 1, 2),
            exchange="XETRA",
            closing_price=Decimal("11"),
            currency_code="EUR",
        )
    fx = record_fx_rate(
        session, currency_code="USD", rate_date=date(2026, 1, 2), rate=Decimal("1.08")
    )
    assert (
        record_fx_rate(
            session,
            currency_code="USD",
            rate_date=date(2026, 1, 2),
            rate=Decimal("1.08"),
        ).id
        == fx.id
    )
    with pytest.raises(ConflictError):
        record_fx_rate(
            session,
            currency_code="USD",
            rate_date=date(2026, 1, 2),
            rate=Decimal("1.09"),
        )
    with pytest.raises(ValueError):
        FxRate(currency_code="EUR", rate_date=date(2026, 1, 2), rate=Decimal("1"))
    with pytest.raises(ValueError):
        FxRate(currency_code="USD", rate_date=date(2026, 1, 2), rate=Decimal("0"))
