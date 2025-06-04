import os
import random
import string
import time
import typing
from io import BytesIO
from typing import List, Optional, Sequence, Union

import asyncpg
import discord
import dotenv
from cogs.giveaway import GiveawayView
from cogs.ticket import CreateTicket, DeleteTicket
from cogs.voicemaster import vmbuttons
from discord import Embed, utils
from discord.ext import commands
from discord.gateway import DiscordWebSocket
from discord.ui import View
from headers import Session
from helpers import ResentContext
from humanfriendly import format_timespan
from rivalapi.rivalapi import RivalAPI
from twscrape import API
from utils.database import create_db
from utils.dynamicrolebutton import DynamicRoleButton
from utils.ext import HTTP, Client
from utils.utils import PaginatorView, StartUp

dotenv.load_dotenv(verbose=True)
token = os.environ["token"]


def generate_key():
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(6)
    )


async def checkthekey(key: str):
    check = await bot.db.fetchrow("SELECT * FROM cmderror WHERE code = $1", key)
    if check:
        newkey = await generate_key(key)
        return await checkthekey(newkey)
    return key


DiscordWebSocket.identify = StartUp.identify

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"
os.environ["JISHAKU_RETAIN"] = "True"


async def botrun():
    await bot.start(reconnect=True)


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


class NeoContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def find_role(self, name: str):
        for role in self.guild.roles:
            if role.name == "@everyone":
                continue
            if name.lower() in role.name.lower():
                return role
        return None

    async def send_success(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=self.bot.color,
                description=f"{self.bot.yes} {self.author.mention}: {message}",
            )
        )

    async def send_error(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=self.bot.color,
                description=f"{self.bot.no} {self.author.mention}: {message}",
            )
        )

    async def send_warning(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=self.bot.color,
                description=f"{self.bot.warning} {self.author.mention}: {message}",
            )
        )

    async def paginate(
        self,
        contents: List[str],
        title: str = None,
        author: dict = {"name": "", "icon_url": None},
    ):
        iterator = [m for m in utils.as_chunks(contents, 10)]
        embeds = [
            Embed(
                color=self.bot.color,
                title=title,
                description="\n".join(
                    [f"`{(m.index(f)+1)+(iterator.index(m)*10)}.` {f}" for f in m]
                ),
            ).set_author(**author)
            for m in iterator
        ]
        return await self.paginator(embeds)

    async def paginator(self, embeds: List[discord.Embed]):
        if len(embeds) == 1:
            return await self.send(embed=embeds[0])
        view = PaginatorView(self, embeds)
        view.message = await self.reply(embed=embeds[0], view=view)

    async def reply(
        self,
        content: Optional[str] = None,
        *,
        embed: Optional[discord.Embed] = None,
        view: Optional[View] = None,
        mention_author: Optional[bool] = False,
        file: Optional[discord.File] = discord.utils.MISSING,
        files: Optional[Sequence[discord.File]] = discord.utils.MISSING,
    ) -> discord.Message:
        reskin = await self.bot.db.fetchrow(
            "SELECT * FROM reskin WHERE user_id = $1 AND toggled = $2",
            self.author.id,
            True,
        )
        if reskin != None and reskin["toggled"]:
            hook = await self.webhook(self.message.channel)
            if view == None:
                return await hook.send(
                    content=content,
                    embed=embed,
                    username=reskin["name"],
                    avatar_url=reskin["avatar"],
                    file=file,
                )
            return await hook.send(
                content=content,
                embed=embed,
                username=reskin["name"],
                avatar_url=reskin["avatar"],
                view=view,
                file=file,
            )
        return await self.send(
            content=content,
            embed=embed,
            reference=self.message,
            view=view,
            mention_author=mention_author,
            file=file,
        )

    async def send(
        self,
        content: Optional[str] = None,
        *,
        embed: Optional[discord.Embed] = None,
        view: Optional[View] = discord.utils.MISSING,
        mention_author: Optional[bool] = False,
        allowed_mentions: discord.AllowedMentions = discord.utils.MISSING,
        reference: Optional[
            Union[discord.Message, discord.MessageReference, discord.PartialMessage]
        ] = None,
        file: Optional[discord.File] = discord.utils.MISSING,
        files: Optional[Sequence[discord.File]] = discord.utils.MISSING,
    ) -> discord.Message:
        reskin = await self.bot.db.fetchrow(
            "SELECT * FROM reskin WHERE user_id = $1 AND toggled = $2",
            self.author.id,
            True,
        )
        if reskin != None and reskin["toggled"]:
            hook = await self.webhook(self.message.channel)
            return await hook.send(
                content=content,
                embed=embed,
                username=reskin["name"],
                avatar_url=reskin["avatar"],
                view=view,
                allowed_mentions=allowed_mentions,
                file=file,
            )
        return await self.channel.send(
            content=content,
            embed=embed,
            view=view,
            allowed_mentions=allowed_mentions,
            reference=reference,
            mention_author=mention_author,
            file=file,
        )

    async def webhook(self, channel) -> discord.Webhook:
        for webhook in await channel.webhooks():
            if webhook.user == self.me:
                return webhook
        return await channel.create_webhook(name="resent")

    async def cmdhelp(self):
        command = self.command
        commandname = (
            f"{str(command.parent)} {command.name}"
            if str(command.parent) != "None"
            else command.name
        )
        if command.cog_name == "owner" or "jishaku":
            return
        embed = discord.Embed(
            color=bot.color, title=commandname, description=command.description
        )
        embed.set_author(
            name=self.author.name,
            icon_url=self.author.display_avatar.url if not None else "",
        )
        embed.add_field(
            name="aliases", value=", ".join(map(str, command.aliases)) or "none"
        )
        embed.add_field(name="permissions", value=command.brief or "any")
        embed.add_field(
            name="usage",
            value=f"```{commandname} {command.usage if command.usage else ''}```",
            inline=False,
        )
        embed.set_footer(
            text=f"module: {command.cog_name}",
            icon_url=self.author.display_avatar.url if not None else "",
        )
        await self.reply(embed=embed)

    async def create_pages(self):
        embeds = []
        i = 0
        for command in self.command.commands:
            commandname = (
                f"{str(command.parent)} {command.name}"
                if str(command.parent) != "None"
                else command.name
            )
            i += 1
            embeds.append(
                discord.Embed(
                    color=bot.color,
                    title=f"{commandname}",
                    description=command.description,
                )
                .set_author(
                    name=self.author.name,
                    icon_url=self.author.display_avatar.url if not None else "",
                )
                .add_field(
                    name="usage",
                    value=f"```{commandname} {command.usage if command.usage else ''}```",
                    inline=False,
                )
                .set_footer(
                    text=f"module: {command.cog_name} • aliases: {', '.join(a for a in command.aliases) if len(command.aliases) > 0 else 'none'} ・ {i}/{len(self.command.commands)}"
                )
            )

        return await self.paginator(embeds)


