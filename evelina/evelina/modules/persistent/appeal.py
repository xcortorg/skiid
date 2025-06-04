import json
import asyncio
import asyncpg

from datetime import datetime

from discord import Embed, TextStyle, Interaction, ButtonStyle, Guild, User, TextChannel, Thread, NotFound
from discord.ui import View, Button, Modal, button, TextInput

from modules.styles import colors

class AppealsModal(Modal):
    def __init__(self, bot, view: "AppealsView"):
        super().__init__(title="Appeal Application")
        self.bot = bot
        self.view = view
        self.text = TextInput(label="Reason", style=TextStyle.long, required=True)
        self.add_item(self.text)

    async def on_submit(self, interaction: Interaction):
        reason = self.text.value
        record = await interaction.client.db.fetchrow("SELECT * FROM history WHERE appeal_id = $1",  interaction.message.id)
        if not record:
            return await interaction.warn("This appeal can't be found in the database", ephemeral=True)
        check = await interaction.client.db.fetchrow("SELECT * FROM appeals WHERE guild_id = $1",  record["server_id"])
        if not check:
            return await interaction.warn("Appeals are not enabled in this server", ephemeral=True)
        guild = interaction.client.get_guild(record["server_id"])
        if not guild:
            return await interaction.warn("This guild can't be found", ephemeral=True)
        channel = guild.get_channel(check["channel_id"])
        if not channel:
            return await interaction.warn("Appeals channel can't be found", ephemeral=True)
        if not channel.permissions_for(guild.me).send_messages:
            return await interaction.warn("I don't have permission to send messages in the appeals channel", ephemeral=True)
        embed = Embed(title="Appeal Application", color=colors.NEUTRAL)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.add_field(name="User", value=interaction.user.mention, inline=True)
        embed.add_field(name="Moderator", value=f"<@{record['moderator_id']}>", inline=True)
        embed.add_field(name="Case ID", value=f"{record['guild_id']}", inline=True)
        embed.add_field(name="Punishment", value=f"{record['punishment']}", inline=True)
        embed.add_field(name="Reason", value=f"{record['reason']}", inline=True)
        embed.add_field(name="Time", value=f"<t:{record['time']}:R>", inline=True)
        embed.add_field(name="Appeal Message", value=f"```{reason}```", inline=False)
        msg = await channel.send(embed=embed, view=AppealsModerationView(self))
        await interaction.client.db.execute("UPDATE history SET appeal_msg = $1, appeal_msg_id = $2 WHERE appeal_id = $3", reason, msg.id, interaction.message.id)
        for button in self.view.children:
            button.disabled = True
        await interaction.response.edit_message(view=self.view)
        return await interaction.approve("Your appeal has been submitted")

class AppealsModerationModal(Modal):
    def __init__(self, action, callback):
        super().__init__(title=f"{action} Appeal Reason")
        self.action = action
        self.callback = callback
        self.reason = TextInput(label="Reason", style=TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.reason)

    async def on_submit(self, interaction: Interaction):
        await self.callback(interaction, self.reason.value)

