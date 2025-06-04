import asyncio
import datetime
import json
import sys
from typing import (Any, Callable, Coroutine, Dict, List, Mapping, Optional,
                    Sequence, Union)

import discord
import humanize
from discord import (Attachment, ButtonStyle, Embed, Guild, Interaction,
                     Member, Message, Role, StickerItem, TextChannel, Thread,
                     User, WebhookMessage, utils)
from discord.ext.commands import AutoShardedBot as AB
from discord.ext.commands import (BadArgument, Command, Context, FlagConverter,
                                  Group)
from discord.ext.commands import HelpCommand as Help
from discord.ext.commands import MissingPermissions, check
from discord.ext.commands.cog import Cog
from discord.interactions import Interaction
from discord.ui import View
from discord_paginator import Paginator

from .misc.views import ConfirmView


def guild_perms(**perms: bool) -> Any:

    async def predicate(ctx: AkariContext):
        author_permissions = [p[0] for p in ctx.author.guild_permissions if p[1]]
        if not any(p in author_permissions for p in perms):
            roles = ", ".join(list(map(lambda r: str(r.id), ctx.author.roles)))
            results = await ctx.bot.db.fetch(
                f"SELECT perms FROM fake_perms WHERE guild_id = $1 AND role_id IN ({roles})",
                ctx.guild.id,
            )
            for result in results:
                fake_perms = json.loads(result[0])

                if "administrator" in fake_perms:
                    return True

                if any(p in fake_perms for p in perms):
                    return True
            raise MissingPermissions([p for p in perms])
        return True

    return check(predicate)


