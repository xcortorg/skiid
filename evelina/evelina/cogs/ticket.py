import os
import string
import random
import json
import asyncio
import datetime
import chat_exporter
import secrets

from typing import Union
from chat_exporter import AttachmentToLocalFileHostHandler

from discord import PermissionOverwrite, Member, Embed, Role, CategoryChannel, TextChannel, Interaction, ButtonStyle, SelectOption, Emoji, PartialEmoji, Thread, User
from discord.ui import View, Button, Select
from discord.utils import get
from discord.ext.commands import Cog, has_guild_permissions, bot_has_guild_permissions, group, command, cooldown, BucketType

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.converters import NewRoleConverter
from modules.persistent.tickets import TicketTopic, TicketButtonView, DeleteTicketRequestView
from modules.predicates import get_ticket, manage_ticket, close_ticket, ticket_exists

async def check_emoji(emoji: str, interaction: Interaction):
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

class Ticket(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Ticket commands"

    async def make_transcript(self, c: TextChannel):
        try:
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
        except Exception:
            return "https://evelina.bot"

    @group(name="ticket", aliases=["t", "tickets"], invoke_without_command=True, description="Ticket commands")
    async def ticket(self, ctx: EvelinaContext):
        """Ticket commands"""
        return await ctx.create_pages()

    @ticket.command(name="setup", brief="manage guild", description="Setup the ticket system")
    @has_guild_permissions(manage_guild=True)
    async def ticket_setup(self, ctx: EvelinaContext):
        """Setup the ticket system"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket WHERE guild_id = $1)", ctx.guild.id)
        if check:
            return await ctx.send_warning("Ticket system is already setup")
        else:
            await self.bot.db.execute("INSERT INTO ticket (guild_id) VALUES ($1)", ctx.guild.id)
        topics = []
        while True:
            await ctx.send_question("Please enter a topic name (or type `done` to finish):")
            topic_name = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author)
            if topic_name.content.lower() == 'done':
                break
            await ctx.send_question("Please mention the support roles for this topic (or type `none` if there are no specific roles):")
            roles_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and (m.role_mentions or m.content.lower() == 'none'))
            roles = [role.id for role in roles_message.role_mentions] if roles_message.content.lower() != 'none' else []
            await ctx.send_question("Please enter the embed message for this topic (or type `default` to use the default embed):")
            embed_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author)
            embed_code = embed_message.content if embed_message.content.lower() != 'default' else None
            await ctx.send_question("Please enter the description for this topic (or type `none` to skip):")
            description_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author)
            description = description_message.content if description_message.content.lower() != 'none' else None
            await ctx.send_question("Please enter the emoji for this topic (or type `none` to skip):")
            emoji_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author)
            emoji = emoji_message.content if emoji_message.content.lower() != 'none' else None
            await ctx.send_question("Please mention the category for this topic (or type `none` to skip):")
            category_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and (m.channel_mentions or m.content.lower() == 'none'))
            category_id = category_message.channel_mentions[0].id if category_message.content.lower() != 'none' else None
            topics.append((topic_name.content, roles, embed_code, description, emoji, category_id))
            await self.bot.db.execute("INSERT INTO ticket_topics (guild_id, name, support_roles, embed, description, emoji, category_id) VALUES ($1, $2, $3, $4, $5, $6, $7)", ctx.guild.id, topic_name.content, json.dumps(roles), embed_code, description, emoji, category_id)
            await ctx.send_question(f"Added topic: {topic_name.content} with roles: {', '.join([f'<@&{role}>' for role in roles])}")
        await ctx.send_question("Please enter the embed message for the ticket panel (or type `default` to use the default embed):")
        embed_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author)
        embed_code = embed_message.content if embed_message.content.lower() != 'default' else None
        await self.bot.db.execute("UPDATE ticket SET open_embed = $1 WHERE guild_id = $2", embed_code, ctx.guild.id)
        await ctx.send_question("Please mention the default category for tickets (or type `none` to skip):")
        category_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and (m.channel_mentions or m.content.lower() == 'none'))
        category_id = category_message.channel_mentions[0].id if category_message.content.lower() != 'none' else None
        await self.bot.db.execute("UPDATE ticket SET category_id = $1 WHERE guild_id = $2", category_id, ctx.guild.id)
        await ctx.send_question("Please mention the logs channel for tickets (or type `none` to skip):")
        logs_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and (m.channel_mentions or m.content.lower() == 'none'))
        logs_channel_id = logs_message.channel_mentions[0].id if logs_message.content.lower() != 'none' else None
        await self.bot.db.execute("UPDATE ticket SET logs = $1 WHERE guild_id = $2", logs_channel_id, ctx.guild.id)
        await ctx.send_question("Please mention the support roles for tickets (or type `none` if there are no specific roles):")
        roles_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and (m.role_mentions or m.content.lower() == 'none'))
        roles = [role.id for role in roles_message.role_mentions] if roles_message.content.lower() != 'none' else []
        await self.bot.db.execute("UPDATE ticket SET support_roles = $1 WHERE guild_id = $2", json.dumps(roles), ctx.guild.id)
        await ctx.send_question("Please mention the channel where you want to send the ticket panel:")
        channel_message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel_mentions)
        channel = channel_message.channel_mentions[0]
        code = embed_message.content if embed_message.content.lower() != 'default' else "{embed}{color: #729bb0}$v{title: Create a ticket}$v{description: Please select your inquiry below.\nDo **not** create a ticket and suddenly go offline.\n> Refer to [nohello.net](https://nohello.net)}$v{thumbnail: {guild.icon}}"
        x = await self.bot.embed_build.convert(ctx, code)
        view = TicketButtonView(self.bot)
        view.create_ticket()
        x["view"] = view
        try:
            await channel.send(**x)
            return await ctx.send_success(f"Sent the ticket panel to {channel.mention}")
        except Exception as e:
            return await ctx.send_warning(f"An error occurred while trying to send the ticket panel:\n ```{e}```")

    @ticket.command(name="allow", aliases=["add"], brief="ticket support / manage channels", usage="ticket allow comminate", description="Add a user or role to the ticket")
    @manage_ticket()
    @get_ticket()
    async def ticket_allow(self, ctx: EvelinaContext, *, target: Union[Member, Role]):
        """Add a user or role to the ticket"""
        overwrites = PermissionOverwrite()
        overwrites.send_messages = True
        overwrites.view_channel = True
        overwrites.attach_files = True
        overwrites.embed_links = True
        await ctx.channel.set_permissions(target, overwrite=overwrites, reason="Added to the ticket")
        if isinstance(target, Member):
            try:
                dm_button = Button(label=f"Sent from server: {ctx.guild.name}", style=ButtonStyle.secondary, disabled=True)
                dm_view = View()
                dm_view.add_item(dm_button)
                dm_embed = Embed(color=colors.NEUTRAL, description=f"You have been added to the ticket: {ctx.channel.mention}")
                await target.send(embed=dm_embed, view=dm_view)
            except Exception:
                pass
            return await ctx.send_success(f"Added {target.mention} to the ticket")
        else:
            return await ctx.send_success(f"Added {target.mention} to the ticket")

    @ticket.command(name="unallow", aliases=["remove"], brief="ticket support / manage channels", usage="ticket unallow comminate", description="Remove a user or role from the ticket")
    @manage_ticket()
    @get_ticket()
    async def ticket_unallow(self, ctx: EvelinaContext, *, target: Union[Member, Role]):
        """Remove a user or role from the ticket"""
        overwrites = PermissionOverwrite()
        overwrites.send_messages = False
        overwrites.view_channel = False
        overwrites.attach_files = False
        overwrites.embed_links = False
        await ctx.channel.set_permissions(target, overwrite=overwrites, reason="Removed from the ticket")
        if isinstance(target, Member):
            return await ctx.send_success(f"Removed {target.mention} from the ticket")
        else:
            return await ctx.send_success(f"Removed {target.mention} from the ticket")
        
    @ticket.group(name="claiming", brief="manage guild", invoke_without_command=True, description="Configure the ticket claiming system", case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_claiming(self, ctx: EvelinaContext):
        """Configure the ticket claiming system"""
        return await ctx.create_pages()
    
    @ticket_claiming.command(name="enable", brief="manage guild", description="Enable the ticket claiming system")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_claiming_enable(self, ctx: EvelinaContext):
        """Enable the ticket claiming system"""
        claiming = await self.bot.db.fetchval("SELECT claiming FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if claiming == True:
            return await ctx.send_warning(f"Ticket claiming system is **already** enabled")
        await self.bot.db.execute("UPDATE ticket SET claiming = $1 WHERE guild_id = $2", True, ctx.guild.id)
        return await ctx.send_success("Enabled the ticket claiming system")
    
    @ticket_claiming.command(name="disable", brief="manage guild", description="Disable the ticket claiming system")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_claiming_disable(self, ctx: EvelinaContext):
        """Disable the ticket claiming system"""
        claiming = await self.bot.db.fetchval("SELECT claiming FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if claiming == False:
            return await ctx.send_warning(f"Ticket claiming system is **already** disabled")
        await self.bot.db.execute("UPDATE ticket SET claiming = $1 WHERE guild_id = $2", False, ctx.guild.id)
        return await ctx.send_success("Disabled the ticket claiming system")
    
    @ticket_claiming.command(name="privat", brief="manage guild", description="Set the ticket claiming system to private")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_claiming_privat(self, ctx: EvelinaContext):
        """Set the ticket claiming system to private"""
        claiming = await self.bot.db.fetchval("SELECT claiming_privat FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if claiming == True:
            return await ctx.send_warning(f"Ticket claiming system is **already** privat")
        await self.bot.db.execute("UPDATE ticket SET claiming_privat = $1 WHERE guild_id = $2", True, ctx.guild.id)
        return await ctx.send_success("Set the ticket claiming system to privat")
    
    @ticket_claiming.command(name="public", brief="manage guild", description="Set the ticket claiming system to public")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_claiming_public(self, ctx: EvelinaContext):
        """Set the ticket claiming system to public"""
        claiming = await self.bot.db.fetchval("SELECT claiming_privat FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if claiming == False:
            return await ctx.send_warning(f"Ticket claiming system is **already** public")
        await self.bot.db.execute("UPDATE ticket SET claiming_privat = $1 WHERE guild_id = $2", False, ctx.guild.id)
        return await ctx.send_success("Set the ticket claiming system to public")
        
    @ticket.command(name="claim", brief="ticket support / manage channels", description="Claim the current ticket")
    @manage_ticket()
    @get_ticket()
    async def ticket_claim(self, ctx: EvelinaContext):
        """Claim the current ticket"""
        claiming = await self.bot.db.fetchval("SELECT claiming FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if claiming == False:
            return await ctx.send_warning(f"Ticket claiming system is **disabled**")
        ticket = await self.bot.db.fetchrow("SELECT * FROM ticket_opened WHERE channel_id = $1", ctx.channel.id)
        if ticket['claimed_by'] is not None:
            return await ctx.send_warning(f"Ticket is already claimed by <@{ticket['claimed_by']}>")
        support_roles_data = None
        if ticket['topic'] == "default":
            support_roles_data = await self.bot.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", ctx.guild.id)
        else:
            support_roles_data = await self.bot.db.fetchval("SELECT support_roles FROM ticket_topics WHERE guild_id = $1 AND name = $2", ctx.guild.id, ticket['topic'])
            if not support_roles_data or not json.loads(support_roles_data):
                support_roles_data = await self.bot.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", ctx.guild.id)
        support_roles = json.loads(support_roles_data) if support_roles_data else []
        for role_id in support_roles:
            role = ctx.guild.get_role(int(role_id))
            if role:
                private = await ctx.bot.db.fetchval("SELECT claiming_privat FROM ticket WHERE guild_id = $1", ctx.guild.id)
                if private == True:
                    try:
                        overwrite = ctx.channel.overwrites_for(role)
                        overwrite.send_messages = False
                        overwrite.read_messages = False
                        await ctx.channel.set_permissions(role, overwrite=overwrite, reason="Ticket claimed by a staff member")
                    except Exception:
                        continue
                else:
                    try:
                        overwrite = ctx.channel.overwrites_for(role)
                        overwrite.send_messages = False
                        await ctx.channel.set_permissions(role, overwrite=overwrite, reason="Ticket claimed by a staff member")
                    except Exception:
                        continue
        try:
            overwrite = ctx.channel.overwrites_for(ctx.author)
            overwrite.send_messages = True
            overwrite.read_messages = True
            await ctx.channel.set_permissions(ctx.author, overwrite=overwrite, reason="Claimed the ticket")
        except Exception:
            pass
        claim_check = await self.bot.db.fetchrow("SELECT * FROM ticket_claims WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, ctx.channel.id)
        if not claim_check:
            await self.bot.db.execute("INSERT INTO ticket_claims (guild_id, user_id, channel_id) VALUES ($1, $2, $3)", ctx.guild.id, ctx.author.id, ctx.channel.id)
        else:
            await self.bot.db.execute("UPDATE ticket_claims SET user_id = $1 WHERE guild_id = $2 AND channel_id = $3", ctx.author.id, ctx.guild.id, ctx.channel.id)
        await self.bot.db.execute("UPDATE ticket_opened SET claimed_by = $1 WHERE channel_id = $2", ctx.author.id, ctx.channel.id)
        await ctx.send_success(f"Claimed the ticket from <@{ticket['user_id']}>")

    @ticket.command(name="unclaim", brief="ticket support / manage channels", description="Unclaim the current ticket")
    @manage_ticket()
    @get_ticket()
    async def ticket_unclaim(self, ctx: EvelinaContext):
        """Unclaim the current ticket"""
        ticket = await self.bot.db.fetchrow("SELECT * FROM ticket_opened WHERE channel_id = $1", ctx.channel.id)
        if ticket['claimed_by'] is None:
            return await ctx.send_warning("Ticket is not claimed by anyone")
        support_roles_data = None
        if ticket['topic'] == "default":
            support_roles_data = await self.bot.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", ctx.guild.id)
        else:
            support_roles_data = await self.bot.db.fetchval("SELECT support_roles FROM ticket_topics WHERE guild_id = $1 AND name = $2", ctx.guild.id, ticket['topic'])
            if not support_roles_data or not json.loads(support_roles_data):
                support_roles_data = await self.bot.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", ctx.guild.id)
        support_roles = json.loads(support_roles_data) if support_roles_data else []
        for role_id in support_roles:
            role = ctx.guild.get_role(int(role_id))
            if role:
                try:
                    overwrite = ctx.channel.overwrites_for(role)
                    overwrite.send_messages = True
                    overwrite.read_messages = True
                    await ctx.channel.set_permissions(role, overwrite=overwrite, reason="Ticket unclaimed by a staff member")
                except Exception:
                    continue
        try:
            overwrite = ctx.channel.overwrites_for(ctx.author)
            overwrite.send_messages = None
            await ctx.channel.set_permissions(ctx.author, overwrite=overwrite, reason="Unclaimed the ticket")
        except Exception:
            pass
        claim_check = await self.bot.db.fetchrow("SELECT * FROM ticket_claims WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, ctx.channel.id)
        if claim_check:
            await self.bot.db.execute("DELETE FROM ticket_claims WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, ctx.channel.id)
        await self.bot.db.execute("UPDATE ticket_opened SET claimed_by = $1 WHERE channel_id = $2", None, ctx.channel.id)
        await ctx.send_success(f"Unclaimed the ticket from <@{ticket['user_id']}>")
    
    @ticket.command(name="leaderboard", aliases=["lb"], description="View the ticket leaderboard")
    async def ticket_leaderboard(self, ctx: EvelinaContext):
        """View the ticket leaderboard"""
        results = await self.bot.db.fetch("SELECT user_id, COUNT(user_id) FROM ticket_claims WHERE guild_id = $1 GROUP BY user_id ORDER BY COUNT(user_id) DESC", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There are no claims saved")
        content = []
        for result in results:
            user = ctx.guild.get_member(result['user_id'])
            if user:
                content.append(f"{user.mention}: {result['count']}")
        return await ctx.paginate(content, title="Ticket Leaderboard", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @ticket.command(name="remind", aliases=["r"], brief="ticket support / manage channels", description="Remind the ticket owner")
    @manage_ticket()
    @get_ticket()
    @cooldown(1, 300, BucketType.channel)
    async def ticket_remind(self, ctx: EvelinaContext, *, reason: str = None):
        """Remind the ticket owner"""
        await ctx.message.delete()
        ticket_owner_id = await self.bot.db.fetchval("SELECT user_id FROM ticket_opened WHERE channel_id = $1", ctx.channel.id)
        ticket_owner = ctx.guild.get_member(ticket_owner_id)
        if ticket_owner:
            try:
                dm_button = Button(label=f"Sent from server: {ctx.guild.name}", style=ButtonStyle.secondary, disabled=True)
                dm_view = View()
                dm_view.add_item(dm_button)
                if reason:
                    dm_embed = Embed(color=colors.NEUTRAL, description=f"# ⏰ Friendly Reminder\nHi, if you see this message it probably means you forgot about your open ticket.\nMake sure to check it out: {ctx.channel.mention} in reason of {reason}")
                else:
                    dm_embed = Embed(color=colors.NEUTRAL, description=f"# ⏰ Friendly Reminder\nHi, if you see this message it probably means you forgot about your open ticket.\nMake sure to check it out: {ctx.channel.mention}")
                await ticket_owner.send(embed=dm_embed, view=dm_view)
                return await ctx.send_success(f"Reminder was successfully sent to {ticket_owner.mention}")
            except Exception:
                await ctx.send_warning(f"{ticket_owner.mention} has disabled their Direct Messages for this server.")
    
    @command(name="tc", brief="ticket support / manage channels", description="Close the current ticket")
    @close_ticket()
    @get_ticket()
    async def tc(self, ctx: EvelinaContext):
        """Close the current ticket"""
        await self.ticket_close(ctx)

    @ticket.command(name="close", brief="ticket support / manage channels", description="Close the current ticket")
    @close_ticket()
    @get_ticket()
    async def ticket_close(self, ctx: EvelinaContext):
        """Close the current ticket"""
        ticket_owner = await self.bot.db.fetchval("SELECT user_id FROM ticket_opened WHERE channel_id = $1", ctx.channel.id)
        ticket_owner_user = ctx.guild.get_member(ticket_owner)
        ticket_category = await self.bot.db.fetchval("SELECT topic FROM ticket_opened WHERE channel_id = $1", ctx.channel.id)
        if ticket_category == "default":
            ticket_category = "ticket"
        check = await self.bot.db.fetchrow("SELECT logs FROM ticket WHERE guild_id = $1", ctx.guild.id)
        message = await ctx.send(embed=Embed(color=colors.LOADING, description=f"{emojis.LOADING} {ctx.author.mention}: Transcript generation in progress..."))
        url = await self.make_transcript(ctx.channel)
        await self.bot.db.execute("INSERT INTO ticket_transcripts (guild_id, user_id, moderator_id, id, topic, timestamp) VALUES ($1, $2, $3, $4, $5, $6)", ctx.guild.id, ticket_owner, ctx.author.id, url.rsplit('/', 1)[-1], str(ticket_category).capitalize(), datetime.datetime.now().timestamp())
        if check:
            channel = ctx.guild.get_channel(check[0])
            if channel:
                e = Embed(color=colors.NEUTRAL, timestamp=datetime.datetime.now())
                e.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon or None)
                e.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon or None)
                e.add_field(name="Ticket ID", value=f"[`{url.rsplit('/', 1)[-1]}`]({url})", inline=False)
                e.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                e.add_field(name="Member", value=f"<@{ticket_owner}>", inline=True)
                e.add_field(name="Category", value=str(ticket_category).capitalize(), inline=True)
                v = View()
                v.add_item(Button(label=f"View Transcript", url=url))
                await channel.send(embed=e, view=v)
                if ticket_owner_user:
                    try:
                        dm_channel = await ticket_owner_user.create_dm()
                        dm_e = Embed(color=colors.NEUTRAL, timestamp=datetime.datetime.now())
                        dm_e.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon or None)
                        dm_e.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon or None)
                        dm_e.add_field(name="Ticket ID", value=f"[`{url.rsplit('/', 1)[-1]}`]({url})", inline=False)
                        dm_e.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                        dm_e.add_field(name="Member", value=f"<@{ticket_owner}>", inline=True)
                        dm_e.add_field(name="Category", value=str(ticket_category).capitalize(), inline=True)
                        dm_view = View()
                        dm_view.add_item(Button(label=f"Sent from server: {ctx.guild.name}", style=ButtonStyle.secondary, disabled=True))
                        dm_view.add_item(Button(label=f"View Transcript", url=url))
                        await dm_channel.send(embed=dm_e, view=dm_view)
                    except Exception:
                        pass
        owner_role_id = await self.bot.db.fetchval("SELECT owner_role FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if owner_role_id:
            try:
                owner_role = ctx.guild.get_role(owner_role_id)
                if owner_role:
                    await ticket_owner_user.remove_roles(owner_role, reason="ticket opened")
            except Exception:
                pass
        await self.bot.db.execute("DELETE FROM ticket_opened WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, ctx.channel.id)
        await message.edit(embed=Embed(color=colors.LOADING, description=f"{emojis.LOADING} {ctx.author.mention}: Ticket will be closed shortly..."))
        try:
            if ctx.channel:
                await ctx.channel.delete(reason="ticket closed")
        except Exception:
            pass

    @ticket.command(name="closerequest", aliases=["cr"], brief="ticket support / manage channels", description="Request to close the current ticket")
    @manage_ticket()
    @get_ticket()
    @cooldown(1, 300, BucketType.channel)
    async def ticket_closerequest(self, ctx: EvelinaContext):
        """Request to close the current ticket"""
        ticket_owner = await self.bot.db.fetchval("SELECT user_id FROM ticket_opened WHERE channel_id = $1", ctx.channel.id)
        ticket_owner_user = ctx.guild.get_member(ticket_owner)
        if ticket_owner_user:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {ticket_owner_user.mention}, {ctx.author.mention} has requested to close this ticket.\n> Click on the Button to confirm.")
            view = DeleteTicketRequestView(self.bot)
            await ctx.send(content=ticket_owner_user.mention, embed=embed, view=view)
            return await ctx.message.delete()
        await ctx.send_warning("Ticket owner left the server")

    @command(name="trn", brief="ticket support / manage channels", usage="trn nitro", description="Close the current ticket")
    @manage_ticket()
    @get_ticket()
    @bot_has_guild_permissions(manage_channels=True)
    async def trn(self, ctx: EvelinaContext, *, name: str):
        """Rename a ticket channel"""
        await self.ticket_rename(ctx, name=name)

    @ticket.command(name="rename", brief="ticket support / manage channels", usage="ticket rename nitro", description="Rename a ticket channel")
    @manage_ticket()
    @get_ticket()
    @bot_has_guild_permissions(manage_channels=True)
    async def ticket_rename(self, ctx: EvelinaContext, *, name: str):
        """Rename a ticket channel"""
        check = await self.bot.db.fetchval("SELECT user_id FROM ticket_opened WHERE channel_id = $1", ctx.channel.id)
        user = self.bot.get_user(check)
        if user is None:
            return await ctx.send_warning("User left the server")
        await ctx.channel.edit(name=f"{name}-{user.name}", reason=f"Ticket channel renamed by {ctx.author}")
        await ctx.send_success(f"Renamed ticket channel to **{name}-{user.name}**")

    @ticket.command(name="info", brief="manage guild", usage="ticket info comminate", description="View all tickets from a given user")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_info(self, ctx: EvelinaContext, user: User):
        """View all tickets from a given user"""
        results = await self.bot.db.fetch("SELECT * FROM ticket_transcripts WHERE guild_id = $1 AND user_id = $2 ORDER BY timestamp DESC", ctx.guild.id, user.id)
        if not results:
            return await ctx.send_warning(f"There are no transcripts saved for {user.mention}")
        embeds = []
        for result in results:
            embed = Embed(color=colors.NEUTRAL)
            embed.description = f"**Topic:** {result['topic']}\n**Ticket Owner:** {user.mention} (`{user.id}`)"
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.add_field(name="Transcript", value=f"[`{result['id']}`](https://{self.bot.transcript}/{result['id']})", inline=False)
            embed.add_field(name="Closed", value=f"<t:{result['timestamp']}:R>", inline=False)
            embed.set_footer(text=f"Page: {results.index(result)+1}/{len(results)} ({len(results)} entries)")
            embeds.append(embed)
        return await ctx.paginator(embeds)

    @ticket.group(name="role", brief="manage guild", description="Manage the ticket roles", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_role(self, ctx: EvelinaContext):
        """Manage the ticket roles"""
        return await ctx.create_pages()

    @ticket_role.command(name="set", brief="manage guild", usage="ticket role set Ticket Owner", description="Set a role as ticket owner role")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_role_set(self, ctx: EvelinaContext, role: NewRoleConverter):
        """Manage the ticket owner roles"""
        check = await self.bot.db.fetchval("SELECT owner_role FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if check == role.id:
            return await ctx.send_warning(f"{role.mention} is already the ticket owner role")
        await self.bot.db.execute("UPDATE ticket SET owner_role = $1 WHERE guild_id = $2", role.id, ctx.guild.id)
        return await ctx.send_success(f"Updated the ticket owner role to {role.mention}")
    
    @ticket_role.command(name="remove", brief="manage guild", description="Remove the ticket owner role")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_role_remove(self, ctx: EvelinaContext):
        """Remove the ticket owner role"""
        check = await self.bot.db.fetchval("SELECT owner_role FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if check is None:
            return await ctx.send_warning("No ticket owner role is set")
        await self.bot.db.execute("UPDATE ticket SET owner_role = $1 WHERE guild_id = $2", None, ctx.guild.id)
        return await ctx.send_success("Removed the ticket owner role")

    @ticket.group(name="support", brief="manage guild", invoke_without_command=True, description="Manage the support roles for the ticket system", case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def ticket_support(self, ctx: EvelinaContext):
        """Manage the support roles for the ticket system"""
        return await ctx.create_pages()

    @ticket_support.command(name="add", brief="manage guild", usage="ticket support add staff [topic]", description="Add a support role to the ticket system")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_support_add(self, ctx: EvelinaContext, topic: str, *, role: Role):
        """Add a support role to the ticket system, optionally for a specific topic"""
        role_id = str(role.id)
        if topic == "default":
            support_roles = await self.bot.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", ctx.guild.id)
            if support_roles is None:
                support_roles = []
            else:
                try:
                    support_roles = json.loads(support_roles)
                    if not isinstance(support_roles, list):
                        return await ctx.send_warning("Unexpected data format for **default** roles.")
                except json.JSONDecodeError:
                    return await ctx.send_warning("Invalid JSON format for **default** roles.")
            if role_id not in support_roles:
                support_roles.append(role_id)
                await self.bot.db.execute("UPDATE ticket SET support_roles = $1 WHERE guild_id = $2", json.dumps(support_roles), ctx.guild.id)
                return await ctx.send_success(f"Added {role.mention} as a **default** supporter role for the ticket system")
            else:
                return await ctx.send_warning(f"{role.mention} is already a **default** supporter role for the ticket system")
        else:
            topic_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, topic)
            if not topic_exists:
                return await ctx.send_warning(f"Topic `{topic}` does not exist")
            topic_support_roles = await self.bot.db.fetchval("SELECT support_roles FROM ticket_topics WHERE guild_id = $1 AND name = $2", ctx.guild.id, topic)
            if topic_support_roles is None:
                topic_support_roles = []
            else:
                try:
                    topic_support_roles = json.loads(topic_support_roles)
                    if not isinstance(topic_support_roles, list):
                        return await ctx.send_warning("Unexpected data format for topic support roles.")
                except json.JSONDecodeError:
                    return await ctx.send_warning("Invalid JSON format for topic support roles.")
            if role_id not in topic_support_roles:
                topic_support_roles.append(role_id)
                await self.bot.db.execute("UPDATE ticket_topics SET support_roles = $1 WHERE guild_id = $2 AND name = $3", json.dumps(topic_support_roles), ctx.guild.id, topic)
                return await ctx.send_success(f"Added {role.mention} as a support role for the topic `{topic}`")
            else:
                return await ctx.send_warning(f"{role.mention} is already a support role for the topic `{topic}`")

    @ticket_support.command(name="remove", brief="manage guild", usage="ticket support remove staff [topic]", description="Remove a support role from the ticket system")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_support_remove(self, ctx: EvelinaContext, topic: str, *, role: Role):
        """Remove a support role from the ticket system, optionally for a specific topic"""
        role_id = str(role.id)
        if topic == "default":
            support_roles = await self.bot.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", ctx.guild.id)
            if support_roles is None:
                return await ctx.send_warning("No **default** support roles are set for the ticket system")
            try:
                support_roles = json.loads(support_roles)
                if not isinstance(support_roles, list):
                    return await ctx.send_warning("Unexpected data format for **default** support roles.")
            except json.JSONDecodeError:
                return await ctx.send_warning("Invalid JSON format for **default** support roles.")
            if role_id in support_roles:
                support_roles.remove(role_id)
                await self.bot.db.execute("UPDATE ticket SET support_roles = $1 WHERE guild_id = $2", json.dumps(support_roles), ctx.guild.id)
                return await ctx.send_success(f"Removed {role.mention} from the **default** support roles")
            else:
                return await ctx.send_warning(f"{role.mention} is not a **default** support role for the ticket system")
        else:
            topic_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, topic)
            if not topic_exists:
                return await ctx.send_warning(f"Topic `{topic}` does not exist")
            topic_support_roles = await self.bot.db.fetchval("SELECT support_roles FROM ticket_topics WHERE guild_id = $1 AND name = $2", ctx.guild.id, topic)
            if topic_support_roles is None:
                return await ctx.send_warning("No support roles are set for the topic `{topic}`")
            try:
                topic_support_roles = json.loads(topic_support_roles)
                if not isinstance(topic_support_roles, list):
                    return await ctx.send_warning("Unexpected data format for topic support roles.")
            except json.JSONDecodeError:
                return await ctx.send_warning("Invalid JSON format for topic support roles.")
            if role_id in topic_support_roles:
                topic_support_roles.remove(role_id)
                await self.bot.db.execute("UPDATE ticket_topics SET support_roles = $1 WHERE guild_id = $2 AND name = $3", json.dumps(topic_support_roles), ctx.guild.id, topic)
                return await ctx.send_success(f"Removed {role.mention} from the support roles for the topic `{topic}`")
            else:
                return await ctx.send_warning(f"{role.mention} is not a support role for the topic `{topic}`")
            
    @ticket_support.command(name="list", brief="manage guild", description="List all support roles for the ticket system")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_support_list(self, ctx: EvelinaContext):
        """List all support roles for the ticket system"""
        global_support_roles = await self.bot.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if global_support_roles:
            try:
                global_support_roles = json.loads(global_support_roles)
                if isinstance(global_support_roles, list) and global_support_roles:
                    global_support_list = ', '.join([f"<@&{role_id}>" for role_id in global_support_roles])
                else:
                    global_support_list = "N/A"
            except (json.JSONDecodeError, TypeError):
                return await ctx.send_warning("Invalid or corrupted format for global support roles.")
        else:
            global_support_list = "N/A"
        topic_results = await self.bot.db.fetch("SELECT * FROM ticket_topics WHERE guild_id = $1", ctx.guild.id)
        topic_support_lists = []
        for result in topic_results:
            topic_support_roles = result.get('support_roles')
            if topic_support_roles:
                try:
                    topic_support_roles = json.loads(topic_support_roles)
                    if isinstance(topic_support_roles, list) and topic_support_roles:
                        topic_support_list = ', '.join([f"<@&{role_id}>" for role_id in topic_support_roles])
                    else:
                        topic_support_list = "N/A"
                except (json.JSONDecodeError, TypeError):
                    topic_support_list = "N/A"
            else:
                topic_support_list = "N/A"
            topic_support_lists.append((result['name'], topic_support_list))
        embed = Embed(color=colors.NEUTRAL, title="Support Roles")
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.add_field(name="Default", value=global_support_list)
        for topic_name, roles_list in topic_support_lists:
            embed.add_field(name=f"{topic_name}", value=roles_list)
        await ctx.reply(embed=embed)

    @ticket.group(name="settings", brief="manage guild", description="Configure the ticket system", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_settings(self, ctx: EvelinaContext):
        """Configure the ticket system"""
        return await ctx.create_pages()
    
    @ticket_settings.command(name="reset", aliases=["disable"], brief="manage guild", description="Disable the ticket module in the server")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_settings_reset(self, ctx: EvelinaContext):
        """Disable the ticket module in the server"""
        for i in ["ticket", "ticket_blacklist", "ticket_modals", "ticket_opened", "ticket_statuses", "ticket_topics"]:
            await self.bot.db.execute(f"DELETE FROM {i} WHERE guild_id = $1", ctx.guild.id)
        await ctx.send_success("Reseted all ticket settings in this server")

    @ticket_settings.command(name="category", brief="manage guild", usage="ticket settings category default #tickets", description="Configure the category where the tickets should open")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_settings_category(self, ctx: EvelinaContext, topic: str, *, category: CategoryChannel = None):
        """Configure the category where the tickets should open"""
        if topic == "default":
            await self.bot.db.execute("UPDATE ticket SET category_id = $1 WHERE guild_id = $2", category.id if category else None, ctx.guild.id)
            if category:
                return await ctx.send_success(f"Updated ticket category to {category.mention}")
            else:
                return await ctx.send_success("Removed the default category channel")
        else:
            topic_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, topic)
            if not topic_exists:
                return await ctx.send_warning(f"Topic `{topic}` does not exist")
            await self.bot.db.execute("UPDATE ticket_topics SET category_id = $1 WHERE guild_id = $2 AND name = $3", category.id if category else None, ctx.guild.id, topic)
            if category:
                return await ctx.send_success(f"Updated category for topic `{topic}` to {category.mention}")
            else:
                return await ctx.send_success(f"Removed the category for topic `{topic}`")

    @ticket_settings.command(name="logs", brief="manage guild", usage="ticket settings logs #transcripts", description="Configure a channel for logging ticket transcripts")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_settings_logs(self, ctx: EvelinaContext, *, channel: TextChannel = None):
        """Configure a channel for logging ticket transcripts"""
        if channel:
            await self.bot.db.execute("UPDATE ticket SET logs = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
            return await ctx.send_success(f"Updated logs channel to {channel.mention}")
        else:
            await self.bot.db.execute("UPDATE ticket SET logs = $1 WHERE guild_id = $2", None, ctx.guild.id)
            return await ctx.send_success("Removed the logs channel")
        
    @ticket_settings.command(name="closed", brief="manage guild", usage="ticket settings closed #transcripts", description="Configure a category for closed tickets")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_settings_closed(self, ctx: EvelinaContext, *, category: CategoryChannel = None):
        """Configure a category for closed tickets"""
        if category:
            await self.bot.db.execute("UPDATE ticket SET closed = $1 WHERE guild_id = $2", category.id, ctx.guild.id)
            return await ctx.send_success(f"Updated closed category to {category.mention}")
        else:
            await self.bot.db.execute("UPDATE ticket SET closed = $1 WHERE guild_id = $2", None, ctx.guild.id)
            return await ctx.send_success("Removed the closed category")
        
    @ticket_settings.command(name="embed", brief="manage guild", usage="ticket settings embed default {user.mention}, support will be with you shortly", description="Set a message to be sent when a member opens a ticket")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_settings_embed(self, ctx: EvelinaContext, topic: str, *, code: str = None):
        """Set a message to be sent when a member opens a ticket"""
        if topic == "default":
            await self.bot.db.execute("UPDATE ticket SET open_embed = $1 WHERE guild_id = $2", code, ctx.guild.id)
            if code:
                return await ctx.send_success(f"Updated the default ticket opening message to\n```{code}```")
            else:
                return await ctx.send_success("Removed the default ticket opening message")
        topic_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, topic)
        if not topic_exists:
            return await ctx.send_warning(f"Topic `{topic}` does not exist")
        await self.bot.db.execute("UPDATE ticket_topics SET embed = $1 WHERE guild_id = $2 AND name = $3", code, ctx.guild.id, topic)
        if code:
            return await ctx.send_success(f"Updated the ticket opening message for topic `{topic}` to\n```{code}```")
        else:
            return await ctx.send_success(f"Removed the custom ticket opening message for topic `{topic}`")
        
    @ticket_settings.command(name="counting", brief="manage guild", usage="ticket settings counting on", description="Enable or disable the ticket counting system")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_settings_counting(self, ctx: EvelinaContext, option: str):
        """Enable or disable the ticket counting system"""
        if option.lower() == "on":
            await self.bot.db.execute("UPDATE ticket SET counter_status = $1 WHERE guild_id = $2", True, ctx.guild.id)
            return await ctx.send_success("Enabled the ticket counting system")
        elif option.lower() == "off":
            await self.bot.db.execute("UPDATE ticket SET counter_status = $1 WHERE guild_id = $2", False, ctx.guild.id)
            return await ctx.send_success("Disabled the ticket counting system")
        else:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")
        
    @ticket.group(name="status", brief="manage guild", invoke_without_command=True, description="Configure the ticket status", case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_status(self, ctx: EvelinaContext, name: str = None):
        """Configure the ticket status"""
        return await ctx.create_pages()
    
    @ticket_status.command(name="add", brief="manage guild", usage="ticket status add paid #paid", description="Add a ticket status")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_status_add(self, ctx: EvelinaContext, name: str, *, category: CategoryChannel):
        """Add a ticket status"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_statuses WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if check:
            return await ctx.send_warning(f"Status `{name}` already exists")
        await self.bot.db.execute("INSERT INTO ticket_statuses (guild_id, name, category_id) VALUES ($1, $2, $3)", ctx.guild.id, name, category.id)
        return await ctx.send_success(f"Added **{name}** status with category {category.mention}")
    
    @ticket_status.command(name="remove", brief="manage guild", usage="ticket status remove paid", description="Remove a ticket status")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_status_remove(self, ctx: EvelinaContext, name: str):
        """Remove a ticket status"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_statuses WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"Status `{name}` does not exist")
        await self.bot.db.execute("DELETE FROM ticket_statuses WHERE guild_id = $1 AND name = $2", ctx.guild.id, name)
        return await ctx.send_success(f"Removed **{name}** status")
    
    @ticket_status.command(name="category", brief="manage guild", usage="ticket status category paid #paid", description="Change the category for a ticket status")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_status_category(self, ctx: EvelinaContext, name: str, *, category: CategoryChannel):
        """Change the category for a ticket status"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_statuses WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"Status `{name}` does not exist")
        await self.bot.db.execute("UPDATE ticket_statuses SET category_id = $1 WHERE guild_id = $2 AND name = $3", category.id, ctx.guild.id, name)
        return await ctx.send_success(f"Updated **{name}** status category to {category.mention}")
    
    @ticket_status.command(name="list", brief="manage guild", description="List all ticket statuses")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_status_list(self, ctx: EvelinaContext):
        """List all ticket statuses with pagination."""
        results = await self.bot.db.fetch("SELECT * FROM ticket_statuses WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("No ticket statuses found")
        content = []
        for result in results:
            category = ctx.guild.get_channel(result['category_id'])
            content.append(f"**{result['name']}** - {category.mention if category else 'N/A'}")
        await ctx.paginate(content, "Ticket Statuses", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command(name="tm", brief="ticket support / manage channels", usage="tm #tickets", description="Move the ticket to another category")
    @manage_ticket()
    @get_ticket()
    async def tm(self, ctx: EvelinaContext, name: str):
        """Move the ticket to another category"""
        await self.ticket_move(ctx, name=name)
    
    @ticket.command(name="move", brief="ticket support / manage channels", usage="ticket move #tickets", description="Move the ticket to another category")
    @manage_ticket()
    @get_ticket()
    @bot_has_guild_permissions(manage_channels=True)
    async def ticket_move(self, ctx: EvelinaContext, name: str):
        """Move the ticket to another category"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_statuses WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"Status `{name}` does not exist")
        category_id = await self.bot.db.fetchval("SELECT category_id FROM ticket_statuses WHERE guild_id = $1 AND name = $2", ctx.guild.id, name)
        category = ctx.guild.get_channel(category_id)
        if not category:
            return await ctx.send_warning(f"Category for status `{name}` does not exist")
        await ctx.channel.edit(category=category, reason=f"Ticket moved to {category.name}")
        check = await self.bot.db.fetchval("SELECT user_id FROM ticket_opened WHERE channel_id = $1", ctx.channel.id)
        return await ctx.send_success(f"Moved ticket to {category.mention}")
    
    @ticket.command(name="limit", brief="manage guild", usage="ticket limit 5", description="Set the maximum amount of tickets a user can have open")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_limit(self, ctx: EvelinaContext, limit: int):
        """Set the maximum amount of tickets a user can have open"""
        if limit < 1:
            return await ctx.send_warning("Ticket limit must between **1** and **10**")
        if limit > 10:
            return await ctx.send_warning("Ticket limit must between **1** and **10**")
        await self.bot.db.execute('UPDATE ticket SET "limit" = $1 WHERE guild_id = $2', limit, ctx.guild.id)
        return await ctx.send_success(f"Updated ticket limit to **{limit}**")

    @ticket.command(name="topics", brief="administrator", description="Manage the ticket topics")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_topics(self, ctx: EvelinaContext):
        """Manage the ticket topics"""
        results = await self.bot.db.fetch("SELECT * FROM ticket_topics WHERE guild_id = $1", ctx.guild.id)
        embed = Embed(color=colors.NEUTRAL, description=f"🔍 Choose a setting")
        button1 = Button(label="add topic", style=ButtonStyle.gray)
        button2 = Button(label="remove topic", style=ButtonStyle.red, disabled=len(results) == 0)
        async def interaction_check(interaction: Interaction):
            if interaction.user != ctx.author:
                await interaction.warn("You are **not** the author of this message", ephemeral=True)
            return interaction.user == ctx.author
        async def button1_callback(interaction: Interaction):
            return await interaction.response.send_modal(TicketTopic())
        async def button2_callback(interaction: Interaction):
            e = Embed(color=colors.NEUTRAL, description=f"🔍 Select a topic to delete")
            options = [SelectOption(label=result[1], description=result[2] if len(result[2]) < 100 else None) for result in results]
            select = Select(options=options, placeholder="select a topic...")
            async def select_callback(inter: Interaction):
                await self.bot.db.execute("DELETE FROM ticket_topics WHERE guild_id = $1 AND name = $2", inter.guild.id, select.values[0])
                await inter.response.send_message(f"Removed **{select.values[0]}** topic", ephemeral=True)
            select.callback = select_callback
            v = View()
            v.add_item(select)
            v.interaction_check = interaction_check
            return await interaction.response.edit_message(embed=e, view=v)
        button1.callback = button1_callback
        button2.callback = button2_callback
        view = View()
        limit = await self.bot.db.fetchval("SELECT COUNT(*) FROM ticket_topics WHERE guild_id = $1", ctx.guild.id)
        if limit >= 25:
            view.add_item(button2)
        else:
            view.add_item(button1)
            view.add_item(button2)
        view.interaction_check = interaction_check
        return await ctx.reply(embed=embed, view=view)
        
    @ticket.group(name="modal", brief="administrator", description="Modify modal for ticket topics", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def ticket_modal(self, ctx: EvelinaContext):
        """Modify modal for ticket topics"""
        return await ctx.create_pages()

    @ticket_modal.command(name="add", brief="administrator", usage="ticket modal add Support Question What is your Question?", description="Add modal to a ticket topic")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_modal_add(self, ctx: EvelinaContext, topic: str, name: str, *, description: str):
        """Add modal to a ticket topic"""
        if len(name) > 50:
            return await ctx.send_warning("Modal name must be less than 50 characters")
        if len(description) > 200:
            return await ctx.send_warning("Modal description must be less than 200 characters")
        if topic.lower() != "default":
            topic_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, topic)
            if not topic_exists:
                return await ctx.send_warning(f"Topic `{topic}` does not exist")
        modal_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_modals WHERE guild_id = $1 AND topic = $2 AND name = $3)", ctx.guild.id, topic, name)
        if modal_exists:
            return await ctx.send_warning(f"Modal `{name}` already exists for topic `{topic}`")
        modal_count = await self.bot.db.fetchval("SELECT COUNT(*) FROM ticket_modals WHERE guild_id = $1 AND topic = $2", ctx.guild.id, topic)
        if modal_count >= 3:
            return await ctx.send_warning(f"Cannot add more than 3 modals to topic `{topic}`")
        source = string.ascii_letters + string.digits
        code = "".join(random.choice(source) for _ in range(8))
        await self.bot.db.execute("INSERT INTO ticket_modals (guild_id, topic, name, description, code) VALUES ($1, $2, $3, $4, $5)", ctx.guild.id, topic, name, description, code)
        return await ctx.send_success(f"Added **{name}** modal to **{topic}** topic as **{code}**")

    @ticket_modal.command(name="remove", brief="administrator", usage="ticket modal remove Support Question", description="Remove modal from a ticket topic")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_modal_remove(self, ctx: EvelinaContext, topic: str, name: str):
        """Remove modal from a ticket topic"""
        if topic.lower() != "default":
            topic_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, topic)
            if not topic_exists:
                return await ctx.send_warning(f"Topic `{topic}` does not exist")
        modal_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_modals WHERE guild_id = $1 AND topic = $2 AND name = $3)", ctx.guild.id, topic, name)
        if not modal_exists:
            return await ctx.send_warning(f"Modal `{name}` does not exist")
        await self.bot.db.execute("DELETE FROM ticket_modals WHERE guild_id = $1 AND topic = $2 AND name = $3", ctx.guild.id, topic, name)
        return await ctx.send_success(f"Removed **{name}** modal from **{topic}** topic")
    
    @ticket_modal.command(name="name", brief="administrator", usage="ticket modal name Support Question Product", description="Edit modal name for a ticket topic")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_modal_name(self, ctx: EvelinaContext, topic: str, old: str, new: str):
        """Edit modal name for a ticket topic"""
        if len(new) > 50:
            return await ctx.send_warning("Modal name must be less than 50 characters")
        if topic.lower() != "default":
            topic_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, topic)
            if not topic_exists:
                return await ctx.send_warning(f"Topic `{topic}` does not exist")
        modal_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_modals WHERE guild_id = $1 AND topic = $2 AND name = $3)", ctx.guild.id, topic, old)
        if not modal_exists:
            return await ctx.send_warning(f"Modal `{old}` does not exist")
        await self.bot.db.execute("UPDATE ticket_modals SET name = $1 WHERE guild_id = $2 AND topic = $3 AND name = $4", new, ctx.guild.id, topic, old)
        return await ctx.send_success(f"Updated **{old}** modal name to **{new}** for **{topic}** topic")

    @ticket_modal.command(name="description", brief="administrator", usage="ticket modal description Support Question What is your Question?", description="Edit modal description for a ticket topic")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_modal_description(self, ctx: EvelinaContext, topic: str, name: str, *, description: str):
        """Edit modal description for a ticket topic"""
        if len(description) > 200:
            return await ctx.send_warning("Modal description must be less than 200 characters")
        if topic.lower() != "default":
            topic_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, topic)
            if not topic_exists:
                return await ctx.send_warning(f"Topic `{topic}` does not exist")
        modal_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_modals WHERE guild_id = $1 AND topic = $2 AND name = $3)", ctx.guild.id, topic, name)
        if not modal_exists:
            return await ctx.send_warning(f"Modal `{name}` does not exist")
        await self.bot.db.execute("UPDATE ticket_modals SET description = $1 WHERE guild_id = $2 AND topic = $3 AND name = $4", description, ctx.guild.id, topic, name)
        return await ctx.send_success(f"Updated **{name}** modal description to\n```{description}``` for **{topic}** topic")
    
    @ticket_modal.command(name="toggle", brief="administrator", usage="ticket modal toggle Support Question", description="Toggle a modal for a ticket topic")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_modal_toggle(self, ctx: EvelinaContext, topic: str, name: str):
        """Toggle a modal for a ticket topic"""
        if topic.lower() != "default":
            topic_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, topic)
            if not topic_exists:
                return await ctx.send_warning(f"Topic `{topic}` does not exist")
        modal_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_modals WHERE guild_id = $1 AND topic = $2 AND name = $3)", ctx.guild.id, topic, name)
        if not modal_exists:
            return await ctx.send_warning(f"Modal `{name}` does not exist")
        required = await self.bot.db.fetchval("SELECT required FROM ticket_modals WHERE guild_id = $1 AND topic = $2 AND name = $3", ctx.guild.id, topic, name)
        await self.bot.db.execute("UPDATE ticket_modals SET required = $1 WHERE guild_id = $2 AND topic = $3 AND name = $4", not required, ctx.guild.id, topic, name)
        return await ctx.send_success(f"Modal **{name}** is now **{'required' if not required else 'optional'}** for **{topic}** topic")
    
    @ticket_modal.command(name="style", brief="administrator", usage="ticket modal style Support Question long", description="Change the style of a modal for a ticket topic")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_modal_style(self, ctx: EvelinaContext, topic: str, name: str, style: str):
        """Change the style of a modal for a ticket topic"""
        if topic.lower() != "default":
            topic_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, topic)
            if not topic_exists:
                return await ctx.send_warning(f"Topic `{topic}` does not exist")
        modal_exists = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_modals WHERE guild_id = $1 AND topic = $2 AND name = $3)", ctx.guild.id, topic, name)
        if not modal_exists:
            return await ctx.send_warning(f"Modal `{name}` does not exist")
        if style.lower() not in ["short", "long"]:
            return await ctx.send_warning("Invalid style. Valid styles are: `short` & `long`")
        await self.bot.db.execute("UPDATE ticket_modals SET style = $1 WHERE guild_id = $2 AND topic = $3 AND name = $4", True if style.lower() == 'long' else False, ctx.guild.id, topic, name)
        return await ctx.send_success(f"Updated **{name}** modal style to **{style}** for **{topic}** topic")
    
    @ticket_modal.command(name="list", brief="administrator", usage="ticket modal list", description="List all modals for all ticket topics")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_modal_list(self, ctx: EvelinaContext):
        """List all modals for all ticket topics"""
        topics = await self.bot.db.fetch("SELECT DISTINCT name FROM ticket_topics WHERE guild_id = $1", ctx.guild.id)
        topics.append({"name": "default"})
        if not topics:
            return await ctx.send_warning("No ticket topics found for this server")
        results = await self.bot.db.fetch("SELECT * FROM ticket_modals WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("No modals found for this server")
        topic_modals = {}
        for result in results:
            topic = result['topic']
            if topic not in topic_modals:
                topic_modals[topic] = []
            topic_modals[topic].append(result)
        embeds = []
        for topic, modals in topic_modals.items():
            embed = Embed(color=colors.NEUTRAL, title=f"Modals for {topic}")
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            for modal in modals:
                embed.add_field(name=f"{modal['name']} ({modal['code']})", value=f"```{modal['description']}```", inline=False)
            embeds.append(embed)
        for i, embed in enumerate(embeds):
            embed.set_footer(text=f"Page: {i + 1}/{len(embeds)} ({len(embeds)} entries)")
        if embeds:
            await ctx.paginator(embeds)
        else:
            await ctx.send_warning("No modals found for any topics in this server")

    @ticket.group(name="topic", brief="administrator", invoke_without_command=True, description="Manage the ticket topics", case_insensitive=True)
    @has_guild_permissions(administrator=True)
    async def ticket_topic(self, ctx: EvelinaContext):
        """Manage the ticket topics"""
        return await ctx.create_pages()
    
    @ticket_topic.command(name="add", brief="administrator", usage="ticket topic add Support", description="Create a ticket topic")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_topic_add(self, ctx: EvelinaContext, name: str):
        """Create a ticket topic"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if check:
            return await ctx.send_warning(f"Topic `{name}` already exists")
        limit = await self.bot.db.fetchval("SELECT COUNT(*) FROM ticket_topics WHERE guild_id = $1", ctx.guild.id)
        if limit >= 25:
            return await ctx.send_warning("Cannot add more than 25 topics")
        await self.bot.db.execute("INSERT INTO ticket_topics (guild_id, name) VALUES ($1, $2)", ctx.guild.id, name)
        return await ctx.send_success(f"Added **{name}** topic")
    
    @ticket_topic.command(name="remove", brief="administrator", usage="ticket topic remove Support", description="Delete a ticket topic")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_topic_remove(self, ctx: EvelinaContext, name: str):
        """Delete a ticket topic"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"Topic `{name}` does not exist")
        await self.bot.db.execute("DELETE FROM ticket_topics WHERE guild_id = $1 AND name = $2", ctx.guild.id, name)
        return await ctx.send_success(f"Removed **{name}** topic")
    
    @ticket_topic.command(name="name", brief="administrator", usage="ticket topic name Support General", description="Edit a ticket topic name")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_topic_name(self, ctx: EvelinaContext, old: str, new: str):
        """Edit a ticket topic name"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, old)
        if not check:
            return await ctx.send_warning(f"Topic `{old}` does not exist")
        await self.bot.db.execute("UPDATE ticket_topics SET name = $1 WHERE guild_id = $2 AND name = $3", new, ctx.guild.id, old)
        return await ctx.send_success(f"Updated **{old}** topic name to **{new}**")
    
    @ticket_topic.command(name="description", brief="administrator", usage="ticket topic description Support Support related questions", description="Edit a ticket topic description")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_topic_description(self, ctx: EvelinaContext, name: str, *, description: str = None):
        """Edit a ticket topic description"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"Topic `{name}` does not exist")
        await self.bot.db.execute("UPDATE ticket_topics SET description = $1 WHERE guild_id = $2 AND name = $3", description, ctx.guild.id, name)
        if description is None:
            return await ctx.send_success(f"Removed **{name}** topic description")
        else:
            return await ctx.send_success(f"Updated **{name}** topic description to\n```{description}```")
    
    @ticket_topic.command(name="emoji", brief="administrator", usage="ticket topic emoji Support 🛠️", description="Edit a ticket topic emoji")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_topic_emoji(self, ctx: EvelinaContext, name: str, emoji: str):
        """Edit a ticket topic emoji"""
        if isinstance(emoji, str):
            emoji = emoji.strip(":")
            custom_emoji = None
            if emoji.startswith('<:') and emoji.endswith('>'):
                custom_emoji = get(ctx.guild.emojis, name=emoji.split(':')[1])
            else:
                custom_emoji = get(ctx.guild.emojis, name=emoji.strip(':'))
            if custom_emoji:
                emoji = custom_emoji
            else:
                try:
                    unicode_emoji = PartialEmoji.from_str(emoji)
                    if unicode_emoji.is_unicode_emoji():
                        emoji = unicode_emoji
                    else:
                        return await ctx.send_warning(f"Emoji `{emoji}` is not **available** on this server or it's not a valid emoji")
                except Exception:
                    return await ctx.send_warning(f"An error occurred while trying to set the emoji")
        emoji_str = str(emoji) if isinstance(emoji, Emoji) else emoji.name
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"Topic `{name}` does not exist")
        await self.bot.db.execute("UPDATE ticket_topics SET emoji = $1 WHERE guild_id = $2 AND name = $3", emoji_str, ctx.guild.id, name)
        return await ctx.send_success(f"Updated **{name}** topic emoji to **{emoji_str}**")

    @ticket_topic.command(name="channelname", aliases=["cn", "cname"], brief="administrator", usage="ticket topic channelname Support 💰-{user.name}", description="Edit a ticket topic channel name")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_topic_channelname(self, ctx: EvelinaContext, name: str, *, channelname: str = None):
        """Edit a ticket topic channel name"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"Topic `{name}` does not exist")
        if channelname is None:
            await self.bot.db.execute("UPDATE ticket_topics SET channel_name = $1 WHERE guild_id = $2 AND name = $3", None, ctx.guild.id, name)
            return await ctx.send_success(f"Removed **{name}** topic channel name")
        else:
            await self.bot.db.execute("UPDATE ticket_topics SET channel_name = $1 WHERE guild_id = $2 AND name = $3", channelname, ctx.guild.id, name)
            return await ctx.send_success(f"Updated **{name}** topic channel name to **{channelname}**")
    
    @ticket_topic.command(name="channeltopic", aliases=["ct", "ctopic"], brief="administrator", usage="ticket topic channeltopic Support 💰-{user.name}", description="Edit a ticket topic channel topic")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_topic_channeltopic(self, ctx: EvelinaContext, name: str, *, channeltopic: str = None):
        """Edit a ticket topic channel topic"""
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"Topic `{name}` does not exist")
        if channeltopic is None:
            await self.bot.db.execute("UPDATE ticket_topics SET channel_topic = $1 WHERE guild_id = $2 AND name = $3", None, ctx.guild.id, name)
            return await ctx.send_success(f"Removed **{name}** topic channel topic")
        else:
            await self.bot.db.execute("UPDATE ticket_topics SET channel_topic = $1 WHERE guild_id = $2 AND name = $3", channeltopic, ctx.guild.id, name)
            return await ctx.send_success(f"Updated **{name}** topic channel topic to **{channeltopic}**")
        
    @ticket_topic.command(name="weight", brief="administrator", usage="ticket topic weight Support 5", description="Edit a ticket topic weight")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_topic_weight(self, ctx: EvelinaContext, name: str, weight: int):
        """Edit a ticket topic weight"""
        if weight < 1:
            return await ctx.send_warning("Topic weight must be greater than **0**")
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"Topic `{name}` does not exist")
        await self.bot.db.execute("UPDATE ticket_topics SET weight = $1 WHERE guild_id = $2 AND name = $3", weight, ctx.guild.id, name)
        return await ctx.send_success(f"Updated **{name}** topic weight to **{weight}**")
    
    @ticket_topic.command(name="status", brief="administrator", usage="ticket topic status Support on", description="Edit a ticket topic status")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_topic_status(self, ctx: EvelinaContext, name: str, option: str):
        """Edit a ticket topic status"""
        if option.lower() not in ["on", "off"]:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")
        check = await self.bot.db.fetchval("SELECT EXISTS (SELECT 1 FROM ticket_topics WHERE guild_id = $1 AND name = $2)", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"Topic `{name}` does not exist")
        await self.bot.db.execute("UPDATE ticket_topics SET status = $1 WHERE guild_id = $2 AND name = $3", True if option.lower() == 'on' else False, ctx.guild.id, name)
        return await ctx.send_success(f"Updated **{name}** topic status to **{'enabled' if option.lower() == 'on' else 'disabled'}**")

    @ticket.command(name="config", description="Check the server's ticket settings")
    @ticket_exists()
    async def ticket_config(self, ctx: EvelinaContext):
        """Check the server's ticket settings"""
        check = await self.bot.db.fetchrow("SELECT * FROM ticket WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Ticket module is **not** enabled in this server")
        
        if check["support_roles"]:
            support_roles = json.loads(check["support_roles"])
            support = ', '.join([f"<@&{role_id}>" for role_id in support_roles])
        else:
            support = "N/A"
        
        embed = Embed(color=colors.NEUTRAL, title="Ticket Configuration")
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.add_field(name="Logs", value=f"<#{check['logs']}>" if check["logs"] else "N/A")
        embed.add_field(name="Category", value=f"<#{check['category_id']}>" if check["category_id"] else "N/A")
        embed.add_field(name="Support", value=support)
        embed.add_field(name="Open Embed", value=f"```\n{check['open_embed']}```")
        await ctx.reply(embed=embed)
        
        results = await self.bot.db.fetch("SELECT * FROM ticket_topics WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return
        
        embeds = [
            Embed(color=colors.NEUTRAL)
            .set_footer(text=f"Page: {results.index(result)+1}/{len(results)}")
            .add_field(name=f"Name", value=f"{result['name']}", inline=True)
            .add_field(name=f"Emoji", value=f"{result['emoji'] if result['emoji'] else 'N/A'}", inline=True)
            .add_field(name=f"Category", value=f"{ctx.guild.get_channel(result['category_id']).mention if ctx.guild.get_channel(result['category_id']) else 'N/A'}", inline=True)
            .add_field(name=f"Open Embed", value=f"```{result['embed']}```", inline=False)
            for result in results
        ]
        await ctx.paginator(embeds)

    @ticket.command(name="send", brief="manage guild", usage="ticket send #ticket {embed}$v{description: Create a Ticket}", description="Send the ticket panel to a channel")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_send(self, ctx: EvelinaContext, channel: Union[TextChannel, Thread], *, code: str =
            "{embed}{color: #729bb0}$v{title: Create a ticket}$v"
            "{description: Please select your inquiry below.\n"
            "Do **not** create a ticket and suddenly go offline.\n"
            "> Refer to [nohello.net](https://nohello.net)}$v"
            "{thumbnail: {guild.icon}}"
        ):
        """Send the ticket panel to a channel"""
        x = await self.bot.embed_build.convert(ctx, code)
        view = TicketButtonView(self.bot)
        view.create_ticket()
        x["view"] = view
        try:
            await channel.send(**x)
            return await ctx.send_success(f"Sent the ticket panel to {channel.mention}")
        except Exception as e:
            return await ctx.send_warning(f"An error occurred while trying to send the ticket panel:\n ```{e}```")

    @ticket.command(name="blacklist", brief="Manage guild", usage="ticket blacklist comminate Spamming")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_blacklist(self, ctx: EvelinaContext, user: User, *, reason: str):
        """Blacklist a member from creating tickets"""
        if user.id in self.bot.owner_ids:
            return await ctx.send_warning("Don't blacklist a bot owner, are you sure?")
        try:
            await self.bot.db.execute("INSERT INTO ticket_blacklist (guild_id, user_id, reason) VALUES ($1, $2, $3)", ctx.guild.id, user.id, reason)
            await ctx.send_success(f"Blacklisted {user.mention} from creating tickets for reason: **{reason}**")
        except Exception:
            await ctx.send_warning(f"User {user.mention} is **already** blacklisted from creating tickets")
        
    @ticket.command(name="unblacklist", brief="Manage guild", usage="ticket unblacklist comminate")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_unblacklist(self, ctx: EvelinaContext, user: User):
        """Unblacklist a member from creating tickets"""
        if user.id in self.bot.owner_ids:
            return await ctx.send_warning("Don't unblacklist a bot owner, are you sure?")
        try:
            result = await self.bot.db.fetchval("SELECT COUNT(*) FROM ticket_blacklist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
            if result == 0:
                return await ctx.send_warning(f"{user.mention} isn't blacklisted from creating tickets")
            await self.bot.db.execute("DELETE FROM ticket_blacklist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
            await ctx.send_success(f"Unblacklisted {user.mention} from creating tickets")
        except Exception:
            await ctx.send_warning(f"User {user.mention} is **not** blacklisted from creating tickets")
        
    @ticket.command(name="blacklisted", brief="Manage guild")
    @has_guild_permissions(manage_guild=True)
    @ticket_exists()
    async def ticket_blacklisted(self, ctx: EvelinaContext):
        """List all blacklisted users from creating tickets"""
        results = await self.bot.db.fetch("SELECT user_id, reason FROM ticket_blacklist WHERE guild_id = $1", ctx.guild.id)
        to_show = [f"**{self.bot.get_user(check['user_id'])}** (`{check['user_id']}`)\n{emojis.REPLY} **Reason:** {check['reason']}" for check in results]
        if to_show:
            await ctx.paginate(to_show, f"Ticket Blacklisted", {"name": ctx.author, "icon_url": ctx.author.avatar.url})
        else:
            await ctx.send_warning("No ticket blacklisted user found")

    @ticket.group(name="admin", brief="administrator", description="Manage the members that can change the Antinuke settings", invoke_without_command=True, case_insensitive=True)
    async def ticket_admin(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @ticket_admin.command(name="add", brief="administrator", usage="ticket admin add comminate", description="Give a user permissions to view ticket transcripts")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_admin_add(self, ctx: EvelinaContext, *, member: User):
        if member.bot:
            return await ctx.send("Why would a bot be a ticket admin? They can't manage the settings anyways -_-")
        admins = await self.bot.db.fetchval("SELECT users FROM ticket_transcripts_access WHERE guild_id = $1", ctx.guild.id)
        if admins:
            admins = json.loads(admins)
            if member.id in admins:
                return await ctx.send_warning("This member is **already** a ticket admin")
            admins.append(member.id)
            await self.bot.db.execute("UPDATE ticket_transcripts_access SET users = $1 WHERE guild_id = $2", json.dumps(admins), ctx.guild.id)
        else:
            admins = [member.id]
            await self.bot.db.execute("INSERT INTO ticket_transcripts_access (guild_id, users) VALUES ($1, $2)", ctx.guild.id, json.dumps(admins))
        return await ctx.send_success(f"Added {member.mention} as a ticket admin")

    @ticket_admin.command(name="remove", brief="administrator", usage="ticket admin remove comminate", description="Remove a user's permissions to view ticket transcripts")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_admin_remove(self, ctx: EvelinaContext, *, member: User):
        admins = await self.bot.db.fetchval("SELECT users FROM ticket_transcripts_access WHERE guild_id = $1", ctx.guild.id)
        if admins:
            admins = json.loads(admins)
            if not member.id in admins:
                return await ctx.send_warning("This member isn't a ticket admin")
            admins.remove(member.id)
            if admins:
                await self.bot.db.execute("UPDATE ticket_transcripts_access SET users = $1 WHERE guild_id = $2", json.dumps(admins), ctx.guild.id)
            else:
                await self.bot.db.execute("DELETE FROM ticket_transcripts_access WHERE guild_id = $1", ctx.guild.id)
            return await ctx.send_success(f"Removed {member.mention} from the ticket admins")
        return await ctx.send_warning("There is **no** ticket admin")
    
    @ticket.command(name="admins", brief="administrator", description="View ticket admins on your server")
    @has_guild_permissions(administrator=True)
    @ticket_exists()
    async def ticket_admins(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT users FROM ticket_transcripts_access WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There is **no** ticket admin")
        content = []
        admins = json.loads(check["users"]) if check["users"] else []
        content.extend([f"<@!{wl}>" for wl in admins])
        await ctx.paginate(content, f"Ticket admins", {"name": ctx.guild.name, "icon_url": ctx.guild.icon if ctx.guild.icon else None})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Ticket(bot))