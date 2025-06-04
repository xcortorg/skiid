import io
import websockets
import websockets.exceptions
import traceback
import asyncio
import discord
import datetime
import aiohttp
import json
import ssl
from discord.ext import commands, tasks
from lib.patch.context import Context
from discord.ext.commands import GuildID, CommandError, Cog
from asyncio.subprocess import PIPE
from loguru import logger, logger as logging
from typing import Optional, Union, Dict, Any, List
from var.config import CONFIG
from discord import User, Member
from lib.classes.checks import is_staff
from lib.classes.builtins import get_error
from pydantic import BaseModel
from datetime import datetime as dt
from io import BytesIO


class MessageAuthor(BaseModel):
    username: str
    public_flags: int
    primary_guild: Optional[Any] = None
    id: str
    global_name: Optional[str] = None
    discriminator: str
    clan: Optional[Any] = None
    bot: Optional[bool] = False
    avatar_decoration_data: Optional[Any] = None
    avatar: Optional[str] = None


class MessageMember(BaseModel):
    roles: Optional[List[str]] = None
    premium_since: Optional[dt] = None
    pending: bool
    nick: Optional[str] = None
    mute: bool
    joined_at: dt
    flags: int
    deaf: bool
    communication_disabled_until: Optional[dt] = None
    banner: Optional[str] = None
    avatar: Optional[str] = None


class MessageAttachment(BaseModel):
    content_scan_version: Optional[int] = 1
    content_type: str
    filename: str
    height: Optional[int] = None
    width: Optional[int] = None
    id: str
    placeholder: Optional[str] = None
    placeholder_version: Optional[int] = 1
    proxy_url: str
    size: int
    url: str

    async def to_file(self: "MessageAttachment") -> discord.File:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                data = await response.read()
        return discord.File(fp=BytesIO(data), filename=self.filename)


class EmbedField(BaseModel):
    name: str
    value: str
    inline: bool


class EmbedFooter(BaseModel):
    text: Optional[str] = None
    icon_url: Optional[str] = None


class EmbedAuthor(BaseModel):
    name: Optional[str] = None
    icon_url: Optional[str] = None
    url: Optional[str] = None


class EmbedThumbnail(BaseModel):
    flags: Optional[int] = 0
    height: Optional[int] = None
    width: Optional[int] = None
    proxy_url: str
    url: str


class EmbedImage(BaseModel):
    flags: Optional[int] = 0
    height: Optional[int] = None
    width: Optional[int] = None
    proxy_url: str
    url: str


class MessageEmbed(BaseModel):
    color: Optional[int] = 0
    description: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    footer: Optional[EmbedFooter] = None
    author: Optional[EmbedAuthor] = None
    image: Optional[EmbedImage] = None
    thumbnail: Optional[EmbedThumbnail] = None
    fields: Optional[List[EmbedField]] = None


class Message(BaseModel):
    type: int
    tts: bool
    timestamp: dt
    pinned: bool
    mentions: list
    mention_roles: list
    mention_everyone: bool
    member: Optional[MessageMember] = None
    id: str
    flags: int
    embeds: Optional[List[MessageEmbed]] = None
    edited_timestamp: Optional[dt] = None
    content: Optional[str] = None
    components: list
    channel_type: int
    channel_id: str
    author: MessageAuthor
    attachments: Optional[List[MessageAttachment]] = None
    guild_id: Optional[str]

    async def mirror(
        self: "Message", webhook_url: str, session: aiohttp.ClientSession
    ) -> Any:
        import discord

        kwargs = {}

        if self.embeds:
            kwargs["embeds"] = []
            for embed in self.embeds:
                kwargs["embeds"].append(discord.Embed.from_dict(embed.dict()))

        if self.attachments:
            kwargs["files"] = []
            for attachment in self.attachments:
                kwargs["files"].append(await attachment.to_file())

        if self.content:
            kwargs["content"] = self.content

        kwargs["username"] = f"{self.author.username} ({self.author.id})"

        if self.author.avatar:
            kwargs["avatar_url"] = (
                f"https://cdn.discordapp.com/avatars/{self.author.id}/{self.author.avatar}"
            )

        webhook = discord.Webhook.from_url(webhook_url, session=session)
        response = await webhook.send(**kwargs)
        return response


