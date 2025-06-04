from contextlib import suppress
from copy import copy
from datetime import datetime
from io import BytesIO, StringIO
from typing import (TYPE_CHECKING, Any, Dict, List, Optional, Self, TypedDict,
                    Unpack, cast)

import config
from discord import (AllowedMentions, ButtonStyle, Color, Embed, File, Guild,
                     HTTPException, Member, Message, MessageReference)
from discord.ext.commands import Command, CommandError
from discord.ext.commands import Context as BaseContext
from discord.ext.commands import FlagConverter as DefaultFlagConverter
from discord.ext.commands import Group, UserInputError
from discord.ui import Button, View
from discord.utils import cached_property
from tools.client import views
from tools.managers.paginator import Paginator
from tools.utilities.text import shorten
from tools.utilities.typing import Typing

if TYPE_CHECKING:
    from tools.bleed import Bleed


class FieldDict(TypedDict, total=False):
    name: str
    value: str
    inline: bool


class FooterDict(TypedDict, total=False):
    text: Optional[str]
    icon_url: Optional[str]


class AuthorDict(TypedDict, total=False):
    name: Optional[str]
    icon_url: Optional[str]


class ButtonDict(TypedDict, total=False):
    url: Optional[str]
    emoji: Optional[str]
    style: Optional[ButtonStyle]
    label: Optional[str]


class MessageKwargs(TypedDict, total=False):
    content: Optional[str]
    tts: Optional[bool]
    allowed_mentions: Optional[AllowedMentions]
    reference: Optional[MessageReference]
    mention_author: Optional[bool]
    delete_after: Optional[float]

    # Embed Related
    url: Optional[str]
    title: Optional[str]
    color: Optional[Color]
    image: Optional[str]
    description: Optional[str]
    thumbnail: Optional[str]
    footer: Optional[FooterDict]
    author: Optional[AuthorDict]
    fields: Optional[List[FieldDict]]
    timestamp: Optional[datetime]
    view: Optional[View]
    buttons: Optional[List[ButtonDict]]


