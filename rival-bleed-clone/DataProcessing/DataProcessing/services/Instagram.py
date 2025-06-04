"""
  Author: cop-discord
  Email: cop@catgir.ls
  Discord: aiohttp
"""

from typing import List, Optional, Any, Tuple
from redis.asyncio import Redis
from .Base import BaseService, cache
from contextlib import suppress
from loguru import logger as log
from playwright.async_api import Page, async_playwright
from playwright.async_api import Request as PlaywrightRequest
from playwright.async_api import Response as PlaywrightResponse
from collections import deque
from playwright._impl._errors import TargetClosedError
from ..models.Instagram import (
    InstagramProfileModel,
    InstagramProfileModelResponse,
    UserPostItem,
    InstaStoryModel,
    InstagramStoryResponse,
    InstagramUserResponse,
    StoryItem,
    InstagramHighlightGraphQueryRaw,
    InstagramHighlightRaw,
)
from asyncer import asyncify
from bs4 import BeautifulSoup
from pathlib import Path
from ..models.Instagram.raw_post import InstagramPost
from ..models.authentication import InstagramCredentials
from tornado.escape import url_unescape
from urllib.parse import urlparse
from ..models.mime import mimes

import re
import os
import pyotp
import orjson
import time
import json
import asyncio
import msgpack
import random
import traceback

try:
    from asyncio import timeout
except ImportError:
    try:
        from async_timeout import timeout
    except ImportError:
        from async_timeout import Timeout as timeout


def get_error(exception):
    exc = "".join(
        traceback.format_exception(type(exception), exception, exception.__traceback__)
    )
    return exc


