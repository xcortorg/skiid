import aiohttp
import asyncio
import logging
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)

class Session:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
            "referer": "https://evelina.bot/",
        }
        self._session = None
        self._closed = False
        self._lock = asyncio.Lock()
        self._closing = False
        self._pending_operations = 0
        self._close_event = asyncio.Event()

    async def _create_session(self):
        async with self._lock:
            if self._closed:
                raise RuntimeError("Session has been closed")
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession(headers=self.headers)
                logger.debug("Created new aiohttp ClientSession")

    async def get_session(self):
        if self._session is None or self._session.closed:
            await self._create_session()
        return self._session

    async def close(self):
        if self._closing:
            return
        self._closing = True
        async with self._lock:
            if self._session and not self._session.closed:
                logger.debug("Closing aiohttp ClientSession")
                try:
                    if self._pending_operations > 0:
                        await self._close_event.wait()
                    await asyncio.shield(self._session.close())
                    await asyncio.sleep(0.25)
                except Exception as e:
                    logger.error(f"Error closing session: {e}")
                finally:
                    self._session = None
                    self._closed = True
                    self._closing = False
                    logger.debug("Session closed successfully")

    async def __aenter__(self):
        await self._create_session()
        self._pending_operations += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._pending_operations -= 1
        if self._pending_operations == 0:
            self._close_event.set()
        await self.close()

    async def post_json(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        proxy: Optional[str] = None,
        return_status: bool = False,
    ) -> Union[dict, Tuple[dict, int]]:
        session = await self.get_session()
        try:
            async with session.post(
                url, headers=headers, json=params, proxy=proxy
            ) as r:
                try:
                    json_data = await r.json()
                except aiohttp.ContentTypeError:
                    json_data = None
                if return_status:
                    return json_data, r.status
                return json_data
        except Exception as e:
            logger.error(f"Error in post_json request to {url}: {e}")
            raise

    async def get_json(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        proxy: Optional[str] = None,
        return_status: bool = False,
    ) -> Union[dict, Tuple[dict, int]]:
        session = await self.get_session()
        try:
            async with session.get(
                url, headers=headers, params=params, proxy=proxy
            ) as r:
                try:
                    json_data = await r.json()
                except aiohttp.ContentTypeError:
                    json_data = None
                if return_status:
                    return json_data, r.status
                return json_data
        except Exception as e:
            logger.error(f"Error in get_json request to {url}: {e}")
            raise

    async def get_text(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        proxy: Optional[str] = None,
        return_status: bool = False,
    ) -> Union[str, Tuple[str, int]]:
        session = await self.get_session()
        try:
            async with session.get(
                url, headers=headers, params=params, proxy=proxy
            ) as r:
                text_data = await r.text()
                if return_status:
                    return text_data, r.status
                return text_data
        except Exception as e:
            logger.error(f"Error in get_text request to {url}: {e}")
            raise

    async def get_bytes(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        proxy: Optional[str] = None,
        return_status: bool = False,
    ) -> Union[bytes, Tuple[bytes, int]]:
        session = await self.get_session()
        try:
            async with session.get(
                url, headers=headers, params=params, proxy=proxy
            ) as r:
                bytes_data = await r.read()
                if return_status:
                    return bytes_data, r.status
                return bytes_data
        except Exception as e:
            logger.error(f"Error in get_bytes request to {url}: {e}")
            raise