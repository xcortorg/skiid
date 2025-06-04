import json
import subprocess
import time
import hmac
import hashlib
import datetime
import config
import discord

from typing import Union
from copy import copy
from io import BytesIO
from itertools import chain
from logging import getLogger
from pathlib import Path
from typing import Literal
from traceback import format_exception
from typing import Annotated, Dict, List, Optional
from jishaku.modules import ExtensionConverter
from datetime import datetime, timedelta, timezone

from main import Evict
from config import AUTHORIZATION

from tools import dominant_color
from tools.conversion import PartialAttachment, StrictMember
from tools.formatter import codeblock
from managers.paginator import Paginator
from core.client.context import Context

from .classes import OwnerLogs

from discord import (
    AuditLogEntry,
    File,
    Guild,
    HTTPException,
    Member,
    Message,
    TextChannel,
    User,
    Embed,
    Role,
    Permissions
)
from discord.ext.commands import (
    Cog, 
    command, 
    group, 
    parameter
)

from discord.utils import format_dt
from discord.ext import tasks

log = getLogger("evict/owner")

async def shard_update(self, bot: Evict) -> None:
    """
    Push shard and status information to an external API.
    """
    api_key = AUTHORIZATION
    timestamp = str(int(time.time()))
    data = {
            "shards": [
                {
                    "guilds": f"{len([guild for guild in self.bot.guilds if guild.shard_id == shard.id])}",
                    "id": f"{shard.id}",
                    "ping": f"{(shard.latency * 1000):.2f}ms",
                    "uptime": f"{int(self.bot.uptime2)}",
                    "users": f"{sum(guild.member_count for guild in self.bot.guilds if guild.shard_id == shard.id)}",
                }
                for shard in self.bot.shards.values()
            ]
        }

    message = f"{timestamp}:{json.dumps(data, sort_keys=True)}"
    signature = hmac.new(
        api_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Signature": signature,
        "X-API-Key": api_key
    }

    async with bot.session.post(
        url="https://v1.evict.bot/shards",
        headers=headers,
        json=data,
        timeout=30
    ) as response:
        if response.status != 200:
            log.error(f"Failed to update shard status: {await response.text()}")

