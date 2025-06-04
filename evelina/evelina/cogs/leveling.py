import json
import asyncio

from discord import Member, Embed, Interaction, TextChannel, Role, User, HTTPException
from discord.ext.commands import Cog, group, command, BucketType, Author, has_guild_permissions, cooldown

from typing import Union

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import leveling_enabled
from modules.converters import LevelMember, NewRoleConverter

class Leveling(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Leveling commands"

    async def level_replace(self, member: Member, params: str):
        check = await self.bot.db.fetchrow("SELECT * FROM level_user WHERE guild_id = $1 AND user_id = $2", member.guild.id, member.id)
        if not check:
            if "{level}" in params:
                params = params.replace("{level}", "1")
            if "{target_xp}" in params:
                params = params.replace("{target_xp}", "100")
            return params
        if "{level}" in params:
            params = params.replace("{level}", str(check["level"]))
        if "{target_xp}" in params:
            params = params.replace("{target_xp}", str(check["target_xp"]))
        return params
    
    async def update_blacklist(self, ctx: EvelinaContext, column: str, item_id: int, add: bool):
        current_blacklist = await self.bot.db.fetchval(f"SELECT {column} FROM leveling WHERE guild_id = $1", ctx.guild.id)
        current_list = json.loads(current_blacklist) if current_blacklist else []
        if column == "roles":
            item = ctx.guild.get_role(item_id)
            item_mention = item.mention if item else f"{item_id}"
        elif column == "channels":
            item = ctx.guild.get_channel(item_id)
            item_mention = item.mention if item else f"{item_id}"
        elif column == "users":
            item = ctx.guild.get_member(item_id) or await self.bot.fetch_user(item_id)
            item_mention = item.mention if item else f"{item_id}"
        if add:
            if item_id in current_list:
                return await ctx.send_warning(f"This {column[:-1]} is already ignored")
            current_list.append(item_id)
            message = f"Added {column[:-1]} {item_mention} to ignore list"
        else:
            if item_id not in current_list:
                return await ctx.send_warning(f"This {column[:-1]} is not ignored")
            current_list.remove(item_id)
            message = f"Removed {column[:-1]} {item_mention} from the ignore list"
        await self.bot.db.execute(f"UPDATE leveling SET {column} = $1 WHERE guild_id = $2", json.dumps(current_list), ctx.guild.id)
        await ctx.send_success(message)

    @command(name="rank", usage="rank comminate", description="View your level and experience")
    async def rank(self, ctx: EvelinaContext, *, member: Union[Member, User] = Author):
        results = await self.bot.db.fetch("SELECT * FROM level_user WHERE guild_id = $1", ctx.guild.id)
        def sorting(c):
            return c["level"], c["xp"]
        sorted_members = sorted(results, key=sorting, reverse=True)
        user_rank = next((index + 1 for index, m in enumerate(sorted_members) if m['user_id'] == member.id), None)
        if user_rank is None:
            return await ctx.send_warning("This member doesn't have a rank recorded")
        level = next(m for m in sorted_members if m['user_id'] == member.id)
        total_members = len(sorted_members)
        progress_percentage = level['xp'] / level['target_xp']
        progress_bar_length = 10
        filled_length = int(progress_bar_length * progress_percentage)
        empty_length = progress_bar_length - filled_length
        if filled_length == 0:
            progress_bar = f"{emojis.WHITELEFT}{emojis.WHITE * (empty_length - 1)}{emojis.WHITERIGHT}"
        elif filled_length == progress_bar_length:
            progress_bar = f"{emojis.BLUELEFT}{emojis.BLUE * (filled_length - 1)}{emojis.BLUERIGHT}"
        else:
            progress_bar = f"{emojis.BLUELEFT}{emojis.BLUE * (filled_length - 1)}{emojis.WHITE}{emojis.WHITE * (empty_length - 1)}{emojis.WHITERIGHT}"
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="Level", value=f"{level['level']}", inline=True)
        embed.add_field(name="Server Rank", value=f"#{user_rank} out of {total_members}", inline=True)
        embed.add_field(name="Experience", value=f"{level['xp']}/{level['target_xp']} XP", inline=True)
        embed.add_field(name=f"Progress ({progress_percentage*100:.2f}%)", value=progress_bar, inline=False)
        total_experience = self.calculate_total_xp(level["level"], level["xp"])
        embed.set_footer(text=f"Total Experience: {total_experience:,}")
        embed.timestamp = ctx.message.created_at
        return await ctx.send(embed=embed)

    def calculate_total_xp(self, current_level: int, current_xp: float) -> int:
        total_xp = 0
        for level in range(current_level):
            total_xp += int((100 * level + 1) ** 0.9)
        total_xp += int(current_xp)
        return total_xp

    @group(name="level", description="Setup the leveling module", invoke_without_command=True, case_insensitive=True)
    async def level(self, ctx: EvelinaContext, member: Member = Author):
        await ctx.invoke(self.bot.get_command("rank"), member=member)

    @level.command(name="test", brief="manage guild", description="View the level up message for the server")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_test(self, ctx: EvelinaContext):
        res = await self.bot.db.fetchrow("SELECT * FROM leveling WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("Leveling is not configured for this server.")
        channel = ctx.guild.get_channel(res["channel_id"]) or ctx.channel
        embed = res["message"]
        x = await self.bot.embed_build.convert(ctx, await self.level_replace(ctx.author, embed))
        try:
            mes = await channel.send(**x)
            return await ctx.send_success(f"Sent the message {mes.jump_url}")
        except Exception as e:
            return await ctx.send_warning(f"An error occurred while sending the message\n```{e}```")

    @level.command(name="enable", brief="manage guild", description="Enable the leveling system")
    @has_guild_permissions(manage_guild=True)
    async def level_enable(self, ctx: EvelinaContext):
        if await self.bot.db.fetchrow("SELECT * FROM leveling WHERE guild_id = $1", ctx.guild.id):
            return await ctx.send_warning("Leveling system is **already** enabled")
        await self.bot.db.execute("INSERT INTO leveling (guild_id, message) VALUES ($1,$2)", ctx.guild.id, "Good job, {user}! You leveled up to **Level {level}**")
        return await ctx.send_success("Enabled the leveling system")

    @level.command(name="disable", brief="manage guild", description="Disable the leveling system")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_disable(self, ctx: EvelinaContext):
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM leveling WHERE guild_id = $1", interaction.guild.id)
            await interaction.client.db.execute("DELETE FROM level_user WHERE guild_id = $1", interaction.guild.id)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Disabled the leveling system")
            await interaction.response.edit_message(embed=embed, view=None)
        async def no_callback(interaction: Interaction):
            embed = Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Leveling system deactivation got canceled")
            await interaction.response.edit_message(embed=embed, view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **reset** the leveling system? This will reset the level statistics aswell", yes_callback, no_callback)

    @level.command(name="channel", brief="manage guild", usage="level channel #levels", description="Set a channel for the level up messages")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_channel(self, ctx: EvelinaContext, *, channel: Union[TextChannel, str]):
        if channel == "any":
            args = ["UPDATE leveling SET channel_id = $1 WHERE guild_id = $2", None, ctx.guild.id]
            message = "Level up messages are going to be sent in any channel"
        elif channel == "dm":
            args = ["UPDATE leveling SET channel_id = $1 WHERE guild_id = $2", 0, ctx.guild.id]
            message = "Level up messages are going to be sent in DMs"
        elif isinstance(channel, TextChannel):
            args = ["Update leveling SET channel_id = $1 WHERE guild_id = $2", channel.id, ctx.guild.id]
            message = f"Level up messages are going to be sent in {channel.mention}"
        else:
            return await ctx.send_warning("Invalid channel option. Valid options are: `any`, `dm`, or a valid channel mention")
        await self.bot.db.execute(*args)
        return await ctx.send_success(message)

    @level.command(name="message", brief="manage guild", usage="level message {user}, you leveled up", description="Set a custom level up message")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_message(self, ctx: EvelinaContext, *, message: str = "Good job, {user}! You leveled up to **Level {level}**",):
        if message.lower().strip() == "none":
            await self.bot.db.execute("UPDATE leveling SET message = $1 WHERE guild_id = $2", "none", ctx.guild.id)
            return await ctx.send_success(f"Removed the **level up** message")
        await self.bot.db.execute("UPDATE leveling SET message = $1 WHERE guild_id = $2", message, ctx.guild.id)
        return await ctx.send_success(f"Level up message configured to:\n```{message}```")

    @level.command(name="booster", brief="manage guild", usage="level booster 2", description="Set the multiplier for boosters")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_booster(self, ctx: EvelinaContext, multiplier: float):
        if multiplier not in (0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3):
            return await ctx.send_warning(f"Multiplier can only be `0.25`, `0.50`, `0.75`, `1.00`, `1.25`, `1.50`, `1.75`, `2.00`, `2.25`, `2.50`, `2.75` or `3.00`")
        await self.bot.db.execute("UPDATE leveling SET booster = $1 WHERE guild_id = $2", multiplier, ctx.guild.id)
        return await ctx.send_success(f"Set the booster multiplier to **{multiplier:.2f}**")
    
    @level.command(name="multiplier", brief="manage guild", usage="level multiplier 2", description="Set the multiplier for the leveling system")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_multiplier(self, ctx: EvelinaContext, multiplier: float):
        if multiplier not in (0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3):
            return await ctx.send_warning(f"Multiplier can only be `0.25`, `0.50`, `0.75`, `1.00`, `1.25`, `1.50`, `1.75`, `2.00`, `2.25`, `2.50`, `2.75` or `3.00`")
        await self.bot.db.execute("UPDATE leveling SET multiplier = $1 WHERE guild_id = $2", multiplier, ctx.guild.id)
        return await ctx.send_success(f"Set the multiplier to **{multiplier:.2f}**")
    
    @level.group(name="rolemultiplier", aliases=["rmulti", "rmultiplier"], description="Manage the role multipliers", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_rolemultiplier(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @level_rolemultiplier.command(name="add", brief="manage guild", usage="level rolemultiplier add Vanity 3", description="Add or update a role multiplier")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_rolemultiplier_add(self, ctx: EvelinaContext, role: Role, multiplier: float):
        if multiplier not in (0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3):
            return await ctx.send_warning(f"Multiplier can only be `0.25`, `0.50`, `0.75`, `1.00`, `1.25`, `1.50`, `1.75`, `2.00`, `2.25`, `2.50`, `2.75` or `3.00`")
        await self.bot.db.execute(
            "INSERT INTO level_multiplier (guild_id, role_id, multiplier) VALUES ($1, $2, $3) "
            "ON CONFLICT (guild_id, role_id) DO UPDATE SET multiplier = $3",
            ctx.guild.id, role.id, multiplier
        )
        return await ctx.send_success(f"Set the multiplier for role **{role.name}** to **{multiplier:.2f}**")

    @level_rolemultiplier.command(name="remove", brief="manage guild", usage="level rolemultiplier remove Vanity", description="Remove a role multiplier")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_rolemultiplier_remove(self, ctx: EvelinaContext, role: Role):
        result = await self.bot.db.fetchrow("SELECT * FROM level_multiplier WHERE guild_id = $1 AND role_id = $2",  ctx.guild.id, role.id)
        if not result:
            return await ctx.send_warning(f"No multiplier found for role **{role.name}**.")
        await self.bot.db.execute("DELETE FROM level_multiplier WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        return await ctx.send_success(f"Removed the multiplier for role **{role.mention}**")
    
    @level.group(name="voice", aliases=["manage guild"], description="Manage voice mulipliers for leveling system")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_voice(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @level_voice.command(name="booster", brief="manage guild", usage="level voice booster 2", description="Set the voice multiplier for boosters", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_voice_booster(self, ctx: EvelinaContext, multiplier: float):
        if multiplier not in (0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3):
            return await ctx.send_warning(f"Multiplier can only be `0.25`, `0.50`, `0.75`, `1.00`, `1.25`, `1.50`, `1.75`, `2.00`, `2.25`, `2.50`, `2.75` or `3.00`")
        await self.bot.db.execute("UPDATE leveling SET voice_booster = $1 WHERE guild_id = $2", multiplier, ctx.guild.id)
        return await ctx.send_success(f"Set the booster voice multiplier to **{multiplier:.2f}**")
    
    @level_voice.command(name="multiplier", brief="manage guild", usage="level voice multiplier 2", description="Set the voice multiplier for the leveling system")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_voice_multiplier(self, ctx: EvelinaContext, multiplier: float):
        if multiplier not in (0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3):
            return await ctx.send_warning(f"Multiplier can only be `0.25`, `0.50`, `0.75`, `1.00`, `1.25`, `1.50`, `1.75`, `2.00`, `2.25`, `2.50`, `2.75` or `3.00`")
        await self.bot.db.execute("UPDATE leveling SET voice_multiplier = $1 WHERE guild_id = $2", multiplier, ctx.guild.id)
        return await ctx.send_success(f"Set the voice multiplier to **{multiplier:.2f}**")
    
    @level_voice.group(name="rolemultiplier", brief="manage guild", aliases=["rmulti", "rmultiplier"], description="Manage the role voice multipliers", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_voice_rolemultiplier(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @level_voice_rolemultiplier.command(name="add", brief="manage guild", usage="level voice rolemultiplier add Vanity 3")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_voice_rolemultiplier_add(self, ctx: EvelinaContext, role: Role, multiplier: float):
        """Add or update a role voice multiplier"""
        if multiplier not in (0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3):
            return await ctx.send_warning(f"Multiplier can only be `0.25`, `0.50`, `0.75`, `1.00`, `1.25`, `1.50`, `1.75`, `2.00`, `2.25`, `2.50`, `2.75` or `3.00`")
        await self.bot.db.execute(
            "INSERT INTO level_multiplier_voice (guild_id, role_id, multiplier) VALUES ($1, $2, $3) "
            "ON CONFLICT (guild_id, role_id) DO UPDATE SET multiplier = $3",
            ctx.guild.id, role.id, multiplier
        )
        return await ctx.send_success(f"Set the multiplier for role **{role.name}** to **{multiplier:.2f}**")

    @level_voice_rolemultiplier.command(name="remove", brief="manage guild", usage="level voice rolemultiplier remove Vanity")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_voice_rolemultiplier_remove(self, ctx: EvelinaContext, role: Role):
        """Remove a role voice multiplier"""
        result = await self.bot.db.fetchrow("SELECT * FROM level_multiplier_voice WHERE guild_id = $1 AND role_id = $2",  ctx.guild.id, role.id)
        if not result:
            return await ctx.send_warning(f"No voice multiplier found for role **{role.name}**")
        await self.bot.db.execute("DELETE FROM level_multiplier_voice WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        return await ctx.send_success(f"Removed the voice multiplier for role **{role.mention}**")

    @level.command(name="multipliers", aliases=["multis"], description="Displays the current multipliers for the server")
    @leveling_enabled()
    async def level_multipliers(self, ctx: EvelinaContext):
        res = await self.bot.db.fetchrow("SELECT * FROM leveling WHERE guild_id = $1", ctx.guild.id)
        if res:
            global_multiplier = res['multiplier'] if res.get("multiplier") else 1
            booster_multiplier = res['booster'] if res.get("booster") else 1
        else:
            global_multiplier = 1
            booster_multiplier = 1
        role_multipliers = await self.bot.db.fetch("SELECT role_id, multiplier FROM level_multiplier WHERE guild_id = $1", ctx.guild.id)
        voice_res = await self.bot.db.fetchrow("SELECT * FROM leveling WHERE guild_id = $1", ctx.guild.id)
        if res:
            global_voice_multiplier = voice_res['voice_multiplier'] if voice_res.get("voice_multiplier") else 1
            booster_voice_multiplier = voice_res['voice_booster'] if voice_res.get("voice_booster") else 1
        else:
            global_voice_multiplier = 1
            booster_voice_multiplier = 1
        role_voice_multipliers = await self.bot.db.fetch("SELECT role_id, multiplier FROM level_multiplier_voice WHERE guild_id = $1", ctx.guild.id)
        embed = Embed(title="Multipliers for Server", color=colors.NEUTRAL)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.add_field(name="Global Multiplier", value=f"{global_multiplier:.2f}", inline=True)
        embed.add_field(name="Booster Multiplier", value=f"{booster_multiplier:.2f}", inline=True)
        if role_multipliers:
            role_multiplier_str = ""
            for role in role_multipliers:
                role_id = role['role_id']
                multiplier = role['multiplier']
                role_obj = ctx.guild.get_role(role_id)
                if role_obj:
                    role_multiplier_str += f"{role_obj.mention} - {multiplier:.2f}\n"
                else:
                    role_multiplier_str += f"**{role_id}** - {multiplier:.2f}\n"
            embed.add_field(name="Role Multipliers", value=role_multiplier_str, inline=False)
        else:
            embed.add_field(name="Role Multipliers", value="No role multipliers set.", inline=False)
        embed.add_field(name="Global Voice Multiplier", value=f"{global_voice_multiplier:.2f}", inline=True)
        embed.add_field(name="Booster Voice Multiplier", value=f"{booster_voice_multiplier:.2f}", inline=True)
        if role_voice_multipliers:
            role_voice_multiplier_str = ""
            for role in role_voice_multipliers:
                role_id = role['role_id']
                multiplier = role['multiplier']
                role_obj = ctx.guild.get_role(role_id)
                if role_obj:
                    role_voice_multiplier_str += f"{role_obj.mention} - {multiplier:.2f}\n"
                else:
                    role_voice_multiplier_str += f"**{role_id}** - {multiplier:.2f}\n"
            embed.add_field(name="Role Voice Multipliers", value=role_voice_multiplier_str, inline=False)
        else:
            embed.add_field(name="Role Voice Multipliers", value="No role voice multipliers set.", inline=False)
        await ctx.send(embed=embed)

    @level.command(name="config", aliases=["settings", "stats", "statistics", "status"], brief="manage guild", description="Check the settings for the leveling system")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_config(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM leveling WHERE guild_id = $1", ctx.guild.id)
        voice_leveling = await self.bot.db.fetchval("SELECT level_state FROM voicetrack_settings WHERE guild_id = $1", ctx.guild.id)
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name=f"{ctx.guild.name}'s Leveling Config", icon_url=ctx.guild.icon)
        embed.add_field(name="Channel", value=ctx.guild.get_channel(check["channel_id"]) if ctx.guild.get_channel(check["channel_id"]) else emojis.DENY)
        embed.add_field(name="Stackroles", value=emojis.APPROVE if check["stack"] else emojis.DENY)
        embed.add_field(name="Voice Level", value=emojis.APPROVE if voice_leveling else emojis.DENY)
        embed.add_field(name="Message", value=check["message"], inline=False)
        await ctx.send(embed=embed)

    @level.command(name="set", brief="manage guild", usage="level set comminate 15", description="Set a user's level")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_set(self, ctx: EvelinaContext, member: LevelMember, level: int):
        if member is None:
            return await ctx.send_warning(f"Member **{member}** couldn't be found")
        if level < 1:
            return await ctx.send_warning("The level can't be **lower** than 0")
        if level > 1000:
            return await ctx.send_warning("The level can't be **higher** than 1,000")
        if await self.bot.db.fetchrow("SELECT * FROM level_user WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id):
            await self.bot.db.execute("UPDATE level_user SET xp = $1, target_xp = $2, level = $3 WHERE guild_id = $4 AND user_id = $5", 0, int((100 * level + 1) ** 0.9), level, ctx.guild.id, member.id)
        else:
            await self.bot.db.execute("INSERT INTO level_user VALUES ($1,$2,$3,$4,$5)", ctx.guild.id, member.id, 0, level, int((100 * level + 1) ** 0.9))
        await ctx.send_success(f"Set the level for {member.mention} to **Level {level}**")
        await self.sync_user_roles(ctx.guild, member, level)

    async def sync_user_roles(self, guild, member, user_level):
        stack_status = await self.bot.db.fetchval("SELECT stack FROM leveling WHERE guild_id = $1", guild.id)
        level_rewards = await self.bot.db.fetch("SELECT level, role_id FROM level_rewards WHERE guild_id = $1", guild.id)
        if not level_rewards:
            return
        level_rewards_dict = {}
        for reward in level_rewards:
            level_rewards_dict.setdefault(reward['level'], []).append(reward['role_id'])
        
        min_level_reward = min(level_rewards_dict.keys(), default=None)
        if user_level < min_level_reward:
            roles_to_remove = [
                guild.get_role(role_id)
                for role_ids in level_rewards_dict.values()
                for role_id in role_ids
                if guild.get_role(role_id) in member.roles
            ]
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove, reason="Removing level rewards for low-level user")
                except HTTPException:
                    pass
            return
        if stack_status:
            roles_to_add = [
                guild.get_role(role_id)
                for level, role_ids in level_rewards_dict.items()
                if level <= user_level
                for role_id in role_ids
                if guild.get_role(role_id) not in member.roles
            ]
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Syncing level rewards after level set")
                except HTTPException:
                    pass
        else:
            highest_level = max((lvl for lvl in level_rewards_dict if lvl <= user_level), default=None)
            if highest_level:
                highest_role = guild.get_role(level_rewards_dict[highest_level][0])
                roles_to_remove = [
                    role for level, role_ids in level_rewards_dict.items()
                    if level < highest_level
                    for role_id in role_ids
                    for role in member.roles if role.id == role_id
                ]
                if roles_to_remove:
                    try:
                        await member.remove_roles(*roles_to_remove, reason="Removing old level rewards")
                    except HTTPException:
                        pass
                if highest_role and highest_role not in member.roles:
                    try:
                        await member.add_roles(highest_role, reason="Syncing highest level reward after level set")
                    except HTTPException:
                        pass

    @level.command(name="reset", brief="manage guild", usage="level reset comminate", description="Reset a user's level and XP")
    @has_guild_permissions(manage_guild=True)
    @leveling_enabled()
    async def level_reset(self, ctx: EvelinaContext, *, member: Member = None):
        async def no_callback(interaction: Interaction):
            embed = Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Leveling system reset got canceled")
            await interaction.response.edit_message(embed=embed, view=None)
        if member is None:
            async def yes_callback(interaction: Interaction):
                await interaction.client.db.execute("DELETE FROM level_user WHERE guild_id = $1", interaction.guild.id)
                return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Reset level statistics for **all** members"), view=None)
            mes = f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **reset** level statistics for everyone in this server?"
        else:
            member = await LevelMember().convert(ctx, str(member.id))
            async def yes_callback(interaction: Interaction):
                await interaction.client.db.execute("DELETE FROM level_user WHERE guild_id = $1 AND user_id = $2", interaction.guild.id, member.id)
                return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Reset level statistics for {member.mention}"), view=None)
            mes = f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **reset** level statistics for {member.mention} in this server?"
        await ctx.confirmation_send(mes, yes_callback, no_callback)

    @level.command(name="leaderboard", aliases=["lb"], description="View the highest-ranking members")
    @leveling_enabled()
    async def level_leaderboard(self, ctx: EvelinaContext):
        results = await self.bot.db.fetch("SELECT * FROM level_user WHERE guild_id = $1", ctx.guild.id)
        server_member_ids = {member.id for member in ctx.guild.members}
        filtered_results = [m for m in results if m["user_id"] in server_member_ids]
        def sorting(c):
            return c["level"], c["xp"]
        members = sorted(filtered_results, key=sorting, reverse=True)
        if not filtered_results:
            return await ctx.send_warning("No members have been ranked yet.")
        leaderboard_entries = [f"**{self.bot.get_user(m['user_id']) or m['user_id']}** has level **{m['level']}** (`{m['xp']:,}`/`{m['target_xp']:,}`)" for m in members]
        await ctx.paginate(leaderboard_entries, "Level leaderboard", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @level.group(name="rewards", brief="manage guild", description="Manage the rewards for leveling up", invoke_without_command=True, case_insensitive=True)
    @leveling_enabled()
    async def level_rewards(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @level_rewards.command(name="add", brief="manage guild", usage="level rewards add 15 gang", description="Assign a reward role to a level")
    @has_guild_permissions(manage_guild=True)
    async def level_rewards_add(self, ctx: EvelinaContext, level: int, *, role: NewRoleConverter):
        if level < 0:
            return await ctx.send_warning("Level can't be lower than 0")
        if check := await self.bot.db.fetchrow("SELECT * FROM level_rewards WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id):
            return await ctx.send_warning(f"This role is **already** a reward for **Level {check['level']}**")
        await self.bot.db.execute("INSERT INTO level_rewards VALUES ($1,$2,$3)", ctx.guild.id, level, role.id)
        return await ctx.send_success(f"Added {role.mention} as a reward for reaching **Level {level}**")

    @level_rewards.command(name="remove", brief="manage guild", usage="level rewards remove gang", description="Remove a reward from a level")
    @has_guild_permissions(manage_guild=True)
    async def level_rewards_remove(self, ctx: EvelinaContext, *, role: NewRoleConverter):
        if check := await self.bot.db.fetchrow("SELECT * FROM level_rewards WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id):
            await self.bot.db.execute("DELETE FROM level_rewards WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
            return await ctx.send_success(f"Removed a reward for reaching **Level {check['level']}**")
        return await ctx.send_warning("This role is **not** a reward for any level")

    @level_rewards.command(name="reset", brief="manage guild", description="Remove every reward that was added")
    @has_guild_permissions(manage_guild=True)
    async def level_rewards_reset(self, ctx: EvelinaContext):
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM level_rewards WHERE guild_id = $1", interaction.guild.id)
            await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Removed every reward that was saved in this server"), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Leveling reward deletion got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure that you want to **remove** every reward saved in this server?", yes_callback, no_callback)

    @level_rewards.command(name="list", description="Get a list of every role reward in this server")
    async def level_rewards_list(self, ctx: EvelinaContext):
        check = await self.bot.db.fetch("SELECT role_id, level FROM level_rewards WHERE guild_id = $1", ctx.guild.id)
        roles = sorted(check, key=lambda c: c["level"])
        if not roles:
            await ctx.send_warning("There are no level rewards set")
            return
        await ctx.paginate([f"{ctx.guild.get_role(r['role_id']).mention} for **Level {r['level']}**" for r in roles], f"Level rewards", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @level_rewards.command(name="stack", brief="manage guild", usage="level rewards stack on", description="Toggle stacking rewards for leveling up")
    @has_guild_permissions(manage_guild=True)
    async def level_rewards_stack(self, ctx: EvelinaContext, option: str):
        if option == "off":
            await self.bot.db.execute("UPDATE leveling SET stack = $1 WHERE guild_id = $2", False, ctx.guild.id)
            return await ctx.send_success("Disabled stacking rewards for leveling up")
        elif option == "on":
            await self.bot.db.execute("UPDATE leveling SET stack = $1 WHERE guild_id = $2", True, ctx.guild.id)
            return await ctx.send_success("Enabled stacking rewards for leveling up")
        else:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")

    @level_rewards.command(name="sync", brief="manage guild", description="Sync all user's roles based on their levels")
    @has_guild_permissions(manage_guild=True)
    @cooldown(1, 3600, BucketType.guild)
    async def level_rewards_sync(self, ctx: EvelinaContext):
        guild = ctx.guild
        level_rewards = await self.bot.db.fetch("SELECT level, role_id FROM level_rewards WHERE guild_id = $1", guild.id)
        if not level_rewards:
            return await ctx.send_warning("There are no level rewards configured for this server")
        level_rewards_dict = {}
        for reward in level_rewards:
            level_rewards_dict.setdefault(reward['level'], []).append(reward['role_id'])
        min_level_reward = min(level_rewards_dict.keys())
        users_levels = await self.bot.db.fetch("SELECT user_id, level FROM level_user WHERE guild_id = $1", guild.id)
        if not users_levels:
            return await ctx.send_warning("No user levels found for this server.")
        loading_message = await ctx.send_loading("Synchronizing all users roles with their levels...")
        batch_size = 5
        delay_between_batches = 2
        for i in range(0, len(users_levels), batch_size):
            batch = users_levels[i:i + batch_size]
            for user_data in batch:
                user_id = user_data['user_id']
                user_level = user_data['level']
                member = guild.get_member(user_id)
                if not member:
                    continue
                stack_status = await self.bot.db.fetchval("SELECT stack FROM leveling WHERE guild_id = $1", guild.id)
                if user_level < min_level_reward:
                    roles_to_remove = [
                        guild.get_role(role_id)
                        for role_ids in level_rewards_dict.values()
                        for role_id in role_ids
                        if guild.get_role(role_id) in member.roles
                    ]
                    if roles_to_remove:
                        try:
                            await member.remove_roles(*roles_to_remove, reason="Removing level rewards for low-level user")
                        except HTTPException:
                            pass
                    continue
                if stack_status:
                    roles_to_add = [
                        guild.get_role(role_id)
                        for level, role_ids in level_rewards_dict.items()
                        if level <= user_level
                        for role_id in role_ids
                        if guild.get_role(role_id) not in member.roles
                    ]
                    if roles_to_add:
                        try:
                            await member.add_roles(*roles_to_add, reason="Syncing level rewards")
                        except HTTPException:
                            pass
                else:
                    highest_level = max((lvl for lvl in level_rewards_dict if lvl <= user_level), default=None)
                    if highest_level:
                        highest_role = guild.get_role(level_rewards_dict[highest_level][0])
                        if highest_role and highest_role not in member.roles:
                            await member.add_roles(highest_role, reason="Syncing highest level reward")
                        roles_to_remove = [
                            guild.get_role(role_id)
                            for level, role_ids in level_rewards_dict.items()
                            if level < highest_level
                            for role_id in role_ids
                            if guild.get_role(role_id) in member.roles
                        ]
                        if roles_to_remove:
                            try:
                                await member.remove_roles(*roles_to_remove, reason="Removing old level rewards")
                            except HTTPException:
                                pass
                await asyncio.sleep(delay_between_batches)
        embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {ctx.author.mention}: All users roles have been synchronized based on their levels")
        await loading_message.edit(embed=embed)

    @level.group(name="ignore", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def level_ignore(self, ctx: EvelinaContext):
        """Manage the XP ignore list"""
        return await ctx.create_pages()

    @level_ignore.command(name="add", brief="manage guild", usage="level ignore add comminate")
    @has_guild_permissions(manage_guild=True)
    async def level_ignore_add(self, ctx: EvelinaContext, target: Union[User, Role, TextChannel]):
        """Add a user, role or channel to the XP ignore list"""
        if isinstance(target, User):
            await self.update_blacklist(ctx, "users", target.id, add=True)
        elif isinstance(target, Role):
            await self.update_blacklist(ctx, "roles", target.id, add=True)
        elif isinstance(target, TextChannel):
            await self.update_blacklist(ctx, "channels", target.id, add=True)

    @level_ignore.command(name="remove", brief="manage guild", usage="level ignore remove comminate")
    @has_guild_permissions(manage_guild=True)
    async def level_ignore_remove(self, ctx: EvelinaContext, target: Union[User, Role, TextChannel]):
        """Remove a user, role or channel from the XP ignore list"""
        if isinstance(target, User):
            await self.update_blacklist(ctx, "users", target.id, add=False)
        elif isinstance(target, Role):
            await self.update_blacklist(ctx, "roles", target.id, add=False)
        elif isinstance(target, TextChannel):
            await self.update_blacklist(ctx, "channels", target.id, add=False)

    @level_ignore.command(name="command", brief="manage guild", usage="level ignore command on")
    @has_guild_permissions(manage_guild=True)
    async def level_ignore_command(self, ctx: EvelinaContext, option: str):
        """Enable or disable the option to exclude commands from the leveling system"""
        if option.lower() == "on":
            await self.bot.db.execute("UPDATE leveling SET command = $1 WHERE guild_id = $2", True, ctx.guild.id)
            return await ctx.send_success("Commands now ignored for leveling")
        elif option.lower() == "off":
            await self.bot.db.execute("UPDATE leveling SET command = $1 WHERE guild_id = $2", False, ctx.guild.id)
            return await ctx.send_success("Command not ignored for leveling anymore")
        else:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")

    @level_ignore.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def level_ignore_list(self, ctx: EvelinaContext):
        """View the XP ignore list"""
        categories = ["users", "roles", "channels"]
        content = []
        for column in categories:
            current_blacklist = await self.bot.db.fetchval(f"SELECT {column} FROM leveling WHERE guild_id = $1", ctx.guild.id)
            current_list = json.loads(current_blacklist) if current_blacklist else []
            if current_list:
                if column == "users":
                    content.extend([f"<@{item_id}>" for item_id in current_list])
                elif column == "roles":
                    content.extend([f"<@&{item_id}>" for item_id in current_list])
                elif column == "channels":
                    content.extend([f"<#{item_id}>" for item_id in current_list])
        if not content:
            await ctx.send_warning("No users, roles, or channels are ignored for XP")
            return
        await ctx.paginate(content, "Level Blacklisted", {
            "name": ctx.guild.name,
            "icon_url": ctx.guild.icon.url if ctx.guild.icon else None
        })

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Leveling(bot))