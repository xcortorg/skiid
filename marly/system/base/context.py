from __future__ import annotations

from config import Emojis, Color as ColorConfig
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TYPE_CHECKING,
    Tuple,
    Literal,
    Unpack,
    TypedDict,
    cast,
    Self,
)

from discord import (
    AllowedMentions,
    ButtonStyle,
    Color,
    DMChannel,
    GroupChannel,
    Guild,
    Interaction,
    Message,
    MessageReference,
    Embed,
    PartialMessageable,
    Role,
)
from discord.ui import View, Button
from discord.ext.commands import Context as BaseContext, UserInputError
from contextlib import suppress

# from discord.ext.commands.context import MISSING
from discord.ext.commands import CommandError
from discord.ext.commands.core import Command, Group
from asyncio import TimeoutError as ATimeoutError
from discord.ui import View, Button as UI_Button
from discord.ui import button

# from discord.ext.commands.parameters import Parameter
# from discord.ext.commands.view import StringView
from discord.utils import cached_property

from .paginator import Paginator

if TYPE_CHECKING:
    from tools.utils import hierachy, manageable


if TYPE_CHECKING:
    from system import Marly


class Confirmation(View):
    value: Optional[bool]

    def __init__(self, ctx: Context, *, timeout: Optional[int] = 60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.value = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.warn("This confirmation is not for you!")
            return False
        return True

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


def get_index(iterable: Optional[Tuple[Any, Any]], index: int) -> Optional[Any]:
    if not iterable or (type(iterable) is not tuple and index != 0):
        return None

    if type(iterable) is not tuple and index == 0:
        return iterable

    return iterable[index] if len(iterable) > index else None


class Context(BaseContext):
    bot: "Marly"
    guild: Guild  # type: ignore

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response: Optional[Message] = None

    @cached_property
    def replied_message(self: "Context") -> Optional[Message]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, Message):
            return ref.resolved

    async def manage(self, role: Role) -> None:
        """Check if the role is manageable by the author or the bot."""
        if manageable(role, self) and hierachy(role, self):
            return

        raise CommandError(f"{role} is not **manageable** by either yourself or me.")

    async def group(self) -> Optional[Message]:
        if not self.invoked_subcommand:
            return await self.send_help(self.command)
        return

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

    async def add_check(self: "Context"):
        await self.message.add_reaction("✅")

    async def thumbsup(self: "Context"):
        await self.message.add_reaction("👍")

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
                color=kwargs.get("color") or 0xF0F0F0,
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
            "reference": kwargs.get("reference"),
            "mention_author": kwargs.get("mention_author", False),
        }

    async def approve(
        self, message: str, *args: str, **kwargs: Unpack[MessageKwargs]
    ) -> Message:
        kwargs["description"] = (
            f"{Emojis.Embeds.APPROVE} {self.author.mention}: {message}"
            + ("\n" + "\n".join(args) if args else "")
        )
        kwargs["color"] = ColorConfig.approve
        return await self.embed(
            **kwargs,
        )

    async def warn(
        self, message: str, *args: str, **kwargs: Unpack[MessageKwargs]
    ) -> Message:
        kwargs["description"] = (
            f"{Emojis.Embeds.WARN} {self.author.mention}: {message}"
            + ("\n" + "\n".join(args) if args else "")
        )
        kwargs["color"] = ColorConfig.warn
        return await self.embed(
            **kwargs,
        )

    async def deny(
        self, message: str, *args: str, **kwargs: Unpack[MessageKwargs]
    ) -> Message:
        kwargs["description"] = (
            f"{Emojis.Embeds.DENY} {self.author.mention}: {message}"
            + ("\n" + "\n".join(args) if args else "")
        )
        kwargs["color"] = ColorConfig.deny
        return await self.embed(
            **kwargs,
        )

    async def neutral(
        self,
        message: str = "",
        *args: str,
        emoji: str = "",
        **kwargs: Unpack[MessageKwargs],
    ) -> Message:
        kwargs["description"] = f"{emoji} {self.author.mention}: {message}" + (
            "\n" + "\n".join(args) if args else ""
        )
        return await self.embed(
            **kwargs,
        )

    async def utility(
        self,
        message: str = "",
        *args: str,
        emoji: str = "",
        **kwargs: Unpack[MessageKwargs],
    ) -> Message:
        kwargs["description"] = f"{emoji}{message}" + (
            "\n" + "\n".join(args) if args else ""
        )
        return await self.embed(
            **kwargs,
        )

    async def prompt(
        self: "Context",
        value: str,
        *args,
        timeout: int = 30,
        delete_after: bool = True,
        **kwargs,
    ) -> Literal[True]:
        embed = Embed(
            description=(
                f"{Emojis.Embeds.WARN} {self.author.mention}: {value}\n"
                + "\n".join(
                    ("" if len(args) == 1 or index == len(args) - 1 else "") + str(arg)
                    for index, arg in enumerate(args)
                )
            ),
            color=ColorConfig.warn,
            **kwargs,
        )

        view = Confirmation(self, timeout=timeout)
        message = await self.send(embed=embed, view=view)

        await view.wait()
        if delete_after:
            await message.delete()

        if view.value is True:
            return True

        raise UserInputError("Prompt was declined.")

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

    async def send_help(self, command: Command | Group = None):
        command_obj: Command | Group = command or self.command

        commands_list = []
        if isinstance(command_obj, Group):
            commands_list.append(command_obj)
            for subcmd_name, subcmd in command_obj.all_commands.items():
                if subcmd not in commands_list:
                    commands_list.append(subcmd)
        else:
            commands_list = [command_obj]

        pages = []
        total_pages = len(commands_list)
        for index, subcommand in enumerate(commands_list):
            embed = Embed(
                color=ColorConfig.neutral,
                title=(
                    (
                        "Group Command: "
                        if isinstance(subcommand, Group)
                        else "Command: "
                    )
                    + subcommand.qualified_name
                ),
                description=(subcommand.help or "")  # Add null check here
                + (
                    f"\n{subcommand.customdescription}"
                    if getattr(subcommand, "customdescription", None)
                    else ""
                ),
            )
            embed.set_author(
                name=f"{self.bot.user.display_name} help",
                icon_url=self.bot.user.display_avatar,
            )
            embed.add_field(
                name="Usage",
                value=(
                    f"```syntax: {self.prefix}{subcommand.qualified_name} {subcommand.usage or ''}"
                    + (
                        f"\nExample: {self.prefix}{subcommand.qualified_name} {subcommand.example}"
                        if subcommand.example
                        else ""
                    )
                    + "```"
                ),
                inline=False,
            )
            if total_pages > 1:
                embed.set_footer(
                    text=f"Page {index + 1}/{total_pages} ({total_pages} Entries)"
                )
            pages.append(embed)

        return await self.paginate(pages=pages)

    def style(self: "Context", embed: Embed) -> Embed:
        if not embed.color:
            embed.color = ColorConfig.baseColor

        return embed
