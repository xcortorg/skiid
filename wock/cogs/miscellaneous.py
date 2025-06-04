import asyncio
import io
import typing
from asyncio import Lock
from collections import defaultdict
from datetime import datetime
from typing import Optional

import aiohttp
import arrow
import discord
from discord.ext import commands
from discord.ext.commands import Cog
from tools.important import (Context,  # type: ignore # type: ignore
                             PatPatCreator)

if typing.TYPE_CHECKING:
    from tools.wock import Wock  # type: ignore

from cashews import cache
from pydantic import BaseModel
from tools.quote import Quotes  # type: ignore

cache.setup("mem://")
eros_key = "c9832179-59f7-477e-97ba-dca4a46d7f3f"


class ValorantProfile(BaseModel):
    account_level: Optional[int] = None
    avatar_url: Optional[str] = None
    current_rating: Optional[str] = None
    damage_round_ratio: Optional[float] = None
    deaths: Optional[int] = None
    headshot_percent: Optional[float] = None
    kd_ratio: Optional[float] = None
    kills: Optional[int] = None
    last_update: Optional[int] = None
    lost: Optional[int] = None
    matches_played: Optional[int] = None
    name: Optional[str] = None
    peak_rating_act: Optional[str] = None
    peak_rating: Optional[str] = None
    puuid: Optional[str] = None
    region: Optional[str] = None
    tag: Optional[str] = None
    win_percent: Optional[float] = None
    wins: Optional[int] = None

    async def to_embed(self, ctx: Context) -> discord.Embed:
        embed = discord.Embed(
            color=ctx.bot.color,
            title=f"{self.name}#{self.tag}",
            url=f"https://eros.rest/valorant?user={self.name}&tag={self.tag}",
        )
        embed.add_field(
            name="MMR",
            value=f"""**Current Rank:** {self.current_rating}\n**Peak:** {self.peak_rating}\n**Peak Act:** {self.peak_rating_act}""",
            inline=True,
        )
        embed.add_field(
            name="Stats",
            value=f"""**KDR:** {str(self.kd_ratio)[2]}\n**WR:** {str(self.wr_ratio)[2]}\n**HSR:** {str(self.hs_ratio)[2]}\n""",
            inline=True,
        )
        embed.set_thumbnail(url=self.avatar_url)
        embed.set_footer(
            text=f"Region: {self.region} | Matches: {self.matches_played} | DPR: {int(self.damage_round_ratio)}"
        )
        return embed

    @classmethod
    async def from_snowflake(cls, user: str, tag: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://eros.rest/valorant",
                params={"user": user, "tag": tag},
                headers={"api-key": eros_key},
            ) as response:
                data = await response.read()
        return cls.parse_raw(data)  # type: ignore


class ValorantUser(commands.Converter):
    async def convert(self, ctx: Context, argument: str):  # type: ignore
        if "#" not in argument:
            raise commands.CommandError(
                "please include a `#` inbetween the user and tag"
            )
        return argument.split("#")


snipe_message_author = {}
snipe_message_content = {}
snipe_message_attachment = {}
snipe_message_author_avatar = {}
snipe_message_time = {}
snipe_message_sticker = {}
snipe_message_embed = {}
from tools import valorant  # noqa: E402


