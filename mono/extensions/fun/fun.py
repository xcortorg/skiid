import asyncio
from asyncio import sleep
from io import BytesIO
from random import choice, randint
from typing import Any, Dict, List, Literal, Optional, cast

import config
from core.client.cache.redis import Redis
from core.client.context import Context
from core.Mono import Mono
from core.tools import eightball_responses, plural, valid_flavors
from discord import Embed, File, Member, Message, NotFound, Reaction
from discord.ext.commands import (BucketType, Cog, Range, command, cooldown,
                                  group, max_concurrency)
from discord.ext.commands.context import Context
from loguru import logger
from pydantic import BaseModel
from typing_extensions import Self
from xxhash import xxh64_hexdigest
from yarl import URL

from .views import RPS, TicTacToe


class Blacktea(BaseModel):
    message_id: int
    channel_id: int
    waiting: bool = True
    players: Dict[int, int] = {}
    used_words: List[str] = []

    @staticmethod
    def key(channel_id: int) -> str:
        return xxh64_hexdigest(f"blacktea:{channel_id}")

    @classmethod
    async def get(cls, redis: Redis, channel_id: int) -> Optional[Self]:
        key = cls.key(channel_id)
        data = cast(Optional[Dict[str, Any]], await redis.get(key))
        if not data:
            return

        return cls(**data)

    async def save(self, redis: Redis, **kwargs) -> None:
        key = self.key(self.channel_id)
        await redis.set(key, self.dict(), **kwargs)

    async def delete(self, redis: Redis) -> None:
        key = self.key(self.channel_id)
        await redis.delete(key)


