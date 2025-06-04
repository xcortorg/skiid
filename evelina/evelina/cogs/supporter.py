import json
import string
import random
import datetime
import discord

from discord import User
from discord.ext.commands import Cog, command, group

from typing import Union

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import is_supporter
from modules.economy.functions import EconomyMeasures

class Supporter(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.cash = "💵"
    
    @group(brief="bot supporter", invoke_without_command=True, case_insensitive=True)
    @is_supporter()
    async def donor(self, ctx: EvelinaContext):
        """Donor commands"""
        return await ctx.create_pages()

    @donor.command(name="add", usage="donor add comminate", brief="bot supporter")
    @is_supporter()
    async def donor_add(self, ctx: EvelinaContext, member: User):
        """Add donator perks to a member"""
        check = await self.bot.db.fetchrow("SELECT * FROM donor WHERE user_id = $1", member.id)
        if check:
            return await ctx.send_warning("This member is **already** a donor")
        await self.bot.manage.add_role(member, 1364712418877509774)
        
        await self.bot.db.execute("INSERT INTO donor VALUES ($1, $2, $3)", member.id, datetime.datetime.now().timestamp(), "purchased")
        await self.bot.manage.logging(ctx.author, f"Added **donator** to `{member.name}`", "system")
        return await ctx.send_success(f"{member.mention} can use donator perks now!")
    
    @donor.command(name="remove", usage="donor remove comminate", brief="bot supporter")
    @is_supporter()
    async def donor_remove(self, ctx: EvelinaContext, *, member: User):
        """Remove donator perks from a member"""
        check = await self.bot.db.fetchrow("SELECT * FROM donor WHERE user_id = $1 AND status = $2", member.id, "purchased")
        if not check:
            return await ctx.send_warning("This member can't have their perks removed")
        await self.bot.manage.remove_role(member, 1364712418877509774)
        await self.bot.db.execute("DELETE FROM donor WHERE user_id = $1", member.id)
        await self.bot.manage.logging(ctx.author, f"Removed **donator** from `{member.name}`", "system")
        return await ctx.send_success(f"Removed {member.mention}'s perks")
    
    @group(name="bug", brief="bot supporter", invoke_without_command=True, case_insensitive=True)
    @is_supporter()
    async def bug(self, ctx: EvelinaContext):
        """Bug Hunter commands"""
        return await ctx.create_pages()
    
    @bug.command(name="add", brief="bot supporter", usage="bug add comminate Permission Bug")
    @is_supporter()
    async def bug_add(self, ctx: EvelinaContext, member: User, *, reason: str):
        """Add a bug report to a member"""
        case = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        await self.bot.db.execute("INSERT INTO bugreports VALUES ($1, $2, $3, $4, $5)", case, member.id, ctx.author.id, reason, datetime.datetime.now().timestamp())
        count = await self.bot.db.fetchval("SELECT COUNT(*) FROM bugreports WHERE user_id = $1", member.id)
        if count >= 3:
            await self.bot.manage.add_role(member, 1243745562197626982)
        if count >= 5:
            await self.bot.manage.add_role(member, 1300196517969137754)
        return await ctx.send_success(f"Added a bug to {member.mention} (`#{count}`) - **{reason}**")

    @bug.command(name="remove", brief="bot supporter", usage="bug remove 2kFynXQo")
    @is_supporter()
    async def bug_remove(self, ctx: EvelinaContext, case: str):
        """Remove a bug report from a member"""
        check = await self.bot.db.fetchrow('SELECT * FROM bugreports WHERE "case" = $1', case)
        if not check:
            return await ctx.send_warning(f"Bug report `{case}` doesn't exist")
        await self.bot.db.execute('DELETE FROM bugreports WHERE "case" = $1', case)
        return await ctx.send_success(f"Removed a bug from <@{check['user_id']}> with ID `{case}`")
    
    @bug.command(name="list", brief="bot supporter", usage="bug list comminate")
    @is_supporter()
    async def bug_list(self, ctx: EvelinaContext, *, member: User):
        """List all bugs from a given member"""
        check = await self.bot.db.fetch("SELECT * FROM bugreports WHERE user_id = $1 ORDER BY timestamp DESC", member.id)
        if not check:
            return await ctx.send_warning(f"Couldn't find any bug that got reported from {member.mention}")
        bug_list = [f"**{bug['reason']}** - <t:{bug['timestamp']}:R>\n {emojis.REPLY} `{bug['case']}`" for bug in check]
        await ctx.smallpaginate(bug_list, "Bug Reports", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url})

    @bug.command(name="leaderboard", aliases=["lb"], brief="bot supporter")
    @is_supporter()
    async def bug_leaderboard(self, ctx: EvelinaContext):
        """Display a leaderboard of members with the most bug reports"""
        leaderboard_data = await self.bot.db.fetch("SELECT user_id, COUNT(*) AS bug_count FROM bugreports GROUP BY user_id ORDER BY bug_count DESC")
        if not leaderboard_data:
            return await ctx.send_warning("No bug reports found")
        leaderboard_list = [f"<@{entry['user_id']}> repoted `{entry['bug_count']}` bugs" for entry in leaderboard_data]
        return await ctx.paginate(leaderboard_list, "Bug Report Leaderboard", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url})        

    @group(name="premium", aliases=["prem"], brief="bot supporter", invoke_without_command=True, case_insensitive=True)
    @is_supporter()
    async def premium(self, ctx: EvelinaContext):
        """Premium commands"""
        return await ctx.create_pages()

    @premium.command(name="add", usage="premium add comminate /evelina", brief="bot supporter")
    @is_supporter()
    async def premium_add(self, ctx: EvelinaContext, member: User, invite: Union[discord.Invite, int]):
        """Add premium to a guild"""
        if isinstance(invite, discord.Invite):
            invite = invite.guild.id
        if await self.bot.db.fetchrow("SELECT * FROM premium WHERE guild_id = $1", invite):
            return await ctx.send_warning(f"This guild is **already** premium")
        await self.bot.db.execute("INSERT INTO premium VALUES ($1, $2, $3, $4)", invite, member.id, datetime.datetime.now().timestamp(), 3)
        await self.bot.manage.add_role(member, 1242474452353290291)
        await self.bot.manage.logging(ctx.author, f"Added **premium** subscription to `{member.name}`\n > **Guild ID:** {invite}", "system")
        return await ctx.send_success(f"Premium added to {await self.bot.manage.guild_name(invite, True)}, requested by **{member}**")

    @premium.command(name="remove", usage="premium remove comminate /evelina", brief="bot supporter")
    @is_supporter()
    async def premium_remove(self, ctx: EvelinaContext, invite: Union[discord.Invite, int]):
        """Remove premium from a guild"""
        if isinstance(invite, discord.Invite):
            invite = invite.guild.id
        check = await self.bot.db.fetchrow("SELECT * FROM premium WHERE guild_id = $1", invite)
        if not check:
            return await ctx.send_warning(f"This guild is **not** premium")
        await self.bot.db.execute("DELETE FROM premium WHERE guild_id = $1", invite)
        member = await self.bot.fetch_user(check["user_id"])
        await self.bot.manage.remove_role(member, 1242474452353290291)
        await self.bot.manage.logging(ctx.author, f"Removed **premium** subscription from `{member.name}`\n > **Guild ID:** {invite}", "system")
        return await ctx.send_success(f"Premium removed from {await self.bot.manage.guild_name(invite, True)}")
    
    @premium.command(name="transfer", usage="premium transfer /evelina /bender", brief="bot supporter")
    @is_supporter()
    async def premium_transfer(self, ctx: EvelinaContext, old_inv: Union[discord.Invite, int], new_inv: Union[discord.Invite, int]):
        """Transfer premium from one guild to another"""
        if isinstance(old_inv, discord.Invite):
            old_inv = old_inv.guild.id
        if isinstance(new_inv, discord.Invite):
            new_inv = new_inv.guild.id
        check = await self.bot.db.fetchrow("SELECT * FROM premium WHERE guild_id = $1", old_inv)
        if not check:
            return await ctx.send_warning("The first guild id is **not** premium")
        transfers = check["transfers"]
        if transfers == 0:
            return await ctx.send_warning("This server has ran out of transfers :(")
        await self.bot.db.execute("UPDATE premium SET guild_id = $1, transfers = $2 WHERE guild_id = $3", new_inv, transfers - 1, old_inv)
        await self.bot.manage.logging(ctx.author, f"Transferred **premium** subscription from `{old_inv}` to `{new_inv}`", "system")
        return await ctx.send_success(f"Transferred **premium** subscription from {await self.bot.manage.guild_name(old_inv, True)} to {await self.bot.manage.guild_name(new_inv, True)}\n > **Transfers left:** {transfers-1}")
    
    @premium.command(name="inspect", usage="premium inspect comminate", brief="bot supporter")
    @is_supporter()
    async def premium_inspect(self, ctx: EvelinaContext, user: User):
        """Inspect all premium guilds of a member"""
        premium_guilds = await self.bot.db.fetch("SELECT * FROM premium WHERE user_id = $1", user.id)
        if len(premium_guilds) == 0:
            return await ctx.send_warning(f"{user.mention} doesn't have any premium guilds")
        premium_list = []
        for guild in premium_guilds:
            guild_obj = self.bot.get_guild(guild['guild_id'])
            if guild_obj:
                premium_list.append(f"**{guild_obj.name}** (`{guild['guild_id']}`) - <t:{guild['since']}:R> (`{guild['transfers']}`)")
            else:
                premium_list.append(f"**{guild['guild_id']}** - <t:{guild['since']}:R> (`{guild['transfers']}`)")
        return await ctx.paginate(premium_list, f"Premium Guilds of {user.name}", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url})
    
    @premium.command(name="check", usage="premium check /evelina", brief="bot supporter")
    @is_supporter()
    async def premium_check(self, ctx: EvelinaContext, invite: Union[discord.Invite, int]):
        """Check if a server has premium"""
        if isinstance(invite, discord.Invite):
            invite = invite.guild.id
        check = await self.bot.db.fetchrow("SELECT * FROM premium WHERE guild_id = $1", invite)
        guild = self.bot.get_guild(invite)
        if not check:
            return await ctx.send_warning(f"Guild **{guild.name if guild else invite}** has no **premium**")
        guild = self.bot.get_guild(check['guild_id'])
        return await ctx.send_success(f"Guild **{guild.name if guild else check['guild_id']}** has premium since <t:{check['since']}:R> with **{check['transfers']} transfers** left")
    
    @premium.command(name="list", brief="bot supporter")
    @is_supporter()
    async def premium_list(self, ctx: EvelinaContext):
        """List all premium guilds"""
        premium_guilds = await self.bot.db.fetch("SELECT * FROM premium;")
        if len(premium_guilds) == 0:
            return await ctx.send_warning("There are no premium guilds")
        premium_list = []
        for guild in premium_guilds:
            guild_obj = self.bot.get_guild(guild['guild_id'])
            if guild_obj:
                premium_list.append(f"**{guild_obj.name}** (`{guild['guild_id']}`) - <t:{guild['since']}:R> (`{guild['transfers']}`)")
            else:
                premium_list.append(f"**{guild['guild_id']}** - <t:{guild['since']}:R> (`{guild['transfers']}`)")
        return await ctx.paginate(premium_list, "Premium Guilds", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url})
    
    @command(aliases=["trace"], usage="trace A1Y2Pu", brief="bot supporter")
    @is_supporter()
    async def error(self, ctx: EvelinaContext, code: str):
        """View information about an error code"""
        fl = await self.bot.db.fetch("SELECT * FROM error_codes;")
        error_details = [x for x in fl if x.get("code") == code]
        if len(error_details) == 0 or len(code) != 6:
            return await ctx.send_warning("Please provide a **valid** error code")
        error_details = error_details[0]
        error_details = json.loads(error_details.get("info"))
        guild = self.bot.get_guild(error_details["guild_id"])
        embed = (
            discord.Embed(description=str(error_details["error"]), color=colors.NEUTRAL)
            .add_field(name="Guild", value=f"{guild.name if guild else 'Unknown'}\n`{guild.id if guild else error_details['guild_id']}`", inline=True)
            .add_field(name="Channel", value=f"<#{error_details['channel_id']}>\n`{error_details['channel_id']}`", inline=True)
            .add_field(name="User", value=f"<@{error_details['user_id']}>\n`{error_details['user_id']}`", inline=True)
            .add_field(name="Command", value=f"**{error_details['command']}**")
            .add_field(name="Timestamp", value=f"{error_details['timestamp']}")
            .set_author(name=f"Error Code: {code}")
        )
        return await ctx.send(embed=embed)
    
async def setup(bot: Evelina) -> None:
    await bot.add_cog(Supporter(bot))