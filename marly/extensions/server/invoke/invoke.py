from discord.ext.commands import (
    command,
    Cog,
    group,
    parameter,
    UserConverter,
    CommandError,
    has_permissions,
)
from discord import Member, User, Permissions, Message
from discord.utils import format_dt, oauth_url
from system.base.embed import EmbedScript
from system import Marly
from config import Emojis, Color, Marly
from system.base.context import Context
from system.base.settings import Settings
from typing import Optional

from system.tools.metaclass import CompositeMetaClass, MixinMeta


class invoke(MixinMeta, metaclass=CompositeMetaClass):
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
    async def invoke_kick(self, ctx: Context) -> Message:
        """Change kick message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_kick.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_kick_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change kick message for command response"""
        await ctx.settings.update(invoke_kick_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} kick message",
            f"Use `{ctx.clean_prefix}invoke kick message remove` to remove it",
        )

    @invoke_kick_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_kick_message_view(self, ctx: Context) -> Message:
        """View the kick message for command response"""
        if not ctx.settings.invoke_kick_message:
            return await ctx.warn("No kick message set")
        return await ctx.neutral(
            f"Kick Message:\n```\n{ctx.settings.invoke_kick_message}\n```"
        )

    @invoke_kick_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_kick_message_remove(self, ctx: Context) -> Message:
        """Remove the kick message."""
        await ctx.settings.update(invoke_kick_message=None)
        return await ctx.approve("Removed the **kick** message")

    @invoke_kick.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_kick_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change kick message for Direct Messages"""
        await ctx.settings.update(invoke_kick_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} kick DM message",
            f"Use `{ctx.clean_prefix}invoke kick dm remove` to remove it",
        )

    @invoke_kick_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_kick_dm_view(self, ctx: Context) -> Message:
        """View the kick message for Direct Messages"""
        if not ctx.settings.invoke_kick_dm:
            return await ctx.warn("No kick DM message set")
        return await ctx.neutral(
            f"Kick DM Message:\n```\n{ctx.settings.invoke_kick_dm}\n```"
        )

    @invoke_kick_dm.command(name="remove", aliases=["delete", "del", "rm"], hidden=True)
    @has_permissions(manage_guild=True)
    async def invoke_kick_dm_remove(self, ctx: Context) -> Message:
        """Remove the kick DM message."""
        await ctx.settings.update(invoke_kick_dm=None)
        return await ctx.approve("Removed the **kick** DM message")

    # Ban commands
    @invoke.group(name="ban", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_ban(self, ctx: Context) -> Message:
        """Change ban message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_ban.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_ban_message(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change ban message for command response"""
        await ctx.settings.update(invoke_ban_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} ban message",
            f"Use `{ctx.clean_prefix}invoke ban message remove` to remove it",
        )

    @invoke_ban_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_ban_message_view(self, ctx: Context) -> Message:
        """View the ban message for command response"""
        if not ctx.settings.invoke_ban_message:
            return await ctx.warn("No ban message set")
        return await ctx.neutral(
            f"Ban Message:\n```\n{ctx.settings.invoke_ban_message}\n```"
        )

    @invoke_ban_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_ban_message_remove(self, ctx: Context) -> Message:
        """Remove the ban message."""
        await ctx.settings.update(invoke_ban_message=None)
        return await ctx.approve("Removed the **ban** message")

    @invoke_ban.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_ban_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change ban message for Direct Messages"""
        await ctx.settings.update(invoke_ban_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} ban DM message",
            f"Use `{ctx.clean_prefix}invoke ban dm remove` to remove it",
        )

    @invoke_ban_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_ban_dm_view(self, ctx: Context) -> Message:
        """View the ban message for Direct Messages"""
        if not ctx.settings.invoke_ban_dm:
            return await ctx.warn("No ban DM message set")
        return await ctx.neutral(
            f"Ban DM Message:\n```\n{ctx.settings.invoke_ban_dm}\n```"
        )

    @invoke_ban_dm.command(name="remove", aliases=["delete", "del", "rm"], hidden=True)
    @has_permissions(manage_guild=True)
    async def invoke_ban_dm_remove(self, ctx: Context) -> Message:
        """Remove the ban DM message."""
        await ctx.settings.update(invoke_ban_dm=None)
        return await ctx.approve("Removed the **ban** DM message")

    @invoke.group(name="unban", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_unban(self, ctx: Context) -> Message:
        """Change unban message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_unban.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_unban_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change unban message for command response"""
        await ctx.settings.update(invoke_unban_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} unban message",
            f"Use `{ctx.clean_prefix}invoke unban message remove` to remove it",
        )

    @invoke_unban_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_unban_message_view(self, ctx: Context) -> Message:
        """View the unban message for command response"""
        if not ctx.settings.invoke_unban_message:
            return await ctx.warn("No unban message set")
        return await ctx.neutral(
            f"Unban Message:\n```\n{ctx.settings.invoke_unban_message}\n```"
        )

    @invoke_unban_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_unban_message_remove(self, ctx: Context) -> Message:
        """Remove the unban message."""
        await ctx.settings.update(invoke_unban_message=None)
        return await ctx.approve("Removed the **unban** message")

    @invoke_unban.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_unban_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change unban message for Direct Messages"""
        await ctx.settings.update(invoke_unban_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} unban DM message",
            f"Use `{ctx.clean_prefix}invoke unban dm remove` to remove it",
        )

    @invoke_unban_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_unban_dm_view(self, ctx: Context) -> Message:
        """View the unban message for Direct Messages"""
        if not ctx.settings.invoke_unban_dm:
            return await ctx.warn("No unban DM message set")
        return await ctx.neutral(
            f"Unban DM Message:\n```\n{ctx.settings.invoke_unban_dm}\n```"
        )

    @invoke_unban_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_unban_dm_remove(self, ctx: Context) -> Message:
        """Remove the unban DM message."""
        await ctx.settings.update(invoke_unban_dm=None)
        return await ctx.approve("Removed the **unban** DM message")

    @invoke.group(name="timeout", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_timeout(self, ctx: Context) -> Message:
        """Change timeout message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_timeout.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_timeout_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change timeout message for command response"""
        await ctx.settings.update(invoke_timeout_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} timeout message",
            f"Use `{ctx.clean_prefix}invoke timeout message remove` to remove it",
        )

    @invoke_timeout_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_timeout_message_view(self, ctx: Context) -> Message:
        """View the timeout message for command response"""
        if not ctx.settings.invoke_timeout_message:
            return await ctx.warn("No timeout message set")
        return await ctx.neutral(
            f"Timeout Message:\n```\n{ctx.settings.invoke_timeout_message}\n```"
        )

    @invoke_timeout_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_timeout_message_remove(self, ctx: Context) -> Message:
        """Remove the timeout message."""
        await ctx.settings.update(invoke_timeout_message=None)
        return await ctx.approve("Removed the **timeout** message")

    @invoke_timeout.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_timeout_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change timeout message for Direct Messages"""
        await ctx.settings.update(invoke_timeout_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} timeout DM message",
            f"Use `{ctx.clean_prefix}invoke timeout dm remove` to remove it",
        )

    @invoke_timeout_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_timeout_dm_view(self, ctx: Context) -> Message:
        """View the timeout message for Direct Messages"""
        if not ctx.settings.invoke_timeout_dm:
            return await ctx.warn("No timeout DM message set")
        return await ctx.neutral(
            f"Timeout DM Message:\n```\n{ctx.settings.invoke_timeout_dm}\n```"
        )

    @invoke_timeout_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_timeout_dm_remove(self, ctx: Context) -> Message:
        """Remove the timeout DM message."""
        await ctx.settings.update(invoke_timeout_dm=None)
        return await ctx.approve("Removed the **timeout** DM message")

    # Untimeout commands
    @invoke.group(name="untimeout", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_untimeout(self, ctx: Context) -> Message:
        """Change untimeout message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_untimeout.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change untimeout message for command response"""
        await ctx.settings.update(invoke_untimeout_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} untimeout message",
            f"Use `{ctx.clean_prefix}invoke untimeout message remove` to remove it",
        )

    @invoke_untimeout_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_message_view(self, ctx: Context) -> Message:
        """View the untimeout message for command response"""
        if not ctx.settings.invoke_untimeout_message:
            return await ctx.warn("No untimeout message set")
        return await ctx.neutral(
            f"Untimeout Message:\n```\n{ctx.settings.invoke_untimeout_message}\n```"
        )

    @invoke_untimeout_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_message_remove(self, ctx: Context) -> Message:
        """Remove the untimeout message."""
        await ctx.settings.update(invoke_untimeout_message=None)
        return await ctx.approve("Removed the **untimeout** message")

    @invoke_untimeout.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_dm(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change untimeout message for Direct Messages"""
        await ctx.settings.update(invoke_untimeout_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} untimeout DM message",
            f"Use `{ctx.clean_prefix}invoke untimeout dm remove` to remove it",
        )

    @invoke_untimeout_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_dm_view(self, ctx: Context) -> Message:
        """View the untimeout message for Direct Messages"""
        if not ctx.settings.invoke_untimeout_dm:
            return await ctx.warn("No untimeout DM message set")
        return await ctx.neutral(
            f"Untimeout DM Message:\n```\n{ctx.settings.invoke_untimeout_dm}\n```"
        )

    @invoke_untimeout_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_dm_remove(self, ctx: Context) -> Message:
        """Remove the untimeout DM message."""
        await ctx.settings.update(invoke_untimeout_dm=None)
        return await ctx.approve("Removed the **untimeout** DM message")

    @invoke.group(name="mute", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_mute(self, ctx: Context) -> Message:
        """Change mute message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_mute.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_mute_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change mute message for command response"""
        await ctx.settings.update(invoke_mute_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} mute message",
            f"Use `{ctx.clean_prefix}invoke mute message remove` to remove it",
        )

    @invoke_mute_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_mute_message_view(self, ctx: Context) -> Message:
        """View the mute message for command response"""
        if not ctx.settings.invoke_mute_message:
            return await ctx.warn("No mute message set")
        return await ctx.neutral(
            f"Mute Message:\n```\n{ctx.settings.invoke_mute_message}\n```"
        )

    @invoke_mute_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_mute_message_remove(self, ctx: Context) -> Message:
        """Remove the mute message."""
        await ctx.settings.update(invoke_mute_message=None)
        return await ctx.approve("Removed the **mute** message")

    @invoke_mute.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_mute_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change mute message for Direct Messages"""
        await ctx.settings.update(invoke_mute_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} mute DM message",
            f"Use `{ctx.clean_prefix}invoke mute dm remove` to remove it",
        )

    @invoke_mute_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_mute_dm_view(self, ctx: Context) -> Message:
        """View the mute message for Direct Messages"""
        if not ctx.settings.invoke_mute_dm:
            return await ctx.warn("No mute DM message set")
        return await ctx.neutral(
            f"Mute DM Message:\n```\n{ctx.settings.invoke_mute_dm}\n```"
        )

    @invoke_mute_dm.command(name="remove", aliases=["delete", "del", "rm"], hidden=True)
    @has_permissions(manage_guild=True)
    async def invoke_mute_dm_remove(self, ctx: Context) -> Message:
        """Remove the mute DM message."""
        await ctx.settings.update(invoke_mute_dm=None)
        return await ctx.approve("Removed the **mute** DM message")

    # Unmute commands
    @invoke.group(name="unmute", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_unmute(self, ctx: Context) -> Message:
        """Change unmute message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_unmute.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_unmute_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change unmute message for command response"""
        await ctx.settings.update(invoke_unmute_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} unmute message",
            f"Use `{ctx.clean_prefix}invoke unmute message remove` to remove it",
        )

    @invoke_unmute_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_unmute_message_view(self, ctx: Context) -> Message:
        """View the unmute message for command response"""
        if not ctx.settings.invoke_unmute_message:
            return await ctx.warn("No unmute message set")
        return await ctx.neutral(
            f"Unmute Message:\n```\n{ctx.settings.invoke_unmute_message}\n```"
        )

    @invoke_unmute_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_unmute_message_remove(self, ctx: Context) -> Message:
        """Remove the unmute message."""
        await ctx.settings.update(invoke_unmute_message=None)
        return await ctx.approve("Removed the **unmute** message")

    @invoke_unmute.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_unmute_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change unmute message for Direct Messages"""
        await ctx.settings.update(invoke_unmute_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} unmute DM message",
            f"Use `{ctx.clean_prefix}invoke unmute dm remove` to remove it",
        )

    @invoke_unmute_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_unmute_dm_view(self, ctx: Context) -> Message:
        """View the unmute message for Direct Messages"""
        if not ctx.settings.invoke_unmute_dm:
            return await ctx.warn("No unmute DM message set")
        return await ctx.neutral(
            f"Unmute DM Message:\n```\n{ctx.settings.invoke_unmute_dm}\n```"
        )

    @invoke_unmute_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_unmute_dm_remove(self, ctx: Context) -> Message:
        """Remove the unmute DM message."""
        await ctx.settings.update(invoke_unmute_dm=None)
        return await ctx.approve("Removed the **unmute** DM message")

    # Warn commands
    @invoke.group(name="warn", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_warn(self, ctx: Context) -> Message:
        """Change warn message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_warn.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_warn_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change warn message for command response"""
        await ctx.settings.update(invoke_warn_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} warn message",
            f"Use `{ctx.clean_prefix}invoke warn message remove` to remove it",
        )

    @invoke_warn_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_warn_message_view(self, ctx: Context) -> Message:
        """View the warn message for command response"""
        if not ctx.settings.invoke_warn_message:
            return await ctx.warn("No warn message set")
        return await ctx.neutral(
            f"Warn Message:\n```\n{ctx.settings.invoke_warn_message}\n```"
        )

    @invoke_warn_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_warn_message_remove(self, ctx: Context) -> Message:
        """Remove the warn message."""
        await ctx.settings.update(invoke_warn_message=None)
        return await ctx.approve("Removed the **warn** message")

    @invoke_warn.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_warn_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change warn message for Direct Messages"""
        await ctx.settings.update(invoke_warn_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} warn DM message",
            f"Use `{ctx.clean_prefix}invoke warn dm remove` to remove it",
        )

    @invoke_warn_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_warn_dm_view(self, ctx: Context) -> Message:
        """View the warn message for Direct Messages"""
        if not ctx.settings.invoke_warn_dm:
            return await ctx.warn("No warn DM message set")
        return await ctx.neutral(
            f"Warn DM Message:\n```\n{ctx.settings.invoke_warn_dm}\n```"
        )

    @invoke_warn_dm.command(name="remove", aliases=["delete", "del", "rm"], hidden=True)
    @has_permissions(manage_guild=True)
    async def invoke_warn_dm_remove(self, ctx: Context) -> Message:
        """Remove the warn DM message."""
        await ctx.settings.update(invoke_warn_dm=None)
        return await ctx.approve("Removed the **warn** DM message")

    # Jail commands
    @invoke.group(name="jail", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_jail(self, ctx: Context) -> Message:
        """Change jail message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_jail.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_jail_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change jail message for command response"""
        await ctx.settings.update(invoke_jail_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} jail message",
            f"Use `{ctx.clean_prefix}invoke jail message remove` to remove it",
        )

    @invoke_jail_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_jail_message_view(self, ctx: Context) -> Message:
        """View the jail message for command response"""
        if not ctx.settings.invoke_jail_message:
            return await ctx.warn("No jail message set")
        return await ctx.neutral(
            f"Jail Message:\n```\n{ctx.settings.invoke_jail_message}\n```"
        )

    @invoke_jail_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_jail_message_remove(self, ctx: Context) -> Message:
        """Remove the jail message."""
        await ctx.settings.update(invoke_jail_message=None)
        return await ctx.approve("Removed the **jail** message")

    @invoke_jail.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_jail_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change jail message for Direct Messages"""
        await ctx.settings.update(invoke_jail_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} jail DM message",
            f"Use `{ctx.clean_prefix}invoke jail dm remove` to remove it",
        )

    @invoke_jail_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_jail_dm_view(self, ctx: Context) -> Message:
        """View the jail message for Direct Messages"""
        if not ctx.settings.invoke_jail_dm:
            return await ctx.warn("No jail DM message set")
        return await ctx.neutral(
            f"Jail DM Message:\n```\n{ctx.settings.invoke_jail_dm}\n```"
        )

    @invoke_jail_dm.command(name="remove", aliases=["delete", "del", "rm"], hidden=True)
    @has_permissions(manage_guild=True)
    async def invoke_jail_dm_remove(self, ctx: Context) -> Message:
        """Remove the jail DM message."""
        await ctx.settings.update(invoke_jail_dm=None)
        return await ctx.approve("Removed the **jail** DM message")

    # Unjail commands
    @invoke.group(name="unjail", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_unjail(self, ctx: Context) -> Message:
        """Change unjail message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_unjail.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_unjail_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change unjail message for command response"""
        await ctx.settings.update(invoke_unjail_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} unjail message",
            f"Use `{ctx.clean_prefix}invoke unjail message remove` to remove it",
        )

    @invoke_unjail_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_unjail_message_view(self, ctx: Context) -> Message:
        """View the unjail message for command response"""
        if not ctx.settings.invoke_unjail_message:
            return await ctx.warn("No unjail message set")
        return await ctx.neutral(
            f"Unjail Message:\n```\n{ctx.settings.invoke_unjail_message}\n```"
        )

    @invoke_unjail_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_unjail_message_remove(self, ctx: Context) -> Message:
        """Remove the unjail message."""
        await ctx.settings.update(invoke_unjail_message=None)
        return await ctx.approve("Removed the **unjail** message")

    @invoke_unjail.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_unjail_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change unjail message for Direct Messages"""
        await ctx.settings.update(invoke_unjail_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} unjail DM message",
            f"Use `{ctx.clean_prefix}invoke unjail dm remove` to remove it",
        )

    @invoke_unjail_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_unjail_dm_view(self, ctx: Context) -> Message:
        """View the unjail message for Direct Messages"""
        if not ctx.settings.invoke_unjail_dm:
            return await ctx.warn("No unjail DM message set")
        return await ctx.neutral(
            f"Unjail DM Message:\n```\n{ctx.settings.invoke_unjail_dm}\n```"
        )

    @invoke_unjail_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_unjail_dm_remove(self, ctx: Context) -> Message:
        """Remove the unjail DM message."""
        await ctx.settings.update(invoke_unjail_dm=None)
        return await ctx.approve("Removed the **unjail** DM message")

    # Softban commands
    @invoke.group(name="softban", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_softban(self, ctx: Context) -> Message:
        """Change softban message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_softban.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_softban_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change softban message for command response"""
        await ctx.settings.update(invoke_softban_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} softban message",
            f"Use `{ctx.clean_prefix}invoke softban message remove` to remove it",
        )

    @invoke_softban_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_softban_message_view(self, ctx: Context) -> Message:
        """View the softban message for command response"""
        if not ctx.settings.invoke_softban_message:
            return await ctx.warn("No softban message set")
        return await ctx.neutral(
            f"Softban Message:\n```\n{ctx.settings.invoke_softban_message}\n```"
        )

    @invoke_softban_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_softban_message_remove(self, ctx: Context) -> Message:
        """Remove the softban message."""
        await ctx.settings.update(invoke_softban_message=None)
        return await ctx.approve("Removed the **softban** message")

    @invoke_softban.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_softban_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change softban message for Direct Messages"""
        await ctx.settings.update(invoke_softban_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} softban DM message",
            f"Use `{ctx.clean_prefix}invoke softban dm remove` to remove it",
        )

    @invoke_softban_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_softban_dm_view(self, ctx: Context) -> Message:
        """View the softban message for Direct Messages"""
        if not ctx.settings.invoke_softban_dm:
            return await ctx.warn("No softban DM message set")
        return await ctx.neutral(
            f"Softban DM Message:\n```\n{ctx.settings.invoke_softban_dm}\n```"
        )

    @invoke_softban_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_softban_dm_remove(self, ctx: Context) -> Message:
        """Remove the softban DM message."""
        await ctx.settings.update(invoke_softban_dm=None)
        return await ctx.approve("Removed the **softban** DM message")

    # Hardban commands
    @invoke.group(name="hardban", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_hardban(self, ctx: Context) -> Message:
        """Change hardban message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_hardban.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_hardban_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change hardban message for command response"""
        await ctx.settings.update(invoke_hardban_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} hardban message",
            f"Use `{ctx.clean_prefix}invoke hardban message remove` to remove it",
        )

    @invoke_hardban_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_hardban_message_view(self, ctx: Context) -> Message:
        """View the hardban message for command response"""
        if not ctx.settings.invoke_hardban_message:
            return await ctx.warn("No hardban message set")
        return await ctx.neutral(
            f"Hardban Message:\n```\n{ctx.settings.invoke_hardban_message}\n```"
        )

    @invoke_hardban_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_hardban_message_remove(self, ctx: Context) -> Message:
        """Remove the hardban message."""
        await ctx.settings.update(invoke_hardban_message=None)
        return await ctx.approve("Removed the **hardban** message")

    @invoke_hardban.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_hardban_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change hardban message for Direct Messages"""
        await ctx.settings.update(invoke_hardban_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} hardban DM message",
            f"Use `{ctx.clean_prefix}invoke hardban dm remove` to remove it",
        )

    @invoke_hardban_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_hardban_dm_view(self, ctx: Context) -> Message:
        """View the hardban message for Direct Messages"""
        if not ctx.settings.invoke_hardban_dm:
            return await ctx.warn("No hardban DM message set")
        return await ctx.neutral(
            f"Hardban DM Message:\n```\n{ctx.settings.invoke_hardban_dm}\n```"
        )

    @invoke_hardban_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_hardban_dm_remove(self, ctx: Context) -> Message:
        """Remove the hardban DM message."""
        await ctx.settings.update(invoke_hardban_dm=None)
        return await ctx.approve("Removed the **hardban** DM message")

    # Tempban commands
    @invoke.group(name="tempban", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_tempban(self, ctx: Context) -> Message:
        """Change tempban message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_tempban.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_tempban_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change tempban message for command response"""
        await ctx.settings.update(invoke_tempban_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} tempban message",
            f"Use `{ctx.clean_prefix}invoke tempban message remove` to remove it",
        )

    @invoke_tempban_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_tempban_message_view(self, ctx: Context) -> Message:
        """View the tempban message for command response"""
        if not ctx.settings.invoke_tempban_message:
            return await ctx.warn("No tempban message set")
        return await ctx.neutral(
            f"Tempban Message:\n```\n{ctx.settings.invoke_tempban_message}\n```"
        )

    @invoke_tempban_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_tempban_message_remove(self, ctx: Context) -> Message:
        """Remove the tempban message."""
        await ctx.settings.update(invoke_tempban_message=None)
        return await ctx.approve("Removed the **tempban** message")

    @invoke_tempban.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_tempban_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change tempban message for Direct Messages"""
        await ctx.settings.update(invoke_tempban_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} tempban DM message",
            f"Use `{ctx.clean_prefix}invoke tempban dm remove` to remove it",
        )

    @invoke_tempban_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_tempban_dm_view(self, ctx: Context) -> Message:
        """View the tempban message for Direct Messages"""
        if not ctx.settings.invoke_tempban_dm:
            return await ctx.warn("No tempban DM message set")
        return await ctx.neutral(
            f"Tempban DM Message:\n```\n{ctx.settings.invoke_tempban_dm}\n```"
        )

    @invoke_tempban_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_tempban_dm_remove(self, ctx: Context) -> Message:
        """Remove the tempban DM message."""
        await ctx.settings.update(invoke_tempban_dm=None)
        return await ctx.approve("Removed the **tempban** DM message")

    # IMute commands
    @invoke.group(name="imute", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_imute(self, ctx: Context) -> Message:
        """Change imute message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_imute.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_imute_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change imute message for command response"""
        await ctx.settings.update(invoke_imute_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} imute message",
            f"Use `{ctx.clean_prefix}invoke imute message remove` to remove it",
        )

    @invoke_imute_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_imute_message_view(self, ctx: Context) -> Message:
        """View the imute message for command response"""
        if not ctx.settings.invoke_imute_message:
            return await ctx.warn("No imute message set")
        return await ctx.neutral(
            f"IMute Message:\n```\n{ctx.settings.invoke_imute_message}\n```"
        )

    @invoke_imute_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_imute_message_remove(self, ctx: Context) -> Message:
        """Remove the imute message."""
        await ctx.settings.update(invoke_imute_message=None)
        return await ctx.approve("Removed the **imute** message")

    @invoke_imute.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_imute_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change imute message for Direct Messages"""
        await ctx.settings.update(invoke_imute_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} imute DM message",
            f"Use `{ctx.clean_prefix}invoke imute dm remove` to remove it",
        )

    @invoke_imute_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_imute_dm_view(self, ctx: Context) -> Message:
        """View the imute message for Direct Messages"""
        if not ctx.settings.invoke_imute_dm:
            return await ctx.warn("No imute DM message set")
        return await ctx.neutral(
            f"IMute DM Message:\n```\n{ctx.settings.invoke_imute_dm}\n```"
        )

    @invoke_imute_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_imute_dm_remove(self, ctx: Context) -> Message:
        """Remove the imute DM message."""
        await ctx.settings.update(invoke_imute_dm=None)
        return await ctx.approve("Removed the **imute** DM message")

    # IUnmute commands
    @invoke.group(name="iunmute", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_iunmute(self, ctx: Context) -> Message:
        """Change iunmute message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_iunmute.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_iunmute_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change iunmute message for command response"""
        await ctx.settings.update(invoke_iunmute_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} iunmute message",
            f"Use `{ctx.clean_prefix}invoke iunmute message remove` to remove it",
        )

    @invoke_iunmute_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_iunmute_message_view(self, ctx: Context) -> Message:
        """View the iunmute message for command response"""
        if not ctx.settings.invoke_iunmute_message:
            return await ctx.warn("No iunmute message set")
        return await ctx.neutral(
            f"IUnmute Message:\n```\n{ctx.settings.invoke_iunmute_message}\n```"
        )

    @invoke_iunmute_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_iunmute_message_remove(self, ctx: Context) -> Message:
        """Remove the iunmute message."""
        await ctx.settings.update(invoke_iunmute_message=None)
        return await ctx.approve("Removed the **iunmute** message")

    @invoke_iunmute.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_iunmute_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change iunmute message for Direct Messages"""
        await ctx.settings.update(invoke_iunmute_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} iunmute DM message",
            f"Use `{ctx.clean_prefix}invoke iunmute dm remove` to remove it",
        )

    @invoke_iunmute_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_iunmute_dm_view(self, ctx: Context) -> Message:
        """View the iunmute message for Direct Messages"""
        if not ctx.settings.invoke_iunmute_dm:
            return await ctx.warn("No iunmute DM message set")
        return await ctx.neutral(
            f"IUnmute DM Message:\n```\n{ctx.settings.invoke_iunmute_dm}\n```"
        )

    @invoke_iunmute_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_iunmute_dm_remove(self, ctx: Context) -> Message:
        """Remove the iunmute DM message."""
        await ctx.settings.update(invoke_iunmute_dm=None)
        return await ctx.approve("Removed the **iunmute** DM message")

    # RMute commands
    @invoke.group(name="rmute", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_rmute(self, ctx: Context) -> Message:
        """Change rmute message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_rmute.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_rmute_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change rmute message for command response"""
        await ctx.settings.update(invoke_rmute_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} rmute message",
            f"Use `{ctx.clean_prefix}invoke rmute message remove` to remove it",
        )

    @invoke_rmute_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_rmute_message_view(self, ctx: Context) -> Message:
        """View the rmute message for command response"""
        if not ctx.settings.invoke_rmute_message:
            return await ctx.warn("No rmute message set")
        return await ctx.neutral(
            f"RMute Message:\n```\n{ctx.settings.invoke_rmute_message}\n```"
        )

    @invoke_rmute_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_rmute_message_remove(self, ctx: Context) -> Message:
        """Remove the rmute message."""
        await ctx.settings.update(invoke_rmute_message=None)
        return await ctx.approve("Removed the **rmute** message")

    @invoke_rmute.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_rmute_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change rmute message for Direct Messages"""
        await ctx.settings.update(invoke_rmute_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} rmute DM message",
            f"Use `{ctx.clean_prefix}invoke rmute dm remove` to remove it",
        )

    @invoke_rmute_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_rmute_dm_view(self, ctx: Context) -> Message:
        """View the rmute message for Direct Messages"""
        if not ctx.settings.invoke_rmute_dm:
            return await ctx.warn("No rmute DM message set")
        return await ctx.neutral(
            f"RMute DM Message:\n```\n{ctx.settings.invoke_rmute_dm}\n```"
        )

    @invoke_rmute_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_rmute_dm_remove(self, ctx: Context) -> Message:
        """Remove the rmute DM message."""
        await ctx.settings.update(invoke_rmute_dm=None)
        return await ctx.approve("Removed the **rmute** DM message")

    # RUnmute commands
    @invoke.group(name="runmute", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_runmute(self, ctx: Context) -> Message:
        """Change runmute message for DM or command response"""
        return await ctx.send_help(ctx.command)

    @invoke_runmute.group(name="message", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_runmute_message(
        self, ctx: Context, *, script: EmbedScript
    ) -> Message:
        """Change runmute message for command response"""
        await ctx.settings.update(invoke_runmute_message=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} runmute message",
            f"Use `{ctx.clean_prefix}invoke runmute message remove` to remove it",
        )

    @invoke_runmute_message.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_runmute_message_view(self, ctx: Context) -> Message:
        """View the runmute message for command response"""
        if not ctx.settings.invoke_runmute_message:
            return await ctx.warn("No runmute message set")
        return await ctx.neutral(
            f"RUnmute Message:\n```\n{ctx.settings.invoke_runmute_message}\n```"
        )

    @invoke_runmute_message.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_runmute_message_remove(self, ctx: Context) -> Message:
        """Remove the runmute message."""
        await ctx.settings.update(invoke_runmute_message=None)
        return await ctx.approve("Removed the **runmute** message")

    @invoke_runmute.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_runmute_dm(self, ctx: Context, *, script: EmbedScript) -> Message:
        """Change runmute message for Direct Messages"""
        await ctx.settings.update(invoke_runmute_dm=str(script))
        return await ctx.approve(
            f"Successfully set {script.type()} runmute DM message",
            f"Use `{ctx.clean_prefix}invoke runmute dm remove` to remove it",
        )

    @invoke_runmute_dm.command(name="view")
    @has_permissions(manage_guild=True)
    async def invoke_runmute_dm_view(self, ctx: Context) -> Message:
        """View the runmute message for Direct Messages"""
        if not ctx.settings.invoke_runmute_dm:
            return await ctx.warn("No runmute DM message set")
        return await ctx.neutral(
            f"RUnmute DM Message:\n```\n{ctx.settings.invoke_runmute_dm}\n```"
        )

    @invoke_runmute_dm.command(
        name="remove", aliases=["delete", "del", "rm"], hidden=True
    )
    @has_permissions(manage_guild=True)
    async def invoke_runmute_dm_remove(self, ctx: Context) -> Message:
        """Remove the runmute DM message."""
        await ctx.settings.update(invoke_runmute_dm=None)
        return await ctx.approve("Removed the **runmute** DM message")

    @invoke.command(name="reset", aliases=["clear"])
    @has_permissions(manage_guild=True)
    async def invoke_reset(self, ctx: Context) -> Message:
        """Remove all invoke messages (both channel and DM messages)"""
        await ctx.prompt(
            "Are you sure you want to reset **all** invoke messages?\n"
            "This will remove both channel and DM messages for all moderation commands."
        )

        await ctx.settings.update(
            # Channel invoke messages
            invoke_kick_message=None,
            invoke_ban_message=None,
            invoke_unban_message=None,
            invoke_timeout_message=None,
            invoke_untimeout_message=None,
            invoke_mute_message=None,
            invoke_unmute_message=None,
            invoke_softban_message=None,
            invoke_warn_message=None,
            invoke_tempban_message=None,
            invoke_hardban_message=None,
            invoke_jail_message=None,
            invoke_unjail_message=None,
            invoke_imute_message=None,
            invoke_iunmute_message=None,
            invoke_rmute_message=None,
            invoke_runmute_message=None,
            # DM invoke messages
            invoke_unban_dm=None,
            invoke_kick_dm=None,
            invoke_ban_dm=None,
            invoke_timeout_dm=None,
            invoke_untimeout_dm=None,
            invoke_mute_dm=None,
            invoke_unmute_dm=None,
            invoke_softban_dm=None,
            invoke_warn_dm=None,
            invoke_tempban_dm=None,
            invoke_hardban_dm=None,
            invoke_jail_dm=None,
            invoke_unjail_dm=None,
        )

        return await ctx.approve("Successfully reset all **invoke messages**")


#    @invoke.group(name="settings", invoke_without_command=True)
#    @has_permissions(manage_guild=True)
#    async def invoke_settings(self, ctx: Context) -> Message:
#        """Manage invoke settings."""
#        return await ctx.send_help(ctx.command)
#
#    @invoke_settings.command(name="silent", invoke_without_command=True)
#    @has_permissions(manage_guild=True)
#    async def invoke_settings_silent(self, ctx: Context, setting: str) -> Message:
#        """Toggle silent mode for DM messages."""
#        setting = setting.lower()
#        if setting not in ("on", "off"):
#            raise CommandError("Setting must be 'on' or 'off'")
#
#        silent_mode = setting == "on"
#        await ctx.settings.update(invoke_silent_mode=silent_mode)
#
#        status = "enabled" if silent_mode else "disabled"
#        return await ctx.approve(f"Silent mode for DM messages **{status}**")
