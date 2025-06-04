import discord
from discord.ext import commands
from managers.bot import Luma
from managers.helpers import Context
from managers.validators import NoStaff


class Donor(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot

    @commands.command(aliases=["me", "sc"])
    @commands.donor_perk()
    async def selfpurge(self: "Donor", ctx: Context, *, amount: int = 100):
        """
        Purge messages sent by you
        """
        return await ctx.channel.purge(
            limit=amount + 1,
            check=lambda m: m.author.id == ctx.author.id and not m.pinned,
            bulk=True,
        )

    @commands.command(aliases=["fn", "nicklock"])
    @commands.has_guild_permissions(manane_nicknames=True)
    @commands.bot_has_guild_permissions(manage_nicknames=True)
    async def forcenick(self: "Donor", ctx: Context, member: NoStaff, *, nick: str):
        """
        Force nick a member nickname
        """
        if nick.lower() == "none":
            if await self.bot.db.fetchrow(
                "SELECT * FROM forcenick WHERE guild_id = $1 AND user_id = $2",
                ctx.guild.id,
                member.id,
            ):
                await self.bot.db.execute(
                    "DELETE FROM forcenick WHERE guild_id = $1 AND user_id = $2",
                    ctx.guild.id,
                    member.id,
                )

                await member.edit(nick=None, reason="Removed force nickname")
                return await ctx.confirm(f"Removed {member.mention}'s force nick name")

        await self.bot.db.execute(
            """
      INSERT INTO forcenick VALUES ($1,$2,$3)
      ON CONFLICT (guild_id, user_id) DO UPDATE
      SET nickname = $3""",
            ctx.guild.id,
            member.id,
            nick,
        )

        await member.edit(nick=nick, reason="This member has been force nicknamed")
        await ctx.confirm(f"Added **{nick}** as {member.mention}'s force nickname")

    @commands.group(invoke_without_command=True)
    async def reskin(self: "Donor", ctx: Context):
        """
        Commands for reskin
        """
        return await ctx.send_help(ctx.command)

    @reskin.command(name="name")
    @commands.donor_perk()
    async def reskin_name(self: "Donor", ctx: Context, *, name: str):
        """
        Edit ur reskin name
        """
        if name.lower() == "none":
            name = None

        await self.bot.db.execute(
            """
      INSERT INTO reskin (user_id, username) VALUES ($1,$2)
      ON CONFLICT (user_id) DO UPDATE
      SET username = $2""",
            ctx.author.id,
            name,
        )
        await ctx.confirm(f"Reskin name changed to `{name or self.bot.user.name}`")

    @reskin.command(name="avatar", aliases=["pfp", "av"])
    @commands.donor_perk()
    async def reskin_avatar(
        self: "Donor", ctx: Context, *, attachment: discord.Attachment
    ):
        """
        Edit ur reskin avatar
        """
        if not attachment.content_type.startswith("image"):
            return await ctx.error("This is not an image")

        await self.bot.db.execute(
            """
      INSERT INTO reskin (user_id, avatar_url) VALUES ($1,$2)
      ON CONFLICT (user_id) DO UPDATE
      SET avatar_url = $2""",
            ctx.author.id,
            attachment.url,
        )
        await ctx.confirm("Reskin avatar updated")

    @reskin.command(name="copy")
    @commands.donor_perk()
    async def reskin_copy(self: "Donor", ctx: Context, *, member: discord.User):
        """
        Copye someones reskin
        """
        check = await self.bot.db.fetchrow(
            "SELECT username, avatar_url FROM reskin WHERE user_id = $1", member.id
        )
        if not check:
            return await ctx.error("This user doesnt have a reskin")

        await self.bot.db.execute(
            """
      INSERT INTO reskin VALUES ($1,$2,$3)
      ON CONFLICT (user_id) DO UPDATE
      SET username = $2, avatar_url = $3""",
            ctx.author,
            *check,
        )
        await ctx.confirm(f"Copied {member.mention}'s reskin")

    @reskin.command(name="delete")
    @commands.donor_perk()
    async def reskin_delete(self: "Donor", ctx: Context):
        """
        Remove ur reskin
        """
        if not await self.bot.db.fetchrow(
            "SELECT * FROM reskin WHERE user_id = $1", ctx.author.id
        ):
            return await ctx.error("You dont have reskin")

        await self.bot.db.execute(
            "DELETE FROM reskin WHERE user_id = $1", ctx.author.id
        )
        await ctx.confirm("Removed ur reskin")


async def setup(bot: Luma):
    return await bot.add_cog(Donor(bot))
