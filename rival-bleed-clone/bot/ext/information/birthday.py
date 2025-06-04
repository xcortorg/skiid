from discord.ext.commands import (
    Cog,
    command,
    group,
    has_permissions,
    CommandError,
    Converter,
)
from discord import Client, Member, User, Embed, utils, Role, TextChannel
from lib.patch.context import Context
from typing import Optional, Union, List, Tuple, Callable, Any
from datetime import datetime, timedelta
from loguru import logger
from lib.classes.database import Record
from asyncio import create_task, sleep, Task
import calendar
import re

PATTERN = r"\b(\d+)(st|nd|rd|th)\b"
REGEX = re.compile(PATTERN)

MAPPING = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


class BirthdayConverter(Converter):
    async def convert(self, ctx: Context, argument: str):
        month = None
        day = None
        now = datetime.now()
        if "/" in argument:
            args = argument.split("/")
            arg1 = int(args[0].strip())
            arg2 = int(args[1].strip())
            if arg1 > 12:
                day = arg1
                month = arg2
            else:
                day = arg2
                month = arg1
        else:
            args = argument.split(" ")
            try:
                arg1 = int(args[0])
            except Exception:
                pass
            try:
                arg2 = int(args[1])
            except Exception:
                pass
            if isinstance(arg1, int) and isinstance(arg2, int):
                if arg1 > 12:
                    day = arg1
                    month = arg2
                else:
                    day = arg2
                    month = arg1
            else:
                if match := REGEX.match(arg1):
                    day = int(match.group(1))
                    month = arg2
                elif match := REGEX.match(arg2):
                    day = int(match.group(1))
                    month = arg1
                else:
                    if isinstance(arg1, int):
                        day = arg1
                        month = arg2
                    elif isinstance(arg2, int):
                        day = arg2
                        month = arg1
        if not month:
            raise CommandError("Couldn't parse the date you provided")
        if not isinstance(month, int):
            if not (month := MAPPING.get(month)):
                raise CommandError("Invalid month")
        if int(now.month) > month:
            now = now.replace(year=now.year + 1)
        if int(now.day) > day:
            now = now.replace(year=now.year + 1)
        now = now.replace(month=month, day=month)
        return now


async def daily_task(
    coroutines: List[Tuple[Callable[..., Any], Tuple[Any, ...], dict]]
) -> None:
    while True:
        now = datetime.now()
        # Calculate the time until midnight
        midnight = datetime.combine(now.date() + timedelta(days=1), datetime.time(0, 0))
        wait_time = (midnight - now).total_seconds()

        # Wait until midnight
        await sleep(wait_time)

        # Execute each provided coroutine with its arguments
        for coroutine, args, kwargs in coroutines:
            await coroutine(*args, **kwargs)
            logger.info(f"Executed daily task for {coroutine.__name__} at midnight.")


def humanize_date(record: Record) -> str:
    month = calendar.month_name[record.month]
    return f"{month} {record.day}"


