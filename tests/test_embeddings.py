from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import GigaChatSettings
from app.llm.embeddings.gigachat import GigaChatEmbeddings
from app.llm.embeddings.local import apply_e5_prefix
from app.llm.embeddings.mock import MockEmbeddings


async def test_mock_embeddings_are_deterministic_and_normalized() -> None:
    provider = MockEmbeddings(vector_size=8)
    try:
        first = await provider.embed_query("issuer risk")
        second = await provider.embed_query("issuer risk")
        different = await provider.embed_query("other text")

        assert first == second
        assert first != different
        assert len(first) == 8
        norm = sum(value * value for value in first) ** 0.5
        assert norm == pytest.approx(1.0)
    finally:
        await provider.close()


async def test_mock_embeddings_batch_matches_single() -> None:
    provider = MockEmbeddings(vector_size=16)
    try:
        batch = await provider.embed_documents(["alpha", "beta"])
        single = await provider.embed_query("alpha")
        assert batch[0] == single
        assert len(batch) == 2
    finally:
        await provider.close()


def test_apply_e5_prefix_adds_query_and_passage_prefixes() -> None:
    assert apply_e5_prefix("risk profile", is_query=True) == "query: risk profile"
    assert apply_e5_prefix("annual report section", is_query=False) == (
        "passage: annual report section"
    )


def test_apply_e5_prefix_does_not_double_prefix() -> None:
    assert apply_e5_prefix("query: already prefixed", is_query=True) == "query: already prefixed"
    assert apply_e5_prefix("passage: already prefixed", is_query=False) == (
        "passage: already prefixed"
    )


async def test_gigachat_embeddings_returns_vectors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "access_token": "test-token",
                    "expires_at": 4_000_000_000_000,
                },
            )
        payload = json.loads(request.content.decode("utf-8"))
        inputs = payload["input"]
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": "Embeddings",
                "data": [
                    {
                        "object": "embedding",
                        "index": index,
                        "embedding": [0.1 * (index + 1), 0.2 * (index + 1), 0.3 * (index + 1)],
                    }
                    for index, _ in enumerate(inputs)
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        base_url="https://gigachat.devices.sberbank.ru/api/v1",
        transport=transport,
    )
    settings = GigaChatSettings(auth_key=SecretStr("test-auth-key"), verify_ssl=False)
    provider = GigaChatEmbeddings(settings, http_client=http_client)
    try:
        query_vector = await provider.embed_query("SBER debt ratio")
        batch_vectors = await provider.embed_documents(["doc one", "doc two"])

        assert query_vector == [0.1, 0.2, 0.3]
        assert batch_vectors == [[0.1, 0.2, 0.3], [0.2, 0.4, 0.6]]
        assert provider.vector_size == 1024
    finally:
        await provider.close()
