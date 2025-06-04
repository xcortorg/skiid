import chat_exporter
import secrets
import os
import json

import discord
import config
import datetime
import asyncio
import logging
from typing import Union

from contextlib import suppress
from secrets import token_urlsafe
from typing import Annotated, Dict, List, Literal, Optional, TypedDict, cast, overload
from logging import getLogger

from discord import (
    ActionRow,
    AllowedMentions,
    ButtonStyle,
    CategoryChannel,
    Color,
    Embed,
    Guild,
    HTTPException,
    Interaction,
    Member,
    Message,
    PartialMessage,
    PermissionOverwrite,
    Role,
    TextChannel,
)
from core.client import FlagConverter, Context as OriginalContext

from discord.ui import View, Button, button
from discord import Emoji, ComponentType
from discord.utils import find
from discord.components import Button as ButtonComponent
from discord.ext.commands import group, has_permissions, Cog, flag, check, Range

from tools.conversion.discord import StrictRole, TouchableMember
from tools.parser import Script, parse
from tools.formatter import codeblock, vowel
from tools import CompositeMetaClass, MixinMeta

from managers.paginator import Paginator

log = getLogger("evict/ticket")


class Context(OriginalContext):
    channel: TextChannel


class TicketConfig(TypedDict):
    guild_id: int
    channel_id: int
    message_id: int
    staff_ids: list[int]
    blacklisted_ids: list[int]
    channel_name: Optional[str]


class TicketButton(TypedDict):
    identifier: str
    guild_id: int
    template: Optional[str]
    category_id: Optional[int]
    topic: Optional[str]


class TicketChannel(TypedDict):
    identifier: str
    guild_id: int
    channel_id: int
    user_id: int


class ButtonFlags(FlagConverter):
    style: Literal["blurple", "grey", "gray", "green", "red"] = flag(
        default="green",
        aliases=["color"],
    )
    emoji: Optional[str] = flag(
        aliases=["emote"],
    )