TOKEN = "MTMyMTk1OTM2NTQ1NjE3MTA3MA.Gi07wE.FM05rrPj1vHwSGUETRs5FEuopg_wAOQG4-fikg"


async def xray(guild_id: int, channel_id: int, webhook_url: str):
    session = aiohttp.ClientSession()

    async def heartbeat(ws, interval, last_sequence):
        while True:
            await asyncio.sleep(interval)
            payload = {"op": 1, "d": last_sequence}
            await ws.send(json.dumps(payload))
            logging.info("Heartbeat packet sent.")

    async def identify(ws):
        identify_payload = {
            "op": 2,
            "d": {
                "token": TOKEN,
                "properties": {"$os": "windows", "$browser": "chrome", "$device": "pc"},
            },
        }
        await ws.send(json.dumps(identify_payload))
        logging.info("Identification sent.")

    async def on_message(ws):
        last_sequence = None
        while True:
            event = json.loads(await ws.recv())
            logging.debug(f"Event received: {event}")
            op_code = event.get("op", None)

            if op_code == 10:
                interval = event["d"]["heartbeat_interval"] / 1000
                asyncio.create_task(heartbeat(ws, interval, last_sequence))

            elif op_code == 0:
                last_sequence = event.get("s", None)
                event_type = event.get("t")
                if event_type == "MESSAGE_CREATE":
                    channel__id = event["d"]["channel_id"]
                    message = event["d"]
                    try:
                        msg = Message(**message)
                        if int(channel_id) == int(channel__id):
                            await msg.mirror(webhook_url, session)
                            logging.debug(f"Message received from Discord: {message}")
                    except Exception as e:
                        logging.error(f"Error processing message: {get_error(e)}")
                        pass

            elif op_code == 9:
                logging.debug("Invalid session. Starting a new session...")
                await identify(ws)

    async def main():
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        while True:
            try:
                async with websockets.connect(
                    "wss://gateway.discord.gg/?v=6&encoding=json", ssl=ssl_context
                ) as ws:
                    await identify(ws)
                    await on_message(ws)
            except websockets.exceptions.ConnectionClosed as e:
                logging.error(
                    f"WebSocket connection closed unexpectedly: {e}. Reconnecting..."
                )
                await asyncio.sleep(5)
                continue

    await main()


async def fetch_channel(channel_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.request(
            "PATCH",
            f"https://discord.com/api/v10/channels/{channel_id}",
            headers={"Authorization": TOKEN},
        ) as response:
            data = await response.json()
    return data


async def get_commits(author: str, repository: str, token: str):
    url = f"https://api.github.com/repos/{author}/{repository}/commits"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            headers={
                "accept": "application/vnd.github.v3.raw",
                "authorization": "token {}".format(token),
            },
        ) as response:
            data = await response.json()
    return data


