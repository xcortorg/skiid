from __future__ import annotations

import datetime
import io
import re

import discord
from aiohttp import ClientSession
from discord.ext.commands import CommandError
from discord.ui import Button, View
from discord.utils import format_dt
from tools.important.subclasses.parser import Script
from yarl import URL


def ordinal(n):
    n = int(n)
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4])


class EmbedBuilder:
    def __init__(self, user: discord.User | discord.Member, lastfm_data: dict = {}):
        self.user = user
        self.lastfm_data = lastfm_data
        self.replacements = {
            "{user}": str(user),
            "{user.mention}": user.mention,
            "{user.name}": user.name,
            "{user.avatar}": user.display_avatar.url,
            "{user.joined_at}": format_dt(user.joined_at, style="R"),
            "{user.created_at}": format_dt(user.created_at, style="R"),
            "{guild.name}": user.guild.name,
            "{guild.count}": str(user.guild.member_count),
            "{guild.count.format}": ordinal(len(user.guild.members)),
            "{guild.id}": user.guild.id,
            "{guild.created_at}": format_dt(user.guild.created_at, style="R"),
            "{guild.boost_count}": str(user.guild.premium_subscription_count),
            "{guild.booster_count}": str(len(user.guild.premium_subscribers)),
            "{guild.boost_count.format}": ordinal(
                str(user.guild.premium_subscription_count)
            ),
            "{guild.booster_count.format}": ordinal(
                str(user.guild.premium_subscription_count)
            ),
            "{guild.boost_tier}": str(user.guild.premium_tier),
            "{guild.icon}": user.guild.icon.url if user.guild.icon else "",
            "{track}": lastfm_data.get("track", ""),
            "{track.duration}": lastfm_data.get("duration", ""),
            "{artist}": lastfm_data.get("artist", ""),
            "{user}": lastfm_data.get("user", ""),
            "{avatar}": lastfm_data.get("avatar", ""),
            "{track.url}": lastfm_data.get("track.url", ""),
            "{artist.url}": lastfm_data.get("artist.url", ""),
            "{scrobbles}": lastfm_data.get("scrobbles", ""),
            "{track.image}": lastfm_data.get("track.image", ""),
            "{username}": lastfm_data.get("username", ""),
            "{artist.plays}": lastfm_data.get("artist.plays", ""),
            "{track.plays}": lastfm_data.get("track.plays", ""),
            "{track.lower}": lastfm_data.get("track.lower", ""),
            "{artist.lower}": lastfm_data.get("artist.lower", ""),
            "{track.hyperlink}": lastfm_data.get("track.hyperlink", ""),
            "{track.hyperlink_bold}": lastfm_data.get("track.hyperlink_bold", ""),
            "{artist.hyperlink}": lastfm_data.get("artist.hyperlink", ""),
            "{artist.hyperlink_bold}": lastfm_data.get("artist.hyperlink_bold", ""),
            "{track.color}": lastfm_data.get("track.color", ""),
            "{artist.color}": lastfm_data.get("artist.color", ""),
            "{date}": lastfm_data.get("date", ""),
        }

    async def replace_placeholders(self, d: str):
        for placeholder, value in self.replacements.items():
            d = d.replace(placeholder, str(value))

    @property
    def replacements(self):
        return Script("{embed}{description: sup my nigga}", self.user).replacements

    async def build_embed(self, code: str) -> dict:
        code = await self.replace_placeholders(code)
        parser = Script(code, self.user, self.lastfm_data)
        await parser.compile()
        return parser.data
