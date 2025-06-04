import asyncio
import datetime
import random
import string

import asyncpg
import discord
from discord import Guild, Member, User
from discord.ext import commands
from discord.ext.commands import Cog, command, group, is_owner
from get.checks import Owners
from get.pretend import Pretend, PretendContext

from .auth import owners


class owner(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @commands.command(
        name="eval", aliases=["evaluate", "ev"], description="Evaluates code"
    )
    @commands.is_owner()
    async def eval(self, ctx, code: str):
        await ctx.reply(f"```{eval(code)}```")

    @commands.command(name="exec", aliases=["ex"], description="Executes code")
    @commands.is_owner()
    async def exec(self, ctx, code: str):
        await ctx.reply(f"```{exec(code)}```")

    @commands.command(name="shutdown", aliases=["sd"], description="Shuts down the bot")
    @commands.is_owner()
    async def shutdown(self, ctx):
        await ctx.reply(f"```{self.bot.logout()}```")

    @commands.command(name="leaveguild", aliases=["lv"], description="Leaves the guild")
    @commands.is_owner()
    async def leave(self, ctx):
        await ctx.guild.leave()
        await ctx.approve("Successfully left the guild")

    @commands.command(
        name="join", aliases=["jn"], description="Generates an invite link for the bot"
    )
    @commands.is_owner()
    async def join(self, ctx):
        try:
            invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot"
            await ctx.send(
                f"Use this link to invite the bot to a server: {invite_link}"
            )
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="reload", aliases=["rl"], description="Reload all functions")
    @commands.is_owner()
    async def reload(self, ctx):
        reloaded = []

        # Loop through all loaded extensions (cogs)
        for extension_name in list(self.bot.extensions):
            try:
                await self.bot.reload_extension(
                    extension_name
                )  # Correctly await the coroutine
                reloaded.append(extension_name)
            except Exception as e:
                # Log the error for debugging purposes
                print(f"Failed to reload {extension_name}: {e}")
                await ctx.send_warning(f"Failed to reload `{extension_name}` - {e}")

        await ctx.send_success(f"Successfully reloaded `{len(reloaded)}` features!")

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def donor(self, ctx: commands.Context):
        await ctx.create_pages()

    @donor.command()
    @commands.is_owner()
    async def add(self, ctx: commands.Context, *, member: discord.User):
        result = await self.bot.db.fetchrow(
            "SELECT * FROM donor WHERE user_id = {}".format(member.id)
        )
        if result is not None:
            return await ctx.send_error(f"This member is **already** a donor")
        ts = int(datetime.datetime.now().timestamp())
        await self.bot.db.execute("INSERT INTO donor VALUES ($1,$2)", member.id, ts)
        return await ctx.send_success(f"{member.mention} can use donator perks now!")

    @donor.command()
    @commands.is_owner()
    async def remove(self, ctx: commands.Context, *, member: discord.User):
        result = await self.bot.db.fetchrow(
            "SELECT * FROM donor WHERE user_id = {}".format(member.id)
        )
        if result is None:
            return await ctx.reply(f"{member} isn't a donor")
        await self.bot.db.execute(
            "DELETE FROM donor WHERE user_id = {}".format(member.id)
        )
        return await ctx.send_success(f"Removed {member.mention}'s perks")

    @commands.command(aliases=["guilds"])
    @commands.is_owner()
    async def servers(self, ctx: commands.Context):
        def key(s):
            return s.member_count

        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        lis = [g for g in self.bot.guilds]
        lis.sort(reverse=True, key=key)
        for guild in lis:
            mes = f"{mes}`{k}` {guild.name} ({guild.id}) - ({guild.member_count}) - {guild.owner}\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    discord.Embed(
                        color=self.bot.color,
                        title=f"guilds ({len(self.bot.guilds)})",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        number.append(
            discord.Embed(
                color=self.bot.color,
                title=f"guilds ({len(self.bot.guilds)})",
                description=messages[i],
            )
        )
        await ctx.paginator(number)

    @commands.command(aliases=["db"])
    @commands.is_owner()
    async def dbexecute(self, ctx: commands.Context, *, dbinp):
        if not ctx.author.id in self.bot.owner_ids:
            return None
        try:
            dbexec = await self.bot.db.execute(f"{dbinp}")
            await ctx.send(dbexec)
        except Exception as e:
            await ctx.send(str(e))

    @commands.command()
    @commands.is_owner()
    async def portal(self, ctx, id: int):
        await ctx.message.delete()
        guild = self.bot.get_guild(id)
        for c in guild.text_channels:
            if c.permissions_for(guild.me).create_instant_invite:
                invite = await c.create_invite()
                await ctx.author.send(f"{guild.name} invite link - {invite}")
                break

    @commands.command()
    @commands.is_owner()
    async def unblacklist(self, ctx, *, member: discord.User):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM nodata WHERE user_id = $1", member.id
        )
        if check is None:
            return await ctx.send_warning(f"{member.mention} is not blacklisted")
        await self.bot.db.execute(
            "DELETE FROM nodata WHERE user_id = {}".format(member.id)
        )
        await ctx.send_success(f"{member.mention} can use the bot")

    @commands.command()
    @commands.is_owner()
    async def delerrors(self, ctx: commands.Context):
        await self.bot.db.execute("DELETE FROM cmderror")
        await ctx.reply("deleted all errors")

    @commands.command(aliases=["trace"])
    @commands.is_owner()
    async def geterror(self, ctx: commands.Context, key: str):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM cmderror WHERE code = $1", key
        )
        if not check:
            return await ctx.send_error(f"No error associated with the key `{key}`")
        embed = discord.Embed(
            color=self.bot.color,
            title=f"error {key}",
            description=f"```{check['error']}```",
        )
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def getkey(self, ctx: commands.Context):
        def generate_key(length):
            return "".join(
                random.choice(string.ascii_letters + string.digits)
                for _ in range(length)
            )

        await ctx.send(generate_key(36))

    @commands.command()
    @commands.is_owner()
    async def blacklist(self, ctx: commands.Context, *, member: discord.User):
        if member.id in owners:
            return await ctx.reply("Do not blacklist a bot owner, retard")
        check = await self.bot.db.fetchrow(
            "SELECT * FROM nodata WHERE user_id = $1 AND state = $2", member.id, "false"
        )
        if check is not None:
            return await ctx.send_warning(f"{member.mention} is already blacklisted")
        await self.bot.db.execute(
            "DELETE FROM nodata WHERE user_id = {}".format(member.id)
        )
        await self.bot.db.execute(
            "INSERT INTO nodata VALUES ($1,$2)", member.id, "false"
        )
        await ctx.send_success(f"{member.mention} can no longer use the bot")


async def setup(bot) -> None:
    await bot.add_cog(owner(bot))
