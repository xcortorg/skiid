from __future__ import annotations

import asyncio
from typing import List, Optional, cast

import config
from cashews import cache
from core.client.context import Context
from core.client.database.settings import Settings
from core.managers.script import EmbedScript, EmbedScriptValidator
from core.Mono import Mono
from core.tools import codeblock, plural, quietly_delete, vowel
from discord import AuditLogEntry, HTTPException, Message, TextChannel
from discord.ext.commands import (BucketType, Cog, Range, cooldown, group,
                                  has_permissions, parameter)

from .extended import Extended


class Server(Extended, Cog):
    def __init__(self, bot: Mono):
        self.bot = bot

    @group(invoke_without_command=True)
    async def prefix(self, ctx: Context) -> Message:
        """
        View the current server prefix and your personal prefix.
        """
        server_prefix = ctx.settings.prefix or config.Mono.prefix
        self_prefix = await Settings.get_self_prefix(self.bot, ctx.author)

        message = f"The current **server prefix** is: `{server_prefix}`"
        if self_prefix:
            message += f"\n> Your **self-prefix** is: `{self_prefix}`"

        return await ctx.neutral(message)

    @prefix.command(name="set")
    @has_permissions(manage_guild=True)
    async def prefix_set(self, ctx: Context, prefix: str) -> Message:
        """
        Set the server prefix.
        """

        if not prefix:
            return await ctx.warn("You must provide a prefix!")

        await ctx.prompt(
            f"Are you sure you want to set the prefix to `{prefix}`?",
            "This will overwrite all existing prefixes.",
        )

        await ctx.settings.update(prefixes=[prefix])
        return await ctx.approve(f"The prefix has been set to `{prefix}`")

    @prefix.command(name="add")
    @has_permissions(manage_guild=True)
    async def prefix_add(self, ctx: Context, prefix: str) -> Message:
        """
        Add a prefix to the server.
        """

        if not prefix:
            return await ctx.warn("You must provide a prefix!")

        elif prefix in ctx.settings.prefixes:
            return await ctx.warn(f"`{prefix}` is already a prefix!")

        await ctx.settings.update(prefixes=[*ctx.settings.prefixes, prefix])
        return await ctx.approve(f"Now accepting `{prefix}` as a prefix")

    @prefix.command(name="remove")
    @has_permissions(manage_guild=True)
    async def prefix_remove(self, ctx: Context, prefix: str) -> Message:
        """
        Remove a prefix from the server.
        """

        if not prefix:
            return await ctx.warn("You must provide a prefix!")

        elif prefix not in ctx.settings.prefixes:
            return await ctx.warn(f"`{prefix}` is not a prefix!")

        await ctx.settings.update(
            prefixes=[p for p in ctx.settings.prefixes if p != prefix]
        )
        return await ctx.approve(f"No longer accepting `{prefix}` as a prefix")

    @prefix.command(name="reset")
    @has_permissions(manage_guild=True)
    async def prefix_reset(self, ctx: Context) -> Message:
        """
        Reset the server prefixes.
        """

        await ctx.settings.update(prefixes=[])
        return await ctx.approve("Reset the server prefixes")

    @group(invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke(self, ctx: Context) -> Message:
        """
        Set custom moderation invoke messages.

        Accepts the `moderator` and `reason` variables.
        """
        return await ctx.send_help(ctx.command)

    @invoke.group(name="kick", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_kick(
        self, ctx: Context, *, script: EmbedScriptValidator
    ) -> Message:
        """
        Set the kick invoke message.
        """
        await ctx.settings.update(invoke_kick=script.script)
        return await ctx.approve(
            f"Successfully set {vowel(script.type())} **kick** message",
            f"Use `{ctx.clean_prefix}invoke kick remove` to remove it",
        )

    @invoke_kick.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        hidden=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_kick_remove(self, ctx: Context) -> Message:
        """
        Remove the kick invoke message.
        """
        await ctx.settings.update(invoke_kick=None)
        return await ctx.approve("Removed the **kick** invoke message")

    @invoke.group(name="ban", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_ban(
        self, ctx: Context, *, script: EmbedScriptValidator
    ) -> Message:
        """
        Set the ban invoke message.
        """
        await ctx.settings.update(invoke_ban=script.script)
        return await ctx.approve(
            f"Successfully set {vowel(script.type())} **ban** message",
            f"Use `{ctx.clean_prefix}invoke ban remove` to remove it",
        )

    @invoke_ban.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        hidden=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_ban_remove(self, ctx: Context) -> Message:
        """
        Remove the ban invoke message.
        """
        await ctx.settings.update(invoke_ban=None)
        return await ctx.approve("Removed the **ban** invoke message")

    @invoke.group(name="unban", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_unban(
        self, ctx: Context, *, script: EmbedScriptValidator
    ) -> Message:
        """
        Set the unban invoke message.
        """
        await ctx.settings.update(invoke_unban=script.script)
        return await ctx.approve(
            f"Successfully set {vowel(script.type())} **unban** message",
            f"Use `{ctx.clean_prefix}invoke unban remove` to remove it",
        )

    @invoke_unban.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        hidden=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_unban_remove(self, ctx: Context) -> Message:
        """
        Remove the unban invoke message.
        """
        await ctx.settings.update(invoke_unban=None)
        return await ctx.approve("Removed the **unban** invoke message")

    @invoke.group(name="timeout", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_timeout(
        self, ctx: Context, *, script: EmbedScriptValidator
    ) -> Message:
        """
        Set the timeout invoke message.

        Accepts the `duration` and `expires` variables.
        """
        await ctx.settings.update(invoke_timeout=script.script)
        return await ctx.approve(
            f"Successfully set {vowel(script.type())} **timeout** message",
            f"Use `{ctx.clean_prefix}invoke timeout remove` to remove it",
        )

    @invoke_timeout.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        hidden=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_timeout_remove(self, ctx: Context) -> Message:
        """
        Remove the timeout invoke message.
        """
        await ctx.settings.update(invoke_timeout=None)
        return await ctx.approve("Removed the **timeout** invoke message")

    @invoke.group(name="untimeout", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_untimeout(
        self, ctx: Context, *, script: EmbedScriptValidator
    ) -> Message:
        """
        Set the untimeout invoke message.
        """
        await ctx.settings.update(invoke_untimeout=script.script)
        return await ctx.approve(
            f"Successfully set {vowel(script.type())} **untimeout** message",
            f"Use `{ctx.clean_prefix}invoke untimeout remove` to remove it",
        )

    @invoke_untimeout.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        hidden=True,
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_remove(self, ctx: Context) -> Message:
        """
        Remove the untimeout invoke message.
        """
        await ctx.settings.update(invoke_untimeout=None)
        return await ctx.approve("Removed the **untimeout** invoke message")
