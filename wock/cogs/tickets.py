import asyncio
import re

import discord  # type: ignore
from discord import (ButtonStyle, CategoryChannel, Embed,  # type: ignore
                     Interaction, Member, PermissionOverwrite, Role,
                     SelectOption, TextChannel)
from discord.abc import GuildChannel  # type: ignore
from discord.ext import commands  # type: ignore
from discord.ext.commands import (Cog, Context,  # type: ignore
                                  PartialEmojiConverter, bot_has_permissions,
                                  check, group, has_permissions)
from discord.ui import Button, Select, View  # type: ignore
from tools.important.subclasses.parser import EmbedConverter  # type: ignore

EMOJI_REGEX = re.compile(
    r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
)

DEFAULT_EMOJIS = re.compile(
    r"[\U0001F300-\U0001F5FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]|[\U0001F700-\U0001F77F]|[\U0001F780-\U0001F7FF]|[\U0001F800-\U0001F8FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FA6F]|[\U0001FA70-\U0001FAFF]|[\U00002702-\U000027B0]|[\U000024C2-\U0001F251]|[\U0001F910-\U0001F9C0]|[\U0001F3A0-\U0001F3FF]"
)


class Emojis(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        emojis = []
        matches = EMOJI_REGEX.finditer(argument)
        for emoji in matches:
            e = emoji.groupdict()
            emojis.append(
                await PartialEmojiConverter().convert(
                    ctx, f"<{e['animated']}:{e['name']}:{e['id']}>"
                )
            )
        defaults = DEFAULT_EMOJIS.findall(argument)
        if len(defaults) > 0:
            emojis.extend(defaults)
        return emojis


def get_ticket():
    async def predicate(ctx: Context):
        check = await ctx.bot.db.fetchrow(
            "SELECT * FROM opened_tickets WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            ctx.channel.id,
        )
        if check is None:
            await ctx.fail("This message has to be used in an opened ticket")
            return False
        return True

    return check(predicate)


def manage_ticket():
    async def predicate(ctx: Context):
        acheck = await ctx.bot.db.fetchrow(
            "SELECT support_id FROM tickets WHERE guild_id = $1", ctx.guild.id
        )
        if acheck:
            role = ctx.guild.get_role(acheck[0])
            if role:
                if (
                    role not in ctx.author.roles
                    and not ctx.author.guild_permissions.manage_channels
                ):
                    await ctx.fail(
                        f"Only members with {role.mention} role and members with the **Manage Channels** permission can **add** or **remove** new members from the ticket",
                    )
                    return False
            else:
                if not ctx.author.guild_permissions.manage_channels:
                    await ctx.fail(
                        "Only members with the **Manage Channels** permission can **add** or **remove** new members from the ticket"
                    )
                    return False
        else:
            if not ctx.author.guild_permissions.manage_channels:
                await ctx.fail(
                    "Only members with the **Manage Channels** permission can **add** or **remove** new members from the ticket",
                )
                return False
        return True

    return check(predicate)


def ticket_exists():
    async def predicate(ctx: Context):
        check = await ctx.bot.db.fetchrow(
            "SELECT * FROM tickets WHERE guild_id = $1", ctx.guild.id
        )
        if not check:
            await ctx.bot.db.execute(
                "INSERT INTO tickets (guild_id) VALUES ($1)", ctx.guild.id
            )
        return True

    return check(predicate)


class TicketCategory(discord.ui.Modal, title="Add a ticket category"):
    name = discord.ui.TextInput(
        label="category name",
        placeholder="the ticket category's name..",
        required=True,
        style=discord.TextStyle.short,
    )

    description = discord.ui.TextInput(
        label="category description",
        placeholder="the description of the ticket category...",
        required=False,
        max_length=100,
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction):
        check = await interaction.client.db.fetchrow(
            "SELECT * FROM ticket_topics WHERE guild_id = $1 AND name = $2",
            interaction.guild.id,
            self.name.value,
        )

        if check:
            return await interaction.response.send_message(
                f"A topic with the name **{self.name.value}** already exists",
                ephemeral=True,
            )

        await interaction.client.db.execute(
            "INSERT INTO ticket_topics VALUES ($1,$2,$3)",
            interaction.guild.id,
            self.name.value,
            self.description.value,
        )
        return await interaction.response.send_message(
            f"Added new ticket topic **{self.name.value}**", ephemeral=True
        )


class OpenTicket(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"button:open:(?P<guild_id>[0-9]+)",
):
    def __init__(self, guild_id: int, emoji: str = "🎫"):
        super().__init__(
            discord.ui.Button(
                label="Create",
                emoji=emoji,
                custom_id=f"button:open:{guild_id}",
                style=discord.ButtonStyle.primary,
            )
        )
        self.guild_id = guild_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):  # type: ignore # type: ignore
        guild_id = int(match["guild_id"])
        return cls(guild_id)

    async def create_channel(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        title: str = None,
        topic: str = None,
        embed: str = None,
    ):
        view = TicketView(interaction.client, guild_id=self.guild_id)
        await view.setup()
        view.delete_ticket()
        overwrites = category.overwrites if category else {}

        che = await interaction.client.db.fetchrow(
            "SELECT support_id FROM tickets WHERE guild_id = $1", interaction.guild.id
        )
        if che:
            role = interaction.guild.get_role(che[0])
            if role:
                overwrites.update(
                    {
                        role: discord.PermissionOverwrite(
                            manage_permissions=True,
                            read_messages=True,
                            send_messages=True,
                            attach_files=True,
                            embed_links=True,
                            manage_messages=True,
                        )
                    }
                )

        overwrites.update(
            {
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                )
            }
        )
        overwrites.update(
            {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    read_messages=False, view_channel=False
                )
            }
        )

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            topic=f"A ticket opened by {interaction.user.name} ({interaction.user.id})",
            reason=f"Ticket opened by {interaction.user.name}",
            overwrites=overwrites,
        )

        await interaction.client.db.execute(
            "INSERT INTO opened_tickets VALUES ($1,$2,$3)",
            interaction.guild.id,
            channel.id,
            interaction.user.id,
        )

        if not embed:
            embed = "{embed}{author: {user.name} && https://wock.bot/ && {user.avatar}}$v{title: {title}}$v{content: {user.mention}}$v{description: To close the ticket please press :wastebasket:¸}$v{color: #d6bcd0}".replace(
                "{title}", title or "Ticket Opened"
            )

        mes = await interaction.client.send_embed(
            channel,
            embed.replace("{topic}", topic or "none"),
            user=interaction.user,
            view=view,
        )
        await mes.pin(reason="pinned the ticket message")
        return channel

    async def callback(self, interaction: discord.Interaction) -> None:
        check = await interaction.client.db.fetchrow(
            "SELECT * FROM tickets WHERE guild_id = $1", interaction.guild.id
        )
        if not check:
            return await interaction.fail("Tickets module is disabled in this server")
        if await interaction.client.db.fetchrow(
            "SELECT * FROM opened_tickets WHERE guild_id = $1 AND guild_id = $2",
            interaction.guild.id,
            interaction.user.id,
        ):
            return await interaction.fail("You **already** have an opened ticket")

        results = await interaction.client.db.fetch(
            "SELECT * FROM ticket_topics WHERE guild_id = $1", interaction.guild.id
        )
        category = interaction.guild.get_channel(check["category_id"])
        open_embed = check["open_embed"]
        if len(results) == 0:
            channel = await self.create_channel(
                interaction, category, title=None, topic=None, embed=open_embed
            )
            return await interaction.success(
                f"Opened ticket for you in {channel.mention}"
            )
        else:
            options = [
                discord.SelectOption(
                    label=result["name"], description=result["description"]
                )
                for result in results
            ]
            select = discord.ui.Select(options=options, placeholder="Topic menu")
            view = discord.ui.View(timeout=None)

            async def select_callback(inter: discord.Interaction) -> None:
                channel = await self.create_channel(
                    interaction,
                    category,
                    title=f"Category: {select.values[0]}",
                    topic=select.values[0],
                    embed=open_embed,
                )
                return await inter.success(
                    f"Opened ticket for you in {channel.mention}"
                )

            select.callback = select_callback
            view.add_item(select)
            embed = discord.Embed(
                color=interaction.client.color, description="🔍 Select a topic"
            )
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )


