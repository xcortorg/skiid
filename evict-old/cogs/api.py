import discord
from bot.bot import Evict
from bot.helpers import EvictContext
from bot.managers.emojis import Colors, Emojis
from discord.ext import commands


class api(commands.Cog):
    def __init__(self, bot: Evict):
        self.bot = bot

    @commands.group(invoke_without_command=True, name="apikey")
    async def api(self, ctx: EvictContext):
        await ctx.create_pages()

    @api.command(
        name="add",
        brief="bot owner",
        usage="[user] [key] [role]\n[master] [bot_developer] [premium] [pro] [basic]",
        description="add an api key",
    )
    @commands.is_owner()
    async def apikey_add(
        self, ctx: EvictContext, user: discord.User, key: str, role: str
    ):

        url = "https://api.evict.cc"

        check = await self.bot.db.fetchrow(
            "SELECT * FROM api_key WHERE user_id = {}".format(user.id)
        )

        if check is not None:
            return await ctx.warning(
                f"The user **{user.name}** already has a **valid** API key."
            )

        embed = discord.Embed(
            description=f"Your API key for {url} is listed above.", color=Colors.color
        )

        await self.bot.db.execute(
            "INSERT INTO api_key VALUES ($1,$2,$3)", key, user.id, role
        )

        await ctx.success(
            f"I have **successfully** added the API key **{key}** to {user.mention}."
        )

        await user.send(f"{key}", embed=embed)

    @api.command(
        name="delete",
        brief="bot owner",
        usage="[user]",
        description="delete an api key",
    )
    @commands.is_owner()
    async def apikey_delete(self, ctx: EvictContext, user: discord.User):

        check = await self.bot.db.fetchrow(
            "SELECT * FROM api_key WHERE user_id = {}".format(user.id)
        )

        if check is None:
            return await ctx.warning(
                f"The user **{user.name}** doesn't have a **valid** API key."
            )

        await self.bot.db.execute(
            "DELETE FROM api_key WHERE user_id = {}".format(user.id)
        )

        await ctx.success(
            f"I have **successfully** deleted the API key from **{user.name}**."
        )

    @api.command(
        name="get",
        brief="bot owner",
        usage="[user]",
        description="get the api key for a user",
    )
    @commands.is_owner()
    async def apikey_get(self, ctx: EvictContext, user: discord.User):

        check = await self.bot.db.fetchrow(
            "SELECT * FROM api_key WHERE user_id = {}".format(user.id)
        )

        if check is None:
            return await ctx.warning(
                f"The user **{user.name}** doesn't have a **valid** API key."
            )

        key = check["key"]

        await ctx.author.send(key)


async def setup(bot: Evict):
    await bot.add_cog(api(bot))
