import asyncio
import datetime
import json
import os
import random
import string
import sys
import traceback
import typing
from io import BytesIO
from typing import Any, List, Optional

import asyncpg
import discord
import jishaku
from asyncpg import create_pool
from cogs.giveaway import GiveawayView
from cogs.music import Music
from cogs.voicemaster import vmbuttons
from discord import AllowedMentions
from discord import AutoShardedClient as AB
from discord import CustomActivity, Embed, Intents, Interaction, Message
from discord.ext import commands
from discord.ext.commands import AutoShardedBot as AB
from discord.ext.commands import (BucketType, CheckFailure, CommandError,
                                  CommandNotFound, CommandOnCooldown, Context,
                                  CooldownMapping, MissingPermissions,
                                  MissingRequiredArgument, NotOwner)
from humanfriendly import format_timespan
from humanize import precisedelta

from .context import PretendContext, PretendHelp, PretendInteraction
from .ext import HTTP, Client
from .handlers.embedbuilder import EmbedScript
from .persistent.tickets import TicketView

Interaction.approve = PretendInteraction.approve
Interaction.warn = PretendInteraction.warn
Interaction.error = PretendInteraction.error

intents = discord.Intents.all()
intents.presences = False


def generate_key():
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(6)
    )


async def getprefix(bot, message):
    if not message.guild:
        return ";"
    check = await bot.db.fetchrow(
        "SELECT * FROM selfprefix WHERE user_id = $1", message.author.id
    )
    if check:
        selfprefix = check["prefix"]
    res = await bot.db.fetchrow(
        "SELECT * FROM prefixes WHERE guild_id = $1", message.guild.id
    )
    if res:
        guildprefix = res["prefix"]
    else:
        guildprefix = ";"
    if not check and res:
        selfprefix = res["prefix"]
    elif not check and not res:
        selfprefix = ";"
    return guildprefix, selfprefix


async def checkthekey(key: str):
    check = await bot.db.fetchrow("SELECT * FROM cmderror WHERE code = $1", key)
    if check:
        newkey = await generate_key()
        return await checkthekey(newkey)
    return key


class Record(asyncpg.Record):

    def __getattr__(self, name: str):
        return self[name]


