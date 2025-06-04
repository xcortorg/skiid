import asyncio
import typing
from logging import Logger, getLogger

import discord

from grief.core import Config, commands
from grief.core.bot import Grief

from .converter import RoleHierarchyConverter

LISTENER_NAME: str = (
    "on_presence_update" if discord.version_info.major == 2 else "on_member_update"
)
logger = getLogger("grief.vanity")


class Vanity(commands.Cog):
    """For level 3 servers, award your users for advertising the vanity in their status."""

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n"

    def __init__(self, bot: Grief):
        self.bot: Grief = bot
        self.logger: Logger = getLogger("grief.vanity")
        self.config = Config.get_conf(
            self, identifier=12039492, force_registration=True
        )
        default_guild = {
            "role": None,
            "toggled": False,
            "channel": None,
            "vanity": None,
        }
        self.config.register_guild(**default_guild)
        self.settings = {}
        self.first_run = True
        self.vanity_cache = {}
        self.update_cache()

    async def update_cache(self):
        await self.bot.wait_until_red_ready()
        data = await self.config.all_guilds()
        for x in data:
            vanity = data[x]["vanity"]
            if vanity:
                self.vanity_cache[x] = vanity

    async def safe_send(
        self, channel: discord.TextChannel, embed: discord.Embed
    ) -> None:
        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException) as e:
            self.logger.warning(
                f"Failed to send message to {channel.name} in {channel.guild.name}/{channel.guild.id}: {str(e)}"
            )

    @commands.Cog.listener(LISTENER_NAME)
    async def on_vanity_trigger(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        if after.guild.id not in self.vanity_cache:
            await self.update_cache()

        if before.bot:
            return
        guild: discord.Guild = after.guild
        data = await self.config.guild(guild).all()
        if not data.get("toggled"):
            return
        if not data.get("role") or not data.get("channel"):
            return
        # if not "VANITY_URL" in guild.features:
        # return
        vanity: str = "/" + self.vanity_cache[guild.id]
        role: discord.Role = guild.get_role(int(data["role"]))
        log_channel: discord.TextChannel = guild.get_channel(int(data["channel"]))
        if not role:
            self.logger.info(
                f"Vanity role not found for {guild.name}/{guild.id}, skipping"
            )
            return
        if not log_channel:
            self.logger.info(
                f"Vanity log channel not found for {guild.name}/{guild.id}, skipping"
            )
            return
        if role.position >= guild.me.top_role.position:
            self.logger.info(
                f"Vanity role is higher than me in {guild.name}/{guild.id}, skipping"
            )
            return

        before_custom_activity: typing.List[discord.CustomActivity] = [
            activity
            for activity in before.activities
            if isinstance(activity, discord.CustomActivity)
        ]
        after_custom_activity: typing.List[discord.CustomActivity] = [
            activity
            for activity in after.activities
            if isinstance(activity, discord.CustomActivity)
        ]
        has_in_status_embed = discord.Embed(
            color=0x2F3136,
            description=f"Thanks {after.mention} for having {vanity} in your status.\nI rewarded you with {role.mention}",
        )
        has_in_status_embed.set_footer(
            text=self.bot.user.name,
            icon_url="https://cdn.discordapp.com/emojis/886356428116357120.gif",
        )

        if not before_custom_activity and after_custom_activity:
            if after_custom_activity[0].name is not None:
                if vanity.lower() in after_custom_activity[0].name.lower():
                    if role.id not in after._roles:
                        try:
                            await after.add_roles(
                                role,
                                reason="grief vanity: user had the server vanity in their status",
                            )
                        except (discord.Forbidden, discord.HTTPException) as e:
                            self.logger.warning(
                                f"Failed to add role to {after} in {guild.name}/{guild.id}: {str(e)}"
                            )
                            return
                    self.bot.loop.create_task(
                        self.safe_send(log_channel, has_in_status_embed)
                    )
        elif before_custom_activity and not after_custom_activity:
            if before_custom_activity[0].name is not None:
                if vanity.lower() in before_custom_activity[0].name.lower():
                    if role.id in after._roles:
                        try:
                            await after.remove_roles(
                                role,
                                reason="grief vanity: user removed the server vanity from their status",
                            )
                        except (discord.Forbidden, discord.HTTPException) as e:
                            self.logger.warning(
                                f"Failed to remove role from {after} in {guild.name}/{guild.id}: {str(e)}"
                            )
        elif (
            before_custom_activity
            and after_custom_activity
            and before_custom_activity[0] != after_custom_activity[0]
        ):
            if before_custom_activity[0].name is None:
                before_match = False
            else:
                before_match = vanity.lower() in before_custom_activity[0].name.lower()
            if after_custom_activity[0].name is None:
                after_match = False
            else:
                after_match = vanity.lower() in after_custom_activity[0].name.lower()
            if not before_match and after_match:
                if role.id not in after._roles:
                    try:
                        await after.add_roles(role)
                    except (discord.Forbidden, discord.HTTPException) as e:
                        self.logger.warning(
                            f"Failed to add role to {after} in {guild.name}/{guild.id}: {str(e)}"
                        )
                        return
                self.bot.loop.create_task(
                    self.safe_send(log_channel, has_in_status_embed)
                )
            elif before_match and not after_match:
                if role.id in after._roles:
                    try:
                        await after.remove_roles(role)
                    except (discord.Forbidden, discord.HTTPException) as e:
                        self.logger.warning(
                            f"Failed to remove role from {after} in {guild.name}/{guild.id}: {str(e)}"
                        )
        if not before_custom_activity and not after_custom_activity:
            # cope with the case where the user does not have a custom status
            if role.id in after._roles:
                try:
                    await after.remove_roles(role)
                except (discord.Forbidden, discord.HTTPException) as e:
                    self.logger.warning(
                        f"Failed to remove role from {after} in {guild.name}/{guild.id}: {str(e)}"
                    )

    @commands.group(
        name="vanity",
    )
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanity(self, ctx: commands.Context) -> None:
        """Vanity management for Grief."""

    @vanity.command()
    async def toggle(self, ctx: commands.Context, on: bool, vanity: str) -> None:
        """Toggle vanity checker for current server on/off. Do not use "/"."""
        await self.config.guild(ctx.guild).toggled.set(on)
        await self.config.guild(ctx.guild).vanity.set(vanity)
        # if "VANITY_URL" in ctx.guild.features:
        self.vanity_cache[ctx.guild.id] = vanity
        await ctx.send(
            f"Vanity status tracking for current server is now {'on' if on else 'off'} and set to {vanity}."
        )

    @vanity.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def role(
        self,
        ctx: commands.Context,
        role: RoleHierarchyConverter,
    ):
        """Setup the role to be rewarded."""
        await self.config.guild(ctx.guild).role.set(role.id)
        await ctx.send(
            f"Vanity role has been updated to {role.mention}",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @vanity.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def channel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> None:
        """Setup the log channel."""
        if not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(
                f"I don't have permission to send messages in {channel.mention}, please give me permission to send messages."
            )
            return
        if not channel.permissions_for(ctx.guild.me).embed_links:
            await ctx.send(
                f"I don't have permission to embed links in {channel.mention}, please give me permission to embed links."
            )
            return
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(
            f"Vanity log channel has been updated to {channel.mention}",
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: Grief):
    cog = Vanity(bot)
    await discord.utils.maybe_coroutine(bot.add_cog, cog)
    asyncio.create_task(cog.update_cache())
