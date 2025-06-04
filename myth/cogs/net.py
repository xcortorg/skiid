from datetime import datetime, timedelta

import aiohttp
import discord
from config import color, emoji
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import format_dt, get
from fulcrum_api import FulcrumAPI
from system.base.context import Context


class Network(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.fulcrumapi = FulcrumAPI()

    @commands.command(description="Get information on a tiktok user")
    async def tiktok(self, ctx, username: str):
        data = await self.fulcrumapi.tiktok_user(username)
        bio = data.get("bio") or "n/a"

        embed = discord.Embed(color=color.default, description=f"> {bio}")
        embed.set_author(
            name=f"{data.get('nickname', 'unknown')} | {data.get('username', 'n/a')}"
        )
        embed.set_thumbnail(url=data.get("avatar", ""))
        embed.add_field(
            name="Stats",
            value=f"> **Followers:** {data.get('followers', 'n/a')}\n> **Following:** {data.get('following', 'n/a')}\n> **Likes:** {data.get('hearts', 'n/a')}",
        )
        embed.add_field(
            name="Extras",
            value=f"> **Videos:** {data.get('videos', 'n/a')} \n> **Verified:** {'Yes' if data.get('verified') else 'No'}\n> **Private:** {'Yes' if data.get('private') else 'No'}",
        )
        embed.set_footer(text=f"ID: {data.get('id', 'n/a')}")

        view = View()
        profile = Button(
            style=discord.ButtonStyle.link,
            label="Profile",
            url=data.get("url", ""),
            emoji=emoji.link,
        )
        view.add_item(profile)

        await ctx.send(embed=embed, view=view)

    @commands.command(description="Get information on a twitter user")
    async def twitter(self, ctx, username: str):
        data = await self.fulcrumapi.twitter_user(username)
        bio = data.get("bio") or "n/a"
        location = data.get("location" or "n/a")

        created_at = data.get("created_at", None)
        try:
            created_at_formatted = (
                format_dt(datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y"), "R")
                if created_at
                else "n/a"
            )
        except ValueError:
            created_at_formatted = "n/a"

        embed = discord.Embed(color=color.default, description=f"> {bio}")
        embed.set_author(
            name=f"{data.get('display_name', 'unknown')} | {data.get('username', 'n/a')}"
        )
        embed.set_thumbnail(url=data.get("avatar", ""))
        embed.add_field(
            name="Stats",
            value=f"> **Followers:** {data.get('followers', 'n/a')}\n> **Following:** {data.get('following', 'n/a')}\n> **Posts:** {data.get('posts', 'n/a')}",
        )
        embed.add_field(
            name="Extras",
            value=f"> **Verified:** {'Yes' if data.get('verified') else 'No'}\n> **Created:** {created_at_formatted} \n> **Location:** {location}",
        )
        embed.set_footer(text=f"ID: {data.get('id', 'n/a')}")
        embed.add_field(
            name="More",
            value=f"> **Liked Posts:** {data.get('liked_posts', 'n/a')}\n> **Tweets:** {data.get('tweets', 'n/a')}",
        )

        view = View()
        profile = Button(
            style=discord.ButtonStyle.link,
            label="Profile",
            url=data.get("url", ""),
            emoji=emoji.link,
        )
        view.add_item(profile)
        await ctx.send(embed=embed, view=view)

    @commands.command(description="Get information on a roblox user")
    async def roblox(self, ctx, username: str):
        data = await self.fulcrumapi.roblox(username)
        bio = data.get("bio") or "n/a"

        created_at = data.get("created_at", None)
        created_at_formatted = (
            format_dt(datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S"))
            if created_at
            else "n/a"
        )

        embed = discord.Embed(color=color.default, description=f"> {bio}")
        embed.set_author(
            name=f"{data.get('display_name', 'unknown')} | {data.get('username', 'n/a')}"
        )
        embed.set_thumbnail(url=data.get("avatar", ""))
        embed.add_field(
            name="Stats",
            value=f"> **Friends:** {data.get('friends', 'n/a')}\n> **Followers:** {data.get('followers', 'n/a')}\n> **Following:** {data.get('followings', 'n/a')}",
        )
        embed.add_field(
            name="Profile Info",
            value=f"> **Banned:** {'Yes' if data.get('banned') else 'No'}\n> **Verified:** {'Yes' if data.get('verified') else 'No'} \n> **Created:** {created_at_formatted}",
        )
        embed.set_footer(text=f"ID: {data.get('id', 'n/a')}")

        view = View()
        profile = Button(
            style=discord.ButtonStyle.link,
            label="Profile",
            url=data.get("url", ""),
            emoji=emoji.link,
        )
        view.add_item(profile)
        await ctx.send(embed=embed, view=view)

    @commands.command(description="Get information on a cashapp user")
    async def cashapp(self, ctx, username: str):
        data = await self.fulcrumapi.cashapp(username)

        embed = discord.Embed(color=color.default)
        embed.set_author(
            name=f"{data.get('display_name', 'unknown')} | {data.get('username', 'n/a')}"
        )
        embed.set_thumbnail(url=data.get("avatar", ""))
        embed.add_field(
            name="Profile Info",
            value=f"> **Verified:** {'Yes' if data.get('verified') else 'No'}",
            inline=True,
        )

        view = View()
        profile = Button(
            style=discord.ButtonStyle.link,
            label="Profile",
            url=data.get("url", ""),
            emoji=emoji.link,
        )
        qr_code = Button(
            style=discord.ButtonStyle.link,
            label="QR Code",
            url=data.get("qr_url", ""),
            emoji=emoji.link,
        )

        view.add_item(profile)
        view.add_item(qr_code)
        await ctx.send(embed=embed, view=view)

    @commands.command(description="Get information on a city")
    async def weather(self, ctx, city: str):
        data = await self.fulcrumapi.weather(city)

        city = data.get("city", "unknown")
        country = data.get("country", "unknown")
        timestring = data.get("timestring", "time unavailable")
        last_updated = data.get("last_updated", None)
        last_updated_formatted = (
            format_dt(datetime.strptime(last_updated, "%Y-%m-%dT%H:%M:%S"))
            if last_updated
            else "n/a"
        )

        celsius = data.get("celsius", "n/a")
        fahrenheit = data.get("fahrenheit", "n/a")
        feelslike_c = data.get("feelslike_c", "n/a")
        feelslike_f = data.get("feelslike_f", "n/a")
        wind_mph = data.get("wind_mph", "n/a")
        wind_kph = data.get("wind_kph", "n/a")
        condition_text = data.get("condition_text", "no data")
        condition_icon = data.get("condition_icon", "")
        humidity = data.get("humidity", "n/a")

        embed = discord.Embed(color=color.default, description=f"> {condition_text}")
        embed.set_author(name=f"{city}, {country} | {timestring}")
        embed.set_thumbnail(url=condition_icon)
        embed.add_field(
            name="Temperature",
            value=f"> **Celsius:** {celsius}°C\n> **Fahrenheit:** {fahrenheit}°F",
        )
        embed.add_field(
            name="Feels Like",
            value=f"> **Celsius:** {feelslike_c}°C\n> **Fahrenheit:** {feelslike_f}°F",
        )
        embed.add_field(
            name="Wind", value=f"> **MPH:** {wind_mph} mph\n> **KPH:** {wind_kph} kph"
        )
        embed.add_field(
            name="Extras",
            value=f"> **Humidity:** {humidity}% \n> **Last Updated:** {last_updated_formatted}",
        )

        view = View()
        more_info = Button(
            style=discord.ButtonStyle.link,
            label="More Info",
            url=f"https://www.weather.com/weather/today/l/{city_name}",
            emoji=emoji.link,
        )
        view.add_item(more_info)

        await ctx.send(embed=embed, view=view)


async def setup(client):
    await client.add_cog(Network(client))
