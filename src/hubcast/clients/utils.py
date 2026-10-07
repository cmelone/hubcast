import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from functools import partial

import aiohttp
from gidgethub import aiohttp as gh_aiohttp
from gidgetlab import aiohttp as gl_aiohttp

from hubcast import retry

# rate limited, or gateway/availability errors
RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})


class TokenCache:
    """
    Cache for web tokens with an expiration.
    """

    def __init__(self):
        self._tokens: dict[str, tuple[float, str]] = {}

    async def get(
        self,
        name: str,
        renew: Callable[[], Awaitable[tuple[float, str]]],
        time_needed: int = 60,
    ) -> str:
        """
        Get a cached token, or renew as needed.

        Parameters
        ---------
        name: str
            An identifying name of a token to get from the cache.
        renew: Callable[[], Awaitable[tuple[float, str]]]
            A function to call in order to generate a new token if the cache
            is stale.
        time_needed: int
            The number of seconds a token will be needed. Thus any token that
            expires during this window should be disregarded and renewed.
        """
        expires, token = self._tokens.get(name, (0, ""))

        now = time.time()
        if expires < now + time_needed:
            expires, token = await renew()
            self._tokens[name] = (expires, token)

        return token


Response = tuple[int, Mapping[str, str], bytes]


async def _with_retries(
    send: Callable[[], Awaitable[Response]], method: str, url: str
) -> Response:
    """Await send() and retry on connection errors, timeouts, and HTTP 429/502/503/504. Applies to all HTTP methods."""
    for attempt in range(retry.retries):
        try:
            response = await send()
        except (TimeoutError, aiohttp.ClientConnectionError) as e:
            reason = repr(e)
        else:
            if response[0] not in RETRYABLE_STATUSES:
                return response
            reason = f"HTTP {response[0]}"

        await asyncio.sleep(retry.retry_delay(f"{method} {url}", attempt, reason))
    return await send()


class GitHubAPI(gh_aiohttp.GitHubAPI):
    """gidgethub's GitHubAPI with retried requests."""

    async def _request(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes = b""
    ) -> Response:
        send = partial(super()._request, method, url, headers, body)
        return await _with_retries(send, method, url)


class GitLabAPI(gl_aiohttp.GitLabAPI):
    """gidgetlab's GitLabAPI with retried requests."""

    async def _request(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes = b""
    ) -> Response:
        send = partial(super()._request, method, url, headers, body)
        return await _with_retries(send, method, url)
