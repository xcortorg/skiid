import datetime
import re
from typing import Optional

import discord
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter
from managers.bot import Luma
from managers.helpers import Context


class Developer(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context):
        return await self.bot.is_owner(ctx.author)

    @commands.Cog.listener()
    async def on_guild_join(self: "Developer", guild: discord.Guild):
        if await self.bot.db.fetchrow(
            "SELECT * FROM blacklist WHERE id = $1 AND type = $2", guild.id, "guild"
        ):
            await guild.leave()

    @commands.command()
    async def pull(self: "Developer", ctx: Context):
        """
        Pull the latest update from github
        """
        await ctx.invoke(
            self.bot.get_command("jishaku shell"),
            argument=codeblock_converter("git pull"),
        )

    @commands.command(aliases=["py"])
    async def eval(self, ctx: Context, *, argument: codeblock_converter):
        """
        Run a python script
        """
        return await ctx.invoke(self.bot.get_command("jishaku py"), argument=argument)

    @commands.command(aliases=["sh"])
    async def shell(self: "Developer", ctx: Context, *, argument: codeblock_converter):
        """
        Run a shell script
        """
        return await ctx.invoke(
            self.bot.get_command("jishaku shell"), argument=argument
        )

    @commands.command(aliases=["servers"])
    async def guilds(self: "Developer", ctx: Context):
        """
        Get a list of the bots servers
        """
        servers = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        await ctx.paginate(
            [f"{g.name} - {g.member_count:,}" for g in servers], title="Luma servers"
        )

    @commands.group(invoke_without_command=True, aliases=["bl", "noyap"])
    async def blacklist(self: "Developer", ctx: Context):
        """
        Allow the bot owners to blacklist
        """
        return await ctx.send_help(ctx.command)

    @blacklist.command(name="user")
    async def blacklist_user(self: "Developer", ctx: Context, *, member: discord.User):
        """
        Blacklist an user from using this bot
        """
        if member.id in self.bot.owner_ids:
            return await ctx.error("You cant blacklist a bot owner")

        try:
            await self.bot.db.execute(
                "INSERT INTO blacklist VALUES ($1,$2)", member.id, "user"
            )
            return await ctx.confirm("This guy got no yapping for life")
        except:
            await self.bot.db.execute("DELETE FROM blacklist WHERE id = $1", member.id)
            return await ctx.confirm("This guy got lucky and can yap again")

    @blacklist.command(name="guild")
    async def blacklist_guild(self: "Developer", ctx: Context, *, gid: int):
        """
        Stop a whole server yapping
        """
        if gid in [1262401468875411547]:
            return await ctx.error("You cant blacklist this server")

        try:
            await self.bot.db.execute(
                "INSERT INTO blacklist VALUES ($1,$2)", gid, "guild"
            )
            guild = self.bot.get_guild(gid)
            if guild:
                await guild.leave()
            return await ctx.confirm("Blacklisted this server yapping")
        except:
            await self.bot.db.execute("DELETE FROM blacklist WHERE id = $1", gid)
            return await ctx.confirm("This server can yap again")

    @commands.group(invoke_without_command=True)
    async def edit(self: "Developer", ctx: Context):
        """
        Edit the bots appearance
        """
        return await ctx.send_help(ctx.command)

    @edit.command(name="avatar", aliases=["pfp"])
    async def edit_avatar(self: "Developer", ctx: Context, image: Optional[str] = None):
        """
        Change the bot's avatar
        """

        if image:
            if image.lower() == "none":
                await self.bot.user.edit(avatar=None)
                return await ctx.confirm("Removed the bot's banner")

            if re.search(
                r"(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])",
                image,
            ):
                buffer = await self.bot.session.get(image)

                if isinstance(buffer, bytes):
                    await self.bot.user.edit(avatar=buffer)
                    return await ctx.confirm("Edited the bot's banner")

            return await ctx.error("This is not a valid image")

        img = next(iter(ctx.message.attachments))
        await self.bot.user.edit(avatar=await img.read())
        return await ctx.confirm("Edited the bot's banner")

    @edit.command(name="banner")
    async def edit_banner(self: "Developer", ctx: Context, image: Optional[str] = None):
        """
        Change the bot's banner
        """

        if image:
            if image.lower() == "none":
                await self.bot.user.edit(banner=None)
                return await ctx.confirm("Removed the bot's banner")

            if re.search(
                r"(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])",
                image,
            ):
                buffer = await self.bot.session.get(image)

                if isinstance(buffer, bytes):
                    await self.bot.user.edit(banner=buffer)
                    return await ctx.confirm("Edited the bot's banner")

            return await ctx.error("This is not a valid image")

        img = next(iter(ctx.message.attachments))
        await self.bot.user.edit(banner=await img.read())
        return await ctx.confirm("Edited the bot's banner")

    @commands.group(invoke_without_command=True)
    async def donor(self: "Developer", ctx: Context):
        """
        Give donor to someone
        """
        return await ctx.send_help(ctx.command)

    @donor.command(name="add")
    async def donor_add(
        self: "Developer", ctx: Context, member: discord.Member, *, reason: str
    ):
        """
        Give donor perks to a member
        """
        if await self.bot.db.fetchrow(
            "SELECT * FROM donor WHERE user_id = $1", member.id
        ):
            return await ctx.error("This member is already a donor")

        await self.bot.db.execute(
            "INSERT INTO donor VALUES ($1,$2,$3)",
            member.id,
            datetime.datetime.now().timestamp(),
            reason,
        )
        await ctx.confirm(f"{member.mention} is now a donor. enjoy")

    @donor.command(name="remove")
    async def donor_remove(self: "Developer", ctx: Context, *, member: discord.Member):
        """
        Delete someones donor
        """
        if not await self.bot.db.fetchrow(
            "SELECT * FROM donor WHERE user_id = $1", member.id
        ):
            return await ctx.error("This member is not a donor")

        await self.bot.db.execute("DELETE FROM donor WHERE user_id = $1", member.id)
        await ctx.confirm(f"{member.mention} perks just got wiped")

    @commands.command()
    async def portal(self: "Developer", ctx: Context, *, gid: int):
        """
        Get the invite link of a server the bot is in
        """
        guild = self.bot.get_guild(gid)

        return await ctx.reply(await guild.text_channels[0].create_invite())


async def setup(bot: Luma):
    return await bot.add_cog(Developer(bot))
