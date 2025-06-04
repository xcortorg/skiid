from discord.ext.commands import (
    Cog,
    BadArgument,
    command,
    group,
    CommandError,
    has_permissions,
    hybrid_group,
    check,
)
from discord.app_commands import allowed_installs, allowed_contexts
from tools import timeit
from itertools import chain
from discord.ext import commands
from humanize import naturaldelta
from lib.patch.context import Context
from discord import Client, Embed, File, Member, User, TextChannel, Guild, Message
from aiohttp import ClientSession
from lib.services.cache import cache
from random import shuffle, choice
from .games.blacktea import BlackteaButton, start_blacktea
from .games.tictactoe import TicTacToe
from lib.classes.flags.fun import BlackTeaFlags
from asyncio import (
    ensure_future,
    create_task,
    all_tasks,
    Lock,
    sleep,
    gather,
    CancelledError,
    as_completed,
)
from io import BytesIO
from discord.http import iteration
from discord.utils import chunk_list
from typing import Optional, Union, Dict, List
from collections import defaultdict
from lib.worker import offloaded
from lib.services.MusixMatch import lyrics_command
from ext.information.views import confirmation
from xxhash import xxh3_64_hexdigest
from datetime import datetime
from .util.quote import Quote
import re
import arrow
import msgspec

GOOGLE_KEY = ""

URL_RE = re.compile(
    r"([\w+]+\:\/\/)?([\w\d-]+\.)*[\w-]+[\.\:]\w+([\/\?\=\&\#]?[\w-]+)*\/?", flags=re.I
)


@offloaded
def read_words():
    with open("var/words.txt", "r") as file:
        data = file.read().splitlines()
    return data


def blacktea_round():
    async def predicate(ctx: Context):
        if ctx.bot.blacktea_matches.get(ctx.guild.id):
            await ctx.alert("There's a match of blacktea in progress")

        return ctx.guild.id not in ctx.bot.blacktea_matches.keys()

    return check(predicate)


