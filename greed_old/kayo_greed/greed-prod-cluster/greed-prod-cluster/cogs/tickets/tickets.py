import os
import asyncio
import datetime
import chat_exporter
import secrets

from discord import (
    PermissionOverwrite,
    Embed,
    Interaction,
    ButtonStyle,
    SelectOption,
    TextChannel,
    Member,
    Message,
    Role,
    CategoryChannel,
)
from discord.ui import View, Button, Select
from discord.ext.commands import (
    Cog,
    group,
    has_permissions,
    bot_has_permissions,
)
from discord.abc import GuildChannel

from main import greed
from tools.parser import Script
from tools.client import Context
from tools.conversion import get_ticket, manage_ticket, ticket_exists
from .interface import TicketView, TicketTopic


class Ticket(Cog):
    def __init__(self, bot: greed):
        self.bot = bot
        self.bot.add_view(TicketView(self.bot, adding=True))

    async def make_transcript(self, channel: TextChannel) -> str:
        log_id = secrets.token_hex(16)
        logs_directory = "/root/logs/logs"
        file_path = f"{logs_directory}/{log_id}.html"
        os.makedirs(logs_directory, exist_ok=True)
        messages = await chat_exporter.export(channel)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(messages)
        return f"https://logs.greed.best/{log_id}"

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        if isinstance(channel, TextChannel):
            await self.bot.db.execute(
                "DELETE FROM tickets.opened WHERE guild_id = $1 AND channel_id = $2",
                channel.guild.id,
                channel.id,
            )

    @group(invoke_without_command=True)
    async def ticket(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @ticket.command(
        name="add", description="ticket support / manage channels", brief="yurrion"
    )
    @get_ticket()
    @manage_ticket()
    async def ticket_add(self, ctx: Context, *, member: Member) -> Message:
        """add a person to the ticket"""
        overwrites = PermissionOverwrite(
            send_messages=True, view_channel=True, attach_files=True, embed_links=True
        )
        await ctx.channel.set_permissions(
            member, overwrite=overwrites, reason="Added to the ticket"
        )
        return await ctx.approve(f"Added {member.mention} to the ticket")

    @ticket.command(
        name="remove", description="ticket support / manage channels", brief="yurrion"
    )
    @get_ticket()
    @manage_ticket()
    async def ticket_remove(self, ctx: Context, *, member: Member) -> Message:
        """remove a member from the ticket"""
        overwrites = PermissionOverwrite(
            send_messages=False,
            view_channel=False,
            attach_files=False,
            embed_links=False,
        )
        await ctx.channel.set_permissions(
            member, overwrite=overwrites, reason="Removed from the ticket"
        )
        return await ctx.approve(f"Removed {member.mention} from the ticket")

    @ticket.command(name="close", description="ticket support / manage channels")
    @get_ticket()
    @manage_ticket()
    async def ticket_close(self, ctx: Context) -> Message:
        """closes a ticket"""
        check = await self.bot.db.fetchrow(
            "SELECT logs FROM tickets.setup WHERE guild_id = $1", ctx.guild.id
        )
        if check:
            channel = ctx.guild.get_channel(check[0])
            if channel:
                url = await self.make_transcript(ctx.channel)
                e = Embed(
                    title=f"Logs for {ctx.channel.name} `{ctx.channel.id}`",
                    description=f"Closed by **{ctx.author}**",
                    url=url,
                )
                await channel.send(embed=e)

        await ctx.send(content="Deleting this channel in 5 seconds")
        await asyncio.sleep(5)
        await ctx.channel.delete(reason="ticket closed")

    @ticket.command(name="reset", aliases=["disable"], description="manage server")
    @ticket_exists()
    @has_permissions(manage_guild=True)
    async def ticket_reset(self, ctx: Context) -> Message:
        """resets the ticket module"""
        for table in ["tickets.setup", "tickets.topics", "tickets.opened"]:
            await self.bot.db.execute(
                f"DELETE FROM {table} WHERE guild_id = $1", ctx.guild.id
            )
        await ctx.approve("Disabled the tickets module")

    @ticket.command(
        name="rename",
        description="ticket support / manage channels",
        brief="yurrions ticket",
    )
    @get_ticket()
    @manage_ticket()
    @bot_has_permissions(manage_channels=True)
    async def ticket_rename(self, ctx: Context, *, name: str) -> Message:
        """rename a ticket channel"""
        await ctx.channel.edit(
            name=name, reason=f"Ticket channel renamed by {ctx.author}"
        )
        return await ctx.approve(f"Renamed ticket channel to **{name}**")

    @ticket.command(
        name="support",
        aliases=["role"],
        description="manage server",
        brief="support role",
    )
    @ticket_exists()
    @has_permissions(manage_guild=True)
    async def ticket_support(self, ctx: Context, *, role: Role = None) -> Message:
        """add a role to manage tickets"""
        await self.bot.db.execute(
            "UPDATE tickets.setup SET support_id = $1 WHERE guild_id = $2",
            role.id if role else None,
            ctx.guild.id,
        )
        message = (
            f"Updated ticket support role to {role.mention}"
            if role
            else "Removed the ticket support role"
        )
        return await ctx.approve(message)

    @ticket.command(
        name="category", description="manage server", brief="tickets category"
    )
    @ticket_exists()
    @has_permissions(manage_guild=True)
    async def ticket_category(
        self, ctx: Context, *, category: CategoryChannel = None
    ) -> Message:
        """set the category that tickets goes in"""
        await self.bot.db.execute(
            "UPDATE tickets.setup SET category_id = $1 WHERE guild_id = $2",
            category.id if category else None,
            ctx.guild.id,
        )
        message = (
            f"Updated ticket category to {category.mention}"
            if category
            else "Removed the category channel"
        )
        return await ctx.approve(message)

    @ticket.command(name="logs", description="manage server", brief="logs channel")
    @ticket_exists()
    @has_permissions(manage_guild=True)
    async def ticket_logs(
        self, ctx: Context, *, channel: TextChannel = None
    ) -> Message:
        """set the channel for ticket logs"""
        await self.bot.db.execute(
            "UPDATE tickets.setup SET logs = $1 WHERE guild_id = $2",
            channel.id if channel else None,
            ctx.guild.id,
        )
        message = (
            f"Updated logs channel to {channel.mention}"
            if channel
            else "Removed the logs channel"
        )
        return await ctx.approve(message)

    @ticket.command(
        name="opened",
        description="manage server",
        brief="{color: #181a14}{title: Create a ticket}{description: Click on the button below this message to create a ticket}{author: {guild.name} && {guild.icon}}",
    )
    @ticket_exists()
    @has_permissions(manage_guild=True)
    async def ticket_opened(self, ctx: Context, *, code: str = None) -> Message:
        """make a new message for opening a ticket"""
        await self.bot.db.execute(
            "UPDATE tickets.setup SET open_embed = $1 WHERE guild_id = $2",
            code,
            ctx.guild.id,
        )
        message = (
            f"Updated the ticket opening message to\n```{code}```"
            if code
            else "Removed the custom ticket opening message"
        )
        return await ctx.approve(message)

    @ticket.command(description="administrator")
    @ticket_exists()
    @has_permissions(manage_guild=True)
    async def topics(self, ctx: Context) -> Message:
        """add or remove a ticket topic"""
        results = await self.bot.db.fetch(
            "SELECT * FROM tickets.topics WHERE guild_id = $1", ctx.guild.id
        )
        embed = Embed(description=f"🔍 Choose a setting")
        button1 = Button(label="add topic", style=ButtonStyle.gray)
        button2 = Button(
            label="remove topic", style=ButtonStyle.red, disabled=len(results) == 0
        )

        async def interaction_check(interaction: Interaction):
            if interaction.user != ctx.author:
                await interaction.warn("You are **not** the author of this message")
            return interaction.user == ctx.author

        async def button1_callback(interaction: Interaction):
            return await interaction.response.send_modal(TicketTopic())

        async def button2_callback(interaction: Interaction):
            e = Embed(description=f"🔍 Select a topic to delete")
            options = [
                SelectOption(label=result[1], description=result[2])
                for result in results
            ]

            select = Select(options=options, placeholder="select a topic...")

            async def select_callback(inter: Interaction):
                await self.bot.db.execute(
                    "DELETE FROM tickets.topics WHERE guild_id = $1 AND name = $2",
                    inter.guild.id,
                    select.values[0],
                )
                await inter.approve(f"Removed **{select.values[0]}** topic")

            select.callback = select_callback
            view = View()
            view.add_item(select)
            view.interaction_check = interaction_check
            return await interaction.response.edit_message(embed=e, view=view)

        button1.callback = button1_callback
        button2.callback = button2_callback
        view = View()
        view.add_item(button1)
        view.add_item(button2)
        view.interaction_check = interaction_check
        await ctx.reply(embed=embed, view=view)

    @ticket.command(name="config", description="manage guild", aliases=["settings"])
    @has_permissions(manage_guild=True)
    async def ticket_config(self, ctx: Context) -> Message:
        """view the config for tickets"""
        check = await self.bot.db.fetchrow(
            "SELECT * FROM tickets.setup WHERE guild_id = $1", ctx.guild.id
        )

        if not check:
            return await ctx.warn("Ticket module is **not** enabled in this server")

        results = await self.bot.db.fetch(
            "SELECT * FROM tickets.topics WHERE guild_id = $1", ctx.guild.id
        )

        support = f"<@&{check['support_id']}>" if check["support_id"] else "none"
        embed = Embed(
            title="Ticket Settings",
            description=f"Support role: {support}",
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.add_field(
            name="logs", value=f"<#{check['logs']}>" if check["logs"] else "none"
        )
        embed.add_field(
            name="category",
            value=f"<#{check['category_id']}>" if check["category_id"] else "none",
        )
        embed.add_field(name="topics", value=str(len(results)))
        embed.add_field(
            name="opening ticket embed", value=f"```\n{check['open_embed']}```"
        )
        await ctx.reply(embed=embed)

    @ticket.command(
        name="send",
        description="manage server",
        usage="<channel> [code]",
        brief="{color: #181a14}{title: Create a ticket}{description: Click on the button below this message to create a ticket}{author: {guild.name} && {guild.icon}}",
    )
    @ticket_exists()
    @has_permissions(manage_guild=True)
    async def ticket_send(
        self,
        ctx: Context,
        channel: TextChannel = None,
        *,
        code: str = "{color: #181a14}{title: Create a ticket}{description: Click on the button below this message to create a ticket}{author: {guild.name} && {guild.icon}}",
    ) -> Message:
        """send the ticket panel to a channel"""
        if not channel:
            check = await self.bot.db.fetchrow(
                "SELECT ticket_channel FROM tickets.setup WHERE guild_id = $1",
                ctx.guild.id,
            )
            if not check or not check["ticket_channel"]:
                return await ctx.warn("No ticket channel set and no channel provided.")
            channel = ctx.guild.get_channel(check["ticket_channel"])

        script = Script(code, [ctx.guild, ctx.author, ctx.channel])
        view = TicketView(self.bot)
        view.create_ticket()

        script_data = script.data
        script_data["view"] = view

        if (
            script_data["embed"]
            and script_data["embed"].author
            and not script_data["embed"].author.icon_url
        ):
            script_data["embed"].author.icon_url = None

        await channel.send(**script_data)
        return await ctx.approve(f"Sent ticket panel in {channel.mention}")

    @ticket.command(name="channel", description="manage guild", brief="#tickets")
    @has_permissions(manage_guild=True)
    async def ticket_channel(
        self, ctx: Context, *, channel: TextChannel = None
    ) -> Message:
        """set the ticket channel"""
        await self.bot.db.execute(
            "UPDATE tickets.setup SET ticket_channel = $1 WHERE guild_id = $2",
            channel.id if channel else None,
            ctx.guild.id,
        )
        message = (
            f"Updated ticket channel to {channel.mention}"
            if channel
            else "Removed the ticket channel"
        )
        return await ctx.approve(message)
