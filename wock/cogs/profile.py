import json
from logging import getLogger
from typing import Optional, Union

from discord import Embed, Member, User, utils
from discord.ext.commands import AutoShardedBot, Cog, Context, command, group

logger = getLogger(__name__)


class Profile(Cog):
    def __init__(self, bot: AutoShardedBot):
        self.bot = bot
        self.emoji_map = {
            "instagram": "[IG]",
            "tiktok": "[TT]",
            "x": "[X]",
            "pinterest": "[PIN]",
        }

    def format_url(self, kind: str, username: str) -> str:
        if kind.lower() == "tiktok":
            return f"https://tiktok.com/@{username}"
        elif kind.lower() == "instagram":
            return f"https://instagram.com/{username}"
        elif kind.lower() == "x":
            return f"https://x.com/{username}"
        else:
            return f"https://pinterest.com/{username}"

    @group(
        name="profile",
        aliases=("aboutme",),
        brief="show information regarding yourself",
        invoke_without_command=True,
    )
    async def profile(self, ctx: Context, *, member: Optional[Member] = None):
        if not member:
            member = ctx.author

        data = await self.bot.db.fetchrow(
            """SELECT description, socials, friends FROM profile WHERE user_id = $1""",
            member.id,
        )
        if not data:
            return await ctx.fail("that user doesn't have a profile setup")
        embed = Embed(
            title=member.name,
            url=f"https://discord.com/users/{member.id}",
            color=member.color,
        )
        embed.add_field(
            name="Bio", value=data.description or "No bio added", inline=False
        )
        socials = ""
        friends = ""
        if not data.socials:
            __socials = "[]"
        else:
            __socials = data.socials
        if not data.friends:
            __friends = "[]"
        else:
            __friends = data.friends
        logger.info(f"{__socials}\n{__friends}")
        _socials = json.loads(__socials)
        _friends = json.loads(__friends)
        for _social in _socials:
            if isinstance(_social, str):
                _social = json.loads(_social)
            for key, value in _social.items():
                socials += f"{self.emoji_map[key]}({self.format_url(key, value)})\n"
        i = 0
        if len(_friends) > 0:
            for f in _friends:
                if user := self.bot.get_user(f):
                    if i == 0:
                        friends += f"**{user.name}**"
                    else:
                        friends += f", **{user.name}**"
        else:
            friends += "No Friends Added"
        if socials == "":
            socials = "No Socials Added"
        embed.add_field(name="Socials", value=socials, inline=False)
        embed.add_field(name="Friends", value=friends, inline=False)
        embed.add_field(
            name="Creation",
            value=utils.format_dt(member.created_at, style="R"),
            inline=False,
        )
        return await ctx.send(embed=embed)

    @profile.command(
        name="set",
        brief="setup your profile",
        usage=",profile set {variable} {value}",
        example=",profile set instagram terrorist",
    )
    async def profile_set(self, ctx: Context, variable: str, *, username: str):
        data = await self.bot.db.fetchrow(
            """SELECT * FROM profile WHERE user_id = $1""", ctx.author.id
        )
        if variable.lower() in [
            "bio",
            "biography",
            "desc",
            "description",
            "aboutme",
            "abtme",
            "abme",
        ]:
            kwargs = ("description", username, ctx.author.id)
        elif variable.lower() in ["tt", "tiktok"]:
            if data.socials:
                socials = json.loads(data.socials)
                socials.append({"tiktok": username})
            else:
                socials = [{"tiktok": username}]
            kwargs = ("socials", json.dumps(socials), ctx.author.id)
        elif variable.lower() in ["ig", "insta", "instagram"]:
            if data.socials:
                socials = json.loads(data.socials)
                socials.append({"instagram": username})
            else:
                socials = [{"instagram": username}]
            kwargs = ("socials", json.dumps(socials), ctx.author.id)
        elif variable.lower() in ["x", "twitter", "tw"]:
            if data.socials:
                socials = json.loads(data.socials)
                socials.append({"x": username})
            else:
                socials = [{"x": username}]
            kwargs = ("socials", json.dumps(socials), ctx.author.id)
        elif variable.lower() in ["pinterest", "pin"]:
            if data.socials:
                socials = json.loads(data.socials)
                socials.append({"pinterest": username})
            else:
                socials = [{"pinterest": username}]
            kwargs = ("socials", json.dumps(socials), ctx.author.id)
        else:
            return await ctx.fail(f"not a proper variable")
        await self.bot.db.execute(
            f"INSERT INTO profile (user_id, {kwargs[0]}) VALUES($1, $2) ON CONFLICT(user_id) DO UPDATE SET {kwargs[0]} = excluded.{kwargs[0]}",
            kwargs[2],
            kwargs[1],
        )
        return await ctx.success(
            f"successfully set your **{kwargs[0]}** as `{username}`"
        )

    @profile.command(
        name="friend",
        brief="add or remove a user as a friend",
        usage=",profile friend {user}",
        example=",profile friend aiohttp",
    )
    async def profile_friend(self, ctx: Context, *, user: User | Member):
        data = await self.bot.db.fetchval(
            """SELECT friends FROM profile WHERE user_id = $1""", ctx.author.id
        )
        if data:
            friends = json.loads(data)
        else:
            friends = []
        if user.id in friends:
            friends.remove(user.id)
            m = "removed"
        else:
            friends.append(user.id)
            m = "added"
        await self.bot.db.execute(
            """INSERT INTO profile (user_id, friends) VALUES($1, $2) ON CONFLICT(user_id) DO UPDATE SET friends = excluded.friends""",
            ctx.author.id,
            json.dumps(friends),
        )
        return await ctx.success(f"successfully **{m}** `{user.name}` as a friend")


async def setup(bot):
    await bot.add_cog(Profile(bot))