class Context(BaseContext):
    bot: "Bleed"
    guild: Guild

    def typing(self) -> Typing:
        return Typing(self)

    @cached_property
    def parameters(self):
        data = {}
        if command := self.command:
            if parameters := command.parameters:
                for name, parameter in parameters.items():
                    data[name] = ParameterParser(self).get(name, **parameter)

        return data

    @cached_property
    def replied_message(self) -> Message:
        if (reference := self.message.reference) and isinstance(
            reference.resolved, Message
        ):
            return reference.resolved

    async def send(self, *args, **kwargs):
        kwargs["files"] = kwargs.get("files") or []
        if file := kwargs.pop("file", None):
            kwargs["files"].append(file)

        if embed := kwargs.get("embed"):
            if not embed.color:
                embed.color = config.Color.neutral  # Default color
            if embed.title:
                embed.title = shorten(embed.title, 256)
            if embed.description:
                embed.description = shorten(embed.description, 4096)
            for field in embed.fields:
                embed.set_field_at(
                    index=embed.fields.index(field),
                    name=field.name,
                    value=field.value[:1024],
                    inline=field.inline,
                )
            if hasattr(embed, "_attachments") and embed._attachments:
                for attachment in embed._attachments:
                    if isinstance(attachment, File):
                        kwargs["files"].append(
                            File(
                                copy(attachment.fp),
                                filename=attachment.filename,
                            )
                        )
                    elif isinstance(attachment, tuple):
                        response = await self.bot.session.get(attachment[0])
                        if response.status == 200:
                            kwargs["files"].append(
                                File(
                                    BytesIO(await response.read()),
                                    filename=attachment[1],
                                )
                            )

        if embeds := kwargs.get("embeds"):
            for embed in embeds:
                if not embed.color:
                    embed.color = config.Color.neutral  # Default color
                if embed.title:
                    embed.title = shorten(embed.title, 256)
                if embed.description:
                    embed.description = shorten(embed.description, 4096)
                for field in embed.fields:
                    embed.set_field_at(
                        index=embed.fields.index(field),
                        name=field.name,
                        value=field.value[:1024],
                        inline=field.inline,
                    )
                if hasattr(embed, "_attachments") and embed._attachments:
                    for attachment in embed._attachments:
                        if isinstance(attachment, File):
                            kwargs["files"].append(
                                File(
                                    copy(attachment.fp),
                                    filename=attachment.filename,
                                )
                            )
                        elif isinstance(attachment, tuple):
                            response = await self._state._get_client().session.get(
                                attachment[0]
                            )
                            if response.status == 200:
                                kwargs["files"].append(
                                    File(
                                        BytesIO(await response.read()),
                                        filename=attachment[1],
                                    )
                                )

        if content := (args[0] if args else kwargs.get("content")):
            content = str(content)
            if len(content) > 4000:
                kwargs["content"] = (
                    f"Response too large to send (`{len(content)}/4000`)"
                )
                kwargs["files"].append(
                    File(
                        StringIO(content),
                        filename="reiResult.txt",
                    )
                )
                if args:
                    args = args[1:]

        return await super().send(*args, **kwargs)

    async def send_help(self, command: Command | Group = None):
        command_obj: Command | Group = command or self.command

        embed = Embed(
            color=config.Color.neutral,
            title=(
                ("Command: " if isinstance(command_obj, Group) else "Command: ")
                + command_obj.qualified_name
            ),
            description=command_obj.help,
        )
        embed.set_author(
            name=f"{self.bot.user.display_name} help",
            icon_url=self.bot.user.display_avatar,
        )

        embed.add_field(
            name="",
            value=(
                f"```\nSyntax: {self.prefix}{command_obj.qualified_name} {command_obj.usage or ''}"
                + (
                    f"\nExample: {self.prefix}{command_obj.qualified_name} {command_obj.example}"
                    if command_obj.example
                    else ""
                )
                + "```"
            ),
            inline=False,
        )

        await self.send(embed=embed)

    async def add_check(self: "Context"):
        await self.message.add_reaction("✅")

    async def thumbsup(self: "Context"):
        await self.message.add_reaction("👍")

    async def neutral(
        self: "Context",
        description: str,
        emoji: str = "",
        color=config.Color.neutral,
        **kwargs: Any,
    ) -> Message:
        """Send a neutral embed."""
        # Create embed with only description and color
        embed = Embed(
            description=f"{emoji} {description}",
            color=color,
        )

        if previous_load := getattr(self, "previous_load", None):
            cancel_load = kwargs.pop("cancel_load", False)
            result = await previous_load.edit(embed=embed, **kwargs)
            if cancel_load:
                delattr(self, "previous_load")
            return result

        # Pass remaining kwargs to send()
        return await self.send(embed=embed, **kwargs)

    async def utility(
        self: "Context",
        description: str,
        emoji: str = "",
        color=config.Color.neutral,
        **kwargs: Any,
    ) -> Message:
        """Send a neutral embed."""
        # Create embed with only description and color
        embed = Embed(
            description=f"{emoji} {self.author.mention}: {description}",
            color=color,
        )

        if previous_load := getattr(self, "previous_load", None):
            cancel_load = kwargs.pop("cancel_load", False)
            result = await previous_load.edit(embed=embed, **kwargs)
            if cancel_load:
                delattr(self, "previous_load")
            return result

        # Pass remaining kwargs to send()
        return await self.send(embed=embed, **kwargs)

    async def approve(
        self: "Context",
        description: str,
        emoji=config.Emoji.approve,
        **kwargs: Any,
    ) -> Message:
        """Send an approve embed."""
        color = kwargs.pop("color", config.Color.approve)

        embed = Embed(
            description=f"{emoji} {self.author.mention}: {description}",
            color=color,
            **kwargs,
        )
        if previous_load := getattr(self, "previous_load", None):
            cancel_load = kwargs.pop("cancel_load", False)
            result = await previous_load.edit(embed=embed, **kwargs)
            if cancel_load:
                delattr(self, "previous_load")
            return result

        return await self.send(embed=embed, **kwargs)

    async def warn(
        self: "Context",
        description: str,
        emoji=config.Emoji.warn,
        **kwargs: Any,
    ) -> Message:
        """Send an warn embed."""
        color = kwargs.pop("color", config.Color.warn)

        embed = Embed(
            description=f"{emoji} {self.author.mention}: {description}",
            color=color,
            **kwargs,
        )
        if previous_load := getattr(self, "previous_load", None):
            cancel_load = kwargs.pop("cancel_load", False)
            result = await previous_load.edit(embed=embed, **kwargs)
            if cancel_load:
                delattr(self, "previous_load")
            return result

        return await self.send(embed=embed, **kwargs)

    async def deny(
        self: "Context",
        description: str,
        emoji=config.Emoji.deny,
        **kwargs: Any,
    ) -> Message:
        """Send an error embed."""
        color = kwargs.pop("color", config.Color.deny)
        embed = Embed(
            description=f"{emoji} {self.author.mention}: {description}",
            color=color,
            **kwargs,
        )
        if previous_load := getattr(self, "previous_load", None):
            cancel_load = kwargs.pop("cancel_load", False)
            result = await previous_load.edit(embed=embed, **kwargs)
            if cancel_load:
                delattr(self, "previous_load")
            return result

        return await self.send(embed=embed, **kwargs)

    async def load(self, message: str, emoji: str = "", **kwargs: Any):
        """Send a loading embed."""
        color = kwargs.pop("color", config.Color.neutral)
        sign = "> " if "\n>" not in message else ""
        embed = Embed(
            color=color,
            description=f"{sign} {message}",
        )
        if not getattr(self, "previous_load", None):
            message = await self.send(embed=embed, **kwargs)
            setattr(self, "previous_load", message)
            return self.previous_load

        await self.previous_load.edit(embed=embed, **kwargs)
        return self.previous_load

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

    async def style_embed(self, embed: Embed) -> Embed:
        if (
            self.command
            and self.command.name == "createembed"
            and len(self.message.content.split()) > 1
        ):
            return embed

        if not embed.color:
            embed.color = config.Color.neutral

        if not embed.author and embed.title:
            embed.set_author(
                name=self.author.display_name,
                icon_url=self.author.display_avatar,
            )

        if embed.title:
            embed.title = shorten(embed.title, 256)

        if embed.description:
            embed.description = shorten(embed.description, 4096)

        for field in embed.fields:
            embed.set_field_at(
                index=embed.fields.index(field),
                name=field.name,
                value=shorten(field.value, 1024),
                inline=field.inline,
            )

        return embed

    async def prompt(self, message: str, member: Member = None, **kwargs):
        if member:
            view = views.ConfirmViewForUser(self, member)
            message = await self.send(
                embed=Embed(description=message), view=view, **kwargs
            )
            await view.wait()
            with suppress(HTTPException):
                await message.delete()
            if view.value is False:
                raise UserInputError("Prompt was denied.")

            return view.value
        view = views.ConfirmView(self)
        message = await self.send(embed=Embed(description=message), view=view, **kwargs)

        await view.wait()
        with suppress(HTTPException):
            await message.delete()

        if view.value is False:
            raise UserInputError("Prompt was denied.")
        return view.value

    async def embed(self, **kwargs: Unpack[MessageKwargs]) -> Message:
        return await self.send(**self.create(**kwargs))

    def create(self, **kwargs: Unpack[MessageKwargs]) -> Dict[str, Any]:
        """Create a message with the given keword arguments.

        Returns:
            Dict[str, Any]: The message content, embed, view and delete_after.
        """
        view = View()

        for button in kwargs.get("buttons") or []:
            if not button or not button.get("label"):
                continue

            view.add_item(
                Button(
                    label=button.get("label"),
                    style=button.get("style") or ButtonStyle.secondary,
                    emoji=button.get("emoji"),
                    url=button.get("url"),
                )
            )

        embed = (
            Embed(
                url=kwargs.get("url"),
                description=kwargs.get("description"),
                title=kwargs.get("title"),
                color=kwargs.get("color") or config.Color.neutral,
                timestamp=kwargs.get("timestamp"),
            )
            .set_image(url=kwargs.get("image"))
            .set_thumbnail(url=kwargs.get("thumbnail"))
            .set_footer(
                text=cast(dict, kwargs.get("footer", {})).get("text"),
                icon_url=cast(dict, kwargs.get("footer", {})).get("icon_url"),
            )
            .set_author(
                name=cast(dict, kwargs.get("author", {})).get("name", ""),
                icon_url=cast(dict, kwargs.get("author", {})).get("icon_url", ""),
            )
        )

        for field in kwargs.get("fields") or []:
            if not field:
                continue

            embed.add_field(
                name=field.get("name"),
                value=field.get("value"),
                inline=field.get("inline", False),
            )

        return {
            "content": kwargs.get("content"),
            "embed": embed,
            "view": kwargs.get("view") or view,
            "delete_after": kwargs.get("delete_after"),
        }


