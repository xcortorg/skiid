import asyncio
import math

import discord
from discord.ext import commands
from utils.permissions import Permissions


def get_progress(xp, level):
    corner_black_left = "<:blue_left_rounded:1209439340585943093>"
    black = "<:blue:1209439373947576370>"
    corner_black_right = "<:blue_right_rounded:1209439404980969473>"
    corner_white_left = "<:white_left_rounded:1209439872188944424>"
    white = "<:white:1209439850957381632>"
    corner_white_right = "<:white_right_rounded:1209439893516845117>"
    xp_end = math.floor(5 * math.sqrt(level) + 50 * level + 30)
    percentage = xp / xp_end * 100
    if percentage < 10:
        rest = ""
        for _ in range(8):
            rest = rest + black
        return corner_black_left + rest + corner_black_right
    elif percentage > 10 and percentage < 20:
        return (
            corner_white_left
            + white
            + black
            + black
            + black
            + black
            + black
            + black
            + black
            + corner_black_right
        )
    elif percentage > 20 and percentage < 30:
        rest = ""
        rest2 = ""
        for _ in range(6):
            rest = rest + black
        for _ in range(2):
            rest2 = rest2 + white

        return corner_white_left + rest2 + rest + corner_black_right
    elif percentage > 30 and percentage < 40:
        rest = ""
        rest2 = ""
        for _ in range(5):
            rest = rest + black
        for _ in range(3):
            rest2 = rest2 + white

        return corner_white_left + rest2 + rest + corner_black_right
    elif percentage > 40 and percentage < 50:
        rest = ""
        rest2 = ""
        for _ in range(4):
            rest = rest + black
        for _ in range(4):
            rest2 = rest2 + white

        return corner_white_left + rest2 + rest + corner_black_right
    elif percentage > 50 and percentage < 60:
        rest = ""
        rest2 = ""
        for _ in range(3):
            rest = rest + black
        for _ in range(5):
            rest2 = rest2 + white

        return corner_white_left + rest2 + rest + corner_black_right
    elif percentage > 60 and percentage < 70:
        rest = ""
        rest2 = ""
        for _ in range(2):
            rest = rest + black
        for _ in range(6):
            rest2 = rest2 + white

        return corner_white_left + rest2 + rest + corner_black_right
    elif percentage > 70 and percentage < 80:
        rest = ""
        for _ in range(7):
            rest = rest + white
        return corner_white_left + rest + black + corner_black_right
    elif percentage > 80 and percentage < 90:
        rest = ""
        for _ in range(8):
            rest = rest + white
        return corner_white_left + rest + corner_black_right
    elif percentage > 90:
        rest = ""
        for _ in range(8):
            rest = rest + white
        return corner_white_left + rest + corner_white_right
    return "N/A"


