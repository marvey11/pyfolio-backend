from __future__ import annotations

from collections.abc import AsyncGenerator, Generator  # noqa: TC003
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from pydantic import AfterValidator
from sqlalchemy import asc, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session  # noqa: TC002

from core.database import database_url, get_session
from core.models import Country, Security
from core.services import ConflictError, save
from core.services import create_country as save_country
from core.validation import InstrumentType, normalise_country_code
from pyfolio_api.schemas import (
    CountryInput,
    CountryOut,
    CountryPatch,
    SecurityInput,
    SecurityOut,
    SecurityPatch,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    database_url()
    yield


app = FastAPI(title="Pyfolio API", version="0.1.0", lifespan=lifespan)
CountryCode = Annotated[str, AfterValidator(normalise_country_code)]


def session_dependency() -> Generator[Session]:
    yield from get_session()


def persist(session: Session, entity: Country | Security) -> Country | Security:
    try:
        return save(session, entity)  # type: ignore[return-value]
    except ConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/countries", response_model=CountryOut, status_code=status.HTTP_201_CREATED)
def create_country(
    payload: CountryInput, session: Session = Depends(session_dependency)
) -> Country:
    try:
        return save_country(session, payload.code, payload.name)
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/countries", response_model=list[CountryOut])
def list_countries(
    session: Session = Depends(session_dependency),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    sort_by: str = Query(default="code", pattern="^(code|name)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> list[Country]:
    sort_column = {"code": Country.code, "name": Country.name}[sort_by]
    return list(
        session.scalars(
            select(Country)
            .order_by((asc if sort_order == "asc" else desc)(sort_column), Country.code)
            .offset(offset)
            .limit(limit)
        )
    )


@app.get("/countries/{code}", response_model=CountryOut)
def get_country(code: str, session: Session = Depends(session_dependency)) -> Country:
    country = session.get(Country, code.upper())
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return country


@app.patch("/countries/{code}", response_model=CountryOut)
def patch_country(
    code: str, payload: CountryPatch, session: Session = Depends(session_dependency)
) -> Country:
    country = session.get(Country, code.upper())
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    values = CountryInput.model_validate(
        {
            **CountryOut.model_validate(country).model_dump(),
            **payload.model_dump(exclude_unset=True),
        }
    )
    if values.code != country.code and session.get(Country, values.code) is not None:
        raise HTTPException(status_code=409, detail="country code already exists")
    country.code, country.name = values.code, values.name
    return persist(session, country)  # type: ignore[return-value]


@app.delete("/countries/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_country(
    code: str, session: Session = Depends(session_dependency)
) -> Response:
    country = session.get(Country, code.upper())
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    session.delete(country)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Country is referenced by a security"
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/securities", response_model=SecurityOut, status_code=status.HTTP_201_CREATED
)
def create_security(
    payload: SecurityInput, session: Session = Depends(session_dependency)
) -> Security:
    security = Security(**payload.model_dump())
    duplicate = session.scalar(
        select(Security).where(
            (Security.isin == security.isin) | (Security.wkn == security.wkn)
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="ISIN or WKN already exists")
    return persist(session, security)  # type: ignore[return-value]


@app.get("/securities", response_model=list[SecurityOut])
def list_securities(
    session: Session = Depends(session_dependency),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    sort_by: str = Query(
        default="id",
        pattern="^(id|isin|wkn|name|instrument_type|country|country_code)$",
    ),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    instrument_type: list[InstrumentType] | None = Query(default=None),
    country_code: list[CountryCode] | None = Query(default=None),
) -> list[Security]:
    statement = select(Security)
    if instrument_type:
        statement = statement.where(Security.instrument_type.in_(instrument_type))
    if country_code:
        statement = statement.where(Security.country_code.in_(country_code))
    if sort_by == "country":
        statement = statement.join(Security.country)

    sort_columns = {
        "id": Security.id,
        "isin": Security.isin,
        "wkn": Security.wkn,
        "name": Security.name,
        "instrument_type": Security.instrument_type,
        "country": Country.name,
        "country_code": Security.country_code,
    }
    return list(
        session.scalars(
            statement.order_by(
                (asc if sort_order == "asc" else desc)(sort_columns[sort_by]),
                Security.id,
            )
            .offset(offset)
            .limit(limit)
        )
    )


@app.get("/securities/{security_id}", response_model=SecurityOut)
def get_security(
    security_id: int, session: Session = Depends(session_dependency)
) -> Security:
    security = session.get(Security, security_id)
    if security is None:
        raise HTTPException(status_code=404, detail="Security not found")
    return security


@app.patch("/securities/{security_id}", response_model=SecurityOut)
def patch_security(
    security_id: int,
    payload: SecurityPatch,
    session: Session = Depends(session_dependency),
) -> Security:
    security = session.get(Security, security_id)
    if security is None:
        raise HTTPException(status_code=404, detail="Security not found")
    current = SecurityOut.model_validate(security).model_dump(exclude={"id"})
    values = SecurityInput.model_validate(
        {**current, **payload.model_dump(exclude_unset=True)}
    )
    duplicate = session.scalar(
        select(Security).where(
            Security.id != security.id,
            (Security.isin == values.isin) | (Security.wkn == values.wkn),
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="ISIN or WKN already exists")
    for field, value in values.model_dump().items():
        setattr(security, field, value)
    return persist(session, security)  # type: ignore[return-value]


@app.delete("/securities/{security_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_security(
    security_id: int, session: Session = Depends(session_dependency)
) -> Response:
    security = session.get(Security, security_id)
    if security is None:
        raise HTTPException(status_code=404, detail="Security not found")
    session.delete(security)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