class Pretend(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix=getprefix,
            case_sensitive=True,
            intents=intents,
            shard_count=3,
            allowed_mentions=AllowedMentions(
                roles=False, everyone=False, users=True, replied_user=False
            ),
            strip_after_prefix=True,
            help_command=PretendHelp(),
            owner_ids=[852784127447269396, 713128996287807600],
            activity=discord.Activity(name="", type=discord.ActivityType.competing),
        )
        self.color = 0x747F8D
        self.warn = 0xEFBC1B
        self.deny = 0xEB3434
        self.approve = 0x47D403
        self.ext = Client(self)
        self.embed_build = EmbedScript()
        self.main_guilds = [
            1258712533284683798,
            1246416801311625308,
            1266088675880472669,
        ]
        self.proxy_url = "http://14a4a94eff770:c3ac0449fd@104.234.255.18:12323"
        self.no = "<:deny:1251929424777969797>"
        self.yes = "<:check:1251929419795398708>"
        self.warning = "<:warning:1305212823470866513>"
        self.warning_color = 0xFFC56E
        self.no_color = 0xFF6464
        self.yes_color = 0x8AFF9A
        self.m_cd = commands.CooldownMapping.from_cooldown(
            1, 5, commands.BucketType.member
        )
        self.c_cd = commands.CooldownMapping.from_cooldown(
            1, 5, commands.BucketType.channel
        )
        self.m_cd2 = commands.CooldownMapping.from_cooldown(
            1, 10, commands.BucketType.member
        )
        self.global_cd = commands.CooldownMapping.from_cooldown(
            2, 3, commands.BucketType.member
        )
        self.session_id = "59071245027%3AD0cDcLaxyzVyVQ%3A16%3AAYdIOvL5SM85A62N-zDxn04CaabIDHneyhA6I0r6VQ"

    async def create_db_pool(self):
        self.db = await create_pool(
            port="5432",
            database="postgres",
            user="postgres.pexxcoqyhdudkxrzxidm",
            host="aws-0-us-east-1.pooler.supabase.com",
            password="4MymSKEevVzwIo9G",
        )

    def humanize_date(self, date: datetime.datetime) -> str:
        """
        Humanize a datetime (ex: 2 days ago)
        """

        if date.timestamp() < datetime.datetime.now().timestamp():
            return f"{(precisedelta(date, format='%0.0f').replace('and', ',')).split(', ')[0]} ago"
        else:
            return f"in {(precisedelta(date, format='%0.0f').replace('and', ',')).split(', ')[0]}"

    async def guild_change(self, mes: str, guild: discord.Guild) -> discord.Message:
        channel = self.get_channel(1258714537855684699)
        try:
            await channel.send(
                embed=discord.Embed(
                    color=self.color,
                    description=f"{mes} **{guild.name}** owned by **{guild.owner}** with **{guild.member_count}** members",
                )
            )
        except:
            pass

    async def on_guild_join(self, guild: discord.Guild):
        if not guild.chunked:
            await guild.chunk(cache=True)
        await self.guild_change("joined", guild)

    async def on_guild_remove(self, guild: discord.Guild):
        await self.guild_change("left", guild)

    @property
    def members(self):
        return list(self.get_all_members())

    @property
    def channels(self):
        return list(self.get_all_channels())

    @property
    def text_channels(self):
        return list(
            filter(
                lambda channel: isinstance(channel, discord.TextChannel),
                self.get_all_channels(),
            )
        )

    @property
    def voice_channels(self):
        return list(
            filter(
                lambda channel: isinstance(channel, discord.VoiceChannel),
                self.get_all_channels(),
            )
        )

    @property
    def ping(self) -> int:
        return round(bot.latency * 1000)

    @property
    def lines(self) -> int:
        """
        Return the code's amount of lines
        """
        lines = 0
        for d in [x[0] for x in os.walk("./") if not ".git" in x[0]]:
            for file in os.listdir(d):
                if file.endswith(".py"):
                    lines += len(open(f"{d}/{file}", "r").read().splitlines())
        return lines

    def is_dangerous(self, role: discord.Role) -> bool:
        permissions = role.permissions
        return any(
            [
                permissions.kick_members,
                permissions.ban_members,
                permissions.administrator,
                permissions.manage_channels,
                permissions.manage_guild,
                permissions.manage_messages,
                permissions.manage_roles,
                permissions.manage_webhooks,
                permissions.manage_emojis_and_stickers,
                permissions.manage_threads,
                permissions.mention_everyone,
                permissions.moderate_members,
            ]
        )

    async def prefixes(self, message: discord.Message) -> List[str]:
        prefixes = []
        for l in set(p for p in await self.command_prefix(self, message)):
            prefixes.append(l)
        return prefixes

    async def channel_ratelimit(self, message: discord.Message) -> typing.Optional[int]:
        cd = self.c_cd
        bucket = cd.get_bucket(message)
        return bucket.update_rate_limit()

    async def member_ratelimit(self, message: discord.Message) -> typing.Optional[int]:
        cd = self.m_cd
        bucket = cd.get_bucket(message)
        return bucket.update_rate_limit()

    def convert_datetime(self, date: datetime.datetime = None):
        if date is None:
            return None
        month = f"0{date.month}" if date.month < 10 else date.month
        day = f"0{date.day}" if date.day < 10 else date.day
        year = date.year
        minute = f"0{date.minute}" if date.minute < 10 else date.minute
        if date.hour < 10:
            hour = f"0{date.hour}"
            meridian = "AM"
        elif date.hour > 12:
            hour = f"0{date.hour - 12}" if date.hour - 12 < 10 else f"{date.hour - 12}"
            meridian = "PM"
        else:
            hour = date.hour
            meridian = "PM"
        return f"{month}/{day}/{year} at {hour}:{minute} {meridian} ({discord.utils.format_dt(date, style='R')})"

    def ordinal(self, num: int) -> str:
        """Convert from number to ordinal (10 - 10th)"""
        numb = str(num)
        if numb.startswith("0"):
            numb = numb.strip("0")
        if numb in ["11", "12", "13"]:
            return numb + "th"
        if numb.endswith("1"):
            return numb + "st"
        elif numb.endswith("2"):
            return numb + "nd"
        elif numb.endswith("3"):
            return numb + "rd"
        else:
            return numb + "th"

    async def getbyte(self, video: str):
        return BytesIO(await self.session.read(video, proxy=self.proxy_url, ssl=False))

    async def on_message(self, message: discord.Message):
        channel_rl = await self.channel_ratelimit(message)
        member_rl = await self.member_ratelimit(message)

        if channel_rl == True:
            return
        if member_rl == True:
            return

        prefixes = ", ".join(f"`{p}`" for p in await self.prefixes(message))

        # Handle the mention and display the prefix
        if message.content == "<@{}>".format(self.user.id):
            prefix_text = (
                "Prefix is "
                if len(await self.prefixes(message)) == 1
                else "Your prefixes"
            )
            return await message.reply(
                embed=discord.Embed(
                    color=self.color, description=f"{prefix_text}: {prefixes}"
                )
            )

        await bot.process_commands(message)

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.NotOwner):
            pass
        elif isinstance(error, commands.CheckFailure):
            if isinstance(error, commands.MissingPermissions):
                return await ctx.send_warning(
                    f"You do not have the **required** permission: `{error.missing_permissions[0]}` to **proceed** with this **action**."
                )
        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.command.name != "hit":
                return await ctx.reply(
                    embed=discord.Embed(
                        color=0xEFBC1B,
                        description=f"{ctx.author.mention}: You must wait  **{format_timespan(error.retry_after)}** before attempting to use **{ctx.command.qualified_name}** again to prevent further conflicts.",
                    ),
                    mention_author=False,
                )
        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.cmdhelp()
        elif isinstance(error, commands.EmojiNotFound):
            return await ctx.send_warning(
                f"Unable to convert {error.argument} into an **emoji**"
            )
        elif isinstance(error, commands.MemberNotFound):
            return await ctx.send_warning(f"Unable to find member **{error.argument}**")
        elif isinstance(error, commands.UserNotFound):
            return await ctx.send_warning(f"Unable to find user **{error.argument}**")
        elif isinstance(error, commands.RoleNotFound):
            return await ctx.send_warning(f"Couldn't find role **{error.argument}**")
        elif isinstance(error, commands.ChannelNotFound):
            return await ctx.send_warning(f"Couldn't find channel **{error.argument}**")
        elif isinstance(error, commands.UserConverter):
            return await ctx.send_warning(f"Couldn't convert that into an **user** ")
        elif isinstance(error, commands.MemberConverter):
            return await ctx.send_warning("Couldn't convert that into a **member**")
        elif isinstance(error, commands.BadArgument):
            return await ctx.send_warning(error.args[0])
        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send_warning(
                f"I do not have enough **permissions** to execute this command"
            )
        elif isinstance(error, discord.HTTPException):
            return await ctx.send_warning("Unable to execute this command")
        else:
            key = await checkthekey(generate_key())
            trace = str(error)
            rl = await self.member_ratelimit(ctx.message)
            if rl == True:
                return
            await self.db.execute("INSERT INTO cmderror VALUES ($1,$2)", key, trace)
            await self.ext.send_warning(
                ctx,
                f"A **system** error has occurred. To **expedite resolution**, please join our [**support server**](https://discord.gg/blonde) and share the **following reference** code: `{key}`.  Our **team** will assist you **promptly**.",
            )

    async def setup_hook(self) -> None:
        self.session = HTTP()
        self.add_view(vmbuttons())
        # self.add_view(CreateTicket())
        # self.add_view(DeleteTicket())
        self.add_view(TicketView(self, True))
        self.add_view(GiveawayView())
        await self.create_db_pool()
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                await self.load_extension("cogs." + file[:-3])
                print(f"Loaded cog: {file[:-3]}")
        await self.load_extension("jishaku")

    async def get_context(self, message, *, cls=PretendContext):
        return await super().get_context(message, cls=cls)

    async def on_message_edit(self, before: Message, after: Message):
        if not before.guild:
            return
        if before.content != after.content:
            await self.process_commands(after)

    async def on_ready(self):
        print(f"Connected in as {self.user} {self.user.id}")
        await Music(self).start_node()


