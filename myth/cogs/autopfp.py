import discord
from aiohttp import ClientSession
from discord.ext import commands


class autopfp(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.header = {"Authorization": "Bearer 59f4c035-cd6c-4a38-8f10-933a519f0a74"}

    @commands.command()
    @commands.is_owner()
    async def testpfp(self, ctx, *, option: str):
        embed = discord.Embed(color=0x2B2D31).set_footer(text="powered by signed.bio")
        async with ClientSession() as session:
            async with session.get(
                "https://signed.bio/api", headers=self.header, params={"option": option}
            ) as response:
                if response.status != 200:
                    await ctx.send("Failed to fetch image.")
                    return
                data = await response.json()
                embed.set_thumbnail(url=data["url"])
                msg = await ctx.send(embed=embed)
                await msg.add_reaction(f"{emoji.agree}")


async def setup(client):
    await client.add_cog(autopfp(client))
