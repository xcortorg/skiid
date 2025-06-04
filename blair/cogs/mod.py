import asyncio
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Bot, hybrid_command
from tools.config import color
from tools.context import Context


class Moderation(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    def time(self, time_value: int, unit: str) -> int:
        return time_value * {"m": 60, "h": 3600, "d": 86400}.get(unit, 0)

    async def send_agree(self, ctx, message):
        await ctx.agree(message)

    @hybrid_command(aliases=["k"])
    @app_commands.describe(member="The member to kick")
    @commands.has_permissions(kick_members=True)
    async def kick(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = "None"
    ):
        await member.kick(reason=reason)
        await self.send_agree(
            ctx, f"**Kicked** {member.mention} with reason: `{reason}`"
        )

    @hybrid_command(aliases=["bn"])
    @app_commands.describe(member="The member to ban")
    @commands.has_permissions(ban_members=True)
    async def ban(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = "None"
    ):
        await member.ban(reason=reason)
        await self.send_agree(
            ctx, f"**Banned** {member.mention} with reason: `{reason}`"
        )

    @hybrid_command(aliases=["unb"])
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: str = "None"):
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        await self.send_agree(ctx, f"**Unbanned** <@{user_id}> with reason: `{reason}`")

    @hybrid_command(aliases=["mt"])
    @commands.has_permissions(ban_members=True)
    async def mute(self, ctx: Context, member: discord.Member, duration: str = "5m"):
        if member.top_role >= ctx.author.top_role:
            return await ctx.deny(
                "You **cannot** mute someone with an equal or higher role"
            )

        unit = duration[-1]
        if unit not in {"m", "h", "d"}:
            return await ctx.deny("**Invalid format,** use minutes, hours, or days")

        try:
            time_value = int(duration[:-1])
        except ValueError:
            return await ctx.warn("You're **missing** time")

        seconds = self.time(time_value, unit)
        mute_until = discord.utils.utcnow() + timedelta(seconds=seconds)
        await member.timeout(mute_until)
        await self.send_agree(
            ctx, f"**Muted** {member.mention} for {time_value} {unit}."
        )

    @hybrid_command(aliases=["unm"])
    @commands.has_permissions(ban_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        await member.edit(timed_out_until=None)
        await self.send_agree(ctx, f"**Unmuted** {member.mention}")

    @commands.command(description="Purge messages", aliases=["pr"])
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = None):
        if amount is None:
            return await ctx.warn("You're **missing** a number")
        if not (1 <= amount <= 100):
            return await ctx.warn("You can only delete between 1 and 100 messages.")

        deleted_messages = await ctx.channel.purge(limit=amount + 1)
        await self.send_agree(ctx, f"**Purged** {len(deleted_messages) - 1} messages.")

    @commands.command(description="Lock a channel")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: Context, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await self.send_agree(ctx, f"**Locked** {channel.mention}")

    @commands.command(description="Unlock a channel")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: Context, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await self.send_agree(ctx, f"**Unlocked** {channel.mention}")

    @hybrid_command(aliases=["ca"])
    @commands.has_permissions(manage_channels=True)
    async def channelattachments(
        self, ctx: commands.Context, channel: discord.TextChannel = None, *, action: str
    ):
        """Toggle attachment permissions for a channel. Use 'on' to allow attachments or 'off' to disallow."""
        channel = channel or ctx.channel
        action = action.lower()

        if action not in {"on", "off"}:
            return await ctx.deny("Please specify `on` or `off`.")

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.read_messages = action == "on"

        asyncio.create_task(
            channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        )
        await ctx.agree(
            f"**Attachment permissions turned {action}** for {channel.mention}"
        )

    @hybrid_command(aliases=["chc"])
    @commands.has_permissions(manage_channels=True)
    async def channelcreate(self, ctx: commands.Context, name: str):
        """Create a new text channel with the specified name."""

        async def create_channel():
            channel = await ctx.guild.create_text_channel(name)
            await ctx.agree(f"**Created** channel: {channel.mention}")

        asyncio.create_task(create_channel())

    @hybrid_command(aliases=["cd"])
    @commands.has_permissions(manage_channels=True)
    async def channeldelete(self, ctx: commands.Context, channel: discord.TextChannel):
        """Delete the specified text channel."""

        async def delete_channel():
            await channel.delete()
            await ctx.agree(f"**Deleted** channel: {channel.name}")

        asyncio.create_task(delete_channel())

    @hybrid_command(aliases=["cpt"])
    @commands.has_permissions(manage_channels=True)
    async def channelpermit(
        self,
        ctx: commands.Context,
        member: discord.Member,
        channel: discord.TextChannel,
    ):
        """Grant the specified member access to view the specified channel."""
        overwrite = channel.overwrites_for(member)
        overwrite.read_messages = True

        asyncio.create_task(channel.set_permissions(member, overwrite=overwrite))
        await ctx.agree(f"**Permitted** {member.mention} to view {channel.mention}")

    @hybrid_command(aliases=["cpriv"])
    @commands.has_permissions(manage_channels=True)
    async def channelprivate(
        self, ctx: commands.Context, channel: discord.TextChannel = None, *, action: str
    ):
        """Make the specified channel private ('on') or public ('off')."""
        channel = channel or ctx.channel
        action = action.lower()

        if action not in {"on", "off"}:
            return await ctx.deny("Please specify `on` or `off`.")

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.read_messages = action == "off"

        asyncio.create_task(
            channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        )
        await ctx.agree(f"**Private mode turned {action}** for {channel.mention}")

    @hybrid_command(aliases=["crn"])
    @commands.has_permissions(manage_channels=True)
    async def channelrename(
        self, ctx: commands.Context, channel: discord.TextChannel, *, new_name: str
    ):
        """Rename the specified channel to the new name."""

        async def rename_channel():
            await channel.edit(name=new_name)
            await ctx.agree(f"**Renamed** channel to: {new_name}")

        asyncio.create_task(rename_channel())

    @hybrid_command(aliases=["crv"])
    @commands.has_permissions(manage_channels=True)
    async def channelrevoke(
        self,
        ctx: commands.Context,
        member: discord.Member,
        channel: discord.TextChannel,
    ):
        """Revoke the specified member's permission to view the specified channel."""
        overwrite = channel.overwrites_for(member)
        overwrite.read_messages = False

        asyncio.create_task(channel.set_permissions(member, overwrite=overwrite))
        await ctx.agree(
            f"**Revoked** {member.mention}'s permission to view {channel.mention}"
        )

    @hybrid_command(aliases=["bc"])
    @commands.has_permissions(manage_messages=True)
    async def cleanup(self, ctx: commands.Context, amount: int = 100):
        """Delete a specified number of messages from the current channel."""
        if not (1 <= amount <= 100):
            return await ctx.deny("You can only delete between 1 and 100 messages.")

        async def purge_messages():
            deleted_messages = await ctx.channel.purge(limit=amount + 1)
            await ctx.agree(f"**Cleaned up** {len(deleted_messages) - 1} messages.")

        asyncio.create_task(purge_messages())

    @hybrid_command(aliases=["ld"])
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx: commands.Context):
        """Activate lockdown in the current channel, preventing members from sending messages."""

        async def lock_channel():
            await ctx.channel.set_permissions(
                ctx.guild.default_role, send_messages=False
            )
            await ctx.agree(
                f"**Lockdown activated in** {ctx.channel.mention}. Members cannot send messages."
            )

        asyncio.create_task(lock_channel())

    @hybrid_command(aliases=["lda"])
    @commands.has_permissions(manage_guild=True)
    async def lockdown_all(self, ctx: commands.Context):
        """Activate lockdown in all text channels of the server, preventing members from sending messages."""
        tasks = [
            channel.set_permissions(ctx.guild.default_role, send_messages=False)
            for channel in ctx.guild.channels
            if isinstance(channel, discord.TextChannel)
        ]

        async def lock_all_channels():
            await asyncio.gather(*tasks)
            await ctx.agree(
                "**Lockdown activated in all channels.** Members cannot send messages."
            )

        asyncio.create_task(lock_all_channels())

    @hybrid_command(aliases=["ulda"])
    @commands.has_permissions(manage_guild=True)
    async def unlockdown_all(self, ctx: commands.Context):
        """Deactivate lockdown in all text channels of the server, allowing members to send messages."""
        tasks = [
            channel.set_permissions(ctx.guild.default_role, send_messages=True)
            for channel in ctx.guild.channels
            if isinstance(channel, discord.TextChannel)
        ]

        async def unlock_all_channels():
            await asyncio.gather(*tasks)
            await ctx.agree(
                "**Lockdown deactivated in all channels.** Members can send messages."
            )

        asyncio.create_task(unlock_all_channels())


async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
