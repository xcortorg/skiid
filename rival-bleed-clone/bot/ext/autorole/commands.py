from discord.ext.commands import (
    Cog,
    group,
    CommandError,
    has_permissions,
    StyleConverter,
    PartialEmojiConverter,
)
from discord import (
    Client,
    Embed,
    Message,
    Role,
)
from lib.patch.context import Context
import re
import asyncio
from typing import Optional
from lib.views.roles import ButtonRoleView

EMOJI_REGEX = re.compile(
    r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
)

DEFAULT_EMOJIS = re.compile(
    r"[\U0001F300-\U0001F5FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]|[\U0001F700-\U0001F77F]|[\U0001F780-\U0001F7FF]|[\U0001F800-\U0001F8FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FA6F]|[\U0001FA70-\U0001FAFF]|[\U00002702-\U000027B0]|[\U000024C2-\U0001F251]|[\U0001F910-\U0001F9C0]|[\U0001F3A0-\U0001F3FF]"
)


class PartialEmojiConverter(PartialEmojiConverter):
    async def convert(self, ctx: Context, argument: str):
        if not DEFAULT_EMOJIS.findall(argument):
            emoji = await PartialEmojiConverter().convert(
                ctx, argument.lstrip().rstrip()
            )
        else:
            emoji = argument.replace(" ", "")
        return emoji


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot

    @group(
        name="autorole",
        description="Set up automatic role assign on member join",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def autorole(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @autorole.command(
        name="list",
        description="View a list of every auto role",
        aliases=["ls", "view", "show", "l"],
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def autorole_list(self, ctx: Context):
        if not (
            role_ids := await self.bot.db.fetch(
                """SELECT role_id FROM auto_role WHERE guild_id = $1""", ctx.guild.id
            )
        ):
            raise CommandError("there are no auto roles setup")
        roles = [
            ctx.guild.get_role(r.role_id).mention
            for r in role_ids
            if ctx.guild.get_role(r.role_id)
        ]
        rows = [f"`{i}` {r}" for i, r in enumerate(roles, start=1)]
        embed = Embed(title="Auto Roles")
        return await ctx.paginate(embed, rows)

    @autorole.command(
        name="remove",
        aliases=["delete", "del", "d", "r", "rem"],
        description="Removes a autorole and stops assigning on join",
        example=",autorole remove @member",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def autorole_remove(self, ctx: Context, *, role: Role):
        await self.bot.db.execute(
            """DELETE FROM auto_role WHERE guild_id = $1 AND role_id = $2""",
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(
            f"successfully removed the auto role of {role.mention}"
        )

    @autorole.command(
        name="reset",
        aliases=["clear", "cl"],
        description="Clears every autorole for guild",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def autorole_reset(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM auto_role WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("successfully cleared **auto roles**")

    @autorole.command(
        name="add",
        aliases=["create", "a", "c", "set"],
        description="Adds a autorole and assigns on join to member",
        example=",autorole add members",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def autorole_add(self, ctx: Context, *, role: Role):
        await self.bot.db.execute(
            """INSERT INTO auto_role (guild_id, role_id) VALUES($1, $2) ON CONFLICT(guild_id, role_id) DO NOTHING""",
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(f"successfully added {role.mention} as an auto role")

    @group(
        name="buttonrole",
        aliases=["buttonroles"],
        description="No Description Provided",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @buttonrole.command(
        name="remove",
        description="Remove a button role from a message",
        example=",buttonrole remove discord.channels/... 3",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_remove(self, ctx: Context, message: Message, index: int):
        entries = await self.bot.db.fetch(
            """SELECT index FROM button_roles WHERE message_id = $1 ORDER BY index ASC"""
        )
        if index > len(entries):
            index = len(index)
        await self.bot.db.execute(
            """DELETE FROM button_roles WHERE message_id = $1 AND index = $2""",
            message.id,
            entries[index - 1].index,
        )
        view = ButtonRoleView(self.bot, ctx.guild.id, message.id)
        await view.prepare()
        await message.edit(view=view)
        return await ctx.success(
            f"successfully removed that button from the button roles on [this message]({message.jump_url})"
        )

    @buttonrole.command(name="reset", description="Clears every button role from guild")
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_reset(self, ctx: Context):
        for row in await self.bot.db.fetch(
            """SELECT message_id, channel_id FROM button_roles WHERE guild_id = $1""",
            ctx.guild.id,
        ):
            channel = ctx.guild.get_channel(row.channel_id)
            if not channel:
                continue
            try:
                message = await channel.fetch_message(row.message_id)
            except Exception:
                continue
            await message.edit(view=None)
        await self.bot.db.execute(
            """DELETE FROM button_roles WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("successfully cleared all button roles")

    @buttonrole.command(
        name="removeall",
        description="Removes all button roles from a message",
        example=",buttonrole removeall discord.com/channels/...",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_removeall(self, ctx: Context, message: Message):
        await message.edit(view=None)
        await self.bot.db.execute(
            """DELETE FROM button_roles WHERE message_id = $1""", message.id
        )
        return await ctx.success(
            f"successfully removed all button roles from [this message]({message.jump_url})"
        )

    @buttonrole.command(name="list", description="View a list of every button role")
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_list(self, ctx: Context):
        rows = []
        embed = Embed(color=self.bot.color, title="Button roles").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        i = 0
        for row in await self.bot.db.fetch(
            """SELECT message_id, channel_id, role_id FROM button_roles WHERE guild_id = $1 ORDER BY index ASC""",
            ctx.guild.id,
        ):
            if not (channel := ctx.guild.get_channel(row.channel_id)):
                asyncio.ensure_future(
                    self.bot.db.execute(
                        """DELETE FROM button_roles WHERE channel_id = $1 AND guild_id = $2""",
                        row.channel_id,
                        ctx.guild.id,
                    )
                )
                continue
            try:
                message = await channel.fetch_message(row.message_id)
            except Exception:
                asyncio.ensure_future(
                    self.bot.db.execute(
                        """DELETE FROM button_roles WHERE message_id = $1 AND guild_id = $2""",
                        row.message_id,
                        ctx.guild.id,
                    )
                )
                continue
            if not (role := ctx.guild.get_role(row.role_id)):
                asyncio.ensure_future(
                    self.bot.db.execute(
                        """DELETE FROM button_roles WHERE role_id = $1 AND guild_id = $2""",
                        row.role_id,
                        ctx.guild.id,
                    )
                )
                continue
            i += 1
            rows.append(f"`{i}` {role.mention} - [message]({message.jump_url})")
        return await ctx.paginate(embed, rows, 10, "button role", "button roles")

    @buttonrole.command(name="add", description="", example="")
    @has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_add(
        self,
        ctx: Context,
        message: Message,
        role: Role,
        style: StyleConverter,
        emoji: Optional[PartialEmojiConverter] = None,
        label: Optional[str] = None,
    ):
        if not message.author.id == self.bot.user.id:
            raise CommandError("That is not a message that I created")
        if not emoji and not label:
            raise CommandError("either an emoji or label must be provided")
        indexes = await self.bot.db.fetch(
            """SELECT index FROM button_roles WHERE message_id = $1 ORDER BY index ASC""",
            message.id,
        )
        try:
            index = indexes[-1].index + 1
        except Exception:
            index = 1
        if len(label) > 100:
            raise CommandError("label must be 100 characters or less")
        await self.bot.db.execute(
            """INSERT INTO button_roles (guild_id, message_id, channel_id, role_id, style, emoji, label, index) VALUES($1, $2, $3, $4, $5, $6, $7, $8)""",
            ctx.guild.id,
            message.id,
            message.channel.id,
            role.id,
            style,
            emoji,
            label,
            index,
        )

    @group(
        name="reactionrole",
        aliases=["rr", "reactrole"],
        description="Set up self-assignable roles with reactions",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @reactionrole.command(
        name="removeall",
        description="Removes all reaction roles from a message",
        example=",reactionrole removeall .../channels/...",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole_removeall(self, ctx: Context, *, message: Message):
        await self.bot.db.execute(
            """DELETE FROM reaction_role WHERE guild_id = $1 AND message_id = $2""",
            ctx.guild.id,
            message.id,
        )
        return await ctx.success(
            f"successfully cleared all **reaction roles** from [this message]({message.jump_url})"
        )

    @reactionrole.command(
        name="reset", description="Clears every reaction role from guild"
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole_reset(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM reaction_role WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("successfully cleared all **reaction roles**")

    @reactionrole.command(
        name="remove",
        description="Removes a reaction role from a message",
        example=",reactionrole remove .../channels/... :wave: @members",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole_remove(
        self, ctx: Context, message: Message, *, emoji: PartialEmojiConverter
    ):
        await self.bot.db.execute(
            """DELETE FROM reaction_role WHERE guild_id = $1 AND message_id = $2 AND emoji = $3""",
            ctx.guild.id,
            message.id,
            str(emoji),
        )
        return await ctx.success("successfully removed that reaction role")

    @reactionrole.command(
        name="list",
        aliases=["ls", "view", "l", "show"],
        description="View a list of every reaction role",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole_list(self, ctx: Context):

        def get_message_link(row):
            return f"https://discord.com/channels/{row.guild_id}/{row.channel_id}/{row.message_id}"

        def get_row(row):
            if not (role := ctx.guild.get_role(row.role_id)):
                return None
            return f"{str(row.emoji)} [{row.message_id}]({get_message_link(row)}) {role.mention}"

        rows = await self.bot.db.fetch(
            """SELECT * FROM reaction_role WHERE guild_id = $1""", ctx.guild.id
        )
        if not rows:
            raise CommandError("No Reaction Roles have been setup yet")
        rows = [
            f"`{i}` {row}"
            for i, row in enumerate([get_row(r) for r in rows if get_row(r)], start=1)
        ]
        embed = Embed(title="Reaction Roles")
        return await ctx.send(embed, rows)

    @reactionrole.command(
        name="add",
        aliases=["a", "create"],
        description="Adds a reaction role to a message",
        example="",
    )
    @has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole_add(
        self,
        ctx: Context,
        message: Message,
        emoji: PartialEmojiConverter,
        *,
        role: Role,
    ):
        try:
            await message.add_reaction(emoji)
        except Exception:
            raise CommandError(f"Emoji {emoji} is not a valid emoji")
        await self.bot.db.execute(
            """INSERT INTO reaction_role (guild_id, channel_id, message_id, emoji, role_id) VALUES($1, $2, $3, $4, $5) ON CONFLICT(guild_id, channel_id, message_id, role_id) DO UPDATE SET emoji = excluded.emoji""",
            ctx.guild.id,
            message.channel.id,
            message.id,
            str(emoji),
            role.id,
        )
        return await ctx.success(
            f"successfully added that **reaction role** to [this message]({message.jump_url})"
        )
