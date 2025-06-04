import aiohttp, json, os
from discord.ext.commands import CommandError
from lib.worker import offloaded
from DataProcessing.models.mime import mimes


def setup(bot):
    # Not a cog
    pass


async def async_post_json(url, data=None, headers=None, ssl=None):
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, data=data, ssl=ssl) as response:
            return await response.json()


async def async_post_text(url, data=None, headers=None, ssl=None):
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, data=data, ssl=ssl) as response:
            res = await response.read()
            return res.decode("utf-8", "replace")


async def async_post_bytes(url, data=None, headers=None, ssl=None):
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, data=data, ssl=ssl) as response:
            return await response.read()


async def async_head_json(url, headers=None, ssl=None):
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.head(url, ssl=ssl) as response:
            return await response.json()


async def async_dl(url, headers=None, ssl=None):
    # print("Attempting to download {}".format(url))
    total_size = 0
    data = b""
    ext = None
    async with aiohttp.ClientSession() as session:
        async with session.request("HEAD", url) as test:
            if int(test.headers.get("Content-Length", 5)) > 52428800:
                raise CommandError("Content Length Too Large")
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"{url}", ssl=ssl) as response:
            assert response.status == 200
            for e, mime in mimes.items():
                if mime == response.content_type:
                    ext = e
                    break
            while True:
                chunk = await response.content.read(4 * 1024)  # 4k
                data += chunk
                total_size += len(chunk)
                if not chunk:
                    break
    return data, ext


async def async_text(url, headers=None, ssl=None):
    data, ext = await async_dl(url, headers, ssl)
    if data != None:
        return data.decode("utf-8", "replace")
    else:
        return data


async def async_json(url, headers=None, ssl=None):
    data, ext = await async_dl(url, headers, ssl)
    if data != None:
        return json.loads(data.decode("utf-8", "replace"))
    else:
        return data