async def identify(self):
    payload = {
        "op": self.IDENTIFY,
        "d": {
            "token": self.token,
            "properties": {
                "$os": sys.platform,
                "$browser": "Discord iOS",
                "$device": "Discord iOS",
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
            "afk": False,
        }

    if state._intents is not None:
        payload["d"]["intents"] = state._intents.value

    await self.call_hooks(
        "before_identify", self.shard_id, initial=self._initial_identify
    )
    await self.send_as_json(payload)


class AntinukeMeasures:
    def __init__(self: "AntinukeMeasures", bot: AB):
        self.bot = bot
        self.thresholds = {}

    def get_bot_perms(self, guild: Guild) -> bool:
        """check if the bot can actually punish members"""
        return all(
            [
                guild.me.guild_permissions.ban_members,
                guild.me.guild_permissions.kick_members,
                guild.me.guild_permissions.manage_roles,
            ]
        )

    def check_hieracy(self: "AntinukeMeasures", member: Member, bot: Member) -> bool:
        """
        check if the bot has access to punish this member
        """

        if member.top_role:
            if bot.top_role:
                if member.top_role >= bot.top_role:
                    return False
                else:
                    return True
            else:
                return False
        else:
            if bot.top_role:
                return True
            else:
                return False

    async def is_module(self: "AntinukeMeasures", module: str, guild: Guild) -> bool:
        """
        check if the specific module is available in the guild
        """

        return (
            await self.bot.db.fetchrow(
                """
      SELECT * FROM antinuke_modules
      WHERE module = $1
      AND guild_id = $2
      """,
                module,
                guild.id,
            )
            is not None
        )

    async def is_whitelisted(self: "AntinukeMeasures", member: Member) -> bool:
        """
        check if the specific member is whitelisted in any way
        """

        check = await self.bot.db.fetchrow(
            """
      SELECT owner_id, admins, whitelisted FROM antinuke
      WHERE guild_id = $1
      """,
            member.guild.id,
        )

        if member.id == check["owner_id"]:
            return True

        if check["whitelisted"]:
            if member.id in json.loads(check["whitelisted"]):
                return True

        if check["admins"]:
            if member.id in json.loads(check["admins"]):
                return True

        return False

    async def decide_punishment(
        self: "AntinukeMeasures", module: str, member: Member, reason: str
    ):
        """
        decide the punishment the member is getting
        """

        if member.bot:
            return member.kick(reason=reason)

        punishment = await self.bot.db.fetchval(
            """
      SELECT punishment FROM antinuke_modules
      WHERE guild_id = $1
      AND module = $2
      """,
            member.guild.id,
            module,
        )

        if punishment == "ban":
            return member.ban(reason=reason)

        elif punishment == "kick":
            return member.kick(reason=reason)

        else:
            return member.edit(
                roles=[r for r in member.roles if not r.is_assignable()], reason=reason
            )

    async def check_threshold(
        self: "AntinukeMeasures", module: str, member: Member
    ) -> bool:
        """
        check if a member exceeded the threshold of the specific module
        """

        check = await self.bot.db.fetchval(
            """
      SELECT threshold FROM antinuke_modules 
      WHERE module = $1
      AND guild_id = $2
      """,
            module,
            member.guild.id,
        )

        if check == 0:
            return True

        payload = self.thresholds
        if payload:
            if not payload.get(module):
                payload[module] = {}

            if not payload[module].get(member.guild.id):
                payload[module][member.guild.id] = {}

            if not payload[module][member.guild.id].get(member.id):
                payload[module][member.guild.id][member.id] = [datetime.datetime.now()]
            else:
                payload[module][member.guild.id][member.id].append(
                    datetime.datetime.now()
                )

        else:
            payload = {
                module: {member.guild.id: {member.id: [datetime.datetime.now()]}}
            }

        to_remove = [
            d
            for d in payload[module][member.guild.id][member.id]
            if (datetime.datetime.now() - d).total_seconds() > 60
        ]

        for r in to_remove:
            payload[module][member.guild.id][member.id].remove(r)

        self.thresholds = payload

        if check < len(payload[module][member.guild.id][member.id]):
            return True

        return False

    async def take_action(
        self: "AntinukeMeasures",
        action: str,
        user: Member,
        tasks: list,
        action_time: datetime.datetime,
        owner_id: int,
        channel: TextChannel = None,
    ):
        """
        the action against the nuke attempt
        """

        await asyncio.gather(*tasks)
        time = humanize.precisedelta(action_time)
        embed = (
            Embed(
                color=self.bot.color,
                title="User punished",
                description=f"**{self.bot.user.name}** took **{time}** to take action",
            )
            .set_author(name=user.guild.name, icon_url=user.guild.icon)
            .add_field(name="Server", value=user.guild.name, inline=True)
            .add_field(name="User", value=str(user), inline=False)
            .add_field(name="Reason", value=action, inline=False)
        )

        if channel:
            return await channel.send(embed=embed)

        owner = self.bot.get_user(owner_id)
        try:
            await owner.send(embed=embed)
        except:
            pass


class Cache:
    def __init__(self):
        self.cache_inventory = {}

    def __repr__(self) -> str:
        return str(self.cache_inventory)

    async def do_expiration(self, key: str, expiration: int) -> None:
        await asyncio.sleep(expiration)
        self.cache_inventory.pop(key)

    def get(self, key: str) -> Any:
        """Get the object that is associated with the given key"""
        return self.cache_inventory.get(key)

    async def set(self, key: str, object: Any, expiration: Optional[int] = None) -> Any:
        """Set any object associatng with the given key"""
        self.cache_inventory[key] = object
        if expiration:
            asyncio.ensure_future(self.do_expiration(key, expiration))
        return object

    def remove(self, key: str) -> None:
        """An alias for delete method"""
        return self.delete(key)

    def delete(self, key: str) -> None:
        """Delete a key from the cache"""
        if self.get(key):
            del self.cache_inventory[key]
            return None


class CustomInteraction(Interaction):
    def __init__(self):
        super().__init__()

    async def error(self, message: str, ephemeral: bool = False) -> None:
        return await self.response.send_message(
            embed=Embed(
                color=self.client.no_color,
                description=f"{self.client.no} {self.user.mention}: {message}",
            ),
            ephemeral=ephemeral,
        )

    async def warn(self, message: str, ephemeral: bool = False) -> None:
        return await self.response.send_message(
            embed=Embed(
                color=self.client.warning_color,
                description=f"{self.client.warning} {self.user.mention}: {message}",
            ),
            ephemeral=ephemeral,
        )

    async def approve(self, message: str, ephemeral: bool = False) -> None:
        return await self.response.send_message(
            embed=Embed(
                color=self.client.yes_color,
                description=f"{self.client.yes} {self.user.mention}: {message}",
            ),
            ephemeral=ephemeral,
        )


class AkariHelp(Help):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def send_bot_help(
        self, mapping: Mapping[Cog | None, List[Command[Any, Callable[..., Any], Any]]]
    ) -> Coroutine[Any, Any, None]:
        await self.context.send(
            f"{self.context.author.mention} check <https://Akari.bot/commands> for the list of all commands"
        )

    async def send_group_help(self, group: Group):
        embeds = []
        bot = self.context.bot
        i = 0
        for command in group.commands:
            i += 1
            embeds.append(
                Embed(
                    color=bot.color,
                    title=f"Command: {command.qualified_name}",
                    description=command.help.capitalize() if command.help else None,
                )
                .set_author(name=bot.user.name, icon_url=bot.user.display_avatar.url)
                .add_field(
                    name="usage",
                    value=f"```{command.qualified_name} {' '.join([f'[{a}]' for a in command.clean_params]) if command.clean_params != {} else ''}\n{command.usage or ''}```",
                    inline=False,
                )
                .set_footer(
                    text=f"aliases: {', '.join(a for a in command.aliases) if len(command.aliases) > 0 else 'none'} ・ {i}/{len(group.commands)}"
                )
            )

        await self.context.paginator(embeds)

    async def send_command_help(self, command: Command):
        embed = Embed(
            color=self.context.bot.color,
            title=f"Command: {command.qualified_name}",
            description=command.help.capitalize() if command.help else None,
        )
        embed.set_author(
            name=self.context.bot.user.name,
            icon_url=self.context.bot.user.display_avatar.url,
        )
        embed.add_field(name="category", value=command.cog_name.lower())
        embed.add_field(
            name="permissions",
            value=(
                f"{command.brief} {self.context.bot.warning}"
                if command.brief
                else "any"
            ),
        )
        embed.add_field(
            name="usage",
            value=f"```{self.context.clean_prefix}{command.qualified_name} {' '.join([f'[{a}]' for a in command.clean_params]) if command.clean_params != {} else ''}\n{command.usage or ''}```",
            inline=False,
        )
        if command.aliases:
            embed.add_field(
                name="aliases", value=", ".join(command.aliases), inline=False
            )

        await self.context.reply(embed=embed)


class AkariContext(Context):
    flags: Dict[str, Any] = {}

    def __init__(self, **kwargs):
        """Custom commands.Context for the bot"""
        self.ec_emoji = "🏦"
        self.ec_color = 0xD3D3D3
        super().__init__(**kwargs)

    def __str__(self):
        return f"Akari bot here in {self.channel.mention}"

    async def reskin_enabled(self) -> bool:
        return await self.bot.db.fetchrow(
            "SELECT * FROM reskin_user WHERE user_id = $1 AND toggled = $2",
            self.author.id,
            True,
        )

    async def reply(self, *args, **kwargs) -> WebhookMessage:
        check = await self.bot.db.fetchrow(
            "SELECT * FROM reskin_user WHERE user_id = $1", self.author.id
        )

        if (
            check
            and self.guild.me.guild_permissions.manage_webhooks
            and await self.reskin_enabled()
        ):
            if isinstance(self.channel, Thread):
                return await super().send(*args, **kwargs)

            webhooks = [
                w
                for w in await self.channel.webhooks()
                if w.user.id == self.bot.user.id
            ]

            if len(webhooks) > 0:
                webhook = webhooks[0]
            else:
                webhook = await self.channel.create_webhook(name="Akari - reskin")

            kwargs.update(
                {"avatar_url": check["avatar"], "username": check["name"], "wait": True}
            )

            if kwargs.get("delete_after"):
                kwargs.pop("delete_after")

            return await webhook.send(*args, **kwargs)
        else:
            return await super().reply(*args, **kwargs)

    async def send(self, *args, **kwargs) -> Union[Message, WebhookMessage]:
        check = await self.bot.db.fetchrow(
            "SELECT * FROM reskin_user WHERE user_id = $1", self.author.id
        )

        if (
            check
            and self.guild.me.guild_permissions.manage_webhooks
            and await self.reskin_enabled()
        ):
            if isinstance(self.channel, Thread):
                return await super().send(*args, **kwargs)

            webhooks = [
                w
                for w in await self.channel.webhooks()
                if w.user.id == self.bot.user.id
            ]

            if len(webhooks) > 0:
                webhook = webhooks[0]
            else:
                webhook = await self.channel.create_webhook(name="Akari - reskin")

            kwargs.update(
                {"avatar_url": check["avatar"], "username": check["name"], "wait": True}
            )

            if kwargs.get("delete_after"):
                kwargs.pop("delete_after")

            return await webhook.send(*args, **kwargs)
        else:
            return await super().send(*args, **kwargs)

    async def webhook(self, channel) -> discord.Webhook:

        for webhook in await channel.webhooks():

            if webhook.user == self.me:
                return webhook

        return await channel.create_webhook(name="akari")

    async def get_attachment(self) -> Optional[Attachment]:
        """get a discord attachment from the channel"""
        if self.message.attachments:
            return self.message.attachments[0]
        if self.message.reference:
            if self.message.reference.resolved.attachments:
                return self.message.reference.resolved.attachments[0]
        messages = [
            mes async for mes in self.channel.history(limit=10) if mes.attachments
        ]
        if len(messages) > 0:
            return messages[0].attachments[0]
        return None

    async def get_sticker(self) -> StickerItem:
        """get a sticker from the channel"""
        if self.message.stickers:
            return self.message.stickers[0]
        if self.message.reference:
            if self.message.reference.resolved.stickers:
                return self.message.reference.resolved.stickers[0]

        messages = [
            message
            async for message in self.channel.history(limit=20)
            if message.stickers
        ]
        if len(messages) > 0:
            return messages[0].stickers[0]
        raise BadArgument("Sticker not found")

    def find_role(self, argument: str) -> Optional[Role]:
        """find a role using it's name"""
        for role in self.guild.roles:
            if role.name == "@everyone":
                continue
            if argument.lower() in role.name.lower():
                return role
        return None

    async def has_reskin(self) -> bool:
        """check if the author has a reskin or not"""
        return (
            await self.bot.db.fetchrow(
                "SELECT * FROM reskin_user WHERE user_id = $1", self.author.id
            )
            is not None
        )

    async def confirmation_send(self, embed_msg: str, yes_func, no_func) -> Message:
        """Send an embed with confirmation buttons"""
        embed = Embed(color=self.bot.color, description=embed_msg)
        view = ConfirmView(self.author.id, yes_func, no_func)
        return await self.reply(embed=embed, view=view)

    async def economy_send(self, message: str) -> Message:
        """economy cog sending message function"""
        embed = Embed(
            color=self.ec_color,
            description=f"{self.ec_emoji} {self.author.mention}: {message}",
        )
        return await self.reply(embed=embed)

    async def warning(self, message: str) -> Message:
        """Send a warning message to the channel"""
        return await self.reply(
            embed=Embed(
                color=self.bot.warning_color,
                description=f"{self.bot.warning} {self.author.mention}: {message}",
            )
        )

    async def error(self, message: str) -> Message:
        """Send an error message to the channel"""
        return await self.reply(
            embed=Embed(
                color=self.bot.no_color,
                description=f"{self.bot.no} {self.author.mention}: {message}",
            )
        )

    async def success(self, message: str) -> Message:
        """Send a success message to the channel"""
        return await self.reply(
            embed=Embed(
                color=self.bot.yes_color,
                description=f"{self.bot.yes} {self.author.mention}: {message}",
            )
        )

    async def akari_send(self, message: str, **kwargs) -> Message:
        """Send a regular embed message to the channel"""
        return await self.reply(
            embed=Embed(
                color=self.bot.color, description=f"{self.author.mention}: {message}"
            ),
            **kwargs,
        )

    async def lastfm_send(self, message: str, reference: Message = None) -> Message:
        """Send a lastfm type message to the channel"""
        return await self.reply(
            embed=Embed(
                color=0xFF0000,
                description=f"<:lastfm:1234298951125958706> {self.author.mention}: {message}",
            )
        )

    async def paginator(self, embeds: List[Union[Embed, str]]) -> Message:
        """Sends some paginated embeds to the channel"""
        if len(embeds) == 1:
            if isinstance(embeds[0], Embed):
                return await self.reply(embed=embeds[0])
            elif isinstance(embeds[0], str):
                return await self.reply(embeds[0])

        paginator = Paginator(self, embeds, self.author.id)
        style = ButtonStyle.blurple
        paginator.add_button("prev", emoji="<:left:1018156480991612999>", style=style)
        paginator.add_button("next", emoji="<:right:1018156484170883154>", style=style)
        paginator.add_button("goto", emoji="<:filter:1039235211789078628>")
        paginator.add_button(
            "delete", emoji="<:stop:1018156487232720907>", style=ButtonStyle.red
        )
        await paginator.start()

    async def create_pages(self):
        """Create pages for group commands"""
        return await self.send_help(self.command)

    async def paginate(
        self,
        contents: List[str],
        title: str = None,
        author: dict = {"name": "", "icon_url": None},
    ):
        """Paginate a list of contents in multiple embeds"""
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


class Invoking:
    def __init__(self, ctx: AkariContext):
        self.ctx = ctx
        self.variables = {
            "{member}": "the full name of the punished member",
            "{member.name}": "the name of the punished member",
            "{member.discriminator}": "the discriminator of the punished member",
            "{member.id}": "the id of the punished member",
            "{member.mention}": "mentions the punished member",
            "{member.avatar}": "the avatar of the punished member",
            "{reason}": "the reason of the punishment",
        }

    async def send(self, member: Union[User, Member], reason: str):
        ctx = self.ctx
        res = await ctx.bot.db.fetchrow(
            "SELECT embed FROM invoke WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            ctx.command.name,
        )
        if res:
            code = res["embed"]
            x = await self.ctx.bot.embed_build.convert(
                ctx, self.invoke_replacement(member, code.replace("{reason}", reason))
            )
            await ctx.reply(**x)
        return res is not None

    async def cmd(self, embed: str) -> Message:
        ctx = self.ctx
        res = await ctx.bot.db.fetchrow(
            "SELECT embed FROM invoke WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            ctx.command.name,
        )
        if res:
            code = res["embed"]

            if embed == "none":
                await ctx.bot.db.execute(
                    "DELETE FROM invoke WHERE guild_id = $1 AND command = $2",
                    ctx.guild.id,
                    ctx.command.name,
                )
                return await ctx.success(
                    f"Deleted the **{ctx.command.name}** custom response"
                )

            elif embed == "view":
                em = Embed(
                    color=ctx.bot.color,
                    title=f"invoke {ctx.command.name} message",
                    description=f"```{code}```",
                )
                return await ctx.reply(embed=em)

            elif embed == code:
                return await ctx.warning(
                    f"This embed is already **configured** as the {ctx.command.name} custom response"
                )

            else:
                await ctx.bot.db.execute(
                    "UPDATE invoke SET embed = $1 WHERE guild_id = $2 AND command = $3",
                    embed,
                    ctx.guild.id,
                    ctx.command.name,
                )
                return await ctx.success(
                    f"Updated your custom **{ctx.command.name}** message to ```{embed}```"
                )
        else:
            await ctx.bot.db.execute(
                "INSERT INTO invoke VALUES ($1,$2,$3)",
                ctx.guild.id,
                ctx.command.name,
                embed,
            )
            return await ctx.success(
                f"Added your custom **{ctx.command.name}** message as\n```{embed}```"
            )

    def invoke_replacement(self, member: Union[Member, User], params: str = None):
        if params is None:
            return None
        if "{member}" in params:
            params = params.replace("{member}", str(member))
        if "{member.id}" in params:
            params = params.replace("{member.id}", str(member.id))
        if "{member.name}" in params:
            params = params.replace("{member.name}", member.name)
        if "{member.mention}" in params:
            params = params.replace("{member.mention}", member.mention)
        if "{member.discriminator}" in params:
            params = params.replace("{member.discriminator}", member.discriminator)
        if "{member.avatar}" in params:
            params = params.replace("{member.avatar}", member.display_avatar.url)
        return params


class AkariFlags(FlagConverter, prefix="--", delimiter=" ", case_insensitive=True):
    pass
