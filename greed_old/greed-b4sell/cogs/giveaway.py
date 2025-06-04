from discord import Message, Guild, Object
from discord.ext.commands import Context, Cog, has_permissions
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import humanfriendly
import random
import discord
from logging import getLogger
from typing import Optional, Union
from tool.views import GiveawayView
from tool.important.subclasses.command import Role
from asyncio import gather, Lock
from async_timeout import timeout
from tools import ratelimit
from tool.important.subclasses.parser import Script
import traceback
from collections import defaultdict

logger = getLogger(__name__)


def get_tb(error: Exception):
    return "".join(traceback.format_exception(type(error), error, error.__traceback__))


class Giveaway(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaway_loop.start()
        self.cleanup_loop.start()
        self.entry_updating = False
        self.locks = defaultdict(Lock)

    def cog_unload(self):
        self.giveaway_loop.cancel()
        self.cleanup_loop.cancel()

    @commands.hybrid_group(name="giveaway", aliases=["gw"], invoke_without_command=True)
    async def giveaway(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @giveaway.command(
        name="blacklist",
        brief="Blacklist a role from entering giveaways",
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
                """INSERT INTO giveaway_blacklist (guild_id, role_id) VALUES($1, $2) ON CONFLICT(guild_id, role_id) DO NOTHING""",
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
        try:
            converted = humanfriendly.parse_timespan(timeframe)
        except Exception:
            converted = humanfriendly.parse_timespan(
                f"{await self.get_int(timeframe)} hours"
            )
        time = datetime.now() + timedelta(seconds=converted)
        return time

    async def get_winners(self, entries: list, amount: int):
        """Properly weighted entry system"""
        weighted_entries = []
        for entry in entries:
            weighted_entries.extend([entry["user_id"]] * entry["entry_count"])

        if not weighted_entries:
            return []

        if amount >= len(weighted_entries):
            return list(set(weighted_entries))

        return random.sample(weighted_entries, amount)

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
    ):
        _creator = self.bot.get_user(creator)
        embed = discord.Embed(
            title="Giveaway Ended", description=f"**Prize**: {prize}\n**Winners**:\n"
        )
        desc = ""
        for i, winner in enumerate(winner_objects, start=1):
            desc += f"`{i}` {winner.mention}\n"
        if desc == "":
            desc += "**No one entered**"
        embed.description += desc
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
                    await _creator.send(content=content, embed=embed)
                except Exception:
                    pass
            if config["dm_winners"] is True:

                @ratelimit("dms", 30, 59, True)
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
            code = code.replace("{prize}", prize)
            code = code.replace("{ends}", discord.utils.format_dt(end_time, style="R"))
            script = Script(code, creator)
            await script.compile()
            embed = script.data
        else:
            ends_timestamps = f"{self.bot.get_timestamp(end_time)} ({self.bot.get_timestamp(end_time, 'f')})"
            embed = discord.Embed(
                title=prize,
                description=f"**Winners:** {winners}\n**Ends:** {ends_timestamps}",
                color=0x2F3136,
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

    async def end_giveaway(self, message: Message, winners: int, prize: str):
        """Handle giveaway ending with proper data preservation"""
        await self.bot.db.execute(
            """INSERT INTO ended_giveaways 
            (guild_id, message_id, channel_id, prize, winner_count, creator_id, ended_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            message.guild.id,
            message.id,
            message.channel.id,
            prize,
            winners,
            await self.get_creator_id(message.id),
            datetime.now(),
        )

        embed = discord.Embed(
            title="<:giveaway:1356908120273588265> Giveaway Ended",
            description=f"**Prize:** {prize}\n**Winners:** {winners}",
            color=0x2F3136,
        )
        await message.edit(embed=embed, view=None)

    async def get_creator_id(self, message_id: int):
        return await self.bot.db.fetchval(
            "SELECT creator FROM gw WHERE message_id = $1", message_id
        )

    @tasks.loop(minutes=5)
    async def cleanup_loop(self):
        """Clean up old giveaways and their entries after 5 days"""
        five_days_ago = datetime.now() - timedelta(days=5)

        old_giveaways = await self.bot.db.fetch(
            """SELECT guild_id, message_id FROM ended_giveaways 
            WHERE ended_at < $1""",
            five_days_ago,
        )

        for gw in old_giveaways:
            await self.bot.db.execute(
                """DELETE FROM giveaway_entries 
                WHERE guild_id = $1 AND message_id = $2""",
                gw["guild_id"],
                gw["message_id"],
            )

            await self.bot.db.execute(
                """DELETE FROM ended_giveaways 
                WHERE guild_id = $1 AND message_id = $2""",
                gw["guild_id"],
                gw["message_id"],
            )

    @tasks.loop(minutes=1)
    async def giveaway_loop(self):
        try:
            await self.do_gw()
        except Exception as e:
            self.bot.gwtb = e
            logger.info(f"Uncaught exception in giveaway loop: {get_tb(e)}")

    async def do_gw(self):
        async with self.locks["gw"]:
            active_giveaways = await self.bot.db.fetch(
                """SELECT * FROM gw WHERE ex < NOW()"""
            )

            for gw in active_giveaways:
                guild = self.bot.get_guild(gw["guild_id"])
                if not guild:
                    continue

                channel = guild.get_channel(gw["channel_id"])
                if not channel:
                    continue

                try:
                    message = await channel.fetch_message(gw["message_id"])
                    prize = gw["prize"]
                except:
                    continue

                entries = await self.bot.db.fetch(
                    """SELECT user_id, entry_count FROM giveaway_entries 
                    WHERE guild_id = $1 AND message_id = $2""",
                    guild.id,
                    message.id,
                )

                winners = await self.get_winners(entries, gw["winner_count"])
                winner_objects = [
                    guild.get_member(w) for w in winners if guild.get_member(w)
                ]

                embed = discord.Embed(
                    title=f"<:giveaway:1356908120273588265> Giveaway Ended: {prize}",
                    description="**Winners**\n"
                    + "\n".join(
                        [f"{i+1}. {w.mention}" for i, w in enumerate(winner_objects)]
                        or ["No valid winners"]
                    ),
                    color=0x2F3136,
                )

                try:
                    await channel.send(
                        content=(
                            f"Congratulations {' '.join([w.mention for w in winner_objects])}!"
                            if winner_objects
                            else ""
                        ),
                        embed=embed,
                    )
                except discord.HTTPException:
                    pass

                await self.end_giveaway(message, gw["winner_count"], prize)
                await self.bot.db.execute(
                    """DELETE FROM gw WHERE message_id = $1""", message.id
                )

    @giveaway.command(
        name="start",
        aliases=["create"],
        brief="Create a giveaway",
        example=",giveaway start 1h 1 $10",
    )
    @has_permissions(manage_guild=True)
    async def giveaway_start(
        self, ctx: Context, duration: str, winners: int = 1, *, prize: str
    ):
        end_time = await self.get_timeframe(duration)
        message = await ctx.send("Starting giveaway...", view=GiveawayView())

        await self.bot.db.execute(
            """INSERT INTO gw 
            (guild_id, channel_id, message_id, ex, creator, winner_count, prize) 
            VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            ctx.guild.id,
            ctx.channel.id,
            message.id,
            end_time,
            ctx.author.id,
            winners,
            prize,
        )

        embed = await self.get_message(
            ctx.guild, prize, end_time, winners, ctx.author, message
        )
        await message.edit(**embed)
        await ctx.success("Giveaway started successfully!")

    @giveaway.command(
        name="reroll",
        brief="Reroll giveaway winners",
        example=",giveaway reroll 1234567890",
    )
    @has_permissions(manage_guild=True)
    async def reroll(self, ctx: Context, message_id: int):
        """Reroll winners for an ended giveaway"""
        ended_gw = await self.bot.db.fetchrow(
            """SELECT * FROM ended_giveaways 
            WHERE guild_id = $1 AND message_id = $2""",
            ctx.guild.id,
            message_id,
        )

        if not ended_gw:
            return await ctx.fail("No ended giveaway found with that message ID.")

        entries = await self.bot.db.fetch(
            """SELECT user_id, entry_count FROM giveaway_entries 
            WHERE guild_id = $1 AND message_id = $2""",
            ctx.guild.id,
            message_id,
        )

        if not entries:
            return await ctx.fail("No entries found for this giveaway.")

        winners = await self.get_winners(entries, ended_gw["winner_count"])
        winners = [winners] if not isinstance(winners, list) else winners

        winner_objects = []
        for w in winners:
            if member := ctx.guild.get_member(w):
                winner_objects.append(member)

        if not winner_objects:
            return await ctx.fail("No valid winners found.")

        embed = discord.Embed(
            title=f"<:giveaway:1356908120273588265> Reroll: {ended_gw['prize']}",
            description="**New Winners**\n"
            + "\n".join([f"{i+1}. {w.mention}" for i, w in enumerate(winner_objects)]),
            color=0x2F3136,
        )

        channel = ctx.guild.get_channel(ended_gw["channel_id"])
        if channel:
            try:
                await channel.send(
                    content=f"New winners: {' '.join([w.mention for w in winner_objects])}",
                    embed=embed,
                )
                await ctx.success("Successfully rerolled winners!")
            except discord.HTTPException as e:
                await ctx.fail(f"Failed to send reroll message: {e}")
        else:
            await ctx.fail("Original channel not found.")

    @giveaway.command(
        name="end",
        brief="End a specific giveaway from that giveaway message",
        aliases=["stop"],
        example=",giveaway end 1234567890",
    )
    @has_permissions(manage_guild=True)
    async def giveaway_end(self, ctx: Context, message_id: Optional[int] = None):
        data = await self.bot.db.fetch(
            """SELECT * FROM gw WHERE guild_id = $1""", ctx.guild.id
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
                """UPDATE gw SET ex = $1 WHERE guild_id = $2 AND message_id = $3""",
                datetime.now(),
                ctx.guild.id,
                message_id,
            )
        except Exception:
            return await ctx.fail(f"**No giveaway found** under `{message_id}`")
        return await ctx.success("**Giveaway will end in a few moments!**")

    @giveaway.command(
        name="dmcreator",
        brief="Dm the creator when the giveaway has ended of the winner(s)",
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
        brief="dm the winners when the giveaway has ended",
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
