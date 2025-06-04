import re
import json
import asyncio
import discord

from typing import Mapping, Coroutine, List, Any, Callable, Optional, Union, Dict

from discord import Embed
from discord import Role, ButtonStyle, Message, Embed, StickerItem, Interaction, User, Member, Attachment, WebhookMessage, TextChannel, Guild, utils, Thread
from discord.ext import commands
from discord.ext.commands import BadArgument, HelpCommand as Help, Command, MissingPermissions, check, Group,AutoShardedBot as AB, FlagConverter
from discord.ext.commands.cog import Cog

from modules.styles import emojis, colors
from modules.paginator.embed import Paginator
from modules.paginator.content import PaginatorContent
from modules.misc.views import ConfirmView, TargetConfirmView, ModalButtonView, ChooseView

def stringfromtime(t, accuracy=4):
    m, s = divmod(t, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    components = []
    if d > 0:
        components.append(f"{int(d)} day" + ("s" if d != 1 else ""))
    if h > 0:
        components.append(f"{int(h)} hour" + ("s" if h != 1 else ""))
    if m > 0:
        components.append(f"{int(m)} minute" + ("s" if m != 1 else ""))
    if s > 0:
        components.append(f"{int(s)} second" + ("s" if s != 1 else ""))
    return " ".join(components[:accuracy])

def guild_perms(**perms: bool) -> Any:
    async def predicate(ctx: EvelinaContext):
        author_guild_permissions = [p[0] for p in ctx.author.guild_permissions if p[1]]
        author_channel_permissions = [p[0] for p in ctx.channel.permissions_for(ctx.author) if p[1]]
        if any(p in author_guild_permissions for p in perms):
            return True
        if any(p in author_channel_permissions for p in perms):
            return True
        roles = ", ".join(list(map(lambda r: str(r.id), ctx.author.roles)))
        res = await ctx.bot.db.fetch(f"SELECT perms FROM fake_perms WHERE guild_id = $1 AND role_id IN ({roles})", ctx.guild.id)
        for result in res:
            fake_perms = json.loads(result[0])
            if "administrator" in fake_perms:
                return True
            if any(p in fake_perms for p in perms):
                return True
        raise MissingPermissions([p for p in perms])
    return check(predicate)

class Cache:
    def __init__(self):
        self.cache_inventory = {}

    def __repr__(self) -> str:
        return str(self.cache_inventory)

    async def do_expiration(self, key: str, expiration: int) -> None:
        try:
            await asyncio.sleep(expiration)
            self.cache_inventory.pop(key)
        except KeyError:
            pass

    async def get(self, key: str) -> Any:
        return self.cache_inventory.get(key)

    async def set(self, key: str, object: Any, expiration: Optional[int] = None) -> Any:
        self.cache_inventory[key] = object
        if expiration:
            asyncio.ensure_future(self.do_expiration(key, expiration))
        return object

    async def remove(self, key: str) -> None:
        return await self.delete(key)

    async def delete(self, key: str) -> None:
        if await self.get(key):
            del self.cache_inventory[key]
            return None
        
class CustomInteraction(Interaction):
    def __init__(self):
        super().__init__()

    async def error(self, message: str, ephemeral: bool = False) -> None:
        if self.response.is_done():
            return await self.followup.send(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {self.user.mention}: {message}"), ephemeral=ephemeral)
        else:
            return await self.response.send_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {self.user.mention}: {message}"), ephemeral=ephemeral)
    
    async def warn(self, message: str, ephemeral: bool = False) -> None:
        if self.response.is_done():
            return await self.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {self.user.mention}: {message}"), ephemeral=ephemeral)
        else:
            return await self.response.send_message(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {self.user.mention}: {message}"), ephemeral=ephemeral)

    async def approve(self, message: str, ephemeral: bool = False) -> None:
        if self.response.is_done():
            return await self.followup.send(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {self.user.mention}: {message}"), ephemeral=ephemeral)
        else:
            return await self.response.send_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {self.user.mention}: {message}"), ephemeral=ephemeral)
    
    async def add(self, message: str, ephemeral: bool = False) -> None:
        if self.response.is_done():
            return await self.followup.send(embed=Embed(color=colors.SUCCESS, description=f"{emojis.ADD} {self.user.mention}: {message}"), ephemeral=ephemeral)
        else:
            return await self.response.send_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.ADD} {self.user.mention}: {message}"), ephemeral=ephemeral)
    
    async def remove(self, message: str, ephemeral: bool = False) -> None:
        if self.response.is_done():
            return await self.followup.send(embed=Embed(color=colors.ERROR, description=f"{emojis.REMOVE} {self.user.mention}: {message}"), ephemeral=ephemeral)
        else:
            return await self.response.send_message(embed=Embed(color=colors.ERROR, description=f"{emojis.REMOVE} {self.user.mention}: {message}"), ephemeral=ephemeral)

    async def embed(self, message: str, ephemeral: bool = False) -> None:
        if self.response.is_done():
            return await self.followup.send(embed=Embed(color=colors.NEUTRAL, description=f"{message}"), ephemeral=ephemeral)
        else:
            return await self.response.send_message(embed=Embed(color=colors.NEUTRAL, description=f"{message}"), ephemeral=ephemeral)

class EvelinaContext(commands.Context):
    flags: Dict[str, Any] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def find_role(self, argument: str) -> Optional[Role]:
        for role in self.guild.roles:
            if role.name == "@everyone":
                continue
            if argument.lower() in role.name.lower():
                return role
        return None
        
    async def get_attachment(self) -> Optional[Attachment]:
        if self.message.attachments:
            return self.message.attachments[0]
        if self.message.reference:
            if self.message.reference.resolved.attachments:
                return self.message.reference.resolved.attachments[0]
        messages = [mes async for mes in self.channel.history(limit=10) if mes.attachments]
        if len(messages) > 0:
            return messages[0].attachments[0]
        return None
    
    async def get_sticker(self) -> StickerItem:
        if self.message.stickers:
            return self.message.stickers[0]
        if self.message.reference:
            ref_message = self.message.reference.resolved
            if not ref_message:
                ref_message = await self.channel.fetch_message(self.message.reference.message_id)
            if ref_message and ref_message.stickers:
                return ref_message.stickers[0]    
        raise BadArgument("Sticker not found")

    async def reply(self, *args, **kwargs) -> Union[Message, WebhookMessage]:
        return await self.send(*args, **kwargs)

    async def send(self, *args, **kwargs) -> Union[Message, WebhookMessage]:
        return await super().send(*args, **kwargs)

    async def evelina_send(self, message: str, emoji: str = None, content: str = None, **kwargs) -> Message:
        return await self.send(content=content if content else '', embed=Embed(color=colors.NEUTRAL, description=f"{emoji if emoji else ''} {self.author.mention}: {message}"), **kwargs)
    
    async def lastfm_send(self, message: str, reference: Message = None) -> Message:
        return await self.send(embed=Embed(color=colors.LASTFM, description=f"{emojis.LASTFM} {self.author.mention}: {message}"))
    
    async def spotify_send(self, message: str) -> Message:
        return await self.send(embed=Embed(color=colors.SPOTIFY, description=f"{emojis.SPOTIFY} {self.author.mention}: {message}"))

    async def send_reminder(self, message: str, **kwargs) -> Message:
        return await self.send(embed=Embed(color=colors.NEUTRAL, description=f"🕐 {self.author.mention}: {message}"), **kwargs)
    
    async def send_question(self, message: str, channel: TextChannel = None, obj: Message = None) -> Message:
        e = Embed(color=colors.NEUTRAL, description=f"{emojis.QUESTION} {self.author.mention}: {message}")
        if obj:
            return await obj.edit(embed=e, view=None)
        if channel:
            if channel.permissions_for(self.guild.me).send_messages:
                return await channel.send(embed=e)
        else:
            return await self.send(embed=e)

    async def send_success(self, message: str, channel: TextChannel = None, obj: Message = None) -> Message:
        e = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {self.author.mention}: {message}")
        if obj:
            return await obj.edit(embed=e, view=None)
        if channel:
            if channel.permissions_for(self.guild.me).send_messages:
                return await channel.send(embed=e)
        else:
            return await self.send(embed=e)

    async def send_loading(self, message: str, channel: TextChannel = None, obj: Message = None) -> Message:
        e = Embed(color=colors.LOADING, description=f"{emojis.LOADING} {self.author.mention}: {message}")
        if obj:
            return await obj.edit(embed=e, view=None)
        if channel:
            if channel.permissions_for(self.guild.me).send_messages:
                return await channel.send(embed=e)
        else:
            return await self.send(embed=e)

    async def send_error(self, message: str, channel: TextChannel = None, obj: Message = None) -> Message:
        e = Embed(color=colors.ERROR, description=f"{emojis.DENY} {self.author.mention}: {message}")
        if obj:
            return await obj.edit(embed=e, view=None)
        if channel:
            if channel.permissions_for(self.guild.me).send_messages:
                return await channel.send(embed=e)
        else:
            return await self.send(embed=e)

    async def send_warning(self, message: str, channel: TextChannel = None, obj: Message = None) -> Message:
        e = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {self.author.mention}: {message}")
        if obj:
            return await obj.edit(embed=e, view=None)
        if channel:
            if channel.permissions_for(self.guild.me).send_messages:
                return await channel.send(embed=e)
        else:
            return await self.send(embed=e)
    
    async def confirmation_send(self, embed_msg: str, yes_func, no_func) -> Message:
        embed = Embed(color=colors.NEUTRAL, description=embed_msg)
        view = ConfirmView(self.author.id, yes_func, no_func)
        return await self.send(embed=embed, view=view)
    
    async def target_confirmation_send(self, embed_msg: str, user_id: int, yes_func, no_func) -> Message:
        embed = Embed(color=colors.NEUTRAL, description=embed_msg)
        content = f"<@{user_id}>"
        view = TargetConfirmView(self.author.id, user_id, yes_func, no_func)
        return await self.send(content=content, embed=embed, view=view)
    
    async def modal_send(self, prompt: str, button_label: str, modal_title: str, fields: list[tuple[str, str]], callback_func):
        embed = Embed(color=colors.NEUTRAL, description=prompt)
        view = ModalButtonView(self.author.id, button_label, modal_title, fields, callback_func)
        return await self.send(embed=embed, view=view)

    async def ticket_send(self, embed_msg: str, button_func, select_func) -> Message:
        embed = Embed(color=colors.NEUTRAL, description=embed_msg)
        view = ChooseView(self.author.id, button_func, select_func)
        return await self.send(embed=embed, view=view)
    
    async def economy_send(self, message: str) -> Message:
        embed = Embed(color=colors.ECONOMY, description=f"{emojis.ECONOMY} {self.author.mention}: {message}")
        return await self.send(embed=embed)
    
    async def cooldown_send(self, message: str) -> Message:
        embed = Embed(color=colors.COOLDOWN, description=f"{emojis.COOLDOWN_WARN} {self.author.mention}: {message}")
        return await self.send(embed=embed)
    
    async def send_exchange(self, message: str) -> Message:
        return await self.send(embed=Embed(color=colors.EXCHANGE, description=f"{emojis.EXCHANGE} {self.author.mention}: {message}"))

    async def embed(self, message: str, color: int = None, emoji: str = None, **kwargs) -> Message:
        embed = Embed(color=color if color else colors.NEUTRAL, description=f"{emoji if emoji else ''} {self.author.mention}: {message}")
        return await self.send(embed=embed, **kwargs)

    async def paginator(self, embeds: List[Union[Embed, str]], author_only: bool = True, interaction: Interaction = None, ephemeral: bool = False) -> Message:
        if len(embeds) == 1:
            if isinstance(embeds[0], Embed):
                if interaction:
                    try:
                        return await interaction.response.send_message(embed=embeds[0], ephemeral=ephemeral)
                    except discord.errors.InteractionResponded:
                        return await interaction.followup.send(embed=embeds[0], ephemeral=ephemeral)
                else:
                    return await self.send(embed=embeds[0])
            elif isinstance(embeds[0], str):
                if interaction:
                    try:
                        return await interaction.response.send_message(embeds[0], ephemeral=ephemeral)
                    except discord.errors.InteractionResponded:
                        return await interaction.followup.send(embeds[0], ephemeral=ephemeral)
                else:
                    return await self.send(embeds[0])
        paginator = Paginator(self, embeds=embeds, author_only=author_only)
        style = ButtonStyle.blurple
        paginator.add_button("prev", emoji=f"{emojis.LEFT}", style=style)
        paginator.add_button("next", emoji=f"{emojis.RIGHT}", style=style)
        paginator.add_button("goto", emoji=f"{emojis.GOTO}")
        if not ephemeral or not interaction:
            paginator.add_button("delete", emoji=f"{emojis.CANCEL}", style=ButtonStyle.red)
        if interaction:
            await paginator.start(interaction=interaction, ephemeral=ephemeral)
        else:
            await paginator.start()

    async def paginator_content(self, contents: List[str], author_only: bool = True, interaction: Interaction = None, ephemeral: bool = False) -> discord.Message:
        if len(contents) == 1:
            if isinstance(contents[0], str):
                if interaction:
                    try:
                        return await interaction.response.send_message(content=contents[0], ephemeral=ephemeral)
                    except discord.errors.InteractionResponded:
                        return await interaction.followup.send(content=contents[0], ephemeral=ephemeral)
                else:
                    return await self.send(content=contents[0])
        paginator = PaginatorContent(self, contents, author_only=author_only)
        style = ButtonStyle.blurple
        paginator.add_button("prev", emoji=f"{emojis.LEFT}", style=style)
        paginator.add_button("next", emoji=f"{emojis.RIGHT}", style=style)
        paginator.add_button("goto", emoji=f"{emojis.GOTO}")
        if not ephemeral or not interaction:
            paginator.add_button("delete", emoji=f"{emojis.CANCEL}", style=ButtonStyle.red)
        if interaction:
            await paginator.start(author_only=author_only, interaction=interaction, ephemeral=ephemeral)
        else:
            await paginator.start()

    async def create_pages(self):
        return await self.send_help(self.command)

    async def paginate(self, contents: List[str], title: str = None, author: dict = {"name": "", "icon_url": None}, url: str = None, image: str = None, author_only: bool = True, interaction: Interaction = False, ephemeral: bool = False) -> Message:
        iterator = [m for m in utils.as_chunks(contents, 10)]
        totalpages = len(iterator)
        entries = len(contents)
        embeds = [Embed(color=colors.NEUTRAL, title=title, url=url, description="\n".join([f"`{(m.index(f)+1)+(iterator.index(m)*10)}.` {f}" for f in m]))
            .set_author(**author)
            .set_footer(text=f"Page: {i+1}/{totalpages} ({entries} entries)")
            .set_thumbnail(url=image)
            for i, m in enumerate(iterator)
        ]
        return await self.paginator(embeds, author_only, interaction, ephemeral)

    async def smallpaginate(self, contents: List[str], title: str = None, author: dict = {"name": "", "icon_url": None}, url: str = None, author_only: bool = True, interaction: Interaction = False, ephemeral: bool = False) -> Message:
        iterator = [m for m in utils.as_chunks(contents, 5)]
        totalpages = len(iterator)
        entries = len(contents)
        embeds = [Embed(color=colors.NEUTRAL, title=title, url=url, description="\n".join([f"`{(m.index(f)+1)+(iterator.index(m)*5)}.` {f}" for f in m]))
            .set_author(**author)
            .set_footer(text=f"Page: {i+1}/{totalpages} ({entries} entries)")
            for i, m in enumerate(iterator)
        ]
        return await self.paginator(embeds, author_only, interaction, ephemeral)
    
    async def namespaginate(self, contents: List[str], title: str = None, author: dict = {"name": "", "icon_url": None}, url: str = None, author_only: bool = True, interaction: Interaction = False, ephemeral: bool = False) -> Message:
        iterator = [m for m in utils.as_chunks(contents, 10)]
        totalpages = len(iterator)
        entries = len(contents)
        embeds = [Embed(color=colors.NEUTRAL, title=title, url=url, description="\n".join([f"{f}" for f in m]))
            .set_author(**author)
            .set_footer(text=f"Page: {i+1}/{totalpages} ({entries} entries)")
            for i, m in enumerate(iterator)
        ]
        return await self.paginator(embeds, author_only, interaction, ephemeral)
    
    def is_dangerous(self, role: discord.Role) -> bool:
        return any(
            [
                role.permissions.ban_members,
                role.permissions.kick_members,
                role.permissions.mention_everyone,
                role.permissions.manage_channels,
                role.permissions.manage_events,
                role.permissions.manage_expressions,
                role.permissions.manage_guild,
                role.permissions.manage_roles,
                role.permissions.manage_messages,
                role.permissions.manage_webhooks,
                role.permissions.manage_permissions,
                role.permissions.manage_threads,
                role.permissions.moderate_members,
                role.permissions.mute_members,
                role.permissions.deafen_members,
                role.permissions.move_members,
                role.permissions.administrator,
            ]
        )
    
class Invoking:
    def __init__(self, ctx: EvelinaContext):
        self.ctx = ctx

    async def send(self, member: Union[User, Member], reason: str, formated_time: str, history_id: str):
        ctx = self.ctx
        res = await ctx.bot.db.fetchrow("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, ctx.command.name)
        if res:
            code = res["embed"]
            if formated_time == None:
                x = await self.ctx.bot.embed_build.convert(ctx, self.invoke_replacement(member, code.replace("{reason}", reason).replace("{case.id}", history_id)))
            else:
                x = await self.ctx.bot.embed_build.convert(ctx, self.invoke_replacement(member, code.replace("{reason}", reason).replace("{case.id}", history_id).replace("{duration}", formated_time).replace("{time}", formated_time)))
            await ctx.reply(**x)
        return res is not None
    
    def invoke_replacement(self, member: Union[Member, User], params: str = None):
        if params is None:
            return None
        if "{member.id}" in params:
            params = params.replace("{member.id}", str(member.id))
        if "{member.name}" in params:
            params = params.replace("{member.name}", member.name)
        if "{member.nick}" in params:
            params = params.replace("{member.nick}", member.nick or member.display_name)
        if "{member.display}" in params:
            params = params.replace("{member.display}", member.display_name)
        if "{member.mention}" in params:
            params = params.replace("{member.mention}", member.mention)
        if "{member.discriminator}" in params:
            params = params.replace("{member.discriminator}", member.discriminator)
        if "{member.avatar}" in params:
            params = params.replace("{member.avatar}", member.avatar.url if member.avatar else member.default_avatar.url)
        return params
    
class ChannelInvoking:
    def __init__(self, ctx: EvelinaContext, channel: TextChannel):
        self.ctx = ctx
        self.channel = channel

    async def send(self, member: Union[User, Member], reason: str, formated_time: str, history_id: str):
        ctx = self.ctx
        res = await ctx.bot.db.fetchrow("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jailchannel")
        if res:
            code = res["embed"]
            if formated_time == None:
                x = await self.ctx.bot.embed_build.convert(ctx, self.invoke_replacement(member, code.replace("{reason}", reason).replace("{case.id}", history_id)))
            else:
                x = await self.ctx.bot.embed_build.convert(ctx, self.invoke_replacement(member, code.replace("{reason}", reason).replace("{case.id}", history_id).replace("{duration}", formated_time).replace("{time}", formated_time)))
            await self.channel.send(**x)
        return res is not None
    
    def invoke_replacement(self, member: Union[Member, User], params: str = None):
        if params is None:
            return None
        if "{member.id}" in params:
            params = params.replace("{member.id}", str(member.id))
        if "{member.name}" in params:
            params = params.replace("{member.name}", member.name)
        if "{member.nick}" in params:
            params = params.replace("{member.nick}", member.nick or member.display_name)
        if "{member.display}" in params:
            params = params.replace("{member.display}", member.display_name)
        if "{member.mention}" in params:
            params = params.replace("{member.mention}", member.mention)
        if "{member.discriminator}" in params:
            params = params.replace("{member.discriminator}", member.discriminator)
        if "{member.avatar}" in params:
            params = params.replace("{member.avatar}", member.avatar.url if member.avatar else member.default_avatar.url)
        return params

class DmInvoking:
    def __init__(self, ctx: EvelinaContext):
        self.ctx = ctx

    async def send(self, member: Union[User, Member], reason: str, case_id: str, formated_time: str):
        ctx = self.ctx
        res = await ctx.bot.db.fetchrow("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, ctx.command.name)
        if res:
            code = res["embed"]
            if formated_time == None:
                x = await self.ctx.bot.embed_build.convert(ctx, self.invoke_replacement(member, code.replace("{reason}", reason)))
            else:
                x = await self.ctx.bot.embed_build.convert(ctx, self.invoke_replacement(member, code.replace("{reason}", reason).replace("{duration}", formated_time).replace("{time}", formated_time)))
            await member.send(**x)
        return res is not None

    def invoke_replacement(self, member: Union[Member, User], params: str = None, code: str = None):
        if params is None:
            return None
        if "{member}" in params:
            params = params.replace("{member}", str(member))
        if "{member.id}" in params:
            params = params.replace("{member.id}", str(member.id))
        if "{member.name}" in params:
            params = params.replace("{member.name}", member.name)
        if "{member.nick}" in params:
            params = params.replace("{member.nick}", member.nick or member.display_name)
        if "{member.display}" in params:
            params = params.replace("{member.display}", member.display_name)
        if "{member.mention}" in params:
            params = params.replace("{member.mention}", member.mention)
        if "{member.discriminator}" in params:
            params = params.replace("{member.discriminator}", member.discriminator)
        if "{member.avatar}" in params:
            params = params.replace("{member.avatar}", member.avatar.url if member.avatar else member.default_avatar.url)
        return params

class EvelinaHelp(Help):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def send_bot_help(self, mapping: Mapping[Cog | None, List[Command[Any, Callable[..., Any], Any]]]) -> Coroutine[Any, Any, None]:
        await self.context.send(f"{self.context.author.mention}: <https://evelina.bot/commands>, join the discord server @ <https://evelina.bot/discord>")

    async def send_group_help(self, group: Group):
        bot = self.context.bot
        ctx = self.context
        cog_name = group.cog_name
        if (group.hidden or cog_name and cog_name.lower() in ["owner", "jishaku", "auth", "helper"]) and self.context.author.id not in bot.owner_ids:
            staff = await ctx.bot.db.fetchrow("SELECT * FROM team_members WHERE user_id = $1", self.context.author.id)
            if not staff:
                embed = Embed(color=colors.ERROR, description=f"{emojis.DENY} {self.context.author.mention}: No command called `{self.context.message.content}` found")
                return await self.context.send(embed=embed)
        embeds = []
        bot = self.context.bot
        i = 0
        sorted_commands = sorted(group.commands, key=lambda command: command.qualified_name.lower())
        for command in sorted_commands:
            i += 1
            def format_cooldown(cooldown):
                cooldown_str = str(cooldown)
                match = re.search(r'per:\s*(\d+(\.\d+)?)', cooldown_str)
                if match:
                    seconds = float(match.group(1))
                    return f"{int(seconds)} seconds" if seconds.is_integer() else f"{seconds} seconds"
                return "N/A"
            params = list(command.clean_params.keys())
            if command.extras:
                params.append("flags")
            embed = Embed(color=colors.NEUTRAL, title=f"Command: {command.qualified_name}", description=command.description if command.description else command.help)
            embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else bot.user.default_avatar.url)
            embed.add_field(name="Aliases", value=f"{', '.join(a for a in command.aliases) if len(command.aliases) > 0 else 'N/A'}", inline=True)
            embed.add_field(name="Parameters", value=', '.join(params) if params else 'N/A', inline=True)
            if command.cooldown and command.brief:
                information = f"{emojis.COOLDOWN} {format_cooldown(command.cooldown)}\n{emojis.WARNING} {command.brief.title()}"
            elif command.cooldown:
                information = f"{emojis.COOLDOWN} {format_cooldown(command.cooldown)}"
            elif command.brief:
                information = f"{emojis.WARNING} {command.brief.title()}"
            else:
                information = "N/A"
            embed.add_field(name="Information", value=information, inline=True)
            flags = []
            for flag, desc in command.extras.items():
                flags.append(f"`--{flag}`: {desc}")
            if flags:
                embed.add_field(name="Optional Flags", value="\n".join(flags), inline=False)
            embed.add_field(name="Usage", value = f"""```js\nSyntax: {self.context.clean_prefix}{command.qualified_name} {' '.join([f'[{a}]' for a in command.clean_params]) if command.clean_params else ''}{' [flags]' if command.extras else ''}\n{f'Example: {self.context.clean_prefix}{command.usage}' if command.usage else ''}\n```""", inline=False)
            embed.set_footer(text=f"Page: {i}/{len(group.commands)} {'・ Aliases: ' + ', '.join(group.aliases) if group.aliases else ''} ・ Module: {command.cog_name.lower() + '.py' if command.cog_name else 'N/A'}")
            embeds.append(embed)
        await self.context.paginator(embeds)

    async def send_command_help(self, command: Command):
        bot = self.context.bot
        ctx = self.context
        cog_name = command.cog_name
        if (command.hidden or cog_name and cog_name.lower() in ["owner", "jishaku", "auth", "helper"]) and self.context.author.id not in bot.owner_ids:
            staff = await ctx.bot.db.fetchrow("SELECT * FROM team_members WHERE user_id = $1", self.context.author.id)
            if not staff:
                embed = Embed(color=colors.ERROR, description=f"{emojis.DENY} {self.context.author.mention}: No command called `{self.context.message.content}` found")
                return await self.context.send(embed=embed)
        def format_cooldown(cooldown):
            cooldown_str = str(cooldown)
            match = re.search(r'per:\s*(\d+(\.\d+)?)', cooldown_str)
            if match:
                seconds = float(match.group(1))
                return f"{int(seconds)} seconds" if seconds.is_integer() else f"{seconds} seconds"
            return "N/A"
        params = command.clean_params
        params = list(command.clean_params.keys())
        if command.extras:
            params.append("flags")
        embed = Embed(color=colors.NEUTRAL, title=f"Command: {command.qualified_name}", description=command.description if command.description else command.help)
        embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else bot.user.default_avatar.url)
        embed.add_field(name="Aliases", value=f"{', '.join(a for a in command.aliases) if len(command.aliases) > 0 else 'N/A'}", inline=True)
        embed.add_field(name="Parameters", value=', '.join(params) if params else 'N/A', inline=True)
        if command.cooldown and command.brief:
            information = f"{emojis.COOLDOWN} {format_cooldown(command.cooldown)}\n{emojis.WARNING} {command.brief.title()}"
        elif command.cooldown:
            information = f"{emojis.COOLDOWN} {format_cooldown(command.cooldown)}"
        elif command.brief:
            information = f"{emojis.WARNING} {command.brief.title()}"
        else:
            information = "N/A"
        embed.add_field(name="Information", value=information, inline=True)
        flags = []
        for flag, desc in command.extras.items():
            flags.append(f"`--{flag}`: {desc}")
        if flags:
            embed.add_field(name="Optional Flags", value="\n".join(flags), inline=False)
        embed.add_field(name="Usage", value=f"""```js\nSyntax: {self.context.clean_prefix}{command.qualified_name} {' '.join([f'[{a}]' for a in command.clean_params]) if command.clean_params else ''}{' [flags]' if command.extras else ''}\n{f'Example: {self.context.clean_prefix}{command.usage}' if command.usage else ''}\n```""", inline=False)
        embed.set_footer(text=f"Page: 1/1 ・ Module: {command.cog_name.lower() + '.py' if command.cog_name else 'N/A'}")
        await self.context.send(embed=embed)

    async def send_warning_message(self, error: str):
        return await self.context.send_warning(error)