class AppealsModerationView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def insert_history(self, interaction, member, action_type, duration, reason, timestamp):
        max_retries = 5
        attempts = 0
        while attempts < max_retries:
            try:
                record = await interaction.client.db.fetchrow(
                    """
                    INSERT INTO history 
                    (id, guild_id, user_id, moderator_id, server_id, punishment, duration, reason, time) 
                    VALUES (
                        (SELECT COALESCE(MAX(id), 0) + 1 FROM history),
                        (SELECT COALESCE(MAX(guild_id), 0) + 1 FROM history WHERE server_id = $1), 
                        $2, $3, $4, $5, $6, $7, $8
                    ) RETURNING guild_id
                    """,
                    interaction.guild.id, member.id, interaction.user.id, interaction.guild.id, action_type, duration, reason, timestamp
                )
                if record:
                    return str(record['guild_id'])
                return None
            except asyncpg.UniqueViolationError:
                attempts += 1
                await asyncio.sleep(0.1)
                continue
            except Exception as e:
                return None
        return None
    
    async def logging(self, interaction, guild: Guild, user: User, moderator: User, reason: str, description: str, punishment: str, history_id: int):
        if guild:
            record = await interaction.client.db.fetchval("SELECT moderation FROM logging WHERE guild_id = $1", guild.id)
            if record:
                channel = guild.get_channel_or_thread(record)
                if isinstance(channel, (TextChannel, Thread)):
                    if not channel.permissions_for(channel.guild.me).send_messages:
                        return
                    if isinstance(channel, Thread) and not channel.permissions_for(channel.guild.me).send_messages_in_threads:
                        return
                    embed = Embed(color=colors.NEUTRAL, timestamp=datetime.utcnow())
                    embed.description = f"{user.mention} got {description}"
                    embed.set_author(name=user.name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
                    embed.add_field(name="User", value=f"**{user.name}** (`{user.id}`)", inline=False)
                    embed.add_field(name="Moderator", value=f"**{moderator.name}** (`{moderator.id}`)", inline=False)
                    embed.add_field(name="Reason", value=reason or "N/A", inline=False)
                    embed.set_footer(text=f"Members: {guild.member_count} | ID: {user.id}")
                    embed.title = f"{punishment} #{history_id}"
                    try:
                        await channel.send(embed=embed)
                    except NotFound:
                        pass

    @button(label="Accept", style=ButtonStyle.success, custom_id="persistent:accept")
    async def accept(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(AppealsModerationModal("Accept", self.process_accept))

    @button(label="Reject", style=ButtonStyle.danger, custom_id="persistent:reject")
    async def reject(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(AppealsModerationModal("Reject", self.process_reject))

    async def process_accept(self, interaction: Interaction, reason: str):
        discord_reason = f"[Appeal] {reason} | {interaction.user} ({interaction.user.id})"
        record = await interaction.client.db.fetchrow("SELECT * FROM history WHERE appeal_msg_id = $1", interaction.message.id)
        if not record:
            return await interaction.warn("This appeal can't be found in the database", ephemeral=True)
        guild = interaction.client.get_guild(record["server_id"])
        if not guild:
            return await interaction.warn("This guild can't be found", ephemeral=True)
        if record['punishment'] == "Ban":
            user = await interaction.client.fetch_user(record["user_id"])
            try:
                await guild.unban(user, reason=discord_reason)
            except Exception:
                return await interaction.warn(f"Failed to unban {user.mention}", ephemeral=True)
            history_id = await self.insert_history(interaction, user, "Unban", 'None', reason, datetime.now().timestamp())
            await self.logging(interaction, interaction.guild, user, interaction.user, reason, "unbanned", "Unban", history_id)
            try:
                embed = Embed(color=colors.ERROR, description=f"You have been accepted in {guild.name}\n> Reason: {reason}")
                await user.send(embed=embed)
            except:
                pass
        elif record['punishment'] == "Mute":
            member = guild.get_member(record["user_id"])
            try:
                await member.timeout(None, reason=discord_reason)
            except Exception:
                return await interaction.warn(f"Failed to unmute {member.mention}", ephemeral=True)
            history_id = await self.insert_history(interaction, member, "Unmute", 'None', reason, datetime.now().timestamp())
            await self.logging(interaction, interaction.guild, member, interaction.user, reason, "unmuted", "Unmute", history_id)
            try:
                embed = Embed(color=colors.SUCCESS, description=f"You have been unmuted in {guild.name}\n> Reason: {reason}")
                await member.send(embed=embed)
            except:
                pass
        elif record['punishment'] == "Jail":
            member = guild.get_member(record["user_id"])
            jailed_data = await interaction.bot.db.fetchrow("SELECT roles FROM jail_members WHERE guild_id = $1 AND user_id = $2", interaction.guild.id, member.id)
            if not jailed_data:
                return await interaction.warn(f"{member.mention} is **not** jailed", ephemeral=True)
            jail_info = await interaction.bot.db.fetchrow("SELECT * FROM jail WHERE guild_id = $1", interaction.guild.id)
            jail_role = interaction.guild.get_role(jail_info["role_id"])
            if not jail_role:
                return await interaction.warn("Jail role **not found**. Please unset jail and set it back", ephemeral=True)
            roles = [interaction.guild.get_role(role_id) for role_id in json.loads(jailed_data["roles"]) if interaction.guild.get_role(role_id)]
            manageable_roles = [role for role in roles if role and role.position < interaction.guild.me.top_role.position]
            if interaction.guild.premium_subscriber_role in member.roles:
                manageable_roles.append(interaction.guild.premium_subscriber_role)
            await member.edit(roles=manageable_roles, reason=discord_reason)
            await interaction.bot.db.execute("DELETE FROM jail_members WHERE guild_id = $1 AND user_id = $2", interaction.guild.id, member.id)
            history_id = await self.insert_history(interaction, member, "Unjail", 'None', reason, datetime.now().timestamp())
            await self.logging(interaction, interaction.guild, member, interaction.user, reason, "unjailed", "Unjail", history_id)
            try:
                embed = Embed(color=colors.SUCCESS, description=f"You have been unjailed in {guild.name}\n> Reason: {reason}")
                await member.send(embed=embed)
            except:
                pass
        for button in self.children:
            button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.approve("The appeal has been accepted\n> Reason: " + reason)

    async def process_reject(self, interaction: Interaction, reason: str):
        record = await interaction.client.db.fetchrow("SELECT * FROM history WHERE appeal_msg_id = $1", interaction.message.id)
        if not record:
            return await interaction.warn("This appeal can't be found in the database", ephemeral=True)
        guild = interaction.client.get_guild(record["server_id"])
        if not guild:
            return await interaction.warn("This guild can't be found", ephemeral=True)
        target = await interaction.client.fetch_user(record["user_id"]) if record['punishment'] == "Ban" else guild.get_member(record["user_id"])
        try:
            embed = Embed(color=colors.ERROR, description=f"You have been rejected in {guild.name}\n> Reason: {reason}")
            await target.send(embed=embed)
        except:
            pass
        for button in self.children:
            button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.approve("The appeal has been rejected\n> Reason: " + reason)

class AppealsView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Appeal", style=ButtonStyle.secondary, custom_id="persistent:appeal")
    async def appeal(self, interaction: Interaction, button: Button):
        record = await interaction.client.db.fetchrow("SELECT * FROM history WHERE appeal_id = $1",  interaction.message.id)
        if not record:
            return await interaction.warn("This appeal can't be found in the database", ephemeral=True)
        check = await interaction.client.db.fetchrow("SELECT * FROM appeals WHERE guild_id = $1",  record["server_id"])
        if not check:
            return await interaction.warn("Appeals are not enabled in this server", ephemeral=True)
        guild = interaction.client.get_guild(record["server_id"])
        if not guild:
            return await interaction.warn("This guild can't be found", ephemeral=True)
        channel = guild.get_channel(check["channel_id"])
        if not channel:
            return await interaction.warn("Appeals channel can't be found", ephemeral=True)
        if not channel.permissions_for(guild.me).send_messages:
            return await interaction.warn("I don't have permission to send messages in the appeals channel", ephemeral=True)
        return await interaction.response.send_modal(AppealsModal(self.bot, self))