class Fun(Cog):
    def __init__(self, bot: Mono):
        self.bot = bot
        self.words: List[str] = []

    async def cog_load(self) -> None:
        async with self.bot.session.get(
            "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
        ) as resp:
            buffer = await resp.text()
            self.words = buffer.splitlines()

    async def cog_unload(self) -> None:
        self.words = []

    @Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, member: Member) -> None:
        if member.bot or reaction.emoji != "✅":
            return

        session = await Blacktea.get(self.bot.redis, reaction.message.channel.id)
        if (
            not session
            or not session.waiting
            or session.message_id != reaction.message.id
        ):
            return

        if member.id in session.players:
            return

        session.players[member.id] = 2
        await session.save(self.bot.redis)

        embed = Embed(description=f"**{member}** joined the game")
        await reaction.message.reply(embed=embed, delete_after=3)

    @group(invoke_without_command=True)
    async def blacktea(self, ctx: Context) -> Optional[Message]:
        """
        Start a game of Blacktea.
        """

        session = await Blacktea.get(self.bot.redis, ctx.channel.id)
        if session:
            return await ctx.warn("There is already a game in progress.")

        embed = Embed(
            title="Blacktea",
            description="\n> ".join(
                [
                    "React with `🍵` to join the game. The game will start in **30 seconds**",
                    "You'll have **10 seconds** type a word containing the given letters",
                    "The word must be at least **3 letters long** and **not used before**",
                ]
            ),
        )
        message = await ctx.channel.send(embed=embed)

        session = Blacktea(message_id=message.id, channel_id=ctx.channel.id)
        await session.save(self.bot.redis)
        await message.add_reaction("🍵")

        await asyncio.sleep(30)
        session = await Blacktea.get(self.bot.redis, ctx.channel.id)
        if not session or len(session.players) < 2:
            await self.bot.redis.delete(Blacktea.key(ctx.channel.id))
            return await ctx.warn("Not enough players to start the game!")

        session.waiting = False
        await session.save(self.bot.redis, ex=600)

        while True:
            for member_id, lives in list(session.players.items()):
                member = ctx.guild.get_member(member_id)
                if not member:
                    del session.players[member_id]
                    if len(session.players) < 2:
                        await session.delete(self.bot.redis)
                        return await ctx.warn(
                            "Not enough players to continue the game!"
                        )
                    continue

                if len(session.players) == 1:
                    await session.delete(self.bot.redis)
                    return await ctx.approve(f"**{member}** has won the game!")

                letters = choice(
                    [
                        segment.upper()
                        for word in self.words
                        if (segment := word[: round(len(word) / 4)])
                        and len(segment) == 3
                    ]
                )
                embed = Embed(description=f"Type a **word** containing `{letters}`")
                prompt = await ctx.channel.send(content=member.mention, embed=embed)

                for index in range(4):
                    try:
                        message: Message = await self.bot.wait_for(
                            "message",
                            check=lambda m: (
                                m.content
                                and m.channel == ctx.channel
                                and m.author == member
                                and m.content.lower() in self.words
                                and letters.lower() in m.content.lower()
                                and m.content.lower() not in session.used_words
                            ),
                            timeout=(7 if index == 0 else 1),
                        )
                    except asyncio.TimeoutError:
                        if index == 3:
                            lives = session.players[member_id] - 1
                            if not lives:
                                del session.players[member_id]
                                embed = Embed(
                                    description=f"**{member}** has been **eliminated**!"
                                )
                            else:
                                session.players[member_id] = lives
                                embed = Embed(
                                    description="\n> ".join(
                                        [
                                            f"You ran out of time, **{member}**!",
                                            f"You have {plural(lives, md='**'):life|lives} remaining",
                                        ]
                                    )
                                )

                            await ctx.channel.send(embed=embed)
                            break

                        elif index != 0:
                            reactions = {
                                1: "3️⃣",
                                2: "2️⃣",
                                3: "1️⃣",
                            }
                            try:
                                await prompt.add_reaction(reactions[index])
                            except NotFound:
                                pass

                        continue
                    else:
                        await message.add_reaction("✅")
                        session.used_words.append(message.content.lower())
                        break

            if len(session.players) < 2:
                await session.delete(self.bot.redis)
                break

    @command(aliases=["ttt"])
    @max_concurrency(1, BucketType.member)
    async def tictactoe(self, ctx: Context, opponent: Member) -> Message:
        """
        Play Tic Tac Toe with another member.
        """

        if opponent == ctx.author:
            return await ctx.warn("You can't play against **yourself**")

        elif opponent.bot:
            return await ctx.warn("You can't play against **bots**")

        return await TicTacToe(ctx, opponent).start()

    @command()
    @max_concurrency(1, BucketType.member)
    async def rps(self, ctx: Context, opponent: Member) -> Message:
        """
        Play Rock Paper Scissors with another member.
        """

        if opponent == ctx.author:
            return await ctx.warn("You can't play against **yourself**")

        elif opponent.bot:
            return await ctx.warn("You can't play against **bots**")

        return await RPS(ctx, opponent).start()

    @command(aliases=["scrap"])
    async def scrapbook(
        self, ctx: Context, *, text: Range[str, 1, 20]
    ) -> Optional[Message]:
        """
        Create scrapbook letters.
        """
        async with ctx.typing():
            async with self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="api.jeyy.xyz",
                    path="/v2/image/scrapbook",
                ),
                headers={"Authorization": f"Bearer {config.Api.JEYY}"},
                params={"text": text},
            ) as response:
                if not response.ok:
                    return await ctx.warn("Failed to generate the image")

                buffer = await response.read()
                image = BytesIO(buffer)

                await ctx.reply(
                    file=File(image, filename="scrapbook.gif"),
                )

    @command(
        name="coinflip",
        usage="<heads/tails>",
        example="heads",
        aliases=["flipcoin", "cf", "fc"],
    )
    async def coinflip(
        self: "Fun", ctx: Context, *, side: Literal["heads", "tails"] = None
    ):
        """Flip a coin"""
        await ctx.neutral(
            f"Flipping a coin{f' and guessing **:coin: {side}**' if side else ''}.."
        )

        coin = choice(["heads", "tails"])
        await getattr(ctx, ("approve" if (not side or side == coin) else "warn"))(
            f"The coin landed on **:coin: {coin}**"
            + (f", you **{'won' if side == coin else 'lost'}**!" if side else "!")
        )

    @command(
        name="8ball",
        usage="(question)",
        example="am I pretty?",
        aliases=["8b"],
    )
    async def eightball(self, ctx: Context, *, question: str):
        """Ask the magic 8ball a question"""
        await ctx.neutral("Shaking the **magic 8ball**..")

        shakes = randint(1, 5)
        response = choice(list(eightball_responses.keys()))
        await sleep(shakes * 0.5)

        await getattr(ctx, ("approve" if eightball_responses[response] else "warn"))(
            f"The **magic 8ball** says: `{response}` after {plural(shakes):shake} ({question})"
        )

    @command(name="dice", usage="(sides)", example="6", aliases=["dise"])
    async def diceroll(self: "Fun", ctx: Context, sides: int = 6):
        """Roll a dice"""
        await ctx.neutral(f"Rolling a **{sides}** sided dice..")

        await ctx.approve(f"You rolled a **{randint(1, sides)}**")

    @command(
        name="slots",
        aliases=["slot", "spin"],
    )
    @max_concurrency(1, BucketType.member)
    async def slots(self: "Fun", ctx: Context):
        """Play the slot machine"""
        await ctx.neutral("Spinning the **slot machine**..")

        slots = [choice(["🍒", "🍊", "🍋", "🍉", "🍇"]) for _ in range(3)]
        if len(set(slots)) == 1:
            await ctx.approve(
                f"You won the **slot machine**!\n\n `{slots[0]}` `{slots[1]}` `{slots[2]}`"
            )
        else:
            await ctx.warn(
                f"You lost the **slot machine**\n\n `{slots[0]}` `{slots[1]}` `{slots[2]}`"
            )

    @group(
        name="vape",
        aliases=["juul"],
        description="Vape commands.",
        invoke_without_command=True,
    )
    @cooldown(1, 5, BucketType.user)
    async def vape(self, ctx: Context):
        data = await self.bot.db.fetchrow(
            "SELECT * FROM vape WHERE user_id = $1", ctx.author.id
        )

        if data is None:
            return await ctx.warn(
                f"You don't have a **vape**. Use `{ctx.clean_prefix}vape flavor <flavor>` to get a vape."
            )

        flavor = data["flavor"]
        embed = Embed(
            description=f"{config.Emojis.juul} You have a **{flavor}** vape.",
            color=config.Color.base,
        )
        return await ctx.send(embed=embed)

    @vape.command(
        name="flavors", aliases=["flavours"], description="See a list of vape flavors."
    )
    @cooldown(1, 5, BucketType.user)
    async def vape_flavors(self, ctx: Context):
        flavors_list = "\n> ".join(valid_flavors)
        embed = Embed(
            title="Available vape flavors",
            description=f"> {flavors_list}",
            color=config.Color.base,
        )
        return await ctx.reply(embed=embed)

    @vape.command(name="hit", aliases=["smoke"], description="Hit your vape.")
    @cooldown(1, 5, BucketType.user)
    async def vape_hit(self, ctx: Context):
        data = await self.bot.db.fetchrow(
            "SELECT * FROM vape WHERE user_id = $1", ctx.author.id
        )

        if data is None:
            return await ctx.warn(
                f"You don't have a **vape**. Use `{ctx.clean_prefix}vape flavor <flavor>` to get a vape."
            )

        hits = data.get("hits", 0) + 1
        flavor = data.get("flavor", "Unknown")

        try:
            await self.bot.db.execute(
                """
                UPDATE vape
                SET hits = $2
                WHERE user_id = $1
                """,
                ctx.author.id,
                hits,
            )
        except Exception as e:
            logger.error(f"Database error in vape_hit: {e}")
            return await ctx.error("An error occurred while updating your vape data.")

        embed1 = Embed(
            description=f"{config.Emojis.juul} **Hitting your vape..**",
            color=config.Color.base,
        )
        msg = await ctx.send(embed=embed1)

        await asyncio.sleep(1)

        embed = Embed(
            description=f"{config.Emojis.juul} Hit your **{flavor}** vape. You now have **{hits}** hits.",
            color=config.Color.base,
        )
        await msg.edit(embed=embed)

    @vape.command(
        name="flavor", aliases=["flavour", "set"], description="Set your vape flavor"
    )
    @cooldown(1, 5, BucketType.user)
    async def vape_flavor(self, ctx: Context, *, flavor: str = None):
        if flavor is None:
            return await ctx.warn("A flavor is needed.")

        flavor = flavor.title()
        if flavor not in valid_flavors:
            flavors_list = ", ".join(valid_flavors)
            return await ctx.warn(f"Invalid flavor. Valid flavors are: {flavors_list}")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO vape (user_id, flavor, hits)
                VALUES ($1, $2, 0)
                ON CONFLICT (user_id)
                DO UPDATE SET flavor = $2
                """,
                ctx.author.id,
                flavor,
            )
        except Exception as e:
            logger.error(f"Database error in vape_flavor: {e}")
            return await ctx.error("An error occurred while setting your vape flavor.")

        return await ctx.approve(f"Your vape flavor has been set to **{flavor}**.")

    @group(
        name="blunt",
        example="pass fiji",
        aliases=["joint"],
        invoke_without_command=True,
        hidden=False,
    )
    async def blunt(self: "Fun", ctx: Context):
        """Smoke a blunt"""
        await ctx.send_help(ctx.command)

    @blunt.command(
        name="light",
        aliases=["broll"],
        hidden=False,
    )
    async def blunt_light(self: "Fun", ctx: Context):
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if blunt:
            user = ctx.guild.get_member(blunt.get("user_id"))
            return await ctx.error(
                f"A **blunt** is already held by **{user or blunt.get('user_id')}**\n> It has been hit"
                f" {plural(blunt.get('hits')):time} by {plural(blunt.get('members')):member}",
            )

        try:
            await self.bot.db.execute(
                "INSERT INTO blunt (guild_id, user_id) VALUES($1, $2)",
                ctx.guild.id,
                ctx.author.id,
            )
        except Exception as e:
            logger.error(f"Database error in blunt_light: {e}")
            return await ctx.error("An error occurred while lighting the blunt.")

        await ctx.neutral("Rolling the **blunt**..", emoji="🚬")
        await sleep(2)
        await ctx.approve(
            f"🚬 Lit up a **blunt**\n> Use `{ctx.prefix}blunt hit` to smoke it"
        )

    @blunt.command(
        name="pass",
        example="fiji",
        aliases=["give"],
        hidden=False,
    )
    async def blunt_pass(self: "Fun", ctx: Context, *, member: Member):
        """Pass the blunt to another member"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not blunt:
            return await ctx.warn(
                f"There is no **blunt** to pass\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        if blunt.get("user_id") != ctx.author.id:
            member = ctx.guild.get_member(blunt.get("user_id"))
            return await ctx.warn(
                f"You don't have the **blunt**!\n> Steal it from **{member or blunt.get('user_id')}** first"
            )
        if member == ctx.author:
            return await ctx.warn("You can't pass the **blunt** to **yourself**")

        try:
            await self.bot.db.execute(
                "UPDATE blunt SET user_id = $2, passes = passes + 1 WHERE guild_id = $1",
                ctx.guild.id,
                member.id,
            )
        except Exception as e:
            logger.error(f"Database error in blunt_pass: {e}")
            return await ctx.error("An error occurred while passing the blunt.")

        await ctx.approve(
            f"🚬 The **blunt** has been passed to **{member}**!\n> It has been passed around"
            f" **{plural(blunt.get('passes') + 1):time}**"
        )

    @blunt.command(
        name="steal",
        aliases=["take"],
        hidden=False,
    )
    @cooldown(1, 5, BucketType.member)
    async def blunt_steal(self: "Fun", ctx: Context):
        """Steal the blunt from another member"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not blunt:
            return await ctx.error(
                f"There is no **blunt** to steal\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        if blunt.get("user_id") == ctx.author.id:
            return await ctx.error(
                f"You already have the **blunt**!\n> Use `{ctx.prefix}blunt pass` to pass it to someone else"
            )

        member = ctx.guild.get_member(blunt.get("user_id"))

        if randint(1, 100) <= 50:
            return await ctx.error(
                f"**{member or blunt.get('user_id')}** is hogging the **blunt**!"
            )

        try:
            await self.bot.db.execute(
                "UPDATE blunt SET user_id = $2 WHERE guild_id = $1",
                ctx.guild.id,
                ctx.author.id,
            )
        except Exception as e:
            logger.error(f"Database error in blunt_steal: {e}")
            return await ctx.error("An error occurred while stealing the blunt.")

        await ctx.approve(
            f"You just stole the **blunt** from **{member or blunt.get('user_id')}**!",
            emoji="🚬",
        )

    @blunt.command(
        name="hit",
        aliases=["smoke", "chief"],
        hidden=False,
    )
    @max_concurrency(1, BucketType.guild)
    async def blunt_hit(self: "Fun", ctx: Context):
        """Hit the blunt"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not blunt:
            return await ctx.error(
                f"There is no **blunt** to hit\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        if blunt.get("user_id") != ctx.author.id:
            member = ctx.guild.get_member(blunt.get("user_id"))
            return await ctx.error(
                f"You don't have the **blunt**!\n> Steal it from **{member or blunt.get('user_id')}** first"
            )

        members = blunt.get("members", [])
        if ctx.author.id not in members:
            members.append(ctx.author.id)

        loading_message = await ctx.neutral("Hitting the **blunt**.. 🚬")
        async with ctx.typing():
            await sleep(randint(1, 2))

            if blunt["hits"] + 1 >= 10 and randint(1, 100) <= 25:
                try:
                    await self.bot.db.execute(
                        "DELETE FROM blunt WHERE guild_id = $1",
                        ctx.guild.id,
                    )
                except Exception as e:
                    logger.error(f"Database error in blunt_hit (delete): {e}")
                    return await ctx.error(
                        "An error occurred while updating the blunt data."
                    )

                error_embed = Embed(
                    description=f"The **blunt** burned out after {plural(blunt.get('hits') + 1):hit} by"
                    f" **{plural(len(members)):member}**",
                    color=config.Color.deny,
                )
                await loading_message.edit(embed=error_embed)
                return

            try:
                await self.bot.db.execute(
                    "UPDATE blunt SET hits = hits + 1, members = $2 WHERE guild_id = $1",
                    ctx.guild.id,
                    members,
                )
            except Exception as e:
                logger.error(f"Database error in blunt_hit (update): {e}")
                return await ctx.error(
                    "An error occurred while updating the blunt data."
                )

        approve_embed = Embed(
            description=f"You just hit the **blunt**! 🚬 \n> It has been hit **{plural(blunt.get('hits') + 1):time}** by"
            f" **{plural(len(members)):member}**",
            color=config.Color.approve,
        )
        await loading_message.edit(embed=approve_embed)
