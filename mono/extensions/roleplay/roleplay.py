from typing import Optional, cast

from core.client.context import Context
from core.Mono import Mono
from discord import Embed, Member, Message
from discord.ext.commands import (BucketType, Cog, Range, command, cooldown,
                                  group, max_concurrency)
from humanize import ordinal
from yarl import URL

BASE_URL = URL.build(
    scheme="https",
    host="nekos.best",
)


ACTIONS = {
    "bite": "bites",
    "cuddle": "cuddles",
    "feed": "feeds",
    "hug": "hugs",
    "kiss": "kisses",
    "pat": "pats",
    "poke": "pokes",
    "punch": "punches",
    "slap": "slaps",
    "smug": "smugs at",
    "tickle": "tickles",
    "neko": "shows a neko to",
    "waifu": "shows a waifu to",
    "husbando": "shows a husbando to",
    "kitsune": "shows a kitsune to",
    "lurk": "lurks at",
    "shoot": "shoots",
    "sleep": "sleeps with",
    "shrug": "shrugs at",
    "stare": "stares at",
    "wave": "waves at",
    "smile": "smiles at",
    "peck": "pecks",
    "wink": "winks at",
    "blush": "blushes at",
    "yeet": "yeets",
    "think": "thinks about",
    "highfive": "high-fives",
    "bored": "is bored with",
    "nom": "noms",
    "yawn": "yawns at",
    "facepalm": "facepalms at",
    "happy": "is happy with",
    "baka": "calls baka",
    "nod": "nods at",
    "nope": "nopes at",
    "dance": "dances with",
    "handshake": "shakes hands with",
    "cry": "cries with",
    "pout": "pouts at",
    "handhold": "holds hands with",
    "thumbsup": "gives a thumbs up to",
    "laugh": "laughs with",
}


class Roleplay(Cog):
    def __init__(self, bot: Mono):
        self.bot = bot

    async def send(
        self,
        ctx: Context,
        member: Optional[Member],
        category: str,
    ) -> Message:
        """
        Requests the API,
        and structures the embed.
        """

        response = await self.bot.session.get(
            BASE_URL.with_path(f"/api/v2/{category}"),
        )
        data = await response.json()
        if not data.get("results"):
            return await ctx.warn("Something went wrong, please try again later!")

        embed = Embed()

        if member:
            amount = 0
            if member != ctx.author:
                amount = cast(
                    int,
                    await self.bot.db.fetchval(
                        """
                        INSERT INTO roleplay (user_id, target_id, category)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id, target_id, category)
                        DO UPDATE SET amount = roleplay.amount + 1
                        RETURNING amount
                        """,
                        ctx.author.id,
                        member.id,
                        category,
                    ),
                )

            embed.description = (
                f"> {ctx.author.mention} **{ACTIONS[category]}** {member.mention}"
                + (
                    f" for the **{ordinal(amount)}** time!"
                    if member != ctx.author and amount
                    else ""
                )
            )

        embed.set_image(url=data["results"][0]["url"])

        return await ctx.send(embed=embed)

    @command()
    @cooldown(1, 5, BucketType.member)
    async def bite(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Bite someone."""
        return await self.send(ctx, member, "bite")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def cuddle(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Cuddle someone."""
        return await self.send(ctx, member, "cuddle")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def feed(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Feed someone."""
        return await self.send(ctx, member, "feed")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def hug(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Hug someone."""
        return await self.send(ctx, member, "hug")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def kiss(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Kiss someone."""
        return await self.send(ctx, member, "kiss")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def pat(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Pat someone."""
        return await self.send(ctx, member, "pat")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def poke(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Poke someone."""
        return await self.send(ctx, member, "poke")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def punch(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Punch someone."""
        return await self.send(ctx, member, "punch")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def slap(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Slap someone."""
        return await self.send(ctx, member, "slap")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def smug(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Smug at someone."""
        return await self.send(ctx, member, "smug")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def tickle(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Tickle someone."""
        return await self.send(ctx, member, "tickle")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def neko(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Show a neko to someone."""
        return await self.send(ctx, member, "neko")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def waifu(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Show a waifu to someone."""
        return await self.send(ctx, member, "waifu")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def husbando(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Show a husbando to someone."""
        return await self.send(ctx, member, "husbando")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def kitsune(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Show a kitsune to someone."""
        return await self.send(ctx, member, "kitsune")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def laugh(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Laugh with someone."""
        return await self.send(ctx, member, "laugh")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def lurk(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Lurk at someone."""
        return await self.send(ctx, member, "lurk")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def shoot(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Shoot someone."""
        return await self.send(ctx, member, "shoot")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def sleep(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Sleep with someone."""
        return await self.send(ctx, member, "sleep")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def thumbsup(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Give a thumbs up to someone."""
        return await self.send(ctx, member, "thumbsup")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def shrug(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Shrug at someone."""
        return await self.send(ctx, member, "shrug")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def stare(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Stare at someone."""
        return await self.send(ctx, member, "stare")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def wave(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Wave at someone."""
        return await self.send(ctx, member, "wave")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def smile(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Smile at someone."""
        return await self.send(ctx, member, "smile")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def peck(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Peck someone."""
        return await self.send(ctx, member, "peck")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def wink(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Wink at someone."""
        return await self.send(ctx, member, "wink")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def blush(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Blush at someone."""
        return await self.send(ctx, member, "blush")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def yeet(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Yeet someone."""
        return await self.send(ctx, member, "yeet")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def think(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Think about someone."""
        return await self.send(ctx, member, "think")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def highfive(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """High-five someone."""
        return await self.send(ctx, member, "highfive")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def bored(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Be bored with someone."""
        return await self.send(ctx, member, "bored")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def nom(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Nom someone."""
        return await self.send(ctx, member, "nom")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def yawn(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Yawn at someone."""
        return await self.send(ctx, member, "yawn")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def facepalm(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Facepalm at someone."""
        return await self.send(ctx, member, "facepalm")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def happy(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Be happy with someone."""
        return await self.send(ctx, member, "happy")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def baka(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Call someone baka."""
        return await self.send(ctx, member, "baka")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def nod(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Nod at someone."""
        return await self.send(ctx, member, "nod")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def nope(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Nope at someone."""
        return await self.send(ctx, member, "nope")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def dance(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Dance with someone."""
        return await self.send(ctx, member, "dance")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def handshake(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Shake hands with someone."""
        return await self.send(ctx, member, "handshake")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def cry(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Cry with someone."""
        return await self.send(ctx, member, "cry")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def pout(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Pout at someone."""
        return await self.send(ctx, member, "pout")

    @command()
    @cooldown(1, 5, BucketType.member)
    async def handhold(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """Hold hands with someone."""
        return await self.send(ctx, member, "handhold")
