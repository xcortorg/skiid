import json
import random
import string

from typing import Union

from discord import Interaction, NotFound, ButtonStyle, Emoji, PartialEmoji, Embed, Role, VoiceChannel
from discord.ui import View, Button
from discord.utils import get
from discord.errors import NotFound, HTTPException
from discord.ext.commands import Cog, group, has_guild_permissions

from modules.styles import emojis, colors
from modules.helpers import EvelinaContext
from modules.converters import DangerousRoleConverter
from modules.validators import ValidMessage
from modules.evelinabot import Evelina

class Autorole(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @group(name="reactionrole", invoke_without_command=True, aliases=["rr"], case_insensitive=True)
    async def reactionrole(self, ctx: EvelinaContext):
        """Set up self-assignable roles with reactions"""
        return await ctx.create_pages()

    @reactionrole.command(name="add", brief="manage roles", usage="reactionrole add .../channels/... :skull: dead chat")
    @has_guild_permissions(manage_roles=True)
    async def rr_add(self, ctx: EvelinaContext, message: ValidMessage, emoji: Union[Emoji, str], *, role: DangerousRoleConverter):
        """Adds a reaction role to a message"""
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
                    return await ctx.send_warning(f"An error occurred while trying to add the emoji")
        emoji_str = str(emoji) if isinstance(emoji, Emoji) else emoji.name
        check = await self.bot.db.fetchrow("SELECT * FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4", ctx.guild.id, message.channel.id, message.id, emoji_str)
        if check:
            return await ctx.send_warning("A similar reaction role is **already** added")
        await self.bot.db.execute("INSERT INTO reactionrole VALUES ($1,$2,$3,$4,$5)", ctx.guild.id, message.channel.id, message.id, emoji_str, role.id)
        try:
            await message.add_reaction(emoji)
        except NotFound:
            return await ctx.send_warning("Could not add the reaction to the message. It might be invalid or the message could have been deleted.")
        except HTTPException:
            return await ctx.send_warning("An error occurred while trying to add the emoji")
        return await ctx.send_success(f"Added {emoji} to [`{message.id}`]({message.jump_url}) with {role.mention} assigned")

    @reactionrole.command(name="remove", brief="manage roles", usage="reactionrole remove .../channels/... :skull:")
    @has_guild_permissions(manage_roles=True)
    async def rr_remove(self, ctx: EvelinaContext, message: ValidMessage, emoji: Union[Emoji, str]):
        """Removes a reaction role from a message"""
        check = await self.bot.db.fetchrow("SELECT * FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4", ctx.guild.id, message.channel.id, message.id, str(emoji))
        if not check:
            return await ctx.send_warning("No reaction role found for the message provided")
        await self.bot.db.execute("DELETE FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4", ctx.guild.id, message.channel.id, message.id, str(emoji))
        try:
            await message.remove_reaction(emoji, ctx.guild.me)
        except HTTPException:
            pass
        return await ctx.send_success(f"**No longer** assigning role for {emoji} for [`{message.id}`]({message.jump_url})")
    
    @reactionrole.command(name="removeall", brief="manage roles", usage="reactionrole removeall .../channels/...")
    @has_guild_permissions(manage_roles=True)
    async def rr_removeall(self, ctx: EvelinaContext, message: ValidMessage):
        """Removes all reaction roles from a message"""
        check = await self.bot.db.fetchrow("SELECT * FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        if not check:
            return await ctx.send_warning("No reaction roles found for the message provided")
        await self.bot.db.execute("DELETE FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", ctx.guild.id, message.channel.id, message.id)
        await message.clear_reactions()
        return await ctx.send_success(f"**No longer** assigning roles for message [`{message.id}`]({message.jump_url})")
    
    @reactionrole.command(name="list")
    async def rr_list(self, ctx: EvelinaContext):
        """View a list of every reaction role"""
        results = await self.bot.db.fetch("SELECT * FROM reactionrole WHERE guild_id = $1", ctx.guild.id)
        if len(results) == 0:
            return await ctx.send_warning("No reaction roles available for this server")
        return await ctx.paginate([f"{result['emoji']} [`{result['message_id']}`](https://discord.com/channels/{ctx.guild.id}/{result['channel_id']}/{result['message_id']}) - <@&{result['role_id']}>" for result in results], f"Reaction Roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @reactionrole.command(name="clear", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def rr_clear(self, ctx: EvelinaContext):
        """Clears every reaction role from guild"""
        async def yes_callback(interaction: Interaction) -> None:
            await interaction.client.db.execute("DELETE FROM reactionrole WHERE guild_id = $1", interaction.guild.id)
            return await interaction.response.edit_message(
                embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Cleared **all** reaction roles from the server"), view=None)
        async def no_callback(interaction: Interaction) -> None:
            return await interaction.response.edit_message(
                embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Reaction roles deletion got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to clear **all** reaction roles from the server? The reactions won't be removed", yes_callback, no_callback)

    @group(name="buttonrole", invoke_without_command=True, case_insensitive=True)
    async def buttonrole(self, ctx: EvelinaContext):
        """Buttonrole commands"""
        return await ctx.create_pages()

    @buttonrole.command(name="add", brief="manage roles", usage="buttonrole add .../channels/... member Verify ✅ green")
    @has_guild_permissions(manage_roles=True)
    async def buttonrole_add(self, ctx: EvelinaContext, message: ValidMessage, role: DangerousRoleConverter, label: str, emoji: str = "none", color: str = "grey"):
        """Add a button to a message\n> If you don't want to use an emoji/label, just type `none`"""
        guild_id = message.guild.id
        channel_id = message.channel.id
        message_id = message.id
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            await ctx.send_warning("Could not find this message. I don't have access to this guild")
            return
        channel = guild.get_channel(channel_id)
        if channel is None:
            await ctx.send_warning("Could not find this message. I don't have access to this channel")
            return
        try:
            message = await channel.fetch_message(message_id)
        except NotFound:
            await ctx.send_warning("Could not find this message. It might be invalid or the message could have been deleted")
            return
        if message.author.id != self.bot.user.id:
            await ctx.send_warning("I can't add buttons to messages that I didn't send")
            return
        if color.lower() == "green":
            button_style = ButtonStyle.success
        elif color.lower() == "red":
            button_style = ButtonStyle.danger
        elif color.lower() == "grey":
            button_style = ButtonStyle.secondary
        elif color.lower() == "blue":
            button_style = ButtonStyle.primary
        else:
            button_style = ButtonStyle.secondary
        if message.components:
            view = View.from_message(message)
        else:
            view = View()
        source = string.ascii_letters + string.digits
        code = "".join(random.choice(source) for _ in range(8))
        custom_id = f"{code}"
        try:
            if label == "none":
                label = "\u200b"
            if emoji == "none":
                custom_button = Button(
                    label=label, 
                    style=button_style, 
                    custom_id=custom_id
                )
            else:
                custom_emoji = PartialEmoji.from_str(emoji) if emoji.startswith('<:') or emoji.startswith('<a:') else PartialEmoji(name=emoji)
                custom_button = Button(
                    label=label, 
                    style=button_style, 
                    emoji=custom_emoji,
                    custom_id=custom_id
                )
            async def button_callback(interaction: Interaction):
                await self.toggle_role(interaction, role.id)
            custom_button.callback = button_callback
            view.add_item(custom_button)
            await message.edit(view=view)
            await self.bot.db.execute("INSERT INTO button_role (guild_id, channel_id, message_id, button_id, role_id, label, emoji) VALUES ($1, $2, $3, $4, $5, $6, $7)", guild_id, channel_id, message_id, custom_button.custom_id, role.id, label, emoji)
            await ctx.send_success(f"Added button with role {role.mention} [**here**]({message.jump_url})")
        except HTTPException as e:
            await ctx.send_warning(f"Failed to create the button\n **Important:** If you don't want to use an emoji, just type `none`")

    @buttonrole.command(name="remove", brief="manage guild", usage="buttonrole remove KbJNGwwY")
    @has_guild_permissions(manage_guild=True)
    async def buttonrole_remove(self, ctx: EvelinaContext, button_id: str):
        """Remove a specific button from a message by its custom_id"""
        button_exists = await self.bot.db.fetchrow("SELECT 1 FROM button_role WHERE guild_id = $1 AND button_id = $2 LIMIT 1", ctx.guild.id, button_id)
        if not button_exists:
            return await ctx.send_warning(f"Button **{button_id}** couldn't be found")
        guild_id, channel_id, message_id = await self.bot.db.fetchrow("SELECT guild_id, channel_id, message_id FROM button_role WHERE guild_id = $1 AND button_id = $2", ctx.guild.id, button_id)
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send_warning("Could not find this message. I don't have access to this guild.")
        channel = guild.get_channel(channel_id)
        if not channel:
            async def yes_callback(interaction: Interaction) -> None:
                await self.bot.db.execute("DELETE FROM button_role WHERE guild_id = $1 AND button_id = $2", guild_id, button_id)
                return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Removed button (`{button_id}`) from this [**message**](https://discord.com/{guild_id}/{channel_id}/{message_id})"), view=None)
            async def no_callback(interaction: Interaction) -> None:
                return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Button roles deletion got canceled."), view=None)
            await ctx.confirmation_send(f"{emojis.QUESTION} Message couldn't be found. However, message still exist in the database.\n> Do you want to remove them?", yes_callback, no_callback)
            return
        try:
            message = await channel.fetch_message(message_id)
        except NotFound:
            return await ctx.send_warning("Could not find this message. It might be invalid or the message could have been deleted")
        if not message.components:
            return await ctx.send_warning("This message doesn't have any buttons")
        view = View.from_message(message)
        updated_view = View()
        for item in view.children:
            if isinstance(item, Button) and item.custom_id != button_id:
                updated_view.add_item(item)
        try:
            await message.edit(view=updated_view)
            await self.bot.db.execute("DELETE FROM button_role WHERE guild_id = $1 AND button_id = $2", guild_id, button_id)
            await ctx.send_success(f"Button **{button_id}** has been removed from this [**message**]({message.jump_url})")
        except HTTPException as e:
            await ctx.send_warning(f"An error occurred while removing the button\n```{e}```")

    @buttonrole.command(name="clear", brief="manage roles", usage="buttonrole clear .../channels/...")
    @has_guild_permissions(manage_roles=True)
    async def buttonrole_clear(self, ctx: EvelinaContext, message: ValidMessage):
        """Remove all buttons from a message"""
        guild_id = message.guild.id
        channel_id = message.channel.id
        message_id = message.id
        button_exists = await self.bot.db.fetchrow("SELECT 1 FROM button_role WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 LIMIT 1", guild_id, channel_id, message_id)
        if not button_exists:
            return await ctx.send_warning("There are no buttons in this message.")
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send_warning("Could not find this message. I don't have access to this guild.")
        channel = guild.get_channel(channel_id)
        if not channel:
            return await ctx.send_warning("Could not find this message. I don't have access to this channel.")
        try:
            message = await channel.fetch_message(message_id)
        except NotFound:
            async def yes_callback(interaction: Interaction) -> None:
                await self.bot.db.execute("DELETE FROM button_role WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", guild_id, channel_id, message_id)
                return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Removed all buttons from this [**message**](https://discord.com/{guild_id}/{channel_id}/{message_id})"), view=None)
            async def no_callback(interaction: Interaction) -> None:
                return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Button roles deletion got canceled."), view=None)
            await ctx.confirmation_send(f"{emojis.QUESTION} Message couldn't be found. However,message still exist in the database.\n> Do you want to remove them?", yes_callback, no_callback)
            return
        async def yes_callback(interaction: Interaction) -> None:
            new_view = View()
            await message.edit(view=new_view)
            await self.bot.db.execute("DELETE FROM button_role WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", guild_id, channel_id, message_id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Removed all buttons from this [**message**]({message.jump_url})"), view=None)
        async def no_callback(interaction: Interaction) -> None:
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Button roles deletion got canceled."), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to clear **all** button roles from this [**message**]({message.jump_url})?", yes_callback, no_callback)

    @buttonrole.command(name="list")
    async def buttonrole_list(self, ctx: EvelinaContext):
        """View a list of every button role"""
        results = await self.bot.db.fetch("SELECT * FROM button_role WHERE guild_id = $1", ctx.guild.id)
        if len(results) == 0:
            return await ctx.send_warning("No button roles available for this server")
        button_roles = []
        for result in results:
            emoji_part = f"{result['emoji']} " if result['emoji'] != "none" else ""
            button_roles.append(f"{emoji_part}**{result['label']}** <@&{result['role_id']}> (`{result['button_id']}`) [**here**](https://discord.com/channels/{ctx.guild.id}/{result['channel_id']}/{result['message_id']})")
        return await ctx.paginate(button_roles, "Button Roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @buttonrole.command(name="unique", brief="Set button role unique behavior", usage="buttonrole unique .../channels/... true/false")
    @has_guild_permissions(manage_roles=True)
    async def buttonrole_unique(self, ctx: EvelinaContext, message: ValidMessage, unique: bool):
        """Set whether the roles on a message are unique (only one role allowed)."""
        guild_id = message.guild.id
        channel_id = message.channel.id
        message_id = message.id
        button_exists = await self.bot.db.fetchrow(
            """
            SELECT 1 
            FROM button_role 
            WHERE guild_id = $1 AND message_id = $2
            """,
            guild_id, message_id
        )
        if not button_exists:
            await ctx.send_warning(f"No buttons are assigned to [this message]({message.jump_url})")
            return
        await self.bot.db.execute(
            """
            INSERT INTO button_settings (guild_id, channel_id, message_id, "unique") 
            VALUES ($1, $2, $3, $4) 
            ON CONFLICT (guild_id, message_id) 
            DO UPDATE SET "unique" = $4
            """,
            guild_id, channel_id, message_id, unique
        )
        state = "enabled" if unique else "disabled"
        await ctx.send_success(f"Unique role behavior for [this message]({message.jump_url}) has been {state}")

    async def toggle_role(self, interaction: Interaction, role_id: int):
        await interaction.response.defer(ephemeral=True)
        role = interaction.guild.get_role(role_id)
        if role is None:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Role couldn't be found on this guild")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        member = interaction.user
        bot_member = interaction.guild.me
        if role >= bot_member.top_role:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Bot is **missing** the following permission: `manage_roles`")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            unique_setting = await self.bot.db.fetchrow("SELECT 'unique' FROM button_settings WHERE guild_id = $1 AND message_id = $2", interaction.guild.id, interaction.message.id)
            if unique_setting and unique_setting['unique']:
                roles_to_remove = await self.bot.db.fetch("SELECT role_id FROM button_role WHERE guild_id = $1 AND message_id = $2", interaction.guild.id, interaction.message.id)
                roles_to_remove_ids = [record['role_id'] for record in roles_to_remove if record['role_id'] in [role.id for role in member.roles]]
                if roles_to_remove_ids:
                    await member.remove_roles(*[interaction.guild.get_role(rid) for rid in roles_to_remove_ids])
        except Exception:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while processing roles")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if role in member.roles:
            await member.remove_roles(role)
            response_color = colors.ERROR
            response_emoji = emojis.REMOVE
            response_message = f"Removed role {role.mention}"
        else:
            await member.add_roles(role)
            response_color = colors.SUCCESS
            response_emoji = emojis.ADD
            response_message = f"Added role {role.mention}"
        embed = Embed(color=response_color, description=f"{response_emoji} {interaction.user.mention}: {response_message}")
        return await interaction.followup.send(embed=embed, ephemeral=True)

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if isinstance(interaction.data, dict) and "custom_id" in interaction.data:
            custom_id = interaction.data["custom_id"]
            if not interaction.guild or not interaction.message:
                return
            try:
                record = await self.bot.db.fetchrow("SELECT role_id FROM button_role WHERE guild_id = $1 AND message_id = $2 AND button_id = $3", interaction.guild.id, interaction.message.id, custom_id)
                if record:
                    try:
                        await self.toggle_role(interaction, record["role_id"])
                    except Exception:
                        pass
            except Exception:
                pass
    
    @group(invoke_without_command=True, case_insensitive=True)
    async def autorole(self, ctx: EvelinaContext):
        """Set up automatic role assign on member join"""
        return await ctx.create_pages()

    @autorole.group(name="humans", invoke_without_command=True, case_insensitive=True)
    async def autorole_humans(self, ctx: EvelinaContext):
        """Set up automatic role assign for humans"""
        return await ctx.create_pages()

    @autorole.group(name="bots", invoke_without_command=True, case_insensitive=True)
    async def autorole_bots(self, ctx: EvelinaContext):
        """Set up automatic role assign for bots"""
        return await ctx.create_pages()

    @autorole.group(name="all", invoke_without_command=True, case_insensitive=True)
    async def autorole_all(self, ctx: EvelinaContext):
        """Set up automatic role assign for all members"""
        return await ctx.create_pages()

    @autorole_humans.command(name="add", brief="manage guild", usage="autorole humans add role")
    @has_guild_permissions(manage_guild=True)
    async def autorole_humans_add(self, ctx: EvelinaContext, *, role: DangerousRoleConverter):
        """Adds an autorole for humans and assigns on join"""
        try:
            await self.bot.db.execute("INSERT INTO autorole_humans (guild_id, role_id) VALUES ($1, $2)", ctx.guild.id, role.id)
            return await ctx.send_success(f"{role.mention} added as autorole for humans")
        except:
            return await ctx.send_warning("This role is **already** an autorole for humans")

    @autorole_bots.command(name="add", brief="manage guild", usage="autorole bots add role")
    @has_guild_permissions(manage_guild=True)
    async def autorole_bots_add(self, ctx: EvelinaContext, *, role: DangerousRoleConverter):
        """Adds an autorole for bots and assigns on join"""
        try:
            await self.bot.db.execute("INSERT INTO autorole_bots (guild_id, role_id) VALUES ($1, $2)", ctx.guild.id, role.id)
            return await ctx.send_success(f"{role.mention} added as autorole for bots")
        except:
            return await ctx.send_warning("This role is **already** an autorole for bots")

    @autorole_all.command(name="add", brief="manage guild", usage="autorole all add role")
    @has_guild_permissions(manage_guild=True)
    async def autorole_all_add(self, ctx: EvelinaContext, *, role: DangerousRoleConverter):
        """Adds an autorole for all members and assigns on join"""
        try:
            await self.bot.db.execute("INSERT INTO autorole (guild_id, role_id) VALUES ($1, $2)", ctx.guild.id, role.id)
            return await ctx.send_success(f"{role.mention} added as autorole for all members")
        except:
            return await ctx.send_warning("This role is **already** an autorole for all members")

    @autorole_humans.command(name="remove", brief="manage guild", usage="autorole humans remove role")
    @has_guild_permissions(manage_guild=True)
    async def autorole_humans_remove(self, ctx: EvelinaContext, *, role: Union[Role, int]):
        """Removes an autorole for humans"""
        role_id = self.bot.misc.convert_role(role)
        if not await self.bot.db.fetchrow("SELECT * FROM autorole_humans WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id):
            return await ctx.send_warning("This role is **not** configured as an autorole for humans")
        await self.bot.db.execute("DELETE FROM autorole_humans WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id)
        return await ctx.send_success(f"{self.bot.misc.humanize_role(ctx.guild, role_id)} removed from autorole list for humans")

    @autorole_bots.command(name="remove", brief="manage guild", usage="autorole bots remove role")
    @has_guild_permissions(manage_guild=True)
    async def autorole_bots_remove(self, ctx: EvelinaContext, *, role: Union[Role, int]):
        """Removes an autorole for bots"""
        role_id = self.bot.misc.convert_role(role)
        if not await self.bot.db.fetchrow("SELECT * FROM autorole_bots WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id):
            return await ctx.send_warning("This role is **not** configured as an autorole for bots")
        await self.bot.db.execute("DELETE FROM autorole_bots WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id)
        return await ctx.send_success(f"{self.bot.misc.humanize_role(ctx.guild, role_id)} removed from autorole list for bots")

    @autorole_all.command(name="remove", brief="manage guild", usage="autorole all remove role")
    @has_guild_permissions(manage_guild=True)
    async def autorole_all_remove(self, ctx: EvelinaContext, *, role: Union[Role, int]):
        """Removes an autorole for all members"""
        role_id = self.bot.misc.convert_role(role)
        if not await self.bot.db.fetchrow("SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id):
            return await ctx.send_warning("This role is **not** configured as an autorole for all members")
        await self.bot.db.execute("DELETE FROM autorole WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id)
        return await ctx.send_success(f"{self.bot.misc.humanize_role(ctx.guild, role_id)} removed from autorole list for all members")

    @autorole_humans.command(name="list")
    async def autorole_humans_list(self, ctx: EvelinaContext):
        """View a list of every auto role for humans"""
        results = await self.bot.db.fetch("SELECT * FROM autorole_humans WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("No autoroles for humans found for this server")
        roles = [f"{self.bot.misc.humanize_role(ctx.guild, result['role_id'])}" for result in results]
        await ctx.paginate(roles, f"Autoroles for Humans", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @autorole_bots.command(name="list")
    async def autorole_bots_list(self, ctx: EvelinaContext):
        """View a list of every auto role for bots"""
        results = await self.bot.db.fetch("SELECT * FROM autorole_bots WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("No autoroles for bots found for this server")
        roles = [f"{self.bot.misc.humanize_role(ctx.guild, result['role_id'])}" for result in results]
        await ctx.paginate(roles, f"Autoroles for Bots", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @autorole_all.command(name="list")
    async def autorole_all_list(self, ctx: EvelinaContext):
        """View a list of every auto role for all members"""
        results = await self.bot.db.fetch("SELECT * FROM autorole WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("No autoroles for all members found for this server")
        roles = [f"{self.bot.misc.humanize_role(ctx.guild, result['role_id'])}" for result in results]
        await ctx.paginate(roles, f"Autoroles for All Members", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @autorole_humans.command(name="clear", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def autorole_humans_clear(self, ctx: EvelinaContext):
        """Clears every autorole for humans in guild"""
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM autorole_humans WHERE guild_id = $1", interaction.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"Cleared all autoroles for humans"), view=None)
        async def no_callback(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"Autorole deletion for humans got canceled"), view=None)
        await ctx.confirmation_send("Are you sure you want to clear the autoroles for humans?", yes_callback, no_callback)

    @autorole_bots.command(name="clear", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def autorole_bots_clear(self, ctx: EvelinaContext):
        """Clears every autorole for bots in guild"""
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM autorole_bots WHERE guild_id = $1", interaction.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"Cleared all autoroles for bots"), view=None)
        async def no_callback(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"Autorole deletion for bots got canceled"), view=None)
        await ctx.confirmation_send("Are you sure you want to clear the autoroles for bots?", yes_callback, no_callback)

    @autorole_all.command(name="clear", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def autorole_all_clear(self, ctx: EvelinaContext):
        """Clears every autorole for all members in guild"""
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM autorole WHERE guild_id = $1", interaction.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"Cleared all autoroles for all members"), view=None)
        async def no_callback(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"Autorole deletion for all members got canceled"), view=None)
        await ctx.confirmation_send("Are you sure you want to clear the autoroles for all members?", yes_callback, no_callback)

    @group(name="voicerole", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    async def voicerole(self, ctx: EvelinaContext):
        """Set up voice channel role assign"""
        return await ctx.create_pages()

    @voicerole.command(name="add", brief="manage guild", usage="voicerole add #voice in-game")
    @has_guild_permissions(manage_guild=True)
    async def voicerole_add(self, ctx: EvelinaContext, channel: VoiceChannel, *, role: DangerousRoleConverter):
        """Adds a voice channel role assign"""
        if not channel:
            return await ctx.send_warning("Voice channel not found")
        check = await self.bot.db.fetchrow("SELECT roles FROM voicerole WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if check:
            roles = json.loads(check['roles'])
            if role.id in roles:
                return await ctx.send_warning(f"Role {role.mention} is already assigned to this voice channel")
            roles.append(role.id)
            await self.bot.db.execute("UPDATE voicerole SET roles = $1 WHERE guild_id = $2 AND channel_id = $3", json.dumps(roles), ctx.guild.id, channel.id)
        else:
            await self.bot.db.execute("INSERT INTO voicerole (guild_id, channel_id, roles) VALUES ($1, $2, $3)", ctx.guild.id, channel.id, json.dumps([role.id]))
        return await ctx.send_success(f"Added role {role.mention} for voice channel {channel.mention}")

    @voicerole.command(name="remove", brief="manage guild", usage="voicerole remove #voice role")
    @has_guild_permissions(manage_guild=True)
    async def voicerole_remove(self, ctx: EvelinaContext, channel: Union[VoiceChannel, int], *, role: Union[Role, int]):
        """Removes a voice channel role assign"""
        channel_id = self.bot.misc.convert_voicechannel(channel)
        role_id = self.bot.misc.convert_role(role)
        if not channel:
            return await ctx.send_warning("Voice channel not found")
        check = await self.bot.db.fetchrow("SELECT roles FROM voicerole WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        if not check:
            return await ctx.send_warning("This voice channel is not configured for role assign")
        roles = json.loads(check['roles'])
        if role_id not in roles:
            return await ctx.send_warning(f"Role {self.bot.misc.humanize_role(ctx.guild, role_id)} is not assigned to this voice channel")
        roles.remove(role_id)
        if roles:
            await self.bot.db.execute("UPDATE voicerole SET roles = $1 WHERE guild_id = $2 AND channel_id = $3", json.dumps(roles), ctx.guild.id, channel_id)
        else:
            await self.bot.db.execute("DELETE FROM voicerole WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"Removed role {self.bot.misc.humanize_role(ctx.guild, role_id)} from voice channel {self.bot.misc.humanize_role(ctx.guild, channel_id)}")
    
    @voicerole.group(name="default", invoke_without_command=True, case_insensitive=True)
    async def voicerole_default(self, ctx: EvelinaContext):
        """Set up default role for voice channel role assign"""
        return await ctx.create_pages()
    
    @voicerole_default.command(name="add", brief="manage guild", usage="voicerole default add voice")
    @has_guild_permissions(manage_guild=True)
    async def voicerole_default_add(self, ctx: EvelinaContext, *, role: DangerousRoleConverter):
        """Sets a default role for voice channel role assign"""
        check = await self.bot.db.fetchrow("SELECT role_id FROM voicerole_default WHERE guild_id = $1", ctx.guild.id)
        if check:
            await self.bot.db.execute("UPDATE voicerole_default SET role_id = $1 WHERE guild_id = $2", role.id, ctx.guild.id)
        else:
            await self.bot.db.execute("INSERT INTO voicerole_default (guild_id, role_id) VALUES ($1, $2)", ctx.guild.id, role.id)
        return await ctx.send_success(f"Set {role.mention} as default role for voice channel role assign")
    
    @voicerole_default.command(name="remove", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def voicerole_default_remove(self, ctx: EvelinaContext):
        """Removes the default role for voice channel role assign"""
        check = await self.bot.db.fetchrow("SELECT role_id FROM voicerole_default WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("No default role set for voice channel role assign")
        await self.bot.db.execute("DELETE FROM voicerole_default WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Removed default role for voice channel role assign")
    
    @voicerole.command(name="clear", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def voicerole_clear(self, ctx: EvelinaContext):
        """Clears every voice channel role assign in guild"""
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM voicerole WHERE guild_id = $1", interaction.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Cleared all voice channel role assign"), view=None)
        async def no_callback(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Voice channel role assign deletion got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to clear the voice channel role assign?", yes_callback, no_callback)

    @voicerole.command(name="list", brief="Lists all voice channels and their assigned roles", usage="voicerole list")
    @has_guild_permissions(manage_guild=True)
    async def voicerole_list(self, ctx: EvelinaContext):
        """Lists all voice channels and their assigned roles"""
        records = await self.bot.db.fetch("SELECT channel_id, roles FROM voicerole WHERE guild_id = $1", ctx.guild.id)
        if not records:
            return await ctx.send_warning("No voice channels have assigned roles.")
        content = []
        for record in records:
            channel = ctx.guild.get_channel(record['channel_id'])
            if not channel:
                continue
            try:
                role_ids = json.loads(record['roles'])
                roles = [ctx.guild.get_role(role_id) for role_id in role_ids if ctx.guild.get_role(role_id)]
            except json.JSONDecodeError:
                roles = []
            roles_text = ' '.join([role.mention for role in roles]) if roles else "No roles assigned or roles are unknown."
            content.append(f"**{channel.mention}**: {roles_text}")
        if not content:
            return await ctx.send_warning("No valid voice channels found with assigned roles.")
        await ctx.paginate(content, "Voice Channel Roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

async def setup(bot: Evelina) -> None:
    await bot.add_cog(Autorole(bot))