DDG_ICON = "https://e7.pngegg.com/pngimages/500/732/png-clipart-white-duck-illustration-duckduckgo-logo-icons-logos-emojis-tech-companies.png"


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot
        self.locks = defaultdict(Lock)
        self.buttons: Dict[int, BlackteaButton] = {}
        self.quote = Quote(self.bot)

    @command(
        name="lyrics",
        description="Gets lyrics for the given song",
        example=",lyrics fortunate son",
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def lyrics(self, ctx: Context, *, query: str):
        return await lyrics_command(ctx, query)

    def get_button(self, guild: Guild):
        if button := self.buttons.get(guild.id):
            return button.users
        else:
            return []

    @group(
        name="blacktea",
        description="Find a word with 3 letters!",
        invoke_without_command=True,
    )
    @blacktea_round()
    async def blacktea(self: "Commands", ctx: Context, *, flags: BlackTeaFlags):
        return await create_task(
            start_blacktea(ctx, life_count=flags.lives, timeout=flags.timeout),
            name=f"blacktea-{ctx.guild.id}",
        )

    @blacktea.command(
        name="end", aliases=["stop"], description="end an existing game of blacktea"
    )
    @has_permissions(manage_guild=True)
    async def blacktea_end(self, ctx: Context):
        tasks = all_tasks()
        task = None
        for _t in tasks:
            if _t.get_name() == f"blacktea-{ctx.guild.id}":
                task = _t
                break
        if not task:
            raise CommandError("there is no current blacktea game going on")
        task.cancel()
        if messages := self.bot.blacktea_messages.get(ctx.guild.id):
            for chunk in chunk_list(messages, 99):
                await ctx.channel.delete_messages(chunk)
        try:
            await task
        except CancelledError:
            pass
        return await ctx.success("successfully ended the ongoing blacktea game")

    @command(
        name="image", description="Search Google for an image", example=",image purple"
    )
    async def image(self, ctx: Context, *, query: str):
        safe = True if not ctx.channel.is_nsfw() else False
        message = await ctx.send(
            embed=Embed(
                description=f"🔎 {ctx.author.mention}: **Searching the web..**",
                color=self.bot.color,
            )
        )
        try:
            embeds = []
            results = await self.bot.services.google.get_images(query, safe)
            total_pages = len(results.image_results)
            for i, result in enumerate(results.image_results, start=1):
                embed = Embed(
                    title=f"results for {query}",
                    description=f"[{result.title} ({result.website_name})]({result.url})",
                    color=self.bot.color,
                )
                embed.set_footer(
                    text=f"Page: {i}/{total_pages} For Google Search Results {'(Safe Mode)' if safe else ''} {'(CACHED)' if results.cached else ''}",
                    icon_url="https://cdn4.iconfinder.com/data/icons/logos-brands-7/512/google_logo-google_icongoogle-512.png",
                )
                result.image_url = await self.bot.webserver.add_asset(result.image_url)
                result.redistributed = True
                embed.set_image(url=result.image_url)
                embeds.append(embed)
            return await ctx.alternative_paginate(embeds, message)
        except Exception:
            pass

        try:
            results = await self.bot.services.brave.image_search(query, safe)

        except Exception:
            return await ctx.fail(f"no results for **{query}**")

        embeds = [
            Embed(
                title=f"results for {query}",
                description=f"[{result.title} - ({result.domain})]({result.source})",
                color=self.bot.color,
            )
            .set_image(url=result.url)
            .set_footer(
                text=f"Page {i}/{len(results.results)} of Google Images",
                icon_url="https://cdn4.iconfinder.com/data/icons/logos-brands-7/512/google_logo-google_icongoogle-512.png",
            )
            for i, result in enumerate(results.results, start=1)
        ]

        return await ctx.alternative_paginate(embeds, message)

    @command(
        name="google",
        description="Search the largest search engine on the internet",
        example=",google purple",
    )
    async def google(self, ctx: Context, *, query: str):
        safe = True if not ctx.channel.is_nsfw() else False
        message = await ctx.send(
            embed=Embed(
                description=f"🔎 {ctx.author.mention}: **Searching the web..**",
                color=self.bot.color,
            )
        )
        try:
            saf = "(Safe Mode)" if safe else ""
            data = await self.bot.services.google.search(query, safe)
            if data.cached:
                saf += " (Cached)"
            embeds = []
            e = Embed(
                title=f"Google Search Results for {query}", color=self.bot.color
            ).set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
            total_pages = round(len(data.search_results) / 3)
            if data.knowledge_panel:
                page = 1
                embed = e.copy()
                embed.title = data.knowledge_panel.title
                if data.knowledge_panel.subtitle:
                    embed.title += f" - {data.knowledge_panel.subtitle}"
                embed.description = f"{data.knowledge_panel.subtitle} {data.knowledge_panel.description} [{data.knowledge_panel.source}]({data.knowledge_panel.url})"
                for key, value in data.knowledge_panel.additional_info.items():
                    embed.add_field(name=key, value=value, inline=True)
                embed.set_footer(
                    text=f"Page: {page}/{total_pages} For Google Search Results {saf}",
                    icon_url="https://cdn4.iconfinder.com/data/icons/logos-brands-7/512/google_logo-google_icongoogle-512.png",
                )
                embeds.append(embed)
            else:
                page = 0
            amount = 0
            embed = e.copy()
            for i, r in enumerate(data.search_results, start=1):
                if not r.url.startswith("https://"):
                    continue
                amount += 1
                try:
                    embed.add_field(
                        name=r.title,
                        value=f"[{r.citation.split('https://')[1]}]({r.url})\n"
                        + r.description,
                        inline=False,
                    )
                except Exception:
                    embed.add_field(
                        name=r.title,
                        value=f"[{r.citation.split('https://')[0]}]({r.url})\n"
                        + r.description,
                        inline=False,
                    )
                if amount == 3:
                    embed.url = f"https://google.com/search?q={query.replace(' ', '+')}"
                    page += 1
                    embed.set_footer(
                        text=f"Page: {page}/{total_pages} For Google Search Results {'(Safe Mode)' if safe else ''} {'(CACHED)' if data.cached else ''}",
                        icon_url="https://cdn4.iconfinder.com/data/icons/logos-brands-7/512/google_logo-google_icongoogle-512.png",
                    )
                    embeds.append(embed)
                    embed = e.copy()
                    amount = 0
            return await ctx.alternative_paginate(embeds, message)
        except Exception:
            pass

        try:
            results = await self.bot.services.brave.search(query, safe)
        except Exception:
            embed = await ctx.fail(
                f"**{query[:20]}** has **no results or google is currently ratelimiting us**",
                return_embed=True,
            )
            return await message.edit(embed=embed)
        embeds_ = []
        page_start = 0
        res = chunk_list(results.results, 3)
        pages = len(res)
        if results.main_result:
            if results.main_result.title:
                try:
                    embed = Embed(
                        color=self.bot.color,
                        title=results.main_result.title,
                        url=results.main_result.url or self.bot.config["domain"],
                        description=results.main_result.description,
                    ).set_footer(
                        text=f"Page 1/{pages+1} of Google Search {'(Safe Mode)' if safe else ''}",
                        icon_url="https://cdn4.iconfinder.com/data/icons/logos-brands-7/512/google_logo-google_icongoogle-512.png",
                    )
                    for key, value in results.main_result.full_info.items():
                        embed.add_field(
                            name=key.title(), value=str(value), inline=False
                        )
                    embeds_.append(embed)
                    page_start += 1
                except Exception as e:
                    if ctx.author.name == "aiohttp":
                        raise e
                    pass

        def get_domain(r):
            return r.split("https://", 1)[1].split("/")[0]

        embeds = [
            Embed(
                title="Search Results",
                description="\n\n".join(
                    f"**[{result.title[:255]}](https://{get_domain(result.url)})**\n{result.description}"
                    for result in page
                ),
                color=self.bot.color,
            )
            .set_footer(
                text=f"Page {i+page_start}/{pages+page_start} of Google Search {'(Safe Mode)' if safe else ''} {'(CACHED)' if results.cached else ''}",
                icon_url="https://cdn4.iconfinder.com/data/icons/logos-brands-7/512/google_logo-google_icongoogle-512.png",
            )
            .set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
            for i, page in enumerate(res, start=1)
        ]
        embeds_.extend(embeds)
        return await ctx.alternative_paginate(embeds_, message)

    @command(
        name="duckduckgo",
        description="Search the DuckDuckGo search engine",
        example=",duckduckgo purple",
    )
    async def duckduckgo(self, ctx: Context, *, query: str):
        message = await ctx.send(
            embed=Embed(
                description=f"🔎 {ctx.author.mention}: **Searching the web..**",
                color=self.bot.color,
            )
        )
        results = await self.bot.services.duckduckgo.search(
            keywords=query,
            safesearch="moderate" if not ctx.channel.is_nsfw() else "off",
            max_results=24,
        )
        res = chunk_list(results.results, 3)
        pages = len(res)
        embeds_ = []
        embeds = [
            Embed(
                title="Search Results",
                description="\n\n".join(
                    f"**[{result.title[:255]}](https://{result.href})**\n{result.body}"
                    for result in page
                ),
                color=self.bot.color,
            )
            .set_footer(
                text=f"Page {i+0}/{pages+0} of Duck Duck Go Results {'(Safe Mode)' if not ctx.channel.is_nsfw() else ''}",
                icon_url=DDG_ICON,
            )
            .set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
            for i, page in enumerate(res, start=1)
        ]
        embeds_.extend(embeds)
        return await ctx.alternative_paginate(embeds_, message)

    @command(
        name="duckduckgoimage",
        description="Search duckduckgo for an image",
        example=",duckduckgoimage purple",
    )
    async def duckduckgoimage(self, ctx: Context, *, query: str):
        message = await ctx.send(
            embed=Embed(
                description=f"🔎 {ctx.author.mention}: **Searching the web..**",
                color=self.bot.color,
            )
        )
        raise Exception(
            "couldnt get the look of this command because bleeds errored LMFAOOOO"
        )
        results = await self.bot.services.duckduckgo.image_search(
            keywords=query,
            safesearch="moderate" if not ctx.channel.is_nsfw() else "off",
            max_results=99,
        )
        embeds = []

    async def get_tone(self, query: str):
        key = xxh3_64_hexdigest(f"tone:{query}")
        if not (v := await self.bot.redis.get(key)):
            json_data = {
                "comment": {"text": query},
                "languages": ["en"],
                "requestedAttributes": {
                    "TOXICITY": {},
                    "UNSUBSTANTIAL": {},
                    "LIKELY_TO_REJECT": {},
                    "INFLAMMATORY": {},
                    "NUANCE_EXPERIMENTAL": {},
                    "FLIRTATION": {},
                    "SPAM": {},
                    "ATTACK_ON_AUTHOR": {},
                    "ATTACK_ON_COMMENTER": {},
                    "INCOHERENT": {},
                    "SEXUALLY_EXPLICIT": {},
                },
            }

            async with ClientSession() as session:
                async with session.request(
                    "POST",
                    f"https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={GOOGLE_KEY}",
                    json=json_data,
                ) as response:
                    v = await response.json()
                    await self.bot.redis.set(key, msgspec.json.encode(v))
        else:
            v = msgspec.json.decode(v)
        return v

    @command(
        name="tone",
        description="Run Google Perspective on text",
        example=",tone purple",
        aliases=["ton"],
    )
    async def tone(self, ctx: Context, *, query: str):
        data = await self.get_tone(query)
        embed = Embed(description=f"```{query}```")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        last = None
        values = []
        for key, value in data["attributeScores"].items():
            if key == "NUANCE_EXPERIMENTAL":
                embed.add_field(
                    name="OFF TOPIC",
                    value=f"{value['summaryScore']['value'] * 100:.1f}%",
                    inline=True,
                )
            elif key == "SEXUALLY_EXPLICIT":
                last = {
                    "name": "NSFW",
                    "value": f"{value['summaryScore']['value'] * 100:.1f}%",
                    "inline": True,
                }
            else:
                embed.add_field(
                    name=key.replace("_", " "),
                    value=f"{value['summaryScore']['value'] * 100:.1f}%",
                    inline=True,
                )
            values.append(int(value["summaryScore"]["value"] * 100))
        embed.add_field(**last)
        safety = v = (
            "Very Unlikely"
            if any(
                data["attributeScores"][attr]["summaryScore"]["value"] > 0.75
                for attr in ["SEXUALLY_EXPLICIT", "TOXICITY", "LIKELY_TO_REJECT"]
            )
            else (
                "Unlikely"
                if any(
                    data["attributeScores"][attr]["summaryScore"]["value"] > 0.55
                    for attr in ["SEXUALLY_EXPLICIT", "TOXICITY", "LIKELY_TO_REJECT"]
                )
                else (
                    "Most Likely"
                    if any(
                        data["attributeScores"][attr]["summaryScore"]["value"] < 0.4
                        for attr in [
                            "SEXUALLY_EXPLICIT",
                            "TOXICITY",
                            "LIKELY_TO_REJECT",
                        ]
                    )
                    else (
                        "Very Likely"
                        if any(
                            data["attributeScores"][attr]["summaryScore"]["value"] < 0.1
                            for attr in [
                                "SEXUALLY_EXPLICIT",
                                "TOXICITY",
                                "LIKELY_TO_REJECT",
                            ]
                        )
                        else None
                    )
                )
            )
        ) or "Most Likely"
        embed.add_field(name="Safe", value=safety, inline=True)
        return await ctx.send(embed=embed)
