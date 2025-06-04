from discord.ext.commands import Cog, CommandError
from discord import utils, Guild, Client, Embed, File, Message
from lib.patch.context import Context
import re
import asyncio
from aiomisc.backoff import asyncretry
from io import BytesIO
import os
from aiohttp import ClientSession
import humanize
from lib.services.YouTube import extract
from lib.services.Twitter import from_id
from lib.services.TikTok import PostResponse
from lib.classes.checks import event_checks
from cashews import cache
from os import remove
from lib.services.compress import compress
from loguru import logger

cache.setup("mem://")

TWITTER_REGEX = re.compile(
    r"\b(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\b\/status\/(\d+)"
)
TIKTOK_REGEX = re.compile(
    r"(?:http\:|https\:)?\/\/(?:www\.)?tiktok\.com\/@.*\/(?:photo|video)\/\d+|(?:http\:|https\:)?\/\/(?:www|vm|vt|m).tiktok\.com\/(?:t/)?(\w+)"
)


def format_int(n: int) -> str:
    m = humanize.intword(n)
    m = (
        m.replace(" million", "m")
        .replace(" billion", "b")
        .replace(" trillion", "t")
        .replace(" thousand", "k")
        .replace(" hundred", "")
    )
    return m


@asyncretry(max_tries=3, pause=0.1)
async def fetch_asset(url: str) -> bytes:
    async with ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise TypeError(f"{url} wasn't a valid asset")
            data = await response.read()
    return data


@cache(ttl="30m", key="asset:{url}")
async def get_asset(url: str):
    return await fetch_asset(url)


@cache(ttl="30m", key="tiktok:{url}")
async def fetch_tiktok(url: str) -> PostResponse:
    return await PostResponse.from_response(url, os.environ["EROS_KEY"])


class Bot_Events(Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    def get_embed(self):
        embed = Embed(
            title=f"Getting started with {self.bot.user.name}",
            description=(
                f"Hey! Thanks for your interest in **{self.bot.user.name} bot**. "
                "The following will provide you with some tips on how to get started with your server!"
            ),
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.add_field(
            name="**Prefix 🤖**",
            value=(
                "The most important thing is my prefix. "
                "It is set to `,` by default for this server and it is also customizable, "
                "so if you don't like this prefix, you can always change it with `prefix set` command!"
            ),
            inline=False,
        )
        embed.add_field(
            name="**Moderation System 🛡️**",
            value=(
                "If you would like to use moderation commands, such as `jail`, `ban`, `kick` and so much more... "
                "please run the `setme` command to quickly set up the moderation system."
            ),
            inline=False,
        )
        embed.add_field(
            name="**Documentation and Help 📚**",
            value=(
                "You can always visit our [documentation](https://docs.{self.bot.config['domain']}) "
                "and view the list of commands that are available [here](https://{self.bot.config['domain']}/help)"
                " - and if that isn't enough, feel free to join our [Support Server](https://discord.gg/{self.bot.config['invite_code']}) for extra assistance!"
            ),
        )
        return embed

    async def join_message(self, guild: Guild):
        if channel := utils.find(
            lambda c: c.permissions_for(guild.me).embed_links, guild.text_channels
        ):
            embed = self.get_embed()
            return await channel.send(embed=embed)
        else:
            try:
                return await guild.owner.send(embed=self.get_embed())
            except Exception:
                return None

    @Cog.listener("on_guild_add")
    async def subscription_add(self, guild: Guild):
        return await self.join_message(guild)

    @event_checks
    @Cog.listener("on_media_repost")
    async def on_media_repost(self, ctx: Context):
        await asyncio.gather(
            *[
                self.on_youtube_repost(ctx),
                self.on_twitter_repost(ctx),
                self.on_tiktok_repost(ctx),
            ]
        )

    @Cog.listener("on_youtube_repost")
    async def youtube_repost(self, message: Message, url: str):
        post = await extract(url, download=True)
        if not post:
            return
        # if not post.file:
        #     async with ClientSession() as session:
        #         async with session.get(post.downloadAddr)
        embed = (
            Embed(
                description=f"[{post.title}]({url})",
            )
            .set_author(
                name=f"{post.channel.name}",
                icon_url=post.channel.avatar.url,
                url=post.channel.url,
            )
            .set_footer(
                text=f"💬 {post.statistics.comments.humanize()} comments | 👀 {post.statistics.views.humanize()} views | ❤️ {post.statistics.likes.humanize()}"
            )
        )

        if post.filesize >= message.guild.filesize_limit:
            await compress(post.file, message.guild.filesize_limit)
        file = File(post.file)
        await message.channel.send(embed=embed, file=file)
        remove(post.file)
        return await message.delete()

    @Cog.listener("on_twitter_repost")
    async def on_twitter_repost(self, message: Message, url: str):
        ctx = await self.bot.get_context(message)
        try:
            tweet_id = TWITTER_REGEX.search(message.content).groups(1)
        except Exception:
            return
        try:
            data = await from_id(tweet_id)
            return await data.to_message(message)
        except Exception as e:
            return await self.bot.errors.handle_exceptions(ctx, e)

    @Cog.listener("on_tiktok_repost")
    async def on_tiktok_repost(self, message: Message, url: str):
        ctx = await self.bot.get_context(message)
        try:
            _data = await fetch_tiktok(url)
            if not _data:
                raise CommandError("**TikTok's API** returned a **corrupted** tiktok")
            data = _data.data
            if data.images:
                raise CommandError("Only **VIDEOS** are supported")
            file = File(
                fp=BytesIO(await get_asset(data.play)), filename="wocktiktok.mp4"
            )
            embed = Embed(
                description=f"{data.title[:1000]}", url=url, color=self.bot.color
            )
            embed.set_footer(
                text=f"👁️ {data.play_count} views | 👍🏼 {data.digg_count} likes | 💬 {data.comment_count} comments"
            )
            embed.set_author(name=data.author.unique_id, icon_url=data.author.avatar)
            return await ctx.repost(embed=embed, file=file, post=_data)
        except Exception as e:
            return await self.bot.errors.handle_exceptions(ctx, e)


async def setup(bot: Client):
    await bot.add_cog(Bot_Events(bot))