class Birthday(Cog):
    def __init__(self, bot: Client):
        self.bot = bot
        self.task: Optional[Task] = None

    async def cog_load(self) -> None:
        self.task = self.bot.loop.create_task(
            daily_task(
                [
                    self.daily_task,
                    self.bot,
                ]
            )
        )

    async def cog_unload(self) -> None:
        if self.task:
            self.task.cancel()

    async def daily_task(self):
        now = datetime.now()
        users = await self.bot.db.fetch("""SELECT * FROM birthday.users""")
        servers = await self.bot.db.fetch(
            """SELECT * FROM birthday.servers WHERE guild_id = ANY($1::BIGINT[])""",
            [g.id for g in self.bot.guilds],
        )
        self.bot.dispatch("new_day", servers)
        for user in users:
            if user.day == int(now.day) and user.month == int(now.month):
                for server in servers:
                    if not (guild := self.bot.get_guild(server.guild_id)):
                        continue
                    if not (member := guild.get_member(user.user_id)):
                        continue
                    if server.role_ids:
                        role_ids = [role.id for role in member.roles]
                        if not any(item in role_ids for item in server.role_ids):
                            continue
                    if role := guild.get_role(server.role_id):
                        await member.add_roles(role, reason="Birthday Role")
                    if channel := guild.get_channel(server.channel_id or 0):
                        self.bot.dispatch("birthday_notification", member, channel)

    @Cog.listener("on_new_day")
    async def remove_birthdays(self, records: List[Record]):
        for server in records:
            if not (guild := self.bot.get_guild(server.guild_id)):
                continue
            if not server.role_id:
                continue
            if not (role := guild.get_role(server.role_id)):
                continue
            for member in role.members:
                await member.remove_roles(role, reason="Birthday Role Removal")

    @Cog.listener("on_birthday_notification")
    async def on_new_birthday(self, member: Member, channel: TextChannel):
        await channel.send(f"Happy Birthday {member.mention}!")

    @group(
        name="birthday",
        aliases=["bday"],
        description="View your birthday or somebody elses",
        example=",birthday @aiohttp",
    )
    async def birthday(self, ctx: Context, *, member: Optional[Member] = None):
        member = member or ctx.author
        value = (
            f"{member.mention} hasn't" if not member == ctx.author else "You haven't"
        )
        if not (
            birthday := await self.bot.db.fetchrow(
                """SELECT month, day FROM birthday.users WHERE user_id = $1""",
                ctx.author.id,
            )
        ):
            raise CommandError(
                f"{value} set your birthday using {ctx.prefix}birthday set"
            )

        now = datetime.now()
        if int(now.month) > birthday.month:
            now = now.replace(year=now.year + 1)
        if int(now.day) > birthday.day:
            now = now.replace(year=now.year + 1)
        if int(now.month) == birthday.month and int(now.day) == birthday.day:
            n = "**Today**"
        else:
            now = now.replace(month=birthday.month, day=birthday.month)
            n = f"{utils.format_dt(now, style = 'R')}"
        value = "Your" if member == ctx.author else f"**{str(member)}**'s"
        return await ctx.send(
            embed=Embed(
                color=self.bot.color,
                description=f"🎂 {ctx.author.mention}: {value} **birthday** is **{humanize_date(birthday)}**. That's {n}!",
            )
        )

    @birthday.command(
        name="set", description="Set your birthday", example=",birthday set 12 25"
    )
    async def birthday_set(self, ctx: Context, *, date: BirthdayConverter):
        member = ctx.author
        await self.bot.db.execute(
            """INSERT INTO birthday.users (user_id, month, day) VALUES($1, $2, $3) ON CONFLICT(user_id) DO UPDATE SET month = excluded.month, day = excluded.day""",
            ctx.author.id,
            int(date.month),
            int(date.day),
        )
        now = datetime.now()
        if int(now.month) == date.month and int(now.day) == date.day:
            n = "**Today**"
        else:
            n = f"{utils.format_dt(date, style = 'R')}"
        value = "Your" if member == ctx.author else f"**{str(member)}**'s"
        return await ctx.send(
            embed=Embed(
                color=self.bot.color,
                description=f"🎂 {ctx.author.mention}: Set {value} **birthday** as **{humanize_date(date)}**. That's {n}!",
            )
        )

    @birthday.command(name="role", description="Set the birthday role")
    @has_permissions(manage_roles=True)
    async def birthday_role(self, ctx: Context, *, role: Role):
        await self.bot.db.execute(
            """INSERT INTO birthday.servers (guild_id, role_id) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id""",
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(f"Set the **birthday role** to {role.mention}")

    @birthday.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View a list of every member's birthday",
    )
    async def birthday_list(self, ctx: Context):
        if not (
            data := await self.bot.db.fetch(
                """SELECT user_id, month, day FROM birthday.users WHERE user_id = ANY($1::BIGINT[])""",
                [m.id for m in ctx.guild.members],
            )
        ):
            raise CommandError("No members here have set their **birthday**")
        embed = Embed(color=self.bot.color, title="Birthdays").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        rows = []
        for i, row in enumerate(data, start=1):
            rows.append(
                f"`{i}` **{str(ctx.guild.get_member(row.user_id))}** - {humanize_date(row)}"
            )
        return await ctx.paginate(embed, rows)

    @birthday.group(
        name="celebrate",
        description="Limit birthday celebration to members in certain roles",
        example=",birthday celebrate @bdays",
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def birthday_celebrate(self, ctx: Context, *, role: Role):
        roles = (
            await self.bot.db.fetchval(
                """SELECT role_ids FROM birthday.servers WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or []
        )
        if role.id in roles:
            roles.remove(role.id)
            await self.bot.db.execute(
                """UPDATE birthday.servers SET role_ids = $1 WHERE guild_id = $2""",
                roles,
                ctx.guild.id,
            )
            return await ctx.success(
                f"Removed {role.mention} from the **birthday celebration roles**"
            )
        else:
            await self.bot.db.execute(
                """INSERT INTO birthday.servers (guild_id, role_ids) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET SET role_ids = ARRAY(SELECT DISTINCT unnest(birthday.servers.role_ids || EXCLUDED.role_ids));""",
                ctx.guild.id,
                [role.id],
            )
            return await ctx.success(
                f"Set {role.mention} as a **birthday celebration role**"
            )

    @birthday_celebrate.command(
        name="list", aliases=["ls", "show", "view"], description="List celebrated roles"
    )
    @has_permissions(manage_roles=True)
    async def birthday_celebrate_list(self, ctx: Context):
        if not (
            roles := await self.bot.db.fetchval(
                """SELECT role_ids FROM birthday.servers WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No roles have been set to celebrate **birthdays**")
        embed = Embed(color=self.bot.color, title="Celebration Roles").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        i = 0
        rows = []
        for role_id in roles:
            if not (role := ctx.guild.get_role(role_id)):
                continue
            i += 1
            rows.append(f"`{i}` {role.mention}")
        if len(rows) == 0:
            raise CommandError("No roles have been set to celebrate **birthdays**")
        return await ctx.paginate(embed, rows)

    @birthday.command(
        name="config",
        aliases=["cfg", "settings"],
        description="view the current configuration of birthday celebrations",
    )
    @has_permissions(manage_roles=True)
    async def birthday_config(self, ctx: Context):
        if not (
            data := await self.bot.db.fetchrow(
                """SELECT * FROM birthday.servers WHERE guild_id = $1""", ctx.guild.id
            )
        ):
            raise CommandError("**birthday celebrations** have not been setup")
        if not data.channel_id:
            channel_value = "N/A"
        if not (channel := ctx.guild.get_channel(data.channel_id)):
            channel_value = "N/A"
        else:
            channel_value = f"{channel.mention}"
        if not data.role_id:
            role_value = "N/A"
        if not (role := ctx.guild.get_role(data.role_id)):
            role_value = "N/A"
        else:
            role_value = f"{role.mention}"
        embed = Embed(color=self.bot.color, title="Birthday Config").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        embed.description = f"""**Celebrated Roles:** {len(data.role_ids)}\n**Channel:** {channel_value}\n**Role:** {role_value}"""
        return await ctx.send(embed=embed)

    @birthday.command(
        name="channel",
        description="Set the birthday channel",
        example=",birthday channel #text",
    )
    @has_permissions(manage_channels=True)
    async def birthday_channel(self, ctx: Context, *, channel: TextChannel):
        await self.bot.db.execute(
            """INSERT INTO birthday.servers (guild_id, channel_id) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id""",
            ctx.guild.id,
            channel.id,
        )
        return await ctx.success(
            f"Set **{channel.mention}** as the **birthday channel**"
        )
