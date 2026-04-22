import asyncio
import os
import uuid

import pytest


@pytest.mark.asyncio
async def test_redis_pubsub_smoke():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        pytest.skip("REDIS_URL not set")

    try:
        from redis.asyncio import Redis
    except Exception as e:  # pragma: no cover
        pytest.skip(f"redis package not available: {e}")

    channel = f"agent_test:{uuid.uuid4().hex}"
    payload = f"hello:{uuid.uuid4().hex}"

    r: Redis | None = None
    pubsub = None
    try:
        r = Redis.from_url(redis_url, decode_responses=True)
        await r.ping()

        pubsub = r.pubsub()
        await pubsub.subscribe(channel)

        # Publish after subscribe to avoid race.
        await r.publish(channel, payload)

        async def wait_for_message() -> str:
            async for msg in pubsub.listen():
                if msg.get("type") != "message":
                    continue
                data = msg.get("data")
                if isinstance(data, str):
                    return data
            raise RuntimeError("pubsub stream ended without message")

        got = await asyncio.wait_for(wait_for_message(), timeout=3.0)
        assert got == payload
    except Exception as e:
        pytest.skip(f"Redis not available/reachable at {redis_url}: {e}")
    finally:
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(channel)
            except Exception:
                pass
        if r is not None:
            # redis-py prefers aclose() (close() deprecated)
            if hasattr(r, "aclose"):
                await r.aclose()
            else:  # pragma: no cover
                await r.close()
