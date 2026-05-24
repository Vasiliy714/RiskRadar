from redis.asyncio import Redis


class RedisClient:
    def __init__(self, url: str) -> None:
        self.client: Redis = Redis.from_url(
            url,
            decode_responses=True,
        )

    async def ping(self) -> None:
        ping_result = self.client.ping()
        pong = ping_result if isinstance(ping_result, bool) else await ping_result
        if not pong:
            msg = "Redis ping returned False"
            raise RuntimeError(msg)

    async def close(self) -> None:
        await self.client.aclose()
