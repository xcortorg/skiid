import discord
from discord.ext import commands
from datetime import datetime
import pytz  # For handling timezone
from tool.greed import Greed
from loguru import logger
from cogs.moderation import Moderation


class Antiraid(commands.Cog):
    def __init__(self, bot: Greed):
        self.bot = bot
        self.original_permissions = {}
        self.bot.loop.create_task(self.setup_db())  # Initialize the database

    async def setup_db(self):
        """Sets up the database tables if they don't exist."""
        await self.bot.db.execute(
            """ 
            CREATE TABLE IF NOT EXISTS whitelist ( 
                user_id BIGINT PRIMARY KEY 
            )
        """
        )
        await self.bot.db.execute(
            """ 
            CREATE TABLE IF NOT EXISTS server_settings ( 
                guild_id BIGINT PRIMARY KEY, 
                antiraid_enabled BOOLEAN DEFAULT FALSE, 
                minimum_account_age INT DEFAULT 7, 
                lockdown BOOLEAN DEFAULT FALSE, 
                default_pfp_check BOOLEAN DEFAULT FALSE,
                log_channel_id BIGINT,
                raid_punishment TEXT DEFAULT 'ban'
            )
        """
        )
        await self.bot.db.execute(
            """ 
            ALTER TABLE server_settings 
            ADD COLUMN IF NOT EXISTS antiraid_enabled BOOLEAN DEFAULT FALSE 
        """
        )
        await self.bot.db.execute(
            """ 
            ALTER TABLE server_settings
            ADD COLUMN IF NOT EXISTS minimum_account_age INT DEFAULT 7 
        """
        )
        await self.bot.db.execute(
            """ 
            ALTER TABLE server_settings
            ADD COLUMN IF NOT EXISTS lockdown BOOLEAN DEFAULT FALSE 
        """
        )
        await self.bot.db.execute(
            """ 
            ALTER TABLE server_settings
            ADD COLUMN IF NOT EXISTS default_pfp_check BOOLEAN DEFAULT FALSE 
        """
        )
        await self.bot.db.execute(
            """ 
            ALTER TABLE server_settings
            ADD COLUMN IF NOT EXISTS log_channel_id BIGINT
        """
        )
        await self.bot.db.execute(
            """ 
            ALTER TABLE server_settings
            ADD COLUMN IF NOT EXISTS raid_punishment TEXT DEFAULT 'ban'
        """
        )

    async def get_server_settings(self, guild_id):
        """Fetch server settings for a specific guild."""
        query = """
        SELECT antiraid_enabled, minimum_account_age, lockdown, default_pfp_check, log_channel_id, raid_punishment
        FROM server_settings
        WHERE guild_id = $1
        """
        settings = await self.bot.db.fetchrow(query, guild_id)
        if not settings:
            await self.bot.db.execute(
                """ 
                INSERT INTO server_settings (guild_id) 
                VALUES ($1)
            """,
                guild_id,
            )
            return {
                "antiraid_enabled": False,
                "minimum_account_age": 7,
                "lockdown": False,
                "default_pfp_check": False,
                "log_channel_id": None,
                "raid_punishment": "ban",
            }
        return dict(settings)

    async def is_whitelisted(self, user_id):
        """Check if a user is whitelisted."""
        query = "SELECT 1 FROM whitelist WHERE user_id = $1"
        result = await self.bot.db.fetchrow(query, user_id)
        return result is not None

    async def log_raid_activity(self, reason, member, guild):
        """Logs a failed raid activity to the logs."""
        settings = await self.get_server_settings(guild.id)
        log_channel_id = settings["log_channel_id"]

        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(
                    f"**[Raid Log]** {member} attempted to join with reason: {reason}"
                )
            else:
                await guild.system_channel.send(
                    f"Log channel with ID {log_channel_id} no longer exists."
                )
        else:
            log_channel = discord.utils.get(guild.text_channels, name="raid-log")
            if log_channel:
                await log_channel.send(
                    f"**[Raid Log]** {member} attempted to join with reason: {reason}"
                )
            else:
                return

    @commands.group(name="antiraid", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antiraid(self, ctx):
        """Anti-raid command group."""
        return await ctx.send_help(ctx.command.qualified_name)

    @antiraid.command(name="toggle")
    @commands.has_permissions(administrator=True)
    async def toggle_antiraid(self, ctx):
        """Toggle the anti-raid system on or off."""
        settings = await self.get_server_settings(ctx.guild.id)
        new_status = not settings["antiraid_enabled"]
        await self.bot.db.execute(
            """ 
            UPDATE server_settings
            SET antiraid_enabled = $1
            WHERE guild_id = $2 
        """,
            new_status,
            ctx.guild.id,
        )
        status_text = "enabled" if new_status else "disabled"
        await ctx.success(f"Anti-raid system has been {status_text}.")

    @antiraid.command(name="setminage")
    @commands.has_permissions(administrator=True)
    async def set_min_account_age(self, ctx, days: int):
        """Set the minimum account age in days."""
        await self.bot.db.execute(
            """ 
            UPDATE server_settings
            SET minimum_account_age = $1
            WHERE guild_id = $2
        """,
            days,
            ctx.guild.id,
        )
        await ctx.success(f"Minimum account age set to {days} days.")

    @commands.command(name="lockdown")
    @commands.has_permissions(administrator=True)
    async def toggle_lockdown(self, ctx, status: str):
        """Enable or disable server lockdown (block all new joins)."""
        if status.lower() not in ["on", "off"]:
            await ctx.fail("Invalid status! Use `on` or `off`.")  # Handle invalid input
            return

        new_lockdown = status.lower() == "on"

        # Update lockdown status in the database
        await self.bot.db.execute(
            """
            UPDATE server_settings
            SET lockdown = $1
            WHERE guild_id = $2
        """,
            new_lockdown,
            ctx.guild.id,
        )

        # Apply lockdown or lift lockdown
        for channel in ctx.guild.text_channels:
            overwrites = channel.overwrites_for(ctx.guild.default_role)

            if new_lockdown:
                # Store the original permissions before making changes
                if channel.id not in self.original_permissions:
                    self.original_permissions[channel.id] = {
                        "send_messages": overwrites.send_messages,
                        "read_messages": overwrites.read_messages,
                    }

                # Lock the channel (disable sending messages)
                await channel.set_permissions(
                    ctx.guild.default_role, send_messages=False, read_messages=True
                )

            else:
                # Restore original permissions after lockdown is lifted
                if channel.id in self.original_permissions:
                    original = self.original_permissions[channel.id]
                    await channel.set_permissions(
                        ctx.guild.default_role,
                        send_messages=original["send_messages"],
                        read_messages=original["read_messages"],
                    )
                    del self.original_permissions[
                        channel.id
                    ]  # Clean up after restoring permissions

        state = "locked down" if new_lockdown else "lifted"
        await ctx.success(
            f"Server is now {state}. New member joins are {'blocked' if new_lockdown else 'allowed'}."
        )

    @antiraid.command(name="defaultpfp")
    @commands.has_permissions(administrator=True)
    async def toggle_default_pfp(self, ctx):
        """Toggle blocking users with default profile pictures."""
        settings = await self.get_server_settings(ctx.guild.id)
        new_status = not settings["default_pfp_check"]
        await self.bot.db.execute(
            """ 
            UPDATE server_settings
            SET default_pfp_check = $1
            WHERE guild_id = $2
        """,
            new_status,
            ctx.guild.id,
        )
        status = "enabled" if new_status else "disabled"
        await ctx.success(f"Default profile picture check has been {status}.")

    @antiraid.command(
        name="punishment",
        brief="Set the punishment for raid attempts",
        usage="<ban/kick/timeout/jail>",
    )
    @commands.has_permissions(administrator=True)
    async def set_punishment(self, ctx, punishment: str):
        """Set the punishment for raid attempts."""
        punishment = punishment.lower()
        valid_punishments = ["ban", "kick", "timeout", "jail"]

        if punishment not in valid_punishments:
            return await ctx.fail(
                f"Invalid punishment! Must be one of: {', '.join(valid_punishments)}"
            )

        await self.bot.db.execute(
            """ 
            UPDATE server_settings
            SET raid_punishment = $1
            WHERE guild_id = $2
        """,
            punishment,
            ctx.guild.id,
        )

        await ctx.success(f"Raid punishment has been set to **{punishment}**")

    @antiraid.command(name="status")
    async def status(self, ctx):
        """Check the current anti-raid system status."""
        settings = await self.get_server_settings(ctx.guild.id)
        embed = discord.Embed(title="Anti-Raid Status", color=self.bot.color)
        embed.add_field(
            name="Antiraid System",
            value=(
                "<:UB_Check_Icon:1306875712782864445>"
                if settings["antiraid_enabled"]
                else "<:UB_X_Icon:1306875714426900531>"
            ),
            inline=False,
        )
        embed.add_field(
            name="Lockdown",
            value=(
                "<:UB_Check_Icon:1306875712782864445>"
                if settings["lockdown"]
                else "<:UB_X_Icon:1306875714426900531>"
            ),
            inline=False,
        )
        embed.add_field(
            name="Minimum Account Age",
            value=f"{settings['minimum_account_age']} days",
            inline=False,
        )
        embed.add_field(
            name="Default PFP Check",
            value=(
                "<:UB_Check_Icon:1306875712782864445>"
                if settings["default_pfp_check"]
                else "<:UB_X_Icon:1306875714426900531>"
            ),
            inline=False,
        )
        embed.add_field(
            name="Log Channel",
            value=(
                f"<#{settings['log_channel_id']}>"
                if settings["log_channel_id"]
                else "<:UB_X_Icon:1306875714426900531>"
            ),
            inline=False,
        )
        embed.add_field(
            name="Raid Punishment",
            value=settings.get("raid_punishment", "ban").title(),
            inline=False,
        )
        embed.set_footer(text="Use the antiraid commands to adjust settings.")
        await ctx.send(embed=embed)

    @antiraid.command(name="setlogchannel")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Sets the channel for raid activity logs."""
        if not channel:
            await ctx.fail("You must specify a valid text channel for the log.")
            return

        # Store the log channel in the database
        await self.bot.db.execute(
            """
            INSERT INTO server_settings (guild_id, log_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET log_channel_id = $2
        """,
            ctx.guild.id,
            channel.id,
        )

        await ctx.success(f"Raid log channel has been set to {channel.mention}.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Listen for new member joins and apply anti-raid checks."""
        settings = await self.get_server_settings(member.guild.id)
        if not settings["antiraid_enabled"]:  # Skip listeners if anti-raid is disabled
            return

        if await self.is_whitelisted(member.id):
            return  # Skip checks for whitelisted users

        # Check for lockdown
        if settings["lockdown"]:
            await self.handle_lockdown(member)
            return

        # Check for default profile picture
        if settings["default_pfp_check"] and not member.avatar:
            await self.handle_default_pfp_check(member)
            return

        # Check account age
        member_created_naive = member.created_at.replace(tzinfo=None)
        account_age = (datetime.utcnow() - member_created_naive).days
        if account_age < settings["minimum_account_age"]:
            await self.handle_account_age(
                member, account_age, settings["minimum_account_age"]
            )

    async def handle_lockdown(self, member):
        """Handles the lockdown case."""
        await member.send(
            "The server is currently in lockdown. Please try again later."
        )
        await self.handle_raid_punishment(member, "Server lockdown in effect")
        await self.log_raid_activity("Lockdown", member, member.guild)

    async def handle_default_pfp_check(self, member):
        """Handles default profile picture check."""
        await member.send(
            "Accounts with default profile pictures are not allowed. Please update your profile picture and try again."
        )
        await self.handle_raid_punishment(member, "Default profile picture detected")
        await self.log_raid_activity("Default PFP detected", member, member.guild)

    async def handle_account_age(self, member, account_age, min_age):
        """Handles account age below the minimum required."""
        await member.send(
            f"Your account is too new to join this server. Please try again after {min_age - account_age} days."
        )
        await self.handle_raid_punishment(
            member, f"Account age ({account_age} days) below required {min_age}"
        )
        await self.log_raid_activity(
            f"Account age ({account_age} days) below required {min_age}",
            member,
            member.guild,
        )

    async def handle_raid_punishment(self, member, reason):
        """Handle the punishment for a raid attempt."""
        settings = await self.get_server_settings(member.guild.id)
        punishment = settings.get("raid_punishment", "ban")

        try:
            if punishment == "ban":
                await member.guild.ban(member, reason=f"Anti-raid: {reason}")
            elif punishment == "kick":
                await member.guild.kick(member, reason=f"Anti-raid: {reason}")
            elif punishment == "timeout":
                # 1 hour timeout
                await member.timeout(
                    datetime.timedelta(hours=1), reason=f"Anti-raid: {reason}"
                )
            elif punishment == "jail":
                await Moderation.do_jail(member, reason=f"Anti-raid: {reason}")
            else:
                # Fallback to ban if jail not available
                await member.guild.ban(member, reason=f"Anti-raid: {reason}")
        except Exception as e:
            logger.error(f"Failed to apply punishment {punishment} to {member}: {e}")


# Add the cog to your bot
async def setup(bot):
    await bot.add_cog(Antiraid(bot))
