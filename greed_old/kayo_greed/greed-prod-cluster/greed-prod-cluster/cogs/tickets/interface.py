import os
import asyncio
import discord
import datetime
from discord.ext import commands
import chat_exporter
import secrets
from discord import (
    PermissionOverwrite,
    Embed,
    AllowedMentions,
    Interaction,
    ButtonStyle,
    SelectOption,
    TextStyle,
    TextChannel,
)
from discord.ui import Modal, TextInput, Button, View, Select
from tools.parser import Script
from main import greed


class TicketTopic(Modal, title="Add a ticket topic"):
    name = TextInput(
        label="Topic Name",
        placeholder="Enter the ticket topic's name...",
        required=True,
        style=TextStyle.short,
    )

    description = TextInput(
        label="Topic Description",
        placeholder="Enter the description of the ticket topic...",
        required=False,
        max_length=100,
        style=TextStyle.long,
    )

    async def on_submit(self, interaction: Interaction):
        check = await interaction.client.db.fetchrow(
            "SELECT * FROM tickets.topics WHERE guild_id = $1 AND name = $2",
            interaction.guild.id,
            self.name.value,
        )

        if check:
            return await interaction.warn(
                f"A topic with the name **{self.name.value}** already exists"
            )

        await interaction.client.db.execute(
            "INSERT INTO tickets.topics VALUES ($1, $2, $3)",
            interaction.guild.id,
            self.name.value,
            self.description.value,
        )
        await interaction.approve(f"Added new ticket topic **{self.name.value}**")


