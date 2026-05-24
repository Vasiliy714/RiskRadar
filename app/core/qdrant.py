from qdrant_client import AsyncQdrantClient


class QdrantStore:
    def __init__(
        self,
        host: str,
        port: int,
        grpc_port: int,
        *,
        prefer_grpc: bool = False,
    ) -> None:
        self.client = AsyncQdrantClient(
            host=host,
            port=port,
            grpc_port=grpc_port,
            prefer_grpc=prefer_grpc,
        )

    async def ping(self) -> None:
        await self.client.get_collections()

    async def close(self) -> None:
        await self.client.close()