class Miscellaneous(Cog):
    def __init__(self, bot: "Wock") -> None:
        self.bot = bot
        self.bot.afks = {}
        self.quotes = Quotes(self.bot)
        self.queue = defaultdict(Lock)

    @commands.command(
        name="caption",
        brief="Add a Caption an image",
        example=",caption (with a reply) uwu",
    )
    async def caption(self, ctx: Context, *, text: str):
        return await self.bot.rival.caption(ctx, text)

    @commands.command(
        name="valorant",
        brief="lookup a user's valorant stats",
        usage=",valorant <user>#<tag>",
        example=",valorant cop#00001",
    )
    async def valorant(self, ctx: Context, user: ValorantUser):
        #      try:
        return await valorant.valorant(ctx, f"{user[0]}#{user[1]}")
        #        except:
        #           return await ctx.fail(f"that valorant user couldn't be fetched")
        embed = await data.to_embed(ctx)  # type: ignore  # noqa: F821
        return await ctx.send(embed=embed)

    @commands.command(
        name="quote",
        brief="Quote a message sent by a user",
        example=",quote {as reply}",
    )
    async def quote(self, ctx: Context, message: discord.Message = None):
        return await self.quotes.get_caption(ctx, message)

    @commands.command(
        name="variables",
        brief="show all embed variables used for the bots embed creator",
        example=",variables",
    )
    async def variables(self, ctx: Context):
        from tools.important.subclasses.parser import Script  # type: ignore

        b = Script("{embed}{description: sup}", user=ctx.author)
        rows = [f"`{k}`" for k in b.replacements.keys()]
        rows.extend([f"`{k}`" for k in ["{timer}", "{ends}", "{prize}"]])
        return await self.bot.dummy_paginator(
            ctx, discord.Embed(title="variables", color=self.bot.color), rows
        )

    @commands.command(
        name="tts",
        brief="Allow the bot to speak to a user in a voice channel",
        example=",tts whats up little girl",
    )
    async def tts(self, ctx: Context, *, message: str):
        from aiogtts import aiogTTS  # type: ignore

        if ctx.author.voice is None:
            return
        if voice_channel := ctx.author.voice.channel:
            if ctx.voice_client is None:
                vc = await voice_channel.connect()
            else:
                if ctx.voice_client.channel != voice_channel:
                    await ctx.voice_client.move_to(voice_channel)
            vc = ctx.voice_client
            text = f"{message}"
            i = io.BytesIO()
            #            aiogtts = aiogTTS()
            async with self.queue[ctx.guild.id]:
                await asyncio.sleep(0.5)
                aiogtts = aiogTTS()
                await aiogtts.save(text, ".tts.mp3", lang="en")
                await aiogtts.write_to_fp(text, i, slow=False, lang="en")
                vc.play(discord.FFmpegPCMAudio(source="./.tts.mp3"))
        #                os.remove(".tts.mp3")
        else:
            return await ctx.fail("you aren't in a voice channel")

    @commands.hybrid_command(
        name="afk",
        brief="Set an afk message before going offline",
        example=",afk going to that little girls house",
    )
    async def afk(
        self, ctx: commands.Context, *, status: str = "AFK"
    ) -> discord.Message:
        if self.bot.afks.get(ctx.author.id):
            return await ctx.warning("You are **already afk**")
        self.bot.afks[ctx.author.id] = {"date": datetime.now(), "status": str(status)}
        return await ctx.success(f"You're now afk with the status: **{status}**")

    @commands.command(name="uwuify", brief="uwuify a message", aliases=["uwu"])
    async def uwuify(self, ctx: Context, *, message: str):
        try:
            text = await self.bot.rival.uwuify(message)
            return await ctx.send(text)
        except:  # noqa: E722
            return await ctx.fail("couldn't uwuify that message")

    @commands.hybrid_command(
        name="finger",
        aliases=("playwith",),
        exmaple=",finger @o_5v",
        brief="Finger another users profile picture",
    )
    async def patpat(
        self,
        ctx: commands.Context,
        user: discord.User | discord.Member = commands.Author,
    ) -> discord.Message:
        async with ctx.typing():
            patpat_buffer = await PatPatCreator(
                image_url=user.avatar.url if user.avatar else user.display_avatar.url
            ).create_gif()
            patpat_gif = discord.File(patpat_buffer, filename="pat.gif")
            return await ctx.send(file=patpat_gif)

    @commands.command(
        name="snipe",
        aliases=["s"],
        example=",snipe 4",
        breif="Retrive a recently deleted message",
    )
    async def snipe(self, ctx: Context, index: int = 1):
        if not (
            snipe := await self.bot.snipes.get_entry(
                ctx.channel, type="snipe", index=index
            )
        ):
            return await ctx.fail(
                f"There are **no deleted messages** for {ctx.channel.mention}"
            )
        total = snipe[1]
        snipe = snipe[0]
        if await self.bot.db.fetch(
            """SELECT * FROM filter_event WHERE guild_id = $1 AND event = $2""",
            ctx.guild.id,
            "snipe",
        ):
            if content := snipe.get("content"):
                if (
                    "discord.gg/" in content.lower()
                    or "discord.com/" in content.lower()
                    or "discordapp.com/" in content.lower()
                ):
                    return await ctx.fail("snipe had **filtered content**")
                content = "".join(c for c in content if c.isalnum() or c.isspace())
                if (
                    "discord.gg" in content.lower()
                    or "discord.com/" in content.lower()
                    or "discordapp.com" in content.lower()
                ):
                    return await ctx.fail("snipe had **filtered content**")
                for keyword in self.bot.cache.filter.get(ctx.guild.id, []):
                    if keyword.lower() in content.lower():
                        return await ctx.fail("snipe had **filtered content**")
        embed = discord.Embed(
            color=self.bot.color,
            description=(
                snipe.get("content")
                or (
                    snipe["embeds"][0].get("description") if snipe.get("embeds") else ""
                )
            ),
            timestamp=datetime.fromtimestamp(snipe.get("timestamp")),
        )

        embed.set_author(
            name=snipe.get("author").get("name"),
            icon_url=snipe.get("author").get("avatar"),
        )

        if att := snipe.get("attachments"):
            embed.set_image(url=att[0])

        elif sticks := snipe.get("stickers"):
            embed.set_image(url=sticks[0])

        embed.set_footer(
            text=f"Deleted {arrow.get(snipe.get('timestamp')).humanize()} | {index}/{total}"
        )

        return await ctx.send(embed=embed)

    @commands.command(
        name="editsnipe",
        aliases=["es"],
        example=",editsnipe 2",
        brief="Retrieve a messages original text before edited",
    )
    async def editsnipe(self, ctx: Context, index: int = 1):
        if not (
            snipe := await self.bot.snipes.get_entry(
                ctx.channel, type="editsnipe", index=index
            )
        ):
            return await ctx.fail("There is nothing to snipe.")
        total = snipe[1]
        snipe = snipe[0]
        if await self.bot.db.fetch(
            """SELECT * FROM filter_event WHERE guild_id = $1 AND event = $2""",
            ctx.guild.id,
            "snipe",
        ):
            if content := snipe.get("content"):
                if (
                    "discord.gg/" in content.lower()
                    or "discord.com/" in content.lower()
                    or "discordapp.com/" in content.lower()
                ):
                    return await ctx.fail("snipe had **filtered content**")
                content = "".join(c for c in content if c.isalnum() or c.isspace())
                if (
                    "discord.gg" in content.lower()
                    or "discord.com/" in content.lower()
                    or "discordapp.com/" in content.lower()
                ):
                    return await ctx.fail("snipe had **filtered content**")
                for keyword in self.bot.cache.filter.get(ctx.guild.id, []):
                    if keyword.lower() in content.lower():
                        return await ctx.fail("editsnipe had **filtered content**")
        embed = discord.Embed(
            color=self.bot.color,
            description=(
                snipe.get("content")
                or ("Message contains an embed" if snipe.get("embeds") else "")
            ),
            timestamp=datetime.fromtimestamp(snipe.get("timestamp")),
        )

        embed.set_author(
            name=snipe.get("author").get("name"),
            icon_url=snipe.get("author").get("avatar"),
        )

        if att := snipe.get("attachments"):
            embed.set_image(url=att[0])

        elif sticks := snipe.get("stickers"):
            embed.set_image(url=sticks[0])

        embed.set_footer(
            text=f"Edited {arrow.get(snipe.get('timestamp')).humanize()} | {index}/{total}",
            icon_url=ctx.author.display_avatar,
        )

        return await ctx.send(embed=embed)

    @commands.command(
        name="reactionsnipe",
        aliases=["reactsnipe", "rs"],
        brief="Retrieve a deleted reaction from a message",
        example=",reactionsipe 2",
    )
    async def reactionsnipe(self, ctx: Context, index: int = 1):
        if not (
            snipe := await self.bot.snipes.get_entry(
                ctx.channel, type="reactionsnipe", index=index
            )
        ):
            return await ctx.fail("There is nothing to snipe.")
        snipe[1]  # type: ignore
        snipe = snipe[0]
        embed = discord.Embed(
            color=self.bot.color,
            description=(
                f"""**{str(snipe.get('author').get('name'))}** reacted with {snipe.get('reaction')
                if not snipe.get('reaction').startswith('https://cdn.discordapp.com/')
                else str(snipe.get('reaction'))} <t:{int(snipe.get('timestamp'))}:R>"""
            ),
        )

        return await ctx.send(embed=embed)

    @commands.command(
        name="clearsnipe",
        aliases=["cs"],
        brief="Clear all deleted messages from wock",
        example=",clearsnipe",
    )
    @commands.has_permissions(manage_messages=True)
    async def clearsnipes(self, ctx: Context):
        await self.bot.snipes.clear_entries(ctx.channel)
        return await ctx.success(f"**Cleared** snipes for {ctx.channel.mention}")

    @commands.group(
        name="birthday",
        aliases=["bday", "bd"],
        brief="View a users set birthday",
        example=",birthday @o_5v",
        invoke_without_command=True,
    )
    async def birthday(
        self,
        ctx: Context,
        user: typing.Union[discord.Member, discord.User] = commands.Author,
    ):
        bday = await self.bot.db.fetchval(
            "SELECT birthday FROM birthdays WHERE user_id = $1;", user.id
        )
        if not bday:
            y = discord.Embed(
                description=f"{user.mention} does **not** have their **birthday set**"
            )
            return await ctx.send(embed=y)
        x = discord.Embed(description=f"{user.mention}'s birthday is on **{bday}**")
        return await ctx.send(embed=x)

    @birthday.command(
        name="set",
        brief="Set your birthday through wock",
        example=",birthday set december 31",
    )
    async def birthday_set(self, ctx: Context, *, bday: str):
        bdays = bday.split()
        if len(bdays) <= 1 or len(bdays) > 2:
            return await ctx.fail("Please provide a **valid** birthday")

        if bdays[0].lower() not in (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ) or int(bdays[1]) not in range(1, 32):
            return await ctx.fail("Provide a **valid** birthday")

        await self.bot.db.execute(
            "INSERT INTO birthdays (user_id, birthday) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET birthday = EXCLUDED.birthday;",
            ctx.author.id,
            bday,
        )
        return await ctx.success(
            f"**binded** your birthday to **`{bdays[0]} {bdays[1]}`**"
        )

    @birthday.command(
        name="reset", brief="Clear your set birthday", example="birthday reset"
    )
    async def birthday_clear(self, ctx: Context):
        bday = await self.bot.db.fetchval(
            "SELECT birthday FROM birthdays WHERE user_id = $1;", ctx.author.id
        )
        if not bday:
            return await ctx.fail("You **don't have a birthday** set to clear")

        await self.bot.db.execute(
            "DELETE FROM birthdays WHERE user_id = $1;",
            ctx.author.id,
        )
        return await ctx.success("**reset** your **birthday settings**")

    @commands.command(
        name="selfpurge",
        example=",selfpurge 100",
        brief="Clear your messages from a chat",
    )
    @commands.bot_has_permissions(manage_messages=True)
    async def selfpurge(self, ctx, amount: int):
        amount = amount + 1

        def check(message):
            return message.author == ctx.message.author

        await ctx.message.delete()
        deleted_messages = await ctx.channel.purge(limit=amount, check=check)
        if len(deleted_messages) > amount:
            deleted_messages = deleted_messages[:amount]
            return

    async def check_role(self, ctx, role: discord.Role):
        if (
            ctx.author.top_role.position <= role.position
            and not ctx.author.id == ctx.guild.owner_id
        ):
            await ctx.fail("your role isn't higher then that role")
            return False
        return True


async def setup(bot: "Wock") -> None:
    await bot.add_cog(Miscellaneous(bot))