def in_ticket():
    async def predicate(ctx: Context):
        if not ctx.guild:
            return False

        record = cast(
            Optional[TicketChannel],
            await ctx.bot.db.fetchrow(
                """
                SELECT *
                FROM ticket.open
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                ctx.guild.id,
                ctx.channel.id,
            ),
        )
        return bool(record)

    return check(predicate)


class DeleteTicket(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="Close Ticket",
        emoji=config.EMOJIS.TICKETS.TRASH,
        style=ButtonStyle.red,
        custom_id="ticket:close",
    )
    async def close(self, interaction: Interaction, button: Button):
        await interaction.response.send_message(
            "Use `;ticket close` to close this ticket.", ephemeral=True
        )


class Ticket(MixinMeta, metaclass=CompositeMetaClass):
    """
    Create tickets for users to contact the staff.
    """

    @staticmethod
    def sanitize_data(data):
        if isinstance(data, dict):
            return {k: Ticket.sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Ticket.sanitize_data(item) for item in data]
        elif isinstance(data, discord.PartialEmoji):
            return str(data)
        elif isinstance(data, discord.Emoji):
            return str(data)
        elif hasattr(data, 'id'):
            return str(data.id)
        elif hasattr(data, '__dict__'):
            return str(data)
        return data

    async def get_buttons_data(self, channel):
        messages = [message async for message in channel.history(limit=50)]
        buttons_data = []

        for message in messages:
            if message.components:
                for row in message.components:
                    for component in row.children:
                        if component.type == ComponentType.button:
                            label = component.label if component.label else ""
                            emoji_url = component.emoji.url if component.emoji else None

                            buttons_data.append(
                                {
                                    "label": label or emoji_url,
                                    "type": "button",
                                    "style": str(component.style),
                                    "custom_id": component.custom_id,
                                    "url": (
                                        component.url
                                        if component.style == ButtonStyle.link
                                        else None
                                    ),
                                }
                            )

        return buttons_data

    async def export_transcript(self, ctx, channel: TextChannel):
        channel = channel or ctx.channel
        log_id = secrets.token_hex(8)
        logs_directory = "/root/tickets"
        file_path = f"{logs_directory}/{log_id}.json"
        os.makedirs(logs_directory, exist_ok=True)

        transcript_data = await self.generate_transcript(channel)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, indent=4, ensure_ascii=False)

        await ctx.send(f"Transcript saved: https://logs.evict.bot/{log_id}")

    async def generate_transcript(self, channel: TextChannel):
        transcript = {
            "channel": self.get_channel_data(channel),
            "embeds": [],
            "mentions": [],
            "messages": [],
            "reactions": [],
            "buttons": [],
            "ticket": self.get_ticket_data(channel),
            "users": [],
            "attachments": [],
        }

        messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]

        for message in messages:
            transcript["messages"].append(self.get_message_data(message))
            transcript["embeds"].extend(self.get_embed_data(message))
            transcript["mentions"].extend(self.get_mention_data(message))
            transcript["reactions"].extend(self.get_reaction_data(message))
            transcript["buttons"].extend(await self.get_buttons_data(channel))
            transcript["attachments"].extend(self.get_attachment_data(message))

        transcript["users"] = self.get_users_data(messages)

        return transcript

    def get_channel_data(self, channel):
        return {
            "created_at": channel.created_at.isoformat(),
            "id": str(channel.id),
            "name": channel.name,
            "type": str(channel.type),
        }

    def get_ticket_data(self, channel):
        return {
            "channel_id": channel.id,
            "closed_at": None,
            "closed_by_id": None,
            "guild_id": channel.guild.id,
            "opened_by_id": None,
            "reason": "Assistance requested",
        }

    def get_message_data(self, message):
        return {
            "id": message.id,
            "author_id": message.author.id,
            "channel_id": message.channel.id,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
            "edited_timestamp": (
                message.edited_at.isoformat() if message.edited_at else None
            ),
            "pinned": message.pinned,
            "timestamp": message.created_at.isoformat(),
            "mentions": self.get_mention_data(message),
        }

    def get_embed_data(self, message):
        embeds = []
        for embed in message.embeds:
            embed_data = {
                "title": embed.title,
                "description": embed.description,
                "url": embed.url,
                "color": embed.color.value if embed.color else None,
                "message_id": message.id,
                "author": {
                    "name": embed.author.name if embed.author else None,
                    "icon_url": embed.author.icon_url if embed.author else None,
                    "url": embed.author.url if embed.author else None,
                },
                "footer": {
                    "text": embed.footer.text if embed.footer else None,
                    "icon_url": embed.footer.icon_url if embed.footer else None,
                },
                "timestamp": embed.timestamp.isoformat() if embed.timestamp else None,
                "thumbnail": {"url": embed.thumbnail.url if embed.thumbnail else None},
                "image": {"url": embed.image.url if embed.image else None},
                "fields": [
                    {"name": field.name, "value": field.value, "inline": field.inline}
                    for field in embed.fields
                ],
            }
            embeds.append(embed_data)
        return embeds

    def get_mention_data(self, message):
        return [
            {"message_id": message.id, "user_id": mention.id}
            for mention in message.mentions
        ]

    def get_reaction_data(self, message):
        reactions = []
        for reaction in message.reactions:
            # Get the emoji name properly
            if isinstance(reaction.emoji, discord.Emoji):
                name = reaction.emoji.name
                image_url = str(reaction.emoji.url)
            else:
                # For Unicode emojis
                name = reaction.emoji
                image_url = None

            reaction_data = {
                "message_id": message.id,
                "name": name,
                "count": reaction.count,
                "image": image_url,
                "active": True,
            }
            reactions.append(reaction_data)
        return reactions

    def get_users_data(self, messages):
        users = {}
        for message in messages:
            if message.author.id not in users:
                users[message.author.id] = self.get_user_data(message.author, message)
        return list(users.values())

    def get_user_data(self, user, message):
        return {
            "accent_color": user.accent_color.value if user.accent_color else None,
            "author_id": str(user.id),
            "avatar": str(user.avatar.url) if user.avatar else None,
            "banner": str(user.banner.url) if user.banner else None,
            "bot": user.bot,
            "channel_id": message.channel.id,
            "content": "",
            "created_at": user.created_at.isoformat(),
            "discriminator": user.discriminator,
            "edited_timestamp": None,
            "global_name": user.global_name,
            "id": user.id,
            # "mfa_enabled": False,
            "pinned": False,
            "system": user.system,
            "timestamp": message.created_at.isoformat(),
            "username": user.name,
        }

    def get_attachment_data(self, message):
        return [
            {
                "file_size": attachment.size,
                "filename": attachment.filename,
                "message_id": message.id,
                "url": attachment.url,
            }
            for attachment in message.attachments
        ]

    @overload
    async def get_ticket_message(
        self,
        guild: Guild,
        record: dict,
        partial: Literal[True],
    ) -> PartialMessage: ...

    @overload
    async def get_ticket_message(
        self,
        guild: Guild,
        record: dict,
        partial: Literal[False] = False,
    ) -> Optional[Message]: ...

    async def get_ticket_message(
        self,
        guild: Guild,
        record: dict,
        partial: bool = False,
    ) -> Optional[Message | PartialMessage]:
        channel = guild.get_channel_or_thread(record["channel_id"])
        if not channel:
            return

        if partial:
            return channel.get_partial_message(record["message_id"])  # type: ignore

        try:
            return await channel.fetch_message(record["message_id"])  # type: ignore
        except HTTPException:
            return None

    async def create_ticket_transcript(
        self, channel: TextChannel, reason: str = "No reason provided"
    ) -> dict:
        transcript = {
            "channel": {
                "created_at": channel.created_at.isoformat(),
                "id": str(channel.id),
                "name": channel.name,
                "type": str(channel.type),
            },
            "embeds": [],
            "mentions": [],
            "messages": [],
            "reactions": [],
            "buttons": [],
            "ticket": {
                "channel_id": channel.id,
                "closed_at": None,
                "closed_by_id": None,
                "guild_id": channel.guild.id,
                "opened_by_id": None,
                "reason": reason,
            },
            "users": [],
            "attachments": [],
        }

        messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
        users_dict = {}

        for message in messages:
            message_data = {
                "id": str(message.id),
                "author_id": str(message.author.id),
                "channel_id": str(message.channel.id),
                "content": message.content,
                "created_at": message.created_at.isoformat(),
                "edited_timestamp": message.edited_at.isoformat() if message.edited_at else None,
                "pinned": message.pinned,
                "timestamp": message.created_at.isoformat(),
            }
            transcript["messages"].append(message_data)

            if message.author.id not in users_dict:
                users_dict[message.author.id] = {
                    "accent_color": str(message.author.accent_color) if message.author.accent_color else None,
                    "author_id": str(message.author.id),
                    "avatar": str(message.author.avatar.url) if message.author.avatar else None,
                    "banner": str(message.author.banner.url) if message.author.banner else None,
                    "bot": message.author.bot,
                    "channel_id": str(message.channel.id),
                    "content": "",
                    "created_at": message.author.created_at.isoformat(),
                    "discriminator": message.author.discriminator,
                    "edited_timestamp": None,
                    "global_name": message.author.global_name,
                    "id": str(message.author.id),
                    "pinned": False,
                    "system": message.author.system,
                    "timestamp": message.created_at.isoformat(),
                    "username": message.author.name,
                }

            for embed in message.embeds:
                embed_data = {
                    "title": embed.title,
                    "description": embed.description,
                    "url": embed.url,
                    "color": str(embed.color.value) if embed.color else None,
                    "message_id": str(message.id),
                    "author": {
                        "name": embed.author.name if embed.author else None,
                        "icon_url": str(embed.author.icon_url) if embed.author and embed.author.icon_url else None,
                        "url": str(embed.author.url) if embed.author and embed.author.url else None,
                    },
                    "footer": {
                        "text": embed.footer.text if embed.footer else None,
                        "icon_url": str(embed.footer.icon_url) if embed.footer and embed.footer.icon_url else None,
                    },
                    "timestamp": embed.timestamp.isoformat() if embed.timestamp else None,
                    "thumbnail": {"url": str(embed.thumbnail.url) if embed.thumbnail else None},
                    "image": {"url": str(embed.image.url) if embed.image else None},
                    "fields": [
                        {"name": field.name, "value": field.value, "inline": field.inline}
                        for field in embed.fields
                    ],
                }
                transcript["embeds"].append(embed_data)

            for attachment in message.attachments:
                attachment_data = {
                    "file_size": attachment.size,
                    "filename": attachment.filename,
                    "message_id": str(message.id),
                    "url": attachment.url,
                }
                transcript["attachments"].append(attachment_data)

            for reaction in message.reactions:
                reaction_data = {
                    "message_id": str(message.id),
                    "name": str(reaction.emoji),
                    "count": reaction.count,
                    "image": str(reaction.emoji.url) if hasattr(reaction.emoji, 'url') else None,
                    "active": True,
                }
                transcript["reactions"].append(reaction_data)

        transcript["users"] = list(users_dict.values())

        if message.components:
            for row in message.components:
                for component in row.children:
                    if component.type == ComponentType.button:
                        button_data = {
                            "label": component.label or "",
                            "type": "button",
                            "style": str(component.style),
                            "custom_id": component.custom_id,
                            "url": component.url if component.style == ButtonStyle.link else None,
                        }
                        transcript["buttons"].append(button_data)

        return transcript

    async def get_channel_member_ids(self, channel: TextChannel) -> dict:
        member_ids = set()

        for member in channel.guild.members:
            if channel.permissions_for(member).read_messages:
                member_ids.add(member.id)

        return {"ids": list(member_ids)}

    @Cog.listener("on_guild_channel_delete")
    async def ticket_channel_delete(self, channel: TextChannel):
        if not isinstance(channel, TextChannel):
            return

        await self.bot.db.execute(
            """
            DELETE FROM ticket.open
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            channel.guild.id,
            channel.id,
        )

    @Cog.listener("on_interaction")
    async def ticket_create(self, interaction: Interaction):
        """
        Listener for the ticket interaction.
        """

        if (
            not interaction.data
            or not interaction.guild
            or not isinstance(interaction.user, Member)
        ):
            return

        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.endswith("ticket_create"):
            return

        guild = interaction.guild
        member = interaction.user
        identifier = custom_id.split(":", 1)[0]

        config = cast(
            Optional[TicketConfig],
            await self.bot.db.fetchrow(
                """
                SELECT *
                FROM ticket.config
                WHERE guild_id = $1
                """,
                guild.id,
            ),
        )
        record = cast(
            Optional[TicketButton],
            await self.bot.db.fetchrow(
                """
                SELECT *
                FROM ticket.button
                WHERE guild_id = $1
                AND identifier = $2
                """,
                guild.id,
                identifier,
            ),
        )
        if not config or not record:
            return await interaction.response.send_message(
                embed=Embed(
                    description=(
                        "This button shouldn't exist anymore! \n> Please contact a staff member about this"
                    ),
                ),
                ephemeral=True,
            )

        elif member.id in config["blacklisted_ids"] or [
            role for role in member.roles if role.id in config["blacklisted_ids"]
        ]:
            return await interaction.response.send_message(
                embed=Embed(
                    description="You're not allowed to create tickets!",
                ),
                ephemeral=True,
            )

        ticket = cast(
            Optional[TicketChannel],
            await self.bot.db.fetchrow(
                """
                SELECT *
                FROM ticket.open
                WHERE guild_id = $1
                AND user_id = $2
                AND identifier = $3
                """,
                guild.id,
                member.id,
                identifier,
            ),
        )
        if ticket:
            channel = guild.get_channel(ticket["channel_id"])
            if channel:
                return await interaction.response.send_message(
                    embed=Embed(
                        description=f"You already have an open ticket - {channel.mention}",
                    ),
                    ephemeral=True,
                )

        await interaction.response.defer(ephemeral=True, thinking=True)
        category = guild.get_channel(record["category_id"] or 0)
        if not isinstance(category, CategoryChannel):
            category = None

        overwrites: Dict[Role | Member, PermissionOverwrite] = {
            guild.default_role: PermissionOverwrite(
                view_channel=False,
                read_messages=False,
            ),
        }
        for target in (
            member,
            *[
                role
                for role_id in config["staff_ids"]
                if (role := guild.get_role(role_id))
            ],
        ):
            overwrites[target] = PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
                mention_everyone=False,
            )

        try:
            channel = await guild.create_text_channel(
                name=parse(
                    config["channel_name"] or f"ticket-{member.name}",
                    [guild, member],
                )[:100],
                category=category,
                topic=parse(record["topic"] or "", [guild, member]),
                overwrites=overwrites,
                reason=f"Ticket opened by {member} ({member.id})",
            )
        except HTTPException as exc:
            return await interaction.followup.send(
                embed=Embed(
                    description=(
                        "Falied to create a ticket channel!"
                        f"\n> {codeblock(exc.text)}"
                    ),
                ),
                ephemeral=True,
            )

        await self.bot.db.execute(
            """
            INSERT INTO ticket.open (
                identifier,
                guild_id,
                channel_id,
                user_id
            ) VALUES ($1, $2, $3, $4)
            ON CONFLICT (identifier, guild_id, user_id)
            DO UPDATE SET
                channel_id = EXCLUDED.channel_id
            """,
            identifier,
            guild.id,
            channel.id,
            member.id,
        )

        await interaction.followup.send(
            embed=Embed(
                description=f"Created a new ticket - {channel.mention}",
            ),
            ephemeral=True,
        )

        if record["template"]:
            script = Script(
                record["template"],
                [guild, member, channel],
            )
            with suppress(HTTPException):
                message = await script.send(
                    channel,
                    allowed_mentions=AllowedMentions.all(),
                )

                await message.pin()

        else:
            view = DeleteTicket()
            embed = Embed(
                description="Be patient and staff will be right with you.",
                timestamp=datetime.datetime.now(),
            )
            embed.set_author(
                name=f"{interaction.guild.name}", icon_url=f"{interaction.guild.icon}"
            )
            embed.set_footer(text="evict.bot", icon_url=interaction.client.user.avatar)
            message = await channel.send(
                embed=embed, content=f"Welcome {interaction.user.mention}", view=view
            )

            await message.pin()

    @group(
        aliases=["tickets"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def ticket(self, ctx: Context) -> Message:
        """
        Manage support tickets.
        """

        return await ctx.send_help(ctx.command)

    @ticket.group(
        name="panel",
        aliases=["message", "link"],
        invoke_without_command=True,
        example="1234567890",
    )
    @has_permissions(manage_channels=True)
    async def ticket_panel(self, ctx: Context, message: Message) -> Message:
        """
        Set the ticket panel message.
        """

        if message.guild != ctx.guild:
            return await ctx.warn("The message must be in this server!")

        elif message.author != ctx.guild.me:
            return await ctx.warn("The message must be from me!")

        await self.bot.db.execute(
            """
            INSERT INTO ticket.config (guild_id, channel_id, message_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                channel_id = EXCLUDED.channel_id,
                message_id = EXCLUDED.message_id
            """,
            ctx.guild.id,
            message.channel.id,
            message.id,
        )
        return await ctx.approve(
            f"Successfully set that [`message`]({message.jump_url}) as a ticket panel. Use `{ctx.clean_prefix}ticket button` to attach buttons",
        )

    @ticket_panel.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def ticket_panel_remove(self, ctx: Context) -> Message:
        """
        Remove the ticket panel message.
        """

        record = cast(
            Optional[TicketConfig],
            await self.bot.db.fetchrow(
                """
                DELETE FROM ticket.config
                WHERE guild_id = $1
                RETURNING *
                """,
                ctx.guild.id,
            ),
        )
        if not record:
            return await ctx.warn("The ticket panel hasn't been set yet!")

        message = await self.get_ticket_message(ctx.guild, record, partial=True)
        if message:
            with suppress(HTTPException):
                await message.delete()

        return await ctx.approve("Successfully removed the ticket panel")

    @ticket.group(
        name="button",
        aliases=["option"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def ticket_button(self, ctx: Context) -> Message:
        """
        Control the buttons on the panel.
        """

        return await ctx.send_help(ctx.command)

    @ticket_button.command(
        name="add",
        aliases=["button"],
        example="Support",
    )
    @has_permissions(manage_channels=True)
    async def ticket_button_add(self, ctx: Context, *, label: str) -> Message:
        """
        Add a button to the ticket panel.

        Accepts the following flags:
        `--color`: `blurple`, `grey`, `green` or `red`.
        `--emoji`: A unicode or custom emoji.
        """

        label, flags = await ButtonFlags().find(ctx, label)
        if not label:
            return await ctx.warn("You must provide a button label!")

        record: TicketConfig = await self.bot.db.fetchrow(
            """
            SELECT *
            FROM ticket.config
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if not record:
            return await ctx.warn(
                "The ticket panel hasn't been set yet!",
                f"Use `{ctx.clean_prefix}ticket panel <message>` to set it",
            )

        message = await self.get_ticket_message(ctx.guild, record)
        if not message:
            return await ctx.warn(
                "The ticket panel no longer exists!",
                f"Use `{ctx.clean_prefix}ticket panel <message>` to set it",
            )

        view = View()
        if message.components and isinstance(message.components[0], ActionRow):
            for child in message.components[0].children:
                if isinstance(child, ButtonComponent):
                    view.add_item(
                        Button(
                            style=child.style,
                            label=child.label,
                            disabled=child.disabled,
                            custom_id=child.custom_id,
                            emoji=child.emoji,
                        ),
                    )

        identifier = token_urlsafe(13)
        view.add_item(
            Button(
                style=getattr(
                    ButtonStyle,
                    flags.style,
                    ButtonStyle.green,
                ),
                label=label,
                emoji=flags.emoji,
                custom_id=f"{identifier}:ticket_create",
            ),
        )

        try:
            await message.edit(view=view)
        except HTTPException as exc:
            return await ctx.warn(
                "Something is wrong with your **button**!",
                codeblock(exc.text),
            )

        await self.bot.db.execute(
            """
            INSERT INTO ticket.button (identifier, guild_id)
            VALUES ($1, $2)
            ON CONFLICT (identifier, guild_id)
            DO NOTHING
            """,
            identifier,
            ctx.guild.id,
        )
        return await ctx.approve(
            f"Added button **{flags.emoji or ''} {label}** with identifier [`{identifier}`]({message.jump_url}). Use the identifier above to change what this button does.",
        )

    @ticket_button.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="1234567890",
    )
    @has_permissions(manage_channels=True)
    async def ticket_button_remove(self, ctx: Context, identifier: str) -> Message:
        """
        Remove a button from the ticket panel.

        You can use `ticket button list` to view all identifiers.
        """

        record: TicketConfig = await self.bot.db.fetchrow(
            """
            SELECT *
            FROM ticket.config
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if not record:
            return await ctx.warn(
                "The ticket panel hasn't been set yet!",
                f"Use `{ctx.clean_prefix}ticket panel <message>` to set it",
            )

        message = await self.get_ticket_message(ctx.guild, record)
        if not message:
            return await ctx.warn(
                "The ticket panel no longer exists!",
                f"Use `{ctx.clean_prefix}ticket panel <message>` to set it",
            )

        result = await self.bot.db.execute(
            """
            DELETE FROM ticket.button
            WHERE guild_id = $1
            AND identifier = $2
            """,
            ctx.guild.id,
            identifier,
        )
        if result == "DELETE 0":
            return await ctx.warn(
                f"A button with identifier [`{identifier}`]({message.jump_url}) doesn't exist!"
            )

        view = View()
        if message.components and isinstance(message.components[0], ActionRow):
            for child in message.components[0].children:
                if isinstance(child, ButtonComponent):
                    if (
                        child.custom_id
                        and child.custom_id.split(":", 1)[0] == identifier
                    ):
                        continue

                    view.add_item(
                        Button(
                            style=child.style,
                            label=child.label,
                            disabled=child.disabled,
                            custom_id=child.custom_id,
                            emoji=child.emoji,
                        ),
                    )

        try:
            await message.edit(view=view)
        except HTTPException as exc:
            return await ctx.warn(
                "Something is wrong with your **panel**!",
                codeblock(exc.text),
            )

        return await ctx.approve(
            f"Removed button with identifier [`{identifier}`]({message.jump_url})"
        )

    @ticket_button.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_channels=True)
    async def ticket_button_list(self, ctx: Context) -> Message:
        """
        View all button identifiers.
        """

        record: TicketConfig = await self.bot.db.fetchrow(
            """
            SELECT *
            FROM ticket.config
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if not record:
            return await ctx.warn(
                "The ticket panel hasn't been set yet!",
                f"Use `{ctx.clean_prefix}ticket panel <message>` to set it",
            )

        message = await self.get_ticket_message(ctx.guild, record)
        if not message:
            return await ctx.warn(
                f"The ticket panel no longer exists! Use `{ctx.clean_prefix}ticket panel <message>` to set it",
            )

        elif not message.components or not isinstance(message.components[0], ActionRow):
            return await ctx.warn("No buttons have been added yet!")

        children = message.components[0].children
        buttons = [
            f"**{button.emoji or ''} {button.label}** (`{record['identifier']}`)"
            for record in await self.bot.db.fetch(
                """
                SELECT identifier
                FROM ticket.button
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (
                button := find(
                    lambda b: b.custom_id
                    and b.custom_id.startswith(record["identifier"]),
                    children,
                )
            )
            and isinstance(button, ButtonComponent)
        ]
        if not buttons:
            return await ctx.warn("No buttons have been added yet!")

        paginator = Paginator(
            ctx,
            entries=buttons,
            embed=Embed(title="Ticket Buttons"),
        )
        return await paginator.start()

    @ticket.command(
        name="open",
        aliases=["welcome", "opening"],
        example="{user.mention} welcome!",
    )
    @has_permissions(manage_channels=True)
    async def ticket_welcome(
        self,
        ctx: Context,
        identifier: str,
        *,
        script: Script,
    ) -> Message:
        """
        Set the opening message for a ticket.
        """

        record = cast(
            Optional[TicketButton],
            await self.bot.db.fetchrow(
                """
                SELECT *
                FROM ticket.button
                WHERE guild_id = $1
                AND identifier = $2
                """,
                ctx.guild.id,
                identifier,
            ),
        )
        if not record:
            return await ctx.warn(
                f"A button with identifier `{identifier}` doesn't exist! Use `{ctx.clean_prefix}ticket button list` to view all identifiers",
            )

        await self.bot.db.execute(
            """
            UPDATE ticket.button
            SET template = $3
            WHERE guild_id = $1
            AND identifier = $2
            """,
            ctx.guild.id,
            identifier,
            script.template,
        )
        return await ctx.approve(
            f"Now sending {vowel(script.format)} message to tickets from button `{identifier}`"
        )

    @ticket.group(
        name="category",
        aliases=["redirect"],
        invoke_without_command=True,
        example="1234567890 tickets",
    )
    @has_permissions(manage_channels=True)
    async def ticket_category(
        self,
        ctx: Context,
        identifier: str,
        *,
        channel: CategoryChannel,
    ) -> Message:
        """
        Set the category for a ticket button.
        """

        record = cast(
            Optional[TicketButton],
            await self.bot.db.fetchrow(
                """
                SELECT *
                FROM ticket.button
                WHERE guild_id = $1
                AND identifier = $2
                """,
                ctx.guild.id,
                identifier,
            ),
        )
        if not record:
            return await ctx.warn(
                f"A button with identifier `{identifier}` doesn't exist! Use `{ctx.clean_prefix}ticket button list` to view all identifiers"
            )

        await self.bot.db.execute(
            """
            UPDATE ticket.button
            SET category_id = $3
            WHERE guild_id = $1
            AND identifier = $2
            """,
            ctx.guild.id,
            identifier,
            channel.id,
        )
        return await ctx.approve(
            f"Now redirecting tickets from button `{identifier}` to [`{channel.name}`]({channel.jump_url})"
        )

    @ticket.command(
        name="name",
        aliases=["channel"],
        example="example",
    )
    @has_permissions(manage_channels=True)
    async def ticket_name(
        self,
        ctx: Context,
        *,
        name: Range[str, 1, 100],
    ) -> Message:
        """
        Set the name for new ticket channels.
        """

        result = await self.bot.db.execute(
            """
            UPDATE ticket.config
            SET channel_name = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            name,
        )
        if result.endswith("0"):
            return await ctx.warn(
                f"The ticket panel hasn't been set yet! Use `{ctx.clean_prefix}ticket panel <message>` to set it"
            )

        return await ctx.approve(
            f"Now using `{name}` for ticket channel names. It will appear as **{parse(name, [ctx.guild, ctx.author])}**"
        )

    @ticket_category.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="1234567890",
    )
    @has_permissions(manage_channels=True)
    async def ticket_category_remove(
        self,
        ctx: Context,
        identifier: str,
    ) -> Message:
        """
        Remove the category for a ticket button.
        """

        record = cast(
            Optional[TicketButton],
            await self.bot.db.fetchrow(
                """
                SELECT *
                FROM ticket.button
                WHERE guild_id = $1
                AND identifier = $2
                """,
                ctx.guild.id,
                identifier,
            ),
        )
        if not record:
            return await ctx.warn(
                f"A button with identifier `{identifier}` doesn't exist! Use `{ctx.clean_prefix}ticket button list` to view all identifiers!"
            )

        await self.bot.db.execute(
            """
            UPDATE ticket.button
            SET category_id = NULL
            WHERE guild_id = $1
            AND identifier = $2
            """,
            ctx.guild.id,
            identifier,
        )
        return await ctx.approve(
            f"No longer redirecting tickets from button `{identifier}`"
        )

    @ticket.group(
        name="staff",
        invoke_without_command=True,
        example="@mod"
    )
    @has_permissions(manage_channels=True)
    async def ticket_staff(
        self,
        ctx: Context,
        *,
        role: Annotated[Role, StrictRole],
    ) -> Message:
        """
        Allow a role to see new tickets.
        """

        result = await self.bot.db.execute(
            """
            UPDATE ticket.config
            SET staff_ids = ARRAY_APPEND(staff_ids, $2::BIGINT)
            WHERE NOT staff_ids @> ARRAY[$2::BIGINT]
            AND guild_id = $1
            """,
            ctx.guild.id,
            role.id,
        )
        if result.endswith("0"):
            return await ctx.warn(f"{role.mention} is already allowed!")

        return await ctx.approve(
            f"Now allowing {role.mention} to see new tickets",
        )

    @ticket_staff.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="@mod"
    )
    @has_permissions(manage_channels=True)
    async def ticket_staff_remove(
        self,
        ctx: Context,
        *,
        role: Annotated[Role, StrictRole],
    ) -> Message:
        """
        Disallow a role from seeing tickets.
        """

        result = await self.bot.db.execute(
            """
            UPDATE ticket.config
            SET staff_ids = ARRAY_REMOVE(staff_ids, $2::BIGINT)
            WHERE guild_id = $1
            AND staff_ids @> ARRAY[$2::BIGINT]
            """,
            ctx.guild.id,
            role.id,
        )
        if result.endswith("0"):
            return await ctx.warn(f"{role.mention} already isn't allowed!")

        return await ctx.approve(
            f"No longer allowing {role.mention} to see new tickets",
        )

    @ticket_staff.command(
    name="list",
    aliases=["ls"],
    )
    @has_permissions(manage_channels=True)
    async def ticket_staff_list(self, ctx: Context) -> Message:
        roles = [
            f"{role.mention} (`{role.id}`)"
            for record in await self.bot.db.fetch(
                """
                SELECT UNNEST(staff_ids) AS role_id
                FROM ticket.config
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (role := ctx.guild.get_role(record["role_id"]))
        ]
        if not roles:
            return await ctx.warn("No roles have been allowed yet!")

        paginator = Paginator(
            ctx,
            entries=roles,
            embed=Embed(title="Ticket Staff"),
        )
        return await paginator.start()

    @ticket.group(
        name="ignore",
        aliases=["blacklist"],
        invoke_without_command=True,
        example="@ignore"
    )
    @has_permissions(manage_channels=True)
    async def ticket_ignore(
        self,
        ctx: Context,
        *,
        target: (
            Annotated[
                Role,
                StrictRole,
            ]
            | Annotated[Member, TouchableMember]
        ),
    ) -> Message:
        """
        Prevent a role or member from creating tickets.
        """

        result = await self.bot.db.execute(
            """
            UPDATE ticket.config
            SET blacklisted_ids = ARRAY_APPEND(blacklisted_ids, $2::BIGINT)
            WHERE NOT blacklisted_ids @> ARRAY[$2::BIGINT]
            AND guild_id = $1
            """,
            ctx.guild.id,
            target.id,
        )
        if result.endswith("0"):
            return await ctx.warn(f"{target.mention} is already blacklisted!")

        return await ctx.approve(
            f"No longer allowing {target.mention} to create tickets"
        )

    @ticket_ignore.command(
        name="remove",
        aliases=[
            "delete",
            "del",
            "rm",
        ],
        example="@ignore"
    )
    @has_permissions(manage_channels=True)
    async def ticket_ignore_remove(
        self,
        ctx: Context,
        *,
        target: Annotated[Role, StrictRole] | Annotated[Member, TouchableMember],
    ) -> Message:
        """
        Allow an entity to make tickets again.
        """

        result = await self.bot.db.execute(
            """
            UPDATE ticket.config
            SET blacklisted_ids = ARRAY_REMOVE(blacklisted_ids, $2::BIGINT)
            WHERE guild_id = $1
            AND blacklisted_ids @> ARRAY[$2::BIGINT]
            """,
            ctx.guild.id,
            target.id,
        )
        if result.endswith("0"):
            return await ctx.warn(f"{target.mention} isn't blacklisted!")

        return await ctx.approve(f"Now allowing {target.mention} to create tickets")

    @ticket_ignore.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_channels=True)
    async def ticket_ignore_list(self, ctx: Context) -> Message:
        """
        View all blacklisted entities.
        """

        targets = [
            f"{target.mention} (`{target.id}`)"
            for record in await self.bot.db.fetch(
                """
                SELECT UNNEST(blacklisted_ids) AS target_id
                FROM ticket.config
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (target := ctx.guild.get_member(record["target_id"]))
            or (target := ctx.guild.get_role(record["target_id"]))
        ]
        if not targets:
            return await ctx.warn("No members have been blacklisted yet!")

        paginator = Paginator(
            ctx,
            entries=targets,
            embed=Embed(title="Ticket Blacklisted"),
        )
        return await paginator.start()

    @ticket.command(
        name="add",
        aliases=["allow"],
        example="@x"
    )
    @in_ticket()
    @has_permissions(manage_channels=True)
    async def ticket_add(
        self,
        ctx: Context,
        target: Union[Member, Role],
    ) -> Message:
        """
        Add a role or member to the ticket.
        """
        
        await ctx.channel.set_permissions(
            target,
            view_channel=True,
            read_messages=True,
            read_message_history=True,
            send_messages=True,
            attach_files=True,
            embed_links=True,
            mention_everyone=False,
            reason=f"Granted access by {ctx.author} ({ctx.author.id}).",
        )
        return await ctx.approve(f"Now allowing {target.mention} to see this ticket")

    @ticket.command(
        name="deny",
        aliases=["block"],
        example="@x"
    )
    @in_ticket()
    @has_permissions(manage_channels=True)
    async def ticket_deny(
        self,
        ctx: Context,
        target: Union[Member, Role], 
    ) -> Message:
        """
        Remove a role or member's access to the ticket.
        """
        
        await ctx.channel.set_permissions(
            target,
            view_channel=False,
            read_messages=False,
            read_message_history=False,
            send_messages=False,
            attach_files=False,
            embed_links=False,
            mention_everyone=False,
            reason=f"Denied access by {ctx.author} ({ctx.author.id}).",
        )
        return await ctx.approve(f"Now denying {target.mention} access to this ticket")

    @ticket.command(
        name="remove",
        aliases=["hide"],
        example="@x"
    )
    @in_ticket()
    @has_permissions(manage_channels=True)
    async def ticket_remove(
        self,
        ctx: Context,
        target: Annotated[Role, StrictRole] | Annotated[Member, TouchableMember],
    ) -> Message:
        """
        Remove a role or member from the ticket.
        """

        await ctx.channel.set_permissions(
            target,
            overwrte=None,
            reason=f"Denied access by {ctx.author} ({ctx.author.id}).",
        )
        return await ctx.approve(
            f"No longer allowing {target.mention} to see this ticket"
        )

    def can_close_ticket():
        async def predicate(ctx: Context):
            if ctx.author.guild_permissions.manage_channels:
                return True
            
            config = await ctx.bot.db.fetchrow(
                """
                SELECT staff_ids
                FROM ticket.config
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            
            if not config:
                await ctx.warn("You're missing the `manage_channels` permission!")
                return False
            
            has_staff_role = any(role.id in config['staff_ids'] for role in ctx.author.roles)
            if not has_staff_role:
                await ctx.warn("You're missing the `manage_channels` permission!")
                return False
                
            return True
        
        return check(predicate)

    @ticket.command(
        name="close",
        aliases=["end"],
        example="Resolved",
        brief="manage channels"
    )
    @in_ticket()
    @can_close_ticket()
    async def ticket_close(
        self, ctx: Context, reason: str = "No reason provided."
    ) -> None:
        """
        Close an open ticket and forward the transcript.
        """
        transcript = await self.create_ticket_transcript(ctx.channel, reason)
        member_ids = await self.get_channel_member_ids(ctx.channel)
        channel_config = await self.bot.db.fetchrow(
            """
            SELECT *
            FROM ticket.logs
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if not channel_config:
            return await ctx.warn(f"Ticket logs haven't been set, run ``{ctx.clean_prefix}ticket logs`` to set it.")

        log_id = secrets.token_hex(8)
        logs_directory = "/root/tickets"
        file_path = f"{logs_directory}/{log_id}.json"
        member_ids_file_path = f"{logs_directory}/{log_id}_ids.json"

        logging_channel_id = channel_config["channel_id"]
        logging_channel = self.bot.get_channel(logging_channel_id)

        os.makedirs(logs_directory, exist_ok=True)

        await asyncio.gather(
            self.write_json(file_path, transcript),
            self.write_json(member_ids_file_path, member_ids)
        )

        await ctx.approve(
            f"Your logs can be found here: https://evict.bot/tickets/{log_id}"
        )
        await asyncio.sleep(5)
        await self.bot.db.execute(
            """
            DELETE FROM ticket.open
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            ctx.guild.id,
            ctx.channel.id,
        )

        embed = Embed(
            title="Ticket Closed",
            description=f"Your logs can be found here: https://evict.bot/tickets/{log_id}\n\n"
            f"{config.EMOJIS.CONTEXT.WARN} Ticket logging is currently in beta, please report any bugs you come across.",
            timestamp=datetime.datetime.now(),
        )

        await ctx.channel.delete(
            reason=f"Closed by {ctx.author} ({ctx.author.id}) - {reason}"
        )
        await logging_channel.send(embed=embed)

    async def write_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @ticket.command(name="setup")
    @has_permissions(manage_channels=True)
    async def ticket_setup(self, ctx: Context):
        """
        Automatically create a panel, ticket message, and category channel for your tickets.
        """

        identifier = token_urlsafe(13)

        embed = Embed(
            description="Click on the button below this message to create a ticket.",
            title="Create a ticket",
        )
        embed.set_author(
            name=f"{ctx.guild.name}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
        )

        category = await ctx.guild.create_category(name="Tickets")
        channel = await category.create_text_channel(name="tickets")

        view = View()
        create_ticket_button = Button(
            style=ButtonStyle.grey,
            label="Create Ticket",
            custom_id=f"{identifier}:ticket_create",
            emoji="🎟️",
        )
        view.add_item(create_ticket_button)

        try:
            message = await channel.send(embed=embed, view=view)
        except HTTPException as exc:
            return await ctx.warn(
                f"Something went wrong with sending the message: {exc.text}"
            )

        await self.bot.db.execute(
            """
            INSERT INTO ticket.config (guild_id, channel_id, message_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                channel_id = EXCLUDED.channel_id,
                message_id = EXCLUDED.message_id
            """,
            ctx.guild.id,
            channel.id,
            message.id,
        )

        await self.bot.db.execute(
            """
            INSERT INTO ticket.button (guild_id, identifier, category_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (identifier, guild_id) DO NOTHING
            """,
            ctx.guild.id,
            identifier,
            channel.id,
        )

        await self.bot.db.execute(
            """
            UPDATE ticket.button
            SET category_id = $3
            WHERE guild_id = $1
            AND identifier = $2
            """,
            ctx.guild.id,
            identifier,
            category.id,
        )

        await ctx.approve(
            f"Automatically set up ticket button with identifier `{identifier}`, ticket panel has been sent to {channel.mention}, and category has been set to `{category.name}`."
        )

    @ticket.command(name="logs", example="#logs")
    @has_permissions(manage_channels=True)
    async def ticket_logs(self, ctx: Context, channel: TextChannel):
        """
        Set the channel in which ticket logs will be sent to.
        """

        await self.bot.db.execute(
            """
            INSERT INTO ticket.logs (guild_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                channel_id = EXCLUDED.channel_id
            """,
            ctx.guild.id,
            channel.id,
        )

        await ctx.approve(f"Ticket logs have been set to {channel.mention}!")
