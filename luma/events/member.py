import discord
from discord.ext import commands
from managers.bot import Luma


class Member(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot

    @commands.Cog.listener("on_member_update")
    async def on_forcenick(
        self: "Member", before: discord.Member, after: discord.Member
    ):
        if str(before.nick) != str(after.nick):
            if nickname := await self.bot.db.fetchval(
                "SELECT nickname FROM forcenick WHERE guild_id = $1 AND user_id = $2",
                before.guild.id,
                before.id,
            ):
                if after.nick != nickname:
                    await after.edit(
                        nick=nickname,
                        reason=f"Force nickname has been used on this member",
                    )

    @commands.Cog.listener("on_member_join")
    async def autorole(self: "Member", member: discord.Member):
        result = await self.bot.db.fetchrow(
            "SELECT * FROM autorole WHERE guild_id = $1", member.guild.id
        )
        if result:
            role = member.guild.get_role(result["role_id"])
            if role:
                if role.is_assignable():
                    await member.add_roles(role, reason="autorole")

    @commands.Cog.listener("on_member_join")
    async def on_poj(self: "Member", member: discord.Member):
        result = await self.bot.db.fetchrow(
            "SELECT * FROM pingonjoin WHERE guild_id = $1", member.guild.id
        )
        if result:
            channel = member.guild.get_channel(result["channel_id"])
            if channel:
                await channel.send(member.mention, delete_after=6)

    @commands.Cog.listener("on_member_join")
    async def on_welcome(self: "Member", member: discord.Member):
        results = await self.bot.db.fetch(
            "SELECT * FROM welcome WHERE guild_id = $1", member.guild.id
        )
        for result in results:
            channel = member.guild.get_channel(result["channel_id"])
            if channel:
                x = await self.bot.embed.convert(member, result["message"])
                await channel.send(**x)

    @commands.Cog.listener("on_member_remove")
    async def on_leave(self: "Member", member: discord.Member):
        results = await self.bot.db.fetch(
            "SELECT * FROM leave WHERE guild_id = $1", member.guild.id
        )
        for result in results:
            channel = member.guild.get_channel(result["channel_id"])
            if channel:
                x = await self.bot.embed.convert(member, result["message"])
                await channel.send(**x)


async def setup(bot: Luma):
    return await bot.add_cog(Member(bot))
