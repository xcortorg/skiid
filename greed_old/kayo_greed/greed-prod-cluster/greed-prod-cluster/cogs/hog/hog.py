import os
import discord

from main import greed
from discord.ext.commands import Cog
from posthog import Posthog
import config

posthog = Posthog(config.ANALYTICS.api_key, config.ANALYTICS.url)


class Hog(Cog):
    def __init__(self, bot: greed):
        self.bot = bot
        self.description = "Posthog Analytics for Greed"
        self.bot.after_invoke(self.after_invoke)

    async def after_invoke(self, ctx):
        posthog.capture(
            str(ctx.author.id),
            event="command executed",
            properties={"command name": ctx.command.qualified_name},
            groups={"guild": str(ctx.guild.id)},
        )

    @Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: discord.Guild):
        posthog.group_identify(
            "guild",
            str(guild.id),
            {
                "name": guild.name,
                "member count": guild.member_count,
            },
        )

    @Cog.listener("on_guild_update")
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        posthog.group_identify(
            "guild",
            str(after.id),
            {
                "name": after.name,
                "member count": after.member_count,
            },
        )


async def setup(bot: greed) -> None:
    await bot.add_cog(Hog(bot))
