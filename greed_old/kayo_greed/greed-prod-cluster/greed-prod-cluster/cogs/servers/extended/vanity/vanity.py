from contextlib import suppress
from typing import Annotated, cast

from discord import (
    CustomActivity,
    HTTPException,
    Member,
    Message,
    Role,
    Status,
    TextChannel,
    Thread,
    Embed,
)
from discord.ext.commands import Cog, check, group, has_permissions
from discord.utils import find

from tools import CompositeMetaClass, MixinMeta
from tools.client import Context
from tools.conversion import StrictRole
from tools.formatter import vowel
from tools.parser import Script
import config


class Vanity(MixinMeta, metaclass=CompositeMetaClass):
    """
    cog for vanity related commands
    """

    @Cog.listener()
    async def on_guild_update(
        self, before: TextChannel | Thread, after: TextChannel | Thread
    ):
        if before.vanity_url_code != after.vanity_url_code:
            records = await self.bot.db.fetch(
                "SELECT channel_id FROM vanity_channels WHERE guild_id = $1",
                after.id,
            )
            vanity_channels = [record["channel_id"] for record in records]

            if vanity_channels:
                for channel_id in vanity_channels:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        embed = Embed(
                            description=f"{config.EMOJIS.CONFIG.APPROVE} Vanity /{before.vanity_url_code} has been dropped and is now available",
                            color=self.bot.color,
                        )
                        await channel.send(embed=embed)

    @group(name="vanity", description="manage guild", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def vanity(self, ctx: Context):
        """
        Vanity module within greed allows you to track vanities that are avaliable.
        """
        return await ctx.send_help(ctx.command)

    @vanity.command(
        name="set", description="manage guild", usage="<channel>", brief="#vanity-logs"
    )
    @has_permissions(manage_guild=True)
    async def vanityset(self, ctx: Context, channel: TextChannel):
        """
        Sets the channel for vanity changes
        """
        guild_id = ctx.guild.id
        if channel.guild.id != guild_id:
            await ctx.warn("Please mention a channel within this server.")
            return
        records = await self.bot.db.fetch(
            """SELECT channel_id FROM vanity_channels WHERE guild_id = $1""", guild_id
        )
        vanity_channels = [record["channel_id"] for record in records]
        if channel.id in vanity_channels:
            await ctx.warn("Vanity logging is already enabled for this channel.")
        else:
            await self.bot.db.execute(
                """INSERT INTO vanity_channels (guild_id, channel_id) 
                                     VALUES ($1, $2) 
                                     ON CONFLICT DO NOTHING""",
                guild_id,
                channel.id,
            )
            await ctx.approve(f"Vanity logging enabled for #{channel.name}.")

    @vanity.command(
        name="unset",
        description="manage guild",
        usage="<channel>",
        brief="#vanity-logs",
    )
    @has_permissions(manage_guild=True)
    async def vanityunset(self, ctx: Context, channel: TextChannel):
        """
        Removes the channel from vanity logging

        """
        guild_id = ctx.guild.id
        if channel.guild.id != guild_id:
            await ctx.warn("Please mention a channel within this server.")
            return
        records = await self.bot.db.fetch(
            """SELECT channel_id FROM vanity_channels WHERE guild_id = $1""", guild_id
        )
        vanity_channels = [record["channel_id"] for record in records]
        if channel.id not in vanity_channels:
            await ctx.warn("Vanity logging is not enabled for this channel.")
        else:
            await self.bot.db.execute(
                """DELETE FROM vanity_channels 
                                     WHERE guild_id = $1 AND channel_id = $2""",
                guild_id,
                channel.id,
            )
            await ctx.approve(f"Vanity logging has been disabled for #{channel.name}.")


#     def get_status(self, member: Member) -> str:
#         """
#         Get the status of the member.
#         """
#         custom_activity = find(lambda activity: isinstance(activity, CustomActivity), member.activities)
#         return str(custom_activity).lower() if custom_activity else ""

#     @Cog.listener("on_presence_update")
#     async def vanity_listener(self, before: Member, member: Member):
#         """
#         Listener for awarding members for advertising the server.
#         """
#         guild = member.guild
#         vanity = guild.vanity_url_code
#         if not vanity:
#             return

#         record = await self.bot.db.fetchrow("SELECT * FROM vanity WHERE guild_id = $1", guild.id)
#         if not record:
#             return

#         role = guild.get_role(record["role_id"])
#         if not role or not role.is_assignable():
#             return

#         before_status = self.get_status(before)
#         status = self.get_status(member)
#         if before_status == status:
#             return

#         with suppress(HTTPException):
#             if vanity not in status and role in member.roles:
#                 await member.remove_roles(role, reason="Vanity no longer in status")
#             elif vanity in status and role not in member.roles:
#                 await member.add_roles(role, reason="Vanity added to status")

#                 if (
#                     before.status != Status.offline
#                     and before.status == member.status
#                     and (channel := cast(TextChannel, guild.get_channel(record["channel_id"])))
#                     and not await self.bot.redis.ratelimited(f"vanity:{guild.id}:{member.id}", limit=1, timespan=6 * 3600)
#                 ):
#                     script = Script(
#                         (record["template"] or "{title: vanity set}{description: thank you {user.mention}}{footer: put /{vanity} in your status for the {role} role.}").replace("{vanity}", vanity),
#                         [guild, member, role],
#                     )

#                     try:
#                         await script.send(channel)
#                     except HTTPException:
#                         await self.bot.db.execute("UPDATE vanity SET template = NULL WHERE guild_id = $1", guild.id)

#     @group(aliases=["vr"], invoke_without_command=True)
#     @has_permissions(manage_roles=True)
#     @check(lambda ctx: bool(ctx.guild and ctx.guild.vanity_url_code))
#     async def vanity(self, ctx: Context) -> Message:
#         """
#         Award members for advertising your server.
#         """
#         return await ctx.send_help(ctx.command)

#     @vanity.command(name="role", description="manage roles", usage="<role>")
#     @has_permissions(manage_roles=True)
#     @check(lambda ctx: bool(ctx.guild and ctx.guild.vanity_url_code))
#     async def vanity_role(self, ctx: Context, *, role: Annotated[Role, StrictRole(check_dangerous=True)]) -> Message:
#         """
#         Set the role to award members.
#         """
#         await self.bot.db.execute(
#             """
#             INSERT INTO vanity (guild_id, role_id)
#             VALUES ($1, $2)
#             ON CONFLICT (guild_id)
#             DO UPDATE SET role_id = EXCLUDED.role_id
#             """,
#             ctx.guild.id,
#             role.id,
#         )
#         return await ctx.approve(f"Now granting {role.mention} to advertisers")

#     @vanity.group(name="channel", aliases=["logs"], description="manage roles", invoke_without_command=True)
#     @has_permissions(manage_roles=True)
#     @check(lambda ctx: bool(ctx.guild and ctx.guild.vanity_url_code))
#     async def vanity_channel(self, ctx: Context, *, channel: TextChannel) -> Message:
#         """
#         Set the channel to send award logs.
#         """
#         await self.bot.db.execute(
#             """
#             INSERT INTO vanity (guild_id, channel_id)
#             VALUES ($1, $2)
#             ON CONFLICT (guild_id)
#             DO UPDATE SET channel_id = EXCLUDED.channel_id
#             """,
#             ctx.guild.id,
#             channel.id,
#         )
#         return await ctx.approve(f"Now sending award logs to {channel.mention}")

#     @vanity_channel.command(name="remove", aliases=["delete", "del", "rm"], description="manage roles")
#     @has_permissions(manage_roles=True)
#     @check(lambda ctx: bool(ctx.guild and ctx.guild.vanity_url_code))
#     async def vanity_channel_remove(self, ctx: Context) -> Message:
#         """
#         Remove award logs channel.
#         """
#         await self.bot.db.execute("UPDATE vanity SET channel_id = NULL WHERE guild_id = $1", ctx.guild.id)
#         return await ctx.approve("No longer sending award logs")

#     @vanity.command(name="message", aliases=["msg"], description="manage roles", usage="<script>", brief="Thank you for repping!")
#     @has_permissions(manage_roles=True)
#     @check(lambda ctx: bool(ctx.guild and ctx.guild.vanity_url_code))
#     async def vanity_message(self, ctx: Context, *, script: Script) -> Message:
#         """
#         Set the award message.

#         Available variables:
#         > `{role}`: The award role.
#         > `{vanity}`: The vanity code.
#         """
#         await self.bot.db.execute(
#             """
#             INSERT INTO vanity (guild_id, template)
#             VALUES ($1, $2)
#             ON CONFLICT (guild_id)
#             DO UPDATE SET template = EXCLUDED.template
#             """,
#             ctx.guild.id,
#             script.template,
#         )
#         return await ctx.approve(f"Successfully set {vowel(script.format)} award message")

#     @vanity.command(name="disable", aliases=["reset"], description="manage roles")
#     @has_permissions(manage_roles=True)
#     @check(lambda ctx: bool(ctx.guild and ctx.guild.vanity_url_code))
#     async def vanity_disable(self, ctx: Context) -> Message:
#         """
#         Reset and disable the award system.
#         """
#         await ctx.prompt("Are you sure you completely reset the vanity award system?")
#         await self.bot.db.execute("DELETE FROM vanity WHERE guild_id = $1", ctx.guild.id)
#         return await ctx.approve("No longer awarding members for advertising your server")
