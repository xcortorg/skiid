import aiohttp
import discord
import urllib
from pydantic import BaseModel
from datetime import *  # noqa: F403

key = "HDEV-ec64c7f4-27d4-42e3-8dbf-fbe4457e197f"


# from functions.helpers import format_uri
# from functions import util
# rom functions.util import send_error
class ValorantAccount(BaseModel):
    region: str
    username: str
    level: int
    rank: str
    elo: int
    elo_change: int
    card: str
    updated_at: datetime  # noqa: F405


class ValorantMatch(BaseModel):
    map: str
    status: str
    rounds: int
    kills: int
    deaths: int
    started_at: datetime  # noqa: F405


def format_uri(text: str):
    return urllib.parse.quote(text, safe="")


async def valorant(ctx, username: str):
    """View information about a Valorant Player"""

    sliced = username.split("#", 1)
    if not len(sliced) == 2:
        return await ctx.send_help()
    else:
        username, tag = sliced

    #        await ctx.load(f"Searching for `{username}#{tag}`")

    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"https://api.henrikdev.xyz/valorant/v1/account/{format_uri(username)}/{format_uri(tag)}",
            headers=dict(
                Authorization=key,
            ),
        )
    if response.status == 404:
        return await ctx.fail(f"Couldn't find an account for `{username}#{tag}`")
    elif response.status == 429:
        return await ctx.fail(
            "The **API** is currently **rate limited** - Try again later"
        )
    else:
        data = await response.json()
        if "data" not in data:
            return await ctx.fail(f"Couldn't find an account for `{username}#{tag}`")

        response = await ctx.bot.session.get(
            f"https://api.henrikdev.xyz/valorant/v2/mmr/{data['data']['region']}/{format_uri(username)}/{format_uri(tag)}",
            headers=dict(
                Authorization=key,
            ),
        )
        if response.status == 404:
            return await ctx.fail(f"Couldn't find an account for `{username}#{tag}`")
        elif response.status == 429:
            return await ctx.fail(
                "The **API** is currently **rate limited** - Try again later"
            )
        else:
            _data = await response.json()

        account = ValorantAccount(
            region=data["data"]["region"].upper(),
            username=(data["data"]["name"] + "#" + data["data"]["tag"]),
            level=data["data"]["account_level"],
            rank=_data["data"]["current_data"]["currenttierpatched"] or "Unranked",
            elo=_data["data"]["current_data"]["elo"] or 0,
            elo_change=_data["data"]["current_data"]["mmr_change_to_last_game"] or 0,
            card=data["data"]["card"]["small"],
            updated_at=data["data"]["last_update_raw"],
        )
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"https://api.henrikdev.xyz/valorant/v3/matches/{account.region}/{format_uri(username)}/{format_uri(tag)}",
            params=dict(filter="competitive"),
            headers=dict(
                Authorization=key,
            ),
        )
    if response.status == 404:
        return await ctx.fail(f"Couldn't find any matches for `{username}#{tag}`")
    elif response.status == 429:
        return await ctx.fail(
            "The **API** is currently **rate limited** - Try again later"
        )
    else:
        data = await response.json()
        matches = [
            ValorantMatch(
                map=match["metadata"]["map"],
                rounds=match["metadata"]["rounds_played"],
                status=("Victory" if match["teams"]["red"]["has_won"] else "Defeat"),
                kills=match["players"]["all_players"][0]["stats"]["kills"],
                deaths=match["players"]["all_players"][0]["stats"]["deaths"],
                started_at=match["metadata"]["game_start"],
            )
            for match in data["data"]
        ]

    embed = discord.Embed(
        url=f"https://tracker.gg/valorant/profile/riot/{format_uri(account.username)}/overview",
        title=f"{account.region}: {account.username}",
        color=ctx.bot.color,
        description=(
            f">>> **Account Level:** {account.level}\n**Rank & ELO:** {account.rank} &"
            f" {account.elo} (`{'+' if account.elo_change >= 1 else ''}{account.elo_change}`)"
        ),
    )

    if matches:
        embed.add_field(
            name="Competitive Matches",
            value="\n".join(
                f"> {discord.utils.format_dt(match.started_at, 'd')} {match.status} (`%.2f`)"
                % (match.kills / match.deaths)
                for match in matches
            ),
        )
    embed.set_thumbnail(
        url=account.card,
    )
    embed.set_footer(
        text="Last Updated",
        icon_url="https://img.icons8.com/color/512/valorant.png",
    )
    embed.timestamp = account.updated_at
    return await ctx.send(embed=embed)
