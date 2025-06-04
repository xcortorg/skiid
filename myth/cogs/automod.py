import re

import aiohttp
import discord
from config import color, emoji
from discord.ext import commands
from system.base.context import Context


class AutoMod(commands.Cog):
    def __init__(self, client):
        self.client = client

    # AUTOMOD

    @commands.group(description="Filter out bad words", aliases=["am", "filter"])
    @commands.has_permissions(manage_guild=True)
    async def automod(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @automod.command(description="Add a word to automod")
    @commands.has_permissions(manage_guild=True)
    async def add(self, ctx: commands.Context, *, word: str = None):
        if word is None:
            await ctx.warn("**You're** missing text")
            return

        await self.client.pool.execute(
            "INSERT INTO automod (guild_id, word) VALUES ($1, $2)",
            ctx.guild.id,
            word.lower(),
        )
        await ctx.agree(f"**Started** filtering `{word}`")
        await self.update_word_rule(ctx.guild)

    @automod.command(description="Remove a word from automod")
    @commands.has_permissions(manage_guild=True)
    async def remove(self, ctx: commands.Context, *, word: str):
        if word is None:
            await ctx.warn("**You're** missing text")
            return

        await self.client.pool.execute(
            "DELETE FROM automod WHERE guild_id = $1 AND word = $2",
            ctx.guild.id,
            word.lower(),
        )
        await ctx.agree(f"**Stopped** filtering `{word}`")
        await self.update_word_rule(ctx.guild)

    # ANTILINK

    @commands.group(description="Filter out harmful links or invites", aliases=["al"])
    @commands.has_permissions(manage_guild=True)
    async def antilink(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @antilink.command(description="Filter out discord invites")
    @commands.has_permissions(manage_guild=True)
    async def invites(self, ctx: commands.Context):
        pattern = r"discord\.gg/"
        await self.client.pool.execute(
            "INSERT INTO antilink (guild_id, pattern) VALUES ($1, $2)",
            ctx.guild.id,
            pattern,
        )
        await ctx.agree(f"**Started** filtering discord invites")
        await self.update_invites(ctx.guild, [pattern])

    @antilink.command(description="Filter out links")
    @commands.has_permissions(manage_guild=True)
    async def links(self, ctx: commands.Context):
        pattern = r"https?://(?:www\.)?[a-zA-Z0-9./]+"
        await self.client.pool.execute(
            "INSERT INTO antilink (guild_id, pattern) VALUES ($1, $2)",
            ctx.guild.id,
            pattern,
        )
        await ctx.agree(f"**Started** filtering links")
        await self.update_links(ctx.guild, [pattern])

    # EVENTS

    async def update_word_rule(self, guild: discord.Guild):
        words = await self.client.pool.fetch(
            "SELECT word FROM automod WHERE guild_id = $1", guild.id
        )
        words = [row["word"] for row in words]
        name = "Myth automod words"
        trigger_type = 1
        metadata = {"keyword_filter": words}
        action = [
            {
                "type": 1,
                "metadata": {
                    "custom_message": "Message blocked by Myth due to having a filtered word"
                },
            }
        ]
        await self.update_rule(guild, name, trigger_type, metadata, action)

    async def update_invites(self, guild: discord.Guild, patterns: list):
        name = "Myth automod invites"
        trigger_type = 1
        metadata = {"regex_patterns": patterns}
        action = [
            {
                "type": 1,
                "metadata": {
                    "custom_message": "Message blocked by Myth due to having an invite"
                },
            }
        ]
        await self.update_rule(guild, name, trigger_type, metadata, action)

    async def update_links(self, guild: discord.Guild, patterns: list):
        name = "Myth automod links"
        trigger_type = 1
        metadata = {"regex_patterns": patterns}
        action = [
            {
                "type": 1,
                "metadata": {
                    "custom_message": "Message blocked by Myth due to having a link"
                },
            }
        ]
        await self.update_rule(guild, name, trigger_type, metadata, action)

    async def update_rule(
        self,
        guild: discord.Guild,
        rule_name: str,
        trigger_type: int,
        trigger_metadata: dict,
        actions: list,
    ):
        payload = {
            "name": rule_name,
            "event_type": 1,
            "trigger_type": trigger_type,
            "trigger_metadata": trigger_metadata,
            "actions": actions,
            "enabled": True,
        }
        headers = {
            "Authorization": f"Bot {self.client.http.token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://discord.com/api/v10/guilds/{guild.id}/auto-moderation/rules",
                headers=headers,
            ) as response:
                if response.status == 200:
                    rules = await response.json()
                    for rule in rules:
                        if rule["name"] == rule_name:
                            async with session.patch(
                                f"https://discord.com/api/v10/guilds/{guild.id}/auto-moderation/rules/{rule['id']}",
                                headers=headers,
                                json=payload,
                            ) as update_response:
                                if update_response.status in (200, 201):
                                    return True
                                else:
                                    error_message = await update_response.text()
                                    print(f"Failed to update rule: {error_message}")
                                    return False

            async with session.post(
                f"https://discord.com/api/v10/guilds/{guild.id}/auto-moderation/rules",
                headers=headers,
                json=payload,
            ) as response:
                if response.status in (200, 201):
                    return True
                else:
                    error_message = await response.text()
                    print(f"Failed to create rule: {error_message}")
                    return False


async def setup(client):
    await client.add_cog(AutoMod(client))
