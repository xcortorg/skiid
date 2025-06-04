import json
import random
import string

from datetime import datetime
from humanfriendly import format_timespan

from discord import PartialEmoji, utils, TextChannel, Embed, Interaction, Emoji, NotFound, ButtonStyle, User, Role, AllowedMentions
from discord.ui import View, Button
from discord.utils import get, Union
from discord.ext.commands import Cog, command, group, has_guild_permissions, Flag
from discord.errors import HTTPException

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.validators import ValidTime, ValidMessage

class Responders(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Responders commands"

    @command(name="react", brief="manage guild", usage="react .../channels/... :f_thumbsup:")
    @has_guild_permissions(manage_guild=True)
    async def react(self, ctx: EvelinaContext, message: ValidMessage, emoji: Union[Emoji, str]):
        """Add a reaction to a message"""
        try:
            if isinstance(emoji, str):
                emoji = emoji.strip(":")
                custom_emoji = get(ctx.guild.emojis, name=emoji)
                if not custom_emoji:
                    try:
                        unicode_emoji = PartialEmoji.from_str(emoji)
                        if unicode_emoji.is_unicode_emoji():
                            emoji = unicode_emoji.name
                        else:
                            return await ctx.send_warning(f"Emoji `{emoji}` is not valid or not available on this server.")
                    except Exception:
                        return await ctx.send_warning(f"An error occurred while parsing the emoji.")
                else:
                    emoji = custom_emoji
            await message.add_reaction(emoji)
            await ctx.send_success(f"Added {emoji} to [`{message.id}`]({message.jump_url})")
        except NotFound:
            return await ctx.send_warning("The message could not be found or has been deleted.")
        except HTTPException as e:
            return await ctx.send_warning(f"Could not add the reaction. Error: {str(e)}")

    @group(name="autoreact", invoke_without_command=True, case_insensitive=True)
    async def autoreact(self, ctx: EvelinaContext):
        """Add a reaction(s) to a message"""
        return await ctx.create_pages()

    @autoreact.command(name="add", brief="manage guild", usage="autoreact add panda, :f_thumbsup:")
    @has_guild_permissions(manage_guild=True)
    async def autoreact_add(self, ctx: EvelinaContext, *, content: str):
        """Adds a reaction trigger to guild"""
        con = content.split(", ")
        if len(con) == 1:
            return await ctx.send_warning("No reactions found. Make sure to use a `,` to split the trigger from the reactions")
        trigger = con[0].strip()
        if not trigger:
            return await ctx.send_warning("No valid trigger found")
        reactions_input = con[1].split(" ")
        reactions = []
        for reaction in reactions_input:
            emoji = reaction.strip()
            custom_emoji = None
            if emoji.startswith('<:') or emoji.startswith('<a:'):
                emoji_name = emoji.split(':')[1]
                custom_emoji = utils.get(ctx.guild.emojis, name=emoji_name)
            else:
                custom_emoji = utils.get(ctx.guild.emojis, name=emoji.strip(':'))
            if custom_emoji:
                if not custom_emoji.guild.id == ctx.guild.id:
                    return await ctx.send_warning(f"Emoji `{reaction}` is not **available** on this server")
                reactions.append(str(custom_emoji))
            else:
                try:
                    unicode_emoji = PartialEmoji.from_str(emoji)
                    if unicode_emoji.is_unicode_emoji():
                        reactions.append(unicode_emoji.name)
                except:
                    continue
        if not reactions:
            return await ctx.send_warning(f"Emojis are not **available** on this server or it's not a **valid** emoji")
        check = await self.bot.db.fetchrow("SELECT * FROM autoreact WHERE guild_id = $1 AND trigger = $2", ctx.guild.id, trigger)
        if not check:
            await self.bot.db.execute("INSERT INTO autoreact (guild_id, trigger, reactions) VALUES ($1, $2, $3)", ctx.guild.id, trigger, json.dumps(reactions))
        else:
            await self.bot.db.execute("UPDATE autoreact SET reactions = $1 WHERE guild_id = $2 AND trigger = $3", json.dumps(reactions), ctx.guild.id, trigger)
        return await ctx.send_success(f"Your autoreact for **{trigger}** has been created with the reactions {' '.join(reactions)}")

    @autoreact.command(name="remove", brief="manage guild", usage="autoreact remove skull")
    @has_guild_permissions(manage_guild=True)
    async def autoreact_remove(self, ctx: EvelinaContext, *, trigger: str):
        """Removes a reaction trigger in guild"""
        check = await self.bot.db.fetchrow("SELECT * FROM autoreact WHERE guild_id = $1 AND trigger = $2", ctx.guild.id, trigger)
        if not check:
            return await ctx.send_warning("There is no **autoreact** with this trigger")
        await self.bot.db.execute("DELETE FROM autoreact WHERE guild_id = $1 AND trigger = $2", ctx.guild.id, trigger)
        return await ctx.send_success(f"Removed **{trigger}** from autoreact")

    @autoreact.command(name="list")
    async def autoreact_list(self, ctx: EvelinaContext):
        """View a list of every reaction trigger in guild"""
        check = await self.bot.db.fetch("SELECT * FROM autoreact WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There are no autoreactions available in this server")
        return await ctx.paginate([f"{r['trigger']} - {' '.join(json.loads(r['reactions']))}" for r in check], f"Autoreactions", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @autoreact.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def autoreact_reset(self, ctx: EvelinaContext):
        """Reset all reaction triggers in guild"""
        check = await self.bot.db.fetch("SELECT * FROM autoreact WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There are no autoreactions available in this server")
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM autoreact WHERE guild_id = $1", interaction.guild.id)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Deleted all autoreactions in this server")
            await interaction.response.edit_message(embed=embed, view=None)
        async def no_callback(interaction: Interaction):
            embed = Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Autoreactions deletion got canceled")
            await interaction.response.edit_message(embed=embed, view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **RESET** all autoreactions in this server?", yes_callback, no_callback)

    @autoreact.group(name="channel", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    async def autoreact_channel(self, ctx: EvelinaContext):
        """Set up autoreact channel"""
        return await ctx.create_pages()

    @autoreact_channel.command(name="add", brief="manage guild", usage="autoreact channel add #general :f_thumbsup:")
    @has_guild_permissions(manage_guild=True)
    async def autoreact_channel_add(self, ctx: EvelinaContext, channel: TextChannel, *, reactions: str):
        """Add a channel to autoreact"""
        if not channel.slowmode_delay:
            return await ctx.send_warning(f"You need to set a **slowmode** to {channel.mention} to use this feature.")
        reactions_input = reactions.split(" ")
        reactions = []
        for reaction in reactions_input:
            emoji = reaction.strip()
            custom_emoji = None
            if emoji.startswith('<:') or emoji.startswith('<a:'):
                emoji_name = emoji.split(':')[1]
                custom_emoji = utils.get(ctx.guild.emojis, name=emoji_name)
            else:
                custom_emoji = utils.get(ctx.guild.emojis, name=emoji.strip(':'))
            if custom_emoji:
                if not custom_emoji.guild.id == ctx.guild.id:
                    return await ctx.send_warning(f"Emoji `{reaction}` is not **available** on this server")
                reactions.append(str(custom_emoji))
            else:
                try:
                    unicode_emoji = PartialEmoji.from_str(emoji)
                    if unicode_emoji.is_unicode_emoji():
                        reactions.append(unicode_emoji.name)
                except:
                    continue
        if not reactions:
            return await ctx.send_warning(f"Emojis are not **available** on this server or it's not a **valid** emoji")
        check = await self.bot.db.fetchrow("SELECT * FROM autoreact_channel WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if not check:
            await self.bot.db.execute("INSERT INTO autoreact_channel (guild_id, channel_id, reactions) VALUES ($1, $2, $3)", ctx.guild.id, channel.id, json.dumps(reactions))
        else:
            await self.bot.db.execute("UPDATE autoreact_channel SET reactions = $1 WHERE guild_id = $2 AND channel_id = $3", json.dumps(reactions), ctx.guild.id, channel.id)
        return await ctx.send_success(f"Set {' '.join(reactions)} as **auto reactions** for **{channel.mention}**")
    
    @autoreact_channel.command(name="remove", brief="manage guild", usage="autoreact channel remove #general")
    @has_guild_permissions(manage_guild=True)
    async def autoreact_channel_remove(self, ctx: EvelinaContext, channel: TextChannel):
        """Remove a channel from autoreact"""
        check = await self.bot.db.fetchrow("SELECT * FROM autoreact_channel WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if not check:
            return await ctx.send_warning("There is no **autoreact** with this channel")
        await self.bot.db.execute("DELETE FROM autoreact_channel WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        return await ctx.send_success(f"Removed **auto reactions** from {channel.mention}")
    
    @autoreact_channel.command(name="list")
    async def autoreact_channel_list(self, ctx: EvelinaContext):
        """View a list of every channel in autoreact"""
        check = await self.bot.db.fetch("SELECT * FROM autoreact_channel WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There are no autoreactions available in this server")
        return await ctx.paginate([f"<#{r['channel_id']}> - {' '.join(json.loads(r['reactions']))}" for r in check], f"Autoreactions", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @autoreact_channel.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def autoreact_channel_reset(self, ctx: EvelinaContext):
        """Reset all autoreact channels in guild"""
        check = await self.bot.db.fetch("SELECT * FROM autoreact_channel WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There are no autoreactions available in this server")
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM autoreact_channel WHERE guild_id = $1", interaction.guild.id)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Deleted all autoreactions in this server")
            await interaction.response.edit_message(embed=embed, view=None)
        async def no_callback(interaction: Interaction):
            embed = Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Autoreactions deletion got canceled")
            await interaction.response.edit_message(embed=embed, view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **RESET** all autoreactions in this server?", yes_callback, no_callback)

    @group(name="autoresponder", aliases=["ar"], invoke_without_command=True, case_insensitive=True)
    async def autoresponder(self, ctx: EvelinaContext):
        """Set up automatic replies to messages that match a trigger"""
        return await ctx.create_pages()

    @autoresponder.command(name="add", brief="manage guild", usage="autoresponder add hello, hello world --not_strict", extras={"not_strict": "Respond to messages that match the trigger not exactly.", "delete": "Delete the message that triggered the response.", "reply": "Reply to the message that triggered the response."})
    @has_guild_permissions(manage_guild=True)
    async def ar_add(self, ctx: EvelinaContext, *, response: str):
        """Create a reply for a trigger word"""
        strict = True
        delete_flag = False
        reply_flag = False
        if " --not_strict" in response:
            strict = False
            response = response.replace(" --not_strict", "")
        if " --delete" in response:
            delete_flag = True
            response = response.replace(" --delete", "")
        if " --reply" in response:
            reply_flag = True
            response = response.replace(" --reply", "")
        responses = response.split(", ", maxsplit=1)
        if len(responses) == 1:
            return await ctx.send_warning("Response not found! Please use `,` to split the trigger and the response")
        trigger = responses[0].strip()
        if trigger == "":
            return await ctx.send_warning("No trigger found")
        resp = responses[1].strip()
        if not resp:
            return await ctx.send_warning("Response not found! Please use `,` to split the trigger and the response")
        check = await self.bot.db.fetchrow("SELECT * FROM autoresponder WHERE guild_id = $1 AND trigger = $2", ctx.guild.id, trigger.lower())
        if check:
            return await ctx.send_warning(f"An autoresponder for **{trigger}** already exists")
        else:
            await self.bot.db.execute(
                "INSERT INTO autoresponder (guild_id, trigger, response, strict, delete, reply) VALUES ($1, $2, $3, $4, $5, $6)",
                ctx.guild.id, trigger.lower(), resp, strict, delete_flag, reply_flag
            )
            return await ctx.send_success(f"Added autoresponder for **{trigger}** - {resp} {'(not strict)' if not strict else ''} {'(delete trigger)' if delete_flag else ''} {'(reply)' if reply_flag else ''}")

    @autoresponder.command(name="remove", brief="manage guild", usage="autoresponder remove hello")
    @has_guild_permissions(manage_guild=True)
    async def ar_remove(self, ctx: EvelinaContext, *, trigger: str):
        """Remove a reply for a trigger word"""
        check = await self.bot.db.fetchrow("SELECT * FROM autoresponder WHERE guild_id = $1 AND trigger = $2", ctx.guild.id, trigger)
        if not check:
            return await ctx.send_warning("There is no autoresponder with the trigger you have provided")
        await self.bot.db.execute("DELETE FROM autoresponder WHERE guild_id = $1 AND trigger = $2", ctx.guild.id, trigger)
        return await ctx.send_success(f"Deleted the autoresponder for **{trigger}**")

    @autoresponder.command(name="allow", usage="autoresponder allow hello comminate")
    @has_guild_permissions(manage_guild=True)
    async def ar_allow(self, ctx: EvelinaContext, trigger: str, *, target: Union[User, Role, TextChannel]):
        """Set specific users, channels, or roles as allowed for a trigger"""
        check = await self.bot.db.fetchrow("SELECT * FROM autoresponder WHERE guild_id = $1 AND trigger = $2", ctx.guild.id, trigger)
        if not check:
            return await ctx.send_warning("No autoresponder found with the given trigger")
        permission_data = await self.bot.db.fetchval(
            "SELECT data FROM autoresponder_permissions WHERE guild_id = $1 AND trigger = $2 AND state = $3",
            ctx.guild.id, trigger, "allow"
        )
        if not permission_data:
            permission_data = {"users": [], "channels": [], "roles": []}
        else:
            permission_data = json.loads(permission_data)
        if isinstance(target, User):
            type = "user"
            if target.id in permission_data["users"]:
                state = "Removed"
                permission_data["users"].remove(target.id)
            else:
                state = "Added"
                permission_data["users"].append(target.id)
        elif isinstance(target, Role):
            type = "role"
            if target.id in permission_data["roles"]:
                state = "Removed"
                permission_data["roles"].remove(target.id)
            else:
                state = "Added"
                permission_data["roles"].append(target.id)
        elif isinstance(target, TextChannel):
            type = "channel"
            if target.id in permission_data["channels"]:
                state = "Removed"
                permission_data["channels"].remove(target.id)
            else:
                state = "Added"
                permission_data["channels"].append(target.id)
        else:
            return await ctx.send_warning("No valid `user`, `role`, or `channel` found")
        if not permission_data["users"] and not permission_data["roles"] and not permission_data["channels"]:
            await self.bot.db.execute(
                "DELETE FROM autoresponder_permissions WHERE guild_id = $1 AND trigger = $2 AND state = $3",
                ctx.guild.id, trigger, "allow"
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO autoresponder_permissions (guild_id, trigger, state, data) VALUES ($1, $2, $3, $4) "
                "ON CONFLICT (guild_id, trigger, state) DO UPDATE SET data = $4",
                ctx.guild.id, trigger, "allow", json.dumps(permission_data)
            )
        await ctx.send_success(f"{state} {type} {target.mention} {'to' if state == 'Added' else 'from'} **allow** permissions for trigger **{trigger}**")

    @autoresponder.command(name="deny", usage="autoresponder deny hello comminate")
    @has_guild_permissions(manage_guild=True)
    async def ar_deny(self, ctx: EvelinaContext, trigger: str, *, target: Union[User, Role, TextChannel]):
        """Set specific users, channels, or roles as denied for a trigger"""
        check = await self.bot.db.fetchrow("SELECT * FROM autoresponder WHERE guild_id = $1 AND trigger = $2", ctx.guild.id, trigger)
        if not check:
            return await ctx.send_warning("No autoresponder found with the given trigger")
        permission_data = await self.bot.db.fetchval(
            "SELECT data FROM autoresponder_permissions WHERE guild_id = $1 AND trigger = $2 AND state = $3",
            ctx.guild.id, trigger, "deny"
        )
        if not permission_data:
            permission_data = {"users": [], "channels": [], "roles": []}
        else:
            permission_data = json.loads(permission_data)
        if isinstance(target, User):
            type = "user"
            if target.id in permission_data["users"]:
                state = "Removed"
                permission_data["users"].remove(target.id)
            else:
                state = "Added"
                permission_data["users"].append(target.id)
        elif isinstance(target, Role):
            type = "role"
            if target.id in permission_data["roles"]:
                state = "Removed"
                permission_data["roles"].remove(target.id)
            else:
                state = "Added"
                permission_data["roles"].append(target.id)
        elif isinstance(target, TextChannel):
            type = "channel"
            if target.id in permission_data["channels"]:
                state = "Removed"
                permission_data["channels"].remove(target.id)
            else:
                state = "Added"
                permission_data["channels"].append(target.id)
        else:
            return await ctx.send_warning("No valid `user`, `role`, or `channel` found")
        if not permission_data["users"] and not permission_data["roles"] and not permission_data["channels"]:
            await self.bot.db.execute(
                "DELETE FROM autoresponder_permissions WHERE guild_id = $1 AND trigger = $2 AND state = $3",
                ctx.guild.id, trigger, "deny"
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO autoresponder_permissions (guild_id, trigger, state, data) VALUES ($1, $2, $3, $4) "
                "ON CONFLICT (guild_id, trigger, state) DO UPDATE SET data = $4",
                ctx.guild.id, trigger, "deny", json.dumps(permission_data)
            )
        await ctx.send_success(f"{state} {type} {target.mention} {'to' if state == 'Added' else 'from'} **deny** permissions for trigger **{trigger}**")

    @autoresponder.command(name="permissions", usage="autoresponder permissions")
    @has_guild_permissions(manage_guild=True)
    async def ar_permissions(self, ctx: EvelinaContext):
        """Shows the allowed and denied users, roles, and channels for all autoresponder triggers"""
        triggers = await self.bot.db.fetch("SELECT DISTINCT trigger FROM autoresponder WHERE guild_id = $1", ctx.guild.id)
        if not triggers:
            return await ctx.send_warning("No autoresponder triggers found for this guild.")
        triggers_with_permissions = []
        for trigger in triggers:
            trigger_name = trigger["trigger"]
            allowed_data = await self.bot.db.fetchval(
                "SELECT data FROM autoresponder_permissions WHERE guild_id = $1 AND trigger = $2 AND state = $3",
                ctx.guild.id, trigger_name, "allow"
            )
            allowed_data = json.loads(allowed_data) if allowed_data else {"users": [], "roles": [], "channels": []}
            denied_data = await self.bot.db.fetchval(
                "SELECT data FROM autoresponder_permissions WHERE guild_id = $1 AND trigger = $2 AND state = $3",
                ctx.guild.id, trigger_name, "deny"
            )
            denied_data = json.loads(denied_data) if denied_data else {"users": [], "roles": [], "channels": []}
            if any([allowed_data["users"], allowed_data["roles"], allowed_data["channels"], denied_data["users"], denied_data["roles"], denied_data["channels"]]):
                triggers_with_permissions.append(trigger)
        trigger_count = len(triggers_with_permissions)
        if trigger_count == 0:
            return await ctx.send_warning("No autoresponder triggers have permissions set")
        embeds = []
        for i in range(0, trigger_count, 3):
            embed = Embed(color=colors.NEUTRAL, title="Autoresponder Permissions")
            embed.set_footer(text=f"Page: {i // 3 + 1}/{(trigger_count // 3) + 1} ({trigger_count} entries)")
            for trigger in triggers_with_permissions[i:i + 3]:
                trigger_name = trigger["trigger"]
                allowed_data = await self.bot.db.fetchval(
                    "SELECT data FROM autoresponder_permissions WHERE guild_id = $1 AND trigger = $2 AND state = $3",
                    ctx.guild.id, trigger_name, "allow"
                )
                allowed_data = json.loads(allowed_data) if allowed_data else {"users": [], "roles": [], "channels": []}
                denied_data = await self.bot.db.fetchval(
                    "SELECT data FROM autoresponder_permissions WHERE guild_id = $1 AND trigger = $2 AND state = $3",
                    ctx.guild.id, trigger_name, "deny"
                )
                denied_data = json.loads(denied_data) if denied_data else {"users": [], "roles": [], "channels": []}
                allowed_users = ", ".join([f"<@{user_id}>" for user_id in allowed_data["users"]]) if allowed_data["users"] else ""
                allowed_roles = ", ".join([f"<@&{role_id}>" for role_id in allowed_data["roles"]]) if allowed_data["roles"] else ""
                allowed_channels = ", ".join([f"<#{channel_id}>" for channel_id in allowed_data["channels"]]) if allowed_data["channels"] else ""
                denied_users = ", ".join([f"<@{user_id}>" for user_id in denied_data["users"]]) if denied_data["users"] else ""
                denied_roles = ", ".join([f"<@&{role_id}>" for role_id in denied_data["roles"]]) if denied_data["roles"] else ""
                denied_channels = ", ".join([f"<#{channel_id}>" for channel_id in denied_data["channels"]]) if denied_data["channels"] else ""
                allowed_str = (f"Allowed: {allowed_users} {allowed_roles} {allowed_channels}")
                denied_str = (f"Denied: {denied_users} {denied_roles} {denied_channels}")
                embed.add_field(name=f"{trigger_name}", value=f"{allowed_str}\n{denied_str}", inline=False)
            embeds.append(embed)
        await ctx.paginator(embeds)
    
    @autoresponder.command(name="clear", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def ar_clear(self, ctx: EvelinaContext):
        """Remove all autoresponders"""
        check = await self.bot.db.fetch("SELECT * FROM autoresponder WHERE guild_id = $1", ctx.guild.id)
        if len(check) == 0:
            return await ctx.send_warning("You have **no** autoresponders in this server")
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM autoresponder WHERE guild_id = $1", interaction.guild.id)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Deleted all autoresponders in this server")
            await interaction.response.edit_message(embed=embed, view=None)
        async def no_callback(interaction: Interaction):
            embed = Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Autoresponders deletion got canceled")
            await interaction.response.edit_message(embed=embed, view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **CLEAR** all autoresponders in this server?", yes_callback, no_callback)

    @autoresponder.command(name="list")
    async def ar_list(self, ctx: EvelinaContext):
        """View a list of auto-reply triggers in guild"""
        results = await self.bot.db.fetch("SELECT * FROM autoresponder WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"No **autoresponders** are set!")
        return await ctx.paginate([f"{result['trigger']}" for result in results], f"Autoresponders", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @group(name="timer", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    async def timer(self, ctx: EvelinaContext):
        """Post repeating messages in your server"""
        return await ctx.create_pages()

    @timer.command(name="add", brief="manage guild", usage="timer add #general 10m {embed}$v{description: Hello world}")
    @has_guild_permissions(manage_guild=True)
    async def timer_add(self, ctx: EvelinaContext, channel: TextChannel, interval: ValidTime, *, code: str):
        """Add repeating message to a channel"""
        if interval < 300:
            return await ctx.send_warning("Interval must be at least 5 minutes")
        check = await self.bot.db.fetchrow("SELECT * FROM timer WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if check:
            return await ctx.send_warning(f"Channel {channel.mention} already has a timed message")
        await self.bot.db.execute(
            "INSERT INTO timer (guild_id, channel_id, interval, code, time) VALUES ($1, $2, $3, $4, $5)",
            ctx.guild.id, channel.id, interval, code, datetime.now().timestamp()
        )
        return await ctx.send_success(f"Added an **auto message** with `{format_timespan(interval)}` interval to {channel.mention}\nYou can preview your message by runnging `{ctx.clean_prefix}timer test #{channel.name}`")
    
    @timer.command(name="remove", brief="manage guild", usage="timer remove #general")
    @has_guild_permissions(manage_guild=True)
    async def timer_remove(self, ctx: EvelinaContext, channel: TextChannel):
        """Remove repeating message from a channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM timer WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if not check:
            return await ctx.send_warning(f"Channel {channel.mention} doesn't have a timed message")
        await self.bot.db.execute("DELETE FROM timer WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        return await ctx.send_success(f"Removed the **auto message** for {channel.mention}")
    
    @timer.command(name="test", brief="manage guild", usage="timer test #general")
    @has_guild_permissions(manage_guild=True)
    async def timer_test(self, ctx: EvelinaContext, channel: TextChannel):
        """Preview a channel's auto message"""
        check = await self.bot.db.fetchrow("SELECT * FROM timer WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if not check:
            return await ctx.send_warning(f"Channel {channel.mention} does not have a timed message")
        channel = self.bot.get_channel(check["channel_id"])
        if channel:
            x = await self.bot.embed_build.alt_convert(ctx.author, check["code"])
            x["allowed_mentions"] = AllowedMentions.all()
            mes = await channel.send(**x)
            return await ctx.send_success(f"Sent the message {mes.jump_url}")
        else:
            return await ctx.send_warning(f"Channel {channel.mention} is not available")
        
    @timer.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def timer_list(self, ctx: EvelinaContext):
        """View all auto messages in your server"""
        results = await self.bot.db.fetch("SELECT * FROM timer WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There is no timed message configured in this server")
        embeds = [
            Embed(color=colors.NEUTRAL, title=f"Timed Messages Configuration")
            .set_footer(text=f"Page: {results.index(result)+1}/{len(results)} ({len(results)} entries)")
            .add_field(name=f"Channel", value=f"{ctx.guild.get_channel(result['channel_id']).mention if ctx.guild.get_channel(result['channel_id']) else 'None'}", inline=True)
            .add_field(name=f"Interval", value=f"{format_timespan(result['interval'])}", inline=True)
            .add_field(name=f"Message", value=f"```{result['code']}```", inline=False)
            for result in results
        ]
        await ctx.paginator(embeds)

    @group(name="buttonmessage", aliases=["buttonmsg"], invoke_without_command=True, case_insensitive=True)
    async def buttonmessage(self, ctx: EvelinaContext):
        """Buttonmessage commands"""
        return await ctx.create_pages()

    @buttonmessage.command(name="add", brief="manage guild", usage="buttonmessage add .../channels/... Rules ✅ green {embed}$v{description: Hello World!}")
    @has_guild_permissions(manage_guild=True)
    async def buttonmessage_add(self, ctx: EvelinaContext, message: ValidMessage, label: str, emoji: str, color: str, *, embed: str):
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
                custom_button = Button(label=label, style=button_style, custom_id=custom_id)
            else:
                custom_emoji = PartialEmoji.from_str(emoji) if emoji.startswith('<:') or emoji.startswith('<a:') else PartialEmoji(name=emoji)
                custom_button = Button(label=label, style=button_style, emoji=custom_emoji, custom_id=custom_id)
            async def button_callback(interaction: Interaction):
                await self.embed_response(interaction, embed)
            custom_button.callback = button_callback
            view.add_item(custom_button)
            await message.edit(view=view)
            await self.bot.db.execute("INSERT INTO button_message (guild_id, channel_id, message_id, button_id, embed, label, emoji) VALUES ($1, $2, $3, $4, $5, $6, $7)", guild_id, channel_id, message_id, custom_button.custom_id, embed, label, emoji)
            await ctx.send_success(f"Added button with embed response [**here**]({message.jump_url})\n```{embed}```")
        except HTTPException as e:
            await ctx.send_warning(f"Failed to create the button\n **Important:** If you don't want to use an emoji, just type `none`")

    @buttonmessage.command(name="edit", brief="manage guild", usage="buttonmessage edit KbJNGwwY {embed}$v{description: Hello World!}")
    @has_guild_permissions(manage_guild=True)
    async def buttonmessage_edit(self, ctx: EvelinaContext, button_id: str, *, embed: str):
        """Edit a button's embed response"""
        check = await self.bot.db.fetchrow("SELECT 1 FROM button_message WHERE guild_id = $1 AND button_id = $2 LIMIT 1", ctx.guild.id, button_id)
        if not check:
            return await ctx.send_warning("Button couldn't be found")
        await self.bot.db.execute("UPDATE button_message SET embed = $1 WHERE guild_id = $2 AND button_id = $3", embed, ctx.guild.id, button_id)
        return await ctx.send_success(f"Button's embed response has been updated to:\n```{embed}```")

    @buttonmessage.command(name="remove", brief="manage guild", usage="buttonmessage remove KbJNGwwY")
    @has_guild_permissions(manage_guild=True)
    async def buttonmessage_remove(self, ctx: EvelinaContext, button_id: str):
        """Remove a specific button from a message by its custom_id"""
        button_exists = await self.bot.db.fetchrow("SELECT 1 FROM button_message WHERE guild_id = $1 AND button_id = $2 LIMIT 1", ctx.guild.id, button_id)
        if not button_exists:
            return await ctx.send_warning(f"Button **{button_id}** couldn't be found")
        guild_id, channel_id, message_id = await self.bot.db.fetchrow("SELECT guild_id, channel_id, message_id FROM button_message WHERE guild_id = $1 AND button_id = $2", ctx.guild.id, button_id)
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send_warning("Could not find this message. I don't have access to this guild.")
        channel = guild.get_channel(channel_id)
        if not channel:
            async def yes_callback(interaction: Interaction) -> None:
                await self.bot.db.execute("DELETE FROM button_message WHERE guild_id = $1 AND button_id = $2", guild_id, button_id)
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
            await self.bot.db.execute("DELETE FROM button_message WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND button_id = $4", guild_id, channel_id, message_id, button_id)
            await ctx.send_success(f"Button **{button_id}** has been removed from this [**message**]({message.jump_url})")
        except HTTPException as e:
            await ctx.send_warning(f"An error occurred while removing the button\n```{e}```")

    @buttonmessage.command(name="clear", brief="manage guild", usage="buttonmessage clear .../channels/...")
    @has_guild_permissions(manage_guild=True)
    async def buttonmessage_clear(self, ctx: EvelinaContext, message: ValidMessage):
        """Remove all buttons from a message"""
        guild_id = message.guild.id
        channel_id = message.channel.id
        message_id = message.id
        button_exists = await self.bot.db.fetchrow("SELECT 1 FROM button_message WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 LIMIT 1", guild_id, channel_id, message_id)
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
                await self.bot.db.execute("DELETE FROM button_message WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", guild_id, channel_id, message_id)
                return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Removed all buttons from this [**message**](https://discord.com/{guild_id}/{channel_id}/{message_id})"), view=None)
            async def no_callback(interaction: Interaction) -> None:
                return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Button roles deletion got canceled."), view=None)
            await ctx.confirmation_send(f"{emojis.QUESTION} Message couldn't be found. However, message still exist in the database.\n> Do you want to remove them?", yes_callback, no_callback)
            return
        async def yes_callback(interaction: Interaction) -> None:
            new_view = View()
            await message.edit(view=new_view)
            await self.bot.db.execute("DELETE FROM button_message WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", guild_id, channel_id, message_id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Removed all buttons from this [**message**]({message.jump_url})"), view=None)
        async def no_callback(interaction: Interaction) -> None:
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Button messages deletion got canceled."), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to clear **all** button messages from this [**message**]({message.jump_url})?", yes_callback, no_callback)

    @buttonmessage.command(name="list")
    async def buttonmessage_list(self, ctx: EvelinaContext):
        """View a list of every button role"""
        results = await self.bot.db.fetch("SELECT * FROM button_message WHERE guild_id = $1", ctx.guild.id)
        if len(results) == 0:
            return await ctx.send_warning("No button messages available for this server")
        button_roles = []
        for result in results:
            emoji_part = f"{result['emoji']} " if result['emoji'] else ""
            button_roles.append(f"{emoji_part}**{result['label']}** (`{result['button_id']}`) [**here**](https://discord.com/channels/{ctx.guild.id}/{result['channel_id']}/{result['message_id']})")
        return await ctx.paginate(button_roles, "Button Messages", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    async def embed_response(self, interaction: Interaction, embed: str):
        x = await self.bot.embed_build.alt_convert(interaction.user, embed)
        if interaction.response.is_done():
            try:
                return await interaction.followup.send(**x, ephemeral=True)
            except HTTPException as e:
                return await interaction.followup.send(f"Failed to send the embed response\n```{e}```", ephemeral=True)
            except Exception:
                pass
        else:
            try:
                return await interaction.response.send_message(**x, ephemeral=True)
            except HTTPException as e:
                return await interaction.response.send_message(f"Failed to send the embed response\n```{e}```", ephemeral=True)
            except Exception:
                pass

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if isinstance(interaction.data, dict) and "custom_id" in interaction.data:
            custom_id = interaction.data["custom_id"]
            if not interaction.guild or not interaction.message:
                return
            try:
                record = await self.bot.db.fetchval("SELECT embed FROM button_message WHERE guild_id = $1 AND message_id = $2 AND button_id = $3", interaction.guild.id, interaction.message.id, custom_id)
                if record:
                    try:
                        await self.embed_response(interaction, record)
                    except Exception:
                        pass
            except Exception:
                pass

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Responders(bot))