import discord
from discord.ext import commands
from utils.embed import Embed
from utils.permissions import Permissions
from utils.utils import GoodRole


class vanity(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def vanity(self, ctx: commands.Context):
        return await ctx.create_pages()

    @vanity.command(
        name="remove",
        description="remove the vanity module",
        help="vanity",
        brief="manage guild",
    )
    @Permissions.has_permission(manage_guild=True)
    async def vanity_remove(self, ctx: commands.Context):
        vanity = await self.bot.db.fetchrow(
            "SELECT vanity_string FROM vanity WHERE guild_id = $1", ctx.guild.id
        )
        if not vanity:
            return await ctx.send_warning(
                f"no vanity has been **set**, to set a vanity use `{ctx.clean_prefix}vanity set`"
            )

        await self.bot.db.execute(
            "DELETE FROM vanity WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.send_success("removed **vanity string**.")

    @vanity.command(
        name="set",
        description="set the vanity module",
        help="vanity",
        usage="[url] [role] [channel]",
        brief="manage guild",
    )
    @Permissions.has_permission(manage_guild=True)
    async def vanity_set(
        self,
        ctx: commands.Context,
        vanity: str = None,
        role: GoodRole = None,
        channel: discord.TextChannel = None,
    ):

        if vanity == None:
            return await ctx.send_warning(
                "please specify a **vanity string** and **role** and **channel**."
            )
        if role == None:
            return await ctx.send_warning(
                "please specify a **vanity string** and **role** and **channel**."
            )
        if channel == None:
            return await ctx.send_warning(
                "please specify a **vanity string** and **role** and **channel**."
            )

        vanityCheck = await self.bot.db.fetchrow(
            "SELECT vanity_string FROM vanity WHERE guild_id = $1", ctx.guild.id
        )
        if vanityCheck:
            return await ctx.send_warning(
                f"**vanity** already set to `{vanityCheck['vanity_string']}`. To remove this use `{ctx.clean_prefix}vanity remove`"
            )

        await self.bot.db.execute(
            "INSERT INTO vanity_channel VALUES ($1, $2)", ctx.guild.id, channel.id
        )
        await self.bot.db.execute(
            "INSERT INTO vanity VALUES ($1, $2, $3, $4)",
            ctx.guild.id,
            "{embed}$v{description: Thanks {user.mention} for having {vanity} in your status.\nI rewarded you with {role.mention}.}",
            vanity,
            role.id,
        )
        await ctx.send_success(
            f"set **vanity url** to **{vanity}** and **role** to {role.mention} and **channel** to {channel.mention}."
        )

    @vanity.command(
        name="channel",
        description="change vanity notification channel",
        help="vanity",
        usage="[channel]",
        brief="manage guild",
    )
    @Permissions.has_permission(manage_guild=True)
    async def vanity_channel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):

        if channel == None:
            return await ctx.send_warning("please specify a **vanity channel**")

        vanityChannel = await self.bot.db.fetchrow(
            "SELECT * FROM vanity_channel WHERE guild_id = $1", ctx.guild.id
        )
        if vanityChannel:
            await self.bot.db.execute(
                "UPDATE vanity_channel SET channel = $1 WHERE guild_id = $2",
                channel.id,
                ctx.guild.id,
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO vanity_channel VALUES ($1, $2)", ctx.guild.id, channel.id
            )

        return await ctx.send_success(f"set **vanity channel** to {channel.mention}")

    @vanity.command(
        name="string",
        description="change vanity string",
        help="vanity",
        usage="[vanity string]",
        brief="manage guild",
    )
    @Permissions.has_permission(manage_guild=True)
    async def vanity_string(self, ctx: commands.Context, vanity: str):

        if vanity == None:
            return await ctx.send_warning("please specify a **vanity string**")

        vanityString = await self.bot.db.fetchrow(
            "SELECT * FROM vanity WHERE guild_id = $1", ctx.guild.id
        )
        if vanityString:
            await self.bot.db.execute(
                "UPDATE vanity SET guild_id = $1 WHERE vanity = $2",
                ctx.guild.id,
                vanity,
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO vanity VALUES ($1, $2)", ctx.guild.id, vanity
            )

        return await ctx.send_success(f"set **vanity string** to **{vanity}**.")

    @vanity.command(
        name="role",
        description="change vanity reward role",
        help="vanity",
        usage="[role]",
        brief="manage guild",
    )
    @Permissions.has_permission(manage_guild=True)
    async def vanity_role(self, ctx: commands.Context, role: GoodRole = None):
        if role == None:
            return await ctx.send_warning("please specify a **vanity role**")

        vanityRole = await self.bot.db.fetchrow(
            "SELECT * FROM vanity WHERE guild_id = $1", ctx.guild.id
        )
        if vanityRole:
            await self.bot.db.execute(
                "UPDATE vanity SET role_id = $1 WHERE guild_id = $2",
                role.id,
                ctx.guild.id,
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO vanity VALUES ($1, $2)", ctx.guild.id, role.id
            )

        return await ctx.send_success(f"set **vanity role** to {role.mention}")

    @vanity.command(
        name="message",
        description="set vanity channel message",
        usage="[message]",
        brief="manage guild",
    )
    async def vanity_message(self, ctx: commands.Context, *, message: str = None):
        if message == None:
            return await ctx.send_warning("please specify a **vanity message**")
        vanityCheck = await self.bot.db.fetchrow(
            "SELECT vanity_string FROM vanity WHERE guild_id = $1", ctx.guild.id
        )

        if not vanityCheck:
            return await ctx.send_warning(
                f"please set a **vanity string** using `{ctx.clean_prefix}vanity set [string] [role]` before using this"
            )

        await self.bot.db.execute(
            "UPDATE vanity SET vanity_message = $1 WHERE guild_id = $2",
            message,
            ctx.guild.id,
        )
        return await ctx.send_success(f"set **vanity message** to\n ```{message}```")

    @vanity.command(
        name="variables", help="vanity", description="check vanity variables"
    )
    async def vanity_variables(self, ctx: commands.Context):
        await ctx.invoke(self.bot.get_command("embed variables"))

    @commands.Cog.listener("on_presence_update")
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if after.bot:
            return

        vanityCheck = await self.bot.db.fetchrow(
            "SELECT vanity_string FROM vanity WHERE guild_id = $1", after.guild.id
        )
        if not vanityCheck:
            return

        vanity = await self.bot.db.fetchrow(
            "SELECT * FROM vanity WHERE guild_id = $1", after.guild.id
        )
        vanityChannel = await self.bot.db.fetchrow(
            "SELECT * FROM vanity_channel WHERE guild_id = $1", after.guild.id
        )
        vanityUser = await self.bot.db.fetchrow(
            "SELECT * FROM vanity_users WHERE guild_id = $1 AND user_id = $2",
            after.guild.id,
            after.id,
        )

        if vanityUser and (
            after.status is discord.Status.offline
            or after.status is discord.Status.invisible
        ):
            try:
                return await after.remove_roles(
                    after.guild.get_role(vanity["role_id"]),
                    reason="resent vanity: user removed vanity from status",
                )
            except discord.Forbidden:
                return
        if (
            vanityUser
            and (
                before.status is discord.Status.offline
                or before.status is discord.Status.invisible
            )
            and after.activity is None
        ):
            return
        if (
            vanityUser
            and (
                after.status is not discord.Status.offline
                or after.status is not discord.Status.invisible
            )
            and (
                after.activity is None
                or vanity["vanity_string"] not in after.activity.name
            )
        ):
            try:
                return await after.remove_roles(
                    after.guild.get_role(vanity["role_id"]),
                    reason="resent vanity: user removed vanity from status",
                )
            except discord.Forbidden:
                return

        if after.activity is None:
            return

        if vanity["vanity_string"] in after.activity.name:
            role = after.guild.get_role(vanity["role_id"])
        try:
            await after.add_roles(
                role, reason=f"resent vanity: {after} had vanity in status"
            )
        except:
            return

        if not vanityChannel or vanityUser:
            return

        if not vanityUser:
            await self.bot.db.execute(
                "INSERT INTO vanity_users VALUES ($1, $2)", after.guild.id, after.id
            )

        embed = Embed.from_variable(
            vanity["vanity_message"]
            .replace("{role.mention}", role.mention)
            .replace("{vanity}", vanity["vanity_string"]),
            after,
            after,
        )

        channel = after.guild.get_channel(vanityChannel["channel"])
        try:
            return await channel.send(content=embed.content, embed=embed.to_embed())
        except:
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(vanity(bot))