class OpenTicket(Button):
    def __init__(self, bot: greed):
        super().__init__(label="Create", emoji="🎫", custom_id="ticket_open:persistent")
        self.bot = bot

    async def create_channel(
        self, interaction: Interaction, category, title=None, topic=None, embed=None
    ):
        view = TicketView(self.bot)
        view.delete_ticket()
        overwrites = category.overwrites if category else {}

        che = await interaction.client.db.fetchrow(
            "SELECT support_id FROM tickets.setup WHERE guild_id = $1",
            interaction.guild.id,
        )
        if che:
            role = interaction.guild.get_role(che[0])
            if role:
                overwrites[role] = PermissionOverwrite(
                    manage_permissions=True,
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    manage_messages=True,
                )

        overwrites[interaction.user] = PermissionOverwrite(
            read_messages=True,
            send_messages=True,
            attach_files=True,
            embed_links=True,
        )

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            topic=f"A ticket opened by {interaction.user.name} ({interaction.user.id})",
            reason=f"Ticket opened by {interaction.user.name}",
            overwrites=overwrites,
        )

        await self.bot.db.execute(
            "INSERT INTO tickets.opened VALUES ($1, $2, $3)",
            interaction.guild.id,
            channel.id,
            interaction.user.id,
        )

        if not embed:
            embed_template = (
                "{color: #181a14}"
                + "{title: "
                + (title or "Ticket opened")
                + "}"
                + "{description: Support will be with you shortly. To close the ticket please press 🗑️}"
                + "{author: {user.name} && {guild.icon}}"
                + "{content: {user.mention}}"
            )
            script = Script(
                embed_template,
                [interaction.guild, interaction.user, interaction.channel],
            )
        else:
            script = Script(
                embed, [interaction.guild, interaction.user, interaction.channel]
            )

        x = script.data
        x["view"] = view
        mes = await channel.send(**x, allowed_mentions=AllowedMentions.all())
        await mes.pin(reason="Pinned the ticket message")
        return channel

    async def callback(self, interaction: Interaction):
        check = await interaction.client.db.fetchrow(
            "SELECT * FROM tickets.setup WHERE guild_id = $1", interaction.guild.id
        )
        if not check:
            return await interaction.deny("Tickets module is disabled in this server")

        if await interaction.client.db.fetchrow(
            "SELECT * FROM tickets.opened WHERE guild_id = $1 AND user_id = $2",
            interaction.guild.id,
            interaction.user.id,
        ):
            return await interaction.warn("You **already** have an opened ticket")

        results = await interaction.client.db.fetch(
            "SELECT * FROM tickets.topics WHERE guild_id = $1", interaction.guild.id
        )
        category = interaction.guild.get_channel(check["category_id"])
        open_embed = check["open_embed"]

        if not results:
            channel = await self.create_channel(interaction, category, embed=open_embed)
            return await interaction.response.send_message(
                embed=Embed(
                    description=f"{interaction.user.mention}: Opened ticket for you in {channel.mention}"
                ),
                ephemeral=True,
            )

        options = [
            SelectOption(label=result["name"], description=result["description"])
            for result in results
        ]
        embed = Embed(description="🔍 Select a topic")
        select = Select(options=options, placeholder="Topic menu")

        async def select_callback(inter: Interaction):
            channel = await self.create_channel(
                interaction,
                category,
                title=f"Topic: {select.values[0]}",
                topic=select.values[0],
                embed=open_embed,
            )
            await inter.response.edit_message(
                view=None,
                embed=Embed(
                    description=f"{inter.user.mention}: Opened ticket for you in {channel.mention}"
                ),
            )

        select.callback = select_callback
        view = View(timeout=None)
        view.add_item(select)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await mes.pin(reason="Pinned the ticket message")
        return channel

    async def callback(self, interaction: Interaction):
        check = await interaction.client.db.fetchrow(
            "SELECT * FROM tickets.setup WHERE guild_id = $1", interaction.guild.id
        )
        if not check:
            return await interaction.deny("Tickets module is disabled in this server")

        if await interaction.client.db.fetchrow(
            "SELECT * FROM tickets.opened WHERE guild_id = $1 AND user_id = $2",
            interaction.guild.id,
            interaction.user.id,
        ):
            return await interaction.warn("You **already** have an opened ticket")

        results = await interaction.client.db.fetch(
            "SELECT * FROM tickets.topics WHERE guild_id = $1", interaction.guild.id
        )
        category = interaction.guild.get_channel(check["category_id"])
        open_embed = check["open_embed"]

        if not results:
            channel = await self.create_channel(interaction, category, embed=open_embed)
            return (
                await interaction.approve(
                    f"Opened ticket for you in {channel.mention}"
                ),
            )

        options = [
            SelectOption(label=result["name"], description=result["description"])
            for result in results
        ]
        embed = Embed(description="🔍 Select a topic")
        select = Select(options=options, placeholder="Topic menu")

        async def select_callback(inter: Interaction):
            channel = await self.create_channel(
                interaction,
                category,
                title=f"Topic: {select.values[0]}",
                topic=select.values[0],
                embed=open_embed,
            )
            await inter.response.edit_message(
                view=None,
                embed=Embed(
                    description=f"{inter.user.mention}: Opened ticket for you in {channel.mention}"
                ),
            )

        select.callback = select_callback
        view = View(timeout=None)
        view.add_item(select)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class DeleteTicket(Button):
    def __init__(self):
        super().__init__(emoji="🗑️", custom_id="ticket_close:persistent")

    async def make_transcript(self, channel: TextChannel) -> str:
        log_id = secrets.token_hex(16)
        logs_directory = "/root/logs/logs"
        file_path = f"{logs_directory}/{log_id}.html"
        os.makedirs(logs_directory, exist_ok=True)
        messages = await chat_exporter.export(channel)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(messages)
        return f"https://logs.greed.best/{log_id}"

    async def callback(self, interaction: Interaction):
        guild_id = interaction.guild.id
        user = interaction.user
        channel = interaction.channel

        support_role_record = await interaction.client.db.fetchrow(
            "SELECT support_id FROM tickets.setup WHERE guild_id = $1", guild_id
        )
        support_role = (
            interaction.guild.get_role(support_role_record[0])
            if support_role_record
            else None
        )

        if (
            support_role
            and support_role not in user.roles
            and not user.guild_permissions.manage_channels
        ):
            await interaction.warn(
                f"Only members with the {support_role.mention} role or `manage_channels` permission can close tickets",
            )
            return
        elif not support_role and not user.guild_permissions.manage_channels:
            await interaction.warn(
                "Only members with the `manage_channels` permission can close tickets",
            )
            return

        view = View(timeout=None)
        yes_button = Button(label="Yes", style=ButtonStyle.success)
        no_button = Button(label="No", style=ButtonStyle.danger)

        async def yes_callback(inter: Interaction):
            log_channel_record = await inter.client.db.fetchrow(
                "SELECT logs FROM tickets.setup WHERE guild_id = $1", inter.guild.id
            )
            log_channel = (
                inter.guild.get_channel(log_channel_record[0])
                if log_channel_record
                else None
            )

            if log_channel:
                transcript_url = await self.make_transcript(inter.channel)
                embed = Embed(
                    title=f"Logs for {inter.channel.name} `{inter.channel.id}`",
                    description=f"Closed by **{inter.user}**",
                    url=transcript_url,
                )
                await log_channel.send(embed=embed)

            await inter.response.edit_message(
                content="Deleting this channel in 5 seconds...", view=None
            )
            await asyncio.sleep(5)
            await inter.channel.delete(reason="Ticket closed")

        async def no_callback(inter: Interaction):
            await inter.response.edit_message(
                content="Ticket closure cancelled", view=None
            )

        yes_button.callback = yes_callback
        no_button.callback = no_callback
        view.add_item(yes_button)
        view.add_item(no_button)

        await interaction.response.send_message(
            "Are you sure you want to close this ticket?", view=view
        )


class TicketView(View):
    def __init__(self, bot: greed, adding: bool = False):
        super().__init__(timeout=None)
        self.bot = bot
        self.adding = adding

        if self.adding:
            self.add_open_ticket_button()
            self.add_delete_ticket_button()

    def add_open_ticket_button(self):
        if not any(isinstance(item, OpenTicket) for item in self.children):
            self.add_item(OpenTicket(self.bot))

    def add_delete_ticket_button(self):
        if not any(isinstance(item, DeleteTicket) for item in self.children):
            self.add_item(DeleteTicket())

    def create_ticket(self):
        self.add_open_ticket_button()

    def delete_ticket(self):
        self.add_delete_ticket_button()
