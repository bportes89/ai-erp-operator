import asyncio
import json

from redis.asyncio import Redis

from app.config import get_settings
from app.jobs import process_operation


async def run():
    redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    print("Worker aguardando operações")
    while True:
        job = await redis.blpop("operator:jobs", timeout=5)
        if job:
            payload = json.loads(job[1])
            operation_id = payload.get("operation_id")
            print(f"Processando {operation_id}")
            try:
                await process_operation(operation_id)
            except Exception as exc:
                print(f"Falha em {operation_id}: {exc}")
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(run())