class HelpCommand(commands.HelpCommand):
    def __init__(self, **kwargs):
        self.categories = {}
        super().__init__(**kwargs)

    async def send_bot_help(self, ctx: commands.Context) -> None:
        return await self.context.send(
            f"{self.context.author.mention}: check <https://resent.dev/commands> for list of commands"
        )

    async def send_command_help(self, command: commands.Command):
        commandname = (
            f"{str(command.parent)} {command.name}"
            if str(command.parent) != "None"
            else command.name
        )
        embed = discord.Embed(
            color=bot.color, title=commandname, description=command.description
        )
        embed.set_author(
            name=self.context.author.name,
            icon_url=self.context.author.display_avatar.url if not None else "",
        )
        embed.add_field(
            name="aliases", value=", ".join(map(str, command.aliases)) or "none"
        )
        embed.add_field(name="permissions", value=command.brief or "any")
        embed.add_field(
            name="usage",
            value=f"```{commandname} {command.usage if command.usage else ''}```",
            inline=False,
        )
        embed.set_footer(
            text=f"module: {command.cog_name}",
            icon_url=self.context.author.display_avatar.url if not None else "",
        )
        await self.context.reply(embed=embed)

    async def send_group_help(self, group: commands.Group):
        ctx = self.context
        embeds = []
        i = 0
        for command in group.commands:
            commandname = (
                f"{str(command.parent)} {command.name}"
                if str(command.parent) != "None"
                else command.name
            )
            i += 1
            embeds.append(
                discord.Embed(
                    color=bot.color,
                    title=f"{commandname}",
                    description=command.description,
                )
                .set_author(
                    name=ctx.author.name,
                    icon_url=ctx.author.display_avatar.url if not None else "",
                )
                .add_field(
                    name="usage",
                    value=f"```{commandname} {command.usage if command.usage else ''}```",
                    inline=False,
                )
                .set_footer(
                    text=f"module: {command.cog_name} • aliases: {', '.join(a for a in command.aliases) if len(command.aliases) > 0 else 'none'} ・ {i}/{len(group.commands)}"
                )
            )

        return await ctx.paginator(embeds)


