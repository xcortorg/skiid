import asyncio
import datetime

import discord

from grief.core import commands
from grief.core.bot import Grief
from grief.core.config import Config


class AutoKick(commands.Cog):
    """Instead of banning, have grief automatically kick certain users on join."""

    def __init__(self, bot: Grief) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=959292943657746464,
            force_registration=True,
        )
        default_guild = {"enabled": "True", "blacklisted_ids": [], "enabledd": "False"}
        self.config.register_guild(**default_guild)

    @commands.group(name="autokickset", aliases=["aks"])
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def autokickset(self, ctx):
        """
        Auto Kick settings.
        """

    @autokickset.command(name="enable")
    async def autokickset_enable(self, ctx):
        """
        Enable the autokick feature.
        """
        await self.config.guild(ctx.guild).enabled.set(True)
        await ctx.send(
            "Auto kicking blacklisted members has been enabled for this guild."
        )

    @autokickset.command(name="disable")
    async def autokickset_disable(self, ctx):
        """
        Disable the autokick feature.
        """
        await self.config.guild(ctx.guild).enabled.set(False)
        await ctx.reply(
            embed=discord.Embed(
                description="Autokicking members has been disabled for this guild."
            )
        )

    @autokickset.command(name="add", aliases=["blacklist", "bl"])
    async def autokickset_add(self, ctx, user: discord.User):
        """
        Add a certain user to get auto kicked.
        """
        if user.id in self.bot.owner_ids:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: You can't autokick a bot owner.",
                color=0x313338,
            )
            return await ctx.reply(embed=embed, mention_author=False)

        async with ctx.typing():
            ids = await self.config.guild(ctx.guild).blacklisted_ids()
            ids.append(user.id)
            await self.config.guild(ctx.guild).blacklisted_ids.set(ids)
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: **{user}** will be auto kicked on join.",
            color=0x313338,
        )
        return await ctx.reply(embed=embed, mention_author=False)

    @autokickset.command(name="remove", aliases=["unblacklist", "unbl"])
    async def autokickset_remove(self, ctx, user: discord.User):
        """
        Remove a certain user from getting auto kicked.
        """
        blacklisted_ids: list = await self.config.guild(ctx.guild).blacklisted_ids()

        if user.id in blacklisted_ids:
            async with ctx.typing():
                ids = await self.config.guild(ctx.guild).blacklisted_ids()
                ids.remove(user.id)
            await self.config.guild(ctx.guild).blacklisted_ids.set(ids)
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: **{user}** will not be auto kicked on join.",
            color=0x313338,
        )
        return await ctx.reply(embed=embed, mention_author=False)

    @autokickset.command(name="settings", aliases=["showsettings"])
    async def autokickset_settings(self, ctx):
        """
        Check your autokick settings.
        """
        enabled = await self.config.guild(ctx.guild).enabled()
        blacklisted_ids = await self.config.guild(ctx.guild).blacklisted_ids()
        e = discord.Embed(title="Auto kick Settings", color=discord.Colour.dark_theme())
        e.add_field(name="Enabled", value=enabled, inline=True)
        e.add_field(name="Users", value=blacklisted_ids, inline=True)
        e.set_footer(text=ctx.guild.name, icon_url=getattr(ctx.guild.icon, "url", None))
        await ctx.send(embed=e)

    @autokickset.command(name="clear", aliases=["nuke"], hidden=True)
    async def autokickset_clear(self, ctx):
        """
        Clear the autokick list.
        """
        async with ctx.typing():
            await self.config.guild(ctx.guild).blacklisted_ids.clear()
        await ctx.send("Auto kick list has been cleared.")

    @commands.bot_has_permissions(kick_members=True)
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if await self.config.guild(member.guild).enabled():
            if member.id in await self.config.guild(member.guild).blacklisted_ids():
                await member.guild.kick(member, reason="AutoKicked.")
