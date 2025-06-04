"""
Copyright 2024 Samuel Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from dataclasses import dataclass
from types import TracebackType
from typing import (TYPE_CHECKING, Awaitable, Callable, List, Literal,
                    Optional, Self, Type, TypedDict, TypeVar, Union, Unpack)

import config
from aiomisc import PeriodicCallback
from core.client.cache.redis import Redis
from core.client.network.types import CoroFunc
from core.managers.paginator import Paginator
from discord import (ButtonStyle, Embed, File, Guild, HTTPException,
                     Interaction, Member, Message, TextChannel, Thread,
                     VoiceChannel)
from discord.ext.commands import Context
from discord.ext.commands import Context as DefaultContext
from discord.ext.commands import UserInputError
from discord.ui import Button as UI_Button
from discord.ui import View, button
from discord.utils import cached_property, get
from xxhash import xxh32_hexdigest

BE = TypeVar("BE", bound=BaseException)
import asyncio

if TYPE_CHECKING:
    from core.Mono import Mono


class EmbedField:
    """Represents a field in an Embed.
    Attributes
    -----------
    name: :class:`str`
    value: :class:`str`
    inline: :class:`bool`
    """

    def __init__(self, name: str, value: str, inline: bool = False):
        self.name = name
        self.value = value
        self.inline = inline


class EmbedAuthor:
    """Represents an author in an Embed.
    Attributes
    -----------
    name: :class:`str`
    icon_url: :class:`str`
    """

    def __init__(self, name: str, icon_url: str):
        self.name = name
        self.icon_url = icon_url


class EmbedFooter:
    """Represents a footer in an Embed.
    Attributes
    -----------
    text: :class:`str`
    icon_url: :class:`str`
    """

    def __init__(self, text: str, icon_url: str):
        self.text = text
        self.icon_url = icon_url


class MessageButton:
    """Represents a button in a message.
    Attributes
    ------------
    style: :class:`discord.ButtonStyle`
    label: :class:`str`
    emoji: :class:`str`
    url: :class:`str`
    disabled: :class:`bool`
    """

    def __init__(
        self,
        style: ButtonStyle,
        label: Union[str, None],
        emoji: Optional[str] = None,
        url: Optional[str] = None,
        disabled: Optional[bool] = False,
        check: Optional[CoroFunc] = None,
        callback: Optional[CoroFunc] = None,
    ):
        self.style = style
        self.label = label
        self.emoji = emoji
        self.url = url
        self.disabled = disabled
        self.check = check
        self.callback = callback


class MessageKwargs(TypedDict, total=False):
    content: str
    title: str
    url: str
    color: int
    author: EmbedAuthor
    thumbnail: str
    image: str
    footer: EmbedFooter
    description: str
    fields: List[EmbedField]
    view: View
    delete_after: int
    file: File
    files: List[File]
    buttons: List[MessageButton]


@dataclass
class MessageData:
    content: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    color: Optional[int] = 0x1C1F26
    author: Optional[EmbedAuthor] = EmbedAuthor("", "")
    thumbnail: Optional[str] = None
    image: Optional[str] = None
    footer: Optional[EmbedFooter] = EmbedFooter("", "")
    description: Optional[str] = None
    fields: Optional[List[EmbedField]] = None
    view: Optional[View] = None
    delete_after: Optional[float] = None
    file: Optional[File] = None
    files: Optional[List[File]] = None
    buttons: Optional[List[MessageButton]] = None


class Loading:
    callback: Optional[PeriodicCallback]
    ctx: Context
    channel: Union[VoiceChannel, TextChannel, Thread]

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.channel = ctx.channel
        self.callback = None

    @property
    def redis(self) -> Redis:
        return self.ctx.bot.redis

    @property
    def key(self) -> str:
        return xxh32_hexdigest(f"loader:{self.channel.id}")

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
            try:
                self.callback.stop()
                # Wait a short time for the callback to stop
                await asyncio.sleep(0.1)
            except Exception:
                pass  # Suppress any exceptions during cleanup


class View(View):
    ctx: Context

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def callback(self, interaction: Interaction, button: UI_Button):
        raise NotImplementedError

    async def disable_buttons(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore

    async def on_timeout(self) -> None:
        self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.warn(f"this is {self.ctx.author.mention}'s interaction")

        return interaction.user == self.ctx.author


class Confirmation(View):
    value: Optional[bool]

    def __init__(self, ctx: Context, *, timeout: Optional[int] = 60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.value = None

    @button(label="Approve", style=ButtonStyle.green)
    async def approve(
        self,
        interaction: Interaction,
        button: UI_Button,
    ):
        self.value = True
        self.stop()

    @button(label="Decline", style=ButtonStyle.danger)
    async def decline(
        self,
        interaction: Interaction,
        button: UI_Button,
    ):
        self.value = False
        self.stop()


class Context(DefaultContext):
    bot: "Mono"
    guild: Guild
    author: Member
    response: Optional[Message] = None

    @cached_property
    def replied_message(self: "Context") -> Optional[Message]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, Message):
            return ref.resolved

    async def add_check(self: "Context"):
        await self.message.add_reaction("✅")

    async def send(self: "Context", *args, **kwargs) -> Message:
        embeds: List[Embed] = kwargs.get("embeds", [])
        if embed := kwargs.get("embed"):
            embeds.append(embed)

        for embed in embeds:
            self.style(embed)

        if patch := kwargs.pop("patch", None):
            kwargs.pop("reference", None)

            if args:
                kwargs["content"] = args[0]

            self.response = await patch.edit(**kwargs)
        else:
            self.response = await super().send(*args, **kwargs)

        return self.response

    def loading(self, *args: str, **kwargs) -> Loading:
        if args:
            self.bot.loop.create_task(self.neutral(*args))

        return Loading(self)

    async def neutral(
        self,
        *args: str,
        **kwargs,
    ) -> Message:
        """
        Send a neutral embed.
        """

        embed = Embed(
            description="> "
            + "\n".join(
                ("" if len(args) == 1 or index == len(args) - 1 else "") + str(arg)
                for index, arg in enumerate(args)
            ),
            color=kwargs.pop("color", config.Color.base),
        )
        return await self.send(embed=embed, **kwargs)

    async def approve(
        self,
        *args: str,
        **kwargs,
    ) -> Message:
        """
        Send a success embed.
        """

        embed = Embed(
            description="> "
            + "\n".join(
                ("" if len(args) == 1 or index == len(args) - 1 else "") + str(arg)
                for index, arg in enumerate(args)
            ),
            color=kwargs.pop("color", config.Color.approve),
        )
        return await self.send(embed=embed, **kwargs)

    async def warn(
        self,
        *args: str,
        **kwargs,
    ) -> Message:
        """
        Send an error embed.
        """

        embed = Embed(
            description="> "
            + "\n".join(
                ("" if len(args) == 1 or index == len(args) - 1 else "") + str(arg)
                for index, arg in enumerate(args)
            ),
            color=kwargs.pop("color", config.Color.warn),
        )
        return await self.send(embed=embed, **kwargs)

    async def error(self: "Context", value: str, *args, **kwargs) -> Message:
        patch: Optional[Message] = kwargs.pop("patch", None)
        reference: Optional[Message] = kwargs.pop("reference", None)

        embed = Embed(
            description=("> " if not ">" in value else "") + value,
            color=config.Color.deny,
            *args,
            **kwargs,
        )

        return await self.send(embed=embed, patch=patch, reference=reference)

    async def shazam(
        self: "Context",
        value: str,
        cover_art: Optional[str] = None,
        footer: Optional[str] = None,
        *args,
        **kwargs,
    ) -> Message:
        patch: Optional[Message] = kwargs.pop("patch", None)
        reference: Optional[Message] = kwargs.pop("reference", None)

        embed = Embed(
            description=value,
            color=config.Color.neutral,
            *args,
            **kwargs,
        )

        if cover_art:
            embed.set_thumbnail(url=cover_art)
        if footer:
            embed.set_footer(text=footer)

        return await self.send(embed=embed, patch=patch, reference=reference)

    async def paginate(self, pages: List[Embed], **kwargs) -> Message:
        paginator = Paginator(pages, self, **kwargs)
        await paginator.start()
        return paginator.message

    async def autopaginator(
        self: Self, embed: Embed, description: List[str], split: int = 10, **kwargs
    ) -> Message:
        pages = []
        chunks = [description[i : i + split] for i in range(0, len(description), split)]
        total_pages = len(chunks)

        for index, chunk in enumerate(chunks):
            page_embed = Embed(
                title=embed.title,
                color=embed.color,
                description="\n".join(chunk),
                timestamp=embed.timestamp,
            )

            if embed.author:
                page_embed.set_author(
                    name=embed.author.name,
                    icon_url=embed.author.icon_url,
                )

            if embed.thumbnail:
                page_embed.set_thumbnail(url=embed.thumbnail.url)

            if embed.image:
                page_embed.set_image(url=embed.image.url)

            if total_pages > 1:
                page_embed.set_footer(
                    text=f"Page {index + 1}/{total_pages} ({len(description)} Entries)"
                )

            pages.append(page_embed)

        return await self.paginate(pages=pages, **kwargs)

        return Loading(self)

    async def embed(self: Self, **kwargs: Unpack[MessageKwargs]) -> Message:
        """
        Sends an embedded message.
        """
        data = MessageData(**kwargs)  # type: ignore

        if data.buttons:
            data.view = View()
            data.view.interaction_check = next(
                (button.check for button in data.buttons if button and button.check),
                None,
            )  # type: ignore

            for button in data.buttons:
                if button is None:
                    continue
                _button = UI_Button(
                    **{
                        key: value
                        for key, value in button.__dict__.items()
                        if key not in ["check", "callback"]
                    }
                )
                _button.callback = button.callback  # type: ignore
                data.view.add_item(_button)

        embed = (
            Embed(
                description=data.description,
                title=data.title,
                url=data.url,
                color=data.color,
            )
            .set_image(url=data.image)
            .set_thumbnail(url=data.thumbnail)
            .set_author(name=data.author.name, icon_url=data.author.icon_url)  # type: ignore
            .set_footer(text=data.footer.text, icon_url=data.footer.icon_url)  # type: ignore
        )

        list(
            map(
                lambda field: embed.add_field(
                    name=field.name, value=field.value, inline=field.inline
                ),
                data.fields or [],
            )
        )

        return await super().send(
            content=data.content,
            embed=embed,
            view=data.view,
            delete_after=data.delete_after,
            file=data.file,
            files=data.files,
        )  # type: ignore

    async def prompt(
        self,
        *args: str,
        timeout: int = 60,
        delete_after: bool = True,
        check: Optional[Callable[[Self], Awaitable[bool]]] = None,
    ) -> Literal[True]:
        key = xxh32_hexdigest(f"prompt:{self.author.id}:{self.command.qualified_name}")
        async with self.bot.redis.get_lock(key):
            # Perform the check if provided
            if check:
                try:
                    result = await check(self)
                    if not result:
                        raise UserInputError("Prompt check failed")
                except Exception as e:
                    raise UserInputError(f"Prompt check failed: {str(e)}")

            embed = Embed(
                description="\n".join(
                    ("" if len(args) == 1 or index == len(args) - 1 else "") + str(arg)
                    for index, arg in enumerate(args)
                ),
                color=config.Color.warn,
            )
            view = Confirmation(self, timeout=timeout)

            try:
                message = await self.send(embed=embed, view=view)
            except HTTPException as exc:
                raise UserInputError("Failed to send prompt message!") from exc

            await view.wait()
            if delete_after:
                await message.delete()

            if view.value is True:
                return True

            raise UserInputError("Confirmation prompt not approved!")

    def style(self: "Context", embed: Embed) -> Embed:
        if not embed.color:
            embed.color = config.Color.base

        return embed