class CommandClient(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix=getprefix,
            allowed_mentions=discord.AllowedMentions(
                roles=False, everyone=False, users=True, replied_user=False
            ),
            intents=discord.Intents.all(),
            help_command=HelpCommand(),
            strip_after_prefix=True,
            activity=discord.CustomActivity(name="🔗 resent.dev"),
            owner_ids=[959292943657746464, 214753146512080907, 128114020744953856],
        )
        self.uptime = time.time()
        self.persistent_views_added = False
        self.cogs_loaded = False
        self.google_api = "AIzaSyDPrFJ8oxPP5YWM82vqCaLq8F6ZdlSGsBo"
        self.color = 0xFFFFFF
        self.yes = "<:approved:1209081187679862784>"
        self.no = "<:false:1209081189269512253>"
        self.warning = "<:warning:1209081190418743326>"
        self.left = "<:left:1227724412967714907>"
        self.right = "<:right:1227724250165678091>"
        self.goto = "<:filter:1208241278891073547>"
        self.twitter = API()
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
        self.main_guilds = [1208651928507129887]
        self.ext = Client(self)
        self.support_server = "https://discord.gg/resent"
        self.commands_url = "https://resent.dev/commands"
        self.proxy_url = (
            "http://38gt3f7lsejwhm4:5xarwv0int6boz5@rp.proxyscrape.com:6060"
        )
        self.resent_api = "58ZCTj0fTkai"
        self.rival_api = "88d7eac6-df61-4a08-a95d-8904f81cc099"
        self.rival = RivalAPI(self.rival_api)
        self.session = Session()

    async def get_context(
        self, message: discord.Message, cls=ResentContext
    ) -> ResentContext:
        return await super().get_context(message, cls=cls)

    async def getbyte(self, url: str) -> BytesIO:
        return BytesIO(await self.session.get_bytes(url))

    async def create_db_pool(self):
        self.db = await asyncpg.create_pool(
            port="5432",
            database="resent",
            user="postgres",
            host="localhost",
            password="admin",
        )

    async def get_context(self, message, *, cls=NeoContext):
        return await super().get_context(message, cls=cls)

    async def setup_hook(self) -> None:
        print("Attempting to start")
        self.session = HTTP()
        await self.twitter.pool.login_all()
        bot.loop.create_task(bot.create_db_pool())
        self.add_dynamic_items(DynamicRoleButton)
        self.add_view(vmbuttons())
        self.add_view(CreateTicket())
        self.add_view(DeleteTicket())
        self.add_view(GiveawayView())
        bot.loop.create_task(StartUp.startup(bot))

        await bot.load_extension("jishaku")

    async def getbyte(self, video: str):
        return BytesIO(await self.session.read(video, proxy=self.proxy_url, ssl=False))

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

    async def on_ready(self):
        await create_db(self)
        if self.cogs_loaded == False:
            await StartUp.loadcogs(self)
        print(f"Connected to Discord API as {self.user} {self.user.id}")

    async def on_message_edit(self, before, after):
        if before.content != after.content:
            await self.process_commands(after)

    async def on_message(self, message: discord.Message):
        channel_rl = await self.channel_ratelimit(message)
        member_rl = await self.member_ratelimit(message)
        if channel_rl == True:
            return
        if member_rl == True:
            return
        if message.content == "<@{}>".format(self.user.id):
            return await message.reply(
                content="prefixes: "
                + " ".join(f"`{g}`" for g in await self.prefixes(message))
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
                    f"This command requires **{error.missing_permissions[0]}** permission"
                )
        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.command.name != "hit":
                return await ctx.reply(
                    embed=discord.Embed(
                        color=0xE1C16E,
                        description=f"⌛ {ctx.author.mention}: You are on cooldown. Try again in {format_timespan(error.retry_after)}",
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
        elif isinstance(error, commands.CommandInvokeError):
            return await ctx.send_warning(error.original)
        elif isinstance(error, discord.HTTPException):
            return await ctx.send_warning("Unable to execute this command")
        else:
            key = await checkthekey(generate_key())
            trace = str(error)
            rl = await self.member_ratelimit(ctx.message)
            if rl == True:
                return
            await self.db.execute("INSERT INTO cmderror VALUES ($1,$2)", key, trace)
            await self.ext.send_error(
                ctx,
                f"An unexpected error was found. Please report the code `{key}` in our [**support server**](https://discord.gg/resent)",
            )


bot = CommandClient()


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
async def blacklist(ctx: commands.Context):
    rl = await check_ratelimit(ctx)
    if rl == True:
        return
    if ctx.guild is None:
        return False
    check = await bot.db.fetchrow(
        "SELECT * FROM nodata WHERE user_id = $1", ctx.author.id
    )
    if check is not None:
        if check["state"] == "false":
            return False
        else:
            return True
    embed = discord.Embed(
        color=bot.color,
        description="Do you **agree** to our [privacy policy](https://resent.dev/privacy) and for your data to be used for commands?\n**DISAGREEING** will result in a blacklist from using bot's commands",
    )
    yes = discord.ui.Button(emoji=bot.yes, style=discord.ButtonStyle.gray)
    no = discord.ui.Button(emoji=bot.no, style=discord.ButtonStyle.gray)

    async def yes_callback(interaction: discord.Interaction):
        if interaction.user != ctx.author:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    color=bot.color,
                    description=f"{bot.warning} {interaction.user.mention}: This is not your message",
                ),
                ephemeral=True,
            )
        await bot.db.execute("INSERT INTO nodata VALUES ($1,$2)", ctx.author.id, "true")
        await interaction.message.delete()
        await bot.process_commands(ctx.message)

    yes.callback = yes_callback

    async def no_callback(interaction: discord.Interaction):
        if interaction.user != ctx.author:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    color=bot.color,
                    description=f"{bot.warning} {interaction.user.mention}: This is not your message",
                ),
                ephemeral=True,
            )
        await bot.db.execute(
            "INSERT INTO nodata VALUES ($1,$2)", ctx.author.id, "false"
        )
        await interaction.response.edit_message(
            embed=discord.Embed(
                color=bot.color,
                description=f"You got blacklisted from using bot's commands. If this is a mistake, please check our [**support server**](https://discord.gg/resent)",
            ),
            view=None,
        )
        return

    no.callback = no_callback

    view = discord.ui.View()
    view.add_item(yes)
    view.add_item(no)
    await ctx.reply(embed=embed, view=view, mention_author=False)


@bot.check
async def is_chunked(ctx: commands.Context):
    if ctx.guild:
        if not ctx.guild.chunked:
            await ctx.guild.chunk(cache=True)
        return True


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
        await bot.ext.send_warning(ctx, f"The command **{cmd.name}** is **disabled**")
    return check is None


if __name__ == "__main__":
    # asyncio.run(botrun())
    bot.run(token)
