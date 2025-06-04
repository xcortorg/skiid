from discord.abc import GuildChannel
from discord import Embed, PermissionOverwrite, Role
from discord.ext.commands import Cog, group, has_guild_permissions, bot_has_guild_permissions, BadArgument

from modules.styles import colors
from modules.evelinabot import Evelina
from modules.converters import EvelinaContext
from modules.converters import ChannelType, CounterMessage, CounterType

class Counters(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Counter commands"

    async def create_counter_channel(
        self, ctx: EvelinaContext, message: str, replace_with: str, channeltype: str
    ) -> GuildChannel:
        overwrites = {ctx.guild.default_role: PermissionOverwrite(connect=False)}
        reason = "creating member counter"
        name = message.replace("{target}", replace_with)
        if channeltype == "stage":
            channel = await ctx.guild.create_stage_channel(name=name, overwrites=overwrites, reason=reason)
        elif channeltype == "voice":
            channel = await ctx.guild.create_voice_channel(name=name, overwrites=overwrites, reason=reason)
        elif channeltype == "category":
            channel = await ctx.guild.create_category(name=name, reason=reason)
        else:
            channel = await ctx.guild.create_text_channel(name=name, reason=reason, overwrites={ctx.guild.default_role: PermissionOverwrite(send_messages=False)})
        return channel

    @group(invoke_without_command=True, name="counter", case_insensitive=True)
    async def counter(self, ctx: EvelinaContext):
        """Create counters for everybody to see"""
        return await ctx.create_pages()

    @counter.command(name="types")
    async def counter_types(self, ctx: EvelinaContext):
        """Returns the counter types and channel types"""
        embed1 = Embed(color=colors.NEUTRAL, title="counter types")
        embed2 = Embed(color=colors.NEUTRAL, title="channel types")
        embed1.description = ">>> members - all members from the server (including bots)\nhumans - all members from the server (excluding bots)\nbots - all bots from the server\nboosters - all server boosters\nvoice - all members in a voice channel\nrole - all members in a certain role\nboosts - all boosts from the server"
        embed2.description = ">>> voice - creates voice channel\nstage - creates stage channel\ntext - creates text channel\ncategory - creates category channel"
        await ctx.paginator([embed1, embed2])
    
    @counter.group(invoke_without_command=True, name="add", brief="manage guild", case_insensitive=True)
    async def counter_add(self, ctx: EvelinaContext):
        """Create channel counter"""
        return await ctx.create_pages()

    @counter_add.command(name="members", brief="manage guild", usage="counter add members voice Members: {target}")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def counter_add_members(self, ctx: EvelinaContext, channeltype: ChannelType, *, message: CounterMessage = "{target}",):
        """Add a counter for the member count"""
        check = await self.bot.db.fetchrow("SELECT * FROM counters WHERE guild_id = $1 AND module = $2", ctx.guild.id, ctx.command.name)
        if check:
            return await ctx.send_warning(f"<#{check['channel_id']}> is already a **member** counter")
        channel = await self.create_counter_channel(ctx, message, str(ctx.guild.member_count), channeltype)
        await self.bot.db.execute("INSERT INTO counters VALUES ($1,$2,$3,$4,$5)", ctx.guild.id, channeltype, channel.id, message, ctx.command.name)
        await ctx.send_success(f"Created **member** counter -> {channel.mention}")

    @counter_add.command(name="humans", brief="manage guild", usage="counter add humans voice Humans: {target}")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def counter_add_humans(self, ctx: EvelinaContext, channeltype: ChannelType, *, message: CounterMessage = "{target}"):
        """Add a counter for non bots members"""
        check = await self.bot.db.fetchrow("SELECT * FROM counters WHERE guild_id = $1 AND module = $2", ctx.guild.id, ctx.command.name)
        if check:
            return await ctx.send_warning(f"<#{check['channel_id']}> is already a **humans** counter")
        channel = await self.create_counter_channel(ctx, message, str(len([m for m in ctx.guild.members if not m.bot])), channeltype)
        await self.bot.db.execute("INSERT INTO counters VALUES ($1,$2,$3,$4,$5)", ctx.guild.id, channeltype, channel.id, message, ctx.command.name)
        await ctx.send_success(f"Created **humans** counter -> {channel.mention}")

    @counter_add.command(name="bots", brief="manage guild", usage="counter add bots voice Bots: {target}")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def counter_add_bots(self, ctx: EvelinaContext, channeltype: ChannelType, *, message: CounterMessage = "{target}"):
        """Add a counter for bots"""
        check = await self.bot.db.fetchrow("SELECT * FROM counters WHERE guild_id = $1 AND module = $2", ctx.guild.id, ctx.command.name)
        if check:
            return await ctx.send_warning(f"<#{check['channel_id']}> is already a **bots** counter")
        channel = await self.create_counter_channel(ctx, message, str(len([m for m in ctx.guild.members if m.bot])), channeltype)
        await self.bot.db.execute("INSERT INTO counters VALUES ($1,$2,$3,$4,$5)", ctx.guild.id, channeltype, channel.id, message, ctx.command.name)
        await ctx.send_success(f"Created **bots** counter -> {channel.mention}")

    @counter_add.command(name="voice", brief="manage guild", usage="counter add voice voice Voice: {target}")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def counter_add_voice(self, ctx: EvelinaContext, channeltype: ChannelType, *, message: CounterMessage = "{target}"):
        """Add a counter for members that are connected to a voice channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM counters WHERE guild_id = $1 AND module = $2", ctx.guild.id, ctx.command.name)
        if check:
            return await ctx.send_warning(f"<#{check['channel_id']}> is already a **voice** counter")
        channel = await self.create_counter_channel(ctx, message, str(sum(len(c.members) for c in ctx.guild.voice_channels)), channeltype)
        await self.bot.db.execute("INSERT INTO counters VALUES ($1,$2,$3,$4,$5)", ctx.guild.id, channeltype, channel.id, message, ctx.command.name)
        await ctx.send_success(f"Created **voice** counter -> {channel.mention}")

    @counter_add.command(name="boosters", brief="manage guild", usage="counter add boosters voice Boosters: {target}")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def counter_add_boosters(self, ctx: EvelinaContext, channeltype: ChannelType, *, message: CounterMessage = "{target}"):
        """Add a counter for boosters"""
        check = await self.bot.db.fetchrow("SELECT * FROM counters WHERE guild_id = $1 AND module = $2", ctx.guild.id, ctx.command.name)
        if check:
            return await ctx.send_warning(f"<#{check['channel_id']}> is already a **booster** counter")
        channel = await self.create_counter_channel(ctx, message, str(len(ctx.guild.premium_subscribers)), channeltype)
        await self.bot.db.execute("INSERT INTO counters VALUES ($1,$2,$3,$4,$5)", ctx.guild.id, channeltype, channel.id, message, ctx.command.name)
        await ctx.send_success(f"Created **boosters** counter -> {channel.mention}")

    @counter_add.command(name="boosts", brief="manage guild", usage="counter add boosts voice Boosts: {target}")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def counter_add_boosts(self, ctx: EvelinaContext, channeltype: ChannelType, *, message: CounterMessage = "{target}"):
        """Add a counter for boosts"""
        check = await self.bot.db.fetchrow("SELECT * FROM counters WHERE guild_id = $1 AND module = $2", ctx.guild.id, ctx.command.name)
        if check:
            return await ctx.send_warning(f"<#{check['channel_id']}> is already a **boosts** counter")
        channel = await self.create_counter_channel(ctx, message, str(ctx.guild.premium_subscription_count), channeltype)
        await self.bot.db.execute("INSERT INTO counters VALUES ($1,$2,$3,$4,$5)", ctx.guild.id, channeltype, channel.id, message, ctx.command.name)
        await ctx.send_success(f"Created **boosts** counter -> {channel.mention}")

    @counter_add.command(name="role", brief="manage guild", usage="counter add role voice @verified Members: {target}")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def counter_add_role(self, ctx: EvelinaContext, channeltype: ChannelType, role: Role, *, message: CounterMessage = "{target}",):
        """Add a counter for a specific role"""
        check = await self.bot.db.fetchrow("SELECT * FROM counters WHERE guild_id = $1 AND module = $2 AND role_id = $3", ctx.guild.id, ctx.command.name, role.id)
        if check:
            return await ctx.send_warning(f"<#{check['channel_id']}> is already a **role** counter for <@&{check['role_id']}>")
        channel = await self.create_counter_channel(ctx, message, str(len(role.members)), channeltype)
        await self.bot.db.execute("INSERT INTO counters VALUES ($1,$2,$3,$4,$5,$6)", ctx.guild.id, channeltype, channel.id, message, ctx.command.name, role.id)
        await ctx.send_success(f"Created **role** counter for {role.mention} -> {channel.mention}")

    @counter.command(name="remove", brief="manage guild", usage="counter remove members")
    @has_guild_permissions(manage_guild=True)
    async def counter_remove(self, ctx: EvelinaContext, countertype: CounterType, role: Role = None):
        """Remove a counter from the server"""
        if role is None and countertype != "role":
            check = await self.bot.db.fetchrow("SELECT * FROM counters WHERE guild_id = $1 AND module = $2", ctx.guild.id, countertype)
            if not check:
                raise BadArgument(f"There is no **{countertype}** counter in this server")
            channel = ctx.guild.get_channel(int(check["channel_id"]))
            if channel:
                await channel.delete()
            await self.bot.db.execute("DELETE FROM counters WHERE guild_id = $1 AND module = $2", ctx.guild.id, countertype)
            return await ctx.send_success(f"Removed **{countertype}** counter")
        elif role and countertype == "role":
            check = await self.bot.db.fetchrow("SELECT * FROM counters WHERE guild_id = $1 AND module = $2 AND role_id = $3", ctx.guild.id, countertype, role.id)
            if not check:
                raise BadArgument(f"There is no **{countertype}** counter for {role.mention} in this server")
            channel = ctx.guild.get_channel(int(check["channel_id"]))
            if channel:
                await channel.delete()
            await self.bot.db.execute("DELETE FROM counters WHERE guild_id = $1 AND module = $2 AND role_id = $3", ctx.guild.id, countertype, role.id)
            return await ctx.send_success(f"Removed **{countertype}** counter for {role.mention}")
        else:
            return await ctx.send_help(ctx.command)
    
    @counter.command(name="list")
    async def counter_list(self, ctx: EvelinaContext):
        """Returns a list of the active server counters"""
        results = await self.bot.db.fetch("SELECT * FROM counters WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There are no counters")
        return await ctx.paginate([f"{result['module']} -> {ctx.guild.get_channel(int(result['channel_id'])).mention if ctx.guild.get_channel(int(result['channel_id'])) else result['channel_id']}" for result in results], f"Counters", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Counters(bot))