async def check_commits(commits: list):
    for commit in commits:
        if commit["commit"]["author"]["name"] != "root":
            date = datetime.datetime.strptime(
                commit["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ"
            ).timestamp()
            if int(datetime.datetime.utcnow().timestamp() - date) < 61:
                return (True, commit)
    return (False, None)


def format_commit(d: tuple):
    d = d[0].decode("UTF-8")
    if "\n" in d:
        for _ in d.split("\n"):
            if "cogs" not in _:
                if "tools" in _:
                    return True
        return False
    else:
        try:
            for _ in d.splitlines():
                if "cogs" not in _:
                    if "tools" not in _:
                        return True
            return False
        except Exception:
            return False


class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tasks: Dict[str, asyncio.Task] = {}

    async def cog_load(self):
        if CONFIG.get("auto_pull", False) is True:
            self.git_pull.start()

    async def cog_unload(self):
        for task in self.tasks:
            task.cancel()

    @tasks.loop(minutes=1)
    async def git_pull(self):
        token = CONFIG["github"]["token"]
        author = CONFIG["github"]["author"]
        repository = CONFIG["github"]["repo"]
        try:
            commits = await get_commits(author, repository, token)
            check, commit = await check_commits(commits)
            if check is True:
                if commit != self.last_commit:
                    proc = await asyncio.create_subprocess_shell(
                        "git pull", stderr=PIPE, stdout=PIPE
                    )
                    data = await proc.communicate()
                    self.last_commit = commit
                    if b"Already up to date.\n" in data:
                        return
                    else:
                        if format_commit(data) is True:
                            logger.info("[ Commit Detected ] Restarting")
                            await asyncio.create_subprocess_shell("pm2 restart wock")
                        else:
                            logger.info("[ Commit Detected ] Auto Reloading..")
        except Exception as e:
            exc = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.info(f"Issue in Git Pull {exc}")

    @commands.group(
        name="system",
        aliases=["sys"],
        description="control payment and authorizations with the bot",
        invoke_without_command=True,
    )
    @is_staff()
    async def system(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @system.command(
        name="whitelist",
        aliases=["authorize", "auth", "wl"],
        description="whitelist or unwhitelist a guild",
        example=",system whitelist 2737373",
    )
    @is_staff()
    async def system_whitelist(self, ctx: Context, guild_id: GuildID):
        if not await self.bot.db.fetchrow(
            """SELECT * FROM authorizations WHERE guild_id = $1""", guild_id
        ):
            await self.bot.db.execute(
                """DELETE FROM authorizations WHERE guild_id = $1""", guild_id
            )
            return await ctx.success(f"removed the authorization from {guild_id}")
        else:
            await self.bot.db.execute(
                """INSERT INTO authorizations (guild_id, creator) VALUES($1, $2)""",
                guild_id,
                ctx.author.id,
            )
            return await ctx.success(f"successfully authorized {guild_id}")

    async def get_ids_from_message(self, message: Message):
        ids = []
        ctx = await self.bot.get_context(message)
        for ctn in ctx.message.content.split():
            try:
                _ = await GuildID().convert(ctx, ctn)
                ids.append(_)
            except Exception:
                pass
        return ids

    @system.command(
        name="transfer",
        aliases=["tr"],
        description="transfer a whitelist",
        example=",system transfer 273737 373636366",
    )
    @is_staff()
    async def system_transfer(
        self,
        ctx: Context,
        current: Optional[GuildID] = None,
        new: Optional[GuildID] = None,
    ):
        if not current and not new:
            if not (reference := ctx.message.reference):
                return await ctx.send_help()
            else:
                message = await ctx.channel.fetch_message(reference.message_id)
                ids = await self.get_ids_from_message(message)
                for _ in ids:
                    if await self.bot.db.fetchrow(
                        """SELECT * From authorizations WHERE guild_id = $1""", _
                    ):
                        current = _
                    else:
                        new = _
                if not new or not current:
                    return await ctx.send_help()
        if not (
            transfers := await self.bot.db.fetchval(
                """SELECT transfers FROM authorizations WHERE guild_id = $1""", current
            )
        ):
            raise CommandError("That guild is not **whitelisted**")
        if transfers == 1:
            raise CommandError("that whitelist has already been transferred")
        try:
            await self.bot.db.execute(
                """UPDATE authorizations SET guild_id = $1, transfers = 1 WHERE guild_id = $2""",
                new,
                current,
            )
            return await ctx.success("successfully transferred that whitelist")
        except Exception:
            return await ctx.fail("that whitelist has already been transferred")

    @system.command(
        name="donator",
        description="remove or add donator to a user",
        example=",system donator @jon",
    )
    @is_staff()
    async def system_donator(self, ctx: Context, *, user: Union[Member, User]):
        if await self.bot.db.fetchrow(
            """SELECT * FROM donators WHERE user_id = $1""", user.id
        ):
            await self.bot.db.execute(
                """DELETE FROM donators WHERE user_id = $1""", user.id
            )
            return await ctx.success(
                f"successfully removed donator from **{str(user)}**"
            )
        else:
            await self.bot.db.execute(
                """INSERT INTO donators (user_id, creator) VALUES($1, $2)""",
                user.id,
                ctx.author.id,
            )
            return await ctx.success(f"successfully gave donator to **{str(user)}**")

    @system.command(
        name="blacklist",
        description="blacklist or unblacklist a guild or user",
        example=",system blacklist @jon",
        parameters={
            "reason": {"converter": str, "default": "No reason provided"},
        },
    )
    @is_staff()
    async def system_blacklist(
        self, ctx: Context, snowflake: Union[Member, User, GuildID]
    ):
        reason = ctx.parameters.get("reason")
        if isinstance(snowflake, (User, Member)):
            if not await self.bot.db.fetchrow(
                """SELECT * FROM blacklists WHERE object_id = $1 AND object_type = $2""",
                snowflake.id,
                "user",
            ):
                await self.bot.db.execute(
                    """INSERT INTO blacklists (object_id, object_type, creator, reason) VALUES($1, $2, $3, $4)""",
                    snowflake.id,
                    "user",
                    ctx.author.id,
                    reason,
                )
                message = f"successfully blacklisted the **user** {str(snowflake)}"
            else:
                await self.bot.db.execute(
                    """DELETE FROM blacklists WHERE object_id = $1 AND object_type = $2""",
                    snowflake.id,
                    "user",
                )
                message = f"successfully unblacklisted the **user** {str(snowflake)}"
        else:
            if not await self.bot.db.fetchrow(
                """SELECT * FROM blacklists WHERE object_id = $1 AND object_type = $2""",
                snowflake,
                "guild",
            ):
                await self.bot.db.execute(
                    """INSERT INTO blacklists (object_id, object_type, creator, reason) VALUES($1, $2, $3, $4)""",
                    snowflake,
                    "guild",
                    ctx.author.id,
                    reason,
                )
                message = f"successfully blacklisted the **guild** {str(snowflake)}"
            else:
                await self.bot.db.execute(
                    """DELETE FROM blacklists WHERE object_id = $1 AND object_type = $2""",
                    snowflake,
                    "guild",
                )
                message = f"successfully unblacklisted the **guild** {str(snowflake)}"
        return await ctx.success(message)

    @commands.command(name="traceback", aliases=["tb", "trace"])
    @commands.is_owner()
    async def traceback(self, ctx: Context, code: Optional[str] = None):
        if reference := await self.bot.get_reference(ctx.message):
            if reference.author.id == self.bot.user.id:
                if reference.content.startswith("`"):
                    code = code.split("`")[1]
        if not code:
            raise CommandError("no code was provided")
        data = await self.bot.db.fetchrow(
            """SELECT * FROM traceback WHERE error_code = $1""", code
        )
        if not data:
            return await ctx.fail(f"no error under code **{code}**")
        self.bot.get_guild(data.guild_id)  # type: ignore
        self.bot.get_channel(data.channel_id)  # type: ignore
        self.bot.get_user(data.user_id)  # type: ignore
        if len(data.error_message) > 2000:
            return await ctx.send(
                file=discord.File(fp=io.StringIO(data.error_message), filename="tb.txt")
            )
        embed = discord.Embed(
            title=f"Error Code {code}", description=f"```{data.error_message}```"
        )
        embed.add_field(name="Context", value=f"`{data.content}`", inline=False)
        return await ctx.send(embed=embed)

    @commands.command(
        name="xray",
        description="forward a guild channel's messages into this channel",
        example=",xray 123 421",
    )
    @commands.is_owner()
    async def xray(self, ctx: Context, action: str, guild_id: int, channel_id: int):
        webhooks = await ctx.channel.webhooks()
        if action == "start":
            if task := self.tasks.get(f"xray-{ctx.channel.id}"):
                raise CommandError("there is already a xray task running here")
            self.tasks[f"xray-{ctx.channel.id}"] = asyncio.create_task(
                xray(guild_id, channel_id, webhooks[0].url)
            )
            return await ctx.success("xray started")
        elif action == "stop":
            try:
                self.tasks[f"xray-{ctx.channel.id}"].cancel()
            except Exception:
                raise CommandError("there is no xray task going on in here...")
            del self.tasks[f"xray-{ctx.channel.id}"]
            return await ctx.success("xray stopped")
        else:
            return await ctx.fail("invalid action")
