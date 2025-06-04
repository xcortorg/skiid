from io import BytesIO
from logging import getLogger
from typing import Any

import imagehash as ih  # type: ignore
from discord import Asset, Embed, File, Member, Message, User  # type: ignore
from discord.ext import commands  # type: ignore
from discord.ext.commands import (Cog, Context, check,  # type: ignore
                                  hybrid_group)
from PIL import Image  # type: ignore # type: ignore
from rival_tools import lock, thread  # type: ignore
from tools.pinpostmodels import Model  # type: ignore
from tools.pinterest import Pinterest  # type: ignore

logger = getLogger(__name__)
import asyncio  # type: ignore
import datetime  # type: ignore
import io  # type: ignore
import os  # type: ignore
import random  # type: ignore
import string  # type: ignore
from asyncio.subprocess import PIPE  # type: ignore
from contextlib import suppress  # type: ignore
from typing import Optional, Union  # type: ignore

import aiohttp  # type: ignore # type: ignore
import discord  # type: ignore # type: ignore
import humanize  # type: ignore # type: ignore
from aiohttp import ClientSession  # type: ignore # type: ignore
from aiohttp import ClientSession as Session
from aiomisc.backoff import asyncretry  # type: ignore # type: ignore
from cashews import cache  # type: ignore # type: ignore
from cogs.information import get_instagram_user  # type: ignore
from discord.utils import chunk_list  # type: ignore # type: ignore
from rust_chart_generator import create_chart  # type: ignore
from tools.expressions import YOUTUBE_WILDCARD  # type: ignore
from tools.important.services.Eros import PostResponse  # type: ignore
from tools.important.services.TikTok.client import (  # type: ignore
    tiktok_video1, tiktok_video2)
from tools.processing.media import MediaHandler  # type: ignore
from tuuid import tuuid  # type: ignore # type: ignore

cache.setup("mem://")


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


async def donator_check(ctx: Context, member: Optional[Union[Member, User]] = None):
    if member is None:
        member = ctx.author
    if member.id in ctx.bot.owner_ids:
        return True
    if (
        member
        in ctx.bot.get_guild(1233406017061257348).get_role(1248808412863791124).members
    ):
        return True
    data = await ctx.bot.db.fetchrow(
        """SELECT * FROM donators WHERE user_id = $1""", member.id
    )
    if not data:
        if await ctx.bot.glory_cache.ratelimited(
            f"rl:donator_message:{member.id}", 2, 10
        ):
            return
        if member:
            m = f"{member.mention} doesn't have [**Wock's Pass**](https://discord.gg/kuwitty)"
        else:
            m = "[**Wock's Pass**](https://discord.gg/kuwitty) is **required for this command**"
        await ctx.fail(m)
        return False
    return True


def is_donator():
    async def predicate(ctx: Context):
        if ctx.author.id in ctx.bot.owner_ids:
            return True
        if (
            ctx.author
            in ctx.bot.get_guild(1233406017061257348)
            .get_role(1248808412863791124)
            .members
        ):
            return True
        data = await ctx.bot.db.fetchrow(
            """SELECT * FROM donators WHERE user_id = $1""", ctx.author.id
        )
        if not data:
            if (
                await ctx.bot.glory_cache.ratelimited(
                    f"rl:donator_message:{ctx.author.id}", 2, 10
                )
                != 0
            ):
                return
            await ctx.fail(
                "[**Wock's Pass**](https://discord.gg/kuwitty) is **required for this command**"
            )
            return False
        return True

    return check(predicate)


async def to_string(self: Asset) -> tuple:
    async with ClientSession() as session:
        async with session.get(self.url) as resp:
            content_type = resp.headers.get("Content-Type")
            data = await resp.read()
    return content_type, data


Asset.to_string = to_string


def unique_id(length: int = 6):  # type: ignore
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))  # type: ignore # type: ignore


@thread
def image_hash(data: bytes):
    image = BytesIO(data)
    result = str(ih.average_hash(image=Image.open(image), hash_size=8))
    if result == "0000000000000000":
        return unique_id(16)
    else:
        return result


def get_filename(hash_: str, content_type: str):
    if "jpeg" in content_type:
        ext = "jpg"
    elif "png" in content_type:
        ext = "png"
    else:
        ext = "gif"
    return f"{hash_}.{ext}"


