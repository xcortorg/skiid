import os
import time
import json
import asyncio
import discord
import secrets
import datetime
import chat_exporter

from chat_exporter import AttachmentToLocalFileHostHandler

from discord import Embed, ButtonStyle, PartialEmoji
from discord.ui import View, Button
from discord.ext import commands
from discord.utils import get

from modules.styles import emojis, colors

async def check_emoji(emoji: str, interaction: discord.Interaction):
    if isinstance(emoji, str):
        emoji = emoji.strip(":")
        custom_emoji = None
        if emoji.startswith('<:') and emoji.endswith('>'):
            custom_emoji = get(interaction.guild.emojis, name=emoji.split(':')[1])
        else:
            custom_emoji = get(interaction.guild.emojis, name=emoji.strip(':'))
        if custom_emoji:
            return custom_emoji
        else:
            try:
                unicode_emoji = PartialEmoji.from_str(emoji)
                if unicode_emoji.is_unicode_emoji():
                    return unicode_emoji
                else:
                    return None
            except Exception:
                return None
    return None

class TicketTopic(discord.ui.Modal, title="Add a ticket topic"):
    name = discord.ui.TextInput(
        label="topic name",
        placeholder="the ticket topic's name..",
        required=True,
        style=discord.TextStyle.short,
    )
    description = discord.ui.TextInput(
        label="topic description",
        placeholder="the description of the ticket topic...",
        required=False,
        max_length=100,
        style=discord.TextStyle.long,
    )
    emoji = discord.ui.TextInput(
        label="topic emoji",
        placeholder="the emoji of the ticket topic...",
        required=False,
        max_length=100,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction):
        check = await interaction.client.db.fetchrow("SELECT * FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, self.name.value)
        if check:
            return await interaction.response.send_message(
                embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: A topic with the name **{self.name.value}** already exists"), ephemeral=True)
        emoji_value = self.emoji.value if self.emoji.value else None
        await interaction.client.db.execute("INSERT INTO ticket_topics VALUES ($1,$2,$3,$4)", interaction.guild.id, self.name.value, self.description.value, emoji_value)
        return await interaction.response.send_message(
            embed=discord.Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Added new ticket topic **{self.name.value}**"), ephemeral=True)
    
class TicketModal(discord.ui.Modal, title="Ticket Module"):
    def __init__(self, bot, selected_topic, module_data_list):
        super().__init__(timeout=None)
        self.bot = bot
        self.selected_topic = selected_topic
        self.module_data_list = module_data_list

        for module_data in module_data_list:
            field_name = module_data['name']
            placeholder = module_data['description']
            required = module_data['required']
            style = discord.TextStyle.long if module_data['style'] else discord.TextStyle.short
            self.add_item(discord.ui.TextInput(label=field_name, placeholder=placeholder, required=required, style=style))

    async def on_submit(self, interaction: discord.Interaction):
        user_inputs = {text_input.label: text_input.value for text_input in self.children}
        selected_topic = self.selected_topic
        module_data = await self.check_module(interaction, selected_topic)
        if not module_data:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: No module data found for the selected topic.")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        module_codes = {module['name']: module['code'] for module in module_data}
        formatted_codes = {}
        for label, value in user_inputs.items():
            code = module_codes.get(label)
            if code:
                formatted_codes[code] = value
        formatted_data = {'formatted_code': formatted_codes, 'user_inputs': user_inputs}
        check = await interaction.client.db.fetchrow("SELECT * FROM ticket WHERE guild_id = $1", interaction.guild.id)
        if not check:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Tickets module is disabled in this server.")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        category_id = await interaction.client.db.fetchval("SELECT category_id FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, selected_topic)
        category = interaction.guild.get_channel(category_id)
        if not category:
            category_id = await interaction.client.db.fetchval("SELECT category_id FROM ticket WHERE guild_id = $1", interaction.guild.id)
            if category_id:
                category = interaction.guild.get_channel(category_id)
            if not category:
                category = None
        if not selected_topic == "default":
            embed = Embed(color=colors.NEUTRAL, description=f"{emojis.LOADING} {interaction.user.mention}: Creating a ticket for you...")
            await interaction.response.edit_message(embed=embed, view=None)
        channel = await self.create_channel(interaction, category, title=selected_topic, topic=selected_topic, embed_template=None, user_inputs=formatted_data)
        if check['owner_role']:
            try:
                owner_role = interaction.guild.get_role(check['owner_role'])
                if owner_role:
                    await interaction.user.add_roles(owner_role, reason="ticket opened")
            except Exception:
                pass
        if selected_topic == "default":
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Opened ticket for you in {channel.mention}")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Opened ticket for you in {channel.mention}")
            return await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=None)

    async def check_module(self, interaction: discord.Interaction, selected_topic):
        module_data_list = await self.bot.db.fetch("SELECT name, description, code, required, style FROM ticket_modals WHERE guild_id = $1 AND topic = $2", interaction.guild.id, selected_topic)
        if module_data_list:
            return [dict(record) for record in module_data_list]
        return None

    async def create_channel(self, interaction: discord.Interaction, category: discord.CategoryChannel, title: str = None, topic: str = None, embed_template: str = None, user_inputs: dict = None):
        view = TicketButtonView(self.bot)
        view.close_ticket()
        view.transcript_ticket()
        view.delete_ticket()
        overwrites = {
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }
        if not isinstance(category, discord.CategoryChannel) or len(category.channels) >= 50:
            category = None
        check_topic_support = await interaction.client.db.fetchval("SELECT support_roles FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, topic)
        if check_topic_support and check_topic_support != "[]":
            try:
                topic_support_roles = json.loads(check_topic_support)
                if not isinstance(topic_support_roles, list):
                    embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An unexpected data format for topic support roles.")
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
                for role_id in topic_support_roles:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(
                            manage_permissions=True,
                            read_messages=True,
                            send_messages=True,
                            attach_files=True,
                            embed_links=True,
                            manage_messages=True
                        )
                support_role_mentions = ' '.join([f"<@&{role_id}>" for role_id in topic_support_roles])
            except json.JSONDecodeError:
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Invalid JSON format for topic support roles.")
                return await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            check_ticket_support = await interaction.client.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", interaction.guild.id)
            if check_ticket_support:
                try:
                    ticket_support_roles = json.loads(check_ticket_support)
                    if not isinstance(ticket_support_roles, list):
                        embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An unexpected data format for default support roles.")
                        return await interaction.response.send_message(embed=embed, ephemeral=True)
                    for role_id in ticket_support_roles:
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            overwrites[role] = discord.PermissionOverwrite(
                                manage_permissions=True,
                                read_messages=True,
                                send_messages=True,
                                attach_files=True,
                                embed_links=True,
                                manage_messages=True
                            )
                    support_role_mentions = ' '.join([f"<@&{role_id}>" for role_id in ticket_support_roles])
                except json.JSONDecodeError:
                    embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Invalid JSON format for default support roles.")
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                support_role_mentions = ""
        channel_name = await interaction.client.db.fetchval("SELECT channel_name FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, topic)
        if channel_name:
            channel_name = channel_name.replace("{user.id}", str(interaction.user.id))
            channel_name = channel_name.replace("{user.name}", str(interaction.user.name))
            channel_name = channel_name.replace("{topic}", str(topic))
        else:
            channel_name = f"{topic}-{interaction.user.name}".replace("default", "ticket")
        counter_data = await interaction.client.db.fetchrow("SELECT * FROM ticket WHERE guild_id = $1", interaction.guild.id)
        if counter_data['counter_status']:
            channel_name = f"ticket-{counter_data['counter']:04d}"
            await interaction.client.db.execute("UPDATE ticket SET counter = counter + 1 WHERE guild_id = $1", interaction.guild.id)
        channel_topic = await interaction.client.db.fetchval("SELECT channel_topic FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, topic)
        if channel_topic:
            if user_inputs and 'formatted_code' in user_inputs:
                formatted_code_dict = user_inputs['formatted_code']
                for code, user_input in formatted_code_dict.items():
                    placeholder = f"{{{code}}}"
                    if placeholder in channel_topic:
                        pass
                    channel_topic = channel_topic.replace(placeholder, user_input)
            for code, user_input in user_inputs.get('user_inputs', {}).items():
                if isinstance(user_input, str):
                    placeholder = f"{{{code}}}"
                    if placeholder in channel_topic:
                        pass
                    channel_topic = channel_topic.replace(placeholder, user_input)
                else:
                    pass
            channel_topic = channel_topic.replace("{user.id}", str(interaction.user.id))
            channel_topic = channel_topic.replace("{user.name}", str(interaction.user.name))
            channel_topic = channel_topic.replace("{topic}", str(topic))
        else:
            channel_topic = f"A ticket opened by {interaction.user.name} ({interaction.user.id})"
        channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            topic=channel_topic,
            reason=f"Ticket opened by {interaction.user.name}"
        )
        await channel.edit(sync_permissions=True)
        for target, overwrite in overwrites.items():
            await channel.set_permissions(target, overwrite=overwrite)
        await self.bot.db.execute("INSERT INTO ticket_opened (guild_id, channel_id, user_id, topic) VALUES ($1, $2, $3, $4)", interaction.guild.id, channel.id, interaction.user.id, topic)
        embed_template = await interaction.client.db.fetchval("SELECT embed FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, topic)
        if not embed_template:
            embed_template = await interaction.client.db.fetchval("SELECT open_embed FROM ticket WHERE guild_id = $1", interaction.guild.id)
            if not embed_template:
                embed_template = ("{embed}{color: #729bb0}$v{title: {title}}$v{description: Support will be with you shortly To close the ticket please press 🗑️}$v{author: name: {user.name} ({user.id}) && icon: {user.avatar}}$v{content: {user.mention} | {support.role}}")
        embed_filled = embed_template.replace("{title}", title or "Ticket opened")
        embed_filled = embed_filled.replace("{topic}", topic or "none")
        embed_filled = embed_filled.replace("{support.role}", support_role_mentions)
        if user_inputs and 'formatted_code' in user_inputs:
            formatted_code_dict = user_inputs['formatted_code']
            for code, user_input in formatted_code_dict.items():
                placeholder = f"{{{code}}}"
                if placeholder in embed_filled:
                    pass
                embed_filled = embed_filled.replace(placeholder, user_input)
        for code, user_input in user_inputs.get('user_inputs', {}).items():
            if isinstance(user_input, str):
                placeholder = f"{{{code}}}"
                if placeholder in embed_filled:
                    pass
                embed_filled = embed_filled.replace(placeholder, user_input)
            else:
                pass
        x = await self.bot.embed_build.alt_convert(interaction.user, embed_filled)
        x["view"] = view
        try:
            mes = await channel.send(**x, allowed_mentions=discord.AllowedMentions.all())
        except Exception as e:
            try:
                return await interaction.response.send_message(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while sending the message\n```{e}```"), ephemeral=True)
            except Exception:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while sending the message\n```{e}```"), ephemeral=True)
        await mes.pin(reason="pinned the ticket message")
        claiming = await interaction.client.db.fetchval("SELECT claiming FROM ticket WHERE guild_id = $1", interaction.guild.id)
        if claiming == True:
            embed = Embed(color=colors.NEUTRAL, description=f"{emojis.QUESTION} Do you want to claim this ticket from {interaction.user.mention}?")
            view = TicketButtonView(interaction.client)
            view.claim_ticket()
            await channel.send(embed=embed, view=view)
        return channel

class ButtonTicket(discord.ui.Button):
    def __init__(self, bot: commands.AutoShardedBot):
        super().__init__(label="Create Ticket", emoji=emojis.CREATE, custom_id="ticket_open:persistent")
        self.bot = bot

    async def check_module(self, interaction: discord.Interaction, selected_topic):
        module_data_list = await self.bot.db.fetch("SELECT name, description, code, required, style FROM ticket_modals WHERE guild_id = $1 AND topic = $2", interaction.guild.id, selected_topic)
        if module_data_list:
            return [dict(record) for record in module_data_list]
        return None

    async def create_channel(self, interaction: discord.Interaction, category: discord.CategoryChannel, title: str = None, topic: str = None, user_inputs: dict = None):
        view = TicketButtonView(self.bot)
        view.close_ticket()
        view.transcript_ticket()
        view.delete_ticket()
        overwrites = {
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }
        if not isinstance(category, discord.CategoryChannel) or len(category.channels) >= 50:
            category = None
        if not topic:
            topic = "default"
        check_topic_support = await interaction.client.db.fetchval("SELECT support_roles FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, topic)
        if check_topic_support and check_topic_support != "[]":
            try:
                topic_support_roles = json.loads(check_topic_support)
                if not isinstance(topic_support_roles, list):
                    embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An unexpected data format for topic support roles.")
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
                for role_id in topic_support_roles:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(
                            manage_permissions=True,
                            read_messages=True,
                            send_messages=True,
                            attach_files=True,
                            embed_links=True,
                            manage_messages=True
                        )
                support_role_mentions = ' '.join([f"<@&{role_id}>" for role_id in topic_support_roles])
            except json.JSONDecodeError:
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Invalid JSON format for topic support roles.")
                return await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            check_ticket_support = await interaction.client.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", interaction.guild.id)
            if check_ticket_support:
                try:
                    ticket_support_roles = json.loads(check_ticket_support)
                    if not isinstance(ticket_support_roles, list):
                        embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An unexpected data format for default support roles.")
                        return await interaction.response.send_message(embed=embed, ephemeral=True)
                    for role_id in ticket_support_roles:
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            overwrites[role] = discord.PermissionOverwrite(
                                manage_permissions=True,
                                read_messages=True,
                                send_messages=True,
                                attach_files=True,
                                embed_links=True,
                                manage_messages=True
                            )
                    support_role_mentions = ' '.join([f"<@&{role_id}>" for role_id in ticket_support_roles])
                except json.JSONDecodeError:
                    embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Invalid JSON format for default support roles.")
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                support_role_mentions = ""
        channel_name = await interaction.client.db.fetchval("SELECT channel_name FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, topic)
        if channel_name:
            channel_name = channel_name.replace("{user.id}", str(interaction.user.id))
            channel_name = channel_name.replace("{user.name}", str(interaction.user.name))
            channel_name = channel_name.replace("{topic}", str(topic))
        else:
            channel_name = f"{topic}-{interaction.user.name}".replace("default", "ticket")
        counter_data = await interaction.client.db.fetchrow("SELECT * FROM ticket WHERE guild_id = $1", interaction.guild.id)
        if counter_data['counter_status']:
            channel_name = f"ticket-{counter_data['counter']:04d}"
            await interaction.client.db.execute("UPDATE ticket SET counter = counter + 1 WHERE guild_id = $1", interaction.guild.id)
        channel_topic = await interaction.client.db.fetchval("SELECT channel_topic FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, topic)
        if channel_topic:
            if user_inputs and 'formatted_code' in user_inputs:
                formatted_code_dict = user_inputs['formatted_code']
                for code, user_input in formatted_code_dict.items():
                    placeholder = f"{{{code}}}"
                    if placeholder in channel_topic:
                        pass
                    channel_topic = channel_topic.replace(placeholder, user_input)
            for code, user_input in user_inputs.get('user_inputs', {}).items():
                if isinstance(user_input, str):
                    placeholder = f"{{{code}}}"
                    if placeholder in channel_topic:
                        pass
                    channel_topic = channel_topic.replace(placeholder, user_input)
                else:
                    pass
            channel_topic = channel_topic.replace("{user.id}", str(interaction.user.id))
            channel_topic = channel_topic.replace("{user.name}", str(interaction.user.name))
            channel_topic = channel_topic.replace("{topic}", str(topic))
        else:
            channel_topic = f"A ticket opened by {interaction.user.name} ({interaction.user.id})"
        channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            topic=f"A ticket opened by {interaction.user.name} ({interaction.user.id})",
            reason=f"Ticket opened by {interaction.user.name}"
        )
        await channel.edit(sync_permissions=True)
        for target, overwrite in overwrites.items():
            await channel.set_permissions(target, overwrite=overwrite)
        await self.bot.db.execute("INSERT INTO ticket_opened (guild_id, channel_id, user_id, topic) VALUES ($1, $2, $3, $4)", interaction.guild.id, channel.id, interaction.user.id, topic)
        embed_template = await interaction.client.db.fetchval("SELECT embed FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, topic)
        if not embed_template:
            embed_template = await interaction.client.db.fetchval("SELECT open_embed FROM ticket WHERE guild_id = $1", interaction.guild.id)
            if not embed_template:
                embed_template = ("{embed}{color: #729bb0}$v{title: {title}}$v{description: Support will be with you shortly To close the ticket please press 🗑️}$v{author: name: {user.name} ({user.id}) && icon: {user.avatar}}$v{content: {user.mention} | {support.role}}")
        embed_filled = embed_template.replace("{title}", title or "Ticket opened")
        embed_filled = embed_filled.replace("{topic}", topic or "none")
        embed_filled = embed_filled.replace("{support.role}", support_role_mentions)
        if user_inputs:
            for code, user_input in user_inputs.items():
                if isinstance(user_input, str):
                    placeholder = f"{{{code}}}"
                    if placeholder in embed_filled:
                        pass
                    embed_filled = embed_filled.replace(placeholder, user_input)
                else:
                    pass
        x = await self.bot.embed_build.alt_convert(interaction.user, embed_filled)
        x["view"] = view
        try:
            mes = await channel.send(**x, allowed_mentions=discord.AllowedMentions.all())
        except Exception as e:
            try:
                return await interaction.response.send_message(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while sending the message\n```{e}```"), ephemeral=True)
            except Exception:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while sending the message\n```{e}```"), ephemeral=True)
        await mes.pin(reason="pinned the ticket message")
        claiming = await interaction.client.db.fetchval("SELECT claiming FROM ticket WHERE guild_id = $1", interaction.guild.id)
        if claiming == True:
            embed = Embed(color=colors.NEUTRAL, description=f"{emojis.QUESTION} Do you want to claim this ticket from {interaction.user.mention}?")
            view = TicketButtonView(interaction.client)
            view.claim_ticket()
            await channel.send(embed=embed, view=view)
        return channel

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            check = await interaction.client.db.fetchrow("SELECT * FROM ticket WHERE guild_id = $1", interaction.guild.id)
            if not check:
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Tickets module is disabled in this server.")
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            check_blacklist = await interaction.client.db.fetchrow("SELECT reason FROM ticket_blacklist WHERE guild_id = $1 AND user_id = $2", interaction.guild.id, interaction.user.id)
            if check_blacklist:
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from creating tickets.\n> **Reason:** {check_blacklist['reason']}")
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            results = await interaction.client.db.fetch("SELECT * FROM ticket_topics WHERE guild_id = $1 AND status = $2 ORDER BY weight ASC", interaction.guild.id, True)
            if len(results) == 0:
                existing_ticket_count = await interaction.client.db.fetchval("SELECT COUNT(*) FROM ticket_opened WHERE guild_id = $1 AND topic = $2 AND user_id = $3", interaction.guild.id, "default", interaction.user.id)
                limit_ticket_count = await interaction.client.db.fetchval(
                    'SELECT "limit" FROM ticket WHERE guild_id = $1',
                    interaction.guild.id)
                if existing_ticket_count >= limit_ticket_count:
                    embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You have reached the maximum number of open tickets")
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
                category_id = await interaction.client.db.fetchval("SELECT category_id FROM ticket WHERE guild_id = $1", interaction.guild.id)
                category = interaction.guild.get_channel(category_id)
                if not category:
                    category = None
                default_modal_data = await self.check_module(interaction, "default")
                if default_modal_data:
                    modal = TicketModal(self.bot, "default", default_modal_data)
                    return await interaction.response.send_modal(modal)
                channel = await self.create_channel(interaction, category, title="Ticket", topic="default")
                if check['owner_role']:
                    try:
                        owner_role = interaction.guild.get_role(check['owner_role'])
                        if owner_role:
                            await interaction.user.add_roles(owner_role, reason="ticket opened")
                    except Exception:
                        pass
                embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Opened a ticket for you in {channel.mention}")
                if interaction.response.is_done():
                    return await interaction.followup.send(embed=embed)
                else:
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
            options = []
            for result in results:
                emoji = await check_emoji(result["emoji"], interaction)
                if emoji is None:
                    options.append(discord.SelectOption(label=result["name"], description=result["description"]))
                else:
                    options.append(discord.SelectOption(label=result["name"], description=result["description"], emoji=emoji))
            select = discord.ui.Select(placeholder="Choose a topic", options=options)

            async def select_callback(select_interaction: discord.Interaction):
                selected_topic = select.values[0]
                existing_ticket_count = await interaction.client.db.fetchval("SELECT COUNT(*) FROM ticket_opened WHERE guild_id = $1 AND topic = $2 AND user_id = $3", interaction.guild.id, selected_topic, interaction.user.id)
                limit_ticket_count = await interaction.client.db.fetchval('SELECT "limit" FROM ticket WHERE guild_id = $1', interaction.guild.id)
                if existing_ticket_count >= limit_ticket_count:
                    embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You have reached the maximum number of open tickets for the topic **{selected_topic}**")
                    if select_interaction.response.is_done():
                        await select_interaction.followup.edit_message(embed=embed, view=None, message_id=select_interaction.message.id)
                    else:
                        await select_interaction.response.edit_message(embed=embed, view=None)
                    return
                module_data_list = await self.check_module(select_interaction, selected_topic)
                if module_data_list:
                    modal = TicketModal(self.bot, selected_topic, module_data_list)
                    try:
                        await select_interaction.response.send_modal(modal)
                    except Exception:
                        pass
                else:
                    user_inputs = {}
                    category_id = await interaction.client.db.fetchval("SELECT category_id FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, selected_topic)
                    category = interaction.guild.get_channel(category_id)
                    if not category:
                        category_id = await interaction.client.db.fetchval("SELECT category_id FROM ticket WHERE guild_id = $1", interaction.guild.id)
                        category = interaction.guild.get_channel(category_id)
                        if not category:
                            category = None
                    embed = Embed(color=colors.NEUTRAL, description=f"{emojis.LOADING} {interaction.user.mention}: Creating a ticket for you...")
                    if select_interaction.response.is_done():
                        await select_interaction.followup.edit_message(embed=embed, view=None, message_id=interaction.message.id)
                    else:
                        await select_interaction.response.edit_message(embed=embed, view=None)
                    channel = await self.create_channel(select_interaction, category, title=selected_topic, topic=selected_topic, user_inputs=user_inputs)
                    if check['owner_role']:
                        try:
                            owner_role = interaction.guild.get_role(check['owner_role'])
                            if owner_role:
                                await interaction.user.add_roles(owner_role, reason="ticket opened")
                        except Exception:
                            pass
                    embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Opened ticket for you in {channel.mention}")
                    if select_interaction.response.is_done():
                        await select_interaction.followup.edit_message(embed=embed, view=None, message_id=select_interaction.message.id)
                    else:
                        await select_interaction.response.edit_message(embed=embed, view=None)
            select.callback = select_callback
            view = discord.ui.View()
            view.add_item(select)
            try:
                if interaction.response.is_done():
                    embed = Embed(color=colors.NEUTRAL, description=f"{emojis.QUESTION} {interaction.user.mention}: Please select a topic for your ticket")
                    try:
                        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                    except Exception as e:
                        embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while creating the ticket\n ```{e}```")
                        await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    embed = Embed(color=colors.NEUTRAL, description=f"{emojis.QUESTION} {interaction.user.mention}: Please select a topic for your ticket")
                    try:
                        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                    except Exception as e:
                        embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while creating the ticket\n ```{e}```")
                        await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                pass
        except Exception as e:
            try:
                if interaction.response.is_done():
                    embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while creating the ticket\n ```{e}```")
                    await interaction.followup.send(embed=embed)
                else:
                    embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while creating the ticket\n ```{e}```")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                pass
        
class DeleteTicket(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Delete", emoji=emojis.DELETE, style=ButtonStyle.secondary, custom_id="ticket_delete:persistent")
        self.bot = bot

    async def make_transcript(self, c: discord.TextChannel) -> str:
        logId = secrets.token_hex(16)
        logs_directory = f"/var/www/html/{logId}"
        file = f"{logs_directory}/index.html"
        os.makedirs(logs_directory, exist_ok=True)
        file_handler = AttachmentToLocalFileHostHandler(
            base_path="/var/www/html/assets",
            url_base=f"https://{self.bot.transcript}/assets",
        )
        messages = await chat_exporter.export(c, attachment_handler=file_handler)
        if messages == "Whoops! Something went wrong...":
            return "https://evelina.bot"
        with open(file, "w", encoding="utf-8") as f:
            f.write(messages)
        return f"https://{self.bot.transcript}/{logId}"

    async def callback(self, interaction: discord.Interaction) -> None:
        support_ids = await interaction.client.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", interaction.guild.id)
        if support_ids:
            try:
                support_role_ids = json.loads(support_ids)
                if not isinstance(support_role_ids, list):
                    return await interaction.response.send_message(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} Unexpected data format for support roles."), ephemeral=True)
                user_has_role = any(interaction.guild.get_role(int(role_id)) in interaction.user.roles for role_id in support_role_ids)
                if not user_has_role and not interaction.user.guild_permissions.manage_channels:
                    return await interaction.response.send_message(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Only members with one of the support roles or members with `manage_channels` permission can close tickets."), ephemeral=True)
            except json.JSONDecodeError:
                return await interaction.response.send_message(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} Invalid JSON format for support roles."), ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_channels:
                return await interaction.response.send_message(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Only members with `manage_channels` permission can close tickets."))
        view = discord.ui.View()
        yes = discord.ui.Button(label="Yes", style=discord.ButtonStyle.success, custom_id="ticket_confirm_close:yes")
        no = discord.ui.Button(label="No", style=discord.ButtonStyle.danger, custom_id="ticket_confirm_close:no")
        view.add_item(yes)
        view.add_item(no)
        embed = discord.Embed(color=colors.NEUTRAL, description=f"{emojis.QUESTION} {interaction.user.mention}: Are you sure you want to close this ticket?")
        await interaction.response.send_message(embed=embed, view=view)

        async def yes_callback(inter: discord.Interaction) -> None:
            embed = discord.Embed(color=colors.LOADING, description=f"{emojis.LOADING} {interaction.user.mention}: Deleting this channel in 5 seconds")
            await inter.response.edit_message(embed=embed, view=None)
            ticket_owner = await inter.client.db.fetchval("SELECT user_id FROM ticket_opened WHERE channel_id = $1", inter.channel.id)
            ticket_owner_user = inter.guild.get_member(ticket_owner)
            ticket_category = await inter.client.db.fetchval("SELECT topic FROM ticket_opened WHERE channel_id = $1", inter.channel.id)
            if ticket_category == "default":
                ticket_category = "ticket"
            check = await inter.client.db.fetchrow("SELECT logs FROM ticket WHERE guild_id = $1", inter.guild.id)
            url = await self.make_transcript(inter.channel)
            await inter.client.db.execute("INSERT INTO ticket_transcripts (guild_id, user_id, moderator_id, id, topic, timestamp) VALUES ($1, $2, $3, $4, $5, $6)", inter.guild.id, ticket_owner, inter.user.id, url.rsplit('/', 1)[-1], str(ticket_category).capitalize(), datetime.datetime.now().timestamp())
            if check:
                channel = inter.guild.get_channel(check[0])
                if channel:
                    e = discord.Embed(color=colors.NEUTRAL, timestamp=datetime.datetime.now())
                    e.set_author(name=inter.guild.name, icon_url=inter.guild.icon or None)
                    e.set_footer(text=inter.guild.name, icon_url=inter.guild.icon or None)
                    e.add_field(name="Ticket ID", value=f"[`{url.rsplit('/', 1)[-1]}`]({url})", inline=False)
                    e.add_field(name="Moderator", value=inter.user.mention, inline=True)
                    e.add_field(name="Member", value=f"<@{ticket_owner}>", inline=True)
                    e.add_field(name="Category", value=str(ticket_category).capitalize(), inline=True)
                    v = View()
                    v.add_item(Button(label="View Transcript", url=url))
                    await channel.send(embed=e, view=v)
                    if ticket_owner_user:
                        try:
                            dm_channel = await ticket_owner_user.create_dm()
                            dm_e = discord.Embed(color=colors.NEUTRAL, timestamp=datetime.datetime.now())
                            dm_e.set_author(name=inter.guild.name, icon_url=inter.guild.icon or None)
                            dm_e.set_footer(text=inter.guild.name, icon_url=inter.guild.icon or None)
                            dm_e.add_field(name="Ticket ID", value=f"[`{url.rsplit('/', 1)[-1]}`]({url})", inline=False)
                            dm_e.add_field(name="Moderator", value=inter.user.mention, inline=True)
                            dm_e.add_field(name="Member", value=f"<@{ticket_owner}>", inline=True)
                            dm_e.add_field(name="Category", value=str(ticket_category).capitalize(), inline=True)
                            dm_view = View()
                            dm_view.add_item(Button(label=f"Sent from server: {inter.guild.name}", style=discord.ButtonStyle.secondary, disabled=True))
                            dm_view.add_item(Button(label="View Transcript", url=url))
                            await dm_channel.send(embed=dm_e, view=dm_view)
                        except discord.Forbidden:
                            pass
                        except discord.HTTPException:
                            pass
            await inter.client.db.execute("DELETE FROM ticket_opened WHERE guild_id = $1 AND channel_id = $2", inter.guild.id, inter.channel.id)
            await asyncio.sleep(5)
            try:
                await inter.channel.delete(reason="ticket closed")
            except Exception:
                pass
            owner_role_id = await interaction.client.db.fetchval("SELECT owner_role FROM ticket WHERE guild_id = $1", interaction.guild.id)
            if owner_role_id:
                try:
                    owner_role = interaction.guild.get_role(owner_role_id)
                    if owner_role:
                        await ticket_owner_user.remove_roles(owner_role, reason="ticket opened")
                except Exception:
                    pass

        async def no_callback(inter: discord.Interaction) -> None:
            embed = discord.Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: You changed your mind")
            if not inter.response.is_done():
                await inter.response.edit_message(embed=embed, view=None)
            else:
                await inter.followup.send(embed=embed, view=None)
        
        yes.callback = yes_callback
        no.callback = no_callback

class DeleteTicketRequest(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Close", emoji=emojis.CLOSE, style=ButtonStyle.danger, custom_id="ticket_delete_request:persistent")
        self.bot = bot

    async def make_transcript(self, c: discord.TextChannel) -> str:
        logId = secrets.token_hex(16)
        logs_directory = f"/var/www/html/{logId}"
        file = f"{logs_directory}/index.html"
        os.makedirs(logs_directory, exist_ok=True)
        file_handler = AttachmentToLocalFileHostHandler(
            base_path="/var/www/html/assets",
            url_base=f"https://{self.bot.transcript}/assets",
        )
        messages = await chat_exporter.export(c, attachment_handler=file_handler)
        if messages == "Whoops! Something went wrong...":
            return "https://evelina.bot"
        with open(file, "w", encoding="utf-8") as f:
            f.write(messages)
        return f"https://{self.bot.transcript}/{logId}"

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        ticket_owner = await interaction.client.db.fetchval("SELECT user_id FROM ticket_opened WHERE channel_id = $1", interaction.channel.id)
        ticket_owner_user = interaction.guild.get_member(ticket_owner)
        ticket_category = await interaction.client.db.fetchval("SELECT topic FROM ticket_opened WHERE channel_id = $1", interaction.channel.id)
        if ticket_category == "default":
            ticket_category = "ticket"
        check = await interaction.client.db.fetchrow("SELECT logs FROM ticket WHERE guild_id = $1", interaction.guild.id)
        url = await self.make_transcript(interaction.channel)
        await interaction.client.db.execute("INSERT INTO ticket_transcripts (guild_id, user_id, moderator_id, id, topic, timestamp) VALUES ($1, $2, $3, $4, $5, $6)", interaction.guild.id, ticket_owner, interaction.user.id, url.rsplit('/', 1)[-1], str(ticket_category).capitalize(), datetime.datetime.now().timestamp())
        if check:
            channel = interaction.guild.get_channel(check[0])
            if channel:
                e = discord.Embed(color=colors.NEUTRAL, timestamp=datetime.datetime.now())
                e.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon or None)
                e.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon or None)
                e.add_field(name="Ticket ID", value=f"[`{url.rsplit('/', 1)[-1]}`]({url})", inline=False)
                e.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                e.add_field(name="Member", value=f"<@{ticket_owner}>", inline=True)
                e.add_field(name="Category", value=str(ticket_category).capitalize(), inline=True)
                v = View()
                v.add_item(Button(label="View Transcript", url=url))
                await channel.send(embed=e, view=v)
                if ticket_owner_user:
                    try:
                        dm_channel = await ticket_owner_user.create_dm()
                        dm_e = discord.Embed(color=colors.NEUTRAL, timestamp=datetime.datetime.now())
                        dm_e.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon or None)
                        dm_e.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon or None)
                        dm_e.add_field(name="Ticket ID", value=f"[`{url.rsplit('/', 1)[-1]}`]({url})", inline=False)
                        dm_e.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                        dm_e.add_field(name="Member", value=f"<@{ticket_owner}>", inline=True)
                        dm_e.add_field(name="Category", value=str(ticket_category).capitalize(), inline=True)
                        dm_view = View()
                        dm_view.add_item(Button(label=f"Sent from server: {interaction.guild.name}", style=discord.ButtonStyle.secondary, disabled=True))
                        dm_view.add_item(Button(label="View Transcript", url=url))
                        await dm_channel.send(embed=dm_e, view=dm_view)
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException as ex:
                        pass
        await interaction.client.db.execute("DELETE FROM ticket_opened WHERE guild_id = $1 AND channel_id = $2", interaction.guild.id, interaction.channel.id)
        embed = discord.Embed(color=colors.LOADING, description=f"{emojis.LOADING} {interaction.user.mention}: Deleting this channel")
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=None)
        try:
            await interaction.channel.delete(reason="ticket closed")
        except Exception:
            pass
        owner_role_id = await interaction.client.db.fetchval("SELECT owner_role FROM ticket WHERE guild_id = $1", interaction.guild.id)
        if owner_role_id:
            try:
                owner_role = interaction.guild.get_role(owner_role_id)
                if owner_role:
                    await ticket_owner_user.remove_roles(owner_role, reason="ticket opened")
            except Exception:
                pass

class CloseTicket(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", emoji=emojis.CLOSE, style=ButtonStyle.danger, custom_id="ticket_close:persistent")
        self.last_interaction = {}

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer()
        now = time.time()
        last_time = self.last_interaction.get(interaction.channel.id, 0)
        if now - last_time < 5:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        self.last_interaction[interaction.channel.id] = now
        message = await interaction.channel.fetch_message(interaction.message.id)
        view = TicketButtonView(interaction.client)
        view.open_ticket()
        view.transcript_ticket()
        view.delete_ticket()
        await message.edit(view=view)
        check = await interaction.client.db.fetchrow("SELECT * FROM ticket_opened WHERE channel_id = $1", interaction.channel.id)
        if check is None:
            return await interaction.followup.send("Ticket data not found.", ephemeral=True)
        ticket_channel = interaction.guild.get_channel(interaction.channel.id)
        ticket_owner = interaction.client.get_user(check['user_id'])
        if ticket_channel is None:
            return await interaction.followup.send("Ticket channel not found.", ephemeral=True)
        if ticket_owner is None:
            return await interaction.followup.send("Ticket owner not found.", ephemeral=True)
        overwrites = ticket_channel.overwrites_for(ticket_owner)
        overwrites.read_messages = False
        overwrites.send_messages = False
        overwrites.attach_files = False
        overwrites.embed_links = False
        try:
            await ticket_channel.set_permissions(ticket_owner, overwrite=overwrites)
        except Exception:
            pass
        closed_category_id = await interaction.client.db.fetchval("SELECT closed FROM ticket WHERE guild_id = $1", interaction.guild.id)
        if closed_category_id:
            closed_category = interaction.guild.get_channel(closed_category_id)
            if closed_category and closed_category.type == discord.ChannelType.category:
                try:
                    await ticket_channel.edit(name=f"closed-{ticket_owner.name}".replace("default", "ticket"), category=closed_category)
                except Exception:
                    pass
            else:
                pass
        else:
            await ticket_channel.edit(name=f"closed-{ticket_owner.name}".replace("default", "ticket"))
        embed = discord.Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Closed the ticket")
        close_view = TicketButtonView(interaction.client)
        close_view.open_ticket()
        close_view.transcript_ticket()
        close_view.delete_ticket()
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=close_view)
            else:
                await interaction.response.send_message(embed=embed, view=close_view)
        except Exception:
            pass

class OpenTicket(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Open", emoji=emojis.OPEN, style=ButtonStyle.success, custom_id="ticket_reopen:persistent")
        self.last_interaction = {}

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer()
        now = time.time()
        last_time = self.last_interaction.get(interaction.channel.id, 0)
        if now - last_time < 5:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        self.last_interaction[interaction.channel.id] = now
        message = await interaction.channel.fetch_message(interaction.message.id)
        view = TicketButtonView(interaction.client)
        view.close_ticket()
        view.transcript_ticket()
        view.delete_ticket()
        await message.edit(view=view)
        check = await interaction.client.db.fetchrow("SELECT * FROM ticket_opened WHERE channel_id = $1", interaction.channel.id)
        if check is None:
            return await interaction.followup.send("Ticket data not found.", ephemeral=True)
        ticket_channel = interaction.guild.get_channel(interaction.channel.id)
        ticket_owner = interaction.client.get_user(check['user_id'])
        if ticket_channel is None:
            return await interaction.followup.send("Ticket channel not found.", ephemeral=True)
        if ticket_owner is None:
            return await interaction.followup.send("Ticket owner not found.", ephemeral=True)
        overwrites = ticket_channel.overwrites_for(ticket_owner)
        overwrites.read_messages = True
        overwrites.send_messages = True
        overwrites.attach_files = True
        overwrites.embed_links = True
        try:
            await ticket_channel.set_permissions(ticket_owner, overwrite=overwrites)
        except Exception:
            pass
        topic_category_id = await interaction.client.db.fetchval("SELECT category_id FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, check['topic'])
        if topic_category_id:
            topic_category = interaction.guild.get_channel(topic_category_id)
            if topic_category and topic_category.type == discord.ChannelType.category:
                try:
                    await ticket_channel.edit(name=f"{check['topic']}-{ticket_owner.name}".replace("default", "ticket"), category=topic_category)
                except Exception:
                    pass
            else:
                pass
        else:
            await ticket_channel.edit(name=f"{check['topic']}-{ticket_owner.name}".replace("default", "ticket"))
        embed = discord.Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Opened the ticket")
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

class TicketTranscript(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Transcript", emoji=emojis.TRANSCRIPT, style=ButtonStyle.primary, custom_id="ticket_transcript:persistent")
        self.bot = bot

    async def make_transcript(self, c: discord.TextChannel) -> str:
        logId = secrets.token_hex(16)
        logs_directory = f"/var/www/html/{logId}"
        file = f"{logs_directory}/index.html"
        os.makedirs(logs_directory, exist_ok=True)
        file_handler = AttachmentToLocalFileHostHandler(
            base_path="/var/www/html/assets",
            url_base=f"https://{self.bot.transcript}/assets",
        )
        messages = await chat_exporter.export(c, attachment_handler=file_handler)
        if messages == "Whoops! Something went wrong...":
            return "https://evelina.bot"
        with open(file, "w", encoding="utf-8") as f:
            f.write(messages)
        return f"https://{self.bot.transcript}/{logId}"

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        support_ids = await interaction.client.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", interaction.guild.id)
        if support_ids:
            try:
                support_role_ids = json.loads(support_ids)
                if not isinstance(support_role_ids, list):
                    return await interaction.followup.send(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} Unexpected data format for support roles."), ephemeral=True)
                user_has_role = any(interaction.guild.get_role(int(role_id)) in interaction.user.roles for role_id in support_role_ids)
                if not user_has_role and not interaction.user.guild_permissions.manage_channels:
                    return await interaction.followup.send(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Only members with one of the support roles or members with `manage_channels` permission can create ticket transcripts."), ephemeral=True)
            except json.JSONDecodeError:
                return await interaction.followup.send(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} Invalid JSON format for support roles."), ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_channels:
                return await interaction.followup.send(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Only members with `manage_channels` permission can create ticket transcripts."))
        ticket_owner = await interaction.client.db.fetchval("SELECT user_id FROM ticket_opened WHERE channel_id = $1", interaction.channel.id)
        ticket_category = await interaction.client.db.fetchval("SELECT topic FROM ticket_opened WHERE channel_id = $1", interaction.channel.id)
        check = await interaction.client.db.fetchrow("SELECT logs FROM ticket WHERE guild_id = $1", interaction.guild.id)
        url = await self.make_transcript(interaction.channel)
        if check:
            channel = interaction.guild.get_channel(check[0])
            if channel:
                e = discord.Embed(color=colors.NEUTRAL, timestamp=datetime.datetime.now())
                e.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon or None)
                e.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon or None)
                e.add_field(name="Ticket ID", value=f"[`{url.rsplit('/', 1)[-1]}`]({url})", inline=False)
                e.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                e.add_field(name="Member", value=f"<@{ticket_owner}>", inline=True)
                e.add_field(name="Category", value=str(ticket_category).capitalize(), inline=True)
                v = View()
                v.add_item(Button(label="View Transcript", url=url))
                await channel.send(embed=e, view=v)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Transcript generated [**here**]({url})")
            return await interaction.followup.send(embed=embed)
        else:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Transcripts are disabled in this server\n> Enable it with `;ticket settings logs [channel]`")
            return await interaction.followup.send(embed=embed, ephemeral=True)
    
class ClaimTicket(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Claim Ticket", emoji=None, style=ButtonStyle.success, custom_id="ticket_claim:persistent")

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        support_ids = await interaction.client.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", interaction.guild.id)
        if support_ids:
            try:
                support_role_ids = json.loads(support_ids)
                if not isinstance(support_role_ids, list):
                    return await interaction.followup.send(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} Unexpected data format for support roles."), ephemeral=True)
                user_has_role = any(interaction.guild.get_role(int(role_id)) in interaction.user.roles for role_id in support_role_ids)
                if not user_has_role and not interaction.user.guild_permissions.manage_channels:
                    return await interaction.followup.send(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Only members with one of the support roles or members with `manage_channels` permission can claim tickets."), ephemeral=True)
            except json.JSONDecodeError:
                return await interaction.followup.send(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} Invalid JSON format for support roles."), ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_channels:
                return await interaction.followup.send(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Only members with `manage_channels` permission can claim tickets."), ephemeral=True)
        ticket = await interaction.client.db.fetchrow("SELECT * FROM ticket_opened WHERE channel_id = $1", interaction.channel.id)
        if ticket['claimed_by'] is not None:
            return await interaction.followup.send(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Ticket is already claimed by <@{ticket['claimed_by']}>"), ephemeral=True)
        support_roles_data = None
        if ticket['topic'] == "default":
            support_roles_data = await interaction.client.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", interaction.guild.id)
        else:
            support_roles_data = await interaction.client.db.fetchval("SELECT support_roles FROM ticket_topics WHERE guild_id = $1 AND name = $2", interaction.guild.id, ticket['topic'])
            if not support_roles_data or not json.loads(support_roles_data):
                support_roles_data = await interaction.client.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", interaction.guild.id)
        support_roles = json.loads(support_roles_data) if support_roles_data else []
        for role_id in support_roles:
            role = interaction.guild.get_role(int(role_id))
            if role:
                private = await interaction.client.db.fetchval("SELECT claiming_privat FROM ticket WHERE guild_id = $1", interaction.guild.id)
                if private == True:
                    try:
                        overwrite = interaction.channel.overwrites_for(role)
                        overwrite.send_messages = False
                        overwrite.read_messages = False
                        await interaction.channel.set_permissions(role, overwrite=overwrite, reason="Ticket claimed by a staff member")
                    except Exception:
                        continue
                else:
                    try:
                        overwrite = interaction.channel.overwrites_for(role)
                        overwrite.send_messages = False
                        await interaction.channel.set_permissions(role, overwrite=overwrite, reason="Ticket claimed by a staff member")
                    except Exception:
                        continue
        try:
            overwrite = interaction.channel.overwrites_for(interaction.user)
            overwrite.send_messages = True
            overwrite.read_messages = True
            await interaction.channel.set_permissions(interaction.user, overwrite=overwrite, reason="Claimed the ticket")
        except Exception:
            pass
        await interaction.client.db.execute("UPDATE ticket_opened SET claimed_by = $1 WHERE channel_id = $2", interaction.user.id, interaction.channel.id)
        prefix = await interaction.client.db.fetchval("SELECT prefix FROM prefixes WHERE guild_id = $1", interaction.guild.id)
        if not prefix:
            prefix = ";"
        embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Claimed the ticket from <@{ticket['user_id']}>\n> You can unclaim it by running `{prefix}ticket unclaim`")
        claim_check = await interaction.client.db.fetchrow("SELECT * FROM ticket_claims WHERE guild_id = $1 AND channel_id = $2", interaction.guild.id, interaction.channel.id)
        if not claim_check:
            await interaction.client.db.execute("INSERT INTO ticket_claims (guild_id, user_id, channel_id) VALUES ($1, $2, $3)", interaction.guild.id, interaction.user.id, interaction.channel.id)
        else:
            await interaction.client.db.execute("UPDATE ticket_claims SET user_id = $1 WHERE guild_id = $2 AND channel_id = $3", interaction.user.id, interaction.guild.id, interaction.channel.id)
        await interaction.followup.edit_message(embed=embed, view=None, message_id=interaction.message.id)

class DeleteTicketRequestView(discord.ui.View):
    def __init__(self, bot: commands.AutoShardedBot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(DeleteTicketRequest(self.bot))

class TicketButtonView(discord.ui.View):
    def __init__(self, bot: commands.AutoShardedBot, adding: bool = False):
        super().__init__(timeout=None)
        self.bot = bot
        self.adding = adding
        if self.adding:
            self.add_item(ButtonTicket(self.bot))
            self.add_item(OpenTicket())
            self.add_item(CloseTicket())
            self.add_item(TicketTranscript(self.bot))
            self.add_item(DeleteTicket(self.bot))
            self.add_item(ClaimTicket())

    def create_ticket(self):
        self.add_item(ButtonTicket(self.bot))

    def open_ticket(self):
        self.add_item(OpenTicket())

    def close_ticket(self):
        self.add_item(CloseTicket())
    
    def transcript_ticket(self):
        self.add_item(TicketTranscript(self.bot))

    def delete_ticket(self):
        self.add_item(DeleteTicket(self.bot))

    def claim_ticket(self):
        self.add_item(ClaimTicket())