import asyncio

import httpx

from app.checker import CHECK_TIMEOUT, check_url


async def main():
    urls = [
        "http://127.0.0.1:8000/health",
        "http://127.0.0.1:8000/monitors/999",
        "http://127.0.0.1:9999",
    ]
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT, follow_redirects=False) as client:
        for url in urls:
            print(url, "->", await check_url(url, client))


asyncio.run(main())
