from discord import User, Member
from typing import List, Optional, Union, Any
from ..services.cache import cache
from var.config import CONFIG
from loguru import logger
from aiohttp import ClientSession
from lib.managers.trackcord import TrackcordUser, Trackcord, Messages

DPY_MAP = {
    "hypesquad_balance": "hypesquad_house_3",
    "hypesquad_bravery": "hypesquad_house_1",
    "hypesquad_brilliance": "hypesquad_house_2",
    "verified_bot": "verified_app"
}
def user_badges(self: User, as_string: Optional[bool] = False, delimiter: Optional[str] = "") -> Optional[Union[List[str], str]]:
    badges = []
    for flag in self.public_flags:
        if flag[1] and (badge := self.bot.config["emojis"]["flags"].get(flag[0])):
            badges.append(badge)
    if as_string:
        return f"{delimiter}".join(badge for badge in badges)
    else:
        return badges
    
def member_badges(self: Member, as_string: Optional[bool] = False, delimiter: Optional[str] = "") -> Optional[Union[List[str], str]]:
    badges = []
    for flag in self.public_flags:
        if flag[1] and (badge := self.bot.config["emojis"]["flags"].get(flag[0])):
            badges.append(badge)
    if as_string:
        return f"{delimiter}".join(badge for badge in badges)
    else:
        return badges
    
@cache(ttl = 300, key = "trackcord:{self.id}:{raw}")
async def trackcord(self: Union[User, Member], raw: Optional[bool] = False):
    return await Trackcord().get(self.id, raw)

@cache(ttl = 300, key = "messages:{self.id}:{raw}")
async def messages(self: Union[User, Member], raw: Optional[bool] = False):
    return await Trackcord().messages(self.id, raw)

async def trackcord_badges(self: Union[User, Member]) -> str:
    try:
        data = await self.trackcord()
    except Exception as e:
        logger.info(f"failed to get badges due to {e}")
        return ""
    badges = ""
    if self.public_flags.verified_bot:
        badges += f"{CONFIG['emojis']['badges']['verified_app']} "
    else:
        if self.bot:
            badges += f"{CONFIG['emojis']['badges']['app']} "
    if isinstance(self, Member):
        if self.id == self.guild.owner_id:
            badges += f"{CONFIG['emojis']['badges']['owner']} "
    for badge in data.badges:
        name = badge.id.replace("guild_booster_lvl", "boost").replace("premium", "nitro").replace("quest_completed", "quest").replace("legacy_username", "pomelo")
        if emoji := CONFIG["emojis"]["badges"].get(name):
            badges += f"{emoji} "
    return badges



@cache(ttl = 300, key = "badges:{self.id}")
async def worker_badges(self: Union[User, Member]):
    for i in CONFIG["user_tokens"]:
        try:
            async with ClientSession() as session:
                async with session.get(f"https://discord.com/api/v9/users/{self.id}/profile", headers = {"Authorization": i}) as response:
                    data = await response.json()
                    if len(data.get("mutual_guilds")) != 0:
                        break
        except Exception:
            pass
    if data.get("badges"):
        for k in data["badges"]:
            if str(k["id"]).startswith("guild_booster"):
                level = int(str(k["id"]).strip("guild_booster_lvl"))
    if data.get("premium_since"):
        nitro = True
    else:
        nitro = False
    try:
        if not level:
            level = None
    except Exception:
        level = None
    return [nitro, level]


User.badges = user_badges
Member.badges = member_badges
User.worker_badges = worker_badges
Member.worker_badges = worker_badges
User.trackcord = trackcord
Member.trackcord = trackcord
User.messages = messages
Member.messages = messages
User.trackcord_badges = trackcord_badges
Member.trackcord_badges = trackcord_badges
