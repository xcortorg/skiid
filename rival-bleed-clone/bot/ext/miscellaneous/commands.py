from discord.ext.commands import (
    Cog,
    command,
    group,
    CommandError,
    EmbedConverter,
    has_permissions,
)
from discord import (
    Client,
    Embed,
    Message,
    File,
    Member,
    User,
    Guild,
    utils,
    AllowedMentions,
)
from io import BytesIO
from typing import Optional, Dict
from asyncio import ensure_future, Task, create_task, Lock, sleep
from lib.patch.context import Context
from discord.ext import commands
from lib.classes.builtins import shorten
from lib.services.YouTube import search as youtube_search
from lib.classes.embed import embed_to_code
from lib.views.embed import EmbedView, EmbedCodeView
from xxhash import xxh3_64_hexdigest as hash_
from aiohttp import ClientSession
from random import choice
from uwu_python import uwu
from collections import defaultdict
from .util.mp3 import make_mp3, song_recognize
from ext.socials.file_types import guess_extension
import re
import orjson

VIDEO_TYPES = (
    "video/mp4",  # MP4 video
    "video/x-msvideo",  # AVI video
    "video/x-matroska",  # MKV video
    "video/ogg",  # OGG video
    "video/webm",  # WebM video
    "video/quicktime",  # MOV video
    "video/x-flv",  # FLV video
    "video/x-ms-wmv",  # WMV video
    "video/x-mpeg",  # MPEG video
    "video/x-ms-asf",  # ASF video
)


async def list_to_string(values: list, limit: Optional[int] = 1950):
    text = ""
    for value in values:
        if len(text) >= limit:
            yield text
            text = ""
            text += f" {value}"
        else:
            text += f" {value}"
    yield text


