# ==============================================================================
# Copyright (C) 2021 Evil0ctal
#
# This file is part of the Douyin_TikTok_Download_API project.
#
# This project is licensed under the Apache License 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# 　　　　 　　  ＿＿
# 　　　 　　 ／＞　　フ
# 　　　 　　| 　_　 _ l
# 　 　　 　／` ミ＿xノ
# 　　 　 /　　　 　 |       Feed me Stars ⭐ ️
# 　　　 /　 ヽ　　 ﾉ
# 　 　 │　　|　|　|
# 　／￣|　　 |　|　|
# 　| (￣ヽ＿_ヽ_)__)
# 　＼yaつ
# ==============================================================================
#
# Contributor Link:
# - https://github.com/Evil0ctal
# - https://github.com/Johnserf-Seed
#
# ==============================================================================

import httpx
import json
import asyncio
import re

from httpx import Response

from loguru import logger
from .api_exceptions import (
    APIError,
    APIConnectionError,
    APIResponseError,
    APITimeoutError,
    APIUnavailableError,
    APIUnauthorizedError,
    APINotFoundError,
    APIRateLimitError,
    APIRetryExhaustedError,
)


class BaseCrawler:
    def __init__(
        self,
        proxies: dict = None,
        max_retries: int = 3,
        max_connections: int = 50,
        timeout: int = 10,
        max_tasks: int = 50,
        crawler_headers: dict = {},
    ):
        if isinstance(proxies, dict):
            self.proxies = proxies
        else:
            self.proxies = None

        self.crawler_headers = crawler_headers or {}

        self._max_tasks = max_tasks
        self.semaphore = asyncio.Semaphore(max_tasks)

        # Limit the maximum number of connections
        self._max_connections = max_connections
        self.limits = httpx.Limits(max_connections=max_connections)

        #  Business logic retry count
        self._max_retries = max_retries
        #  Underlying connection retry count
        self.atransport = httpx.AsyncHTTPTransport(retries=max_retries)

        #  Timeout waiting time
        self._timeout = timeout
        self.timeout = httpx.Timeout(timeout)
        #  Asynchronous client
        self.aclient = httpx.AsyncClient(
            headers=self.crawler_headers,
            proxies=self.proxies,
            timeout=self.timeout,
            limits=self.limits,
            transport=self.atransport,
        )

    async def fetch_response(self, endpoint: str) -> Response:
        """(Get data)

        Args:
            endpoint (str): (Endpoint URL)

        Returns:
            Response: (Raw response object)
        """
        return await self.get_fetch_data(endpoint)

    async def fetch_get_json(self, endpoint: str) -> dict:
        """JSON (Get JSON data)

        Args:
            endpoint (str): (Endpoint URL)

        Returns:
            dict: (Parsed JSON data)
        """
        response = await self.get_fetch_data(endpoint)
        return self.parse_json(response)

    async def fetch_post_json(
        self, endpoint: str, params: dict = {}, data=None
    ) -> dict:
        """JSON (Post JSON data)

        Args:
            endpoint (str): (Endpoint URL)

        Returns:
            dict: (Parsed JSON data)
        """
        response = await self.post_fetch_data(endpoint, params, data)
        return self.parse_json(response)

    def parse_json(self, response: Response) -> dict:
        """JSON (Parse JSON response object)

        Args:
            response (Response): (Raw response object)

        Returns:
            dict: (Parsed JSON data)
        """
        if (
            response is not None
            and isinstance(response, Response)
            and response.status_code == 200
        ):
            try:
                return response.json()
            except json.JSONDecodeError as e:
                # yayayayayayayayayayaresponse.textyayajsonyaya
                match = re.search(r"\{.*\}", response.text)
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError as e:
                    logger.error("{0} JSON {1}".format(response.url, e))
                    raise APIResponseError("JSON")

        else:
            if isinstance(response, Response):
                logger.error("{0}".format(response.status_code))
            else:
                logger.error("{0}".format(type(response)))

            raise APIResponseError("BAD RESPONSE")

    async def get_fetch_data(self, url: str):
        """
        GET (Get GET endpoint data)

        Args:
            url (str): URL (Endpoint URL)

        Returns:
            response: (Response content)
        """
        for attempt in range(self._max_retries):
            try:
                response = await self.aclient.get(url, follow_redirects=True)
                if not response.text.strip() or not response.content:
                    error_message = "{0} {1}, URL:{2}".format(
                        attempt + 1, response.status_code, response.url
                    )

                    logger.warning(error_message)

                    if attempt == self._max_retries - 1:
                        raise APIRetryExhaustedError("RAN OUT OF RETRIES")

                    await asyncio.sleep(self._timeout)
                    continue

                # logger.info("yayayayaya: {0}".format(response.status_code))
                response.raise_for_status()
                return response

            except httpx.RequestError:
                raise APIConnectionError(
                    "{0} {1} {2}".format(url, self.proxies, self.__class__.__name__)
                )

            except httpx.HTTPStatusError as http_error:
                self.handle_http_status_error(http_error, url, attempt + 1)

            except APIError as e:
                e.display_error()

    async def post_fetch_data(self, url: str, params: dict = {}, data=None):
        """
        POST (Get POST endpoint data)

        Args:
            url (str): URL (Endpoint URL)
            params (dict): POST (POST request parameters)

        Returns:
            response: (Response content)
        """
        for attempt in range(self._max_retries):
            try:
                response = await self.aclient.post(
                    url,
                    json=None if not params else dict(params),
                    data=None if not data else data,
                    follow_redirects=True,
                )
                if not response.text.strip() or not response.content:
                    error_message = "{0} {1}, URL:{2}".format(
                        attempt + 1, response.status_code, response.url
                    )

                    logger.warning(error_message)

                    if attempt == self._max_retries - 1:
                        raise APIRetryExhaustedError("RAN OUT OF RETRIES")

                    await asyncio.sleep(self._timeout)
                    continue

                # logger.info("yayayayaya: {0}".format(response.status_code))
                response.raise_for_status()
                return response

            except httpx.RequestError:
                raise APIConnectionError(
                    "{0} {1} {2}".format(url, self.proxies, self.__class__.__name__)
                )

            except httpx.HTTPStatusError as http_error:
                self.handle_http_status_error(http_error, url, attempt + 1)

            except APIError as e:
                e.display_error()

    async def head_fetch_data(self, url: str):
        """
        HEAD (Get HEAD endpoint data)

        Args:
            url (str): URL (Endpoint URL)

        Returns:
            response: (Response content)
        """
        try:
            response = await self.aclient.head(url)
            # logger.info("yayayayaya: {0}".format(response.status_code))
            response.raise_for_status()
            return response

        except httpx.RequestError:
            raise APIConnectionError(
                "{0} {1} {2}".format(url, self.proxies, self.__class__.__name__)
            )

        except httpx.HTTPStatusError as http_error:
            self.handle_http_status_error(http_error, url, 1)

        except APIError as e:
            e.display_error()

    def handle_http_status_error(self, http_error, url: str, attempt):
        """
        HTTP (Handle HTTP status error)

        Args:
            http_error: HTTP (HTTP status error)
            url: URL (Endpoint URL)
            attempt: (Number of attempts)
        Raises:
            APIConnectionError: (Failed to connect to endpoint)
            APIResponseError: (Response error)
            APIUnavailableError: (Service unavailable)
            APINotFoundError: (Endpoint does not exist)
            APITimeoutError: (Connection timeout)
            APIUnauthorizedError: (Unauthorized)
            APIRateLimitError: (Request frequency is too high)
            APIRetryExhaustedError: (The number of retries has reached the upper limit)
        """
        response = getattr(http_error, "response", None)
        status_code = getattr(response, "status_code", None)

        if response is None or status_code is None:
            logger.error("HTTP: {0}, URL: {1}, {2}".format(http_error, url, attempt))
            raise APIResponseError(f"HTTP: {http_error}")

        if status_code == 302:
            pass
        elif status_code == 404:
            raise APINotFoundError(f"HTTP Status Code {status_code}")
        elif status_code == 503:
            raise APIUnavailableError(f"HTTP Status Code {status_code}")
        elif status_code == 408:
            raise APITimeoutError(f"HTTP Status Code {status_code}")
        elif status_code == 401:
            raise APIUnauthorizedError(f"HTTP Status Code {status_code}")
        elif status_code == 429:
            raise APIRateLimitError(f"HTTP Status Code {status_code}")
        else:
            logger.error("HTTP {0}, URL: {1}, {2}".format(status_code, url, attempt))
            raise APIResponseError(f"HTTP: {status_code}")

    async def close(self):
        await self.aclient.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclient.aclose()
