import asyncio
import re
from datetime import datetime, timedelta

import asyncpg
import discord
from config import color, emoji
from discord.ext import commands, tasks
from discord.utils import format_dt
from system.base.context import Context


class Config(commands.Cog):
    def __init__(self, client):
        self.client = client

    def serverinfo(self, guild):
        boosts = guild.premium_subscription_count
        user_count_with_bots = sum(not user.bot for user in guild.members)
        return boosts, user_count_with_bots

    def variables(self, message, user, guild):
        if not message:
            return "contact support: discord.gg/uid"

        placeholders = {
            "{user.mention}": user.mention,
            "{user.name}": user.name,
            "{user.id}": str(user.id),
            "{guild.name}": guild.name,
            "{guild.id}": str(guild.id),
            "{boosts}": str(guild.premium_subscription_count),
            "{user.count}": str(guild.member_count),
        }

        for key, value in placeholders.items():
            message = message.replace(key, value)

        return message

    @commands.group(description="Set the welcome", aliases=["welc"])
    @commands.has_permissions(manage_channels=True)
    async def welcome(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @welcome.command(
        name="channel", description="Set the welcome channel", aliases=["chnnel"]
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_channel(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            await ctx.warn("**Mention** a channel")
            return

        await self.client.pool.execute(
            "INSERT INTO welcome (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        await ctx.agree(f"**Set** the welcome channel to: {channel.mention}")

    @welcome.command(
        name="message", description="Set the welcome message", aliases=["msg"]
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_message(self, ctx, *, message=None):
        if message is None:
            await ctx.warn("**You're** missing text")
            return

        await self.client.pool.execute(
            "INSERT INTO welcome (guild_id, message) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET message = $2",
            ctx.guild.id,
            message,
        )
        await ctx.agree(f"**Set** the welcome message to: `{message}`")

    @welcome.command(name="clear", description="Clear all welcome settings")
    @commands.has_permissions(manage_channels=True)
    async def welcome_clear(self, ctx):
        await self.client.pool.execute(
            "DELETE FROM welcome WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all welcome settings")

    @welcome.command(name="remove", description="Remove the welcome channel")
    @commands.has_permissions(manage_channels=True)
    async def welcome_remove(self, ctx):
        existing = await self.client.pool.fetchrow(
            "SELECT channel_id FROM welcome WHERE guild_id = $1", ctx.guild.id
        )
        if existing:
            await self.client.pool.execute(
                "DELETE FROM welcome WHERE guild_id = $1", ctx.guild.id
            )
            await ctx.agree("**Removed** the welcome channel")
        else:
            await ctx.deny("A channel isn't **set**")

    @welcome.command(name="test", description="Try testing the welcome")
    @commands.has_permissions(manage_channels=True)
    async def welcome_test(self, ctx):
        settings = await self.client.pool.fetchrow(
            "SELECT channel_id, message FROM welcome WHERE guild_id = $1", ctx.guild.id
        )
        if not settings:
            await ctx.deny("**Could not** find any welcome settings for this guild")
            return

        channel = ctx.guild.get_channel(settings["channel_id"])
        if not channel:
            await ctx.warn("**Could not** find the welcome channel")
            return

        if not settings["message"]:
            await ctx.warn("**Could not** find the welcome message")
            return

        message = self.variables(settings["message"], ctx.author, ctx.guild)
        await ctx.agree(f"**Sent** the welcome message to: {channel.mention}")
        await channel.send(message)

    @commands.group(description="Set the goodbye", aliases=["leave"])
    @commands.has_permissions(manage_channels=True)
    async def goodbye(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @goodbye.command(
        name="channel", description="Set the goodbye channel", aliases=["chnnel"]
    )
    @commands.has_permissions(manage_channels=True)
    async def goodbye_channel(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            await ctx.warn("**Mention** a channel")
            return
        await self.client.pool.execute(
            "INSERT INTO goodbye (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        await ctx.agree(f"**Set** the goodbye channel to: {channel.mention}")

    @goodbye.command(
        name="message", description="Set the goodbye message", aliases=["msg"]
    )
    @commands.has_permissions(manage_channels=True)
    async def goodbye_message(self, ctx, *, message=None):
        if message is None:
            await ctx.warn("**You're** missing text")
            return

        await self.client.pool.execute(
            "INSERT INTO goodbye (guild_id, message) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET message = $2",
            ctx.guild.id,
            message,
        )
        await ctx.agree(f"**Set** the goodbye message to: `{message}`")

    @goodbye.command(name="clear", description="Clear all goodbye settings")
    @commands.has_permissions(manage_channels=True)
    async def goodbye_clear(self, ctx):
        await self.client.pool.execute(
            "DELETE FROM goodbye WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all goodbye settings")

    @goodbye.command(name="remove", description="Remove the goodbye channel")
    @commands.has_permissions(manage_channels=True)
    async def goodbye_remove(self, ctx):
        existing = await self.client.pool.fetchrow(
            "SELECT channel_id goodbye WHERE guild_id = $1", ctx.guild.id
        )
        if existing:
            await self.client.pool.execute(
                "DELETE FROM goodbye WHERE guild_id = $1", ctx.guild.id
            )
            await ctx.agree("**Removed** the goodbye channel")
        else:
            await ctx.deny("A channel isn't **set**")

    @goodbye.command(name="test", description="Try testing the goodbye")
    @commands.has_permissions(manage_channels=True)
    async def goodbye_test(self, ctx):
        settings = await self.client.pool.fetchrow(
            "SELECT channel_id, message FROM goodbye WHERE guild_id = $1", ctx.guild.id
        )
        if not settings:
            await ctx.deny("**Could not** find any goodbye settings for this guild")
            return

        channel = ctx.guild.get_channel(settings["channel_id"])
        if not channel:
            await ctx.warn("**Could not** find the goodbye channel")
            return

        if not settings["message"]:
            await ctx.warn("**Could not** find the goodbye message")
            return

        message = self.variables(settings["message"], ctx.author, ctx.guild)
        await ctx.agree(f"**Sent** the goodbye message to: {channel.mention}")
        await channel.send(message)

    @commands.group(description="Set the boost")
    @commands.has_permissions(manage_channels=True)
    async def boost(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @boost.command(
        name="channel", description="Set the boost channel", aliases=["chnnel"]
    )
    @commands.has_permissions(manage_channels=True)
    async def boost_channel(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            await ctx.warn("**Mention** a channel")
            return
        await self.client.pool.execute(
            "INSERT INTO boost (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        await ctx.agree(f"**Set** the boost channel to: {channel.mention}")

    @boost.command(name="message", description="Set the boost message", aliases=["msg"])
    @commands.has_permissions(manage_channels=True)
    async def boost_message(self, ctx, *, message=None):
        if message is None:
            await ctx.warn("**You're** missing text")
            return

        await self.client.pool.execute(
            "INSERT INTO boost (guild_id, message) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET message = $2",
            ctx.guild.id,
            message,
        )
        await ctx.agree(f"**Set** the boost message to: `{message}`")

    @boost.command(name="clear", description="Clear all boost settings")
    @commands.has_permissions(manage_channels=True)
    async def boost_clear(self, ctx):
        await self.client.pool.execute(
            "DELETE FROM boost WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all boost settings")

    @boost.command(name="remove", description="Remove the goodbye channel")
    @commands.has_permissions(manage_channels=True)
    async def boost_remove(self, ctx):
        existing = await self.client.pool.fetchrow(
            "SELECT channel_id FROM boost WHERE guild_id = $1", ctx.guild.id
        )
        if existing:
            await self.client.pool.execute(
                "DELETE FROM boost WHERE guild_id = $1", ctx.guild.id
            )
            await ctx.agree("**Removed** the boost channel")
        else:
            await ctx.deny("A channel isn't **set**")

    @boost.command(name="test", description="Try testing the boost")
    @commands.has_permissions(manage_channels=True)
    async def boost_test(self, ctx):
        settings = await self.client.pool.fetchrow(
            "SELECT channel_id, message FROM boost WHERE guild_id = $1", ctx.guild.id
        )
        if not settings:
            await ctx.deny("**Could not** find any boost settings for this guild")
            return

        channel = ctx.guild.get_channel(settings["channel_id"])
        if not channel:
            await ctx.warn("**Could not** find the boost channel")
            return

        if not settings["message"]:
            await ctx.warn("**Could not** find the boost message")
            return

        message = self.variables(settings["message"], ctx.author, ctx.guild)
        await ctx.agree(f"**Sent** the boost message to: {channel.mention}")
        await channel.send(message)

    @commands.group(description="Add roles to new users", aliases=["ar"])
    @commands.has_permissions(administrator=True)
    async def autorole(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @autorole.command(name="add", description="Add a role to autorole")
    @commands.has_permissions(administrator=True)
    async def autorole_add(self, ctx: Context, *roles: discord.Role):
        if not roles:
            await ctx.warn("**Mention** a role")
            return

        highest = ctx.guild.me.top_role
        if any(role.position >= highest.position for role in roles):
            await ctx.deny(
                "Put the bot's role **higher** than the role you want to give out"
            )
            return

        added = []
        existing = []

        for role in roles:
            record = await self.client.pool.fetchrow(
                "SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )

            if record:
                existing.append(role.mention)
            else:
                await self.client.pool.execute(
                    "INSERT INTO autorole (guild_id, role_id) VALUES ($1, $2)",
                    ctx.guild.id,
                    role.id,
                )
                added.append(role.mention)

        if added:
            await ctx.agree(f"**Added** {', '.join(added)} to autorole")

        if existing:
            await ctx.warn(f"**Already** giving out: {', '.join(existing)}")

    @autorole.command(name="fix", description="Remove deleted roles from autorole")
    @commands.has_permissions(administrator=True)
    async def autorole_fix(self, ctx: Context):
        autorole_records = await self.client.pool.fetch(
            "SELECT role_id FROM autorole WHERE guild_id = $1", ctx.guild.id
        )

        deleted_roles = []
        for record in autorole_records:
            role = ctx.guild.get_role(record["role_id"])
            if role is None:
                await self.client.pool.execute(
                    "DELETE FROM autorole WHERE guild_id = $1 AND role_id = $2",
                    ctx.guild.id,
                    record["role_id"],
                )
                deleted_roles.append(record["role_id"])

        if deleted_roles:
            await ctx.agree(f"**Removed** {len(deleted_roles)} roles")
        else:
            await ctx.deny("**No** deleted roles")

    @autorole.command(name="remove", description="Remove a role from autorole")
    @commands.has_permissions(administrator=True)
    async def autorole_remove(self, ctx: Context, *roles: discord.Role):
        if not roles:
            await ctx.warn("**Mention** a role")
            return

        for role in roles:
            existing_role = await self.client.pool.fetchrow(
                "SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )
            if not existing_role:
                await ctx.deny(f"{role.mention} was **never** given out")
                return

            await self.client.pool.execute(
                "DELETE FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )

        await ctx.agree(f"**Removed** {role.mention} from autorole")

    @autorole.command(name="list", description="Check the autorole list")
    @commands.has_permissions(administrator=True)
    async def autorole_list(self, ctx):
        roles = await self.client.pool.fetch(
            "SELECT role_id FROM autorole WHERE guild_id = $1", ctx.guild.id
        )

        if not roles:
            await ctx.deny("No roles are currently added")
            return

        roles_list = "\n> ".join(
            [ctx.guild.get_role(role["role_id"]).mention for role in roles]
        )
        user_pfp = (
            ctx.author.avatar.url
            if ctx.author.avatar
            else ctx.author.default_avatar.url
        )

        embed = discord.Embed(color=color.default)
        embed.set_author(name=f"{ctx.author.name} | Autorole list", icon_url=user_pfp)
        embed.add_field(name="", value=f"> {roles_list}")
        await ctx.send(embed=embed)

    @autorole.command(name="clear", description="Clear all autorole settings")
    @commands.has_permissions(manage_channels=True)
    async def autorole_clear(self, ctx: Context):
        await self.client.pool.execute(
            "DELETE FROM autorole WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all autorole settings")

    @commands.group(
        description="Track available and old stuff", aliases=["track", "trackers"]
    )
    @commands.has_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def tracker(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @tracker.command(
        name="vanity", description="Track available and old vanities", aliases=["van"]
    )
    @commands.has_permissions(manage_channels=True)
    async def tracker_vanity(
        self, ctx: commands.Context, channel: commands.TextChannelConverter = None
    ):
        guild_id = ctx.guild.id

        if channel is None:
            await ctx.warn("**Mention** a channel")
            return

        result = await self.client.pool.fetchrow(
            "SELECT channel_id FROM vanity WHERE guild_id = $1", guild_id
        )
        if result is not None:
            await ctx.deny(f"Vanity channel is already **set**")
            return

        await self.client.pool.execute(
            "INSERT INTO vanity (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET channel_id = EXCLUDED.channel_id",
            guild_id,
            channel.id,
        )
        await ctx.agree(f"**Set** the vanity channel to: {channel.mention}")

    @tracker.command(
        name="username",
        description="Track available and old usernames",
        aliases=["user", "users", "usernames"],
    )
    @commands.has_permissions(manage_channels=True)
    async def tracker_username(
        self, ctx: commands.Context, channel: commands.TextChannelConverter = None
    ):
        guild_id = ctx.guild.id

        if channel is None:
            await ctx.warn("**Mention** a channel")
            return

        result = await self.client.pool.fetchrow(
            "SELECT channel_id FROM username WHERE guild_id = $1", guild_id
        )
        if result is not None:
            await ctx.deny(f"Username channel is **already** set")
            return

        await self.client.pool.execute(
            "INSERT INTO username (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET channel_id = EXCLUDED.channel_id",
            guild_id,
            channel.id,
        )
        await ctx.agree(f"**Set** the username channel to: {channel.mention}")

    @tracker.command(name="clear", description="Clear all tracker settings")
    @commands.has_permissions(manage_channels=True)
    async def tracker_clear(self, ctx: commands.Context, option: str):
        guild_id = ctx.guild.id

        if option.lower() == "vanity":
            await self.client.pool.execute(
                "DELETE FROM vanity WHERE guild_id = $1", guild_id
            )
            await ctx.agree("**Cleared** all vanity settings")

        elif option.lower() == "username":
            await self.client.pool.execute(
                "DELETE FROM username WHERE guild_id = $1", guild_id
            )
            await ctx.agree("**Cleared** all username settings")

        else:
            await ctx.deny("**Invalid option,** use either vanity or username")

    @commands.group(
        description="Ping people in channels on their join",
        aliases=["poj", "joinping", "ghostping"],
    )
    @commands.has_permissions(manage_channels=True)
    async def pingonjoin(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @pingonjoin.command(name="add", description="Add a channel to pingonjoin")
    @commands.has_permissions(manage_channels=True)
    async def pingonjoin_add(self, ctx, channel: discord.TextChannel):
        existing = await self.client.pool.fetchrow(
            "SELECT * FROM pingonjoin WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )

        if existing:
            await ctx.deny(f"That channel is **already** added to pingonjoin")
        else:
            await self.client.pool.fetchrow(
                "INSERT INTO pingonjoin (guild_id, channel_id) VALUES ($1, $2)",
                ctx.guild.id,
                channel.id,
            )
            await ctx.agree(f"**Added** {channel.mention} to pingonjoin")

    @pingonjoin.command(name="remove", description="Remove a channel from pingonjoin")
    @commands.has_permissions(manage_channels=True)
    async def pingonjoin_remove(self, ctx, channel: discord.TextChannel):
        existing = await self.client.pool.fetchrow(
            "SELECT * FROM pingonjoin WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )

        if existing:
            await self.client.pool.fetchrow(
                "DELETE FROM pingonjoin WHERE guild_id = $1 AND channel_id = $2",
                ctx.guild.id,
                channel.id,
            )
            await ctx.agree(f"**Removed** {channel.mention} from pingonjoin")
        else:
            await ctx.deny(f"A channel isn't **added**")

    @pingonjoin.command(name="list", description="Check the pingonjoin channel list")
    @commands.has_permissions(manage_channels=True)
    async def pingonjoin_list(self, ctx):
        channels = await self.client.pool.fetch(
            "SELECT channel_id FROM pingonjoin WHERE guild_id = $1", ctx.guild.id
        )

        if not channels:
            await ctx.deny("No channels are currently added")
            return

        channel_mentions = "\n> ".join(
            [f"<#{record['channel_id']}>" for record in channels]
        )
        user_pfp = (
            ctx.author.avatar.url
            if ctx.author.avatar
            else ctx.author.default_avatar.url
        )

        embed = discord.Embed(color=color.default)
        embed.set_author(name=f"{ctx.author.name} | Pingonjoin list", icon_url=user_pfp)
        embed.add_field(name="", value=f"> {channel_mentions}")

        await ctx.send(embed=embed)

    @pingonjoin.command(name="clear", description="Clear all pingonjoin settings")
    @commands.has_permissions(manage_channels=True)
    async def pingonjoin_clear(self, ctx):
        await self.client.pool.execute(
            "DELETE FROM pingonjoin WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all pingonjoin settings")

    @commands.group(
        description="Respond to certain messages", aliases=["autoresp", "ap"]
    )
    @commands.has_permissions(manage_messages=True)
    async def autorespond(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @autorespond.command(name="add", description="Add a response to a trigger")
    @commands.has_permissions(manage_messages=True)
    async def autorespond_add(self, ctx, *, args):
        args_split = args.split(",")
        if len(args_split) < 2:
            await ctx.deny("**Invalid argument,** `u stink**,** no i dont`")
            return
        trigger, response = args_split[0].strip().lower(), args_split[1].strip()
        await self.client.pool.fetchrow(
            "INSERT INTO autorespond (guild_id, trigger, response) VALUES ($1, $2, $3)",
            ctx.guild.id,
            trigger,
            response,
        )
        await ctx.agree(f"`{trigger}` will **now** respond to: `{response}`")

    @autorespond.command(name="remove", description="Remove a response from a trigger")
    @commands.has_permissions(manage_messages=True)
    async def autorespond_remove(self, ctx, *, trigger):
        result = await self.client.pool.fetchrow(
            "DELETE FROM autorespond WHERE guild_id = $1 AND trigger = $2",
            ctx.guild.id,
            trigger,
        )
        await ctx.agree(
            f"**Removed** trigger" if result != "DELETE 0" else "Trigger not found"
        )

    @autorespond.command(name="list", description="Check the autorespond list")
    @commands.has_permissions(manage_messages=True)
    async def autorespond_list(self, ctx):
        responses = await self.client.pool.fetchrow(
            "SELECT trigger, response FROM autorespond WHERE guild_id = $1",
            ctx.guild.id,
        )

        if not responses:
            await ctx.deny("No autorespond triggers are currently added")
            return

        user_pfp = (
            ctx.author.avatar.url
            if ctx.author.avatar
            else ctx.author.default_avatar.url
        )
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(
            name=f"{ctx.author.name} | Autorespond List", icon_url=user_pfp
        )

        for record in responses:
            embed.add_field(
                name=record["trigger"], value=f"> {record['response']}", inline=False
            )

        await ctx.send(embed=embed)

    @autorespond.command(name="clear", description="Clear all autorespond settings")
    @commands.has_permissions(manage_messages=True)
    async def autorespond_clear(self, ctx):
        await self.client.pool.fetchrow(
            "DELETE FROM autorespond WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all autorespond settings")

    @commands.group(
        description="React to certain messages with emojis", aliases=["autorea", "ac"]
    )
    @commands.has_permissions(manage_messages=True)
    async def autoreact(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @autoreact.command(name="add", description="Add a reaction to a trigger")
    @commands.has_permissions(manage_messages=True)
    async def autoreact_add(self, ctx, *, args):
        args_split = args.split(",")
        if len(args_split) < 2:
            await ctx.deny("**Invalid argument,** `u stink **,** 🤓`")
            return
        trigger, emoji = args_split[0].strip().lower(), args_split[1].strip()
        await self.client.pool.fetchrow(
            "INSERT INTO autoreact (guild_id, trigger, emoji) VALUES ($1, $2, $3)",
            ctx.guild.id,
            trigger,
            emoji,
        )
        await ctx.agree(f"'{trigger}' will **now** react to: '{emoji}'")

    @autoreact.command(name="remove", description="Remove a reaction from a trigger")
    @commands.has_permissions(manage_messages=True)
    async def autoreact_remove(self, ctx, *, trigger):
        result = await self.client.pool.fetchrow(
            "DELETE FROM autoreact WHERE guild_id = $1 AND trigger = $2",
            ctx.guild.id,
            trigger,
        )
        await ctx.agree(
            f"**Removed** trigger" if result != "DELETE 0" else "Trigger not found"
        )

    @autoreact.command(name="list", description="Check the autoreact list")
    @commands.has_permissions(manage_messages=True)
    async def autoreact_list(self, ctx):
        reacts = await self.client.pool.fetchrow(
            "SELECT trigger, emoji FROM autoreact WHERE guild_id = $1", ctx.guild.id
        )

        if not reacts:
            await ctx.deny("No autoreact triggers are currently added")
            return

        user_pfp = (
            ctx.author.avatar.url
            if ctx.author.avatar
            else ctx.author.default_avatar.url
        )
        embed = discord.Embed(color=color.default)
        embed.set_author(name=f"{ctx.author.name} | Autoreact List", icon_url=user_pfp)

        for record in reacts:
            embed.add_field(
                name=record["trigger"], value=f"> {record['emoji']}", inline=False
            )

        await ctx.send(embed=embed)

    @autoreact.command(name="clear", description="Clear all autoreact settings")
    @commands.has_permissions(manage_messages=True)
    async def autoreact_clear(self, ctx):
        await self.client.pool.fetchrow(
            "DELETE FROM autoreact WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all autoreact settings")

    @commands.group(description="Change messages for multiple commands")
    @commands.has_permissions(manage_guild=True)
    async def invoke(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @invoke.command(name="ban", description="Change the response from ban")
    @commands.has_permissions(manage_guild=True)
    async def invoke_ban(self, ctx, *, message=None):
        if message is None:
            await ctx.warn("**You're** missing text")
            return

        await self.client.pool.fetchrow(
            "INSERT INTO invoke (guild_id, command, message) VALUES ($1, $2, $3) ON CONFLICT (guild_id, command) DO UPDATE SET message = EXCLUDED.message",
            ctx.guild.id,
            "ban",
            message,
        )
        await ctx.agree(f"**Set** the ban message to: `{message}`")

    @invoke.command(name="softban", description="Change the response from softban")
    @commands.has_permissions(manage_guild=True)
    async def invoke_softban(self, ctx, *, message=None):
        if message is None:
            await ctx.warn("**You're** missing text")
            return

        await self.client.pool.fetchrow(
            "INSERT INTO invoke (guild_id, command, message) VALUES ($1, $2, $3) ON CONFLICT (guild_id, command) DO UPDATE SET message = EXCLUDED.message",
            ctx.guild.id,
            "softban",
            message,
        )
        await ctx.agree(f"**Set** the softban message to: `{message}`")

    @invoke.command(name="unban", description="Change the response from unban")
    @commands.has_permissions(manage_guild=True)
    async def invoke_unban(self, ctx, *, message=None):
        if message is None:
            await ctx.warn("**You're** missing text")
            return

        await self.client.pool.fetchrow(
            "INSERT INTO invoke (guild_id, command, message) VALUES ($1, $2, $3) ON CONFLICT (guild_id, command) DO UPDATE SET message = EXCLUDED.message",
            ctx.guild.id,
            "unban",
            message,
        )
        await ctx.agree(f"**Set** the unban message to: `{message}`")

    @invoke.command(name="kick", description="Change the response from kick")
    @commands.has_permissions(manage_guild=True)
    async def invoke_kick(self, ctx, *, message=None):
        if message is None:
            await ctx.warn("**You're** missing text")
            return

        await self.client.pool.fetchrow(
            "INSERT INTO invoke (guild_id, command, message) VALUES ($1, $2, $3) ON CONFLICT (guild_id, command) DO UPDATE SET message = EXCLUDED.message",
            ctx.guild.id,
            "kick",
            message,
        )
        await ctx.agree(f"**Set** the kick message to: `{message}`")

    @invoke.command(name="clear", description="Clear all invoke settings")
    @commands.has_permissions(manage_guild=True)
    async def invoke_clear(self, ctx, command=None):
        if command is None or command not in ["ban", "softban", "unban", "kick"]:
            await ctx.deny("**Invalid option,** use either ban, softban, unban or kick")
            return

        await self.db.execute(
            "DELETE FROM invoke WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            command,
        )
        await ctx.agree(f"**Cleared** all {command} settings")

    @commands.group(description="DM people when they join")
    @commands.has_permissions(manage_guild=True)
    async def joindm(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @joindm.command(name="clear", description="Clear all joindm settings")
    async def joindm_clear(self, ctx):
        await self.client.pool.fetchrow(
            "DELETE FROM joindm WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all joindm settings")

    @joindm.command(name="message", description="Set the joindm message")
    async def joindm_message(self, ctx, *, message=None):
        if message is None:
            await ctx.warn("**You're** missing text")
            return

        await self.client.pool.fetchrow(
            "INSERT INTO joindm (guild_id, message) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET message = EXCLUDED.message",
            ctx.message.guild.id,
            message,
        )
        await ctx.agree(f"**Set** the joindm message to: `{message}`")

    @commands.group(description="Configure reaction roles for messages", aliases=["rr"])
    @commands.has_permissions(manage_channels=True)
    async def reactionroles(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @reactionroles.command(name="add", description="Add a reaction role to a message")
    @commands.has_permissions(manage_roles=True)
    async def reactionroles_add(
        self,
        ctx,
        role: discord.Role = None,
        message: discord.Message = None,
        emoji: str = None,
    ):
        if role is None:
            await ctx.warn("**Mention** a role")
            return

        if message is None:
            await ctx.warn("You're **missing** a message")
            return

        if emoji is None:
            await ctx.warn("You're **missing** an emoji")
            return

        await self.client.pool.execute(
            "INSERT INTO reactionroles (guild_id, message_id, emoji, role_id) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
            ctx.guild.id,
            message.id,
            emoji,
            role.id,
        )
        await message.add_reaction(emoji)
        await ctx.agree(
            f"**Added** {role.mention} with the emoji {emoji} on the message {message.id}"
        )

    @reactionroles.command(
        name="remove", description="Remove a reaction role from a message"
    )
    @commands.has_permissions(manage_roles=True)
    async def reactionroles_remove(
        self,
        ctx,
        role: discord.Role = None,
        message: discord.Message = None,
        emoji: str = None,
    ):
        if role is None:
            await ctx.warn("**Mention** a role")
            return

        if message is None:
            await ctx.warn("You're **missing** a message")
            return

        if emoji is None:
            await ctx.warn("You're **missing** an emoji")
            return

        await self.client.pool.execute(
            "DELETE FROM reactionroles WHERE guild_id = $1 AND message_id = $2 AND emoji = $3 AND role_id = $4",
            ctx.guild.id,
            message.id,
            emoji,
            role.id,
        )
        await message.clear_reaction(emoji)
        await ctx.agree(
            f"**Removed** {role.mention} with the emoji {emoji} from the message {message.id}"
        )

    @reactionroles.command(name="clear", description="Clear all reactionrole settings")
    @commands.has_permissions(manage_roles=True)
    async def reactionroles_clear(self, ctx):
        await self.db.execute(
            "DELETE FROM reactionroles WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all reactionroles settings")

    @reactionroles.command(name="list", description="Check out the reactionrole list")
    @commands.has_permissions(administrator=True)
    async def reactionroles_list(self, ctx):
        records = await self.client.pool.fetch(
            "SELECT * FROM reactionroles WHERE guild_id = $1", ctx.guild.id
        )

        if not records:
            await ctx.deny("**No** reactionroles are currently added")
            return

        user_pfp = (
            ctx.author.avatar.url
            if ctx.author.avatar
            else ctx.author.default_avatar.url
        )

        embed = discord.Embed(color=color.default)
        embed.set_author(
            name=f"{ctx.author.name} | Reactionroles list", icon_url=user_pfp
        )
        for record in records:
            role = ctx.guild.get_role(record["role_id"])
            if role:
                embed.add_field(
                    name=f"Message ID: `{record['message_id']}`",
                    value=f"> Emoji: {record['emoji']} \n> Role: {role.mention}",
                    inline=False,
                )
        await ctx.send(embed=embed)

    # events

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        res = await self.client.pool.fetchrow(
            "SELECT * FROM goodbye WHERE guild_id = $1", member.guild.id
        )
        if res:
            channel = member.guild.get_channel(res["channel_id"])
            if channel is None:
                return
            message = self.variables(res["message"], member, member.guild)
            await channel.send(content=message)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.type == discord.MessageType.premium_guild_subscription:
            res = await self.client.pool.fetchrow(
                "SELECT * FROM boost WHERE guild_id = $1", message.guild.id
            )
            if res:
                channel = message.guild.get_channel(res["channel_id"])
                if channel is None:
                    return
                msg = self.variables(res["message"], message.author, message.guild)
                await channel.send(content=msg)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if (
            not before.guild.premium_subscriber_role in before.roles
            and after.guild.premium_subscriber_role in after.roles
        ):
            res = await self.client.pool.fetchrow(
                "SELECT * FROM boost WHERE guild_id = $1", before.guild.id
            )
            if res:
                channel = before.guild.get_channel(res["channel_id"])
                if channel is None:
                    return
                msg = self.variables(res["message"], before, before.guild)
                await channel.send(content=msg)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if not before.bot and str(before) != str(after):
            channel_ids = await self.client.pool.fetch(
                "SELECT channel_id FROM username"
            )

            availability_date = datetime.now() + timedelta(days=14)
            formatted_date = format_dt(availability_date, style="R")

            for row in channel_ids:
                channel_id = row["channel_id"]
                if channel := self.client.get_channel(channel_id):
                    await asyncio.sleep(0.1)
                    await channel.send(
                        f"The username **{before}** is available {formatted_date}"
                    )

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.vanity_url_code and before.vanity_url_code != after.vanity_url_code:
            channel_ids = await self.client.pool.fetch("SELECT channel_id FROM vanity")

            for row in channel_ids:
                channel_id = row["channel_id"]
                if channel := self.client.get_channel(channel_id):
                    await asyncio.sleep(0.1)
                    await channel.send(
                        f"The vanity **/{before.vanity_url_code}** is available"
                    )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        welc = await self.client.pool.fetchrow(
            "SELECT channel_id, message FROM welcome WHERE guild_id = $1",
            member.guild.id,
        )
        if welc:
            welcome_channel = member.guild.get_channel(welc["channel_id"])
            if welcome_channel:
                welcome_message = self.variables(welc["message"], member, member.guild)
                await welcome_channel.send(content=welcome_message)

        autoroles = await self.client.pool.fetch(
            "SELECT role_id FROM autorole WHERE guild_id = $1", member.guild.id
        )
        if autoroles:
            for record in autoroles:
                role = member.guild.get_role(record["role_id"])
                if role:
                    await member.add_roles(role, reason="Autorole")

        pingjoin = await self.client.pool.fetch(
            "SELECT channel_id FROM pingonjoin WHERE guild_id = $1", member.guild.id
        )
        if pingjoin:
            for record in pingjoin:
                ping_channel = member.guild.get_channel(record["channel_id"])
                if ping_channel:
                    msg = await ping_channel.send(f"{member.mention}")
                    await asyncio.sleep(0.2)
                    await msg.delete()

        joindm = await self.client.pool.fetchrow(
            "SELECT message FROM joindm WHERE guild_id = $1", member.guild.id
        )
        if joindm:
            message = joindm["message"]
            joindm_message = self.variables(message, member, member.guild)
            try:
                await member.send(joindm_message)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_id = message.guild.id

        response_records = await self.client.pool.fetch(
            "SELECT trigger, response FROM autorespond WHERE guild_id = $1", guild_id
        )

        for record in response_records:
            trigger = record["trigger"].strip().lower()
            if trigger in message.content.lower():
                await message.channel.send(record["response"])
                break

        react_records = await self.client.pool.fetch(
            "SELECT trigger, emoji FROM autoreact WHERE guild_id = $1", guild_id
        )

        for record in react_records:
            trigger = record["trigger"].strip().lower()
            if trigger in message.content.lower():
                await message.add_reaction(record["emoji"])
                break

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.guild_id is None:
            return

        guild = self.client.get_guild(payload.guild_id)
        role_data = await self.client.pool.fetchrow(
            "SELECT role_id FROM reactionroles WHERE guild_id = $1 AND message_id = $2 AND emoji = $3",
            payload.guild_id,
            payload.message_id,
            str(payload.emoji),
        )

        if role_data:
            role = guild.get_role(role_data["role_id"])
            if role:
                member = guild.get_member(payload.user_id)
                if member:
                    await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.guild_id is None:
            return

        guild = self.client.get_guild(payload.guild_id)
        role_data = await self.client.pool.fetchrow(
            "SELECT role_id FROM reactionroles WHERE guild_id = $1 AND message_id = $2 AND emoji = $3",
            payload.guild_id,
            payload.message_id,
            str(payload.emoji),
        )

        if role_data:
            role = guild.get_role(role_data["role_id"])
            if role:
                member = guild.get_member(payload.user_id)
                if member:
                    await member.remove_roles(role)


async def setup(client):
    await client.add_cog(Config(client))