async def get_proxy_ports():
    process = await asyncio.create_subprocess_exec(
        "netstat",
        "-tlnp",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if stderr:
        print(f"Error: {stderr.decode().strip()}")
        return []

    ports = []
    for line in stdout.decode().splitlines():
        if "3proxy" in line:
            parts = line.split()
            if len(parts) > 3:
                port_info = parts[3]
                port = port_info.split(":")[-1]  # Get the port number
                ports.append(port)

    return ports


async def get_random_proxy(as_dict: Optional[bool] = True):
    ports = await get_proxy_ports()
    port = random.choice(ports)
    if as_dict:
        return {
            "server": f"http://127.0.0.1:{port}",
            "username": "admin",
            "password": "admin",
        }
    else:
        return f"http://admin:admin@127.0.0.1:{port}"


def url_to_mime(url) -> Tuple[Optional[str], str]:
    """Guess the mime from a URL.

    Args:
    ----
                    url (str)

    Returns:
    -------
                    tuple[str, str]: Returns the mime and the suffix
    """
    suffix = Path(urlparse(url_unescape(url)).path).suffix
    return (mimes.get(suffix), suffix)


@asyncify
def extract_json_tag(data, key_ident: str, soap=True) -> bytes:
    import orjson
    from bs4 import BeautifulSoup
    from loguru import logger as log

    with log.catch():

        def seq_checker(value):
            if len(value) == 1:
                value = [value]
            to_check = deque(value)

            def mapping_checker(value: dict):
                for v in value.values():
                    if type(v) is list:
                        to_check.extend(v)
                        continue
                    if type(v) is dict:
                        to_check.append(v)
                        continue
                    if type(v) is str:
                        try:
                            data = orjson.loads(v)
                            to_check.append(data)
                        except Exception:
                            continue

            rounds = 0
            while to_check:
                item = to_check.pop()
                rounds += 1
                if type(item) is list:
                    to_check.extend(item)
                    continue
                if type(item) is dict:
                    if key_ident in item:
                        return item
                    item = mapping_checker(item)
                    if type(item) is list:
                        to_check.extend(result)
                        continue
                if type(item) is str:
                    try:
                        item = orjson.loads(item)
                        to_check.append(item)
                    except Exception:
                        continue

            return None

        if soap:
            soup = BeautifulSoup(data, "lxml")
            for x in soup.find_all("script", type="application/json"):
                result = seq_checker(orjson.loads(x.decode_contents()))
                if result:
                    return orjson.dumps(result)

        else:
            result = seq_checker(orjson.loads(data))
            if result:
                return orjson.dumps(result)

        return False


class InstagramService(BaseService):
    def __init__(
        self, redis: Redis, credentials: InstagramCredentials, ttl: Optional[int] = None
    ):
        self.redis = redis
        self.ttl = ttl
        self.credentials = credentials
        self.cookies = None
        self.cookies_file = "/root/www.instagram.com.cookies.json"
        super().__init__("Instagram", self.redis, self.ttl)

    def load_cookies_from_file(self, cookies_file: str):
        if self.cookies:
            return self.cookies
        with open(cookies_file, "r") as f:
            cookies = json.load(f)
        self.cookies = cookies
        return cookies

    async def load_cookies_into_browser(self, context):
        if not os.path.exists(self.cookies_file):
            await self.login()
        cookies = self.load_cookies_from_file(self.cookies_file)
        for cookie in cookies:
            await context.add_cookies([cookie])
        return True

    def get_url(
        self: "InstagramService", url: str, params: Optional[dict] = None
    ) -> str:
        """Construct URL with query parameters."""
        if params is None:
            params = {}
        response = url.rstrip("?")
        query_string = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{response}?{query_string}" if query_string else response

    async def login(self: "InstagramService"):
        login = self.credentials
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                proxy={"server": await get_random_proxy()},
            )
            page = await context.new_page()
            await page.goto("https://www.instagram.com/")
            username_locator = page.get_by_label("username")
            await username_locator.fill(login.id)
            await asyncio.sleep(random.uniform(0.5, 1))
            password_locator = page.get_by_label("Password")
            await password_locator.fill(login.password)
            login_button = page.get_by_role("button", name="Log in", exact=True)
            await login_button.click()
            await asyncio.sleep(5)
            if (
                "Enter a 6-digit login code generated by an authentication app."
                in await page.content()
            ):
                authenticator_locator = page.get_by_label("Security Code")
                authenticator = pyotp.TOTP(login.authenticator.replace(" ", ""))
                await authenticator_locator.fill(authenticator.now())
                authenticate_locator = page.get_by_text("Confirm")
                await authenticate_locator.click()
                log.info("need 2fa XD")

            if "login" not in page.url:
                log.info("Login success")

            await asyncio.sleep(15)
            await page.goto("https://yahoo.com")
            state = await page.context.storage_state()
            with open("instagram.com.cookies.json", "wb") as file:
                file.write(orjson.dumps(state["cookies"]))
            await context.close()
            await browser.close()
        await p.stop()
        return True

    @cache()
    async def get_post(
        self: "InstagramService", url: str, **kwargs: Any
    ) -> InstagramPost:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                proxy={"server": await get_random_proxy()},
            )
            await self.load_cookies_into_browser(context)
            page = await context.new_page()
            url = self.get_url(url, {"__a": 1, "__d": "dis"})
            await page.goto(url, wait_until="networkidle")
            response = await page.content()
            soup = BeautifulSoup(response, "html.parser")
            html = json.loads(soup.find("pre").text)
            await browser.close()
        return InstagramPost(**html)

    @cache()
    async def get_user(
        self: "InstagramService", username: str, **kwargs: Any
    ) -> InstagramProfileModelResponse:
        # async def fetch(username: str):
        # 	loop = asyncio.get_running_loop()
        # 	fut = loop.create_future()
        # 	async with async_playwright() as p:
        # 		browser = await p.chromium.launch(headless=True)
        # 		context = await browser.new_context(user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36", proxy=await get_random_proxy(True))
        # 		page = await context.new_page()

        # 		async def find_user(r: PlaywrightRequest):
        # 			if r.url == f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}":
        # 				if fut.done():
        # 					return
        # 				if r.redirected_to:

        # 					return

        # 				resp = await r.response()
        # 				if "json" in resp.headers["content-type"]:
        # 					body = await resp.body()
        # 					body = orjson.dumps(orjson.loads(body))
        # 					with suppress(asyncio.InvalidStateError):
        # 						fut.set_result(body)

        # 			if r.url == f"https://www.instagram.com/{username}":
        # 				with suppress(Exception):
        # 					if fut.done():
        # 						return
        # 					await asyncio.sleep(0.5)
        # 					resp = await r.response()
        # 					await resp.finished()
        # 					body_text = await page.text_content("body")
        # 					if "The link you followed may be broken" in body_text:
        # 						fut.set_result(False)

        # 					html_data = await page.content()

        # 					result = await extract_json_tag(html_data, "biography_with_entities")
        # 					if result:
        # 						log.success("Found {} userdata via extract_json_tag", username)
        # 						data = orjson.dumps({"data": {"user": orjson.loads(result)}})
        # 						fut.set_result(data)

        # 		page.on("request", find_user)
        # 		try:
        # 			await page.goto(f"https://www.instagram.com/{username}", wait_until="domcontentloaded")
        # 			await page.screenshot("instagram.png")
        # 			async with timeout(12):
        # 				data = await fut
        # 			if data is False:
        # 				await page.screenshot("instagram.png")
        # 				log.info("Returning invalid user for {}", username)
        # 				await browser.close()
        # 				return None
        # 		except TimeoutError:
        # 			log.info(f"getting instagram user timed out")
        # 			await page.screenshot("instagram.png")
        # 			await browser.close()
        # 			return None
        # 		except Exception as e:

        # 			await page.screenshot("instagram.png")
        # 			await browser.close()
        # 			log.info("Unknown playwright error {}", get_error(e))
        # 			return None
        # 		finally:
        # 			page.remove_listener("request", find_user)
        # 	data = orjson.loads(data)
        # 	profile = await InstagramProfileModel.from_web_info_response(data)
        # 	final = InstagramProfileModelResponse(**profile.dict())
        # 	final.avatar_url = profile.profile_pic_url_hd
        # 	final.created_at = time.time()
        # 	if profile.edge_owner_to_timeline_media:
        # 		for item in profile.edge_owner_to_timeline_media.edges:
        # 			pi = UserPostItem(**item.node.dict())
        # 			pi.url = f"https://www.instagram.com/p/{pi.shortcode}"
        # 			if item.node.edge_media_to_caption.edges:
        # 				pi.title = item.node.edge_media_to_caption.edges[0].node.text
        # 			pi.display_url = item.node.display_url
        # 			if item.node.video_url:
        # 				pi.video_url = item.node.video_url
        # 			if item.node.edge_media_to_comment:
        # 				pi.comment_count = item.node.edge_media_to_comment.count
        # 			if item.node.edge_liked_by:
        # 				pi.like_count = item.node.edge_liked_by.count
        # 			pi.view_count = item.node.video_view_count or 0
        # 			final.post_items.append(pi)
        # 	await browser.close()
        # 	return final
        # #with suppress(TargetClosedError):
        # return await fetch(username)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            proxy = await get_random_proxy(True)
            #                print(f"using proxy {proxy}")
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                proxy=proxy,
            )
            page = await context.new_page()

            async def fetch(username: str):
                loop = asyncio.get_running_loop()
                fut = loop.create_future()
                try:

                    async def find_user(r: PlaywrightRequest):
                        if (
                            r.url
                            == f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
                        ):
                            if fut.done():
                                return
                            if r.redirected_to:

                                return

                            resp = await r.response()
                            await resp.finished()
                            if "json" in resp.headers["content-type"]:
                                body = await resp.body()
                                body = orjson.dumps(orjson.loads(body))
                                with suppress(asyncio.InvalidStateError):
                                    # print(f"set the future to {body}")
                                    fut.set_result(body)

                        if r.url == f"https://www.instagram.com/{username}":
                            with suppress(Exception):
                                if fut.done():
                                    return
                                await asyncio.sleep(0.5)
                                resp = await r.response()
                                await resp.finished()
                                body_text = await page.text_content("body")
                                if "The link you followed may be broken" in body_text:
                                    fut.set_result(False)

                                html_data = await page.content()

                                result = await extract_json_tag(
                                    html_data, "biography_with_entities"
                                )
                                if result:
                                    log.success(
                                        "Found {} userdata via extract_json_tag",
                                        username,
                                    )
                                    data = orjson.dumps(
                                        {"data": {"user": orjson.loads(result)}}
                                    )
                                    fut.set_result(data)
                                    # print(f"set the future to {data}")

                    try:
                        async with page.expect_request(
                            f"https://www.instagram.com/{username}"
                        ) as req:
                            try:
                                async with page.expect_request(
                                    f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
                                ) as request:
                                    asyncio.ensure_future(
                                        page.goto(
                                            f"https://www.instagram.com/{username}"
                                        )
                                    )
                                    await find_user(await request.value)
                            except Exception:
                                await find_user(await req.value)
                        async with timeout(12):
                            data = await fut
                        if data is False:
                            log.info("Returning invalid user for {}", username)
                            #                       await browser.close()
                            return None
                    except TimeoutError:
                        log.info("getting instagram user timed out")
                        #                    await browser.close()
                        return None
                    except Exception as e:

                        await page.screenshot(path="instagram.png")
                        log.info("Unknown playwright error {}", get_error(e))
                        return None
                except Exception:
                    pass
                data = orjson.loads(data)
                profile = await InstagramProfileModel.from_web_info_response(data)
                final = InstagramProfileModelResponse(**profile.dict())
                final.avatar_url = profile.profile_pic_url_hd
                final.created_at = time.time()
                if profile.edge_owner_to_timeline_media:
                    for item in profile.edge_owner_to_timeline_media.edges:
                        pi = UserPostItem(**item.node.dict())
                        pi.url = f"https://www.instagram.com/p/{pi.shortcode}"
                        if item.node.edge_media_to_caption.edges:
                            pi.title = item.node.edge_media_to_caption.edges[
                                0
                            ].node.text
                        pi.display_url = item.node.display_url
                        if item.node.video_url:
                            pi.video_url = item.node.video_url
                        if item.node.edge_media_to_comment:
                            pi.comment_count = item.node.edge_media_to_comment.count
                        if item.node.edge_liked_by:
                            pi.like_count = item.node.edge_liked_by.count
                        pi.view_count = item.node.video_view_count or 0
                        final.post_items.append(pi)
                await browser.close()
                return final

            with suppress(TargetClosedError):
                d = await fetch(username)
            await browser.close()
        await p.stop()
        return d

    @cache()
    async def get_user_story(
        self: "InstagramService", username: str, **kwargs: Any
    ) -> Optional[InstaStoryModel]:
        async def fetch(username: str):
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            data = None
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    proxy={"server": await get_random_proxy()},
                )
                await self.load_cookies_into_browser(context)
                page = await context.new_page()

                async def on_request(r: PlaywrightRequest):
                    if "https://www.instagram.com/api/v1/feed/reels_media/" in r.url:
                        resp = await r.response()
                        payload = await resp.body()
                        with suppress(asyncio.InvalidStateError):
                            future.set_result(payload)

                page.on("request", on_request)
                try:
                    await page.goto(
                        f"https://www.instagram.com/stories/{username}/",
                        wait_until="domcontentloaded",
                    )
                    if username not in page.url:
                        try:
                            await browser.close()
                        except Exception:
                            pass
                        return None
                    if f"https://www.instagram.com/{username}/" in page.url:
                        try:
                            await browser.close()
                        except Exception:
                            pass
                        return None
                    with suppress(Exception):
                        if "Page not found" in await page.title():
                            log.warning("Username {} is likely invalid.", username)
                            return None

                    html = await page.content()

                    story_feed = await extract_json_tag(
                        html, "xdt_api__v1__feed__reels_media"
                    )
                    if story_feed:
                        story_feed = orjson.loads(story_feed)
                        data = orjson.dumps(
                            story_feed["xdt_api__v1__feed__reels_media"]
                        )

                except Exception as e:
                    log.error("Unknown playwright erorr of type {}", e)
                    try:
                        await browser.close()
                    except Exception:
                        pass
                    return None

                except TimeoutError:
                    log.exception("Timeout on stories")
                    try:
                        await browser.close()
                    except Exception:
                        pass
                    return None
                finally:
                    page.remove_listener("request", on_request)

            if not data:
                try:
                    await browser.close()
                except Exception:
                    pass
                return

            data = InstaStoryModel.parse_raw(data)
            final = InstagramStoryResponse()

            if not data.reels_media:
                try:
                    await browser.close()
                except Exception:
                    pass
                return None
            # s2 = data.reels_media[0].user
            # final.author = InstagramUserResponse(
            #     username=s2.username,
            #     full_name=s2.full_name,
            #     is_private=s2.is_private,
            #     is_verified=s2.is_verified,
            # )
            # for reel in data.reels_media:
            #     for item in reel.items:
            #         story = StoryItem()
            #         final.items.append(story)
            #         story.taken_at = item.taken_at
            #         story.id = item.id
            #         if item.video_versions:
            #             target_url = item.video_versions[0].url
            #             story.is_video = True
            #         else:
            #             for choice in item.image_versions2.candidates:
            #                 _mime = url_to_mime(choice.url)
            #                 if _mime and "heic" not in _mime[0]:
            #                     target_url = choice.url  # noqa: F841
            #                     break
            #             story.is_video = False
            # final.item_count = len(final.items)
            # final.created_at = time.time()
            try:
                await browser.close()
            except Exception:
                pass
            return data

        with suppress(TargetClosedError):
            return await fetch(username)

    async def get_user_highlights(
        self: "InstagramService", username: str, **kwargs: Any
    ):
        raise TypeError("not finished")
        fut = asyncio.get_running_loop().create_future()

        async def handle_ql(r: PlaywrightRequest):
            if fut.done():
                return

            if "https://www.instagram.com/graphql/query/?query_hash" in r.url:
                resp = await r.response()
                body = await resp.body()

                if not body or "edge_highlight_reels" not in body.decode("UTF-8"):
                    return
                if fut.done():
                    return
                with suppress(asyncio.InvalidStateError):
                    fut.set_result(body)

                    log.success("Highlights found in XMR request {} ", r.url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                proxy={"server": await get_random_proxy()},
            )
            await self.load_cookies_into_browser(context)
            page = await context.new_page()
            page.on("request", handle_ql)
            try:
                d = None
                await page.goto(
                    f"https://www.instagram.com/{username}",
                    wait_until="domcontentloaded",
                )
                html = await page.content()
                _data = await extract_json_tag(html, "edge_highlight_reels")
                if _data:
                    log.success("Highlights found in HTML body {} ")
                    d = InstagramHighlightGraphQueryRaw.parse_obj(_data)
                else:
                    data = await fut
                    d = InstagramHighlightGraphQueryRaw.parse_raw(data)
                if not d != None:  # noqa: E711
                    await browser.close()
                    return d

            finally:
                fut.cancel()
                page.remove_listener("request", handle_ql)
        try:
            await browser.close()
        except Exception:
            pass

    async def get_highlight(self: "InstagramService", highlight_id: str, **kwargs: Any):
        raise TypeError("not finished")
        loop = asyncio.get_running_loop()
        fut = loop.create_future()

        async def handle_req(r: PlaywrightResponse):
            if fut.done():
                return

            with suppress(Exception):
                if r.request.resource_type in ("xhr", "script"):
                    if "feed/reels_media" in r.url:
                        data = await r.body()
                        data = orjson.loads(data)
                        fut.set_result(orjson.dumps(data))
                    elif "api/graphql" in r.url:
                        data = await r.body()
                        data = orjson.loads(data)
                        con = data["data"].get(
                            "xdt_api__v1__feed__reels_media__connection"
                        )
                        if con:
                            reels_media = []
                            edges = con["edges"]
                            for e in edges:
                                node = e["node"]
                                reels_media.append(node)
                            fut.set_result(
                                orjson.dumps(
                                    {"reels_media": reels_media, "status": "ok"}
                                )
                            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                proxy={"server": await get_random_proxy()},
            )
            await self.load_cookies_into_browser(context)
            page = await context.new_page()
            page.on("response", handle_req)
            data = None
            try:
                await page.goto(
                    f"https://www.instagram.com/stories/highlights/{highlight_id}",
                    wait_until="domcontentloaded",
                )
                html = await page.content()
                _data = await extract_json_tag(
                    html, "xdt_api__v1__feed__reels_media__connection"
                )
                if _data:
                    _data = orjson.loads(_data)
                    con = _data.get("xdt_api__v1__feed__reels_media__connection")
                    if con:
                        reels_media = []
                        edges = con["edges"]
                        for e in edges:
                            node = e["node"]
                            reels_media.append(node)
                        data = orjson.dumps(
                            {"reels_media": reels_media, "status": "ok"}
                        )

                if not data:
                    data = await fut
                if data:
                    d = InstagramHighlightRaw.parse_raw(data)
                    await browser.close()
                    return d
            finally:
                if not fut.done():
                    fut.cancel()
                page.remove_listener("response", handle_req)
