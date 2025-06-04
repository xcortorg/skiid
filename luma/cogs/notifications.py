import discord
from discord.ext import commands
from managers.bot import Luma
from managers.helpers import Context


class Notifications(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_delete(
        self: "Notifications", channel: discord.abc.GuildChannel
    ):
        if channel.type.name == "text":
            for i in ["welcome", "leave"]:
                await self.bot.db.execute(
                    f"DELETE FROM {i} WHERE channel_id = $1", channel.id
                )

    @commands.group(invoke_without_command=True)
    async def starboard(self: "Notifications", ctx: Context):
        """
        Highlight messages using reactions
        """
        return await ctx.send_help(ctx.command)

    @starboard.command(name="enable", aliases=["e"])
    @commands.has_guild_permissions(manage_guild=True)
    async def starboard_enable(self: "Notifications", ctx: Context):
        """
        Enable the starboard feature
        """
        r = await self.bot.db.execute(
            """
      INSERT INTO starboard (guild_id, emoji) VALUES ($1,$2)
      ON CONFLICT (guild_id) DO NOTHING
      """,
            ctx.guild.id,
            "💀",
        )

        if r == "INSERT 0":
            return await ctx.error("Starboard is **already** enabled")

        await ctx.confirm("Enabled starboard")

    @starboard.command(name="disable")
    @commands.has_guild_permissions(manage_guild=True)
    async def starboard_disable(self: "Notifications", ctx: Context):
        """
        Disable the starboard feature
        """
        r = await self.bot.db.execute(
            "DELETE FROM starboard WHERE guild_id = $1", ctx.guild.id
        )

        if r == "DELETE 0":
            return await ctx.error("Starboard is not enabled...")

        await self.bot.db.execute(
            "DELETE FROM starboard_message WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.confirm("Disabled starboard")

    @starboard.command(name="channel")
    @commands.has_guild_permissions(manage_guild=True)
    async def starboard_channel(
        self: "Notifications", ctx: Context, *, channel: discord.TextChannel
    ):
        """
        Assign the starboard panel channel
        """
        r = await self.bot.db.execute(
            "UPDATE starboard SET channel_id = $1 WHERE guild_id = $2",
            channel.id,
            ctx.guild.id,
        )

        if r == "UPDATE 0":
            return await ctx.error("Starboard is not enabled...")

        await ctx.confirm(f"Updated the starboard channel to {channel.mention}")

    @starboard.command(name="count")
    @commands.has_guild_permissions(manage_guild=True)
    async def starboard_count(self: "Notifications", ctx: Context, count: int):
        """
        Assign the starboard reaction count
        """
        if count < 1:
            return await ctx.error("Number cannot be less than `1`")

        r = await self.bot.db.execute(
            "UPDATE starboard SET count = $1 WHERE guild_id = $2", count, ctx.guild.id
        )

        if r == "UPDATE 0":
            return await ctx.error("Starboard is not enabled...")

        await ctx.confirm(f"Updated the starboard count to `{count}`")

    @starboard.command(name="emoji")
    @commands.has_guild_permissions(manage_guild=True)
    async def starboard_emoji(self: "Notifications", ctx: Context, *, emoji: str):
        """
        Assign the starboard's required reaction
        """
        r = await self.bot.db.execute(
            "UPDATE starboard SET emoji = $1 WHERE guild_id = $2", emoji, ctx.guild.id
        )

        if r == "UPDATE 0":
            return await ctx.error("Starboard is not enabled...")

        await ctx.confirm("Updated the starboard emoji")

    @starboard.command(name="settings")
    @commands.has_guild_permissions(manage_guild=True)
    async def starboard_settings(self: "Notifications", ctx: Context):
        """
        Check the starboard's configuration
        """
        result = await self.bot.db.fetchrow(
            "SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id
        )
        if not result:
            return await ctx.erro("Starboard is **not** enabled")

        condition: bool = all([result["channel_id"], result["count"], result["emoji"]])
        embed = (
            discord.Embed(
                color=getattr(discord.Color, "green" if condition else "red")(),
                description="Functional" if condition else "Not Functional",
            )
            .set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
            .add_field(
                name="Channel",
                value=(
                    ctx.guild.get_channel(result["channel_id"]).mention
                    if ctx.guild.get_channel(result["channel_id"])
                    else "N/A"
                ),
            )
            .add_field(name="Emoji", value=result["emoji"])
            .add_field(name="Count", value=result["count"] or "N/A")
        )
        await ctx.reply(embed=embed)

    @commands.group(invoke_without_command=True)
    async def welcome(self: "Notifications", ctx: Context):
        """
        Send a message when someone joins the server
        """
        return await ctx.send_help(ctx.command)

    @welcome.command(name="add")
    @commands.has_guild_permissions(manage_guild=True)
    async def welcome_add(
        self: "Notifications",
        ctx: Context,
        channel: discord.TextChannel,
        *,
        message: str,
    ):
        """
        Add a welcome channel
        """
        await self.bot.db.execute(
            """
      INSERT INTO welcome VALUES ($1,$2,$3)
      ON CONFLICT (guild_id, channel_id) DO UPDATE
      SET message = $3""",
            ctx.guild.id,
            channel.id,
            message,
        )
        await ctx.confirm(
            f"Added {channel.mention} to welcome with message:\n`{message}`"
        )

    @welcome.command(name="remove")
    @commands.has_guild_permissions(manage_guild=True)
    async def welcome_remove(
        self: "Notifications", ctx: Context, *, channel: discord.TextChannel
    ):
        """
        Remove a welcome channel
        """
        if not await self.bot.db.fetchrow(
            "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.error("This channel is not a welcome channel")

        await self.bot.db.execute(
            "DELETE FROM welcome WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        await ctx.confirm(f"Removed {channel.mention} from welcome channels")

    @welcome.command(name="test")
    @commands.has_guild_permissions(manage_guild=True)
    async def welcome_test(
        self: "Notifications", ctx: Context, *, channel: discord.TextChannel
    ):
        """
        Test the welcome message in a channel
        """
        if check := await self.bot.db.fetchrow(
            "SELECT * FROM welcome WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        ):
            x = await self.bot.embed.convert(ctx.author, check["message"])
            mes = await channel.send(**x)
            await ctx.confirm(f"Sent welcome message to {mes.jump_url}")

    @welcome.command(name="list")
    async def welcome_list(self: "Notifications", ctx: Context):
        """
        See a list of welcome channels
        """
        results = await self.bot.db.fetch(
            "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
        )
        if not results:
            return await ctx.error("No welcome channels in this server")

        await ctx.paginate(
            [f"<#{result['channel_id']}>" for result in results],
            title=f"Welcome channels ({len(results)})",
        )

    @commands.group(invoke_without_command=True)
    async def leave(self: "Notifications", ctx: Context):
        """
        Send a message when someone leaves the server
        """
        return await ctx.send_help(ctx.command)

    @leave.command(name="add")
    @commands.has_guild_permissions(manage_guild=True)
    async def leave_add(
        self: "Notifications",
        ctx: Context,
        channel: discord.TextChannel,
        *,
        message: str,
    ):
        """
        Add a leave channel
        """
        await self.bot.db.execute(
            """
      INSERT INTO leave VALUES ($1,$2,$3)
      ON CONFLICT (guild_id, channel_id) DO UPDATE
      SET message = $3""",
            ctx.guild.id,
            channel.id,
            message,
        )
        await ctx.confirm(
            f"Added leave channel {channel.mention} message:\n`{message}`"
        )

    @leave.command(name="remove")
    @commands.has_guild_permissions(manage_guild=True)
    async def leave_remove(
        self: "Notifications", ctx: Context, *, channel: discord.TextChannel
    ):
        """
        Remove a leave channel
        """
        if not await self.bot.db.fetchrow(
            "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.error("This channel is not a leave channel")

        await self.bot.db.execute(
            "DELETE FROM leave WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        await ctx.confirm(f"Removed {channel.mention} from leave channels")

    @leave.command(name="test")
    @commands.has_guild_permissions(manage_guild=True)
    async def leave_test(
        self: "Notifications", ctx: Context, *, channel: discord.TextChannel
    ):
        """
        Test the leave message in a channel
        """
        if check := await self.bot.db.fetchrow(
            "SELECT * FROM leave WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        ):
            x = await self.bot.embed.convert(ctx.author, check["message"])
            mes = await channel.send(**x)
            await ctx.confirm(f"Sent leave message to {mes.jump_url}")

    @leave.command(name="list")
    async def leave_list(self: "Notifications", ctx: Context):
        """
        See a list of leave channels
        """
        results = await self.bot.db.fetch(
            "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
        )
        if not results:
            return await ctx.error("No leave channels in this server")

        await ctx.paginate(
            [f"<#{result['channel_id']}>" for result in results],
            title=f"Leave channels ({len(results)})",
        )


async def setup(bot: Luma):
    return await bot.add_cog(Notifications(bot))
