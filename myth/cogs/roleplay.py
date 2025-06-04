import aiohttp
import discord
import requests
from config import color, emoji
from discord.ext import commands
from system.base.context import Context


class Roleplay(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def kiss(self, ctx, user: discord.Member = None):
        if user is None:
            await ctx.warn("**Mention** a user")
            return

        response = requests.get("https://nekos.life/api/v2/img/kiss")
        if response.status_code == 200:
            data = response.json()
            kiss = data["url"]
            embed = discord.Embed(color=color.default)
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_image(url=kiss)
            embed.set_author(
                name=f"{ctx.author.name} | kisses {user.name}", icon_url=user_pfp
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def hug(self, ctx, user: discord.Member = None):
        if user is None:
            await ctx.warn("**Mention** a user")
            return

        response = requests.get("https://nekos.life/api/v2/img/hug")
        if response.status_code == 200:
            data = response.json()
            kiss = data["url"]
            embed = discord.Embed(color=color.default)
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_image(url=kiss)
            embed.set_author(
                name=f"{ctx.author.name} | hugs {user.name}", icon_url=user_pfp
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def slap(self, ctx, user: discord.Member = None):
        if user is None:
            await ctx.warn("**Mention** a user")
            return

        response = requests.get("https://nekos.life/api/v2/img/slap")
        if response.status_code == 200:
            data = response.json()
            kiss = data["url"]
            embed = discord.Embed(color=color.default)
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_image(url=kiss)
            embed.set_author(
                name=f"{ctx.author.name} | slaps {user.name}", icon_url=user_pfp
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def cuddle(self, ctx, user: discord.Member = None):
        if user is None:
            await ctx.warn("**Mention** a user")
            return

        response = requests.get("https://nekos.life/api/v2/img/cuddle")
        if response.status_code == 200:
            data = response.json()
            kiss = data["url"]
            embed = discord.Embed(color=color.default)
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_image(url=kiss)
            embed.set_author(
                name=f"{ctx.author.name} | cuddles {user.name}", icon_url=user_pfp
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def tickle(self, ctx, user: discord.Member = None):
        if user is None:
            await ctx.warn("**Mention** a user")
            return

        response = requests.get("https://nekos.life/api/v2/img/tickle")
        if response.status_code == 200:
            data = response.json()
            kiss = data["url"]
            embed = discord.Embed(color=color.default)
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_image(url=kiss)
            embed.set_author(
                name=f"{ctx.author.name} | tickles {user.name}", icon_url=user_pfp
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def lick(self, ctx, user: discord.Member = None):
        if user is None:
            await ctx.warn("**Mention** a user")
            return

        response = requests.get("https://api.otakugifs.xyz/gif?reaction=lick")
        if response.status_code == 200:
            data = response.json()
            kiss = data["url"]
            embed = discord.Embed(color=color.default)
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_image(url=kiss)
            embed.set_author(
                name=f"{ctx.author.name} | licks {user.name}", icon_url=user_pfp
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def pat(self, ctx, user: discord.Member = None):
        if user is None:
            await ctx.warn("**Mention** a user")
            return

        response = requests.get("https://nekos.life/api/v2/img/pat")
        if response.status_code == 200:
            data = response.json()
            kiss = data["url"]
            embed = discord.Embed(color=color.default)
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_image(url=kiss)
            embed.set_author(
                name=f"{ctx.author.name} | pats {user.name}", icon_url=user_pfp
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def stare(self, ctx, user: discord.Member = None):
        if user is None:
            await ctx.warn("**Mention** a user")
            return

        response = requests.get("https://api.otakugifs.xyz/gif?reaction=stare")
        if response.status_code == 200:
            data = response.json()
            kiss = data["url"]
            embed = discord.Embed(color=color.default)
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_image(url=kiss)
            embed.set_author(
                name=f"{ctx.author.name} | stares at {user.name}", icon_url=user_pfp
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def pinch(self, ctx, user: discord.Member = None):
        if user is None:
            await ctx.warn("**Mention** a user")
            return

        response = requests.get("https://api.otakugifs.xyz/gif?reaction=pinch")
        if response.status_code == 200:
            data = response.json()
            kiss = data["url"]
            embed = discord.Embed(color=color.default)
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_image(url=kiss)
            embed.set_author(
                name=f"{ctx.author.name} | pinches {user.name}", icon_url=user_pfp
            )
            await ctx.send(embed=embed)


async def setup(client):
    await client.add_cog(Roleplay(client))
