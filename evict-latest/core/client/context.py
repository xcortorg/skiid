from __future__ import annotations

import discord
import config

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Optional,
    Type,
    cast,
    TypeVar,
)
from aiomisc import PeriodicCallback

from aiohttp import ClientSession
from discord import (
    ButtonStyle,
    Colour,
    Guild,
    HTTPException,
    Member,
    Message,
    PartialMessage,
    Attachment,
    TextChannel,
    Thread,
    VoiceChannel,
    Webhook
)

from discord import WebhookMessage
from discord.ui import View, button
from discord.context_managers import Typing as DefaultTyping
from discord.ext.commands import Command, Context as OriginalContext, UserInputError
from discord.types.embed import EmbedType
from discord.utils import cached_property

from typing import List, Union
from xxhash import xxh32_hexdigest

from tools import View, quietly_delete
from managers.paginator import Paginator
from core.client.database import Database, Settings
from core.client.redis import Redis

if TYPE_CHECKING:
    from main import Evict
    from types import TracebackType

BE = TypeVar("BE", bound=BaseException)

class Approve(discord.ui.View):
    def __init__(self, ctx: Context, user: Optional[Member] = None, *, timeout: Optional[int] = 60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.user = user
        self.value = None

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        if interaction.user != self.user:
            await interaction.warn(f"Only **{self.user}** can respond to this!")
            return
        
        self.value = True
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.warn(f"Only **{self.user}** can respond to this!")
            return
        
        self.value = False
        self.stop()

class Confirmation(View):
    value: Optional[bool]

    def __init__(self, ctx: Context, *, timeout: Optional[int] = 60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.value = None

    @button(label="Approve", style=ButtonStyle.green)
    async def approve(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.value = True
        self.stop()

    @button(label="Decline", style=ButtonStyle.danger)
    async def decline(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.value = False
        self.stop()


class Typing(DefaultTyping):
    ctx: Context

    def __init__(self, ctx: Context):
        super().__init__(ctx.channel)
        self.ctx = ctx

    async def do_typing(self) -> None:
        if self.ctx.settings.reskin:
            return

        return await super().do_typing()


class Loading:
    callback: Optional[PeriodicCallback]
    ctx: Context
    channel: VoiceChannel | TextChannel | Thread

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.channel = ctx.channel
        self.callback = None

    @property
    def redis(self) -> Redis:
        return self.ctx.bot.redis

    @property
    def key(self) -> str:
        return f"loader:{self.channel.id}"

    async def locked(self) -> bool:
        if await self.redis.exists(self.key):
            return True

        await self.redis.set(self.key, 1, ex=30)
        return False

    async def task(self) -> None:
        if not self.ctx.response:
            return

        value = self.ctx.response.embeds[0].description  # type: ignore
        if not value:
            return

        value = value.replace("", "")
        if not value.endswith("..."):
            value += "."
        else:
            value = value.rstrip(".")

        await self.ctx.neutral(value, patch=self.ctx.response)

    async def __aenter__(self) -> None:
        if await self.locked():
            return

        self.callback = PeriodicCallback(self.task)
        self.callback.start(10, delay=2)

    async def __aexit__(
        self,
        exc_type: Optional[Type[BE]],
        exc: Optional[BE],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.redis.delete(self.key)
        if self.callback:
            self.callback.stop()


class Context(OriginalContext):
    bot: "Evict"
    guild: Guild
    author: Member
    channel: VoiceChannel | TextChannel | Thread
    command: Command[Any, ..., Any]
    settings: Settings
    response: Optional[Message] = None

    @property
    def session(self) -> ClientSession:
        return self.bot.session

    @property
    def db(self) -> Database:
        return self.bot.database

    @cached_property
    def replied_message(self) -> Optional[Message]:
        reference = self.message.reference
        if reference and isinstance(reference.resolved, Message):
            return reference.resolved

        return None

    @property
    def color(self) -> Colour:
        return Colour.dark_embed()
        # color = self.me.color
        # if color == Colour.default():
        #     color = Colour.dark_embed()

        # return color

    def typing(self) -> Typing:
        return Typing(self)

    def loading(self, *args: str, **kwargs) -> Loading:
        if args:
            self.bot.loop.create_task(self.neutral(*args))

        return Loading(self)

    async def paginate(self, pages: List[Embed], **kwargs) -> Message:
        """
        Send a paginated message.
        """
        paginator = Paginator(
            entries=pages, ctx=self, **kwargs)
        await paginator.start()
        return paginator.message

    async def reskin_enabled(self) -> bool:
        """
        Check if reskin is enabled for the current user.
        """
        return await self.bot.db.fetchrow(
            """
            SELECT * FROM reskin
            WHERE user_id = $1 
            AND toggled = $2
            """,
            self.author.id,
            True,
        )

    async def reply(self, *args, **kwargs) -> WebhookMessage:
        """
        Send a message, using a webhook if reskin is enabled.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM reskin
            WHERE user_id = $1
            """, 
            self.author.id
        )

        if (
            record
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
                webhook = await self.channel.create_webhook(name="evict - reskin")

            kwargs.update(
                {
                    "avatar_url": record["avatar"],
                    "username": record["username"],
                    "wait": True,
                }
            )

            if kwargs.get("delete_after"):
                kwargs.pop("delete_after")

            return await webhook.send(*args, **kwargs)
        else:
            return await super().reply(*args, **kwargs)

    async def send(self, *args, **kwargs) -> Union[Message, WebhookMessage]:
        """
        Send a message, using a webhook if reskin is enabled.
        """
        if kwargs.pop("no_reference", False):
            reference = None
        else:
            reference = kwargs.pop("reference", self.message)

        patch = cast(Optional[Message], kwargs.pop("patch", None))

        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM reskin
            WHERE user_id = $1
            """, 
            self.author.id
        )

        if (
            record
            and self.guild.me.guild_permissions.manage_webhooks
            and await self.reskin_enabled()
        ):
            if isinstance(self.channel, Thread):
                return await super().send(*args, **kwargs)

            webhook = await self.get_webhook()

            webhook_kwargs = {
                "avatar_url": record["avatar"],
                "username": record["username"],
                "wait": True,
            }

            if "file" in kwargs and kwargs["file"] is None:
                kwargs.pop("file")

            if "delete_after" in kwargs:
                delete_after = kwargs.pop("delete_after")

                try:
                    if patch:
                        self.response = await webhook.edit_message(**kwargs)
                    else:
                        return await webhook.send(*args, **kwargs)

                except Exception as e:
                    print(f"Error sending message: {e}")

            return await webhook.send(*args, **{**kwargs, **webhook_kwargs})
        else:
            return await super().send(*args, **kwargs)

    async def get_attachment(self) -> Optional[Attachment]:
        """
        Get a discord attachment from the channel.
        """
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

    async def neutral(
        self,
        message: str,
        delete_after: bool = False,
        patch: Optional[Message] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Message:
        """
        Sends a neutral message, or edits an existing message if patch is provided.
        """
        if args:
            formatted_args = "\n".join(args)
            message += "\n" + formatted_args

        if delete_after and isinstance(message, (Message, PartialMessage)):
            await quietly_delete(message)

        embed = Embed(
            color=kwargs.pop("color", config.COLORS.NEUTRAL),
            description=f"{self.author.mention}: {message}",
        )

        if patch:
            await patch.edit(embed=embed)
            return patch

        return await self.send(embed=embed)

    async def approve(
        self,
        message: str,
        delete_after: bool = False,
        patch: Optional[Message] = None,
        *args: Any,
    ) -> Message:
        """
        Sends an approval message, or edits an existing message if patch is provided.
        """
        if args:
            formatted_args = "\n".join(args)
            message += "\n" + formatted_args

        if delete_after and isinstance(message, (Message, PartialMessage)):
            await quietly_delete(message)

        embed = Embed(
            color=config.COLORS.APPROVE,
            description=f"{config.EMOJIS.CONTEXT.APPROVE} {self.author.mention}: {message}",
        )

        if patch:
            await patch.edit(embed=embed)
            return patch

        return await self.send(embed=embed)

    async def warn(
        self,
        message: str,
        delete_after: bool = False,
        patch: Optional[Message] = None,
        *args: Any,
    ) -> Message:
        """
        Sends a warning message, or edits an existing message if patch is provided.
        """
        if args:
            formatted_args = "\n".join(args)
            message += "\n" + formatted_args

        if delete_after and isinstance(message, (Message, PartialMessage)):
            await quietly_delete(message)

        embed = Embed(
            color=config.COLORS.WARN,
            description=f"{config.EMOJIS.CONTEXT.WARN} {self.author.mention}: {message}",
        )

        if patch:
            await patch.edit(embed=embed)
            return patch

        try:
            return await self.send(embed=embed)
        except discord.NotFound:
            return await super().send(embed=embed)
        
    async def vape(
        self,
        message: str,
        patch: Optional[Message] = None,
        *args: Any,
    ) -> Message:
        """
        Sends a vape message, or edits an existing message if patch is provided.
        """
        if args:
            formatted_args = "\n".join(args)
            message += "\n" + formatted_args

        embed = Embed(
            color=config.COLORS.NEUTRAL,
            description=f"{config.EMOJIS.CONTEXT.JUUL} {self.author.mention}: {message}",
        )

        if patch:
            await patch.edit(embed=embed)
            return patch

        try:
            return await self.send(embed=embed)
        except discord.NotFound:
            return await super().send(embed=embed)
        
    async def blunt(
        self,
        message: str,
        patch: Optional[Message] = None,
        *args: Any,
    ) -> Message:
        """
        Sends a blunt message, or edits an existing message if patch is provided.
        """
        if args:
            formatted_args = "\n".join(args)
            message += "\n" + formatted_args

        embed = Embed(
            color=config.COLORS.NEUTRAL,
            description=f"🚬 {self.author.mention}: {message}",
        )

        if patch:
            await patch.edit(embed=embed)
            return patch

        try:
            return await self.send(embed=embed)
        except discord.NotFound:
            return await super().send(embed=embed)

    async def check(self):
        """
        Add a checkmark reaction to the message.
        """
        return await self.message.add_reaction(config.EMOJIS.CONTEXT.APPROVE)

    async def prompt(
        self,
        *args: str,
        timeout: int = 60,
        delete_after: bool = True,
    ) -> Literal[True]:
        """
        An interactive reaction confirmation dialog.

        Raises UserInputError if the user denies the prompt.
        """
        key = f"prompt:{self.author.id}:{self.command.qualified_name}"
        async with self.bot.redis.get_lock(key):
            embed = Embed(
                description="\n".join(
                    ("" if len(args) == 1 or index == len(args) - 1 else "") + str(arg)
                    for index, arg in enumerate(args)
                ),
            )
            view = Confirmation(self, timeout=timeout)

            try:
                message = await self.send(embed=embed, view=view)
            except HTTPException as exc:
                raise UserInputError("Failed to send prompt message!") from exc

            await view.wait()
            if delete_after:
                await quietly_delete(message)

            if view.value is True:
                return True

            raise UserInputError("Confirmation prompt wasn't approved!")
        
    async def confirm(
        self,
        *args: str,
        user: Member,
        timeout: int = 60,
        delete_after: bool = True,
    ) -> bool:
        """
        An interactive reaction confirmation dialog.

        Raises UserInputError if the user denies the prompt.
        """
        key = f"confirm:{self.author.id}:{self.command.qualified_name}"
        async with self.bot.redis.get_lock(key):
            embed = Embed(
                    description="\n".join(
                        ("" if len(args) == 1 or index == len(args) - 1 else "") + str(arg)
                        for index, arg in enumerate(args)
                    ),
                )
            view = Approve(self, user=user, timeout=timeout)

            try:
                message = await self.send(embed=embed, view=view)
            except HTTPException as exc:
                    raise UserInputError("Failed to send prompt message!") from exc

            await view.wait()
            if delete_after:
                await quietly_delete(message)

            if view.value is True:
                    return True

            raise UserInputError("Confirmation prompt wasn't approved!")

    async def currency(self, text, **kwargs):
        """
        Send a message with the author's mention and a currency emoji.
        """
        embed = Embed(
            description=f"{self.author.mention}: {text}",
        )
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, delete_after=delete_after)
    

    async def deposit(self, text, **kwargs):
        """
        Send a message with the author's mention and a currency emoji.
        """
        embed = Embed(
            description=f"{self.author.mention}: {text}",
        )
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, delete_after=delete_after)
    
    async def withdraw(self, text, **kwargs):
        """
        Send a message with the author's mention and a currency emoji.
        """
        embed = Embed(
            description=f"{self.author.mention}: {text}",
        )
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, delete_after=delete_after)

    async def get_webhook(self) -> Webhook:
        """
        Get or create a webhook for the current channel.
        """
        if isinstance(self.channel, Thread):
            raise ValueError("Cannot create webhooks in threads")

        webhooks = [
            w 
            for w in await self.channel.webhooks()
            if w.user and w.user.id == self.bot.user.id
        ]

        if webhooks:
            return webhooks[0]
        
        return await self.channel.create_webhook(name="evict - reskin")

class Embed(discord.Embed):
    def __init__(
        self,
        value: Optional[str] = None,
        *,
        colour: int | Colour | None = None,
        color: int | Colour | None = None,
        title: Any | None = None,
        type: EmbedType = "rich",
        url: Any | None = None,
        description: Any | None = None,
        timestamp: datetime | None = None,
    ):
        description = description or value
        super().__init__(
            colour=colour,
            color=color or config.COLORS.APPROVE,
            title=title,
            type=type,
            url=url,
            description=description[:4096] if description else None,
            timestamp=timestamp,
        )


discord.Embed = Embed
