import discord
import humanfriendly
from asyncio import gather
from discord.ext import commands
from tool.important import Context  # type: ignore
from typing import Union  # type: ignore
from discord import Guild
from tool.greed import Greed  # type: ignore
from tool.emotes import EMOJIS

TUPLE = ()
DICT = {}

default_timeout = 20


class Automod(commands.Cog):
    def __init__(self: "Automod", bot: Greed):
        self.bot = bot

    async def check_setup(self, guild: Guild) -> bool:
        if not await self.bot.db.fetchrow(
            """SELECT * FROM filter_setup WHERE guild_id = $1""", guild.id
        ):
            raise commands.errors.CommandError(
                "Filter has not been setup with the `filter setup` command"
            )
        return True

    @commands.group(
        name="filter",
        aliases=(
            "chatfilter",
            "automod",
        ),
        invoke_without_command=False,
        brief="Filter commands to keep your chat secure",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def _filter(self: "Automod", ctx: Context):
        """
        View a variety of options to help clean the chat
        """
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @_filter.command(
        name="clear",
        brief="Clear all words from the automod filter list",
        example=",filter clear",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_clear(self: "Automod", ctx: Context):
        await self.check_setup(ctx.guild)
        from tool.migrate import clear_keywords  # type: ignore

        await clear_keywords(ctx.guild)
        if not await self.bot.db.fetch(
            "SELECT * FROM filter WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail(
                "There **aren't** any **filtered words** in this server"
            )

        await self.bot.db.execute(
            "DELETE FROM filter WHERE guild_id = $1;", ctx.guild.id
        )

        await self.bot.cache.setup_filter()
        return await ctx.success(
            "**Removed** all **filtered words** from the filter list"
        )

    @_filter.command(
        name="add",
        aliases=("create",),
        brief="Add a filter word to the filter list",
        example=",filter add stupid",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_add(self: "Automod", ctx: Context, *, keywords: str):
        if "," in keywords:
            keywords = [f.strip() for f in keywords.split(",")]
        else:
            keywords = [keywords]
        await self.check_setup(ctx.guild)
        for keyword in keywords:
            if await self.bot.db.fetch(
                "SELECT * FROM filter WHERE guild_id = $1 AND keyword = $2",
                ctx.guild.id,
                keyword,
            ):
                return await ctx.fail("That is already a **filtered word**.")

            if len(keyword.split()) > 1:
                return await ctx.fail("The keyword must be **one word**.")

            if len(keyword) > 32:
                return await ctx.fail(
                    "Please provide a **valid** keyword under **32 characters**."
                )

            await self.bot.db.execute(
                "INSERT INTO filter (guild_id, keyword) VALUES ($1, $2);",
                ctx.guild.id,
                keyword,
            )

        self.bot.cache.filter[ctx.guild.id] = [
            _data.keyword
            for _data in await self.bot.db.fetch(
                """SELECT keyword FROM filter WHERE guild_id = $1""", ctx.guild.id
            )
        ]
        from tool.migrate import add_keyword  # type: ignore

        await add_keyword(ctx.guild, keywords)
        return await ctx.success(f"**Added** the word(s): `{', '.join(keywords)}`")

    @_filter.command(
        name="list",
        aliases=("words",),
        brief="View a list of filtered words",
        example=",filter list",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_list(self: "Automod", ctx: Context):
        """
        View every filtered word
        """
        await self.check_setup(ctx.guild)
        if not (
            records := await self.bot.db.fetch(
                "SELECT keyword FROM filter WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail("There aren't any **filtered words** in this server")

        embed = discord.Embed(
            color=self.bot.color,
            title=f"Filtered Words in {ctx.guild.name}",
            description=", ".join((record.keyword for record in records)),
        )

        return await ctx.reply(embed=embed)

    @_filter.command(
        name="whitelist",
        aliases=(
            "exempt",
            "ignore",
        ),
        parameters={
            "event": {
                "converter": str,
                "description": "the event to whitelist them for",
            },
        },
        example=",filter whitelist @sudosql --event spam",
        brief="Exempt roles, users, or channels from filtered automod settings or words",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_whitelist(
        self: "Automod",
        ctx: Context,
        #        *,
        source: Union[discord.Member, discord.TextChannel, discord.Role],
    ):
        """
        Exempt roles from the word filter
        """
        event = (ctx.parameters.get("event") or "all").lower()
        if "," in event:
            event = event.split(",")
        if isinstance(event, list):
            for e in event:
                e.strip()
                if e not in [
                    "invites",
                    "links",
                    "spam",
                    "emojis",
                    "massmention",
                    "snipe",
                    "headers",
                    "nicknames",
                    "spoilers",
                    "caps",
                    "keywords",
                    "all",
                ]:
                    return await ctx.fail(f"`{event}` is **not a valid event**")
        else:
            if event not in [
                "invites",
                "links",
                "spam",
                "emojis",
                "massmention",
                "snipe",
                "headers",
                "nicknames",
                "spoilers",
                "caps",
                "keywords",
                "all",
            ]:
                return await ctx.fail(f"`{event}` is **not a valid event**")

        await self.check_setup(ctx.guild)
        if isinstance(source, discord.Member):
            if await self.bot.hierarchy(ctx, source, ctx.author) is False:
                return

        if await self.bot.db.fetch(
            "SELECT * FROM filter_whitelist WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            source.id,
        ):
            await self.bot.db.execute(
                "DELETE FROM filter_whitelist WHERE guild_id = $1 AND user_id = $2;",
                ctx.guild.id,
                source.id,
            )

            await ctx.success(f"**Unwhitelisted:** {source.mention}")
        else:
            if isinstance(event, list):
                for e in event:
                    await self.bot.db.execute(
                        """
                            INSERT INTO filter_whitelist (guild_id, user_id, events)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (guild_id, user_id)
                            DO UPDATE SET events = filter_whitelist.events || ',' || EXCLUDED.events;
                        """,
                        ctx.guild.id,
                        source.id,
                        e,
                    )
                m = ", ".join(m for m in event)
            else:
                await self.bot.db.execute(
                    """
                        INSERT INTO filter_whitelist (guild_id, user_id, events)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (guild_id, user_id)
                        DO UPDATE SET events = filter_whitelist.events || ',' || EXCLUDED.events;
                    """,
                    ctx.guild.id,
                    source.id,
                    event,
                )
                m = event

            await ctx.success(
                f"**Whitelisted** {source.mention} for the event(s) `{m}`"
            )
        self.bot.cache.filter_whitelist[ctx.guild.id] = [
            data.user_id
            for data in await self.bot.db.fetch(
                """SELECT * FROM filter_whitelist WHERE guild_id = $1""", ctx.guild.id
            )
        ]
        return

    async def get_member(self: "Automod", id: int):
        if user := self.bot.get_user(id):
            return user
        return await self.bot.fetch_user(id)

    def get_object(self: "Automod", guild: discord.Guild, id: int):
        if user := guild.get_member(id):
            return user
        elif role := guild.get_role(id):
            return role
        elif channel := guild.get_channel(id):
            return channel
        else:
            return None

    def get_rows(self: "Automod", guild: discord.Guild, data: list):
        rows = []
        i = 0
        for row in data:
            obj = self.get_object(guild, row["user_id"])
            if obj == None:
                continue
            if isinstance(obj, discord.Member):
                rt = "member"
            elif isinstance(obj, discord.Role):
                rt = "role"
            elif isinstance(obj, discord.TextChannel):
                rt = "channel"
            else:
                pass
            if not rt:
                pass
            else:
                i += 1
                events = row.get("events", "all")
                if "," in events:
                    e = ", ".join(f"**{m}**" for m in events.split(","))
                else:
                    e = f"**{events}**"
                rows.append(f"`{i}` {obj.mention}: `{rt}` - {e}")
        return rows

    @_filter.command(
        name="whitelisted",
        brief="View a all users, roles and channels whitelisted through automod",
        example=",filter whitelisted",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_whitelisted(self: "Automod", ctx: Context):
        await self.check_setup(ctx.guild)
        records = await self.bot.db.fetch(
            "SELECT user_id, events FROM filter_whitelist WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not records:
            return await ctx.fail("there are no **whitelists** setup")

        embed = discord.Embed(color=self.bot.color, title="Whitelisted Objects")
        rows = self.get_rows(ctx.guild, records)
        if len(rows) == 0:
            return await ctx.fail("no whitelists found")
        return await self.bot.dummy_paginator(ctx, embed, rows)

    @_filter.command(
        name="reset",
        brief="Reset all automod settings",
        example=",filter reset",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_reset(self: "Automod", ctx: Context):
        await self.check_setup(ctx.guild)
        tables = [
            """DELETE FROM filter_event WHERE guild_id = $1""",
            """DELETE FROM filter_setup WHERE guild_id = $1""",
            """DELETE FROM automod_timeout WHERE guild_id = $1""",
            """DELETE FROM filter WHERE guild_id = $1""",
            """DELETE FROM filter_whitelist WHERE guild_id = $1""",
        ]
        await gather(*[self.bot.db.execute(table, ctx.guild.id) for table in tables])
        return await ctx.success("filter has been **reset**")

    @_filter.command(
        name="setup",
        brief="Setup the automod filtering for the guild",
        example=",filter setup",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_setup(self: "Automod", ctx: Context):
        """
        Setup the filter
        """
        setup = False
        try:
            await self.check_setup(ctx.guild)
            setup = True
        except Exception:
            pass
        if setup is True:
            return await ctx.fail("filter has already been **setup**")
        if self.bot.check_bot_hierarchy(ctx.guild) is False:
            return await ctx.fail("My top role has to be in the **top 5 roles**")
        await self.bot.db.execute(
            """INSERT INTO filter_setup (guild_id) VALUES ($1)""", ctx.guild.id
        )
        await self.bot.db.execute(
            """INSERT INTO automod_timeout (guild_id, timeframe) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET timeframe = excluded.timeframe""",
            ctx.guild.id,
            "20s",
        )

        return await ctx.success("filter has been **setup**")

    @_filter.command(
        name="nicknames",
        brief="Automatically reset nicknames if a filtered word is detected",
        aliases=(
            "nick",
            "nicks",
        ),
        example=",filter nicknames true",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_nicknames(self: "Automod", ctx: Context, state: bool):
        await self.check_setup(ctx.guild)
        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "nicknames",
        ):
            return await ctx.fail("That is **already** the **current state**")

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled) VALUES ($1, $2, $3) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled;",
            ctx.guild.id,
            "nicknames",
            state,
        )

        await self.bot.cache.setup_filter()
        return await ctx.success(
            f"**{'Enabled' if state else 'Disabled'}** the **nickname filter**"
        )

    async def get_int(self: "Automod", string: str):
        t = ""
        for s in string:
            try:
                d = int(s)
                t += f"{d}"
            except Exception:
                pass
        return t

    def get_state(self: "Automod", state: bool) -> str:
        if state:
            return EMOJIS["UB_Check_Icon"]
        else:
            return EMOJIS["UB_X_Icon"]

    @_filter.command(
        name="snipe",
        brief="filter automod deleted messages from the snipe commands",
        aliases=("snipes", "s"),
        example=",filter snipe true",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_snipe(self: "Automod", ctx: Context, state: bool):
        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "snipe",
        ):
            return await ctx.fail("That is **already** the **current state**")
        else:
            await self.bot.db.execute(
                """INSERT INTO filter_event (guild_id, event, is_enabled) VALUES ($1, $2, $3) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled;""",
                ctx.guild.id,
                "snipe",
                state,
            )
            return await ctx.success(
                f"**{'Enabled' if state else 'Disabled'}** the **snipe filter**"
            )

    @_filter.command(
        name="settings",
        brief="Show the current configuration of automod",
        example=",filter settings",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_settings(self: "Automod", ctx: Context):
        rows = []
        event_types = [
            "invites",
            "links",
            "spam",
            "emojis",
            "massmention",
            "snipe",
            "headers",
            "nicknames",
            "spoilers",
            "caps",
        ]
        e = []

        async def get_timeout():
            keywords = await self.bot.db.fetch(
                """SELECT keyword FROM filter WHERE guild_id = $1""", ctx.guild.id
            )
            words = [keyword["keyword"] for keyword in keywords]
            if len(words) > 0:
                word_list = ", ".join(words)
            else:
                word_list = "No filtered words"
            timeout = (
                await self.bot.db.fetchval(
                    "SELECT timeframe FROM automod_timeout WHERE guild_id = $1",
                    ctx.guild.id,
                )
                or "20 seconds"
            )
            rows.insert(
                0, f"**Timeout:** `{timeout}`\n**Filtered Words:** ```{word_list}```"
            )

        async def get_events():
            events = []
            for event, is_enabled, threshold in await self.bot.db.fetch(
                """SELECT event, is_enabled, threshold FROM filter_event WHERE guild_id = $1""",
                ctx.guild.id,
            ):
                e.append(event.lower())
                if event.lower() not in ["invites", "links", "snipe"]:
                    if is_enabled == True:
                        limit = f"- limit: `{threshold}`"
                    else:
                        limit = f""
                    events.append(
                        f"**filter [{event}]({self.bot.domain}/commands):** {self.get_state(is_enabled)} {limit}"
                    )
                else:
                    limit = ""
                    events.append(
                        f"**filter [{event}]({self.bot.domain}/commands):** {self.get_state(is_enabled)} {limit}"
                    )
            rows.extend(events)

        await gather(*[get_timeout(), get_events()])
        for event_type in event_types:
            if event_type.lower() not in e:
                rows.append(
                    f"**filter [{event_type.lower()}]({self.bot.domain}/commands):** {self.get_state(False)}"
                )

        embed = discord.Embed(
            title="Automod settings", color=self.bot.color, description="\n".join(rows)
        )
        await ctx.send(embed=embed)

    @_filter.command(
        name="headers",
        aliases=["head"],
        brief="enable or disable the header filter",
        example="filter headers true --threshold 5",
        parameters={
            "threshold": {
                "converter": int,
                "description": "The limit for spoilers in one message",
                "aliases": ["limit"],
            }
        },
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def headers(self, ctx: Context, state: bool):
        await self.check_setup(ctx.guild)
        threshold = (
            ctx.parameters.get("threshold")
            or await self.bot.db.fetchval(
                "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "headers",
            )
            or 5
        )

        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "headers",
        ) and threshold == await self.bot.db.fetchval(
            "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "headers",
        ):
            return await ctx.fail("That is **already** the **current state**")

        if state:
            if (
                threshold
                == await self.bot.db.fetchval(
                    "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                    ctx.guild.id,
                    "headers",
                )
                and ctx.parameters.get("threshold") is not None
            ):
                return await ctx.fail("That is **already** the **current threshold**")

            if threshold > 127 or threshold < 1:
                return await ctx.fail(
                    "Provide a **valid** threshold between **1** and **127**"
                )

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled, threshold) VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled, threshold = EXCLUDED.threshold;",
            ctx.guild.id,
            "headers",
            state,
            threshold,
        )
        await self.bot.cache.setup_filter()
        if state is True:
            h = f"(with a threshold of `{threshold}`)"
        else:
            h = ""
        return await ctx.success(
            f"**filter headers** set to **{'enabled' if state is True else 'disabled'}** {h}"
        )

    @_filter.command(name="migrate", brief="migrate filtered words to automod")
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def migrate(self, ctx: Context):
        await self.check_setup(ctx.guild)
        keywords = await self.bot.db.fetch(
            "SELECT keyword FROM filter WHERE guild_id = $1", ctx.guild.id
        )
        if not keywords:
            return await ctx.fail("No filtered words found to migrate.")
        from tool.migrate import add_keyword  # type: ignore

        words = [keyword["keyword"] for keyword in keywords]
        await add_keyword(ctx.guild, words, True)
        return await ctx.success("Migrated words to automod")

    @_filter.command(
        name="images",
        aliases=["img"],
        brief="enable or disable the image filter",
        example="filter images true --threshold 5",
        parameters={
            "threshold": {
                "converter": int,
                "description": "The limit for spoilers in one message",
                "aliases": ["limit"],
            }
        },
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def images(self, ctx: Context, state: bool):
        await self.check_setup(ctx.guild)
        threshold = (
            ctx.parameters.get("threshold")
            or await self.bot.db.fetchval(
                "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "images",
            )
            or 5
        )

        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "images",
        ) and threshold == await self.bot.db.fetchval(
            "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "images",
        ):
            return await ctx.fail("That is **already** the **current state**")

        if state:
            if (
                threshold
                == await self.bot.db.fetchval(
                    "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                    ctx.guild.id,
                    "images",
                )
                and ctx.parameters.get("threshold") is not None
            ):
                return await ctx.fail("That is **already** the **current threshold**")

            if threshold > 127 or threshold < 1:
                return await ctx.fail(
                    "Provide a **valid** threshold between **1** and **127**"
                )

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled, threshold) VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled, threshold = EXCLUDED.threshold;",
            ctx.guild.id,
            "images",
            state,
            threshold,
        )
        if state is True:
            h = f"(with a threshold of `{threshold}`)"
        else:
            h = ""
        await self.bot.cache.setup_filter()
        return await ctx.success(
            f"**filter images** set to **{'enabled' if state is True else 'disabled'}** {h}"
        )

    @_filter.command(
        name="timeout",
        aliases=["to", "time"],
        brief="Set the amount of time someone will be muted when they break an automod rule",
        example=",filter timeout 60s",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_timeout(self: "Automod", ctx: Context, *, time: str):
        await self.check_setup(ctx.guild)
        if "minute" in time.lower():
            time = f"{await self.get_int(time)} minutes"
        elif "m" in time.lower():
            time = f"{await self.get_int(time)} minutes"
        elif "second" in time.lower():
            time = f"{await self.get_int(time)} seconds"
        elif "s" in time.lower():
            time = f"{await self.get_int(time)} seconds"
        elif "hour" in time.lower():
            time = f"{await self.get_int(time)} hours"
        elif "h" in time.lower():
            time = f"{await self.get_int(time)} hours"
        else:
            time = f"{await self.get_int(time)} seconds"

        try:
            converted = humanfriendly.parse_timespan(time)
            if converted < 20:
                return await ctx.fail(
                    "**Punishment timeout** must be **20 seconds** or above"
                )
        except Exception:
            return await ctx.fail(f"Could not convert `{time}` into a timeframe")
        await self.bot.db.execute(
            """INSERT INTO automod_timeout (guild_id,timeframe) VALUES($1,$2) ON CONFLICT(guild_id) DO UPDATE SET timeframe = excluded.timeframe""",
            ctx.guild.id,
            time,
        )
        return await ctx.success(f"**Punishment timeout** is now `{time}`")

    @_filter.command(
        name="spoilers",
        aliases=("spoiler",),
        example=",filter spoilers enable",
        brief="Manage spoiler images being sent in the server",
        parameters={
            "threshold": {
                "converter": int,
                "description": "The limit for spoilers in one message",
                "aliases": ["limit"],
            }
        },
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_spoilers(self: "Automod", ctx: Context, state: bool):
        await self.check_setup(ctx.guild)
        threshold = (
            ctx.parameters.get("threshold")
            or await self.bot.db.fetchval(
                "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "spoilers",
            )
            or 5
        )

        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "spoilers",
        ) and threshold == await self.bot.db.fetchval(
            "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "spoilers",
        ):
            return await ctx.fail("That is **already** the **current state**")

        if state:
            if (
                threshold
                == await self.bot.db.fetchval(
                    "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                    ctx.guild.id,
                    "spoilers",
                )
                and ctx.parameters.get("threshold") is not None
            ):
                return await ctx.fail("That is **already** the **current threshold**")

            if threshold > 127 or threshold < 1:
                return await ctx.fail(
                    "Provide a **valid** threshold between **1** and **127**"
                )

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled, threshold) VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled, threshold = EXCLUDED.threshold;",
            ctx.guild.id,
            "spoilers",
            state,
            threshold,
        )

        await self.bot.cache.setup_filter()
        return await ctx.success(
            f"**{'Enabled' if state else 'Disabled'}** the **spoiler filter** {f'(with threshold: `{threshold}`)' if state else ''}"
        )

    @_filter.command(
        name="links",
        aliases=("urls",),
        brief="Prevent all links from being sent in the server",
        example=",filter links enable",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_links(self: "Automod", ctx: Context, state: bool):
        """
        Delete any message that contains a link
        """
        await self.check_setup(ctx.guild)
        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "links",
        ):
            return await ctx.fail("That is **already** the **current state**")

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled) VALUES ($1, $2, $3) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled;",
            ctx.guild.id,
            "links",
            state,
        )

        await self.bot.cache.setup_filter()
        return await ctx.success(
            f"**{'Enabled' if state else 'Disabled'}** the **link filter**"
        )

    @_filter.command(
        name="spam",
        brief="Prevent users from laddering/spamming in the server",
        example=",filter spam true --threshold 10",
        parameters={
            "threshold": {
                "converter": int,
                "description": "The limit of messages for one user in 5 seconds",
                "aliases": ["limit"],
            }
        },
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_spam(self: "Automod", ctx: Context, state: bool):
        await self.check_setup(ctx.guild)
        threshold = (
            ctx.parameters.get("threshold")
            #        or await self.bot.db.fetchval(
            #                "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
            #               ctx.guild.id,
            #              "spam",
            #         )
            or 5  # default_timeout
        )

        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "spam",
        ) and threshold == await self.bot.db.fetchval(
            "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "spam",
        ):
            return await ctx.fail("That is **already** the **current state**")

        if state:
            if (
                threshold
                == await self.bot.db.fetchval(
                    "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                    ctx.guild.id,
                    "spam",
                )
                and ctx.parameters.get("threshold") is not None
            ):
                return await ctx.fail("That is **already** the **current threshold**")

            if threshold > 127 or threshold < 1:
                return await ctx.fail(
                    "Provide a **valid** threshold between **1** and **127**"
                )

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled, threshold) VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled, threshold = EXCLUDED.threshold;",
            ctx.guild.id,
            "spam",
            state,
            threshold,
        )
        if ctx.guild.id in self.bot.cache.filter_event:
            self.bot.cache.filter_event[ctx.guild.id]["spam"] = {
                "is_enabled": state,
                "threshold": threshold,
            }
        else:
            await self.bot.cache.setup_filter()
        return await ctx.success(
            f"**{'Enabled' if state else 'Disabled'}** the **spam filter** {f'(with threshold: `{threshold}`)' if state else ''}"
        )

    @_filter.command(
        name="emojis",
        brief="Limit the amount of emojis that can be sent in one message",
        aliases=("emoji",),
        example=",filter emojis true --threshold 3",
        parameters={
            "threshold": {
                "converter": int,
                "description": "The limit for emojis in one message",
                "aliases": ["limit"],
            }
        },
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_emojis(self: "Automod", ctx: Context, state: bool):
        await self.check_setup(ctx.guild)
        threshold = (
            ctx.parameters.get("threshold")
            or await self.bot.db.fetchval(
                "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "emojis",
            )
            or 5  # default_timeout
        )

        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "emojis",
        ) and threshold == await self.bot.db.fetchval(
            "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "emojis",
        ):
            return await ctx.fail("That is **already** the **current state**")

        if state:
            if (
                threshold
                == await self.bot.db.fetchval(
                    "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                    ctx.guild.id,
                    "emojis",
                )
                and ctx.parameters.get("threshold") is not None
            ):
                return await ctx.fail("That is **already** the **current threshold**")

            if threshold > 127 or threshold < 1:
                return await ctx.fail(
                    "Provide a **valid** threshold between **1** and **127**"
                )

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled, threshold) VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled, threshold = EXCLUDED.threshold;",
            ctx.guild.id,
            "emojis",
            state,
            threshold,
        )

        await self.bot.cache.setup_filter()
        return await ctx.success(
            f"**{'Enabled' if state else 'Disabled'}** the **emoji filter** {f'(with threshold: `{threshold}`)' if state else ''}"
        )

    @_filter.command(
        name="invites",
        aliases=("invs",),
        brief="Stop outside server invites from being sent in the guild",
        example=",filter invites true",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_invites(self: "Automod", ctx: Context, state: bool):
        await self.check_setup(ctx.guild)
        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "invites",
        ):
            return await ctx.fail("That is **already** the **current state**")

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled) VALUES ($1, $2, $3) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled;",
            ctx.guild.id,
            "invites",
            state,
        )
        await self.bot.cache.setup_filter()
        return await ctx.success(
            f"**{'Enabled' if state else 'Disabled'}** the **invite filter**"
        )

    @_filter.command(
        name="caps",
        aliases=("capslock",),
        brief="Limit how many capital letters can be sent in a single message",
        example=",filter caps true --threshold 6",
        parameters={
            "threshold": {
                "converter": int,
                "description": "The limit for caps in one message",
                "aliases": ["limit"],
            }
        },
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_caps(self: "Automod", ctx: Context, state: bool):
        """
        Delete any messages exceeding the threshold for caps
        """
        threshold = (
            ctx.parameters.get("threshold")
            or await self.bot.db.fetchval(
                "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "caps",
            )
            or 5  # default_timeout
        )
        await self.check_setup(ctx.guild)
        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "caps",
        ) and threshold == await self.bot.db.fetchval(
            "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "caps",
        ):
            return await ctx.fail("That is **already** the **current state**")

        if state:
            if (
                threshold
                == await self.bot.db.fetchval(
                    "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                    ctx.guild.id,
                    "invites",
                )
                and ctx.parameters.get("threshold") is not None
            ):
                return await ctx.fail("That is **already** the **current threshold**")

            if threshold > 127 or threshold < 1:
                return await ctx.fail(
                    "Provide a **valid** threshold between **1** and **127**"
                )

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled, threshold) VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled, threshold = EXCLUDED.threshold;",
            ctx.guild.id,
            "caps",
            state,
            threshold,
        )

        await self.bot.cache.setup_filter()
        return await ctx.success(
            f"**{'Enabled' if state else 'Disabled'}** the **caps filter** {f'(with threshold: `{threshold}`)' if state else ''}"
        )

    @_filter.command(
        name="massmention",
        brief="Prevent users from mentioning more than a set amount of members at once",
        example=",filter massmention true --threshold 4",
        aliases=("mentions",),
        parameters={
            "threshold": {
                "converter": int,
                "description": "The limit for mentions in one message",
                "aliases": ["limit"],
            }
        },
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_massmention(self: "Automod", ctx: Context, state: bool):
        """
        Delete any messages exceeding the threshold for mentions
        """
        await self.check_setup(ctx.guild)
        threshold = (
            ctx.parameters.get("threshold")
            or await self.bot.db.fetchval(
                "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "massmention",
            )
            or 5
        )

        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "massmention",
        ) and threshold == await self.bot.db.fetchval(
            "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "massmention",
        ):
            return await ctx.fail("That is **already** the **current state**")

        if state:
            if (
                threshold
                == await self.bot.db.fetchval(
                    "SELECT threshold FROM filter_event WHERE guild_id = $1 AND event = $2",
                    ctx.guild.id,
                    "invites",
                )
                and ctx.parameters.get("threshold") is not None
            ):
                return await ctx.fail("That is **already** the **current threshold**")

            if threshold > 127 or threshold < 1:
                return await ctx.fail(
                    "Please provide a **valid** threshold between **1** and **127**"
                )

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled, threshold) VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled, threshold = EXCLUDED.threshold;",
            ctx.guild.id,
            "massmention",
            state,
            threshold,
        )

        await self.bot.cache.setup_filter()
        return await ctx.success(
            f"**{'Enabled' if state else 'Disabled'}** the **mention filter** {f'(with threshold: `{threshold}`)' if state else ''}"
        )

    @_filter.command(
        name="remove",
        aliases=("delete",),
        brief="Remove a filtered word from the filter list",
        example=",filter remove stupid",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_remove(self: "Automod", ctx: Context, *, keyword: str):
        from tool.migrate import remove_keyword  # type: ignore

        await self.check_setup(ctx.guild)
        if not await self.bot.db.fetch(
            "SELECT * FROM filter WHERE guild_id = $1 AND keyword = $2",
            ctx.guild.id,
            keyword,
        ):
            return await ctx.fail("That isn't a **filtered word**.")

        await self.bot.db.execute(
            "DELETE FROM filter WHERE guild_id = $1 AND keyword = $2;",
            ctx.guild.id,
            keyword,
        )
        await remove_keyword(ctx.guild, keyword)
        self.bot.cache.filter[ctx.guild.id].remove(keyword)
        return await ctx.success(
            f"**Removed** the `{keyword}` from the **filtered list**"
        )

    @_filter.command(
        name="punishment",
        aliases=["punish"],
        brief="Set the punishment for breaking automod rules",
        example=",filter punishment delete",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_punishment(self, ctx: Context, *, punishment: str):
        await self.check_setup(ctx.guild)
        if punishment.lower() not in ["delete", "timeout", "kick", "ban", "jail"]:
            return await ctx.fail(f"That is not a **valid punishment**")

        await self.bot.db.execute(
            "INSERT INTO filter_setup (guild_id, punishment) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET punishment = EXCLUDED.punishment;",
            ctx.guild.id,
            punishment.lower(),
        )
        return await ctx.success(
            f"**Punishment** for breaking automod rules is now `{punishment.lower()}`"
        )

    @_filter.command(
        name="punishments",
        brief="View the current punishment for breaking automod rules",
        example=",filter punishments",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_punishments(self: "Automod", ctx: Context):
        await self.check_setup(ctx.guild)
        punishment = await self.bot.db.fetchval(
            "SELECT punishment FROM filter_setup WHERE guild_id = $1", ctx.guild.id
        )
        if not punishment:
            p = [
                "delete",
                "timeout",
                "kick",
                "ban",
            ]
            embed = discord.Embed(
                title="Punishments",
                description="\n".join(f"**{i}**" for i in p),
                color=self.bot.color,
            )
            return await ctx.send(embed=embed)
        return await ctx.success(
            f"**Punishment** for breaking automod rules is `{punishment}`"
        )

    @_filter.command(
        name="keywords",
        aliases=("keyword",),
        brief="Enable or disable the keyword filtering in chat",
        example=",filter keywords true",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def filter_keywords(self: "Automod", ctx: Context, state: bool):
        await self.check_setup(ctx.guild)
        if state == await self.bot.db.fetchval(
            "SELECT is_enabled FROM filter_event WHERE guild_id = $1 AND event = $2",
            ctx.guild.id,
            "keywords",
        ):
            return await ctx.fail("That is **already** the **current state**")

        await self.bot.db.execute(
            "INSERT INTO filter_event (guild_id, event, is_enabled) VALUES ($1, $2, $3) ON CONFLICT (guild_id, event) DO UPDATE SET is_enabled = EXCLUDED.is_enabled;",
            ctx.guild.id,
            "keywords",
            state,
        )
        await self.bot.cache.setup_filter()
        return await ctx.success(
            f"**{'Enabled' if state else 'Disabled'}** the **keyword filter**"
        )


async def setup(bot: Greed):
    await bot.add_cog(Automod(bot))