class leveling(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.member
        )

    @commands.command(
        description="check any members rank", help="config", usage="[member]"
    )
    async def rank(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        check = await self.bot.db.fetchrow(
            "SELECT * FROM levelsetup WHERE guild_id = {}".format(ctx.guild.id)
        )
        if check is None:
            return await ctx.send_error("Levels aren't enabled in this server")
        che = await self.bot.db.fetchrow(
            "SELECT * FROM levels WHERE guild_id = {} AND author_id = {}".format(
                ctx.guild.id, member.id
            )
        )
        if che is None:
            return await ctx.reply(
                embed=discord.Embed(color=self.bot.color, title=f"{member.name}'s rank")
                .set_author(name=member, icon_url=member.display_avatar.url)
                .add_field(name="xp", value="**{}**".format("0"))
                .add_field(name="level", value="**{}**".format("0"))
                .add_field(name="progress (0%)", value=get_progress(0, 0), inline=False)
            )
        level = int(che["level"])
        xp = int(che["exp"])
        xp_end = math.floor(5 * math.sqrt(level) + 50 * level + 30)
        percentage = int(xp / xp_end * 100)
        return await ctx.reply(
            embed=discord.Embed(color=self.bot.color, title=f"{member.name}'s rank")
            .set_author(name=member, icon_url=member.display_avatar.url)
            .add_field(name="xp", value="**{}**".format(str(xp)))
            .add_field(name="level", value="**{}**".format(str(level)))
            .add_field(
                name="progress ({}%)".format(percentage),
                value=get_progress(xp, level),
                inline=False,
            )
        )

    @commands.group(invoke_without_command=True)
    async def level(self, ctx):
        await ctx.create_pages()

    @level.group(
        invoke_without_command=True,
        help="config",
        description="manage the rewards for each level",
    )
    async def rewards(self, ctx: commands.Context):
        await ctx.create_pages()

    @rewards.command(
        description="add a level reward",
        help="config",
        usage="[level] [role]",
        brief="manage guild",
    )
    @Permissions.has_permission(manage_guild=True)
    async def add(self, ctx: commands.Context, level: int, *, role: discord.Role):
        if self.bot.ext.is_dangerous(role):
            return await ctx.send_warning(
                "You cannot make a level role a role with dangerous permissions."
            )
        check = await self.bot.db.fetchrow(
            "SELECT level FROM levelroles WHERE guild_id = {} AND level = {}".format(
                ctx.guild.id, level
            )
        )
        if check is not None:
            return await ctx.send_warning(
                f"a role has been already assigned for level **{level}**"
            )
        await self.bot.db.execute(
            "INSERT INTO levelroles VALUES ($1,$2,$3)", ctx.guild.id, level, role.id
        )
        await ctx.send_success(f"added {role.mention} for level **{level}** reward")

    @rewards.command(
        description="remove a level reward",
        help="config",
        usage="[level]",
        brief="manage guild",
    )
    @Permissions.has_permission(manage_guild=True)
    async def remove(self, ctx: commands.Context, level: int = None):
        check = await self.bot.db.fetchrow(
            "SELECT level FROM levelroles WHERE guild_id = {} AND level = {}".format(
                ctx.guild.id, level
            )
        )
        if check is None:
            return await ctx.send_warning(
                f"there is no role assigned for level **{level}**"
            )
        await self.bot.db.execute(
            "DELETE FROM levelroles WHERE guild_id = $1 AND level = $2",
            (ctx.guild.id, level),
        )
        await ctx.send_success(f"Removed level **{level}** reward")

    @rewards.command(
        name="reset",
        description="reset all level rewards",
        help="config",
        brief="administrator",
    )
    @Permissions.has_permission(administrator=True)
    async def rewards_reset(self, ctx: commands.Context):
        results = await self.bot.db.fetch(
            "SELECT * FROM levelroles WHERE guild_id = {}".format(ctx.guild.id)
        )
        if len(results) == 0:
            return await ctx.send_error("there are no role rewards in this server")
        await self.bot.db.execute(
            "DELETE FROM levelroles WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.send_success("reset **all** level rewards")

    @rewards.command(description="return a list of role rewards", help="config")
    async def list(self, ctx: commands.Context):
        results = await self.bot.db.fetch(
            "SELECT * FROM levelroles WHERE guild_id = {}".format(ctx.guild.id)
        )
        if len(results) == 0:
            return await ctx.send_error("there are no role rewards in this server")

        def sortkey(e):
            return e[1]

        results.sort(key=sortkey)
        i = 0
        k = 1
        l = 0
        number = []
        messages = []
        num = 0
        auto = ""
        for table in results:
            level = table["level"]
            reward = table["role_id"]
            num += 1
            auto += f"\n`{num}` level **{level}** - {ctx.guild.get_role(reward).mention if ctx.guild.get_role(reward) else reward}"
            k += 1
            l += 1
            if l == 10:
                messages.append(auto)
                number.append(
                    discord.Embed(color=self.bot.color, description=auto).set_author(
                        name=f"level rewards", icon_url=ctx.guild.icon.url or None
                    )
                )
                i += 1
                auto = ""
                l = 0
        messages.append(auto)
        embed = discord.Embed(description=auto, color=self.bot.color)
        embed.set_author(name=f"level rewards", icon_url=ctx.guild.icon.url or None)
        number.append(embed)
        await ctx.paginator(number)

    @level.command(
        name="reset",
        description="reset levels for a member, leave blank for everyone",
        help="config",
        brief="administrator",
        usage="<member>",
    )
    @Permissions.has_permission(administrator=True)
    async def level_reset(
        self, ctx: commands.Context, *, member: discord.Member = None
    ):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM levelsetup WHERE guild_id = {}".format(ctx.guild.id)
        )
        if check is None:
            return await ctx.send_warning("levels are not configured")
        if not member:
            await self.bot.db.execute(
                "DELETE FROM levels WHERE guild_id = $1", ctx.guild.id
            )
            return await ctx.send_success("reset levels for **all** members")
        else:
            await self.bot.db.execute(
                "DELETE FROM levels WHERE guild_id = $1 AND author_id = $2",
                ctx.guild.id,
                member.id,
            )
            return await ctx.send_success(f"reset levels for **{member}**")

    @level.command(aliases=["lb"], description="check level leaderboard", help="config")
    async def leaderboard(self, ctx: commands.Context):
        await ctx.channel.typing()
        results = await self.bot.db.fetch(
            "SELECT * FROM levels WHERE guild_id = {}".format(ctx.guild.id)
        )
        if len(results) == 0:
            return await ctx.send_error("nobody is on the **level leaderboard**")

        def sortkey(e):
            return int(e[4])

        results.sort(key=sortkey, reverse=True)
        i = 0
        k = 1
        l = 0
        messages = []
        num = 0
        auto = ""
        for table in results:
            user = table["author_id"]
            exp = table["exp"]
            level = table["level"]
            num += 1
            auto += f"\n{'<a:crown:1021829752782323762>' if num == 1 else f'`{num}`'} **{await self.bot.fetch_user(user) or user}** - **{exp}** xp (level {level})"
            k += 1
            l += 1
            if l == 10:
                break
        messages.append(auto)
        embed = discord.Embed(description=auto, color=self.bot.color)
        embed.set_author(name=f"level leaderboard", icon_url=ctx.guild.icon.url or None)
        await ctx.send(embed=embed)

    @level.command(
        description="enable leveling system, or disable it",
        help="config",
        brief="manage guild",
    )
    @Permissions.has_permission(manage_guild=True)
    async def toggle(self, ctx: commands.Context):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM levelsetup WHERE guild_id = {}".format(ctx.guild.id)
        )
        if check is None:
            await self.bot.db.execute(
                "INSERT INTO levelsetup (guild_id) VALUES ($1)", ctx.guild.id
            )
            return await ctx.send_success("enabled leveling system")
        elif check is not None:
            await self.bot.db.execute(
                "DELETE FROM levelsetup WHERE guild_id = {}".format(ctx.guild.id)
            )
            return await ctx.send_success("disabled leveling system")

    @level.command(
        description="set where the level up message should be sent",
        help="config",
        usage="[destination]\ndestinations: channel, dms, off",
        brief="manage guild",
    )
    @Permissions.has_permission(manage_guild=True)
    async def levelup(self, ctx: commands.Context, destination: str):
        if not destination in ["dms", "channel", "off"]:
            return await ctx.send_warning("wrong destination passed")
        check = await self.bot.db.execute(
            "SELECT * FROM levelsetup WHERE guild_id = {}".format(ctx.guild.id)
        )
        if check is None:
            return await ctx.reply(
                "leveling system is not enabled", mention_author=False
            )
        await self.bot.db.execute(
            "UPDATE levelsetup SET destination = $1 WHERE guild_id = $2",
            destination,
            ctx.guild.id,
        )
        return await ctx.send_success(
            f"level up message destination: **{destination}**"
        )

    @level.command(
        description="set a channel to send level up messages",
        help="config",
        usage="[channel]",
        brief="manage guild",
    )
    @Permissions.has_permission(manage_guild=True)
    async def channel(self, ctx: commands.Context, *, channel: discord.TextChannel):
        check = await self.bot.db.fetch(
            "SELECT * FROM levelsetup WHERE guild_id = {}".format(ctx.guild.id)
        )
        if check is None:
            return await ctx.send_warning("leveling system is not enabled")
        if channel is None:
            await self.bot.db.execute(
                "UPDATE levelsetup SET channel_id = {} WHERE guild_id = {}".format(
                    None, ctx.guild.id
                )
            )
            return await ctx.send_success("removed the channel for leveling system")
        elif channel is not None:
            await self.bot.db.execute(
                "UPDATE levelsetup SET channel_id = {} WHERE guild_id = {}".format(
                    channel.id, ctx.guild.id
                )
            )
            await ctx.send_success(
                f"set the channel for leveling system to {channel.mention}"
            )


async def setup(bot):
    await bot.add_cog(leveling(bot))