async def do_transcribe(c: Client, url: str):
    async with ClientSession() as session:
        async with session.get(
            "http://127.0.0.1:8789/", params={"url": url}
        ) as response:
            data = await response.json()
    return data


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot
        self.tasks: Dict[str, Task]
        self.locks: defaultdict[str, Lock] = defaultdict(Lock)

    def split_text(self, text: str, chunk_size: int = 1999):
        # Split the text into chunks of `chunk_size` characters
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    @command(
        name="chatgpt",
        description="Ask a question using the ChatGPT API",
        example=",chatgpt what colors make up purple",
    )
    async def chatgpt(self, ctx: Context, *, question: str):
        obj, message = await self.bot.services.blackbox.prompt(question)
        message = message.replace("<br>", "")
        message = message.replace("$~~~$", "")
        message = message.replace("BLACKBOX AI", "LOSERVM.CO.UK")
        message = message.replace("BLACKBOX", "")
        message = message.replace("BLACKBOX.AI", "")
        embed = Embed(title=f"Answer for {question[:25]}")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        if len(message) > 1999:
            embeds = []
            for chunk in self.split_text(message):
                embed_ = embed.copy()
                embed_.description = chunk
                embeds.append(embed_)
            return await ctx.alternative_paginate(embeds)
        else:
            embed.description = message
            return await ctx.send(embed=embed)

    @command(name="transcribe", description="")
    async def transcribe(self, ctx: Context, message: Optional[Message]):
        voice_message = None
        msg = None
        if message:
            if not (attachments := message.attachments):
                raise CommandError(
                    f"there are no voice messages in [this message]({message.jump_url})"
                )
            for attachment in attachments:
                if attachment.is_voice_message():
                    voice_message = attachment
                    msg = message
        else:
            async for message in ctx.channel.history(limit=100):
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.is_voice_message():
                            voice_message = attachment
                            msg = message
        if not voice_message:
            raise CommandError("No transcribable file was found")
        data = await do_transcribe(self.bot, voice_message.url)
        embed = Embed(description=data["text"]).set_author(
            name=str(msg.author), icon_url=msg.author.display_avatar.url
        )
        return await ctx.send(embed=embed)

    @command(name="uwu", description="Uwuify text", example=",uwu how are you")
    async def uwu(self, ctx: Context, *, text: str):
        text = text.replace("||", "")
        DISCORD_INVITE = r"(?:https?://)?(?:www.:?)?discord(?:(?:app)?.com/invite|.gg)/?[a-zA-Z0-9]+/?"
        DSG = r"(https|http)://(dsc.gg|discord.gg|discord.io|dsc.lol)/?[\S]+/?"
        regex1 = re.compile(DISCORD_INVITE)
        regex2 = re.compile(DSG)
        invites1 = regex1.findall(text)
        invites2 = regex2.findall(text)
        invites = invites1 + invites2
        if len(invites) > 0:
            for i in invites:
                text.strip(i)
        uwuified = uwu(text)
        return await ctx.send(content=f"{uwuified}")

    @command(
        name="names",
        aliases=["namehistory", "nh", "userhistory", "users"],
        description="View username and nickname history of a member or yourself",
        example=",names @kuzay",
    )
    async def names(self, ctx: Context, member: Optional[User] = commands.Author):
        if not (
            history := await self.bot.db.fetch(
                """SELECT username, type, ts FROM names WHERE user_id = $1 ORDER BY ts DESC""",
                member.id,
            )
        ):
            raise CommandError(
                f"{'You have' if member == ctx.author else f'{member.mention} has'} no **name** history"
            )
        embed = Embed(title="Name history").set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        rows = [
            f"`{i}{t.type[0].upper()}` \"{t.username}\" ({utils.format_dt(t.ts, style='R')})"
            for i, t in enumerate(history, start=1)
        ]
        return await ctx.paginate(embed, rows, 10, "name")

    @command(
        name="clearnames",
        aliases=["namesclear", "nc", "cn"],
        description="Reset your name history",
    )
    async def clearnames(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM names WHERE user_id = $1""", ctx.author.id
        )
        return await ctx.success("successfully cleared your **name history**")

    @command(
        name="cleargnames",
        aliases=["cgn", "clgn"],
        description="Reset your guild's name history",
    )
    async def cleargnames(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM guild_names WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("successfully cleard your **guild's name history**")

    @command(
        name="guildnames",
        aliases=["gnames", "gn"],
        description="View guild name changes",
        example=",guildnames 12412412412",
    )
    async def guildnames(self, ctx: Context, guild_id: Optional[int] = None):
        if not guild_id:
            guild_id = ctx.guild.id
        if not (
            history := await self.bot.db.fetch(
                """SELECT name, ts FROM guild_names WHERE user_id = $1 ORDER BY ts DESC""",
                guild_id,
            )
        ):
            raise CommandError("That server has no **name** history")
        embed = Embed(title="Guild Name history").set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        rows = [
            f"`{i}` \"{t.name}\" ({utils.format_dt(t.ts, style='R')})"
            for i, t in enumerate(history, start=1)
        ]
        return await ctx.paginate(embed, rows, 10, "name")

    @commands.command(
        name="createembed",
        aliases=["ce"],
        example=",createembed {embed}{description: whats up}",
        description="Create an embed using an embed code",
    )
    @commands.has_permissions(manage_messages=True)
    async def createembed(self, ctx: Context, *, code: EmbedConverter):
        from lib.classes.exceptions import EmbedError  # type: ignore

        try:
            await self.bot.send_embed(ctx.channel, code, user=ctx.author)
        except EmbedError as e:
            raise e
            return await ctx.fail(e)
        except Exception as e:
            raise e

    @commands.command(
        name="embedcode", description="", example=",embedcode .../channels/..."
    )
    @commands.has_permissions(manage_messages=True)
    async def embedcode(self, ctx: Context, message: Message):
        embed = message.embeds[0]
        code = embed_to_code(embed, message.content)
        view = EmbedCodeView(code)
        return await ctx.success(
            f"**Successfully copied the embed code**\n```{code}```", view=view
        )

    @commands.command(
        name="editembed",
        description="Edit an embed you created",
        example=",editembed .../channels/... {title",
    )
    @commands.has_permissions(manage_messages=True)
    async def editembed(self, ctx: Context, message: Message, *, embed: EmbedConverter):
        if message.author.id != self.bot.user.id:
            raise CommandError("that embed was not authored by me")
        builder = await self.bot.create_embed(embed, member=ctx.author, user=ctx.author)
        await builder.edit(message)
        return await ctx.success(
            f"successfully edited [this message]({message.jump_url})"
        )

    @commands.group(
        name="embed",
        description="Manage and create new embeds easily",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @embed.command(
        name="preview",
        description="Send an existing embed",
        example=",embed preview meow",
    )
    @commands.has_permissions(manage_messages=True)
    async def embed_preview(self, ctx: Context, *, name: str):
        if not (
            code := await self.bot.db.fetchval(
                """SELECT code FROM server_embeds WHERE name = $1 AND guild_id = $2""",
                name,
                ctx.guild.id,
            )
        ):
            raise CommandError(f"No embed found under the name `{name[:25]}`")
        return await self.bot.send_embed(ctx.channel, code, user=ctx.author)

    @embed.command(
        name="create",
        description="Start customization for an embed",
        example=",embed create meow",
    )
    @commands.has_permissions(manage_messages=True)
    async def embed_create(self, ctx: Context, *, name: str):
        if code := await self.bot.db.fetchval(
            """SELECT code FROM server_embeds WHERE name = $1 AND guild_id = $2""",
            name,
            ctx.guild.id,
        ):
            raise CommandError(f"An embed with the name `{name[:25]}` already exists")
        embed = Embed(
            color=self.bot.color,
            title="embed creation",
            description=f"Use the buttons below to customize this embed. You can click the `Code` button to copy this embed or use `embed preview {name}` to show this embed",
        )
        view = EmbedView(ctx, name)
        message = await ctx.send(embed=embed, view=view)
        view.message = message
        return message

    @embed.command(
        name="copy",
        description="Copy an existing embeds code for creating an embed",
        example=",embed copy .../channels/....",
    )
    @commands.has_permissions(manage_messages=True)
    async def embed_copy(self, ctx: Context, *, message: Message):
        embed = message.embeds[0]
        code = embed_to_code(embed, message.content)
        view = EmbedCodeView(code)
        return await ctx.success(
            f"**Successfully copied the embed code**\n```{code}```", view=view
        )

    @embed.command(
        name="delete", description="Delete a stored embed", example=",embed delete meow"
    )
    @commands.has_permissions(manage_messages=True)
    async def embed_delete(self, ctx: Context, *, name: str):
        if not (
            code := await self.bot.db.fetchval(
                """SELECT code FROM server_embeds WHERE name = $1 AND guild_id = $2""",
                name,
                ctx.guild.id,
            )
        ):
            raise CommandError(f"No embed found under the name `{name[:25]}`")
        await self.bot.db.execute(
            """DELETE FROM server_embeds WHERE name = $1 AND guild_id = $2""",
            name,
            ctx.guild.id,
        )
        return await ctx.success(f"successfully deleted the embed `{name[:25]}`")

    @embed.command(name="list", aliases=["show", "ls", "l"], description="")
    @commands.has_permissions(manage_messages=True)
    async def embed_list(self, ctx: Context):
        data = await self.bot.db.fetch(
            """SELECT user_id, name, code FROM server_embeds WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if not data:
            raise CommandError("No embeds have been created")
        embed = Embed(color=self.bot.color, title="Custom Embeds").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )

        def get_user(user_id: int):
            if not (user := self.bot.get_user(user_id)):
                return f"`{user_id}`"
            return f"`{str(user)}`"

        rows = [
            f"`{i}` {row.name} ({get_user(row.user_id)})"
            for i, row in enumerate(data, start=1)
        ]
        return await ctx.paginate(embed, rows, 10, "embed", "embeds")

    @command(name="afk", description="", example=",afk zzz")
    async def afk(self, ctx: Context, *, status: Optional[str] = "AFK"):
        status = status[:100]
        await self.bot.db.execute(
            """
            INSERT INTO afk (
                user_id,
                status
            ) VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO NOTHING;
            """,
            ctx.author.id,
            status,
        )

        await ctx.success(f"You're now AFK with the status: **{status}**")

    @command(name="makemp3", description="Convert a video to an audio file")
    async def makemp3(self, ctx: Context, url: Optional[str] = None):
        if not url:
            if attachments := ctx.message.attachments:
                for attachment in attachments:
                    if attachment.content_type.lower() in VIDEO_TYPES:
                        url = attachment.url
        if not url:
            raise CommandError("No video URL provided...")
        async with ClientSession() as session:
            async with session.request("HEAD", url) as check:
                if int(check.headers.get("Content-Length", 15000)) >= 157_286_400:
                    raise CommandError("The video is too large...")
                if check.content_type not in VIDEO_TYPES:
                    raise CommandError("The video format is not supported...")
            async with session.request("GET", url) as response:
                data = await response.read()
        mp3 = await make_mp3(data)
        await ctx.send(file=File(fp=BytesIO(mp3), filename="output.mp3"))

    @command(
        name="poll", description="Create a short poll", example=",poll 15 Am I gay?"
    )
    async def poll(self, ctx: Context, time: int, *, question: str):
        key = hash_(f"poll-{ctx.guild.id}")
        if task := self.tasks.get(key):
            raise CommandError("There is a poll task currently ongoing...")

        async with self.locks[key]:
            embed = Embed(
                description=f"{str(ctx.author)} started a poll that will end after `{time}` second(s)!\nQuestion: *{question}*"
            )
            embed.set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            )
            embed.set_footer(
                text=f"Guild: {shorten(str(ctx.guild.name), 10)} ∙ Channel: {ctx.channel.name}"
            )
            embed.timestamp = utils.utcnow()
            upvote = "👍"
            downvote = "👎"
            message = await ctx.send(embed=embed)
            await message.add_reaction(upvote)
            await message.add_reaction(downvote)

            async def utask(message: Message):
                results = {"up": 0, "down": 0}
                await sleep(time)
                for reaction in message.reactions:
                    if str(reaction.emoji) == str(upvote):
                        results["up"] += reaction.count - 1
                    elif str(reaction.emoji) == str(downvote):
                        results["down"] += reaction.count - 1
                new_embed = message.embeds[0].copy()
                new_embed.description += f"\n\n**Poll Results:**\n{upvote} `{results['up']}` / {downvote} `{results['down']}`"
                await message.edit(embed=new_embed)
                await message.clear_reactions()

            task = create_task(utask(message))
            self.tasks[key] = task
            await task
            self.tasks.pop(key, None)

    @command(
        name="quickpoll", description="Add up/down arrow to message initiating a poll"
    )
    async def quickpoll(self, ctx: Context, *, msg: str):
        await ctx.message.add_reaction(":arrow_up:")
        await ctx.message.add_reaction(":arrow_down:")

    @command(
        name="seticon",
        aliases=["setavatar"],
        description="Set a new guild icon",
        example=",seticon pngfile",
    )
    @has_permissions(manage_guild=True)
    async def seticon(self, ctx: Context, url: Optional[str] = None):
        if not url:
            if attachments := ctx.message.attachments:
                url = attachments[0].url
        if not url:
            raise CommandError("No File or URL provided...")
        image = await self.bot.get_image(url)
        await ctx.guild.edit(icon=image, reason=f"Updated by {str(ctx.author)}")
        return await ctx.success(f"Set the **guild icon** to [this image]({url})")

    @command(
        name="setsplashbackground",
        aliases=["setsplash"],
        description="Set a new guild splash background",
        example=",setsplash pngfile",
    )
    @has_permissions(manage_guild=True)
    async def setsplashbackground(self, ctx: Context, url: Optional[str] = None):
        if not url:
            if attachments := ctx.message.attachments:
                url = attachments[0].url
        if not url:
            raise CommandError("No File or URL provided...")
        image = await self.bot.get_image(url)
        await ctx.guild.edit(splash=image, reason=f"Updated by {str(ctx.author)}")
        return await ctx.success(f"Set the **guild splash** to [this image]({url})")

    @command(
        name="setbanner",
        description="Set a new guild banner",
        example=",setbanner pngfile",
    )
    @has_permissions(manage_guild=True)
    async def setbanner(self, ctx: Context, url: Optional[str] = None):
        if not url:
            if attachments := ctx.message.attachments:
                url = attachments[0].url
        if not url:
            raise CommandError("No File or URL provided...")
        image = await self.bot.get_image(url)
        await ctx.guild.edit(banner=image, reason=f"Updated by {str(ctx.author)}")
        return await ctx.success(f"Set the **guild banner** to [this image]({url})")

    @command(name="shazam", description="Find a song by providing video or audio")
    async def shazam(self, ctx: Context, *, url: Optional[str] = None):
        if not url:
            if attachments := ctx.message.attachments:
                for attachment in attachments:
                    if (
                        attachment.content_type.lower() in VIDEO_TYPES
                        or attachment.content.lower() == "audio/mpeg"
                    ):
                        url = attachment.url
        if not url:
            raise CommandError("No video/audio URL provided...")
        file_type = guess_extension(url)
        async with ClientSession() as session:
            async with session.request("HEAD", url) as check:
                if int(check.headers.get("Content-Length", 15000)) >= 157_286_400:
                    raise CommandError("The video/audio is too large...")
                if (
                    check.content_type not in VIDEO_TYPES
                    and check.content_type != "audio/mpeg"
                ):
                    raise CommandError("The video/audio format is not supported...")
            async with session.request("GET", url) as response:
                data = await response.read()
        track = await song_recognize(f"{file_type.name}.{file_type.ext}", data)
        if not track:
            raise CommandError("Couldn't **recognize** a song in that file")
        return await ctx.normal(
            f"🎵 Found [**{track.get('title')}**]({track.get('url')}) by **{track.get('subtitle')}**"
        )
