import datetime

from discord import User, Guild, Embed, Invite
from discord.ext.commands import Cog, command, group

from decimal import Decimal
from typing import Union, Optional

from modules.styles import colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import is_moderator, is_manager
from modules.converters import Amount
from modules.validators import ValidCommand, ValidTime, ValidCog
from modules.economy.functions import EconomyMeasures

class Moderator(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.cash = "💵"
        self.economy = EconomyMeasures(self.bot)

    @command(usage="anowner 1228371886690537624 comminate", brief="bot moderator")
    @is_moderator()
    async def anowner(self, ctx: EvelinaContext, guild: Guild, member: User):
        """Change the antinuke owner of a guild"""
        if await self.bot.db.fetchrow("SELECT * FROM antinuke WHERE guild_id = $1", guild.id):
            await self.bot.db.execute("UPDATE antinuke SET owner_id = $1 WHERE guild_id = $2", member.id, guild.id)
        else:
            await self.bot.db.execute("INSERT INTO antinuke (guild_id, configured, owner_id) VALUES ($1,$2,$3)", guild.id, "false", member.id)
        return await ctx.send_success(f"{member.mention} is the **new** antinuke owner for **{guild.name}**")

    @group(brief="bot moderator", invoke_without_command=True, case_insensitive=True)
    @is_manager()
    async def money(self, ctx: EvelinaContext):
        """Money commands"""
        return await ctx.create_pages()

    @money.command(name="add", usage="money add cash comminate 125", brief="bot manager")
    @is_manager()
    async def money_add(self, ctx: EvelinaContext, type: str, user: User, amount: Amount):
        """Add money to a given economy user"""
        if type not in ["cash", "card"]:
            return await ctx.send_warning("Please specify either 'cash' or 'card'.")
        check = await self.bot.db.fetchrow("SELECT cash, card FROM economy WHERE user_id = $1", user.id)
        if check is None:
            return await ctx.send_warning(f"**{user.name}** not found in the economy database.")
        new_amount = round(check[type] + amount, 2)
        await self.bot.db.execute(f"UPDATE economy SET {type} = $1 WHERE user_id = $2", new_amount, user.id)
        await self.bot.manage.logging(ctx.author, f"Added **{self.bot.misc.humanize_number(amount)}** {self.cash} {type} to {user.mention} (`{user.id}`)", "money")
        await self.economy.logging(user, Decimal(amount), "added", type)
        return await ctx.send_success(f"Added **{self.bot.misc.humanize_number(amount)}** {self.cash} {type} to {user.mention}")

    @money.command(name="remove", usage="money remove cash comminate 125", brief="bot manager")
    @is_manager()
    async def money_remove(self, ctx: EvelinaContext, type: str, user: User, amount: Amount):
        """Remove money from a given economy user"""
        if type not in ["cash", "card"]:
            return await ctx.send_warning("Please specify either 'cash' or 'card'.")
        check = await self.bot.db.fetchrow("SELECT cash, card FROM economy WHERE user_id = $1", user.id)
        if check is None:
            return await ctx.send_warning(f"**{user.name}** not found in the economy database.")
        new_amount = round(check[type] - amount, 2)
        if new_amount < 0:
            return await ctx.send_warning(f"**{user.name}** does not have enough {type}.")
        await self.bot.db.execute(f"UPDATE economy SET {type} = $1 WHERE user_id = $2", new_amount, user.id)
        await self.bot.manage.logging(ctx.author, f"Removed **{self.bot.misc.humanize_number(amount)}** {self.cash} {type} from {user.mention} (`{user.id}`)", "money")
        await self.economy.logging(user, Decimal(amount), "removed", type)
        return await ctx.send_success(f"Removed **{self.bot.misc.humanize_number(amount)}** {self.cash} {type} from {user.mention}")

    @money.command(name="set", usage="money set cash comminate 125", brief="bot moderator")
    @is_manager()
    async def money_set(self, ctx: EvelinaContext, type: str, user: User, amount: Amount):
        """Set the money of a given economy user to a specific amount"""
        if type not in ["cash", "card"]:
            return await ctx.send_warning("Please specify either 'cash' or 'card'.")
        check = await self.bot.db.fetchrow("SELECT cash, card FROM economy WHERE user_id = $1", user.id)
        if check is None:
            return await ctx.send_warning(f"**{user.name}** not found in the economy database.")
        new_amount = round(amount, 2)
        await self.bot.db.execute(f"UPDATE economy SET {type} = $1 WHERE user_id = $2", new_amount, user.id)
        await self.bot.manage.logging(ctx.author, f"Set **{self.bot.misc.humanize_number(amount)}** {self.cash} {type} to {user.mention} (`{user.id}`)", "money")
        await self.economy.logging(user, Decimal(amount), "set", type)
        return await ctx.send_success(f"Set {user.mention}'s {type} to **{self.bot.misc.humanize_number(new_amount)}** {self.cash}")

    @command(usage="mutuals comminate", brief="bot moderator")
    @is_moderator()
    async def mutuals(self, ctx: EvelinaContext, *, user: User):
        """Returns mutual servers between the member and the bot with their permissions"""
        if len(user.mutual_guilds) == 0:
            return await ctx.send_warning(f"This member doesn't share any server with {self.bot.user.name}")
        def get_user_permissions(user, guild):
            if user.id == guild.owner_id:
                return "Owner"
            member = guild.get_member(user.id)
            if member:
                if member.guild_permissions.administrator:
                    return "Administrator"
                elif member.guild_permissions.ban_members:
                    return "Moderator"
                elif member.guild_permissions.kick_members:
                    return "Moderator"
                elif member.guild_permissions.moderate_members:
                    return "Moderator"
            return "Member"
        guilds_info = []
        for g in user.mutual_guilds:
            permission = get_user_permissions(user, g)
            guilds_info.append(f"**{g.name}** (`{g.id}`) [`{g.member_count:,.0f}`] - __*{permission}*__")
        await ctx.paginate(guilds_info, "Mutual guilds", {"name": user.name, "icon_url": user.avatar.url if user.avatar else user.default_avatar.url})

    @command(name="globalenable", aliases=["ge"], brief="bot moderator", usage="globalenable blacktea")
    @is_moderator()
    async def globalenable(self, ctx: EvelinaContext, command: ValidCommand):
        """Globally enable a command"""
        if command in ["all"]:
            await self.bot.db.execute("DELETE FROM global_disabled_commands;")
            return await ctx.send_success(f"All commands have been globally enabled.")
        await self.bot.db.execute("DELETE FROM global_disabled_commands WHERE command = $1;", command)
        await self.bot.manage.logging(ctx.author, f"Global enabled `{command}`", "system")
        return await ctx.send_success(f"The command `{command}` has been globally enabled.")
    
    @command(name="globaldisable", aliases=["gd"], brief="bot moderator", usage="globaldisable blacktea abuse")
    @is_moderator()
    async def globaldisable(self, ctx: EvelinaContext, command: ValidCommand, *, reason: str):
        """Globally disable a command"""
        command = command.lower()
        if command in ["globalenable", "globaldisable"]:
            return await ctx.send_warning("Unable to globally disable this command.")
        result = await self.bot.db.fetchrow("SELECT status FROM global_disabled_commands WHERE command = $1;", command)
        if result:
            if result.get("status"):
                return await ctx.send_warning("This command is **already** globally disabled.")
        await self.bot.db.execute("INSERT INTO global_disabled_commands VALUES ($1, $2, $3, $4, $5);", command, True, ctx.author.id, reason, datetime.datetime.now().timestamp())
        await self.bot.manage.logging(ctx.author, f"Global disabled `{command}`\n> **Reason:** {reason}", "system")
        return await ctx.send_success(f"The command `{command}` has been globally disabled.")
    
    @command(name="globaldisabled", aliases=["gdl"], brief="bot moderator")
    @is_moderator()
    async def globaldisabled(self, ctx: EvelinaContext):
        """Show all commands that are globally disabled"""
        global_disabled_commands = await self.bot.db.fetch("SELECT * FROM global_disabled_commands;")
        if len(global_disabled_commands) <= 0:
            return await ctx.send_warning("There are no globally disabled commands.")
        disabled_list = [f"{obj.get('command')} disabled by <@{obj.get('user')}>\n> **Reason:** {obj.get('reason')}" for obj in global_disabled_commands]
        return await ctx.smallpaginate(disabled_list, f"Globally Disabled Commands:", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @group(name="usage", brief="bot moderator", invoke_without_command=True, case_insensitive=True)
    @is_moderator()
    async def usage(self, ctx: EvelinaContext):
        """Usage commands"""
        return await ctx.create_pages()

    @usage.command(name="recent", usage="usage recent userinfo", brief="bot moderator")
    @is_moderator()
    async def usage_recent(self, ctx: EvelinaContext, *, command: str = None):
        """View the most recent uses of a specific command"""
        if command:
            query = "SELECT user_id, server_id, command, arguments, timestamp FROM command_history WHERE command = $1 ORDER BY timestamp DESC LIMIT 500"
            params = (command,)
        else:
            query = "SELECT user_id, server_id, command, arguments, timestamp FROM command_history ORDER BY timestamp DESC LIMIT 500"
            params = ()
        results = await self.bot.db.fetch(query, *params)
        if not results:
            await ctx.send_warning(f"No usage found for `{command}`")
            return
        if not command:
            to_show = [f"<@{check['user_id']}> **{check['command']}** ({check['arguments'] if check['arguments'] else 'N/A'}) - <t:{check['timestamp']}:R>" for check in results]
        else:
            to_show = [f"<@{check['user_id']}> **{check['command']}** ({check['arguments'] if check['arguments'] else 'N/A'}) - <t:{check['timestamp']}:R>" for check in results]
        await ctx.paginate(to_show, f"Recent Command Usage", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})
    
    @usage.command(name="user", usage="usage user comminate userinfo", brief="bot moderator")
    @is_moderator()
    async def usage_user(self, ctx: EvelinaContext, user: User, *, command: str = None):
        """View all uses of a specific command by a user"""
        if user.id in self.bot.owner_ids:
            if ctx.author.id not in self.bot.owner_ids or ctx.author.id in [255489039564668929, 720294426064453665]:
                return await ctx.send_warning(f"You can't lookup **bot owners**")
        if command:
            query = "SELECT user_id, command, arguments, timestamp FROM command_history WHERE user_id = $1 AND command = $2 ORDER BY timestamp DESC"
            params = (user.id, command)
        else:
            query = "SELECT user_id, command, arguments, timestamp FROM command_history WHERE user_id = $1 ORDER BY timestamp DESC"
            params = (user.id,)
        results = await self.bot.db.fetch(query, *params)
        if not results:
            await ctx.send_warning(f"No usage found for {user.mention} with `{command}`")
            return
        if not command:
            to_show = [f"**{check['command']}** ({check['arguments'] if check['arguments'] else 'N/A'}) - <t:{check['timestamp']}:R>" for check in results]
        else:
            to_show = [f"**{check['command']}** ({check['arguments'] if check['arguments'] else 'N/A'}) - <t:{check['timestamp']}:R>" for check in results]
        await ctx.paginate(to_show, f"Command usage", {"name": user.name, "icon_url": user.avatar})

    @usage.command(name="server", usage="usage server 1228371886690537624 userinfo", brief="bot moderator")
    @is_moderator()
    async def usage_server(self, ctx: EvelinaContext, server: int, *, command: str = None):
        """View all uses of a specific command by a server"""
        if command:
            query = "SELECT user_id, command, arguments, timestamp FROM command_history WHERE server_id = $1 AND command = $2 ORDER BY timestamp DESC"
            params = (server, command)
        else:
            query = "SELECT user_id, command, arguments, timestamp FROM command_history WHERE server_id = $1 ORDER BY timestamp DESC"
            params = (server,)
        results = await self.bot.db.fetch(query, *params)
        if not results:
            await ctx.send_warning(f"No usage found for **{server}** with `{command}`")
            return
        if not command:
            to_show = [f"<@{check['user_id']}> **{check['command']}** ({check['arguments'] if check['arguments'] else 'N/A'}) - <t:{check['timestamp']}:R>" for check in results]
        else:
            to_show = [f"<@{check['user_id']}> **{check['command']}** ({check['arguments'] if check['arguments'] else 'N/A'}) - <t:{check['timestamp']}:R>" for check in results]
        guild_icon = self.bot.get_guild(server).icon.url if self.bot.get_guild(server).icon else None
        return await ctx.paginate(to_show, f"Command usage", {"name": await self.bot.manage.guild_name(server), "icon_url": guild_icon})

    @usage.command(name="command", usage="usage command userinfo", brief="bot moderator")
    @is_moderator()
    async def usage_command(self, ctx: EvelinaContext, *, command: str):
        """View all uses of a specific command"""
        query = "SELECT user_id, command, arguments, timestamp FROM command_history WHERE command = $1 ORDER BY timestamp DESC"
        params = (command,)
        results = await self.bot.db.fetch(query, *params)
        if not results:
            await ctx.send_warning(f"No usage found for `{command}`")
            return
        to_show = [f"<@{check['user_id']}> **{check['command']}** ({check['arguments'] if check['arguments'] else 'N/A'}) - <t:{check['timestamp']}:R>" for check in results]
        await ctx.paginate(to_show, f"Command usage for `{command}`", {"name": ctx.author.name, "icon_url": ctx.author.avatar})

    @usage.command(name="commands", brief="bot moderator")
    @is_moderator()
    async def usage_commands(self, ctx: EvelinaContext):
        """View the top 100 most used commands"""
        query = "SELECT command, COUNT(command) AS usage_count FROM command_history GROUP BY command ORDER BY usage_count DESC LIMIT 1500"
        total_query = "SELECT COUNT(*) FROM command_history"
        results = await self.bot.db.fetch(query)
        total_count = await self.bot.db.fetchval(total_query)
        if not results:
            await ctx.send_warning(f"No usage found")
            return
        to_show = [f"**{check['command']}** - {check['usage_count']:,.0f}" for check in results]
        await ctx.paginate(to_show, f"Commands Usage ({total_count:,.0f})", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})

    @usage.command(name="servers", brief="bot moderator")
    @is_moderator()
    async def usage_servers(self, ctx: EvelinaContext):
        """View the top 100 most active servers"""
        query = "SELECT server_id, COUNT(*) AS usage_count FROM command_history GROUP BY server_id ORDER BY usage_count DESC"
        results = await self.bot.db.fetch(query)
        if not results:
            await ctx.send_warning(f"No server usage found")
            return
        to_show = []
        for check in results:
            server_id = check['server_id']
            server_name = await self.bot.manage.guild_name(server_id)
            to_show.append(f"**{server_name}** - {check['usage_count']:,.0f}")
        await ctx.paginate(to_show, f"Servers Usage", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})

    @usage.command(name="users", brief="bot moderator")
    @is_moderator()
    async def usage_users(self, ctx: EvelinaContext):
        """View the top 100 most active users"""
        query = "SELECT user_id, COUNT(*) AS usage_count FROM command_history GROUP BY user_id ORDER BY usage_count DESC"
        results = await self.bot.db.fetch(query)
        if not results:
            await ctx.send_warning(f"No user usage found")
            return
        to_show = [f"<@{check['user_id']}> - {check['usage_count']:,.0f}" for check in results]
        await ctx.paginate(to_show, f"Users Usage", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})

    @usage.group(name="economy", brief="bot moderator", invoke_without_command=True, case_insensitive=True)
    @is_moderator()
    async def usage_economy(self, ctx: EvelinaContext):
        """Economy commands"""
        return await ctx.create_pages()
    
    @usage_economy.command(name="user", brief="bot moderator", usage="usage economy user comminate")
    @is_moderator()
    async def usage_economy_user(self, ctx: EvelinaContext, user: User):
        """View all economy transactions of a user"""
        query = "SELECT * FROM economy_logs WHERE user_id = $1 ORDER BY created DESC LIMIT 500"
        results = await self.bot.db.fetch(query, user.id)
        if not results:
            await ctx.send_warning(f"No economy transactions found for {user.mention}")
            return
        to_show = [f"{Decimal(check['amount']).quantize(Decimal('0.01'))} {check['action']} {check['type']} - <t:{check['created']}:R>" for check in results]
        return await ctx.paginate(to_show, f"Economy transactions for {user.name}", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})
    
    @group(brief="bot manager", invoke_without_command=True, case_insensitive=True)
    @is_moderator()
    async def blacklist(self, ctx: EvelinaContext):
        """Blacklist commands"""
        return await ctx.create_pages()

    @blacklist.command(name="user", brief="bot manager", usage="blacklist user comminate 24h spamming")
    @is_moderator()
    async def blacklist_user(self, ctx: EvelinaContext, user: User, duration: Optional[ValidTime] = None, *, reason: str):
        """Blacklist a user permanently or temporarily"""
        check = await self.bot.db.fetchrow("SELECT * FROM blacklist_user WHERE user_id = $1", user.id)
        if check:
            duration_check = f"for **{self.bot.misc.humanize_time(check['duration'])}**" if check['duration'] else "**permanently**"
            return await ctx.send_warning(f"User {user.mention} is already blacklisted {duration_check} by <@{check['moderator_id']}> (<t:{check['timestamp']}:R>).\n```{check['reason']}```")
        await self.bot.db.execute("INSERT INTO blacklist_user VALUES ($1, $2, $3, $4, $5)", user.id, ctx.author.id, duration, reason, datetime.datetime.now().timestamp())
        duration_text = f"for **{self.bot.misc.humanize_time(duration)}**" if duration else "**permanently**"
        await self.bot.manage.logging(ctx.author, f"Blacklisted user {user.mention} {duration_text}. Reason:\n```{reason}```", "blacklist")
        return await ctx.send_success(f"Blacklisted user {user.mention} {duration_text}. Reason:\n```{reason}```")
        
    @blacklist.command(name="server", brief="bot manager", usage="blacklist server /evelina 24h spamming")
    @is_moderator()
    async def blacklist_server(self, ctx: EvelinaContext, server: Union[Invite, int], duration: Optional[ValidTime] = None, *, reason: str):
        """Blacklist a server permanently or temporarily"""
        if isinstance(server, Invite):
            server = server.guild.id
        check = await self.bot.db.fetchrow("SELECT * FROM blacklist_server WHERE guild_id = $1", server)
        if check:
            duration_check = f"for **{self.bot.misc.humanize_time(check['duration'])}**" if check['duration'] else "**permanently**"
            return await ctx.send_warning(f"Server {await self.bot.manage.guild_name(server, True)} is already blacklisted {duration_check} by <@{check['moderator_id']}> (<t:{check['timestamp']}:R>).\n```{check['reason']}```")
        await self.bot.db.execute("INSERT INTO blacklist_server VALUES ($1, $2, $3, $4, $5)", server, ctx.author.id, duration, reason, datetime.datetime.now().timestamp())
        duration_text = f"for **{self.bot.misc.humanize_time(duration)}**" if duration else "**permanently**"
        await self.bot.manage.logging(ctx.author, f"Blacklisted server {await self.bot.manage.guild_name(server, True)} {duration_text}.\n```{reason}```", "blacklist")
        return await ctx.send_success(f"Blacklisted server {await self.bot.manage.guild_name(server, True)} {duration_text}.\n```{reason}```")
    
    @blacklist.command(name="command", brief="bot manager", usage="blacklist command comminate userinfo 24h spamming")
    @is_moderator()
    async def blacklist_command(self, ctx: EvelinaContext, target: Union[User, Invite, int], command: ValidCommand, duration: Optional[ValidTime] = None, *, reason: str):
        """Blacklist a user or server from a command permanently or temporarily"""
        if isinstance(target, User):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_command WHERE user_id = $1 AND command = $2", target.id, command)
            if check:
                duration_check = f"for **{self.bot.misc.humanize_time(check['duration'])}**" if check['duration'] else "**permanently**"
                return await ctx.send_warning(f"User {target.mention} is already blacklisted from the command `{command}` {duration_check} by <@{check['moderator_id']}> (<t:{check['timestamp']}:R>).\n```{check['reason']}```")
            await self.bot.db.execute("INSERT INTO blacklist_command VALUES ($1, $2, $3, $4, $5, $6)", target.id, ctx.author.id, command, duration, reason, datetime.datetime.now().timestamp())
            duration_text = f"for **{self.bot.misc.humanize_time(duration)}**" if duration else "**permanently**"
            await self.bot.manage.logging(ctx.author, f"Blacklisted user {target.mention} from the command `{command}` {duration_text}.\n```{reason}```", "blacklist")
            return await ctx.send_success(f"Blacklisted user {target.mention} from the command `{command}` {duration_text}.\n```{reason}```")
        elif isinstance(target, int):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_command_server WHERE guild_id = $1 AND command = $2", target, command)
            if check:
                duration_check = f"for **{self.bot.misc.humanize_time(check['duration'])}**" if check['duration'] else "**permanently**"
                return await ctx.send_warning(f"Server {await self.bot.manage.guild_name(target, True)} is already blacklisted from the command `{command}` {duration_check} by <@{check['moderator_id']}> (<t:{check['timestamp']}:R>).\n```{check['reason']}```")
            await self.bot.db.execute("INSERT INTO blacklist_command_server VALUES ($1, $2, $3, $4, $5, $6)", target, ctx.author.id, command, duration, reason, datetime.datetime.now().timestamp())
            duration_text = f"for **{self.bot.misc.humanize_time(duration)}**" if duration else "**permanently**"
            await self.bot.manage.logging(ctx.author, f"Blacklisted server {await self.bot.manage.guild_name(target, True)} from the command `{command}` {duration_text}.\n```{reason}```", "blacklist")
            return await ctx.send_success(f"Blacklisted server {await self.bot.manage.guild_name(target, True)} from the command **{duration_text}** {duration}.\n```{reason}```")
        elif isinstance(target, Invite):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_command_server WHERE guild_id = $1 AND command = $2", target.guild.id, command)
            if check:
                duration_check = f"for **{self.bot.misc.humanize_time(check['duration'])}**" if check['duration'] else "**permanently**"
                return await ctx.send_warning(f"Server {await self.bot.manage.guild_name(target.guild.id, True)} is already blacklisted from the command `{command}` {duration_check} by <@{check['moderator_id']}> (<t:{check['timestamp']}:R>).\n```{check['reason']}```")
            await self.bot.db.execute("INSERT INTO blacklist_command_server VALUES ($1, $2, $3, $4, $5, $6)", target.guild.id, ctx.author.id, command, duration, reason, datetime.datetime.now().timestamp())
            duration_text = f"for **{self.bot.misc.humanize_time(duration)}**" if duration else "**permanently**"
            await self.bot.manage.logging(ctx.author, f"Blacklisted server {await self.bot.manage.guild_name(target.guild.id, True)} from the command `{command}` {duration_text}.\n```{reason}```", "blacklist")
            return await ctx.send_success(f"Blacklisted server {await self.bot.manage.guild_name(target.guild.id, True)} from the command `{command}` {duration_text}.\n```{reason}```")
        else:
            return await ctx.send_warning("Couldn't convert target into a valid user or server")

    @blacklist.command(name="cog", brief="bot manager", usage="blacklist cog comminate utility 24h spamming")
    @is_moderator()
    async def blacklist_cog(self, ctx: EvelinaContext, target: Union[User, Invite, int], cog: ValidCog, duration: Optional[ValidTime] = None, *, reason: str):
        """Blacklist a user or server from a cog permanently or temporarily"""
        if isinstance(target, User):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_cog WHERE user_id = $1 AND cog = $2", target.id, cog)
            if check:
                duration_check = f"for **{self.bot.misc.humanize_time(check['duration'])}**" if check['duration'] else "**permanently**"
                return await ctx.send_warning(f"User {target.mention} is already blacklisted from the cog `{cog}` {duration_check} by <@{check['moderator_id']}> (<t:{check['timestamp']}:R>).\n```{check['reason']}```")
            await self.bot.db.execute("INSERT INTO blacklist_cog VALUES ($1, $2, $3, $4, $5, $6)", target.id, ctx.author.id, cog, duration, reason, datetime.datetime.now().timestamp())
            duration_text = f"for **{self.bot.misc.humanize_time(duration)}**" if duration else "**permanently**"
            await self.bot.manage.logging(ctx.author, f"Blacklisted user {target.mention} from the cog `{cog}` {duration_text}.\n```{reason}```", "blacklist")
            return await ctx.send_success(f"Blacklisted user {target.mention} from the cog `{cog}` {duration_text}.\n```{reason}```")
        elif isinstance(target, int):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_cog_server WHERE guild_id = $1 AND cog = $2", target, cog)
            if check:
                duration_check = f"for **{self.bot.misc.humanize_time(check['duration'])}**" if check['duration'] else "**permanently**"
                return await ctx.send_warning(f"Server {await self.bot.manage.guild_name(target, True)} is already blacklisted from the cog `{cog}` {duration_check} by <@{check['moderator_id']}> (<t:{check['timestamp']}:R>).\n```{check['reason']}```")
            await self.bot.db.execute("INSERT INTO blacklist_cog_server VALUES ($1, $2, $3, $4, $5, $6)", target, ctx.author.id, cog, duration, reason, datetime.datetime.now().timestamp())
            duration_text = f"for **{self.bot.misc.humanize_time(duration)}**" if duration else "**permanently**"
            await self.bot.manage.logging(ctx.author, f"Blacklisted server {await self.bot.manage.guild_name(target, True)} from the cog `{cog}` {duration_text}.\n```{reason}```", "blacklist")
            return await ctx.send_success(f"Blacklisted server {await self.bot.manage.guild_name(target, True)} from the cog `{cog}` {duration_text}.\n```{reason}```")
        elif isinstance(target, Invite):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_cog_server WHERE guild_id = $1 AND cog = $2", target.guild.id, cog)
            if check:
                duration_check = f"for **{self.bot.misc.humanize_time(check['duration'])}**" if check['duration'] else "**permanently**"
                return await ctx.send_warning(f"Server {await self.bot.manage.guild_name(target.guild.id, True)} is already blacklisted from the cog `{cog}` {duration_check} by <@{check['moderator_id']}> (<t:{check['timestamp']}:R>).\n```{check['reason']}```")
            await self.bot.db.execute("INSERT INTO blacklist_cog_server VALUES ($1, $2, $3, $4, $5, $6)", target.guild.id, ctx.author.id, cog, duration, reason, datetime.datetime.now().timestamp())
            duration_text = f"for **{self.bot.misc.humanize_time(duration)}**" if duration else "**permanently**"
            await self.bot.manage.logging(ctx.author, f"Blacklisted server {await self.bot.manage.guild_name(target.guild.id, True)} from the cog `{cog}` {duration_text}.\n```{reason}```", "blacklist")
            return await ctx.send_success(f"Blacklisted server {await self.bot.manage.guild_name(target.guild.id, True)} from the cog `{cog}` {duration_text}.\n```{reason}```")
        else:
            return await ctx.send_warning("Couldn't convert target into a valid user or server")

    @blacklist.command(name="check", brief="bot manager", usage="blacklist check comminate")
    @is_moderator()
    async def blacklist_check(self, ctx: EvelinaContext, target: Union[User, Invite, int]):
        """Check if a user or server is blacklisted and list all blacklists"""
        embeds = []
        def chunkify(items, size):
            return [items[i:i+size] for i in range(0, len(items), size)]
        if isinstance(target, User):
            user_check = await self.bot.db.fetchrow("SELECT * FROM blacklist_user WHERE user_id = $1", target.id)
            command_check = await self.bot.db.fetch("SELECT * FROM blacklist_command WHERE user_id = $1", target.id)
            cog_check = await self.bot.db.fetch("SELECT * FROM blacklist_cog WHERE user_id = $1", target.id)
            if user_check or command_check or cog_check:
                entries = []
                if user_check:
                    duration_text = f"for **{self.bot.misc.humanize_time(user_check['duration'])}**" if user_check['duration'] else "**permanently**"
                    entries.append(
                        f"**Global** {duration_text} by <@{user_check['moderator_id']}> (<t:{user_check['timestamp']}:R>)\n"
                        f"```{user_check['reason']}```"
                    )
                for command in command_check:
                    duration_text = f"for **{self.bot.misc.humanize_time(command['duration'])}**" if command['duration'] else "**permanently**"
                    entries.append(
                        f"**Command** (`{command['command']}`) {duration_text} by <@{command['moderator_id']}> (<t:{command['timestamp']}:R>)\n"
                        f"```{command['reason']}```"
                    )
                for cog in cog_check:
                    duration_text = f"for **{self.bot.misc.humanize_time(cog['duration'])}**" if cog['duration'] else "**permanently**"
                    entries.append(
                        f"**Cog** (`{cog['cog']}`) {duration_text} by <@{cog['moderator_id']}> (<t:{cog['timestamp']}:R>)\n"
                        f"```{cog['reason']}```"
                    )
                for i, chunk in enumerate(chunkify(entries, 3), start=1):
                    embed = Embed(title=f"Blacklists for {target}", description="\n".join(chunk), color=colors.NEUTRAL)
                    embed.set_author(name=target.name, icon_url=target.avatar.url if target.avatar else target.default_avatar.url)
                    embed.set_footer(text=f"Page {i}/{len(chunkify(entries, 3))} ({len(entries)} entries)")
                    embeds.append(embed)
                return await ctx.paginator(embeds)
            else:
                return await ctx.send_success(f"User {target.mention} is not blacklisted")
        elif isinstance(target, Invite):
            server_check = await self.bot.db.fetchrow("SELECT * FROM blacklist_server WHERE guild_id = $1", target.guild.id)
            command_check = await self.bot.db.fetch("SELECT * FROM blacklist_command_server WHERE guild_id = $1", target.guild.id)
            cog_check = await self.bot.db.fetch("SELECT * FROM blacklist_cog_server WHERE guild_id = $1", target.guild.id)
            if server_check or command_check or cog_check:
                entries = []
                if server_check:
                    duration_text = f"for **{self.bot.misc.humanize_time(server_check['duration'])}**" if server_check['duration'] else "**permanently**"
                    entries.append(
                        f"**Global** {duration_text} by <@{server_check['moderator_id']}> (<t:{server_check['timestamp']}:R>)\n"
                        f"```{server_check['reason']}```"
                    )
                for command in command_check:
                    duration_text = f"for **{self.bot.misc.humanize_time(command['duration'])}**" if command['duration'] else "**permanently**"
                    entries.append(
                        f"**Command** (`{command['command']}`) {duration_text} by <@{command['moderator_id']}> (<t:{command['timestamp']}:R>)\n"
                        f"```{command['reason']}```"
                    )
                for cog in cog_check:
                    duration_text = f"for **{self.bot.misc.humanize_time(cog['duration'])}**" if cog['duration'] else "**permanently**"
                    entries.append(
                        f"**Cog** (`{cog['cog']}`) {duration_text} by <@{cog['moderator_id']}> (<t:{cog['timestamp']}:R>)\n"
                        f"```{cog['reason']}```"
                    )
                for i, chunk in enumerate(chunkify(entries, 3), start=1):
                    embed = Embed(title=f"Blacklists for {await self.bot.manage.guild_name(target.guild.id)}", description="\n".join(chunk), color=colors.NEUTRAL)
                    embed.set_author(name=await self.bot.manage.guild_name(target.guild.id), icon_url=target.guild.icon.url if target.guild.icon else None)
                    embed.set_footer(text=f"Page {i}/{len(chunkify(entries, 3))} ({len(entries)} entries)")
                    embeds.append(embed)
                return await ctx.paginator(embeds)
            else:
                return await ctx.send_success(f"Server {await self.bot.manage.guild_name(target.guild.id, True)} is not blacklisted")
        elif isinstance(target, int):
            server_check = await self.bot.db.fetchrow("SELECT * FROM blacklist_server WHERE guild_id = $1", target)
            command_check = await self.bot.db.fetch("SELECT * FROM blacklist_command_server WHERE guild_id = $1", target)
            cog_check = await self.bot.db.fetch("SELECT * FROM blacklist_cog_server WHERE guild_id = $1", target)
            if server_check or command_check or cog_check:
                entries = []
                if server_check:
                    duration_text = f"for **{self.bot.misc.humanize_time(server_check['duration'])}**" if server_check['duration'] else "**permanently**"
                    entries.append(
                        f"**Global** {duration_text} by <@{server_check['moderator_id']}> (<t:{server_check['timestamp']}:R>)\n"
                        f"```{server_check['reason']}```"
                    )
                for command in command_check:
                    duration_text = f"for **{self.bot.misc.humanize_time(command['duration'])}**" if command['duration'] else "**permanently**"
                    entries.append(
                        f"**Command** (`{command['command']}`) {duration_text} by <@{command['moderator_id']}> (<t:{command['timestamp']}:R>)\n"
                        f"```{command['reason']}```"
                    )
                for cog in cog_check:
                    duration_text = f"for **{self.bot.misc.humanize_time(cog['duration'])}**" if cog['duration'] else "**permanently**"
                    entries.append(
                        f"**Cog** (`{cog['cog']}`) {duration_text} by <@{cog['moderator_id']}> (<t:{cog['timestamp']}:R>)\n"
                        f"```{cog['reason']}```"
                    )
                for i, chunk in enumerate(chunkify(entries, 3), start=1):
                    embed = Embed(title=f"Blacklists for {await self.bot.manage.guild_name(target)}", description="\n".join(chunk), color=colors.NEUTRAL)
                    embed.set_author(name=await self.bot.manage.guild_name(target), icon_url=None)
                    embed.set_footer(text=f"Page {i}/{len(chunkify(entries, 3))} ({len(entries)} entries)")
                    embeds.append(embed)
                return await ctx.paginator(embeds)
            else:
                return await ctx.send_success(f"Server {await self.bot.manage.guild_name(target, True)} is not blacklisted")
        else:
            return await ctx.send_warning("Couldn't convert target into a valid user or server")

    @group(brief="bot manager", invoke_without_command=True, case_insensitive=True)
    @is_moderator()
    async def unblacklist(self, ctx: EvelinaContext):
        """Unblacklist commands"""
        return await ctx.create_pages()

    @unblacklist.command(name="user", brief="bot manager", usage="unblacklist user comminate")
    @is_moderator()
    async def unblacklist_user(self, ctx: EvelinaContext, user: User):
        """Unblacklist a user"""
        check = await self.bot.db.fetchrow("SELECT * FROM blacklist_user WHERE user_id = $1", user.id)
        if not check:
            return await ctx.send_warning(f"User {user.mention} isn't blacklisted")
        if check['moderator_id'] != ctx.author.id:
            author_rank = await self.bot.manage.get_rank(ctx.author.id)
            target_rank = await self.bot.manage.get_rank(check['moderator_id'])
            if author_rank < target_rank:
                return await ctx.send_warning(f"Your rank must be higher than or equal to <@{check['moderator_id']}> to unblacklist {user.mention}")
        await self.bot.db.execute("DELETE FROM blacklist_user WHERE user_id = $1", user.id)
        await self.bot.manage.logging(ctx.author, f"Unblacklisted user {user.mention}", "blacklist")
        return await ctx.send_success(f"Unblacklisted user {user.mention}")

    @unblacklist.command(name="server", brief="bot manager", usage="unblacklist server /evelina")
    @is_moderator()
    async def unblacklist_server(self, ctx: EvelinaContext, server: Union[Invite, int]):
        """Unblacklist a server"""
        if isinstance(server, Invite):
            server = server.guild.id
        check = await self.bot.db.fetchrow("SELECT * FROM blacklist_server WHERE guild_id = $1", server)
        if not check:
            return await ctx.send_warning(f"Server {await self.bot.manage.guild_name(server, True)} isn't blacklisted")
        if check['moderator_id'] != ctx.author.id:
            author_rank = await self.bot.manage.get_rank(ctx.author.id)
            target_rank = await self.bot.manage.get_rank(check['moderator_id'])
            if author_rank < target_rank:
                return await ctx.send_warning(f"Your rank must be higher than or equal to <@{check['moderator_id']}> to unblacklist {await self.bot.manage.guild_name(server, True)}")
        await self.bot.db.execute("DELETE FROM blacklist_server WHERE guild_id = $1", server)
        await self.bot.manage.logging(ctx.author, f"Unblacklisted server {await self.bot.manage.guild_name(server, True)}", "blacklist")
        return await ctx.send_success(f"Unblacklisted server {await self.bot.manage.guild_name(server, True)}")
    
    @unblacklist.command(name="command", brief="bot manager", usage="unblacklist command comminate userinfo")
    @is_moderator()
    async def unblacklist_command(self, ctx: EvelinaContext, target: Union[User, int, Invite], command: ValidCommand):
        """Unblacklist a user or server from a command"""
        if isinstance(target, User):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_command WHERE user_id = $1 AND command = $2", target.id, command)
            if not check:
                return await ctx.send_warning(f"User {target.mention} isn't blacklisted from the command `{command}`")
            if check['moderator_id'] != ctx.author.id:
                author_rank = await self.bot.manage.get_rank(ctx.author.id)
                target_rank = await self.bot.manage.get_rank(check['moderator_id'])
                if author_rank < target_rank:
                    return await ctx.send_warning(f"Your rank must be higher than or equal to <@{check['moderator_id']}> to unblacklist {target.mention} from the command `{command}`")
            await self.bot.db.execute("DELETE FROM blacklist_command WHERE user_id = $1 AND command = $2", target.id, command)
            await self.bot.manage.logging(ctx.author, f"Unblacklisted user {target.mention} from the command `{command}`", "blacklist")
            return await ctx.send_success(f"Unblacklisted user {target.mention} from the command `{command}`")
        elif isinstance(target, int):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_command_server WHERE guild_id = $1 AND command = $2", target, command)
            if not check:
                return await ctx.send_warning(f"Server {await self.bot.manage.guild_name(target, True)} isn't blacklisted from the command `{command}`")
            if check['moderator_id'] != ctx.author.id:
                author_rank = await self.bot.manage.get_rank(ctx.author.id)
                target_rank = await self.bot.manage.get_rank(check['moderator_id'])
                if author_rank < target_rank:
                    return await ctx.send_warning(f"Your rank must be higher than or equal to <@{check['moderator_id']}> to unblacklist {await self.bot.manage.guild_name(target, True)} from the command `{command}`")
            await self.bot.db.execute("DELETE FROM blacklist_command_server WHERE guild_id = $1 AND command = $2", target, command)
            await self.bot.manage.logging(ctx.author, f"Unblacklisted server {await self.bot.manage.guild_name(target, True)} from the command `{command}`", "blacklist")
            return await ctx.send_success(f"Unblacklisted server {await self.bot.manage.guild_name(target, True)} from the command `{command}`")
        elif isinstance(target, Invite):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_command_server WHERE guild_id = $1 AND command = $2", target.guild.id, command)
            if not check:
                return await ctx.send_warning(f"Server {await self.bot.manage.guild_name(target.guild.id, True)} isn't blacklisted from the command `{command}`")
            if check['moderator_id'] != ctx.author.id:
                author_rank = await self.bot.manage.get_rank(ctx.author.id)
                target_rank = await self.bot.manage.get_rank(check['moderator_id'])
                if author_rank < target_rank:
                    return await ctx.send_warning(f"Your rank must be higher than or equal to <@{check['moderator_id']}> to unblacklist {await self.bot.manage.guild_name(target.guild.id, True)} from the command `{command}`")
            await self.bot.db.execute("DELETE FROM blacklist_command_server WHERE guild_id = $1 AND command = $2", target.guild.id, command)
            await self.bot.manage.logging(ctx.author, f"Unblacklisted server {await self.bot.manage.guild_name(target.guild.id, True)} from the command `{command}`", "blacklist")
            return await ctx.send_success(f"Unblacklisted server {await self.bot.manage.guild_name(target.guild.id, True)} from the command `{command}`")
        else:
            return await ctx.send_warning("Couldn't convert target into a valid user or server")

    @unblacklist.command(name="cog", brief="bot manager", usage="unblacklist cog comminate utility")
    @is_moderator()
    async def unblacklist_cog(self, ctx: EvelinaContext, target: Union[User, int, Invite], cog: ValidCog):
        """Unblacklist a user or server from a cog"""
        if isinstance(target, User):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_cog WHERE user_id = $1 AND cog = $2", target.id, cog)
            if not check:
                return await ctx.send_warning(f"User {target.mention} isn't blacklisted from the cog `{cog}`")
            if check['moderator_id'] != ctx.author.id:
                author_rank = await self.bot.manage.get_rank(ctx.author.id)
                target_rank = await self.bot.manage.get_rank(check['moderator_id'])
                if author_rank < target_rank:
                    return await ctx.send_warning(f"Your rank must be higher than or equal to <@{check['moderator_id']}> to unblacklist {target.mention} from the cog `{cog}`")
            await self.bot.db.execute("DELETE FROM blacklist_cog WHERE user_id = $1 AND cog = $2", target.id, cog)
            await self.bot.manage.logging(ctx.author, f"Unblacklisted user {target.mention} from the cog `{cog}`", "blacklist")
            return await ctx.send_success(f"Unblacklisted user {target.mention} from the cog `{cog}`")
        elif isinstance(target, int):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_cog_server WHERE guild_id = $1 AND cog = $2", target, cog)
            if not check:
                return await ctx.send_warning(f"Server {await self.bot.manage.guild_name(target, True)} isn't blacklisted from the cog `{cog}`")
            if check['moderator_id'] != ctx.author.id:
                author_rank = await self.bot.manage.get_rank(ctx.author.id)
                target_rank = await self.bot.manage.get_rank(check['moderator_id'])
                if author_rank < target_rank:
                    return await ctx.send_warning(f"Your rank must be higher than or equal to <@{check['moderator_id']}> to unblacklist {await self.bot.manage.guild_name(target, True)} from the cog `{cog}`")
            await self.bot.db.execute("DELETE FROM blacklist_cog_server WHERE guild_id = $1 AND cog = $2", target, cog)
            await self.bot.manage.logging(ctx.author, f"Unblacklisted server {await self.bot.manage.guild_name(target, True)} from the cog `{cog}`", "blacklist")
            return await ctx.send_success(f"Unblacklisted server {await self.bot.manage.guild_name(target, True)} from the cog `{cog}`")
        elif isinstance(target, Invite):
            check = await self.bot.db.fetchrow("SELECT * FROM blacklist_cog_server WHERE guild_id = $1 AND cog = $2", target.guild.id, cog)
            if not check:
                return await ctx.send_warning(f"Server {await self.bot.manage.guild_name(target.guild.id, True)} isn't blacklisted from the cog `{cog}`")
            if check['moderator_id'] != ctx.author.id:
                author_rank = await self.bot.manage.get_rank(ctx.author.id)
                target_rank = await self.bot.manage.get_rank(check['moderator_id'])
                if author_rank < target_rank:
                    return await ctx.send_warning(f"Your rank must be higher than or equal to <@{check['moderator_id']}> to unblacklist {await self.bot.manage.guild_name(target.guild.id, True)} from the cog `{cog}`")
            await self.bot.db.execute("DELETE FROM blacklist_cog_server WHERE guild_id = $1 AND cog = $2", target.guild.id, cog)
            await self.bot.manage.logging(ctx.author, f"Unblacklisted server {await self.bot.manage.guild_name(target.guild.id, True)} from the cog `{cog}`", "blacklist")
            return await ctx.send_success(f"Unblacklisted server {await self.bot.manage.guild_name(target.guild.id, True)} from the cog `{cog}`")
        else:
            return await ctx.send_warning("Couldn't convert target into a valid user or server")

async def setup(bot: Evelina) -> None:
    await bot.add_cog(Moderator(bot))