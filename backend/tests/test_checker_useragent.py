import asyncio

import httpx

from app.checker import CHECK_USER_AGENT, check_url


def test_check_sends_identifying_user_agent():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers.get("user-agent")
        return httpx.Response(200)

    async def run():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await check_url("http://93.184.216.34/", client)

    outcome = asyncio.run(run())
    assert outcome.healthy, outcome
    assert seen["ua"] == CHECK_USER_AGENT
    assert seen["ua"].startswith("PulseCheck/")
