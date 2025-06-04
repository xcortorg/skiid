
from discord import Embed, Member, TextChannel, Interaction
from discord.ext.commands import Cog, group, has_guild_permissions, Author

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.converters import NewRoleConverter
from modules.helpers import EvelinaContext

class InviteTracker(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
    
    @group(aliases=["invitetracker", "invt", "it"], invoke_without_command=True, case_insensitive=True)
    async def invites(self, ctx: EvelinaContext, *, member: Member = Author):
        """Returns the number of invites you have in the server"""
        res = await self.bot.db.fetchrow("SELECT * FROM invites_settings WHERE guild_id = $1",ctx.guild.id)
        if not res:
            inv = await ctx.guild.invites()
            invites = sum(invite.uses for invite in inv if invite.inviter == member)
        else:
            inv = await self.bot.db.fetchrow("SELECT * FROM invites WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
            if inv:
                invites = inv['regular_count'] + inv['bonus']
            else:
                invites = 0
        return await ctx.evelina_send(f"{f'{member.mention} has' if member.id != ctx.author.id else 'You have'} **{invites} invites**", emoji="💌")

    @invites.group(name="rewards", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    async def invites_rewards(self, ctx: EvelinaContext):
        """Manage the invite rewards for the server."""
        return await ctx.send_help(ctx.command)

    @invites.command(name="enable", brief="manage guild")
    async def invites_enable(self, ctx: EvelinaContext):
        """Enable invite tracking for the server."""
        res = await self.bot.db.fetchrow("SELECT * FROM invites_settings WHERE guild_id = $1", ctx.guild.id)
        if res:
            return await ctx.send_warning("Invite tracking is already enabled.")
        await self.bot.db.execute("INSERT INTO invites_settings (guild_id) VALUES ($1)", ctx.guild.id)
        return await ctx.send_success("Invite tracking has been enabled.")

    @invites.command(name="disable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def invites_reset(self, ctx: EvelinaContext):
        """Disable the invite tracker"""
        res = await self.bot.db.fetchrow("SELECT * FROM invites_settings WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("Invite tracking is not enabled.")
        async def yes_func(interaction: Interaction):
            tables = ["invites", "invites_users", "invites_settings", "invites_rewards"]
            for table in tables:
                await self.bot.db.execute(f"DELETE FROM {table} WHERE guild_id = $1", ctx.guild.id)
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {interaction.user.mention} Invite data has been reset for the server.", color=colors.SUCCESS), view=None)
        async def no_func(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {interaction.user.mention} Invite settings reset got canceled", color=colors.ERROR), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to reset all invite data for the server?", yes_func, no_func)

    @invites.command(name="fake-threshold", aliases=["ft", "threshold"], brief="manage guild", usage="invites fake-threshold 5")
    @has_guild_permissions(manage_guild=True)
    async def invites_fake_threshold(self, ctx: EvelinaContext, threshold: int):
        """Set the fake invite threshold for the server."""
        res = await self.bot.db.fetchrow("SELECT * FROM invites_settings WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("Invite tracking is not enabled.")
        await self.bot.db.execute("UPDATE invites_settings SET fake_threshold = $1 WHERE guild_id = $2", threshold, ctx.guild.id)
        return await ctx.send_success(f"Accounts younger than **{threshold} days** are now considered fake users.")

    @invites.group(name="bonus", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    async def invites_bonus(self, ctx: EvelinaContext):
        """Manage the bonus invites for the server."""
        return await ctx.create_pages()

    @invites_bonus.command(name="add", brief="manage guild", usage="invites bonus add comminate 5")
    @has_guild_permissions(manage_guild=True)
    async def invites_bonus_add(self, ctx: EvelinaContext, member: Member, bonus: int):
        """Add bonus invites to a user."""
        res = await self.bot.db.fetchrow("SELECT * FROM invites WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        if not res:
            return await ctx.send_warning("This user has not invited anyone.")
        await self.bot.db.execute("UPDATE invites SET bonus = bonus + $1 WHERE guild_id = $2 AND user_id = $3", bonus, ctx.guild.id, member.id)
        return await ctx.send_success(f"{bonus} bonus invites have been added to {member.mention}")

    @invites_bonus.command(name="remove", brief="manage guild", usage="invites bonus remove comminate 5")
    @has_guild_permissions(manage_guild=True)
    async def invites_bonus_remove(self, ctx: EvelinaContext, member: Member, bonus: int):
        """Remove bonus invites from a user."""
        res = await self.bot.db.fetchrow("SELECT * FROM invites WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        if not res:
            return await ctx.send_warning("This user has not invited anyone.")
        await self.bot.db.execute("UPDATE invites SET bonus = bonus - $1 WHERE guild_id = $2 AND user_id = $3", bonus, ctx.guild.id, member.id)
        return await ctx.send_success(f"{bonus} bonus invites have been removed from {member.mention}")

    @invites.command(name="message", aliases=["msg"], brief="manage guild", usage="invites message {inviter.mention} has invited {user.mention} to the server!")
    @has_guild_permissions(manage_guild=True)
    async def invites_message(self, ctx: EvelinaContext, *, message: str):
        """Set the message for the invite tracker."""
        res = await self.bot.db.fetchrow("SELECT * FROM invites_settings WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("Invite tracking is not enabled.")
        if message == "none":
            await self.bot.db.execute("UPDATE invites_settings SET message = NULL WHERE guild_id = $1", ctx.guild.id)
            return await ctx.send_success("Invite message has been removed.")
        else:
            await self.bot.db.execute("UPDATE invites_settings SET message = $1 WHERE guild_id = $2", message, ctx.guild.id)
            return await ctx.send_success(f"Invite message has been updated\n```{message}```")
    
    @invites.command(name="logs", brief="manage guild", usage="invites logs #logs")
    @has_guild_permissions(manage_guild=True)
    async def invites_logs(self, ctx: EvelinaContext, channel: TextChannel):
        """Set the channel for the invite logs."""
        res = await self.bot.db.fetchrow("SELECT * FROM invites_settings WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("Invite tracking is not enabled")
        if channel == "none":
            await self.bot.db.execute("UPDATE invites_settings SET logs = NULL WHERE guild_id = $1", ctx.guild.id)
            return await ctx.send_success("Invite logs channel has been removed")
        else:
            await self.bot.db.execute("UPDATE invites_settings SET logs = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
            return await ctx.send_success(f"Invite logs channel has been updated to {channel.mention}")

    @invites.command(name="leaderboard", aliases=["lb"])
    async def invites_leaderboard(self, ctx: EvelinaContext):
        """Show the invite leaderboard for the server."""
        settings = await self.bot.db.fetch("SELECT * FROM invites_settings WHERE guild_id = $1", ctx.guild.id)
        if not settings:
            return await ctx.send_warning("Invite tracking is not enabled.")
        res = await self.bot.db.fetch("SELECT * FROM invites WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("Nobody invited someone to show a leaderboard.")
        leaderboard = []
        for record in res:
            user = ctx.guild.get_member(record['user_id']) or await self.bot.fetch_user(record['user_id'])
            total = record['regular_count'] + record['bonus']
            leaderboard.append({
                "user": user,
                "total": total,
                "regular": record['regular_count'],
                "left": record['left_count'],
                "fake": record['fake_count'],
                "bonus": record['bonus']
            })
        leaderboard.sort(key=lambda x: x['total'], reverse=True)
        formatted_leaderboard = [
            f"{entry['user'].mention} - **{entry['total']}** invites ({entry['regular']} **regular**, {entry['left']} **left**, {entry['fake']} **fake**, {entry['bonus']} **bonus**)"
            for entry in leaderboard
        ]
        return await ctx.paginate(formatted_leaderboard, "Invite Leaderboard", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @invites.command(name="inviter", aliases=["invited-by"], usage="invites inviter comminate")
    async def inviter(self, ctx: EvelinaContext, member: Member):
        """Show who invited the user to the server."""
        res = await self.bot.db.fetchrow("SELECT * FROM invites_users WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        if not res:
            return await ctx.send_warning("This user was not invited by anyone.")
        inviter = ctx.guild.get_member(res['inviter_id']) or await self.bot.fetch_user(res['inviter_id'])
        return await ctx.evelina_send(f"{member.mention} was invited by {inviter.mention} <t:{res['timestamp']}:R>", emoji="💌")
    
    @invites.command(name="invited", usage="invites invited comminate")
    async def invites_invited(self, ctx: EvelinaContext, member: Member):
        """Returns a list where all users are listed who got invited by the provided user"""
        res = await self.bot.db.fetch("SELECT * FROM invites_users WHERE guild_id = $1 AND inviter_id = $2", ctx.guild.id, member.id)
        if not res:
            return await ctx.send_warning("This user hasn't invited anyone to the server")
        invited_users = []
        for entry in res:
            guild_member = ctx.guild.get_member(entry['user_id'])
            if guild_member:
                invited_users.append(f"<@!{entry['user_id']}> (**{guild_member.name}**)")
            else:
                invited_users.append(f"<@!{entry['user_id']}>")
        await ctx.paginate(invited_users, f"Invited Users by {member.name}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @invites.command(name="code", usage="invites code comminate")
    async def invites_code(self, ctx: EvelinaContext, member: Member = Author):
        """Display all of your or a user's invite codes."""
        invites = await ctx.guild.invites()
        member_invites = [invite for invite in invites if invite.inviter == member]
        if not member_invites:
            return await ctx.send_warning(f"{member.mention} has not created any invites.")
        return await ctx.paginate([f"**{invite.code}** - {invite.uses} uses" for invite in member_invites], f"{member}'s Invite Codes", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @invites_rewards.command(name="add", brief="manage guild", usage="invites rewards add 5 @Inviter")
    @has_guild_permissions(manage_guild=True)
    async def invites_rewards_add(self, ctx: EvelinaContext, threshold: int, role: NewRoleConverter):
        """Add a role reward for the invite tracker."""
        res = await self.bot.db.fetchrow("SELECT * FROM invites_settings WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("Invite tracking is not enabled.")
        existing_reward = await self.bot.db.fetchrow("SELECT * FROM invites_rewards WHERE guild_id = $1 AND threshold = $2", ctx.guild.id, threshold)
        if existing_reward:
            return await ctx.send_warning(f"A reward for **{threshold} invites** already exists.")
        await self.bot.db.execute("INSERT INTO invites_rewards (guild_id, threshold, role_id) VALUES ($1, $2, $3)", ctx.guild.id, threshold, role.id)
        return await ctx.send_success(f"Role reward has been added for **{threshold} invites**")
    
    @invites_rewards.command(name="remove", brief="manage guild", usage="invites rewards remove 5")
    @has_guild_permissions(manage_guild=True)
    async def invites_rewards_remove(self, ctx: EvelinaContext, threshold: int):
        """Remove a role reward for the invite tracker."""
        res = await self.bot.db.fetchrow("SELECT * FROM invites_rewards WHERE guild_id = $1 AND threshold = $2", ctx.guild.id, threshold)
        if not res:
            return await ctx.send_warning("Role reward does not exist.")
        await self.bot.db.execute("DELETE FROM invites_rewards WHERE guild_id = $1 AND threshold = $2", ctx.guild.id, threshold)
        return await ctx.send_success(f"Role reward for **{threshold} invites** has been removed.")

    @invites_rewards.command(name="stack", brief="manage guild", usage="invites rewards stack on")
    @has_guild_permissions(manage_guild=True)
    async def invites_rewards_stack(self, ctx: EvelinaContext, option: str):
        """Toggle the removal of old invite rewards when a new one is added"""
        res = await self.bot.db.fetchrow("SELECT * FROM invites_settings WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("Invite tracking is not enabled.")
        if option.lower() == "on":
            await self.bot.db.execute("UPDATE invites_settings SET autoupdate = $1 WHERE guild_id = $2", True, ctx.guild.id)
            return await ctx.send_success(f"Enabled stacking rewards for invites")
        elif option.lower() == "off":
            await self.bot.db.execute("UPDATE invites_settings SET autoupdate = $1 WHERE guild_id = $2", False, ctx.guild.id)
            return await ctx.send_success(f"Disabled stacking rewards for invites")
        else:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")

    @invites_rewards.command(name="sync", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def invites_rewards_sync(self, ctx: EvelinaContext):
        """Sync the role rewards with the current invites."""
        config = await self.bot.db.fetchrow("SELECT * FROM invites_settings WHERE guild_id = $1", ctx.guild.id)
        if not config:
            return await ctx.send_warning("Invite tracking is not enabled.")
        autoupdate = config['autoupdate']
        rewards = await self.bot.db.fetch("SELECT * FROM invites_rewards WHERE guild_id = $1 ORDER BY threshold ASC", ctx.guild.id)
        if not rewards:
            return await ctx.send_warning("No role rewards have been set.")
        async with ctx.typing():
            for member in ctx.guild.members:
                invite_count = await self.bot.db.fetchval("SELECT (regular_count + bonus) FROM invites WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
                if invite_count is None:
                    continue
                if autoupdate:
                    highest_role = None
                    for reward in rewards:
                        if invite_count >= reward['threshold']:
                            highest_role = ctx.guild.get_role(reward['role_id'])
                    current_roles = {reward['role_id'] for reward in rewards if reward['role_id'] in [role.id for role in member.roles]}
                    for role_id in current_roles:
                        role = ctx.guild.get_role(role_id)
                        if role and role != highest_role:
                            await member.remove_roles(role, reason="Invite reward updated")
                    if highest_role and highest_role not in member.roles:
                        await member.add_roles(highest_role, reason="Invite Tracker Role Reward synced")
                else:
                    for reward in rewards:
                        if invite_count >= reward['threshold']:
                            role = ctx.guild.get_role(reward['role_id'])
                            if role and role not in member.roles:
                                await member.add_roles(role, reason="Invite Tracker Role Reward synced")
        await ctx.send_success("Role rewards have been **synced** with the current invites.")

    @invites_rewards.command(name="list", brief="manage guild")
    async def invites_rewards_list(self, ctx: EvelinaContext):
        """List all the role rewards for the invite tracker."""
        res = await self.bot.db.fetch("SELECT * FROM invites_rewards WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("No role rewards have been set.")
        rewards = []
        for record in res:
            role = ctx.guild.get_role(record['role_id'])
            rewards.append(f"**{record['threshold']}** invites - {role.mention}")
        return await ctx.paginate(rewards, f"Role Rewards ({len(rewards)})", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(InviteTracker(bot))