class ParameterParser:
    def __init__(self, ctx: "Context"):
        self.context = ctx

    def get(self, parameter: str, **kwargs) -> Any:
        for param in (parameter, *kwargs.get("aliases", ())):
            sliced = self.context.message.content.split()

            if kwargs.get("require_value", True) is False:
                return kwargs.get("default") if f"-{param}" not in sliced else True

            try:
                index = sliced.index(f"--{param}")

            except ValueError:
                return kwargs.get("default")

            result = []
            for word in sliced[index + 1 :]:
                if word.startswith("-"):
                    break

                result.append(word)

            if not (result := " ".join(result).replace("\\n", "\n").strip()):
                return kwargs.get("default")

            if choices := kwargs.get("choices"):
                if choice := tuple(
                    choice for choice in choices if choice.lower() == result.lower()
                ):
                    result = choice[0]

                else:
                    raise CommandError(f"Invalid choice for parameter `{param}`.")

            if converter := kwargs.get("converter"):
                if hasattr(converter, "convert"):
                    result = self.context.bot.loop.create_task(
                        converter().convert(self.ctx, result)
                    )

                else:
                    try:
                        result = converter(result)

                    except Exception as e:
                        raise CommandError(
                            f"Invalid value for parameter `{param}`."
                        ) from e

            if isinstance(result, int):
                if result < kwargs.get("minimum", 1):
                    raise CommandError(
                        f"The **minimum input** for parameter `{param}` is `{kwargs.get('minimum', 1)}`"
                    )

                if result > kwargs.get("maximum", 100):
                    raise CommandError(
                        f"The **maximum input** for parameter `{param}` is `{kwargs.get('maximum', 100)}`"
                    )

            return result

        return kwargs.get("default")


class FlagConverter(
    DefaultFlagConverter, case_insensitive=True, prefix="--", delimiter=" "
): ...