class Premium(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pinterest = Pinterest()
        self.media = MediaHandler(self.bot)

    async def handle_upload(self, before: User, after: User):
        if before.display_avatar == after.display_avatar:
            return
        if "embed" in after.display_avatar.url:
            return
        content_type, data = await after.display_avatar.to_string()
        hash_ = await image_hash(await after.display_avatar.read())
        hashes = await self.bot.db.fetch(
            """SELECT avatar_hash FROM avatarhistory WHERE user_id = $1""", before.id
        )
        if hash_ in hashes:
            return
        filename = get_filename(hash_, content_type)
        await self.bot.db.execute(
            """INSERT INTO avatarhistory (user_id, avatar_hash, content_type, avatar, url, ts) VALUES($1, $2, $3, $4, $5, $6) ON CONFLICT(user_id, avatar_hash) DO NOTHING""",
            before.id,
            hash_,
            content_type,
            data,
            f"https://cdn.wock.bot/avatars/{before.id}/{filename}",
            datetime.datetime.now(),
        )
        return True

    async def get_avatars(self, data: Any):
        images = []

        async def get_bytes(url: str) -> bytes:
            async with ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    byte = await response.read()
            images.append(byte)

        await asyncio.gather(*[get_bytes(row.url) for row in data])
        return images

    @Cog.listener("on_user_update")
    async def on_avatar_change(self, before: User, after: User):
        if (
            await self.bot.db.fetchrow(
                """SELECT * FROM donators WHERE user_id = $1""", before.id
            )
            or after
            in self.bot.get_guild(1233406017061257348)
            .get_role(1248808412863791124)
            .members
            or after.id in self.bot.owner_ids
        ):
            return await self.handle_upload(before, after)

    @thread
    def make_chart(self, images):
        return create_chart(images)

    @lock("avh:{ctx.author.id}")
    async def make_avatarhistory(self, ctx: Context, user: User):
        message = await ctx.send(
            embed=Embed(
                description=f"<a:wockloading:1251040305529094144> **Generating** {user.mention}'s **avatar history..**",
                color=self.bot.color,
            )
        )
        avatars = await self.bot.db.fetch(
            """SELECT url FROM avatarhistory WHERE user_id = $1 ORDER BY ts DESC""",
            user.id,
        )
        avatars = avatars[:24]
        if not avatars:
            embed = message.embeds[0]
            embed = await ctx.fail(
                f"There is **no avatar history** for {user.mention}", return_embed=True
            )
            return await message.edit(embed=embed)
        images = await self.get_avatars(avatars)
        chart = BytesIO(bytes(await self.make_chart(images)))
        chart.seek(0)
        file = File(fp=chart, filename="chart.png")
        if avatars == 0:
            embed = message.embeds
            embed = await ctx.fail(
                "User does **not** have **past avatars**", return_embed=True
            )
            return await message.edit(embed=embed)
        embed = Embed(
            description=f"**Past avatars available [here](https://wock.bot/avatars/{user.id})**",
            color=self.bot.color,
        )
        embed.set_image(url="attachment://chart.png")
        return await message.edit(attachments=[file], embed=embed)

    @hybrid_group(
        name="avatarhistory",
        aliases=["ah", "avh"],
        invoke_without_command=True,
        brief="View your saved profile pictures history through wock",
        example="avatarhistoryn",
    )
    @is_donator()
    @lock("avh-{ctx.guild.id}")
    async def avatarh(
        self, ctx: Context, *, member: Optional[Union[User, Member]] = None
    ):
        if await donator_check(ctx, member) is False:
            return
        if member is None:
            member = ctx.author
        return await self.make_avatarhistory(ctx, member)

    @avatarh.command(
        name="reset",
        aliases=["clear"],
        brief="Reset your saved profile pictures through wock",
        example=",avatarhistory reset",
    )
    async def clear(self, ctx: Context):
        await self.bot.db.execute(
            "DELETE FROM avatarhistory WHERE user_id = $1", ctx.author.id
        )
        return await ctx.success("**Cleared** your **avatar history**")

    @commands.command(
        name="youtube",
        aliases=["yt"],
        brief="Repost a youtube short video",
        example=",youtube {link}",
    )
    @is_donator()
    async def youtube(self, ctx: Context, *, url: str):
        try:
            data = await self.bot.rival.get_youtube_post(url)
        except Exception:
            return await ctx.fail("only urls are accepted")
        if data:
            async with ClientSession() as session:
                async with session.get(data.url) as response:
                    file = File(
                        fp=BytesIO(await response.read()), filename=f"{data.id}.mp4"
                    )

            return await ctx.send(
                file=file,
                embed=Embed(
                    title=data.title,
                    description=data.description,
                    url=data.original_url,
                    color=self.bot.color,
                ),
            )
        else:
            return await ctx.fail(f"could not find a video with the url {url}")

    async def youtube_embed(self, message: Message, url: str) -> Message:
        data = await self.bot.rival.youtube(url)
        embed = (
            Embed(
                description=f"<:wocks_youtube_shorts:1214318621271007314> [{data.title}]({url})",
                color=self.bot.color,
            )
            .set_author(name=f"Wock request - {data.author.name}")
            .set_footer(
                text=f"💬 {format_int(data.comment_count)} comments | ❤️ {format_int(data.view_count)} views"
            )
        )
        async with ClientSession() as session:
            async with session.get(data.url) as response:
                data = await response.read()
        file = File(fp=BytesIO(data), filename="wockyoutube.mp4")
        await message.delete()
        await message.channel.send(embed=embed, file=file)

    @commands.Cog.listener("on_message")
    async def youtube_repost(self, message: Message):
        if message.mention_everyone:
            await self.bot.modlogs.do_log(message)
        if message.author.id == 123:
            await message.delete()
        if message.content.lower().startswith(self.bot.user.name.lower()):
            try:
                if match := YOUTUBE_WILDCARD.match(message.content.split(" ")[1]):
                    if await donator_check(
                        await self.bot.get_context(message), message.author
                    ):
                        return await self.youtube_embed(message, match.string)
            except Exception:
                pass

    @asyncretry(max_tries=3, pause=0.1)
    async def get_asset(self, url: str) -> discord.File:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise TypeError(f"{url} wasn't a valid asset")
                data = await response.read()
        return data

    @cache(ttl=300, key="compress:{data}")
    async def compress(self, data: bytes, size: int) -> bytes:
        size = f"{int(size/1000000)}m"
        async with aiohttp.ClientSession() as session:
            async with session.request(
                "POST",
                f"https://api.rival.rocks/video/compress?identifier={tuuid()}&size={size}",
                data={"file": data},
                headers={"api-key": self.bot.config["rival_api"]},
            ) as response:
                try:
                    url = (await response.json())["url"]
                except Exception:
                    return await response.json()
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.read()
        return data

    #

    async def write_file(self, filename: str, data: bytes):
        def write_file_(filename: str, data: bytes):
            with open(filename, "wb") as file:
                file.write(data)
            return filename

        return await asyncio.to_thread(write_file_, filename, data)

    async def compress_and_send(self, ctx: Context, data: PostResponse, filename: str, embed: Embed, raw: bytes) -> discord.Message:  # type: ignore
        from discord.http import handle_message_parameters  # type: ignore

        logger.info("compressing tiktok....")
        with suppress(FileNotFoundError):
            os.remove("wocktiktok.mp4")
            os.remove("wocktiktoka.mp4")
        filename = filename.split(".")[0]
        await self.write_file(f"{filename}a.mp4", raw)
        process = await asyncio.create_subprocess_shell(
            f"ffmpeg -i {filename}a.mp4 -fs 6M -preset ultrafast {filename}.mp4 -y",
            stderr=PIPE,
            stdout=PIPE,
        )
        await process.communicate()
        try:
            await process.wait()
        except Exception:
            pass
        file = discord.File(f"{filename}.mp4")
        if len(file.fp.read()) > ctx.guild.filesize_limit:
            await ctx.fail("that **tiktok** is **to large**", return_embed=True)
        else:
            self.bot.last_tiktok = file.fp.read()
            logger.info(len(file.fp.read()))
            kwargs = {"headers": {"Authorization": f"Bot {self.bot.config['token']}"}}
            for i in range(5):  # type: ignore
                try:
                    file = discord.File(f"{filename}.mp4")
                    with handle_message_parameters(file=file, embed=embed) as params:
                        for tries in range(5):
                            if params.files:
                                for f in params.files:
                                    f.reset(seek=tries)
                            logger.info(f"{params.files[0]}")
                            form_data = aiohttp.FormData(quote_fields=False)
                            if params.multipart:
                                for params in params.multipart:
                                    form_data.add_field(**params)
                                kwargs["data"] = form_data
                            async with aiohttp.ClientSession() as session:
                                async with session.request(
                                    "POST",
                                    f"https://discord.com/api/v10/channels/{ctx.channel.id}/messages",
                                    **kwargs,
                                ) as response:
                                    await response.json()  # pointless but do it here anyways to end off the async enter
                except AttributeError:
                    break
            return
            await ctx.send(file=file)  # type: ignore
            self.bot.last_tiktok = file.fp.read()

    async def repost_tiktok(
        self, message: Message, url: str, debug: Optional[bool] = False
    ):
        ctx = await self.bot.get_context(message)
        if not await donator_check(ctx):
            return
        logger.info(f"fetching tiktok: {url}")
        try:
            _data = await PostResponse.from_response(url, self.bot.eros)
            if not _data:
                return await message.channel.send(
                    embed=await ctx.fail(
                        "**TikTok's API** returned a **corrupted** tiktok",
                        return_embed=True,
                    )
                )
            filedata = await self.get_asset(_data.data.play)
        except Exception as e:
            await message.channel.send(
                embed=await ctx.fail(
                    "**TikTok's API** returned a **corrupted** tiktok",
                    return_embed=True,
                )
            )
            raise e
        data = _data.data
        if data.images:
            return await ctx.fail("Only **VIDEOS** are supported")
        video = discord.File(fp=BytesIO(filedata), filename="wocktiktok.mp4")
        self.bot.last_tiktok = filedata
        self.last_tiktok_class = _data
        ctx = await self.bot.get_context(message)
        embed = Embed(
            description=f"<:socials_tiktok:1253113073917759550> {data.title[:1000]}",
            color=self.bot.color,
        )
        embed.set_footer(
            text=f"👁️ {data.play_count} views | 👍🏼 {data.digg_count} likes | 💬 {data.comment_count} comments"
        )
        embed.set_author(name=data.author.unique_id, icon_url=data.author.avatar)
        if debug:
            return video, data
        return await self.compress_and_send(ctx, _data, video.filename, embed, filedata)

    def get_regex(self, content: str):
        if "@" not in content:
            try:
                return tiktok_video2.search(content).string
            except Exception:  # type: ignore
                return None
        else:
            try:
                return (tiktok_video1.find_all(content))[0]
            except Exception:  # type: ignore
                return None

    @commands.Cog.listener("on_message")
    async def tiktok_repost(self, message: Message):
        if message.content.lower().startswith(self.bot.user.name.lower()):
            content = message.content.split(self.bot.user.name.lower(), 1)[-1].split(
                " "
            )[-1]
            if "tiktok" in content.lower():
                return await self.repost_tiktok(message, content.lstrip().rstrip())

    @commands.command(
        name="tiktok",
        aliases=["tt"],
        brief="View a tiktok user account",
        example=",tiktok icy",
    )
    @is_donator()
    async def tiktok(self, ctx: Context, *, username: str):
        if "https://" in username:
            data = await self.repost_tiktok(ctx.message, username)
            logger.info(data)
            return
        if "https://" not in username.lower():
            try:
                embed = discord.Embed()
                user = await self.bot.rival.tiktok_user(username)
                embed.title = f"{user.display_name} (@{username})"
                embed.url = f"https://tiktok.com/@{username}"
                embed.description = user.bio
                embed.set_thumbnail(url=user.avatar)
                embed.add_field(name="likes", value=format_int(user.likes), inline=True)
                embed.add_field(
                    name="followers", value=format_int(user.followers), inline=True
                )
                embed.add_field(
                    name="following", value=format_int(user.following), inline=True
                )
                embed.set_author(
                    name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
                )
                embed.set_footer(text="TikTok", icon_url=user.tiktok_logo)
                embed.color = discord.Color.from_str(user.avatar_color)
                return await ctx.send(embed=embed)
            except Exception as e:
                if ctx.author.name == "aiohttp":
                    raise e
                return await ctx.fail(
                    f"tiktok user [**@{username}**](https://tiktok.com/@{username}) could not be found"
                )

    @commands.command(
        name="pinterest",
        aliases=["pin"],
        brief="get a user, post, or reverse search an image on pinterest",
        example=",pinterest {link}",
    )
    @is_donator()
    async def pinterest(self, ctx: Context, *, username_or_url: str):
        try:
            if username_or_url.startswith(
                "https://www.pinterest.com/"
            ) or username_or_url.startswith("https://pin.it/"):
                if post := await self.pinterest.get_post_or_pin(username_or_url):
                    data = Model(**post)
                    if data.resource_response.data.videos is not None:
                        content = None
                        for key in data.resource_response.data.videos[
                            "video_list"
                        ].keys():
                            url = data.resource_response.data.videos["video_list"][key][
                                "url"
                            ]
                            async with Session() as session:
                                async with session.get(url) as response:
                                    file = discord.File(
                                        fp=io.BytesIO(await response.read()),
                                        filename=f"{tuuid()}.mp4",
                                    )
                                    break
                    else:
                        content = None
                        file = None
                    if file is not None:
                        return await ctx.send(
                            embed=discord.Embed(
                                title=data.resource_response.data.pinner.first_name,
                                url=username_or_url,
                                description=data.resource_response.data.description,
                                color=self.bot.color,
                            ),
                            content=content,
                            file=file,
                        )
                    else:
                        return await ctx.send(
                            embed=discord.Embed(
                                title=data.resource_response.data.pinner.first_name,
                                url=username_or_url,
                                description=data.resource_response.data.description,
                                color=self.bot.color,
                            ).set_image(
                                url=data.resource_response.data.images.field_736x.url
                            ),
                            content=content,
                            file=file,
                        )
                        # data.resource_response.data.images.field_600x.url
            else:
                if data := await self.pinterest.get_user(username_or_url):
                    return await ctx.send(
                        embed=discord.Embed(
                            title=f"{data.resource_response.data.first_name} (@{username_or_url})",
                            description=data.resource_response.data.about,
                            url=f"https://pinterest.com/{username_or_url}",
                            color=self.bot.color,
                        )
                        .set_thumbnail(url=data.resource_response.data.image_medium_url)
                        .add_field(
                            name="Following",
                            value=data.resource_response.data.explicit_user_following_count,
                            inline=True,
                        )
                        .add_field(
                            name="Followers",
                            value=data.resource_response.data.follower_count,
                            inline=True,
                        )
                    )
        except Exception as e:
            if ctx.author.name == "aiohttp":
                raise e
            return await ctx.fail("only URLS and usernames are accepted")

    @commands.command(
        name="google",
        brief="get google search results",
        example=",google what is space?",
    )
    @is_donator()
    async def google(self, ctx: Context, *, query: str):
        safe = ctx.channel.is_nsfw()
        message = await ctx.send(
            embed=discord.Embed(
                description=f"<a:wockloading:1251040305529094144> {ctx.author.mention}: **Searching the web..**",
                color=self.bot.color,
            )
        )
        try:
            results = await self.bot.rival.google_search(query, safe)
        except Exception as e:
            if ctx.author.id == 352190010998390796:
                raise e
            embed = await ctx.fail(
                f"**{query[:20]}** has **no results**", return_embed=True
            )
            return await message.edit(embed=embed)
        res = chunk_list(results.results, 3)
        pages = len(res)
        embeds = [
            discord.Embed(
                title="Search Results",
                description="\n\n".join(
                    f"[{result.title[:255]}](https://{result.domain})\n{result.description}"
                    for result in page
                ),
                color=self.bot.color,
            )
            .set_footer(
                text=f"Page {i}/{pages} of Google Search {'(S00000000000afe Mode)' if safe else ''}",
                icon_url="https://cdn4.iconfinder.com/data/icons/logos-brands-7/512/google_logo-google_icongoogle-512.png",
            )
            .set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
            for i, page in enumerate(res, start=1)
        ]
        asyncio.ensure_future(ctx.paginate(embeds, message))
        return

    @commands.command(
        name="image", brief="get results from google images", example=",image car"
    )
    @is_donator()
    async def image(self, ctx: Context, *, query: str):
        if ctx.channel.is_nsfw():
            safe = False

        else:
            safe = True

        try:
            results = await self.bot.rival.google_images(query, safe)

        except Exception as e:
            if ctx.author.name == "aiohttp":
                raise e
            return await ctx.fail(f"no results for **{query}**")

        embeds = [
            discord.Embed(
                title=f"results for {query}",
                description=f"[{result.title}]({result.source})",
                color=self.bot.color,
            )
            .set_image(url=result.url)
            .set_footer(text=f"Page {i}/{len(results.results)} of Google Images")
            for i, result in enumerate(results.results, start=1)
        ]

        return await ctx.paginate(embeds)

    @commands.command(
        name="instagram",
        description="lookup an instagram account",
        aliases=["ig", "insta"],
        example=",instagram icy",
    )
    @is_donator()
    async def instagram(self, ctx: Context, *, username: str):
        try:
            user = await self.bot.rival.instagram_user(username)
        except Exception:
            try:
                user = await get_instagram_user(username)
                embed = (
                    discord.Embed(
                        title=f"{user.fullname} (@{user.username})",
                        url=user.url,
                        description=user.bio,
                        color=self.bot.color,
                    )
                    .add_field(
                        name="Followers", value=format_int(user.followers), inline=True
                    )
                    .add_field(
                        name="Following", value=format_int(user.following), inline=True
                    )
                    .add_field(name="Posts", value=format_int(user.posts), inline=True)
                    .set_thumbnail(url=user.profile_pic)
                )
                return await ctx.send(embed=embed)
            except Exception:
                return await ctx.fail(
                    f"[{username}](https://instagram.com/{username}) is not a valid instagram user"
                )

        badges = ""

        if user.is_private is True:
            badges += "🔒"

        if user.is_verified is True:
            badges += "✔️"

        embed = discord.Embed(
            title=f"{user.full_name} (@{user.username}) {badges}",
            url=f"https://instagram.com/{username}",
            color=self.bot.color,
            description=user.biography,
        )

        embed.add_field(
            name="Followers", value=user.edge_followed_by.count, inline=True
        )

        embed.add_field(name="Following", value=user.edge_follow.count, inline=True)

        embed.set_thumbnail(url=user.profile_pic_url)

        return await ctx.send(embed=embed)

    @commands.command(
        name="transcribe",
        brief="return the text from a voice message",
        example=",transcribe [audio_reply]",
    )
    @is_donator()
    async def transcribe(self, ctx: Context, message: Optional[Message] = None):
        if not message:
            if not ctx.message.reference:
                messages = [
                    message
                    async for message in ctx.channel.history(limit=50)
                    if len(message.attachments) > 0
                    and message.attachments[0].is_voice_message()
                ]

                if len(messages) == 0:
                    return await ctx.fail(
                        "please reply to a message or provide a message to transcribe"
                    )

                else:
                    message = messages[0]

                    msg = await ctx.send(
                        embed=discord.Embed(
                            color=self.bot.color,
                            description=f"<a:wockloading:1251040305529094144> {ctx.author.mention}: **transcribing this message...**",
                        )
                    )

                    text = await self.bot.rival.transcribe(message)

            else:
                message = await self.bot.fetch_message(
                    ctx.channel, ctx.message.reference.message_id
                )

                msg = await ctx.send(
                    embed=discord.Embed(
                        color=self.bot.color,
                        description=f"<a:wockloading:1251040305529094144> {ctx.author.mention}: **transcribing this message...**",
                    )
                )

                text = await self.bot.rival.transcribe(message)

        else:
            text = await self.bot.rival.transcribe(message)

        if text.text is None:
            return await ctx.fail(
                f"**Failed to transcribe** [**this message**]({message.url})"
            )

        return await msg.edit(
            embed=discord.Embed(description=text.text, color=self.bot.color)
            .set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url,
            )
            .set_footer(text="Powered by Rival API")
        )


async def setup(bot):
    await bot.add_cog(Premium(bot))