bot = Pretend()


@bot.check
async def disabled_command(ctx: commands.Context):
    cmd = bot.get_command(ctx.invoked_with)
    if not cmd:
        return True
    check = await ctx.bot.db.fetchrow(
        "SELECT * FROM disablecommand WHERE command = $1 AND guild_id = $2",
        cmd.name,
        ctx.guild.id,
    )
    if check:
        await bot.ext.send_warning(
            ctx,
            f"The **execution** of the command **{cmd.name}** has been **restricted** in this **guild** at the discretion of the **administrator**.",
        )
    return check is None


@bot.check
async def cooldown_check(ctx: commands.Context):
    bucket = bot.global_cd.get_bucket(ctx.message)
    retry_after = bucket.update_rate_limit()
    if retry_after:
        raise commands.CommandOnCooldown(
            bucket, retry_after, commands.BucketType.member
        )
    return True


async def check_ratelimit(ctx):
    cd = bot.m_cd2.get_bucket(ctx.message)
    return cd.update_rate_limit()


@bot.check
async def is_chunked(ctx: commands.Context):
    if ctx.guild:
        if not ctx.guild.chunked:
            await ctx.guild.chunk(cache=True)
        return True


async def mobile(self):
    payload = {
        "op": self.IDENTIFY,
        "d": {
            "token": self.token,
            "properties": {
                "$os": sys.platform,
                "$browser": "Discord iOS",
                "$device": "discord.py",
                "$referrer": "",
                "$referring_domain": "",
            },
            "compress": True,
            "large_threshold": 250,
            "v": 3,
        },
    }
    if self.shard_id is not None and self.shard_count is not None:
        payload["d"]["shard"] = [self.shard_id, self.shard_count]
    state = self._connection
    if state._activity is not None or state._status is not None:
        payload["d"]["presence"] = {
            "status": state._status,
            "game": state._activity,
            "since": 0,
            "afk": True,
        }
    if state._intents is not None:
        payload["d"]["intents"] = state._intents.value
    await self.call_hooks(
        "before_identify", self.shard_id, initial=self._initial_identify
    )
    await self.send_as_json(payload)


discord.gateway.DiscordWebSocket.identify = mobile


@bot.check
async def is_chunked(ctx: commands.Context):
    if ctx.guild:
        if not ctx.guild.chunked:
            await ctx.guild.chunk(cache=True)
        return True


bot.run("MTMwNTE5OTM3Mjc5NDg1NTQ5Nw.GW4B2t.4wbI5Ad8iTYoEScxY0EamGKhxFMo50BXXUYT6U")
