import random
import traceback
from asyncio import gather
from datetime import datetime, timedelta  # type: ignore
from typing import Optional, Union

import discord  # type: ignore # type: ignore
import humanfriendly
from discord import Guild  # type: ignore # type: ignore # type: ignore
from discord.ext import commands, tasks
from discord.ext.commands import (Cog, Context,  # type: ignore # type: ignore
                                  has_permissions)
from loguru import logger
from rival_tools import ratelimit, thread  # type: ignore
from tools.important.subclasses.command import Role  # type: ignore
from tools.important.subclasses.parser import Script  # type: ignore
from tools.views import GiveawayView  # type: ignore


def get_tb(error: Exception):
    _ = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    return _


class Giveaway(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaway_loop.start()
        self.entry_updating = False

    @commands.group(name="giveaway")
    async def giveaway(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command)

    @giveaway.command(
        name="blacklist",
        brief="blacklist a role from entering in givaways",
        example=",giveaway blacklist @members",
    )
    @has_permissions(manage_guilds=True)
    async def giveaway_blacklist(self, ctx: Context, *, role: Role):
        role = role[0]
        if await self.bot.db.fetchrow(
            """SELECT * FROM giveaway_blacklist WHERE guild_id = $1 AND role_id = $2""",
            ctx.guild.id,
            role.id,
        ):
            await self.bot.db.execute(
                """DELETE FROM giveaway_blacklist WHERE guild_id = $1 AND role_id = $2""",
                ctx.guild.id,
                role.id,
            )
            m = f"**Unblacklisted** users with {role.mention} and can now **enter giveaways**"
        else:
            await self.bot.db.execute(
                """INSERT INTO giveaway_blacklist (guild_id, role_id) VALUES($1, $2) ON CONFLICT(guild_id, role_id)""",
                ctx.guild.id,
                role.id,
            )
            m = f"**Blacklisted** users with {role.mention} role from **entering giveaways**"
        return await ctx.success(m)

    async def get_int(self, string: str):
        t = ""
        for s in string:
            try:
                d = int(s)
                t += f"{d}"
            except Exception:
                pass
        return t

    async def get_timeframe(self, timeframe: str):
        from datetime import datetime

        try:
            converted = humanfriendly.parse_timespan(timeframe)
        except Exception:
            converted = humanfriendly.parse_timespan(
                f"{await self.get_int(timeframe)} hours"
            )
        time = datetime.now() + timedelta(seconds=converted)  # noqa: F821
        return time

    @thread
    def get_winners_(self, entries: list, amount: int):
        w = set()
        while len(w) < amount:
            _ = random.choice(entries)
            if _ not in w:
                w.add(_)
        return list(w)

    async def get_winners(self, entries: list, amount: int):
        _ = []
        for e in entries:
            _.extend([e["user_id"] * e["entry_count"]])
        if amount > 1:
            winners = await self.get_winners_(_, amount)
            return winners
        else:
            return random.choice(_)

    async def get_config(
        self,
        guild: Guild,
        prize: str,
        message_id: int,
        winners: str,
        winners_str: str,
        winner_objects: list,
        creator: int,
        ends: datetime,
    ):  # type: ignore # type: ignore # type: ignore
        _creator = self.bot.get_user(creator)  # type: ignore
        embed = discord.Embed(
            title="Giveaway Ended", description=f"**Prize**: {prize}\n**Winners**:\n"
        )
        for i, winner in enumerate(winner_objects, start=1):
            embed.description += f"`{i}` {winner.mention}\n"
        content = winners
        logger.info(embed.description)
        self.bot.gwdesc = embed.description

        async def get_cfg(guild: Guild):
            if cfg := await self.bot.db.fetchrow(
                """SELECT * FROM giveaway_config WHERE guild_id = $1""", guild.id
            ):
                return cfg
            else:
                return {"guild_id": guild.id, "dm_creator": False, "dm_winners": False}

        config = await get_cfg(guild)
        if winners is not None:
            if config["dm_creator"] is True:
                try:
                    await creator.send(content=content, embed=embed)
                except Exception:
                    pass
            if config["dm_winners"] is True:

                @ratelimit(30, 59, True)
                async def dm_winner(w: discord.Member):
                    try:
                        await w.send(content=content, embed=embed)
                    except Exception:
                        pass

                for w in winner_objects:
                    await dm_winner(w)
        return {"embed": embed, "content": content}

    async def get_message(
        self,
        guild: Guild,
        prize: str,
        end_time: datetime,
        winners: int,
        creator: discord.Member,
        message: discord.Message,
    ):
        if template := await self.bot.db.fetchrow(
            """SELECT * FROM giveaway_templates WHERE guild_id = $1""", guild.id
        ):
            code = template["code"]
            code = code.replace(
                "{timer}", f"https://wock.bot/giveaway/{guild.id}/{message.id}"
            )
            code = code.replace("{prize}", prize)
            code = code.replace("{ends}", discord.utils.format_dt(end_time, style="R"))
            # code = code.replace("{winners.simple}", ", ", winners)
            # code = code.replace("{winners.numbered}", winners_str)
            script = Script(code, creator)
            await script.compile()
            embed = script.data
        else:
            ends_timestamps = f"{self.bot.get_timestamp(end_time)} ({self.bot.get_timestamp(end_time, 'f')})"
            embed = discord.Embed(
                title=prize,
                description=f"**Winners:** {winners}\n**Ends:** {ends_timestamps}",
                color=0x2F3136,
                url=f"https://wock.bot/giveaway/{guild.id}/{message.id}",
            )
            embed.set_footer(text=f"hosted by {str(creator)}")
            embed = {"embed": embed, "content": None}
        return embed

    async def fetch_message(
        self, guild: Union[int, discord.Guild], channel_id: int, message_id: int
    ) -> Optional[discord.Message]:
        if isinstance(guild, int):
            guild = self.bot.get_guild(guild)
            if not guild:
                return
        message = None
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        try:
            message = await channel.fetch_message(message_id)
        except Exception:
            pass
        return message

    async def giveaway_loop_(self):
        try:  # with logger.catch():
            return await self.do_gw()
        except Exception as e:
            tb = get_tb(e)
            self.bot.gwtb = tb
            logger.info(f"Uncaught exception in giveaway loop: {tb}")

    async def do_gw(self):
        for gw in await self.bot.db.fetch(
            """SELECT guild_id, channel_id, message_id, expiration, creator, winner_count FROM giveaways"""
        ):
            is_fetched = False
            if guild := self.bot.get_guild(int(gw.guild_id)):
                message = None
                if gw.expiration.timestamp() < datetime.now().timestamp():
                    await self.bot.db.execute(
                        """DELETE FROM giveaways WHERE guild_id = $1 AND message_id = $2""",
                        gw.guild_id,
                        gw.message_id,
                    )
                    entries = await self.bot.db.fetch(
                        """SELECT user_id, entry_count FROM giveaway_entries WHERE guild_id = $1 AND message_id = $2""",
                        gw.guild_id,
                        gw.message_id,
                    )
                    if channel := guild.get_channel(int(gw.channel_id)):
                        message = await self.fetch_message(
                            channel.guild, channel.id, int(gw.message_id)
                        )
                        is_fetched = True
                        try:
                            prize = message.embeds[0].title
                        except Exception:
                            await self.bot.db.execute(
                                """DELETE FROM giveaways WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""",
                                gw.guild_id,
                                gw.channel_id,
                                gw.message_id,
                            )
                            continue
                        content = ""
                        desc = ""
                        d = ""
                        if entries:
                            winners = await self.get_winners(entries, gw.winner_count)
                            if isinstance(winners, list):
                                winner_objects = [
                                    guild.get_member(m)
                                    for m in winners
                                    if guild.get_member(m) is not None
                                ]
                                for i, winner in enumerate(winners, start=1):
                                    user = guild.get_member(winner)
                                    content += f"{user.mention} "
                                    if i == 1:
                                        d += f"{user.mention}"
                                        desc += f"`{i}` {user.mention}\n"
                                    elif i == gw.winner_count:
                                        desc += f"`{i}` {user.mention}\n"
                                        d += f", {user.mention}"
                                    else:
                                        desc += f"`{i}` {user.mention}\n"
                                        d += f", {user.mention}"
                            else:
                                user = guild.get_member(winners)
                                winner_objects = [user]

                                desc += f"`1` {user.mention}"
                                d += f"{user.mention}"
                            embed = await self.get_config(
                                guild,
                                prize,
                                gw.message_id,
                                d,
                                desc,
                                winner_objects,
                                gw.creator,
                                gw.expiration,
                            )
                        else:
                            embed["embed"].description += "**No one entered**"
                        await channel.send(**embed)
                        await self.bot.db.execute(
                            """DELETE FROM giveaway_entries WHERE guild_id = $1 AND message_id = $2""",
                            gw.guild_id,
                            gw.message_id,
                        )
                    else:
                        tasks = [
                            self.bot.db.execute(
                                """DELETE FROM giveaways WHERE guild_id = $1""",
                                gw.guild_id,
                            ),
                            self.bot.db.execute(
                                """DELETE FROM giveaway_entries WHERE guild_id = $1""",
                                gw.guild_id,
                            ),
                            self.bot.db.execute(
                                """DELETE FROM giveaway_settings WHERE guild_id = $1""",
                                gw.guild_id,
                            ),
                        ]
                        await gather(*tasks)
                else:
                    if self.entry_updating is True:
                        if is_fetched is False:
                            message = await self.fetch_message(
                                int(gw.guild_id), int(gw.channel_id), int(gw.message_id)
                            )
                        if message:
                            if (
                                await self.bot.glory_cache.ratelimited(
                                    f"gw_edit:{gw.message_id}", 1, 120
                                )
                                == 0
                            ):
                                embed = message.embeds[0]
                                description = embed.description
                                desc = ""
                                entry_count = await self.bot.db.fetchval(
                                    """SELECT COUNT(*) FROM giveaway_entries WHERE guild_id = $1 AND message_id = $2""",
                                    gw.guild_id,
                                    gw.message_id,
                                )
                                if "Entries" in description:
                                    line = [
                                        l
                                        for l in description.splitlines()
                                        if "Entries" in l
                                    ][
                                        0
                                    ]  # noqa: E741
                                    count = int("".join(m for m in line if m.isdigit()))
                                    if count != entry_count:
                                        for i, line in enumerate(
                                            embed.description.splitlines(), start=0
                                        ):
                                            if "Entries" in line:

                                                line = f"**Entries:** `{entry_count}`"
                                            if i == len(description.splitlines()):
                                                desc += f"{line}"
                                            else:
                                                desc += f"{line}\n"
                                        embed.description = desc
                                        await message.edit(embed=embed)

            else:
                tasks = [
                    self.bot.db.execute(
                        """DELETE FROM giveaways WHERE guild_id = $1""", gw.guild_id
                    ),
                    self.bot.db.execute(
                        """DELETE FROM giveaway_entries WHERE guild_id = $1""",
                        gw.guild_id,
                    ),
                    self.bot.db.execute(
                        """DELETE FROM giveaway_settings WHERE guild_id = $1""",
                        gw.guild_id,
                    ),
                ]
                await gather(*tasks)

    @tasks.loop(seconds=15)
    async def giveaway_loop(self):
        try:
            return await self.giveaway_loop_()
        except Exception as e:
            logger.info(e)
            raise e

    @giveaway.command(
        name="start",
        brief="Create a giveaway for a users to join and win from once the time ends",
        example=",giveaway start nitro --time 5minutes --winners 3",
        parameters={
            "winners": {
                "converter": int,
                "description": "The amount of winners",
            },
            "winner": {
                "converter": int,
                "description": "The amount of winners",
            },
            "timeframe": {
                "converter": str,
                "description": "The amount of time for the giveaway to run for",
            },
            "time": {
                "converter": str,
                "description": "The amount of time for the giveaway to run for",
            },
        },
    )
    @has_permissions(manage_guild=True)
    async def giveaway_start(self, ctx: Context, prize: str):
        self.bot.gwctx = ctx
        winners = ctx.parameters.get("winners") or ctx.parameters.get("winner") or 1
        timeframe = (
            ctx.parameters.get("timeframe") or ctx.parameters.get("time") or "24h"
        )
        end_time = await self.get_timeframe(timeframe)
        message = await ctx.send(content="sup", view=GiveawayView())
        embed = await self.get_message(
            ctx.guild, prize, end_time, winners, ctx.author, message
        )
        try:
            embed.pop("view")
        except Exception:
            pass
        try:
            embed.pop("files")
        except Exception:
            pass
        await message.edit(**embed)
        await self.bot.db.execute(
            """INSERT INTO giveaways (guild_id, channel_id, message_id, expiration, creator, winner_count) VALUES($1, $2, $3, $4, $5, $6) ON CONFLICT(guild_id, message_id) DO NOTHING""",
            ctx.guild.id,
            ctx.channel.id,
            message.id,
            end_time,
            ctx.author.id,
            winners,
        )

    @giveaway.command(
        name="end",
        brief="End a specific giveaway from that giveaway message",
        example=",giveaway end 1234567890",
    )
    @has_permissions(manage_guild=True)
    async def giveaway_end(self, ctx: Context, message_id: Optional[int] = None):
        data = await self.bot.db.fetch(
            """SELECT * FROM giveaways WHERE guild_id = $1""", ctx.guild.id
        )
        if len(data) == 0:
            return await ctx.fail("**no giveaway found**")
        if len(data) == 1:
            message_id = data[0].message_id
        if message_id is None:
            if ctx.message.reference:
                message_id = ctx.message.reference.message_id
        if message_id is None:
            return await ctx.fail("please include the message id of the giveaway")

        try:
            await self.bot.db.execute(
                """UPDATE giveaways SET expiration = $1 WHERE guild_id = $2 AND message_id = $3""",
                datetime.now(),
                ctx.guild.id,
                message_id,
            )
        except Exception:
            return await ctx.fail(f"**No giveaway found** under `{message_id}`")
        return await ctx.success("**Giveaway will end in a few moments!**")

    @giveaway.command(
        name="dmcreator",
        brief="Dm the creator when the giveaway has ended of the winners",
        example=",giveaway dmcreator true",
    )
    @has_permissions(manage_guild=True)
    async def giveaway_dmcreator(self, ctx: Context, state: bool):
        await self.bot.db.execute(
            """INSERT INTO giveaway_config (guild_id, dm_creator, dm_winners) VALUES($1, $2, $3) ON CONFLICT(guild_id) DO UPDATE SET dm_creator = excluded.dm_creator""",
            ctx.guild.id,
            state,
            False,
        )
        return await ctx.success(f"**Dmcreator** is now set to `{state}`")

    @giveaway.command(
        name="dmwinners",
        aliases=["dmwinner"],
        brief="dm the creator when the giveaway has ended of the winners",
        example=",giveaway dmwinners true",
    )
    @has_permissions(manage_guild=True)
    async def giveaway_dmwinner(self, ctx: Context, state: bool):
        await self.bot.db.execute(
            """INSERT INTO giveaway_config (guild_id, dm_creator, dm_winners) VALUES($1, $2, $3) ON CONFLICT(guild_id) DO UPDATE SET dm_winners = excluded.dm_winners""",
            ctx.guild.id,
            False,
            state,
        )
        return await ctx.success(f"**DmWinners** is now set to `{state}`")

    @giveaway.command(
        name="template",
        brief="set your default embed template for giveaways",
        example=",giveaway template [embed_code]",
    )
    @has_permissions(manage_guild=True)
    async def giveaway_template(self, ctx: Context, *, template: Optional[str] = None):
        if template is None:
            await self.bot.db.execute(
                """DELETE FROM giveaway_templates WHERE guild_id = $1""", ctx.guild.id
            )
            m = "**Giveaway template** has been cleared"
        else:
            # do test embed creation here to validate it
            await self.bot.db.execute(
                """INSERT INTO giveaway_templates (guild_id, code) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET code = excluded.code""",
                ctx.guild.id,
                template,
            )
            m = "Giveaway template** is now set to the **embed code provided**"
        return await ctx.success(m)

    @giveaway.command(
        name="setmax",
        brief="Set a max entrie count users with a specific role",
        aliases=["max"],
        example=",giveaway setmax 100",
    )
    @has_permissions(manage_roles=True)
    async def giveaway_setmax(self, ctx: Context, max: int, *, role: Role):
        role = role[0]
        await self.bot.db.execute(
            """INSERT INTO giveaway_settings (guild_id, role_id, entries) VALUES($1, $2, $3) ON CONFLICT(guild_id, role_id) DO UPDATE SET entries = excluded.entries""",
            ctx.guild.id,
            role.id,
            max,
        )
        return await ctx.success(
            f"{role.mention}'s **max entries** set to `{max}` for **entering giveaways**"
        )


async def setup(bot):
    await bot.add_cog(Giveaway(bot))
