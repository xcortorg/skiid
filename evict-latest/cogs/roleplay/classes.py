import config
import discord
import random

from io import BytesIO
from typing import Union, Optional
from discord import Member, User, Message, Embed
from discord.ext.commands import parameter
from aiohttp import ClientSession, TCPConnector
from yarl import URL
from typing import cast
from tools.utilities.humanize import ordinal
from core.client.context import Context


from logging import getLogger

log = getLogger("evict/roleplay")

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
    "shoot": "shot",
    "sleep": "sleeps with",
    "shrug": "shrugs at",
    "stare": "stares at",
    "wave": "waves at",
    "smile": "smiles at",
    "peck": "pecked",
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

BASE_URL = URL.build(
    scheme="https",
    host="nekos.best",
)

class RoleplayContext:

    async def dm(self, ctx: Context, category: str, member: Union[Member, User, None] = parameter(
                default=lambda ctx: ctx.author
            )) -> Message:
            """
            Requests the API for User Apps,
            proxies the request,
            and structures the embed.
            """
            # amount = 0
            # if member != ctx.author:
            #     amount = cast(
            #         int,
            #         await self.bot.db.fetchval(
            #             """
            #             INSERT INTO roleplay (user_id, target_id, category)
            #             VALUES ($1, $2, $3)
            #             ON CONFLICT (user_id, target_id, category)
            #             DO UPDATE SET amount = roleplay.amount + 1
            #             RETURNING amount
            #             """,
            #             ctx.author.id,
            #             member.id,
            #             category,
            #         ),
            #     )

            gif_url = f"https://nekos.best/api/v2/{category}"
            async with self.bot.session.get(gif_url, proxy=config.CLIENT.WARP) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        gif_url = data["results"][0]["url"]
            
            embed = Embed(
                description=f"**{ctx.author.mention}** just {ACTIONS[category]} {f'**{str(member.mention)}**' if member else 'themselves'}"
            #     + (
            #         f" for the **{ordinal(amount)}** time"
            #         if member != ctx.author and amount
            #         else " ... kinky"
            #     )
            )
            
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)

            if isinstance(ctx.channel, discord.DMChannel):
                try:
                    async with self.bot.session.get(gif_url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            file = discord.File(BytesIO(data), filename=f"{category}.gif")
                            embed.set_image(url=f"attachment://{category}.gif")
                            return await ctx.send(file=file, embed=embed)
                
                except Exception as e:
                    log.error(f"Failed to send pat gif in DM: {e}")
                    
            embed.set_image(url=gif_url)
            return await ctx.send(embed=embed)

    async def send(self, ctx: Context, member: Optional[Member], category: str) -> Message:
            """
            Requests the API,
            proxies the request,
            and structures the embed.
            """

            key = f"roleplay_limit:{ctx.author.id}"
            notify_key = f"roleplay_notify:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            
            if uses and int(uses) >= 15:
                if not await self.bot.redis.exists(notify_key):
                    log.info(
                        f"Roleplay ratelimited: {ctx.author} ({ctx.author.id}) in {ctx.guild.name if ctx.guild else 'DM'}"
                    )
                    if not ctx.interaction:
                        await ctx.message.add_reaction("⏰")
                    else:
                        await ctx.warn("You can only use roleplay commands 15 times per minute.")
                    
                    await self.bot.redis.set(notify_key, "1", ex=60)  
                return
                    
            pipe = self.bot.redis.pipeline()
            pipe.incr(key)
            if not uses:
                pipe.expire(key, 60)
            await pipe.execute()

            url = BASE_URL.with_path(f"/api/v2/{category}")

            async with ctx.typing():
                connector = TCPConnector()

                async with ClientSession(connector=connector) as session:
                    async with session.get(url, proxy=config.CLIENT.WARP) as response:
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
                                f"{ctx.author.mention} just {ACTIONS[category]} {member.mention}"
                                + (
                                    f" for the **{ordinal(amount)}** time"
                                    if member != ctx.author and amount
                                    else ""
                                )
                            )

                        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
                        embed.set_image(url=data["results"][0]["url"])

                        # Attempt to send the message and handle potential errors
                        try:
                            return await ctx.send(embed=embed)
                        except discord.Forbidden:
                            return await ctx.warn("I cannot send you a DM. Please check your privacy settings.")
                        except Exception as e:
                            log.error(f"An error occurred while sending the message: {e}")
                            return await ctx.warn("An unexpected error occurred. Please try again later.")
        
    async def cdn(self, ctx: Context, category: str, max:int, member: Union[Member, User, None] = parameter(
                default=lambda ctx: ctx.author)) -> Message:
            """
            Requests the API for Evicts' CDN
            and structures the embed.
            """             
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

            images = f"https://r2.evict.bot/roleplay/{category}/{category}{random.randint(1, max)}.gif"
            embed = Embed(
                    description=f"**{ctx.author.mention}** just killed {f'**{str(member.mention)}**' if member else 'themselves'}"
                    + (
                        f" for the **{ordinal(amount)}** time"
                        if member != ctx.author and amount
                        else " ... kinky"
                    )
                )
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
            embed.set_image(url=images)

            return await ctx.send(embed=embed)