import asyncio
from collections import defaultdict
from typing import Optional

import aiohttp
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from loguru import logger
from rival_tools import lock, ratelimit
from tools.important.subclasses.command import Role, TextChannel
from tools.important.subclasses.parser import Script


class EmbedConverter(commands.Converter):
    async def convert(self, ctx: Context, code: str):
        try:
            s = Script(code, ctx.author)
            await s.compile()
        except Exception as e:
            raise e
        return code


class Vanity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.local_addr = ("23.160.168.196", 0)
        self.helper = discord.ExpiringDictionary()
        self.locks = defaultdict(asyncio.Lock)

    async def cog_load(self):
        await self.bot.db.execute(
            """CREATE TABLE IF NOT EXISTS vanity_roles (guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL, PRIMARY KEY(guild_id, user_id))"""
        )
        logger.info("Now starting the check vanity loop...")
        self.check_vanity.start()
        logger.info("Started the check vanity loop!")

    async def cog_unload(self):
        logger.info("Now stopping the check vanity loop...")
        self.check_vanity.stop()
        logger.info("Stopped the check vanity loop!")

    def activity(self, member: discord.Member):
        if member.activity:
            if member.activity.name is not None:
                return member.activity.name
            else:
                return ""
        return ""

    async def get_vanity_role(
        self, guild: discord.Guild, role_id: Optional[int] = None
    ) -> Optional[discord.Role]:
        if role_id is None:
            if role_id := await self.bot.db.fetchval(
                """SELECT role_id FROM vanity_status WHERE guild_id = $1""", guild.id
            ):
                role_id = role_id
        if role := guild.get_role(int(role_id)):
            return role
        return None

    # @ratelimit("award_message:{member.id}:{member.guild.id}", 1, 600, False)
    async def award_message(self, member: discord.Member):
        data = await self.bot.db.fetchrow(
            """SELECT channel_id, message FROM vanity_status WHERE guild_id = $1""",
            member.guild.id,
        )
        if not data:
            return
        channel = self.bot.get_channel(data["channel_id"])
        if not channel:
            return
        if not data.message:
            return
        return await self.bot.send_embed(channel, data.message, user=member)

    # @ratelimit("vanity:{member.guild.id}", 5, 5, True)
    async def assign_vanity_role(self, member: discord.Member, role: discord.Role):
        guild = member.guild
        if role in member.roles:
            return
        await self.bot.db.execute(
            """INSERT INTO vanity_roles (guild_id, user_id) VALUES($1, $2) ON CONFLICT(guild_id, user_id) DO NOTHING""",
            guild.id,
            member.id,
        )
        return await member.add_roles(role, local_addr=self.local_addr)

    # @ratelimit("vanity:{member.guild.id}", 5, 5, True)
    async def remove_vanity_role(self, member: discord.Member, role: discord.Role):
        await self.bot.db.execute(
            """DELETE FROM vanity_roles WHERE guild_id = $1 AND user_id = $2""",
            member.guild.id,
            member.id,
        )
        guild = member.guild
        if role not in member.roles:
            return
        return await member.remove_roles(role, local_addr=self.local_addr)

    async def check_status(self, member: discord.Member, role: Optional[int] = None):
        if member.guild.vanity_url_code:
            vanity = f"/{str(member.guild.vanity_url_code)}"
            if member.status != discord.Status.offline:
                if vanity in self.activity(member):
                    if role := await self.get_vanity_role(member.guild, role):
                        if role in member.roles:
                            pass
                        else:
                            await self.assign_vanity_role(member, role)
                            return await self.award_message(member)
                else:
                    if role := await self.get_vanity_role(member.guild):
                        if role in member.roles:
                            if not await self.bot.db.fetchrow(
                                """SELECT * FROM vanity_roles WHERE guild_id = $1 AND user_id = $2""",
                                member.guild.id,
                                member.id,
                            ):
                                return
                            return await self.remove_vanity_role(member, role)

    @tasks.loop(seconds=5)
    async def check_vanity(self):
        for guild_id, role_id in await self.bot.db.fetch(
            """SELECT guild_id, role_id FROM vanity_status"""
        ):
            if guild := self.bot.get_guild(int(guild_id)):
                await asyncio.gather(
                    *[self.check_status(member, role_id) for member in guild.members]
                )

    @commands.group(
        name="vanity",
        brief="reward users with a role for repping the vanity",
        example=",vanity",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_roles=True)
    async def vanity(self, ctx: Context):
        return await ctx.send_help(ctx.command.qualified_name)

    @vanity.command(
        name="role", brief="set the reward role", example=",vanity role @pic"
    )
    @commands.has_permissions(manage_roles=True)
    async def vanity_role(self, ctx: Context, *, role: Role):
        if not ctx.guild.vanity_url_code:
            return await ctx.fail("Guild does **not have a vanity**")
        role = role[0]
        await self.bot.db.execute(
            """INSERT INTO vanity_status (guild_id, role_id) VALUES($1, $2) ON CONFLICT (guild_id) DO UPDATE SET role_id = excluded.role_id""",
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(
            f"Users with the **vanity set** will recieve {role.mention} role"
        )

    @vanity.group(
        name="award",
        brief="add a message into a channel upon someone repping",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_roles=True)
    async def vanity_award(self, ctx: Context):
        return await ctx.send_help(ctx.command.qualified_name)

    @vanity_award.command(
        name="message",
        brief="set the message",
        example=",vanity award message {embed}{description: thanks for repping {user.mention}}",
    )
    @commands.has_permissions(manage_roles=True)
    async def vanity_award_message(self, ctx: Context, *, message: EmbedConverter):
        try:
            await self.bot.db.execute(
                """UPDATE vanity_status SET message = $2 WHERE guild_id = $1""",
                ctx.guild.id,
                message,
            )
        except:
            return await ctx.fail(
                f"**Vanity role needs to be set** with `{ctx.prefix}vanity role`"
            )
        return await ctx.success("**Vanity Award message** has been set")

    @vanity_award.command(
        name="channel",
        brief="set the award message channel",
        example="vanity award channel #text",
    )
    @commands.has_permissions(manage_roles=True)
    async def vanity_award_channel(self, ctx: Context, *, channel: TextChannel):
        try:
            await self.bot.db.execute(
                """UPDATE vanity_status SET channel_id = $2 WHERE guild_id = $1""",
                ctx.guild.id,
                channel.id,
            )
        except:
            return await ctx.fail(
                f"**Vanity role needs to be set** with `{ctx.prefix}vanity role`"
            )
        return await ctx.success(f"**Vanity award channel** to {channel.mention}")

    @vanity.command(
        name="view",
        aliases=["config", "cfg", "settings"],
        brief="view your vanity status settings",
    )
    @commands.has_permissions(manage_roles=True)
    async def vanity_view(self, ctx: Context):
        data = await self.bot.db.fetchrow(
            """SELECT role_id, channel_id, message FROM vanity_status WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if not data:
            return await ctx.fail("**vanity status reward** is **not setup**")
        desc = ""
        if role := ctx.guild.get_role(data["role_id"]):
            desc += f"> **Role:** {role.mention}\n"
        if channel := ctx.guild.get_channel(data["channel_id"]):
            desc += f"> **Channel:** {channel.mention}\n"
        if message := data["message"]:
            desc += f"> **Message:** `{message}`\n"
        embed = discord.Embed(
            title="vanity status config", color=self.bot.color, description=desc
        )
        return await ctx.send(embed=embed)

    @vanity.command(name="reset", brief="reset the vanity reward role")
    @commands.has_permissions(manage_roles=True)
    async def vanity_reset(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM vanity_status WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("reset the vanity status configuration")


async def setup(bot):
    return await bot.add_cog(Vanity(bot))