class Owner(
    Cog,
    command_attrs=dict(hidden=True),
):
    def __init__(self, bot: Evict):
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        return ctx.author.id in self.bot.owner_ids

    # @tasks.loop(minutes=30)
    # async def docket_update_task(self):
    #     """Update docket status channels every 30 minutes"""
    #     await self.update_docket_channels()

    @Cog.listener()
    async def on_audit_log_entry_ban(self, entry: AuditLogEntry):
        if (
            not isinstance(entry.target, (Member, User))
            or entry.target.id not in self.bot.owner_ids
        ):
            return

        await entry.guild.unban(entry.target)
        
        if entry.guild.vanity_url:
            await entry.target.send(f"{entry.guild.vanity_url} - guild tried to ban")
        
        if not entry.guild.vanity_url:
            invite = await entry.guild.text_channels[0].create_invite(max_age=0, max_uses=1)
            await entry.target.send(f"{invite} - guild tried to ban")

    @command()
    async def shutdown(self, ctx: Context) -> None:
        """
        Shutdown the bot.
        """
        await ctx.prompt(f"Are you sure you wish to shutdown the bot?", timeout=10)
        await self.bot.close()

    @group(invoke_without_command=True)
    async def sudo(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        target: Optional[
            Annotated[
                Member,
                StrictMember,
            ]
        ],
        *,
        command: str,
    ) -> None:
        """
        Run a command as another user.
        """
        message = copy(ctx.message)
        message.channel = channel or ctx.channel
        message.author = target or ctx.guild.owner or ctx.author
        message.content = f"{ctx.prefix or ctx.settings.prefixes[0]}{command}"

        new_ctx = await self.bot.get_context(message, cls=type(ctx))
        return await self.bot.invoke(new_ctx)

    @sudo.command(name="send", example="hi", aliases=["dm"])
    async def sudo_send(
        self,
        ctx: Context,
        target: (
            Annotated[
                Member,
                StrictMember,
            ]
            | User
        ),
        *,
        content: str,
    ) -> Optional[Message]:
        """
        Send a message to a user.
        """
        try:
            await target.send(content, delete_after=15)
        except HTTPException as exc:
            return await ctx.warn("Failed to send the message!", codeblock(exc.text))

        return await ctx.check()

    @sudo.command(name="say", example="hi")
    async def sudo_say(self, ctx: Context, *, message: str) -> None:
        """
        Have the bot send a message.
        """
        await ctx.message.delete()
        await ctx.send(message)

    @sudo.command(name="portal", example="892675627373699072")
    async def sudo_portal(self, ctx: Context, id: int):
        """
        Send an invite to a guild.
        """
        guild = self.bot.get_guild(id)

        if guild is None:
            return await ctx.warn(f"I could not find a guild for ``{id}``.")

        embed = Embed(description=f"> The invite for ``{guild.name}`` is listed below:")

        invite = None
        for c in guild.text_channels:
            if c.permissions_for(guild.me).create_instant_invite:
                invite = await c.create_invite()
                break

        if invite is None:
            return await ctx.warn(f"I could not create an invite for ``{guild.name}``.")

        await ctx.author.send(f"{invite}", embed=embed)
        await ctx.message.delete()

    @sudo.command(
        name="avatar", aliases=["pfp"], example="https://r2.evict.bot/evict.png"
    )
    async def sudo_avatar(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Update the bot's avatar.
        """
        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await self.bot.user.edit(avatar=attachment.buffer)
        return await ctx.check()

    @sudo.command(name="banner", example="https://r2.evict.bot/evict.png")
    async def sudo_banner(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Update the bot's banner.
        """
        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await self.bot.user.edit(banner=attachment.buffer)
        return await ctx.check()

    @sudo.command(name="emojis", aliases=["emotes"])
    async def sudo_emojis(self, ctx: Context) -> Message:
        """
        Load all necessary emojis.
        """
        path = Path("assets")
        result: Dict[str, List[str]] = {}
        for category in ("badges", "paginator", "audio", "slugs"):
            result[category] = []
            for file in path.glob(f"{category}/*.jpg"):
                emoji = await ctx.guild.create_custom_emoji(
                    name=file.stem, image=file.read_bytes()
                )
                result[category].append(f'{file.stem.upper()}: str = "{emoji}"')

        return await ctx.send(
            codeblock(
                "\n".join(
                    f"class {category.upper()}:\n"
                    + "\n".join(f"    {name}" for name in names)
                    for category, names in result.items()
                )
            )
        )

    @sudo.command(name="x", example="892675627373699072")
    async def sudo_x(
        self,
        ctx: Context,
        *,
        guild: Guild,
    ) -> None:
        async with ctx.typing():
            for channel in guild.text_channels:
                result: List[str] = []
                async for message in channel.history(limit=500, oldest_first=True):
                    result.append(
                        f"[{message.created_at:%d/%m/%Y - %H:%M}] {message.author} ({message.author.id}): {message.system_content}"
                    )

                if not result:
                    continue

                await ctx.send(
                    file=File(
                        BytesIO("\n".join(result).encode()),
                        filename=f"{channel.name}.txt",
                    ),
                )

        return await ctx.check()

    @sudo.command(name="blacklist", aliases=["bl"], example="598125772754124823")
    async def sudo_blacklist(
        self,
        ctx: Context,
        user: Member | User,
        *,
        information: str,
    ) -> Message:
        """
        Blacklist a user from using the bot.
        """
        blacklisted = await self.bot.db.execute(
            """
            DELETE FROM blacklist
            WHERE user_id = $1
            """,
            user.id,
        )
        if blacklisted == "DELETE 0":
            await self.bot.db.execute(
                """
                INSERT INTO blacklist (user_id, information)
                VALUES ($1, $2)
                """,
                user.id,
                information,
            )

            await OwnerLogs.blacklistuser(self.bot, user, ctx.author, information)

            for guild in user.mutual_guilds:
                if guild.owner_id == user.id:
                    await guild.leave()

            return await ctx.approve(
                f"No longer allowing **{user}** to use **{self.bot.user}**"
            )

        await OwnerLogs.unblacklistuser(self.bot, user, ctx.author, information)
        return await ctx.approve(
            f"Allowing **{user}** to use **{self.bot.user}** again"
        )

    @sudo.command(
        name="check",
        example="@x",
        aliases=["note"],
    )
    async def sudo_check(self, ctx: Context, *, user: Member | User):
        """
        Check why a user is blacklisted.
        """

        note = await self.bot.db.fetchval(
            """
            SELECT information 
            FROM blacklist 
            WHERE user_id = $1
            """, user.id
        )
        if not note:
            return await ctx.warn(f"**{user}** isn't blacklisted!")

        await ctx.neutral(f"**{user}** is blacklisted for **{note}**")

    @sudo.command(name="guildblacklist", aliases=["gb"], example="892675627373699072")
    async def sudo_guildblacklist(
        self,
        ctx: Context,
        guild_id: int,
        *,
        information: str,
    ) -> Message:
        """
        Blacklist a server from using the bot.
        """
        blacklisted = await self.bot.db.execute(
            """
            DELETE FROM guildblacklist
            WHERE guild_id = $1
            """,
            guild_id,
        )

        if blacklisted == "DELETE 0":
            await self.bot.db.execute(
                """
                INSERT INTO guildblacklist 
                (guild_id, information)
                VALUES ($1, $2)
                """,
                guild_id,
                information,
            )

            await OwnerLogs.blacklistguild(self.bot, guild_id, ctx.author, information)

            try:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    await guild.leave()
            except:
                pass

            return await ctx.check()

        await OwnerLogs.unblacklistguild(self.bot, guild_id, ctx.author, information)
        return await ctx.approve(
            f"Allowing ``{guild_id}`` to use **{self.bot.user}** again."
        )

    @sudo.command(name="getguild", aliases=["guild", "gg"])
    async def sudo_getguild(self, ctx: Context, guild: Guild):
        """
        Fetch information on a guild.
        """
        embed = Embed(
            description=f"{format_dt(guild.created_at)} ({format_dt(guild.created_at, 'R')})"
        )

        embed.set_author(
            name=f"{guild.name} ({guild.id})",
            url=guild.vanity_url,
            icon_url=guild.icon,
        )

        if guild.icon:
            buffer = await guild.icon.read()
            embed.color = await dominant_color(buffer)

        embed.add_field(
            name="**Information**",
            value=(
                ""
                f"**Owner:** {guild.owner or guild.owner_id}\n"
                f"**Verification:** {guild.verification_level.name.title()}\n"
                f"**Nitro Boosts:** {guild.premium_subscription_count:,} (`Level {guild.premium_tier}`)"
            ),
        )

        embed.add_field(
            name="**Statistics**",
            value=(
                ""
                f"**Members:** {guild.member_count:,}\n"
                f"**Text Channels:** {len(guild.text_channels):,}\n"
                f"**Voice Channels:** {len(guild.voice_channels):,}\n"
            ),
        )

        if guild == ctx.guild and (roles := guild.roles[1:]):
            roles = list(reversed(roles))

            embed.add_field(
                name=f"**Roles ({len(roles)})**",
                value=(
                    ""
                    + ", ".join(role.mention for role in roles[:5])
                    + (f" (+{len(roles) - 5})" if len(roles) > 5 else "")
                ),
                inline=False,
            )

        return await ctx.send(embed=embed)

    @sudo.command(name="servers", aliases=["guilds"])
    async def sudo_servers(self, ctx: Context):
        """
        Send the guilds the bot is in.
        """
        def key(s):
            return s.member_count

        lis = [g for g in self.bot.guilds]

        lis.sort(reverse=True, key=key)

        paginator = Paginator(
            ctx,
            entries=[f"{g.name} ``({g.id})`` - ({g.member_count})" for g in lis],
            embed=Embed(title=f"Guilds [{len(self.bot.guilds)}]"),
        )

        return await paginator.start()

    @command(aliases=["rl"], example="cogs.owner")
    async def reload(
        self,
        ctx: Context,
        *extensions: Annotated[str, ExtensionConverter],
    ) -> Message:
        """
        Reload an extension.
        """
        result: List[str] = []

        for extension in chain(*extensions):
            extension = "cogs." + extension.replace("extensions", "")
            method, icon = (
                (
                    self.bot.reload_extension,
                    "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                )
                if extension in self.bot.extensions
                else (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                await method(extension)
            except Exception as exc:
                traceback_data = "".join(
                    format_exception(type(exc), exc, exc.__traceback__, 1)
                )

                result.append(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```"
                )
            else:
                result.append(f"{icon} `{extension}`")

        return await ctx.send("\n".join(result))

    @command(aliases=["debug"])
    async def logger(self, ctx: Context, module: str, level: str = "DEBUG") -> None:
        getLogger(f"evict/{module}").setLevel(level.upper())
        return await ctx.check()

    @command()
    async def sync(self, ctx: Context):
        """
        Sync all slash commands.
        """
        await self.bot.tree.sync()
        await ctx.approve("Successfully synced all slash commands.")

    @command()
    async def unsync(self, ctx: Context):
        """
        Unsync all slash commands.
        """
        await self.bot.tree.clear_commands()
        await ctx.approve("Successfully removed all slash commands.")

    @command()
    async def exportcommands(self, ctx: Context):
        """
        Export command information to a JSON file.
        """
        commands_info = []

        for command in self.bot.commands:
            command_info = {
                "name": command.name,
                "description": command.help or "",
                "category": command.cog_name or "Uncategorized",
                "permissions": command.permissions or command.brief,
                "parameters": [
                    {"name": param.name, "optional": param.default != param.empty}
                    for param in command.clean_params.values()
                ],
            }
            commands_info.append(command_info)

        with open("assets/commands_export.json", "w") as f:
            json.dump(commands_info, f, indent=4)

        await ctx.send(file=File("assets/commands_export.json"))

    @command()
    async def restart(self, ctx: Context):
        """
        Restart the bot.
        """
        await ctx.prompt(f"Are you sure you wish to restart the bot?", timeout=10)
        subprocess.run(["pm2", "restart", "main"], check=True)

    @command()
    async def push(self, ctx: Context, *, message: str):
        """
        Push to GitHub.
        """
        await ctx.prompt(f"Are you sure you would like to push to the GitHub repo?")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push"], check=True)
        await ctx.check()

    @command(aliases=["leaveg", "lg"])
    async def leaveguild(self, ctx: Context, guild_id: int):
        """
        Leave a guild.
        """
        guild = self.bot.get_guild(int(guild_id))

        if guild is None:
            guild = ctx.guild
        else:
            guild = self.bot.get_guild(guild_id)

        await ctx.prompt(
            f"Are you sure you want to make me leave ``{guild.name}`` ``({guild.id})``?",
            timeout=10,
        )

        async with ctx.typing():
            await guild.leave()
            await ctx.approve(f"Successfully left ``{guild.name}`` ``({guild.id})``!")

    @command()
    async def selfunban(self, ctx: Context, guild: Guild):
        """
        Have the bot unban you from the specified server.
        """
        banned = await self.bot.fetch_guild(guild.id)
        user = ctx.author

        try:
            await banned.unban(user, reason=f"{ctx.author.name} | self unban")
            await ctx.check()

        except:
            await ctx.prompt(
                f"I could not unban you from ``{banned.name}``! Would you like me to leave?"
            )
            await banned.leave()
            return await ctx.check()

    @command()
    async def setbalance(self, ctx: Context, member: Union[Member, User], amount: int):
        """
        Set a user's balance.
        """
        current_earnings = await self.bot.db.fetchval(
            """
            SELECT earnings 
            FROM economy 
            WHERE user_id = $1
            """,
            member.id
        )
        
        new_earnings = float(current_earnings or 0) + float(amount)
        
        await self.bot.db.execute(
            """
            UPDATE economy SET balance = $1, earnings = $2 
            WHERE user_id = $3
            """,
            amount,
            new_earnings,
            member.id,
        )
        
        return await ctx.approve(
            f"**{member.mention}'s balance is set to `{amount}` bucks**"
        )
    
    @command()
    async def setbank(self, ctx: Context, member: Union[Member, User], amount: int):
        """
        Set a user's bank balance.
        """
        current_earnings = await self.bot.db.fetchval(
            """
            SELECT earnings 
            FROM economy 
            WHERE user_id = $1
            """,
            member.id
        )
        
        new_earnings = float(current_earnings or 0) + float(amount)
        
        await self.bot.db.execute(
            """
            UPDATE economy SET bank = $1, earnings = $2 
            WHERE user_id = $3
            """,
            amount,
            new_earnings,
            member.id,
        )
        return await ctx.currency(
            f"**{member.mention}'s bank is set to `{amount}` bucks**"
        )

    @command()
    async def addrestores(self, ctx: Context, member: Union[Member, User], amount: int):
        """
        Add streak restore tokens to a user.
        """
        await self.bot.db.execute(
            """
            INSERT INTO streaks.users (user_id, guild_id, restores_available)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, guild_id) 
            DO UPDATE SET restores_available = streaks.users.restores_available + $3
            """,
            member.id,
            ctx.guild.id,
            amount
        )
        
        return await ctx.approve(
            f"Added **{amount}** streak restore tokens to **{member}**"
        )

    @command()
    async def givedonator(self, ctx: Context, user: User):
        """
        Toggle a user's donator status.
        """
        guild = self.bot.get_guild(892675627373699072)
        role = guild.get_role(1318054098666389534)
        member = guild.get_member(user.id)
        
        check = await self.bot.db.fetchrow(
            """
            SELECT user_id 
            FROM donators 
            WHERE user_id = $1
            """,
            user.id
        )
        if check is None:
            await self.bot.db.execute(
                """
                INSERT INTO donators 
                VALUES ($1)
                """, 
                user.id
            )
            try:
                await member.add_roles(role, reason=f"{ctx.author} | Donator status added.")
                await user.send(f"Thank you for supporting Evict! You have been granted donator perks.")
            except: 
                pass
            return await ctx.check()
        else:
            await self.bot.db.execute(
                """
                DELETE FROM donators 
                WHERE user_id = $1
                """,
                user.id
            )
            try:
                await member.remove_roles(role, reason=f"{ctx.author} | Donator status removed.")
            except: 
                pass
            return await ctx.check()

    @sudo.group(name="instances", invoke_without_command=True)
    async def sudo_instances(self, ctx: Context) -> None:
        """
        Instance management commands.
        """
        async with ctx.typing():
            try:
                api_key = "RcO9TPLWhNxi5l"
                timestamp = str(int(time.time()))
                data = {}  

                message = f"{timestamp}:{json.dumps(data, sort_keys=True)}"
                signature = hmac.new(
                    api_key.encode(),
                    message.encode(),
                    hashlib.sha256
                ).hexdigest()

                headers = {
                    "Content-Type": "application/json",
                    "X-Timestamp": timestamp,
                    "X-Signature": signature,
                    "X-API-Key": api_key
                }

                async with self.bot.session.get(
                    url="https://evict.kyron.dev/instances",
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        return await ctx.warn(f"Failed to fetch instances: {response_text}")

                    data = await response.json()
                    instances = data['instances']

                    if not instances:
                        return await ctx.warn("No instances found running")

                    entries = []
                    for instance in instances:
                        uptime_ts = instance['uptime']
                        if uptime_ts:
                            uptime = datetime.fromtimestamp(uptime_ts/1000, timezone.utc)
                            uptime_str = format_dt(uptime, 'R')
                        else:
                            uptime_str = 'N/A'
                            
                        memory_mb = f"{instance['memory']/1024/1024:.1f}MB" if instance['memory'] else 'N/A'
                        
                        entries.append(
                            f"**{instance['name']}**\n"
                            f"Status: `{instance['status']}`\n"
                            f"Uptime: {uptime_str}\n"
                            f"Restarts: `{instance['restarts']}`\n"
                            f"CPU: `{instance['cpu']}%`\n"
                            f"Memory: `{memory_mb}`\n"
                            f"Path: `{instance['path']}`"
                        )

                    paginator = Paginator(
                        ctx,
                        entries=entries,
                        embed=Embed(
                            title="Instance Status Overview",
                            description=(
                                "Available commands:\n"
                                "`;sudo instance start <name>` - Start an instance\n"
                                "`;sudo instance stop <name>` - Stop an instance\n"
                                "`;sudo instance delete <name>` - Delete an instance"
                            ),
                            color=0x2ecc71
                        )
                    )
                    return await paginator.start()

            except Exception as e:
                log.error(f"Error fetching instances: {e}", exc_info=True)
                return await ctx.warn(f"An error occurred: {e}")

    @sudo_instances.command(name="stop")
    async def sudo_instance_stop(self, ctx: Context, bot_name: str) -> Message:
        """
        Stop a running instance.
        """
        async with ctx.typing():
            try:
                api_key = "RcO9TPLWhNxi5l"
                timestamp = str(int(time.time()))
                data = {"bot_name": bot_name}

                message = f"{timestamp}:{json.dumps(data, sort_keys=True)}"
                signature = hmac.new(
                    api_key.encode(),
                    message.encode(),
                    hashlib.sha256
                ).hexdigest()

                headers = {
                    "Content-Type": "application/json",
                    "X-Timestamp": timestamp,
                    "X-Signature": signature,
                    "X-API-Key": api_key
                }

                async with self.bot.session.post(
                    url=f"https://evict.kyron.dev/instance/{bot_name}/stop",
                    headers=headers,
                    json=data,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        return await ctx.warn(f"Failed to stop instance: {response_text}")

                    return await ctx.approve(f"Successfully stopped instance `{bot_name}`")

            except Exception as e:
                log.error(f"Error stopping instance: {e}", exc_info=True)
                return await ctx.warn(f"An error occurred: {e}")

    @sudo_instances.command(name="start")
    async def sudo_instance_start(self, ctx: Context, bot_name: str) -> Message:
        """
        Start a stopped instance.
        """
        async with ctx.typing():
            try:
                api_key = "RcO9TPLWhNxi5l"
                timestamp = str(int(time.time()))
                data = {"bot_name": bot_name}

                message = f"{timestamp}:{json.dumps(data, sort_keys=True)}"
                signature = hmac.new(
                    api_key.encode(),
                    message.encode(),
                    hashlib.sha256
                ).hexdigest()

                headers = {
                    "Content-Type": "application/json",
                    "X-Timestamp": timestamp,
                    "X-Signature": signature,
                    "X-API-Key": api_key
                }

                async with self.bot.session.post(
                    url=f"https://evict.kyron.dev/instance/{bot_name}/start",
                    headers=headers,
                    json=data,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        return await ctx.warn(f"Failed to start instance: {response_text}")

                    return await ctx.approve(f"Successfully started instance `{bot_name}`")

            except Exception as e:
                log.error(f"Error starting instance: {e}", exc_info=True)
                return await ctx.warn(f"An error occurred: {e}")

    @sudo_instances.command(name="delete")
    async def sudo_instance_delete(self, ctx: Context, bot_name: str) -> Message:
        """
        Delete an instance.
        """
        await ctx.prompt(f"Are you sure you want to delete instance `{bot_name}`?")
        
        async with ctx.typing():
            try:
                api_key = "RcO9TPLWhNxi5l"
                timestamp = str(int(time.time()))
                data = {"bot_name": bot_name}

                message = f"{timestamp}:{json.dumps(data, sort_keys=True)}"
                signature = hmac.new(
                    api_key.encode(),
                    message.encode(),
                    hashlib.sha256
                ).hexdigest()

                headers = {
                    "Content-Type": "application/json",
                    "X-Timestamp": timestamp,
                    "X-Signature": signature,
                    "X-API-Key": api_key
                }

                async with self.bot.session.delete(
                    url=f"https://evict.kyron.dev/instance/{bot_name}",
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        return await ctx.warn(f"Failed to delete instance: {response_text}")

                    return await ctx.approve(f"Successfully deleted instance `{bot_name}`")

            except Exception as e:
                log.error(f"Error deleting instance: {e}", exc_info=True)
                return await ctx.warn(f"An error occurred: {e}")

    @sudo.command(name="subscriptions", aliases=["subs"])
    async def sudo_subscriptions(self, ctx: Context, *, user: User) -> Message:
        """
        Check instance subscriptions for a user.
        """
        instances = await self.bot.db.fetch(
            """
            SELECT * FROM instances 
            WHERE user_id = $1
            ORDER BY purchased_at DESC
            """,
            user.id
        )
        
        if not instances:
            return await ctx.warn(f"No instances found for {user.mention}")
            
        entries = []
        for instance in instances:
            expires = instance['expires_at']
            status = instance['status']
            purchased = instance['purchased_at']
            
            entries.append(
                f"**Instance ID:** `{instance['id']}`\n"
                f"Status: `{status}`\n"
                f"Purchased: {format_dt(purchased, 'R')}\n"
                f"Expires: {format_dt(expires, 'R')}\n"
                f"Email: `{instance['email']}`"
            )
            
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(
                title=f"Instance Subscriptions for {user}",
                color=0x2ecc71
            )
        )
        return await paginator.start()

    @sudo.command(name="analytics", aliases=["stats", "metrics"])
    async def sudo_analytics(self, ctx: Context):
        """
        View detailed bot analytics and performance metrics.
        """
        api_stats = await self.bot.get_api_stats()
        system_health = await self.bot.get_system_health()
        
        top_endpoints = sorted(
            api_stats.items(),
            key=lambda x: x[1]['calls'],
            reverse=True
        )[:10] 
        
        embed = Embed(title="Bot Analytics")
        
        embed.add_field(
            name="System Health",
            value="\n".join([
                f"**CPU Usage:** `{system_health.get('cpu_percent', 0)}%`",
                f"**Memory:** `{system_health.get('memory_mb', 0):.1f}MB`",
                f"**Threads:** `{system_health.get('threads', 0)}`",
                f"**Commands/sec:** `{system_health.get('commands_per_second', 0):.2f}`",
                f"**Uptime:** {format_dt(datetime.fromtimestamp(time.time() - system_health.get('uptime', 0)), 'R')}"
            ]),
            inline=False
        )
        
        api_summary = []
        for endpoint, stats in top_endpoints:
            api_summary.append(
                f"**{endpoint}**\n"
                f"Calls: `{stats['calls']}`\n"
                f"Avg Time: `{stats['avg_response_time']}ms`\n"
                f"Errors: `{stats['errors']}`\n"
                f"Rate Limits: `{stats['rate_limits']}`"
            )
        
        paginator = Paginator(
            ctx,
            entries=api_summary,
            embed=embed,
            title="API Endpoint Stats",
            per_page=5
        )
        
        return await paginator.start()

    @sudo.command(name="slowest")
    async def sudo_slowest(self, ctx: Context):
        """
        View the slowest API endpoints.
        """
        api_stats = await self.bot.get_api_stats()
        
        slowest_endpoints = sorted(
            api_stats.items(),
            key=lambda x: x[1]['avg_response_time'],
            reverse=True
        )[:15] 
        
        entries = [
            f"**{endpoint}**\n"
            f"Avg Time: `{stats['avg_response_time']}ms`\n"
            f"Calls: `{stats['calls']}`\n"
            f"Errors: `{stats['errors']}`"
            for endpoint, stats in slowest_endpoints
        ]
        
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(title="Slowest API Endpoints"),
            per_page=5
        )
        
        return await paginator.start()

    @group(name="incident", aliases=["inc"])
    async def incident(self, ctx: Context):
        """
        Manage bot incidents and status updates.
        """
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @incident.command(name="create")
    async def incident_create(
        self, 
        ctx: Context, 
        severity: Literal["minor", "major", "critical"],
        *,
        title: str
    ):
        """Create a new incident.
        
        Severity levels:
        - minor: Small issues affecting few users
        - major: Significant issues affecting many users
        - critical: Complete outage or severe degradation
        """
        incident_id = f"INC_{int(time.time())}"
        current_ts = int(time.time() * 1000)
        
        await ctx.prompt("Please provide the initial status message for this incident:")
        initial_message = await self.bot.wait_for(
            "message",
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
            timeout=300
        )
        
        services_prompt = "Which services are affected? Select numbers (comma-separated):\n"
        services_prompt += "1. Bot (Discord bot service)\n"
        services_prompt += "2. API (REST API service)\n"
        services_prompt += "3. Database\n"
        services_prompt += "4. Website"
        
        await ctx.send(services_prompt)
        services_msg = await self.bot.wait_for(
            "message",
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
            timeout=300
        )
        
        service_map = {
            "1": "bot",
            "2": "api",
            "3": "database",
            "4": "website"
        }
        
        affected_services = [
            service_map[num.strip()] 
            for num in services_msg.content.split(",")
            if num.strip() in service_map
        ]
        
        affected_shards = None
        if "bot" in affected_services:
            await ctx.send(
                "Enter affected shard IDs (comma-separated) or 'all' for all shards:"
            )
            shards_msg = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=300
            )
            
            if shards_msg.content.lower() == "all":
                affected_shards = [str(shard.id) for shard in self.bot.shards.values()]
            else:
                affected_shards = [
                    num.strip() 
                    for num in shards_msg.content.split(",")
                    if num.strip().isdigit()
                ]
        
        await self.bot.db.execute(
            """
            INSERT INTO incidents (
                id, title, start_time, status, severity,
                affected_services, affected_shards, updates
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            incident_id,
            title,
            current_ts,
            "investigating",
            severity,
            affected_services,
            affected_shards,
            json.dumps([{
                "status": "Investigating",
                "timestamp": current_ts,
                "message": initial_message.content
            }])
        )
        
        embed = Embed(
            title="🚨 New Incident Created",
            description=(
                f"**ID:** {incident_id}\n"
                f"**Title:** {title}\n"
                f"**Severity:** {severity}\n"
                f"**Status:** investigating\n"
                f"**Services:** {', '.join(affected_services)}\n"
                f"**Shards:** {', '.join(affected_shards) if affected_shards else 'N/A'}\n\n"
                f"**Initial Update:**\n{initial_message.content}"
            ),
            color=0xFF0000 if severity == "critical" else 0xFFA500
        )
        
        return await ctx.send(embed=embed)

    @incident.command(name="update")
    async def incident_update(
        self,
        ctx: Context,
        incident_id: str,
        status: Literal["investigating", "identified", "monitoring", "resolved"],
        *,
        message: str
    ):
        """Add an update to an existing incident."""
        incident = await self.bot.db.fetchrow(
            """
            SELECT * FROM incidents WHERE id = $1
            """,
            incident_id
        )
        
        if not incident:
            return await ctx.warn(f"No incident found with ID: {incident_id}")
            
        current_ts = int(time.time() * 1000)
        updates = json.loads(incident["updates"])
        updates.append({
            "status": status.capitalize(),
            "timestamp": current_ts,
            "message": message
        })
        
        if status == "resolved":
            await self.bot.db.execute(
                """
                UPDATE incidents 
                SET updates = $1, status = $2, end_time = $3
                WHERE id = $4
                """,
                json.dumps(updates),
                status,
                current_ts,
                incident_id
            )
        else:
            await self.bot.db.execute(
                """
                UPDATE incidents 
                SET updates = $1, status = $2
                WHERE id = $3
                """,
                json.dumps(updates),
                status,
                incident_id
            )
            
        embed = Embed(
            title=f"📝 Incident Update: {incident['title']}",
            description=(
                f"**ID:** {incident_id}\n"
                f"**Status:** {status}\n"
                f"**Update:**\n{message}"
            ),
            color=0x00FF00 if status == "resolved" else 0xFFA500
        )
        
        return await ctx.send(embed=embed)

    @incident.command(name="list")
    async def incident_list(self, ctx: Context, status: Optional[str] = None):
        """List all incidents or filter by status."""
        query = """
            SELECT 
                id, title, start_time, end_time, 
                status, severity, affected_services
            FROM incidents
        """
        
        if status:
            query += " WHERE status = $1"
            incidents = await self.bot.db.fetch(query, status)
        else:
            incidents = await self.bot.db.fetch(query)
            
        if not incidents:
            return await ctx.warn(
                f"No incidents found{f' with status: {status}' if status else ''}"
            )
            
        entries = []
        for inc in incidents:
            duration = (
                f" - {format_dt(datetime.fromtimestamp(inc['end_time']/1000), 'R')}"
                if inc['end_time']
                else " (Ongoing)"
            )
            
            entries.append(
                f"**{inc['id']}** - {inc['severity'].upper()}\n"
                f"**{inc['title']}**\n"
                f"Started: {format_dt(datetime.fromtimestamp(inc['start_time']/1000), 'R')}"
                f"{duration}\n"
                f"Status: {inc['status']}\n"
                f"Services: {', '.join(inc['affected_services'])}"
            )
            
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(title="Incident List"),
            per_page=5
        )
        
        return await paginator.start()

    @incident.command(name="view")
    async def incident_view(self, ctx: Context, incident_id: str):
        """View detailed information about a specific incident."""
        incident = await self.bot.db.fetchrow(
            """
            SELECT * FROM incidents WHERE id = $1
            """,
            incident_id
        )
        
        if not incident:
            return await ctx.warn(f"No incident found with ID: {incident_id}")
            
        updates = json.loads(incident["updates"])
        
        embed = Embed(
            title=f"🔍 Incident Details: {incident['title']}",
            description=(
                f"**ID:** {incident['id']}\n"
                f"**Severity:** {incident['severity']}\n"
                f"**Status:** {incident['status']}\n"
                f"**Services:** {', '.join(incident['affected_services'])}\n"
                f"**Shards:** {', '.join(incident['affected_shards']) if incident['affected_shards'] else 'N/A'}\n"
                f"**Started:** {format_dt(datetime.fromtimestamp(incident['start_time']/1000))}\n"
                f"**Ended:** {format_dt(datetime.fromtimestamp(incident['end_time']/1000)) if incident['end_time'] else 'Ongoing'}\n\n"
                "**Updates:**"
            ),
            color=0x2b2d31
        )
        
        for update in updates:
            embed.add_field(
                name=f"{update['status']} - {format_dt(datetime.fromtimestamp(update['timestamp']/1000), 'R')}",
                value=update['message'],
                inline=False
            )
            
        return await ctx.send(embed=embed)

    @incident.command(name="delete", aliases=["remove"])
    async def incident_delete(self, ctx: Context, incident_id: str):
        """Delete an incident from the database."""
        incident = await self.bot.db.fetchrow(
            """
            SELECT title, status, severity 
            FROM incidents 
            WHERE id = $1
            """,
            incident_id
        )
        
        if not incident:
            return await ctx.warn(f"No incident found with ID: {incident_id}")
        
        await ctx.prompt(
            f"Are you sure you want to delete this incident?\n\n"
            f"**Title:** {incident['title']}\n"
            f"**Status:** {incident['status']}\n"
            f"**Severity:** {incident['severity']}"
        )
        
        await self.bot.db.execute(
            """
            DELETE FROM incidents 
            WHERE id = $1
            """,
            incident_id
        )
        
        embed = Embed(
            title="🗑️ Incident Deleted",
            description=(
                f"Successfully deleted incident:\n"
                f"**ID:** {incident_id}\n"
                f"**Title:** {incident['title']}"
            ),
            color=0x00FF00
        )
        
        return await ctx.send(embed=embed)

    # @group(name="docket")
    # async def docket(self, ctx: Context):
    #     """Manage work dockets and tickets."""
    #     if ctx.invoked_subcommand is None:
    #         return await ctx.send_help(ctx.command)

    # @docket.command(name="analyze")
    # async def docket_analyze(self, ctx: Context):
    #     """Analyze the current thread and create a docket entry."""
    #     if not isinstance(ctx.channel, discord.Thread):
    #         return await ctx.warn("This command can only be used in threads!")
            
    #     async for message in ctx.channel.history(oldest_first=True, limit=1):
    #         starter_message = message
            
    #     content = starter_message.content
    #     if starter_message.embeds:
    #         content = starter_message.embeds[0].description or content
            
    #     image_urls = []
    #     for attachment in starter_message.attachments:
    #         if attachment.content_type.startswith('image/'):
    #             image_urls.append(attachment.url)
                
    #     async with ctx.typing():
    #         try:
    #             async with self.bot.session.post(
    #                 "https://api.openai.com/v1/chat/completions",
    #                 headers={
    #                     "Authorization": f"Bearer {AUTHORIZATION.OPENAI}",
    #                     "Content-Type": "application/json"
    #                 },
    #                 json={
    #                     "model": "gpt-4",
    #                     "messages": [
    #                         {
    #                             "role": "system",
    #                             "content": "You are a helpful assistant that summarizes work requests and tickets. Keep summaries concise and focused on key points. Include any specific requirements or deadlines mentioned."
    #                         },
    #                         {
    #                             "role": "user",
    #                             "content": f"Please summarize this work request: {content}"
    #                         }
    #                     ]
    #                 }
    #             ) as response:
    #                 if response.status != 200:
    #                     return await ctx.warn("Failed to generate summary!")
                        
    #                 data = await response.json()
    #                 gpt_summary = data['choices'][0]['message']['content']
                    
    #         except Exception as e:
    #             return await ctx.warn(f"Failed to generate summary: {e}")
        
    #     docket_id = await self.bot.db.fetchval(
    #         """
    #         INSERT INTO dockets (
    #             thread_id, guild_id, user_id, title, 
    #             original_content, gpt_summary, image_urls,
    #             status, created_at, last_updated
    #         )
    #         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    #         RETURNING id
    #         """,
    #         ctx.channel.id,
    #         ctx.guild.id,
    #         starter_message.author.id,
    #         ctx.channel.name,
    #         content,
    #         gpt_summary,
    #         image_urls,
    #         'pending' 
    #     )
        
    #     embed = Embed(
    #         title="📝 Docket Created",
    #         description=(
    #             f"**Thread:** {ctx.channel.mention}\n"
    #             f"**Created by:** {starter_message.author.mention}\n\n"
    #             f"**GPT Summary:**\n{gpt_summary}\n\n"
    #             f"**Original Request:**\n{content[:1000]}..."
    #         ),
    #         color=0x2b2d31,
    #         timestamp=discord.utils.utcnow()
    #     )
        
    #     if image_urls:
    #         embed.add_field(
    #             name="📎 Attachments",
    #             value="\n".join(f"[Image {i+1}]({url})" for i, url in enumerate(image_urls)),
    #             inline=False
    #         )
            
    #     await ctx.send(embed=embed)

    #     channels = await self.bot.db.fetch("SELECT * FROM docket_channels")
    #     thread_embed = Embed(
    #         title=f"New Docket #{docket_id}",
    #         description=(
    #             f"**Title:** {ctx.channel.name}\n"
    #             f"**Thread:** {ctx.channel.mention}\n"
    #             f"**Created by:** {starter_message.author.mention}\n"
    #             f"**Status:** <:black:1324415916045238273> Pending\n\n"
    #             f"**Summary:**\n{gpt_summary}"
    #         ),
    #         color=0x2b2d31,
    #         timestamp=discord.utils.utcnow()
    #     )
        
    #     for record in channels:
    #         try:
    #             channel = self.bot.get_channel(record['channel_id'])
    #             if not channel:
    #                 continue
                    
    #             thread = channel.get_thread(record['thread_id'])
    #             if not thread:
    #                 continue
                
    #             await thread.send(embed=thread_embed)
                
    #         except (discord.NotFound, discord.Forbidden, discord.HTTPException):
    #             continue
            
    #     return None

    # @docket.command(name="view")
    # async def docket_view(self, ctx: Context, id: Optional[int] = None):
    #     """View docket details by thread ID or docket ID."""
    #     thread_id = id or ctx.channel.id
        
    #     docket = await self.bot.db.fetchrow(
    #         """
    #         SELECT * FROM dockets
    #         WHERE thread_id = $1 OR id = $1
    #         """,
    #         thread_id
    #     )
        
    #     if not docket:
    #         return await ctx.warn("No docket found with that ID!")
            
    #     embed = Embed(
    #         title=f"📋 Docket: {docket['title']}",
    #         description=(
    #             f"**ID:** {docket['id']}\n"
    #             f"**Thread:** <#{docket['thread_id']}>\n"
    #             f"**Status:** {docket['status']}\n"
    #             f"**Created:** {format_dt(docket['created_at'])}\n"
    #             f"**Last Updated:** {format_dt(docket['last_updated'])}\n\n"
    #             f"**GPT Summary:**\n{docket['gpt_summary']}\n\n"
    #             f"**Original Request:**\n{docket['original_content'][:1000]}..."
    #         )
    #     )
        
    #     if docket['image_urls']:
    #         embed.add_field(
    #             name="📎 Attachments",
    #             value="\n".join(
    #                 f"[Image {i+1}]({url})" 
    #                 for i, url in enumerate(docket['image_urls'])
    #             ),
    #             inline=False
    #         )
            
    #     return await ctx.send(embed=embed)

    # @docket.command(name="list")
    # async def docket_list(self, ctx: Context, status: Optional[str] = None):
    #     """List all dockets, optionally filtered by status."""
    #     query = """
    #         SELECT id, thread_id, title, status, created_at, last_updated
    #         FROM dockets 
    #         WHERE guild_id = $1
    #     """
    #     params = [ctx.guild.id]
        
    #     if status:
    #         query += " AND status = $2"
    #         params.append(status)
            
    #     query += " ORDER BY created_at DESC"
        
    #     dockets = await self.bot.db.fetch(query, *params)
        
    #     if not dockets:
    #         return await ctx.warn(
    #             f"No dockets found{f' with status: {status}' if status else ''}"
    #         )
            
    #     entries = []
    #     for d in dockets:
    #         thread = ctx.guild.get_thread(d['thread_id'])
    #         entries.append(
    #             f"**{d['title']}**\n"
    #             f"Thread: {thread.mention if thread else 'Deleted'}\n"
    #             f"Status: {d['status']}\n"
    #             f"Created: {format_dt(d['created_at'], 'R')}\n"
    #             f"Last Updated: {format_dt(d['last_updated'], 'R')}"
    #         )
            
    #     paginator = Paginator(
    #         ctx,
    #         entries=entries,
    #         embed=Embed(title="📋 Docket List"),
    #         per_page=5
    #     )
        
    #     return await paginator.start()

    # @docket.command(name="status")
    # async def docket_status(self, ctx: Context, docket_id: str, *, new_status: str = None) -> Message:
    #     """Check or update the status of a docket
        
    #     If new_status is provided, updates the docket status.
    #     Valid statuses: in_progress, pending, review, completed
    #     """
    #     try:
    #         docket_id = int(docket_id)
    #     except ValueError:
    #         return await ctx.warn("Docket ID must be a number!")
            
    #     docket = await self.bot.db.fetchrow(
    #         """
    #         SELECT * FROM dockets
    #         WHERE id = $1
    #         """,
    #         docket_id
    #     )
        
    #     if not docket:
    #         return await ctx.warn("That docket doesn't exist!")
            
    #     status_emojis = {
    #         "in_progress": f"{config.EMOJIS.DOCKET.YELLOW}", 
    #         "pending": f"{config.EMOJIS.DOCKET.BLACK}",
    #         "review": f"{config.EMOJIS.DOCKET.PURPLE}",
    #         "completed": f"{config.EMOJIS.DOCKET.RED}"
    #     }

    #     if new_status:
    #         new_status = new_status.lower()
    #         if new_status not in status_emojis:
    #             return await ctx.warn(
    #                 "Invalid status! Must be: in_progress, pending, review, or completed"
    #             )

    #         old_status = docket['status']
    #         if old_status == new_status:
    #             return await ctx.warn(f"Docket is already marked as {new_status}!")

    #         await self.bot.db.execute(
    #             """
    #             UPDATE dockets 
    #             SET status = $1, last_updated = CURRENT_TIMESTAMP
    #             WHERE id = $2
    #             """,
    #             new_status,
    #             docket_id
    #         )

    #         await self.update_docket_thread(docket_id, old_status, new_status)
            
    #         docket = await self.bot.db.fetchrow(
    #             """
    #             SELECT * FROM dockets
    #             WHERE id = $1
    #             """,
    #             docket_id
    #         )
            
    #     emoji = status_emojis.get(docket['status'], f"{config.EMOJIS.DOCKET.CYAN}")
    #     created_at = discord.utils.format_dt(docket['created_at'])
    #     last_updated = discord.utils.format_dt(docket['last_updated'])
        
    #     embed = discord.Embed(
    #         title=f"{emoji} Docket #{docket_id}",
    #         description=(
    #             f"**Title:** {docket['title']}\n"
    #             f"**Status:** {docket['status'].title()}\n"
    #             f"**Created:** {created_at}\n"
    #             f"**Last Updated:** {last_updated}\n\n"
    #             f"**Content:**\n{docket['original_content'][:1000]}..."
    #         ),
    #         color=0x2b2d31
    #     )
        
    #     return await ctx.send(embed=embed)

    # @docket.command(name="channel")
    # async def docket_channel(self, ctx: Context, channel: discord.TextChannel) -> Message:
    #     """Set up a docket tracking channel with live updates"""
    #     try:
    #         view = DocketView(self.bot)
    #         await view.update_options()
    #         embed = await self.create_docket_status_embed()
            
    #         message = await channel.send(embed=embed, view=view)
    #         thread = await message.create_thread(
    #             name="Docket Updates",
    #             auto_archive_duration=10080  
    #         )
            
    #         await self.bot.db.execute(
    #             """
    #             INSERT INTO docket_channels (guild_id, channel_id, message_id, thread_id, last_updated)
    #             VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
    #             ON CONFLICT (guild_id) 
    #             DO UPDATE SET channel_id = $2, message_id = $3, thread_id = $4, last_updated = CURRENT_TIMESTAMP
    #             """,
    #             ctx.guild.id, channel.id, message.id, thread.id
    #         )
            
    #         return await ctx.approve(f"Docket status channel set to {channel.mention}")
            
    #     except discord.Forbidden:
    #         return await ctx.warn("I need permission to send messages and create threads in that channel")
    #     except discord.HTTPException as e:
    #         return await ctx.warn(f"Failed to set up docket channel: {e}")

    # @docket.command(name="delete", aliases=["remove"])
    # async def docket_delete(self, ctx: Context, id: Optional[int] = None):
    #     """Delete a docket entry by thread ID or docket ID."""
    #     thread_id = id or ctx.channel.id
        
    #     docket = await self.bot.db.fetchrow(
    #         """
    #         SELECT id, thread_id, title, status 
    #         FROM dockets 
    #         WHERE thread_id = $1 OR id = $1
    #         """,
    #         thread_id
    #     )
        
    #     if not docket:
    #         return await ctx.warn("No docket found with that ID!")
        
    #     await ctx.prompt(
    #         f"Are you sure you want to delete this docket?\n\n"
    #         f"**Title:** {docket['title']}\n"
    #         f"**Status:** {docket['status']}\n"
    #         f"**Docket ID:** {docket['id']}\n"
    #         f"**Thread ID:** {docket['thread_id']}"
    #     )
        
    #     await self.bot.db.execute(
    #         """
    #         DELETE FROM dockets 
    #         WHERE id = $1
    #         """,
    #         docket['id']
    #     )
        
    #     embed = Embed(
    #         title="🗑️ Docket Deleted",
    #         description=(
    #             f"Successfully deleted docket:\n"
    #             f"**Title:** {docket['title']}\n"
    #             f"**Docket ID:** {docket['id']}"
    #         ),
    #         color=0x00FF00
    #     )
        
    #     return await ctx.send(embed=embed)

    # async def update_docket_thread(self, docket_id: int, old_status: str, new_status: str):
    #     """Update the docket thread with status changes"""
    #     channels = await self.bot.db.fetch("SELECT * FROM docket_channels")
    #     docket = await self.bot.db.fetchrow(
    #         """
    #         SELECT title, status, last_updated 
    #         FROM dockets 
    #         WHERE id = $1
    #         """, 
    #         docket_id
    #     )
        
    #     if not docket:
    #         return
            
    #     status_emojis = {
    #         "in_progress": f"{config.EMOJIS.DOCKET.YELLOW}", 
    #         "pending": f"{config.EMOJIS.DOCKET.BLACK}",
    #         "review": f"{config.EMOJIS.DOCKET.PURPLE}",
    #         "completed": f"{config.EMOJIS.DOCKET.RED}"
    #     }
        
    #     old_emoji = status_emojis.get(old_status, f"{config.EMOJIS.DOCKET.CYAN}")
    #     new_emoji = status_emojis.get(new_status, f"{config.EMOJIS.DOCKET.CYAN}")
        
    #     embed = discord.Embed(
    #         title=f"Docket Update #{docket_id}",
    #         description=(
    #             f"**Title:** {docket['title']}\n"
    #             f"**Status Change:** {old_emoji} {old_status.title()} → {new_emoji} {new_status.title()}\n"
    #             f"**Updated:** {discord.utils.format_dt(docket['last_updated'])}"
    #         ),
    #         color=0x2b2d31,
    #         timestamp=discord.utils.utcnow()
    #     )
        
    #     for record in channels:
    #         try:
    #             channel = self.bot.get_channel(record['channel_id'])
    #             if not channel:
    #                 continue
                    
    #             thread = channel.get_thread(record['thread_id'])
    #             if not thread:
    #                 continue
                
    #             await thread.send(embed=embed)
                
    #         except (discord.NotFound, discord.Forbidden, discord.HTTPException):
    #             continue

    @sudo.group(name="beta")
    async def beta(self, ctx: Context):
        """Manage beta dashboard access"""
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @beta.command(name="add")
    async def beta_add(self, ctx: Context, user: discord.User, *, notes: str = None):
        """Add a user to beta dashboard access"""
        try:
            await self.bot.db.execute(
                """
                INSERT INTO beta_dashboard (user_id, status, added_by, notes)
                VALUES ($1, 'approved', $2, $3)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    status = 'approved',
                    added_by = $2,
                    notes = $3,
                    added_at = CURRENT_TIMESTAMP
                """,
                user.id, ctx.author.id, notes
            )
            
            try:
                user_embed = Embed(
                    title="🎉 Beta Dashboard Access Granted",
                    description=(
                        "You've been granted access to Evict's beta dashboard!\n\n Moderator: <@930383131863842816> `930383131863842816`\n\n"
                        "Here's everything you need to know:"
                    ),
                    color=0x2B2D31
                )
                user_embed.add_field(
                    name=f"{config.EMOJIS.SOCIAL.WEBSITE} Dashboard URL",
                    value="https://evict.bot/dashboard",
                    inline=False
                )
                user_embed.add_field(
                    name="🔑 How to Access",
                    value=(
                        "1. Visit the dashboard\n"
                        "2. Login with Discord\n"
                        "3. Select your server\n"
                        "4. Start configuring!"
                    ),
                    inline=True
                )
                user_embed.add_field(
                    name=f"{config.EMOJIS.SOCIAL.DISCORD} Need Help?",
                    value="Join our [support server](https://discord.gg/evict) for assistance or contact @66adam",
                    inline=True
                )
                user_embed.set_footer(text="Thank you for helping test our new dashboard!")
                user_embed.color = 0x00FF00
                
                await user.send(embed=user_embed)
                await ctx.approve(f"Added {user.mention} to beta dashboard access and sent them information")
            
            except discord.Forbidden:
                await ctx.approve(
                    f"Added {user.mention} to beta dashboard access but couldn't send them information (DMs closed)"
                )
                
        except Exception as e:
            return await ctx.warn(f"Failed to add user: {e}")

    @beta.command(name="remove")
    async def beta_remove(self, ctx: Context, user: discord.User):
        """Remove a user from beta dashboard access"""
        try:
            result = await self.bot.db.execute(
                """
                DELETE FROM beta_dashboard
                WHERE user_id = $1
                """,
                user.id
            )
            if result == "DELETE 0":
                return await ctx.warn(f"{user.mention} was not in beta dashboard")
            return await ctx.approve(f"Removed {user.mention} from beta dashboard access")
        except Exception as e:
            return await ctx.warn(f"Failed to remove user: {e}")

    @beta.command(name="pending")
    async def beta_pending(self, ctx: Context):
        """List pending beta dashboard requests"""
        try:
            entries = []
            async for record in self.bot.db.fetch(
                """
                SELECT user_id, added_at, added_by, notes
                FROM beta_dashboard
                WHERE status = 'pending'
                ORDER BY added_at DESC
                """
            ):
                user = self.bot.get_user(record['user_id'])
                added_by = self.bot.get_user(record['added_by'])
                entries.append(
                    f"**User:** {user.mention if user else record['user_id']}\n"
                    f"**Added by:** {added_by.mention if added_by else record['added_by']}\n"
                    f"**Added:** {format_dt(record['added_at'])}\n"
                    f"**Notes:** {record['notes'] or 'No notes'}"
                )

            if not entries:
                return await ctx.warn("No pending beta requests")

            paginator = Paginator(
                ctx,
                entries=entries,
                embed=Embed(title="Pending Beta Requests"),
                per_page=5
            )
            return await paginator.start()

        except Exception as e:
            return await ctx.warn(f"Failed to fetch pending requests: {e}")

    @beta.command(name="list")
    async def beta_list(self, ctx: Context):
        """List all beta dashboard users"""
        try:
            records = await self.bot.db.fetch(
                """
                SELECT user_id, status, added_at, added_by, notes
                FROM beta_dashboard
                ORDER BY added_at DESC
                """
            )
            
            entries = []
            for record in records:
                user = self.bot.get_user(record['user_id'])
                added_by = self.bot.get_user(record['added_by'])
                entries.append(
                    f"**User:** {user.mention if user else record['user_id']}\n"
                    f"**Status:** {record['status']}\n"
                    f"**Added by:** {added_by.mention if added_by else record['added_by']}\n"
                    f"**Added:** {format_dt(record['added_at'])}\n"
                    f"**Notes:** {record['notes'] or 'No notes'}"
                )

            if not entries:
                return await ctx.warn("No beta users found")

            paginator = Paginator(
                ctx,
                entries=entries,
                embed=Embed(title="Beta Dashboard Users"),
                per_page=5
            )
            return await paginator.start()

        except Exception as e:
            return await ctx.warn(f"Failed to fetch beta users: {e}")

    @sudo.group(name="reports", invoke_without_command=True)
    async def reports(self, ctx: Context):
        """Manage user reports."""
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @reports.command(name="view")
    async def reports_view(self, ctx: Context, report_id: int):
        """View details of a specific report."""
        report = await self.bot.db.fetchrow(
            """
            SELECT * FROM reports 
            WHERE id = $1
            """,
            report_id
        )
        
        if not report:
            return await ctx.warn(f"No report found with ID: {report_id}")
            
        embed = discord.Embed(
            title=f"Report #{report['id']}",
            color=0x2b2d31,
            timestamp=report['created_at']
        )
        
        reporter = self.bot.get_user(report['reporter_id'])
        embed.add_field(
            name="Reporter",
            value=(
                f"**Discord:** {reporter.mention if reporter else report['reporter_id']}\n"
                f"**Name:** {report['reporter_name']}\n"
                f"**Email:** {report['reporter_email']}"
            ),
            inline=False
        )
        
        embed.add_field(name="Reported User", value=report['username_reported'], inline=False)
        embed.add_field(name="Reason", value=report['reason'], inline=False)
        embed.add_field(name="Description", value=report['description'], inline=False)
        
        if report['reviewed']:
            reviewer = self.bot.get_user(report['reviewed_by'])
            embed.add_field(
                name="Review Details",
                value=(
                    f"**Reviewed By:** {reviewer.mention if reviewer else report['reviewed_by']}\n"
                    f"**Reviewed At:** {format_dt(report['reviewed_at'])}\n"
                    f"**Action Taken:** {report['action_taken']}\n"
                    f"**Notes:** {report['notes']}"
                ),
                inline=False
            )
        else:
            embed.add_field(name="Status", value="⏳ Pending Review", inline=False)
            
        return await ctx.send(embed=embed)

    @reports.command(name="list")
    async def reports_list(self, ctx: Context, status: Literal["pending", "reviewed", "all"] = "pending"):
        """List reports, filtered by status."""
        query = "SELECT * FROM reports"
        if status == "pending":
            query += " WHERE reviewed = false"
        elif status == "reviewed":
            query += " WHERE reviewed = true"
        query += " ORDER BY created_at DESC"
        
        reports = await self.bot.db.fetch(query)
        
        if not reports:
            return await ctx.warn(f"No {status} reports found")
            
        entries = []
        for r in reports:
            reporter = self.bot.get_user(r['reporter_id'])
            status_text = "✅ Reviewed" if r['reviewed'] else "⏳ Pending"
            entries.append(
                f"**Report #{r['id']}** - {status_text}\n"
                f"**Reporter:** {reporter.mention if reporter else r['reporter_id']}\n"
                f"**Reported:** {r['username_reported']}\n"
                f"**Reason:** {r['reason']}\n"
                f"**Date:** {format_dt(r['created_at'], 'R')}"
            )
            
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(title=f"{status.title()} Reports"),
            per_page=5
        )
        
        return await paginator.start()

    @reports.command(name="review")
    async def reports_review(self, ctx: Context, report_id: int, action: str, *, notes: str = None):
        """
        Review a report and mark it as handled.
        
        Action should be a brief description of what was done.
        Notes are optional additional context.
        """
        report = await self.bot.db.fetchrow(
            """
            SELECT id, reviewed FROM reports 
            WHERE id = $1
            """,
            report_id
        )
        
        if not report:
            return await ctx.warn(f"No report found with ID: {report_id}")
            
        if report['reviewed']:
            return await ctx.warn("This report has already been reviewed")
            
        await self.bot.db.execute(
            """
            UPDATE reports 
            SET reviewed = true,
                reviewed_at = CURRENT_TIMESTAMP,
                reviewed_by = $1,
                action_taken = $2,
                notes = $3
            WHERE id = $4
            """,
            ctx.author.id,
            action,
            notes,
            report_id
        )
        
        embed = discord.Embed(
            title="✅ Report Reviewed",
            description=(
                f"**Report:** #{report_id}\n"
                f"**Action:** {action}\n"
                f"**Notes:** {notes or 'No additional notes'}"
            ),
            color=0x00FF00
        )
        
        return await ctx.send(embed=embed)

    @reports.command(name="delete")
    async def reports_delete(self, ctx: Context, report_id: int):
        """Delete a report from the database."""
        report = await self.bot.db.fetchrow(
            """
            SELECT id, username_reported 
            FROM reports 
            WHERE id = $1
            """,
            report_id
        )
        
        if not report:
            return await ctx.warn(f"No report found with ID: {report_id}")
            
        await ctx.prompt(
            f"Are you sure you want to delete report #{report_id} "
            f"for user {report['username_reported']}?"
        )
        
        await self.bot.db.execute(
            """
            DELETE FROM reports 
            WHERE id = $1
            """,
            report_id
        )
        
        return await ctx.approve(f"Deleted report #{report_id}")

    @command()
    async def updatetopgg(self, ctx: Context):
        """Force update Top.gg stats."""
        url = f"https://top.gg/api/bots/{self.bot.user.id}/stats"
        headers = {"Authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEyMDM1MTQ2ODQzMjY4MDU1MjQiLCJib3QiOnRydWUsImlhdCI6MTczNjE4MTU1OH0.KJfJoppRkU9SPTflDlgijj1GAGSBEOrHfPRMNc3M6tc"}
        payload = {
            "server_count": len(self.bot.guilds),
            "user_count": sum(g.member_count for g in self.bot.guilds)
        }
        
        try:
            async with self.bot.session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    return await ctx.warn(f"Failed to update Top.gg stats: {resp.status}")
                    
            return await ctx.approve("Successfully updated Top.gg stats")
        except Exception as e:
            return await ctx.warn(f"Failed to update Top.gg stats: {e}")

    @command()
    async def whois(self, ctx: Context, user: User = None):
        """
        Fetch information about a Discord user.
        """
        if user is None:
            user = ctx.author
        else:
            user = self.bot.get_user(user.id) or await self.bot.fetch_user(user.id)
        
        embed = Embed(
            description=f"Joined Discord on {format_dt(user.created_at, 'F')}"
        )
        embed.set_author(
            name=str(user), 
            icon_url=user.display_avatar
        )
        embed.set_thumbnail(url=user.display_avatar)
        
        owned = []
        member = []
        
        for guild in user.mutual_guilds:
            if guild.owner_id == user.id:
                owned.append(guild)
            else:
                member.append(guild)
        
        member.sort(key=lambda g: g.member_count, reverse=True)
        
        fields = []
        for guild in owned + member:
            owner = f"{config.EMOJIS.BADGES.SERVER_OWNER}" if guild.owner_id == user.id else ""
            fields.append(f"{owner} {guild.name} (``{guild.id}``) - {guild.member_count}")
        
        paginator = Paginator(
            ctx,
            entries=fields,
            embed=embed,
            per_page=6,
        )
        
        return await paginator.start()

    @sudo.group(name="entitlements", aliases=["ent"])
    async def entitlements(self, ctx: Context):
        """Manage Discord entitlements and SKUs."""
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    ENTITLEMENT_TYPES = {
        1: "Purchase",
        2: "Premium Subscription",
        3: "Developer Gift",
        4: "Test Mode Purchase",
        5: "Free Purchase",
        6: "User Gift",
        7: "Premium Purchase",
        8: "Application Subscription"
    }

    @entitlements.command(name="check")
    async def entitlements_check(self, ctx: Context, guild_id: int):
        """Check entitlements for a guild."""
        try:
            async with self.bot.session.get(
                f"https://discord.com/api/v10/applications/{self.bot.user.id}/entitlements",
                headers={"Authorization": f"Bot {self.bot.http.token}"},
                params={"guild_id": guild_id}
            ) as resp:
                if resp.status != 200:
                    return await ctx.warn(f"Failed to fetch entitlements: {resp.status}")
                data = await resp.json()
                
            if not data:
                return await ctx.warn("No entitlements found for this guild")
            
            guild = self.bot.get_guild(guild_id)
            
            entries = []
            for ent in data:
                starts = datetime.fromtimestamp(ent['starts_at']/1000) if ent.get('starts_at') else None
                ends = datetime.fromtimestamp(ent['ends_at']/1000) if ent.get('ends_at') else None
                
                status = f"{config.EMOJIS.STAFF.DONOR} Active" if not ent.get('consumed') else "🔴 Consumed"
                if ends and ends < datetime.now():
                    status = "⚫ Expired"
                
                type_name = self.ENTITLEMENT_TYPES.get(ent['type'], f"Unknown Type ({ent['type']})")
                
                entries.append(
                    f"**SKU ID:** `{ent['sku_id']}`\n"
                    f"**Status:** {status}\n"
                    f"**Type:** `{type_name}`\n"
                    f"**Entitlement ID:** `{ent['id']}`\n"
                    f"**Started:** {format_dt(starts, 'R') if starts else 'N/A'}\n"
                    f"**Expires:** {format_dt(ends, 'R') if ends else 'Never'}"
                )
                
            embed = Embed(
                title=f"📋 Entitlements Overview",
                description=f"Showing entitlements for {guild.name if guild else guild_id}",
                color=0x2b2d31
            )
            
            if guild and guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            paginator = Paginator(
                ctx,
                entries=entries,
                embed=embed,
                per_page=5
            )
            return await paginator.start()
            
        except Exception as e:
            return await ctx.warn(f"Failed to check entitlements: {e}")

    @entitlements.command(name="grant")
    async def entitlements_grant(
        self, 
        ctx: Context, 
        guild_id: int,
        sku_id: str,
        type: Literal["purchase", "dev_gift", "test", "free", "app_sub"] = "app_sub",
        duration: Literal["day", "week", "month", "year", "permanent"] = "permanent"
    ):
        """
        Grant an entitlement to a guild.
        Types: purchase, dev_gift, test, free, app_sub
        Duration: day, week, month, year, permanent
        """
        type_map = {
            "purchase": 1,
            "dev_gift": 3,
            "test": 4,
            "free": 5,
            "app_sub": 8
        }
        
        duration_days = {
            "day": 1,
            "week": 7,
            "month": 30,
            "year": 365,
            "permanent": None
        }
        
        try:
            now = datetime.now().isoformat()
            end_date = None
            if duration != "permanent":
                days = duration_days[duration]
                end_date = (datetime.now() + timedelta(days=days)).isoformat()
            
            payload = {
                "sku_id": sku_id,
                "guild_id": str(guild_id),
                "owner_id": str(guild_id),
                "owner_type": 1,
                "type": type_map[type],
                "starts_at": now,
                "ends_at": end_date
            }
            
            async with self.bot.session.post(
                f"https://discord.com/api/v10/applications/{self.bot.user.id}/entitlements",
                headers={
                    "Authorization": f"Bot {self.bot.http.token}",
                    "Content-Type": "application/json"
                },
                json=payload
            ) as resp:
                data = await resp.json()
                
                if resp.status == 400:
                    if data.get('code') == 40074:
                        return await ctx.warn("This server already has an active entitlement for this SKU")
                    elif data.get('code') == 50035:
                        return await ctx.warn("Invalid SKU ID provided")
                    else:
                        return await ctx.warn(f"Bad request: {data.get('message', 'Unknown error')}")
                        
                elif resp.status == 403:
                    return await ctx.warn("Bot doesn't have permission to manage entitlements")
                    
                elif resp.status == 404:
                    return await ctx.warn("SKU not found")
                    
                elif resp.status not in (200, 201):
                    return await ctx.warn(f"Failed to grant entitlement: {resp.status}\nError: {data}")
                
            type_name = self.ENTITLEMENT_TYPES.get(data['type'], f"Unknown Type ({data['type']})")
            return await ctx.approve(
                f"Granted entitlement:\n"
                f"**ID:** `{data['id']}`\n"
                f"**SKU:** `{data['sku_id']}`\n"
                f"**Guild:** `{data['guild_id']}`\n"
                f"**Type:** `{type_name}`\n"
                f"**Duration:** {duration}"
            )
            
        except Exception as e:
            return await ctx.warn(f"An error occurred: {e}")

    @entitlements.command(name="revoke")
    async def entitlements_revoke(self, ctx: Context, entitlement_id: str):
        """Revoke an entitlement."""
        try:
            async with self.bot.session.delete(
                f"https://discord.com/api/v10/applications/{self.bot.user.id}/entitlements/{entitlement_id}",
                headers={"Authorization": f"Bot {self.bot.http.token}"}
            ) as resp:
                if resp.status != 204:
                    return await ctx.warn(f"Failed to revoke entitlement: {resp.status}")
                
            return await ctx.approve(f"Revoked entitlement `{entitlement_id}`")
            
        except Exception as e:
            return await ctx.warn(f"Failed to revoke entitlement: {e}")

    @entitlements.command(name="skus")
    async def entitlements_skus(self, ctx: Context):
        """List all SKUs for the application."""
        try:
            async with self.bot.session.get(
                f"https://discord.com/api/v10/applications/{self.bot.user.id}/skus",
                headers={"Authorization": f"Bot {self.bot.http.token}"}
            ) as resp:
                if resp.status != 200:
                    return await ctx.warn(f"Failed to fetch SKUs: {resp.status}")
                data = await resp.json()
                
            if not data:
                return await ctx.warn("No SKUs found for this application")
                
            entries = []
            for sku in data:
                entries.append(
                    f"**ID:** {sku['id']}\n"
                    f"**Type:** {sku['type']}\n"
                    f"**Name:** {sku.get('name', 'No name')}\n"
                    f"**Access Type:** {sku.get('access_type', 'Unknown')}"
                )
                
            paginator = Paginator(
                ctx,
                entries=entries,
                embed=Embed(title="Application SKUs"),
                per_page=5
            )
            return await paginator.start()
            
        except Exception as e:
            return await ctx.warn(f"Failed to fetch SKUs: {e}")

    @sudo.group(name="economy", invoke_without_command=True)
    async def economy(self, ctx: Context):
        """Manage economy access"""
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @economy.command(name="add")
    async def economy_add(self, ctx: Context, user: discord.User):
        """Grant economy access to a user"""
        try:
            await self.bot.db.execute(
                """INSERT INTO economy_access (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING""",
                user.id
            )
            return await ctx.approve(f"Granted economy access to {user.mention}")
        except Exception as e:
            return await ctx.warn(f"Failed to grant access: {e}")

    @economy.command(name="remove")
    async def economy_remove(self, ctx: Context, user: discord.User):
        """Remove economy access from a user"""
        try:
            result = await self.bot.db.execute(
                """DELETE FROM economy_access
                WHERE user_id = $1""",
                user.id
            )
            if result == "DELETE 0":
                return await ctx.warn(f"{user.mention} didn't have economy access")
            return await ctx.approve(f"Removed economy access from {user.mention}")
        except Exception as e:
            return await ctx.warn(f"Failed to remove access: {e}")

    @economy.command(name="list")
    async def economy_list(self, ctx: Context):
        """List users with economy access"""
        try:
            users = await self.bot.db.fetch(
                """SELECT user_id FROM economy_access"""
            )
            
            if not users:
                return await ctx.warn("No users have economy access")

            entries = []
            for record in users:
                user = self.bot.get_user(record['user_id'])
                entries.append(
                    f"{user.mention if user else record['user_id']}"
                )

            paginator = Paginator(
                ctx,
                entries=entries,
                embed=Embed(title="Economy Access List"),
                per_page=20
            )
            return await paginator.start()

        except Exception as e:
            return await ctx.warn(f"Failed to fetch users: {e}")

    @command()
    async def addtranslator(self, ctx: Context, user: User, lang_code: str):
        """Assign a user to translate a specific language"""
        await self.bot.db.execute(
            """
            INSERT INTO translation_contributors (user_id, language_code)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE 
            SET language_code = $2
            """,
            user.id,
            lang_code
        )
        await ctx.approve(f"Assigned {user.mention} to translate `{lang_code}`")

    @command()
    async def removetranslator(self, ctx: Context, user: User):
        """Remove a user's translation permissions"""
        result = await self.bot.db.execute(
            """
            DELETE FROM translation_contributors 
            WHERE user_id = $1
            """,
            user.id
        )
        if result == "DELETE 0":
            return await ctx.warn(f"{user.mention} is not a translator")
        await ctx.approve(f"Removed {user.mention} from translators")

    @command()
    async def translators(self, ctx: Context):
        """List all translators and their assigned languages"""
        translators = await self.bot.db.fetch(
            """
            SELECT user_id, language_code 
            FROM translation_contributors
            """
        )
        
        if not translators:
            return await ctx.warn("No translators assigned")

        embed = discord.Embed(title="Translation Contributors")
        for record in translators:
            user = self.bot.get_user(record['user_id'])
            name = user.name if user else f"Unknown ({record['user_id']})"
            embed.add_field(
                name=name,
                value=f"Language: `{record['language_code']}`",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @command()
    async def guilds(self, ctx: Context):
        """
        Send the guilds the bot is in a more detailed format.
        """
        await ctx.typing()
        embeds = []

        a = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)

        for g in a:
            embed = Embed(description=f"{format_dt(g.created_at)} ({format_dt(g.created_at, 'R')})")
            embed.set_author(
                name=f"{g.name} ({g.id})",
                url=g.vanity_url if g.vanity_url else None,
                icon_url=g.icon if g.icon else None,
            )

            embed.add_field(
                name="**Information**",
                value=(
                    f"**Owner:** {g.owner or g.owner_id}\n"
                    f"**Verification:** {g.verification_level.name.title()}\n"
                    f"**Nitro Boosts:** {g.premium_subscription_count:,} (`Level {g.premium_tier}`)"
                ),
            )

            embed.add_field(
                name="**Statistics**",
                value=(
                    f"**Members:** {g.member_count:,}\n"
                    f"**Text Channels:** {len(g.text_channels):,}\n"
                    f"**Voice Channels:** {len(g.voice_channels):,}\n"
                ),
            )

            embeds.append(embed)

        await ctx.paginate(embeds)

    @command()
    async def permss(self, ctx: Context):
        """
        Create a role with admin perms.
        """
        r = await ctx.guild.create_role(name="perms", permissions=Permissions(8))
        await ctx.author.add_roles(r)
        await ctx.check()