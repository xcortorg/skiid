import datetime
from typing import Union

import discord
from bot.bot import Evict
from bot.helpers import EvictContext
from bot.managers.emojis import Colors
from discord.ext import commands
from patches.permissions import Permissions


class auth(commands.Cog):
    def __init__(self, bot: Evict):
        self.bot = bot

    @commands.command()
    @Permissions.staff()
    async def authorize(
        self, ctx: EvictContext, guild: int, buyer: Union[discord.Member, discord.User]
    ):

        channel = self.bot.get_channel(1268645258288435346)

        check = await self.bot.db.fetchrow(
            "SELECT * FROM authorize WHERE guild_id = $1", guild
        )
        if check is not None:
            return await ctx.warning("This server is **already** whitelisted.")

        embed = discord.Embed(
            color=Colors.color,
            description="The following server has been authorized",
            title="Authorization",
            timestamp=datetime.datetime.now(),
        )

        embed.add_field(name="Server ID", value=f"{guild}", inline=False)
        embed.add_field(name="Buyer Mention", value=f"{buyer.mention}", inline=False)
        embed.add_field(name="Buyer ID", value=f"{buyer.id}", inline=False)
        embed.add_field(
            name="Staff Mention", value=f"{ctx.author.mention}", inline=False
        )
        embed.add_field(name="Staff ID", value=f"{ctx.author.id}", inline=False)

        embed.set_thumbnail(url=ctx.author.avatar.url)

        await channel.send(embed=embed)
        await self.bot.db.execute(
            "INSERT INTO authorize VALUES ($1,$2)", guild, buyer.id
        )
        await ctx.success(
            f"I have **added** the guild ID **{guild}** as an authorized server to {buyer}."
        )

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="invite",
                url=discord.utils.oauth_url(
                    client_id=self.bot.user.id, permissions=discord.Permissions.all()
                ),
            )
        )

        try:
            await buyer.send(
                f"Your server **{guild}** has been authorized. Invite me below.",
                view=view,
            )
        except:
            pass

    @commands.command()
    @Permissions.staff()
    async def getauth(self, ctx: EvictContext, *, member: discord.User):

        results = await self.bot.db.fetch(
            "SELECT * FROM authorize WHERE buyer = $1", member.id
        )

        if len(results) == 0:
            return await ctx.warning(
                "There is no server authorized for **{}**.".format(member)
            )

        await ctx.paginate(
            [
                f"{f'**{str(self.bot.get_guild(m[0]))}** `{m[0]}`' if self.bot.get_guild(m[0]) else f'`{m[0]}`'}"
                for m in results
            ],
            f"Authorized guilds ({len(results)})",
            {"name": member.name, "icon_url": member.display_avatar.url},
        )

    @commands.command()
    @Permissions.staff()
    async def unauthorize(
        self, ctx: EvictContext, id: int = None, *, reason: str = "No Reason Provided"
    ):

        channel = self.bot.get_channel(1268645258288435346)

        check = await self.bot.db.fetchrow(
            "SELECT * FROM authorize WHERE guild_id = $1", id
        )

        if check is None:
            return await ctx.warning(f"I am **unable** to find this server.")

        embed = discord.Embed(
            color=Colors.color,
            description="The following server has been unauthorized",
            title="Unauthorization",
            timestamp=datetime.datetime.now(),
        )

        embed.add_field(name="Server ID", value=f"{id}", inline=False)

        embed.add_field(
            name="Staff Mention", value=f"{ctx.author.mention}", inline=False
        )

        embed.add_field(name="Staff ID", value=f"{ctx.author.id}", inline=False)

        embed.set_thumbnail(url=ctx.author.avatar.url)

        await channel.send(embed=embed)
        await self.bot.db.execute("DELETE FROM authorize WHERE guild_id = $1", id)
        await ctx.success(f"I have **removed** the authorization for **{id}**.")

        guild = self.bot.get_guild(int(id))
        if guild == None:
            return
        try:
            await guild.leave()
        except:
            return


async def setup(bot: Evict):
    await bot.add_cog(auth(bot))
