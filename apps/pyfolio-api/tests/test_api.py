# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from core.database import configure_engine
from core.models import Base
from pyfolio_api.main import app, session_dependency

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    engine = configure_engine(
        create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    )
    Base.metadata.create_all(engine)

    def override_session() -> Generator[Session]:
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[session_dependency] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_country_crud(client: TestClient) -> None:
    response = client.post("/countries", json={"code": " de ", "name": " Germany "})
    assert response.status_code == 201
    assert response.json() == {"code": "DE", "name": "Germany"}
    assert client.get("/countries/DE").status_code == 200
    assert client.get("/countries").json()[0]["code"] == "DE"
    assert (
        client.patch("/countries/DE", json={"name": " Federal Republic "}).json()[
            "name"
        ]
        == "Federal Republic"
    )
    assert client.delete("/countries/DE").status_code == 204
    assert client.get("/countries/DE").status_code == 404


def test_country_sorting(client: TestClient) -> None:
    client.post("/countries", json={"code": "DE", "name": "Germany"})
    client.post("/countries", json={"code": "FR", "name": "France"})

    by_name = client.get("/countries?sort_by=name&sort_order=asc")
    assert [country["code"] for country in by_name.json()] == ["FR", "DE"]
    by_code_desc = client.get("/countries?sort_by=code&sort_order=desc")
    assert [country["code"] for country in by_code_desc.json()] == ["FR", "DE"]


def test_security_filtering_and_sorting(client: TestClient) -> None:
    for code, name in (("DE", "Germany"), ("FR", "France")):
        client.post("/countries", json={"code": code, "name": name})
    securities = [
        {
            "isin": "US0378331005",
            "wkn": "865985",
            "name": "Apple",
            "instrument_type": "stock",
            "country_code": "DE",
        },
        {
            "isin": "US5949181045",
            "wkn": "B7TL82",
            "name": "Microsoft",
            "instrument_type": "stock",
            "country_code": "FR",
        },
        {
            "isin": "IE00B4L5Y983",
            "wkn": "A0RPWH",
            "name": "iShares Core MSCI World",
            "instrument_type": "etf",
            "country_code": "DE",
        },
    ]
    for security in securities:
        assert client.post("/securities", json=security).status_code == 201

    filtered = client.get(
        "/securities?instrument_type=stock&country_code=de&sort_by=name&sort_order=desc"
    )
    assert [security["name"] for security in filtered.json()] == ["Apple"]
    multiple_types = client.get(
        "/securities?instrument_type=stock&instrument_type=etf&country_code=DE"
    )
    assert [security["name"] for security in multiple_types.json()] == [
        "Apple",
        "iShares Core MSCI World",
    ]
    assert client.get("/securities?sort_by=unknown").status_code == 422
    assert client.get("/securities?country_code=not-a-country").status_code == 422


def test_security_crud_and_validation(client: TestClient) -> None:
    client.post("/countries", json={"code": "DE", "name": "Germany"})
    payload = {
        "isin": "us0378331005",
        "wkn": "865985",
        "name": " Apple ",
        "instrument_type": "stock",
        "country_code": "de",
    }
    created = client.post("/securities", json=payload)
    assert created.status_code == 201
    security_id = created.json()["id"]
    assert client.get(f"/securities/{security_id}").status_code == 200
    assert client.get("/securities").json()[0]["isin"] == "US0378331005"
    assert (
        client.patch(
            f"/securities/{security_id}", json={"name": " Apple Inc. "}
        ).json()["name"]
        == "Apple Inc."
    )
    assert (
        client.patch(f"/securities/{security_id}", json={"name": " "}).status_code
        == 422
    )
    assert client.delete(f"/securities/{security_id}").status_code == 204
    assert client.get(f"/securities/{security_id}").status_code == 404
    assert (
        client.post("/securities", json={**payload, "isin": "bad"}).status_code == 422
    )


def test_duplicate_and_foreign_key_conflict(client: TestClient) -> None:
    country = {"code": "DE", "name": "Germany"}
    assert client.post("/countries", json=country).status_code == 201
    assert client.post("/countries", json=country).status_code == 409
    assert (
        client.post(
            "/securities",
            json={
                "isin": "US0378331005",
                "wkn": "865985",
                "name": "Apple",
                "instrument_type": "stock",
                "country_code": "FR",
            },
        ).status_code
        == 409
    )
    payload = {
        "isin": "US0378331005",
        "wkn": "865985",
        "name": "Apple",
        "instrument_type": "stock",
        "country_code": "DE",
    }
    assert client.post("/securities", json=payload).status_code == 201
    assert (
        client.post("/securities", json={**payload, "isin": "US5949181045"}).status_code
        == 409
    )
    assert (
        client.post("/securities", json={**payload, "wkn": "B7TL82"}).status_code == 409
    )
    assert client.delete("/countries/DE").status_code == 409
    assert client.get("/securities/999").status_code == 404
