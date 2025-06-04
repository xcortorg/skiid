import discord, asyncio, time
from discord.ext import commands
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel
from aiohttp import ClientSession
from orjson import loads
from tool.worker import offloaded
from tools import timeit
from cashews import cache
import humanize
from cogs.miscellaneous import get_donator
from discord.app_commands import allowed_contexts, allowed_installs

cache.setup("mem://")


@offloaded
def load_json(filepath: str):
    with open(filepath, "rb") as file:
        data = loads(file.read())
    return data


def get_timestamp() -> float:
    return datetime.now().timestamp()


class AIResponse(BaseModel):
    text: str
    data: Any
    time_elapsed: float


class AI:
    def __init__(self):
        self.models = {}
        self._cookies = None

    async def cookies(self):
        if not self._cookies:
            data = await load_json("/root/www.blackbox.ai.cookies.json")
            self._cookies = {cookie["name"]: cookie["value"] for cookie in data}
        return self._cookies

    async def _prompt(self, prompt: str, expert: str = "") -> str:
        prompt = (
            prompt.replace("'", "\u2018")
            .replace("'", "\u2019")
            .replace('"', "\u201c")
            .replace('"', "\u201d")
            .replace("'", "\u0027")
            .replace('"', "\u0022")
        )
        async with ClientSession(cookies=await self.cookies()) as session:

            headers = {
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.7",
                "cache-control": "no-cache",
                "origin": "https://www.blackbox.ai",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": "https://www.blackbox.ai/",
                "sec-ch-ua": '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "sec-gpc": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            }

            # First POST request
            json_1 = {
                "query": prompt,
                "messages": [{"id": "iU1JsxF", "content": prompt, "role": "user"}],
                "index": None,
            }
            async with session.post(
                "https://www.blackbox.ai/api/check", json=json_1, headers=headers
            ) as response_1:
                r_1_json = await response_1.json()

            # Second POST request
            json_2 = {
                "messages": [{"id": "iU1JsxF", "content": prompt, "role": "user"}],
                "id": "iU1JsxF",
                "previewToken": None,
                "userId": None,
                "codeModelMode": True,
                "agentMode": {},
                "trendingAgentMode": (
                    {"mode": True, "id": expert.lower()} if expert.lower() != "" else {}
                ),
                "isMicMode": False,
                "userSystemPrompt": None,
                "maxTokens": 1024,
                "playgroundTopP": None,
                "playgroundTemperature": None,
                "isChromeExt": False,
                "githubToken": "",
                "clickedAnswer2": False,
                "clickedAnswer3": False,
                "clickedForceWebSearch": False,
                "visitFromDelta": False,
                "mobileClient": False,
                "userSelectedModel": None,
                "validated": "00f37b34-a166-4efb-bce5-1312d87f2f94",
                "imageGenerationMode": False,
                "webSearchModePrompt": False,
                "deepSearchMode": False,
            }
            async with session.post(
                "https://www.blackbox.ai/api/chat", json=json_2, headers=headers
            ) as response_2:
                response_data = await response_2.text()

        ret = (
            "\n".join(response_data.splitlines()[2:])
            if "Sources:" in response_data
            else response_data
        )

        if "$@$" in ret:
            ret = ret[ret.index("$@$", 2) + 3 :]

        if "$~~~$" in ret:
            ret = ret[ret.index("$~~~$", 2) + 5 :]
        ret = ret.replace("<br>", "")
        ret = (
            ret.replace(", try unlimited chat https://www.blackbox.ai/", "")
            .replace("blackbox.ai", "greed")
            .replace("blackbox", "greed")
        )
        return ret

    @cache(ttl=30000, key="aiii:{prompt}")
    async def generate(self, prompt: str):
        __prompt = "You are being used as a chatbot for my discord bot do not return any html or any markdown or any json content just a string with the answer to the question asked"
        __prompt += f"\n{prompt}"
        text = await self._prompt(__prompt)
        return text

    async def generate_response(self, prompt: str) -> Optional[AIResponse]:
        data = None
        t = None
        async with timeit() as timer:
            text = await self.generate(prompt)
            if "[{" in text:
                obj, content = text.split("[", 1)[1].split("]$~~~$", 1)
                content = "\n".join(m for m in content.splitlines() if len(m) > 1)
                try:
                    obj = loads(f"[{obj}]")
                except Exception:
                    obj = {}
                data = obj
                t = content
            else:
                data = {}
                t = text
        return AIResponse(text=t, data=data, time_elapsed=timer.elapsed)


class ai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ai = AI()
        #        self.bot.loop.create_task(self.task())
        self.future = None  # I need to add a future for revalidating ai keys - lim

    async def task(self):
        while True:
            if self.future:
                await self.future
            await asyncio.sleep(300)
            await self.bot.close()

    def split_text(self, text: str, chunk_size: int = 1999):
        # Split the text into chunks of `chunk_size` characters
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    @commands.hybrid_command(name="ai")
    @allowed_contexts(guilds=True, dms=True, private_channels=True)
    @allowed_installs(guilds=True, users=True)
    async def ask(self, ctx, *, question: str):
        """Command to ask the AI a question."""
        if not await get_donator(ctx, ctx.author.id):
            raise commands.CommandError("this command is for donators only")
        message = await ctx.normal(
            "<:moon:1336683823894757508> please wait whilst I generate a response..."
        )
        try:
            response = await self.ai.generate_response(question)
            if len(response.text) > 1000:
                text = self.split_text(response.text, 1000)
                embeds = [
                    discord.Embed(title=f"{question[:100]}", description=t).set_footer(
                        text=f"Page {i}/{len(text)} ∙ ⏰ took {humanize.naturaldelta(response.time_elapsed, minimum_unit='microseconds')}"
                    )
                    for i, t in enumerate(text, start=1)
                ]
                return await ctx.alternative_paginate(embeds, message=message)
            else:
                await message.edit(
                    embeds=[
                        discord.Embed(
                            title=question[:100],
                            color=self.bot.color,
                            description=response.text,
                        ).set_footer(
                            text=f"⏰ took {humanize.naturaldelta(response.time_elapsed, minimum_unit='microseconds')}"
                        )
                    ]
                )
        except Exception as e:
            if ctx.author.name == "aiohttp":
                raise e
            raise commands.CommandError("that was a flagged prompt")


async def setup(bot):
    await bot.add_cog(ai(bot))
