import discord
from discord.ext import commands
from managers.bot import Luma
from managers.helpers import Context


class AutoMod(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def filter(self: "AutoMod", ctx: Context):
        """
        Commands for filter settings
        """
        return await ctx.send_help(ctx.command)

    @filter.group(name="invites", invoke_without_command=True)
    async def filter_invites(self: "AutoMod", ctx: Context):
        """
        Block sending invite links
        """
        return await ctx.send_help(ctx.command)

    @filter_invites.command(name="enable")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_guild=True)
    async def filter_invites_enable(self: "AutoMod", ctx: Context):
        """
        Enable invite filter
        """
        check = await self.bot.db.fetchrow(
            "SELECT rule_id FROM filter WHERE guild_id = $1 AND module = $2",
            ctx.guild.id,
            "invites",
        )
        if not check:
            trigger = discord.AutoModTrigger(
                type=discord.AutoModRuleTriggerType.keyword,
                regex_patterns=[
                    r"(https?://)?(www.|canary.|ptb.)?(discord.(gg|io|me|li)|discordapp.com/invite|discord.com/invite)/?[a-zA-Z0-9]+/?"
                ],
            )

            rule = await ctx.guild.create_automod_rule(
                name=f"{self.bot.user.name} automod",
                event_type=discord.AutoModRuleEventType.message_send,
                trigger=trigger,
                enabled=True,
                actions=[
                    discord.AutoModRuleAction(
                        custom_message=f"Message contains invite links. Moderator {self.bot.user.name}"
                    )
                ],
                reason="Rule for filter invites created",
            )

            await self.bot.db.execute(
                "INSERT INTO filter VALUES ($1,$2,$3)", ctx.guild.id, "invites", rule.id
            )

            return await ctx.confirm("Filter invites has been enabled")

        else:
            rule = await ctx.guild.fetch_automod_rule(check[0])
            if rule:
                if not rule.enabled:
                    await rule.edit(enabled=True, reason=f"Enabled by {ctx.author}")
                    return await ctx.confirm("Filter invites has been enabled")
                return await ctx.error("Filter invites is already enabled")
            return await ctx.error("Filter invites is not enabled")

    @filter_invites.command(name="disable")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.has_guild_permissions(manage_guild=True)
    async def filter_invites_disable(self: "AutoMod", ctx: Context):
        """
        Disable invite filter
        """
        check = await self.bot.db.fetchrow(
            "SELECT rule_id FROM filter WHERE guild_id = $1 AND module = $2",
            ctx.guild.id,
            "invites",
        )

        if not check:
            return await ctx.error("Filter invites is not enabled")

        rule = await ctx.guild.fetch_automod_rule(check[0])

        if rule:
            await rule.delete(reason=f"Filter invites disabled by {ctx.author}")
            await self.bot.db.execute(
                "DELETE FROM filter WHERE guild_id = $1 AND module = $2",
                ctx.guild.id,
                "invites",
            )
            await ctx.confirm("Filter invites has been disabled")
        else:
            await ctx.error("Cannot find the automod rule")

    @filter_invites.command(name="whilelist", aliases=["wl"])
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_guild=True)
    async def filter_invites_whitelist(
        self: "AutoMod", ctx: Context, *, channel: discord.TextChannel
    ):
        """
        Whitelist a channel for filter invites
        """
        check = await self.bot.db.fetchrow(
            "SELECT rule_id FROM filters WHERE guild_id = $1 AND module = $2",
            ctx.guild.id,
            "invites",
        )

        if not check:
            return await ctx.error("Filter invites is not enabled")

        rule = await ctx.guild.fetch_automod_rule(check[0])
        if not rule:
            return await ctx.error("Invites filter rule not found")

        if channel.id in rule.exempt_channel_ids:
            return await ctx.error("This channel is already whitelisted")

        channels = rule.exempt_channels
        channels.append(channel)
        await rule.edit(
            exempt_channels=channels, reason=f"Channel whitelisted by {ctx.author}"
        )

        await ctx.confirm(f"{channel.mention} is now whitelisted from invites filter")

    @filter_invites.command(name="unwhitelist", aliases=["unwl"])
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_guild=True)
    async def filter_invites_unwhitelist(
        self: "AutoMod", ctx: Context, *, channel: discord.TextChannel
    ):
        """
        Unwhitelist a channel from filter invites
        """
        check = await self.bot.db.fetchrow(
            "SELECT rule_id FROM filters WHERE guild_id = $1 AND module = $2",
            ctx.guild.id,
            "invites",
        )

        if not check:
            return await ctx.error("Filter invites is not enabled")

        rule = await ctx.guild.fetch_automod_rule(check[0])
        if not rule:
            return await ctx.error("Invites filter rule not found")

        if not channel.id in rule.exempt_channel_ids:
            return await ctx.error("This channel is not invites filter whitelisted")

        channels = rule.exempt_channel_ids
        channels.remove(channel)
        await rule.edit(
            exempt_channels=channels, reason=f"Channel unwhitelisted by {ctx.author}"
        )

        await ctx.confirm(f"{channel.mention} is no longer whitelisted")


async def setup(bot: Luma):
    return await bot.add_cog(AutoMod(bot))
