import asyncio
import datetime
import re
from collections import defaultdict
from typing import Annotated

import discord
from discord.ext import commands
from humanfriendly import format_timespan
from managers.bot import Luma
from managers.helpers import Context
from managers.validators import NoStaff, RoleConvert, ValidNickname, ValidTime


class Moderation(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)

    @commands.command()
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def ban(
        self: "Moderation", ctx: Context, member: NoStaff, *, reason: str = "N/A"
    ):
        """
        Remove the intrusive member from your server
        """
        await member.ban(reason=reason + f" banned by {ctx.author}")
        await ctx.reply("🦅")

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    async def kick(
        self: "Moderation", ctx: Context, member: NoStaff, *, reason: str = "N/A"
    ):
        """
        Give another chance to that intrusive guy
        """
        await member.kick(reason=reason + f" kicked by {ctx.author}")
        await ctx.confirm(f"{member} has been kicked")

    @commands.command()
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def unban(
        self: "Moderation", ctx: Context, member: discord.User, *, reason: str = "N/A"
    ):
        """
        Unban a user
        """
        try:
            await ctx.guild.unban(member, reason=reason + f" unbanned by {ctx.author}")
            return await ctx.confirm(f"Unbanned {member.name}")
        except discord.NotFound:
            return await ctx.error("This member is not banned")

    @commands.command()
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def massunban(self: "Moderation", ctx: Context):
        """
        Unban all the banned users in the server
        """
        async with self.locks[ctx.guild.id]:
            bans = [m.user async for m in ctx.guild.bans()]
            if not bans:
                return await ctx.warn("No banned members")

            await asyncio.gather(*[ctx.guild.unban(discord.Object(m.id)) for m in bans])
            await ctx.confirm(f"Unbanned **{len(bans)}** members")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.has_guild_permissions(manage_messages=True)
    async def warn(
        self: "Moderation", ctx: Context, member: NoStaff, *, reason: str = "N/A"
    ):
        """
        Warn a member
        """
        date = datetime.datetime.now()
        await self.bot.db.execute(
            "INSERT INTO warns VALUES ($1,$2,$3,$4)",
            ctx.guild.id,
            member.id,
            f"{date.day}/{f'0{date.month}' if date.month < 10 else date.month}/{str(date.year)[-2:]}",
            reason,
        )
        await ctx.confirm(f"Warned {member.mention} - `{reason}`")

    @commands.command()
    async def warns(self: "Moderation", ctx: Context, *, member: discord.Member):
        """
        See a member warns
        """
        results = await self.bot.db.fetch(
            "SELECT * FROM warns WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member.id,
        )
        if not results:
            return await ctx.error("This member has no warns")

        await ctx.paginate(
            [f"{result['time']} - {result['reason']}" for result in results],
            title=f"Warns ({len(results)})",
        )

    @commands.command(aliases=["nick"])
    @commands.has_guild_permissions(manage_nicknames=True)
    @commands.bot_has_guild_permissions(manage_nicknames=True)
    async def nickname(
        self: "Moderation", ctx: Context, member: NoStaff, *, nick: ValidNickname
    ):
        """
        Change a member nickname
        """
        await member.edit(nick=nick)
        await ctx.confirm(f"Changed {member.mention}'s nickname")

    @commands.command(aliases=["sm"])
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def slowmode(
        self: "Moderation",
        ctx: Context,
        time: ValidTime,
        *,
        channel: discord.TextChannel = commands.CurrentChannel,
    ):
        """
        Set a time before yapping again
        """
        await channel.edit(slowmode_delay=time)
        await ctx.confirm(
            f"Set slowmode to `{format_timespan(time)}` seconds for {channel.mention}"
        )

    @commands.command(aliases=["tm", "timeout"])
    @commands.has_guild_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    async def mute(
        self: "Moderation",
        ctx: Context,
        member: Annotated[discord.Member, NoStaff],
        time: ValidTime = 3600,
        *,
        reason: str = "N/A",
    ):
        """
        Stop someones yapping
        """
        if member.is_timed_out():
            return await ctx.error("This member is already muted")

        await member.timeout(
            discord.utils.utcnow() + datetime.timedelta(seconds=time),
            reason=reason + f" muted by {ctx.author}",
        )
        await ctx.confirm(
            f"Stopped {member.mention}'s yapping for `{format_timespan(time)}`"
        )

    @commands.command(aliases=["untm", "untimeout"])
    @commands.has_guild_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    async def unmute(
        self: "Moderation", ctx: Context, member: NoStaff, *, reason: str = "N/A"
    ):
        """
        Let the person yap again
        """
        if not member.is_timed_out():
            return await ctx.error("This member is not muted")

        await member.timeout(None, reason=reason + f" unmuted by {ctx.author}")
        await ctx.confirm(f"{member.mention} can yap again")

    @commands.group(invoke_without_command=True, aliases=["p"])
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    async def purge(self: "Moderation", ctx: Context, amount: int = 10):
        """
        Delete messages from a channel
        """
        async with self.locks[ctx.channel.id]:
            await ctx.channel.purge(
                limit=amount,
                bulk=True,
                check=lambda m: not m.pinned,
                reason=f"purge invoked by {ctx.author}",
            )

    @purge.command(name="invites")
    @commands.has_guild_permissions(manage_messages=True)
    async def purge_invites(self: "Moderation", ctx: Context, amount: int = 10):
        """
        Delete messages containing invites
        """
        async with self.locks[ctx.channel.id]:
            await ctx.channel.purge(
                limit=amount,
                bulk=True,
                reason=f"purged by {ctx.author}",
                check=lambda m: re.search(
                    r"(https?://)?(www.|canary.|ptb.)?(discord.gg|discordapp.com/invite|discord.com/invite)/?[a-zA-Z0-9]+/?",
                    m.content,
                ),
            )

    @purge.command(name="bots")
    @commands.has_guild_permissions(manage_messages=True)
    async def purge_bots(self: "Moderation", ctx: Context, amount: int = 10):
        """
        Purge messages sent by bots
        """
        async with self.locks[ctx.channel.id]:
            await ctx.channel.purge(
                limit=amount,
                bulk=True,
                reason=f"purged by {ctx.author}",
                check=lambda m: m.author.bot and not m.pinned,
            )

    @purge.command(name="user")
    @commands.has_guild_permissions(manage_messages=True)
    async def purge_user(
        self: "Moderation", ctx: Context, member: discord.Member, amount: int = 10
    ):
        """
        Purge a member messages
        """
        async with self.lock[ctx.channel.id]:
            await ctx.channel.purge(
                limit=amount,
                bulk=True,
                reason=f"purged by {ctx.author}",
                check=lambda m: m.author.id == member.id and not m.pinned,
            )

    @commands.command()
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def lock(
        self: "Moderation",
        ctx: Context,
        *,
        channel: discord.TextChannel = commands.CurrentChannel,
    ):
        """
        Remove the ability of yapping in a channel
        """
        if not channel.overwrites_for(ctx.guild.default_role).send_messages:
            return await ctx.error("This channel is already locked")

        overwrites = channel.overwrites_for(ctx.guild.default_role)
        overwrites.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrites=overwrites)
        await ctx.confirm(f"Yapping ability removed from {channel.mention}")

    @commands.command()
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def unlock(
        self: "Moderation",
        ctx: Context,
        *,
        channel: discord.TextChannel = commands.CurrentChannel,
    ):
        """
        Let the yapping in the channel to continue
        """
        if channel.overwrites_for(ctx.guild.default_role).send_messages:
            return await ctx.error("This channel is not locked")

        overwrites = channel.overwrites_for(ctx.guild.default_role)
        overwrites.send_messages = True
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
        await ctx.reply(f"Yapping started again in {channel.mention}")

    @commands.command()
    @commands.server_owner()
    async def nuke(self: "Moderation", ctx: Context):
        """
        Clone a channel
        """
        async with self.locks[ctx.channel.id]:

            async def yes_callback(interaction: discord.Interaction):
                channel = await ctx.channel.clone(
                    name=interaction.channel.name,
                    reason=f"Channel nuked by {interaction.guild.owner.name}",
                )

                await channel.edit(
                    position=interaction.channel.position,
                    slowmode_delay=interaction.channel.slowmode_delay,
                    topic=interaction.channel.topic,
                    type=interaction.channel.type,
                    reason=f"Channel nuked by {interaction.guild.owner.name}",
                )

                await interaction.channel.delete(
                    reason=f"Channel nuked by {interaction.guild.owner.name}"
                )
                await channel.send("hi")

            async def no_callback(interaction: discord.Interaction):
                await interaction.response.edit_message(
                    embed=discord.Embed(
                        color=interaction.client.color, description="Aborting...."
                    ),
                    view=None,
                )

            await ctx.confirm_view(
                f"Are u sure about nukeing this channel?", yes_callback, no_callback
            )

    @commands.group(invoke_without_command=True)
    async def thread(self: "Moderation", ctx: Context):
        """
        Commands for threads
        """
        return await ctx.send_help(ctx.command)

    @thread.command(name="lock")
    @commands.has_guild_permissions(manage_threads=True)
    @commands.bot_has_guild_permissions(manage_threads=True)
    async def thread_lock(
        self: "Moderation",
        ctx: Context,
        *,
        channel: discord.Thread = commands.CurrentChannel,
    ):
        """
        Lock a thread
        """
        if not isinstance(channel, discord.Thread):
            return await ctx.error("This is not a thread channel")

        if channel.locked:
            return await ctx.error("This thread is already locked")

        await channel.edit(locked=True, reason=f"Thread locked by {ctx.author}")
        await ctx.message.add_reaction("✅")

    @thread.command(name="unlock")
    @commands.has_guild_permissions(manage_threads=True)
    @commands.bot_has_guild_permissions(manage_threads=True)
    async def thread_unlock(
        self: "Moderation",
        ctx: Context,
        *,
        channel: discord.Thread = commands.CurrentChannel,
    ):
        """
        Unlock a thread
        """
        if not isinstance(channel, discord.Thread):
            return await ctx.error("This is not a thread channel")

        if not channel.locked:
            return await ctx.error("This thread is not locked")

        await channel.edit(locked=False, reason=f"Thread unlocked by {ctx.author}")
        await ctx.message.add_reaction("✅")

    @thread.command(name="delete")
    @commands.has_guild_permissions(manage_threads=True)
    @commands.bot_has_guild_permissions(manage_threads=True)
    async def thread_delete(
        self: "Moderation",
        ctx: Context,
        *,
        channel: discord.Thread = commands.CurrentChannel,
    ):
        """
        Delete a thread
        """
        if not isinstance(channel, discord.Thread):
            return await ctx.error("This is not a thread channel")

        await channel.delete(reason=f"Thread deleted by {ctx.author}")
        await ctx.message.add_reaction("✅")

    @thread.command(name="name")
    @commands.has_guild_permissions(manage_threads=True)
    @commands.bot_has_guild_permissions(manage_threads=True)
    async def thread_name(
        self: "Moderation",
        ctx: Context,
        channel: discord.Thread = commands.CurrentChannel,
        *,
        name: str,
    ):
        """
        Rename a thread
        """
        if not isinstance(channel, discord.Thread):
            return await ctx.error("This is not a thread channel")

        await channel.edit(
            name=name, reason=f"Thread renamed by locked by {ctx.author}"
        )
        await ctx.message.add_reaction("✅")

    @thread.command(name="archive")
    @commands.has_guild_permissions(manage_threads=True)
    @commands.bot_has_guild_permissions(manage_threads=True)
    async def thread_archive(
        self: "Moderation",
        ctx: Context,
        *,
        channel: discord.Thread = commands.CurrentChannel,
    ):
        """
        Archive a thread
        """
        if not isinstance(channel, discord.Thread):
            return await ctx.error("This is not a thread channel")

        if channel.archived:
            return await ctx.error("This thread is already archived")

        await channel.edit(archived=True, reason=f"Thread archived by {ctx.author}")

    @thread.command(name="slowmode")
    @commands.has_guild_permissions(manage_threads=True)
    @commands.bot_has_guild_permissions(manage_threads=True)
    async def thread_slowmode(
        self: "Moderation",
        ctx: Context,
        channel: discord.Thread = commands.CurrentChannel,
        *,
        time: ValidTime,
    ):
        """
        Set slowmode delay for a thread
        """
        if not isinstance(channel, discord.Thread):
            return await ctx.error("This is not a thread channel")

        await channel.edit(
            slowmode_delay=time, reason=f"Thread slowmode set by {ctx.author}"
        )
        await ctx.message.add_reaction("✅")

    @commands.group(invoke_without_command=True, aliases=["r"])
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def role(
        self: "Moderation", ctx: Context, member: discord.Member, *, role: str
    ):
        """
        Add or remove user roles
        """
        roles = [await RoleConvert().convert(ctx, r) for r in role.split(", ")][:7]
        actioned = []

        async def manage_roles(role: RoleConvert):
            if role in member.roles:
                await member.remove_roles(role)
                actioned.append(f"-{role.mention}")
            else:
                await member.add_roles(role)
                actioned.append(f"+{role.mention}")

        await asyncio.gather(*[manage_roles(r) for r in roles])
        await ctx.confirm(f"Edited {member.mention}'s roles: {' '.join(actioned)}")

    @role.command(name="create")
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def role_create(self: "Moderation", ctx: Context, *, name: str):
        """
        Create a role
        """
        role = await ctx.guild.create_role(name=name)
        await ctx.confirm(f"Created {role.mention}")

    @role.command(name="delete")
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def role_delete(
        self: "Moderation", ctx: Context, *, role: Annotated[discord.Role, RoleConvert]
    ):
        """
        Delete a role
        """
        await role.delete()
        await ctx.confirm(f"Role deleted")

    @role.command(name="rename")
    @commands.has_guild_permissions(manage_roles=True)
    async def role_rename(
        self: "Moderation",
        ctx: Context,
        role: Annotated[discord.Role, RoleConvert],
        *,
        name: str,
    ):
        """
        Rename a role
        """
        await role.edit(name=name)
        await ctx.confirm(f"Renamed {role.mention} to **{name}**")

    @role.command(name="position")
    @commands.has_guild_permissions(manage_roles=True)
    async def role_position(
        self: "Moderation",
        ctx: Context,
        role: Annotated[discord.Role, RoleConvert],
        position: int,
    ):
        """
        Change a role position
        """
        await role.edit(position=position)
        await ctx.confirm(f"Moved {role.mention} to **{position}**")

    @role.command(name="hoist")
    @commands.has_guild_permissions(manage_roles=True)
    async def role_hoist(
        self: "Moderation",
        ctx: Context,
        role: Annotated[discord.Role, RoleConvert],
        hoist: bool,
    ):
        """
        Change a role hoist
        """
        await role.edit(hoist=hoist)
        await ctx.confirm(f"Changed {role.mention} hoist to **{hoist}**")


async def setup(bot: Luma):
    return await bot.add_cog(Moderation(bot))
