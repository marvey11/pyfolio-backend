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
    response = client.post(
        "/api/v1/countries", json={"code": " de ", "name": " Germany "}
    )
    assert response.status_code == 201
    assert response.json() == {"code": "DE", "name": "Germany"}
    assert client.get("/api/v1/countries/DE").status_code == 200
    assert client.get("/api/v1/countries").json()["items"][0]["code"] == "DE"
    assert (
        client.patch(
            "/api/v1/countries/DE", json={"name": " Federal Republic "}
        ).json()["name"]
        == "Federal Republic"
    )
    assert client.delete("/api/v1/countries/DE").status_code == 204
    assert client.get("/api/v1/countries/DE").status_code == 404


def test_country_sorting(client: TestClient) -> None:
    client.post("/api/v1/countries", json={"code": "DE", "name": "Germany"})
    client.post("/api/v1/countries", json={"code": "FR", "name": "France"})

    by_name = client.get("/api/v1/countries?sort_by=name&sort_order=asc")
    assert [country["code"] for country in by_name.json()["items"]] == ["FR", "DE"]
    by_code_desc = client.get("/api/v1/countries?sort_by=code&sort_order=desc")
    assert [country["code"] for country in by_code_desc.json()["items"]] == [
        "FR",
        "DE",
    ]


def test_country_pagination(client: TestClient) -> None:
    for code, name in (("DE", "Germany"), ("FR", "France"), ("GB", "United Kingdom")):
        client.post("/api/v1/countries", json={"code": code, "name": name})

    first_page = client.get("/api/v1/countries?page=1&pageSize=2").json()
    assert [country["code"] for country in first_page["items"]] == ["DE", "FR"]
    assert first_page["pagination"] == {
        "page": 1,
        "pageSize": 2,
        "totalItems": 3,
        "totalPages": 2,
        "hasPreviousPage": False,
        "hasNextPage": True,
    }

    second_page = client.get("/api/v1/countries?page=2&pageSize=2").json()
    assert [country["code"] for country in second_page["items"]] == ["GB"]
    assert second_page["pagination"]["hasPreviousPage"] is True
    assert second_page["pagination"]["hasNextPage"] is False
    assert client.get("/api/v1/countries?page=0").status_code == 422
    assert client.get("/api/v1/countries?pageSize=501").status_code == 422


def test_country_empty_and_out_of_range_pagination(client: TestClient) -> None:
    empty = client.get("/api/v1/countries").json()
    assert empty["items"] == []
    assert empty["pagination"]["totalPages"] == 0

    client.post("/api/v1/countries", json={"code": "DE", "name": "Germany"})
    out_of_range = client.get("/api/v1/countries?page=3&pageSize=1").json()
    assert out_of_range["items"] == []
    assert out_of_range["pagination"]["page"] == 3
    assert out_of_range["pagination"]["hasPreviousPage"] is False


def test_security_filtering_and_sorting(client: TestClient) -> None:
    for code, name in (("DE", "Germany"), ("FR", "France")):
        client.post("/api/v1/countries", json={"code": code, "name": name})
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
        assert client.post("/api/v1/securities", json=security).status_code == 201

    filtered = client.get(
        "/api/v1/securities?instrument_type=stock&country_code=de&sort_by=name&sort_order=desc"
    )
    assert [security["name"] for security in filtered.json()["items"]] == ["Apple"]
    multiple_types = client.get(
        "/api/v1/securities?instrument_type=stock&instrument_type=etf&country_code=DE"
    )
    assert [security["name"] for security in multiple_types.json()["items"]] == [
        "Apple",
        "iShares Core MSCI World",
    ]
    paged = client.get(
        "/api/v1/securities?instrument_type=stock&instrument_type=etf"
        "&country_code=DE&page=1&pageSize=1"
    ).json()
    assert [security["name"] for security in paged["items"]] == ["Apple"]
    assert paged["pagination"] == {
        "page": 1,
        "pageSize": 1,
        "totalItems": 2,
        "totalPages": 2,
        "hasPreviousPage": False,
        "hasNextPage": True,
    }
    assert client.get("/api/v1/securities?sort_by=unknown").status_code == 422
    assert (
        client.get("/api/v1/securities?country_code=not-a-country").status_code == 422
    )


def test_security_crud_and_validation(client: TestClient) -> None:
    client.post("/api/v1/countries", json={"code": "DE", "name": "Germany"})
    payload = {
        "isin": "us0378331005",
        "wkn": "865985",
        "name": " Apple ",
        "instrument_type": "stock",
        "country_code": "de",
    }
    created = client.post("/api/v1/securities", json=payload)
    assert created.status_code == 201
    security_id = created.json()["id"]
    assert client.get(f"/api/v1/securities/{security_id}").status_code == 200
    assert client.get("/api/v1/securities").json()["items"][0]["isin"] == "US0378331005"
    assert (
        client.patch(
            f"/api/v1/securities/{security_id}", json={"name": " Apple Inc. "}
        ).json()["name"]
        == "Apple Inc."
    )
    assert (
        client.patch(
            f"/api/v1/securities/{security_id}", json={"name": " "}
        ).status_code
        == 422
    )
    assert client.delete(f"/api/v1/securities/{security_id}").status_code == 204
    assert client.get(f"/api/v1/securities/{security_id}").status_code == 404
    assert (
        client.post("/api/v1/securities", json={**payload, "isin": "bad"}).status_code
        == 422
    )


def test_duplicate_and_foreign_key_conflict(client: TestClient) -> None:
    country = {"code": "DE", "name": "Germany"}
    assert client.post("/api/v1/countries", json=country).status_code == 201
    assert client.post("/api/v1/countries", json=country).status_code == 409
    assert (
        client.post(
            "/api/v1/securities",
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
    assert client.post("/api/v1/securities", json=payload).status_code == 201
    assert (
        client.post(
            "/api/v1/securities", json={**payload, "isin": "US5949181045"}
        ).status_code
        == 409
    )
    assert (
        client.post("/api/v1/securities", json={**payload, "wkn": "B7TL82"}).status_code
        == 409
    )
    assert client.delete("/api/v1/countries/DE").status_code == 409
    assert client.get("/api/v1/securities/999").status_code == 404
