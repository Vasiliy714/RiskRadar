import uuid

import httpx
import pytest
from fastapi import status


def unique_code(prefix: str = "ISS") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def create_issuer(
    client: httpx.AsyncClient,
    *,
    code: str | None = None,
    name: str = "Test Issuer",
    inn: str | None = None,
    is_public: bool = True,
) -> httpx.Response:
    payload: dict[str, object] = {
        "code": code or unique_code(),
        "name": name,
        "is_public": is_public,
    }
    if inn is not None:
        payload["inn"] = inn
    return await client.post("/api/v1/issuers", json=payload)


async def delete_issuer(client: httpx.AsyncClient, code: str) -> None:
    response = await client.delete(f"/api/v1/issuers/{code}")
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.integration
async def test_create_duplicate_code_returns_409(async_client: httpx.AsyncClient) -> None:
    code = f"DUP_{uuid.uuid4().hex[:8]}"
    payload = {
        "code": code,
        "name": "First Issuer",
        "is_public": True,
    }

    r1 = await async_client.post("/api/v1/issuers", json=payload)
    assert r1.status_code == status.HTTP_201_CREATED
    assert r1.json()["code"] == code

    r2 = await async_client.post("/api/v1/issuers", json=payload)
    assert r2.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in r2.json()["detail"].lower()

    other_code = f"OTHER_{uuid.uuid4().hex[:8]}"
    r3 = await async_client.post(
        "/api/v1/issuers",
        json={"code": other_code, "name": "Other Issuer", "is_public": True},
    )
    assert r3.status_code == status.HTTP_201_CREATED


@pytest.mark.integration
async def test_get_unknown_issuer_returns_404(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/api/v1/issuers/NO_SUCH_CODE")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_create_issuer(async_client: httpx.AsyncClient) -> None:
    code = unique_code("CREATE")
    try:
        response = await create_issuer(
            async_client,
            code=code,
            name="Sberbank",
            inn="7707083893",
            is_public=True,
        )
        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["code"] == code
        assert body["name"] == "Sberbank"
        assert body["inn"] == "7707083893"
        assert body["is_public"] is True
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body
    finally:
        await delete_issuer(async_client, code)


@pytest.mark.integration
async def test_create_duplicate_issuer(async_client: httpx.AsyncClient) -> None:
    code = unique_code("DUP")
    payload = {"code": code, "name": "First", "is_public": True}
    try:
        r1 = await async_client.post("/api/v1/issuers", json=payload)
        assert r1.status_code == status.HTTP_201_CREATED

        r2 = await async_client.post("/api/v1/issuers", json=payload)
        assert r2.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in r2.json()["detail"].lower()
    finally:
        await delete_issuer(async_client, code)


@pytest.mark.integration
async def test_get_issuer_by_code(async_client: httpx.AsyncClient) -> None:
    code = unique_code("GET")
    try:
        create_response = await create_issuer(async_client, code=code, name="Gazprom")
        assert create_response.status_code == status.HTTP_201_CREATED

        get_response = await async_client.get(f"/api/v1/issuers/{code}")
        assert get_response.status_code == status.HTTP_200_OK
        body = get_response.json()
        assert body["code"] == code
        assert body["name"] == "Gazprom"
        assert body["id"] == create_response.json()["id"]
    finally:
        await delete_issuer(async_client, code)


@pytest.mark.integration
async def test_get_missing_issuer(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get(f"/api/v1/issuers/{unique_code('MISSING')}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_list_issuers_pagination(async_client: httpx.AsyncClient) -> None:
    codes = [unique_code("PAGE") for _ in range(3)]

    baseline = await async_client.get("/api/v1/issuers", params={"limit": 100, "offset": 0})
    assert baseline.status_code == status.HTTP_200_OK
    total_before = baseline.json()["total"]

    try:
        for i, code in enumerate(codes):
            response = await create_issuer(async_client, code=code, name=f"Issuer {i}")
            assert response.status_code == status.HTTP_201_CREATED

        page1 = await async_client.get(
            "/api/v1/issuers",
            params={"limit": 2, "offset": 0},
        )
        assert page1.status_code == status.HTTP_200_OK
        body1 = page1.json()
        assert body1["limit"] == 2
        assert body1["offset"] == 0
        assert body1["total"] == total_before + 3
        assert len(body1["items"]) == 2

        page2 = await async_client.get(
            "/api/v1/issuers",
            params={"limit": 2, "offset": 2},
        )
        body2 = page2.json()
        assert body2["limit"] == 2
        assert body2["offset"] == 2
        assert body2["total"] == total_before + 3
        assert len(body2["items"]) >= 1
    finally:
        for code in codes:
            await delete_issuer(async_client, code)


@pytest.mark.integration
async def test_create_issuer_invalid_inn(async_client: httpx.AsyncClient) -> None:
    response = await create_issuer(
        async_client,
        code=unique_code("BADINN"),
        inn="not-valid-inn",
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
