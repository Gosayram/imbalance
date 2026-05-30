import asyncio


async def fetch_data(url: str) -> dict:
	await asyncio.sleep(0)
	return {"url": url}


class AsyncService:
	async def process(self, item: str) -> bool:
		await asyncio.sleep(0)
		return True
