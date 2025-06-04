import discord
from discord.ext import commands
import logging
from asyncio import sleep


class Usernames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("usernames")

    async def cog_load(self):
        """Ensure the necessary tables are created when the cog loads."""
        await self.create_tables()

    async def create_tables(self):
        """Create the required tables in the database."""
        create_username_changes_table = """
            CREATE TABLE IF NOT EXISTS username_changes (
                user_id BIGINT PRIMARY KEY,
                username TEXT NOT NULL,
                change_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """
        create_tracking_channels_table = """
            CREATE TABLE IF NOT EXISTS tracking_channels (
                guild_id BIGINT PRIMARY KEY,
                channel_id BIGINT NOT NULL
            );
        """
        await self.bot.db.execute(create_username_changes_table)
        await self.bot.db.execute(create_tracking_channels_table)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        """This will be called when a user updates their username."""
        if before.name != after.name:
            if len(before.name) > 4:
                return

            if not await self.bot.glory_cache.ratelimited("rl:usernames", 4, 10) == 0:
                return

            cache_key = f"username_change:{before.id}"
            if await self.bot.redis.get(cache_key):
                return

            await self.bot.redis.set(cache_key, "1", ex=5)

            old_username = before.name
            channel_ids = await self.get_tracking_channel()
            if channel_ids:
                embed = discord.Embed(
                    description=f"**{old_username}** has been **dropped**.\n> usernames will be available after **14 days**",
                    timestamp=discord.utils.utcnow(),
                )
                for channel in channel_ids:
                    try:
                        await self.bot.send_raw(channel, embed=embed)
                        await sleep(0.5)
                    except Exception:
                        pass
                return
                try:
                    data = {"method": "username_change", "username": old_username}
                    #                    return await self.bot.connection.inform(data, destinations=self.bot.ipc.sources)
                    await self.bot.ipc.roundtrip(
                        "send_message",
                        channel_id=channel_ids,
                        embed=embed.to_dict(),
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to send username change notifications: {e}"
                    )

    @commands.Cog.listener("on_username_change")
    async def dispatch_username_change(self, username: str):
        if not (
            rows := await self.bot.db.fetch(
                """SELECT channel_id FROM tracking_channels WHERE guild_id = ANY($1::BIGINT[])""",
                [g.id for g in self.bot.guilds],
            )
        ):
            return

        async def emit(row):
            if not (channel := self.bot.get_channel(row.channel_id)):
                return
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.send_messages or not permissions.embed_links:
                return
            embed = discord.Embed(
                description=f"**{username}** has been **dropped**.\n ",
                timestamp=discord.utils.utcnow(),
            )
            return await channel.send(embed=embed)

        for row in rows:
            await emit(row)

    async def get_tracking_channel(self):
        """Get all tracking channels from the database."""
        try:
            results = await self.bot.db.fetch(
                "SELECT channel_id FROM tracking_channels"
            )
            return [result["channel_id"] for result in results]
        except Exception as e:
            self.logger.error(f"Failed to fetch tracking channels: {e}")
            return []

    @commands.group(invoke_without_command=True)
    async def username(self, ctx):
        """Commands for managing username tracking"""
        await ctx.send_help(ctx.command)

    @username.command(
        name="channel",
        aliases=["set"],
        brief="Set the channel where username changes will be sent.",
        example=",channel #username-changes",
    )
    @commands.has_permissions(manage_channels=True)
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set the channel where username changes will be sent."""
        try:
            is_donator = await self.bot.db.fetchrow(
                """SELECT * FROM boosters WHERE user_id = $1""", ctx.author.id
            )

            if not is_donator:
                return await ctx.fail(
                    "You are not boosting [/greedbot](https://discord.gg/greedbot). Boost this server to use this command."
                )

            if not channel.permissions_for(ctx.guild.me).send_messages:
                return await ctx.fail(
                    f"I don't have permission to send messages in {channel.mention}"
                )

            set_tracking_channel = """
                INSERT INTO tracking_channels (guild_id, channel_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE 
                SET channel_id = $2;
            """
            await self.bot.db.execute(set_tracking_channel, ctx.guild.id, channel.id)

            await ctx.success(
                f"Username change notifications will now be sent to {channel.mention}."
            )
            self.logger.info(
                f"Tracking channel set to {channel.id} for guild {ctx.guild.id}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to set tracking channel for guild {ctx.guild.id}: {e}"
            )
            await ctx.fail(f"An error occurred while setting the tracking channel: {e}")

    @username.command(
        name="unset",
        aliases=["remove", "reset"],
        brief="Remove the channel where username changes are sent.",
        example=",unset",
    )
    @commands.has_permissions(manage_channels=True)
    async def unset(self, ctx):
        """Remove the channel where username changes are sent."""
        try:
            is_donator = await self.bot.db.fetchrow(
                """SELECT * FROM donators WHERE user_id = $1""", ctx.author.id
            )

            if not is_donator:
                return await ctx.fail(
                    "You are not boosting [/greedbot](https://discord.gg/greedbot). Boost this server to use this command."
                )

            delete_tracking_channel = """
                DELETE FROM tracking_channels WHERE guild_id = $1
            """
            result = await self.bot.db.execute(delete_tracking_channel, ctx.guild.id)

            if result == "DELETE 0":
                await ctx.warning("No channel is currently set for username tracking.")
            else:
                await ctx.success("Username tracking channel has been unset.")
                self.logger.info(f"Tracking channel unset for guild {ctx.guild.id}")

        except Exception as e:
            self.logger.error(
                f"Failed to unset tracking channel for guild {ctx.guild.id}: {e}"
            )
            await ctx.fail(
                f"An error occurred while unsetting the tracking channel: {e}"
            )


async def setup(bot):
    await bot.add_cog(Usernames(bot))