class DeleteTicket(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"button:close:(?P<guild_id>[0-9]+)",
):
    def __init__(self, guild_id: int, emoji: str = "🗑️"):
        super().__init__(
            discord.ui.Button(
                emoji=emoji,
                custom_id=f"button:close:{guild_id}",
                style=discord.ButtonStyle.danger,
            )
        )
        self.guild_id = guild_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str], /):  # type: ignore # type: ignore
        guild_id = int(match["guild_id"])
        return cls(guild_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        che = await interaction.client.db.fetchrow(
            "SELECT support_id FROM tickets WHERE guild_id = $1", interaction.guild.id
        )
        if che:
            role = interaction.guild.get_role(che[0])
            if (
                role
                and role not in interaction.user.roles
                and not interaction.user.guild_permissions.manage_channels
            ):
                return await interaction.fail(
                    "You are missing permissions **Manage Channels**"
                )
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.fail(
                "You are missing permissions **Manage Channels**"
            )

        view = discord.ui.View(timeout=None)
        yes = discord.ui.Button(label="Yes", style=discord.ButtonStyle.success)
        no = discord.ui.Button(label="No", style=discord.ButtonStyle.danger)

        async def yes_callback(inter: discord.Interaction) -> None:
            await inter.response.edit_message(
                content="Deleting this channel in 5 seconds", view=None
            )
            await asyncio.sleep(5)
            await inter.channel.delete(reason="Ticket closed")

        async def no_callback(inter: discord.Interaction) -> None:
            await inter.response.edit_message(
                content="You changed your mind", view=None
            )

        yes.callback = yes_callback
        no.callback = no_callback
        view.add_item(yes)
        view.add_item(no)
        return await interaction.response.send_message(
            "Are you sure you want to close this ticket?", view=view, ephemeral=True
        )


class TicketView(discord.ui.View):
    def __init__(
        self,
        bot: commands.AutoShardedBot,
        guild_id: int,
        open_ticket_emoji: str = None,
        delete_ticket_emoji: str = None,
    ):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
        self.open_ticket_emoji = open_ticket_emoji
        self.delete_ticket_emoji = delete_ticket_emoji

    async def setup(self, refresh: bool = False):
        emojis = await self.bot.db.fetchrow(
            "SELECT open_emoji, delete_emoji, message_id FROM tickets WHERE guild_id = $1",
            self.guild_id,
        )
        try:
            self.open_ticket_emoji = emojis["open_emoji"] or "🎫"
            self.delete_ticket_emoji = emojis["delete_emoji"] or "🗑️"
            if refresh:
                return emojis["message_id"]
        except Exception:
            pass
        return

    def create_ticket(self):
        self.add_item(OpenTicket(guild_id=self.guild_id, emoji=self.open_ticket_emoji))

    def delete_ticket(self):
        self.add_item(
            DeleteTicket(guild_id=self.guild_id, emoji=self.delete_ticket_emoji)
        )


class WockDonation(discord.ui.View):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.button(
        label="",
        emoji="<a:Sanrio_hellokittylove:1255713730281607240>",
        custom_id="wock:purchase",
    )
    async def purchase(self, interaction: discord.Interaction, button: discord.ui.Button):  # type: ignore
        embed = discord.Embed(title="Payment Methods")
        embed.description = """
        > **Wock Pass Premium** requires a monthly payment of **$3.99 a month or 2 server boosts**. No additional fees and includes access to commands such as avatar history, google searching, among other commands. Once purchased, Dm a staff member with proof of payment to get the donator role. Users who owns a server with more than 500 users that has wock in it, provided with proof, qualify for wock premium free!
        """
        embed.color = self.bot.color
        embed.add_field(
            name="Cashapp Payment Only",
            value="> <:CashApp:1252763419560640645> - $ocx01",
        )
        embed.set_footer(text="For questions, contact a staff member.")
        return await interaction.response.send_message(embed=embed, ephemeral=True)


class Tickets(Cog):
    def __init__(self, bot):
        self.bot = bot

    async def register_persistent_views(self):
        # Fetching guild-specific settings for emojis
        for guild in self.bot.guilds:

            # Create and register the persistent view for each guild
            view = TicketView(self.bot, guild.id)
            view2 = TicketView(self.bot, guild.id)
            await view2.setup()
            await view.setup(refresh=True)
            view.create_ticket()
            view2.delete_ticket()
            self.bot.add_view(view2, message_id=None)
            self.bot.add_view(
                view, message_id=None
            )  # Register the view without associating it with a specific message

    async def cog_load(self):
        await self.register_persistent_views()
        self.bot.add_view(WockDonation(self.bot))

    @commands.command(name="sendmessage", hidden=True)
    @commands.is_owner()
    async def sendmessage(self, ctx: Context, *, code: EmbedConverter):
        view = WockDonation(self.bot)
        code.pop("view", None)
        code["view"] = view
        return await ctx.send(**code)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        if str(channel.type) == "text":
            await self.bot.db.execute(
                "DELETE FROM opened_tickets WHERE guild_id = $1 AND channel_id = $2",
                channel.guild.id,
                channel.id,
            )

    @group(
        name="ticket",
        brief="Configure the tickets setup for your server",
        example=",ticket",
    )
    @manage_ticket()
    @commands.bot_has_permissions(manage_channels=True)
    async def ticket(self, ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help()

    @ticket.command(
        name="add", brief="Add a user to the ticket", example=",ticket add @o_5v"
    )
    @commands.bot_has_permissions(manage_channels=True)
    @manage_ticket()
    @get_ticket()
    async def ticket_add(self, ctx: Context, *, member: Member):
        """add a person to the ticket"""
        overwrites = PermissionOverwrite()
        overwrites.send_messages = True
        overwrites.view_channel = True
        overwrites.attach_files = True
        overwrites.embed_links = True
        await ctx.channel.set_permissions(
            member, overwrite=overwrites, reason="Added to the ticket"
        )
        return await ctx.success(f"Added {member.mention} to the ticket")

    @ticket.command(
        name="remove",
        brief="Remove a ticket that a user has created",
        example=",ticket remove @o_5v",
    )
    @commands.bot_has_permissions(manage_channels=True)
    @manage_ticket()
    @get_ticket()
    async def ticket_remove(self, ctx: Context, *, member: Member):
        """remove a member from the ticket"""
        overwrites = PermissionOverwrite()
        overwrites.send_messages = False
        overwrites.view_channel = False
        overwrites.attach_files = False
        overwrites.embed_links = False
        await ctx.channel.set_permissions(
            member, overwrite=overwrites, reason="Removed from the ticket"
        )
        return await ctx.success(f"Removed {member.mention} from the ticket")

    @ticket.command(name="close", extras={"perms": "ticket support / manage channels"})
    @manage_ticket()
    @get_ticket()
    @commands.bot_has_permissions(manage_channels=True)
    async def ticket_close(self, ctx: Context):
        """close the ticket"""
        await ctx.send(content="Deleting this channel in 5 seconds")
        await asyncio.sleep(5)
        await ctx.channel.delete(reason="ticket closed")

    @ticket.command(
        name="reset", aliases=["disable"], extras={"perms": "manage server"}
    )
    @has_permissions(manage_guild=True)
    @ticket_exists()
    @commands.bot_has_permissions(manage_channels=True)
    async def ticket_reset(self, ctx: Context):
        """disable the ticket module in the server"""
        for i in ["tickets", "ticket_topics", "opened_tickets"]:
            await self.bot.db.execute(
                f"DELETE FROM {i} WHERE guild_id = $1", ctx.guild.id
            )

        await ctx.success("Disabled the tickets module")

    @ticket.command(
        name="rename",
        brief="Rename a ticket",
        example=",ticket rename name, new-name",
    )
    @manage_ticket()
    @get_ticket()
    @commands.bot_has_permissions(manage_channels=True)
    @bot_has_permissions(manage_channels=True)
    async def ticket_rename(self, ctx: Context, *, name: str):
        """rename a ticket channel"""
        await ctx.channel.edit(
            name=name, reason=f"Ticket channel renamed by {ctx.author}"
        )
        await ctx.success(f"Renamed ticket channel to **{name}**")

    @ticket.command(
        name="support",
        extras={"perms": "manage server"},
        brief="Set a role for users that has that role to answer tickets",
        example=",ticket support @mod",
    )
    @commands.bot_has_permissions(manage_channels=True)
    @has_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_support(self, ctx: Context, *, role: Role = None):
        """configure the ticket support role"""
        if role:
            await self.bot.db.execute(
                "UPDATE tickets SET support_id = $1 WHERE guild_id = $2",
                role.id,
                ctx.guild.id,
            )
            return await ctx.success(f"Updated ticket support role to {role.mention}")
        else:
            await self.bot.db.execute(
                "UPDATE tickets SET support_id = $1 WHERE guild_id = $2",
                None,
                ctx.guild.id,
            )
            return await ctx.success("Removed the ticket support role")

    @ticket.command(
        name="category",
        extras={"perms": "manage server"},
        brief="Set a category where created tickets will be sent to",
        example=",ticket category create-a-ticket",
    )
    @commands.bot_has_permissions(manage_channels=True)
    @has_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_category(self, ctx: Context, *, category: CategoryChannel = None):
        """configure the category where the tickets should open"""
        if category:
            await self.bot.db.execute(
                "UPDATE tickets SET category_id = $1 WHERE guild_id = $2",
                category.id,
                ctx.guild.id,
            )
            return await ctx.success(f"Updated ticket category to {category.mention}")
        else:
            await self.bot.db.execute(
                "UPDATE tickets SET category_id = $1 WHERE guild_id = $2",
                None,
                ctx.guild.id,
            )
            return await ctx.success("Removed the category channel")

    @ticket.command(
        name="message",
        extras={"perms": "manage server"},
        brief="Set a message to be sent when a ticket is opened",
        example=",ticket opened {embed_code}",
    )
    @commands.bot_has_permissions(manage_channels=True)
    @has_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_opened(self, ctx: Context, *, code: str = None):
        """set a message to be sent when a member opens a ticket"""
        await self.bot.db.execute(
            "UPDATE tickets SET open_embed = $1 WHERE guild_id = $2", code, ctx.guild.id
        )
        if code:
            return await ctx.success(
                f"Updated the ticket opening message to\n```{code}```"
            )
        else:
            return await ctx.success("Removed the custom ticket opening message")

    @ticket.command(
        name="topics",
        brief="Assign topics to be chosen from before a user creates a ticket",
        example=",ticket topics",
    )
    @has_permissions(manage_guild=True)
    @ticket_exists()
    @commands.bot_has_permissions(manage_channels=True)
    async def ticket_topics(self, ctx: Context):
        """manage the ticket topics"""
        results = await self.bot.db.fetch(
            "SELECT * FROM ticket_topics WHERE guild_id = $1", ctx.guild.id
        )
        embed = Embed(color=self.bot.color, description="🔍 Choose a setting")
        button1 = Button(label="add topic", style=ButtonStyle.gray)
        button2 = Button(
            label="remove topic", style=ButtonStyle.red, disabled=len(results) == 0
        )

        async def interaction_check(interaction: Interaction):
            if interaction.user != ctx.author:
                await interaction.warn(
                    "You are **not** the author of this message", ephemeral=True
                )
            return interaction.user == ctx.author

        async def button1_callback(interaction: Interaction):
            return await interaction.response.send_modal(TicketCategory())

        async def button2_callback(interaction: Interaction):
            e = Embed(color=self.bot.color, description="🔍 Sleect a topic to delete")
            options = [
                SelectOption(label=result[1], description=result[2])
                for result in results
            ]

            select = Select(options=options, placeholder="select a topic...")

            async def select_callback(inter: Interaction):
                await self.bot.db.execute(
                    "DELETE FROM ticket_topics WHERE guild_id = $1 AND name = $2",
                    inter.guild.id,
                    select.values[0],
                )
                await inter.response.send_message(
                    f"Removed **{select.values[0]}** topic", ephemeral=True
                )

            select.callback = select_callback
            v = View()
            v.add_item(select)
            v.interaction_check = interaction_check
            return await interaction.response.edit_message(embed=e, view=v)

        button1.callback = button1_callback
        button2.callback = button2_callback
        view = View()
        view.add_item(button1)
        view.add_item(button2)
        view.interaction_check = interaction_check
        await ctx.reply(embed=embed, view=view)

    @ticket.command(name="config", aliases=["settings"])
    @commands.bot_has_permissions(manage_channels=True)
    async def ticket_config(self, ctx: Context):
        """check the server's ticket settings"""
        check = await self.bot.db.fetchrow(
            "SELECT * FROM tickets WHERE guild_id = $1", ctx.guild.id
        )

        if not check:
            return await ctx.fail("Ticket module is **not** enabled in this server")

        results = await self.bot.db.fetch(
            "SELECT * FROM ticket_topics WHERE guild_id = $1", ctx.guild.id
        )

        support = f"<@&{check['support_id']}>" if check["support_id"] else "none"
        embed = Embed(
            color=self.bot.color,
            title="Ticket Settings",
            description=f"Support role: {support}",
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.add_field(
            name="Channel Category",
            value=f"<#{check['category_id']}>" if check["category_id"] else "none",
            inline=False,
        )
        embed.add_field(name="Categories", value=str(len(results)), inline=False)
        embed.add_field(
            name="opening ticket embed",
            value=f"```\n{check['open_embed']}```",
            inline=False,
        )
        await ctx.reply(embed=embed)

    @ticket.command(
        name="setup",
        brief="Setup the ticket panel to send to a channel",
        example=",ticket setup #tickets",
        parameters={
            "delete": {
                "converter": Emojis,
                "description": "the delete ticket emoji",
                "default": None,
            },
            "open": {
                "converter": Emojis,
                "description": "the open ticket emoji",
                "default": None,
            },
            "code": {
                "converter": str,
                "description": "the embed code",
                "aliases": ("embed",),
                "default": "{embed}{color: #181a14}$v{title: Create a ticket}$v{description: Click on the button below this message to create a ticket}",
            },
            # "embed": {
            #     "converter": str,
            #     "description": "the embed code",
            #     "default": "{embed}{color: #181a14}$v{title: Create a ticket}$v{description: Click on the button below this message to create a ticket}"
            # }
        },
    )
    @commands.bot_has_permissions(manage_channels=True)
    @has_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_send(
        self,
        ctx: Context,
        channel: TextChannel,
    ):
        """send the ticket panel to a channel"""
        self.bot.cw = ctx
        code: str = ctx.parameters.get("code") or ctx.parameters.get("embed")
        delete_emoji = ctx.parameters.get("delete")
        if delete_emoji:
            delete_emoji = await delete_emoji
        open_emoji = ctx.parameters.get("open")
        if open_emoji:
            open_emoji = await open_emoji
        if delete_emoji and open_emoji:
            await self.bot.db.execute(
                """UPDATE tickets SET delete_emoji = $1, open_emoji = $2 WHERE guild_id = $3""",
                delete_emoji[0],
                open_emoji[0],
                ctx.guild.id,
            )
        elif delete_emoji:
            await self.bot.db.execute(
                """UPDATE tickets SET delete_emoji = $1 WHERE guild_id = $2""",
                delete_emoji[0],
                ctx.guild.id,
            )
        elif open_emoji:
            await self.bot.db.execute(
                """UPDATE tickets SET open_emoji = $1 WHERE guild_id = $2""",
                open_emoji[0],
                ctx.guild.id,
            )
        else:
            pass
        view = TicketView(self.bot, ctx.guild.id)
        await view.setup()
        view.create_ticket()
        self.bot.view_ = view
        message = await self.bot.send_embed(channel, code, user=ctx.author, view=view)
        await self.bot.db.execute(
            """UPDATE tickets SET message_id = $1 WHERE guild_id = $2""",
            message.id,
            ctx.guild.id,
        )
        return await ctx.success(f"Sent ticket panel in {channel.mention}")


async def setup(bot) -> None:
    return await bot.add_cog(Tickets(bot))
