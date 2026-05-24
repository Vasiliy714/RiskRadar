import httpx
import pytest

pytestmark = pytest.mark.asyncio


async def test_healthz(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
async def test_readyz_when_infra_up(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "up"
    assert set(body["checks"]) == {"postgres", "redis", "qdrant"}
    assert all(check["status"] == "up" for check in body["checks"].values())
