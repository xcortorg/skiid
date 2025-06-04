from __future__ import annotations

from contextlib import suppress

import discord
from AAA3A_utils.cogsutils import CogsUtils
from uwuipy import uwuipy

from grief.core import Config, checks, commands, i18n
from grief.core.bot import Grief

T_ = i18n.Translator("Shutup", __file__)

_ = lambda s: s


class Shutup(commands.Cog):
    def __init__(self, bot: Grief) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=959292943657746464,
            force_registration=True,
        )
        default_guild = {
            "enabled": True,
            "target_members": [],
            "uwulocked_members": [],
        }
        self.config.register_guild(**default_guild)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def stfu(self, ctx: commands.Context, user: discord.Member):
        """Add a certain user to have messages get auto-deleted."""

        if user.id in self.bot.owner_ids:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: You can't stfu a bot owner.",
                color=0x313338,
            )
            return await ctx.send(embed=embed, mention_author=False)

        if (
            ctx.author.top_role <= user.top_role
            and ctx.author.id not in self.bot.owner_ids
        ):
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: You may only target someone with a lower top role than you.",
                color=0x313338,
            )
            return await ctx.send(embed=embed, mention_author=False)

        enabled_list: list = await self.config.guild(ctx.guild).target_members()

        if user.id in enabled_list:
            enabled_list.remove(user.id)
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: **{user}** has been unstfu'ed.",
                color=0x313338,
            )
            await ctx.send(embed=embed, mention_author=False)
            async with ctx.typing():
                await self.config.guild(ctx.guild).target_members.set(enabled_list)
            return

        enabled_list.append(user.id)

        async with ctx.typing():
            await self.config.guild(ctx.guild).target_members.set(enabled_list)
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: **{user}** has been stfu'ed.",
                color=0x313338,
            )
            await ctx.send(embed=embed, mention_author=False)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def uwulock(self, ctx: commands.Context, user: discord.Member):
        """Add a certain user to have messages get auto-uwuified"""

        if user.id in self.bot.owner_ids:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: You can't uwulock a bot owner.",
                color=0x313338,
            )
            return await ctx.send(embed=embed, mention_author=False)

        if (
            ctx.author.top_role <= user.top_role
            and ctx.author.id not in self.bot.owner_ids
        ):
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: You may only target someone with a lower top role than you.",
                color=0x313338,
            )
            return await ctx.send(embed=embed, mention_author=False)

        enabled_list: list = await self.config.guild(ctx.guild).uwulocked_members()

        if user.id in enabled_list:
            enabled_list.remove(user.id)
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: **{user}** is no longer uwulocked.",
                color=0x313338,
            )
            await ctx.send(embed=embed, mention_author=False)
            async with ctx.typing():
                await self.config.guild(ctx.guild).uwulocked_members.set(enabled_list)
            return

        enabled_list.append(user.id)

        async with ctx.typing():
            await self.config.guild(ctx.guild).uwulocked_members.set(enabled_list)
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: **{user}** will have messages uwuified.",
                color=0x313338,
            )
            await ctx.send(embed=embed, mention_author=False)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if await self.config.guild(message.guild).enabled():
            if (
                message.author.id
                in await self.config.guild(message.guild).target_members()
            ):
                await message.delete()
            elif (
                message.author.id
                in await self.config.guild(message.guild).uwulocked_members()
            ):
                await message.delete()
                uwu = uwuipy()
                uwu_message = uwu.uwuify(message.content)
                try:
                    hook = await CogsUtils.get_hook(
                        bot=self.bot,
                        channel=getattr(message.channel, "parent", message.channel),
                    )
                    await hook.send(
                        content=uwu_message,
                        username=message.author.display_name,
                        avatar_url=message.author.display_avatar,
                        thread=(
                            message.channel
                            if isinstance(message.channel, discord.Thread)
                            else discord.utils.MISSING
                        ),
                    )
                except discord.HTTPException as error:
                    await message.channel.send("UwU, " + error)
