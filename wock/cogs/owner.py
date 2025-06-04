import asyncio
import datetime
import os
import random
import sys
import traceback
from asyncio.subprocess import PIPE
from typing import Optional, Union

import aiohttp
import discord
from discord import Guild, Member, User
from discord.ext import commands, tasks
from jishaku.codeblocks import codeblock_converter
from loguru import logger
from tools.important import \
    Context  # type: ignore # type: ignore # type: ignore # type: ignore


async def get_commits(author: str, repository: str, token: str):
    url = f"https://api.github.com/repos/{author}/{repository}/commits"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            headers={
                "accept": "application/vnd.github.v3.raw",
                "authorization": "token {}".format(token),
            },
        ) as response:
            data = await response.json()
    return data


async def check_commits(commits: list):
    for commit in commits:
        if commit["commit"]["author"]["name"] != "root":
            date = datetime.datetime.strptime(
                commit["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ"
            ).timestamp()
            if int(datetime.datetime.utcnow().timestamp() - date) < 61:
                return (True, commit)
    return (False, None)


def format_commit(d: tuple):
    d = d[0].decode("UTF-8")
    if "\n" in d:
        for _ in d.split("\n"):
            if "cogs" not in _:
                if "tools" in _:
                    return True
        return False
    else:
        try:
            for _ in d.splitlines():
                if "cogs" not in _:
                    if "tools" not in _:
                        return True
            return False
        except Exception:
            return False


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.github_pull.start()
        self.last_commit = None

    @commands.Cog.listener("on_member_join")
    async def global_ban_event(self, member: Member):
        if global_ban := await self.bot.db.fetchval(
            """SELECT reason FROM globalbans WHERE user_id = $1""", member.id
        ):
            try:
                await member.guild.ban(member, reason=f"Global banned: {global_ban}")
            except Exception:
                pass

    @tasks.loop(minutes=1)
    async def github_pull(self):
        token = "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"
        author = "mazi1337"
        repository = "wockbot"
        try:
            commits = await get_commits(author, repository, token)
            check, commit = await check_commits(commits)
            if check is True:
                if commit != self.last_commit:
                    proc = await asyncio.create_subprocess_shell(
                        "git pull", stderr=PIPE, stdout=PIPE
                    )
                    data = await proc.communicate()
                    self.last_commit = commit
                    if b"Already up to date.\n" in data:
                        return
                    else:
                        if format_commit(data) is True:
                            logger.info("[ Commit Detected ] Restarting")
                            await asyncio.create_subprocess_shell("pm2 restart wock")
                        else:
                            logger.info("[ Commit Detected ] Auto Reloading..")
        except Exception as e:
            exc = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.info(f"Issue in Git Pull {exc}")

    async def do_ban(self, guild: Guild, member: Union[User, Member], reason: str):
        if guild.get_member(member.id):
            try:
                await guild.ban(member, reason=reason)
                return 1
            except Exception:
                return 0
        else:
            return 0

    async def do_global_ban(self, member: Union[Member, User], reason: str):
        if len(member.mutual_guilds) > 0:
            bans = await asyncio.gather(
                *[self.do_ban(guild, member, reason) for guild in member.mutual_guilds]
            )
            return sum(bans)
        else:
            return 0

    @commands.group(name="donator", invoke_without_command=True)
    @commands.is_owner()
    async def donator(self, ctx: Context, *, member: Member | User):
        if await self.bot.db.fetchrow(
            """SELECT * FROM donators WHERE user_id = $1""", member.id
        ):
            await self.bot.db.execute(
                """DELETE FROM donators WHERE user_id = $1""", member.id
            )
            m = f"removed **donator** from {member.mention}"
        else:
            await self.bot.db.execute(
                """INSERT INTO donators (user_id, ts) VALUES($1, $2)""",
                member.id,
                datetime.datetime.now(),
            )
            m = f"added **donator** to {member.mention}"
        return await ctx.success(m)

    @donator.command(name="check")
    @commands.is_owner()
    async def donator_check(self, ctx: Context, member: Member | User):
        if await self.bot.db.fetchrow(
            """SELECT * FROM donators WHERE user_id = $1""", member.id
        ):
            return await ctx.success(f"{member.mention} is a donator")
        return await ctx.success(f"{member.mention} is not a donator")

    @commands.group(usage="[command]")
    async def commandstats(self, ctx: commands.Context):
        """See command usage statistics"""
        if ctx.invoked_subcommand is None:
            if args := ctx.message.content.split()[1:]:
                await self.commandstats_single(ctx, " ".join(args))
            else:
                await ctx.send_help()

    @commandstats.command(name="server")
    async def commandstats_server(
        self, ctx: commands.Context, user: Optional[discord.Member] = None
    ):
        """Most used commands in this server"""
        if ctx.guild is None:
            raise commands.CommandError("Unable to get current guild")

        content = discord.Embed(
            title=f"Most used commands in {ctx.guild.name}"
            + ("" if user is None else f" by {user}")
        )
        opt = [user.id] if user is not None else []
        data = await self.bot.db.fetch(
            """
            SELECT command_name, SUM(uses) as total FROM command_usage
                WHERE command_type = 'internal'
                  AND guild_id = $1
                  AND user_id = $2
                GROUP BY command_name
                ORDER BY total DESC
            """,
            ctx.guild.id,
            *opt,
        )
        if not data:
            raise commands.CommandError("No commands have been used yet!")

        rows = []
        total = 0
        for i, (command_name, count) in enumerate(data, start=1):
            total += count
            rows.append(
                f"`{i}` **{count}** use{'' if count == 1 else 's'} : "
                f"`{ctx.prefix}{command_name}`"
            )

        if rows:
            content.set_footer(text=f"Total {total} commands")
            await self.bot.dummy_paginator(ctx, content, rows)
        else:
            content.description = "No data"
            await ctx.send(embed=content)

    @commandstats.command(name="globalstats")
    @commands.is_owner()
    async def commandstats_global(
        self, ctx: commands.Context, user: Optional[discord.Member] = None
    ):
        """Most used commands globally"""
        content = discord.Embed(
            title="Most used commands" + ("" if user is None else f" by {user}")
        )
        opt = [user.id] if user is not None else [u.id for u in self.bot.users]
        data = await self.bot.db.fetch(
            """
            SELECT command_name, SUM(uses) as total FROM command_usage
                WHERE command_type = 'internal'
                  AND user_id = any($1::bigint[])
                GROUP BY command_name
                ORDER BY total DESC
            """,
            opt,
        )
        if not data:
            raise commands.CommandError("No commands have been used yet!")

        rows = []
        total = 0
        for i, (command_name, count) in enumerate(data, start=1):
            total += count
            rows.append(
                f"`{i}` **{count}** use{'' if count == 1 else 's'} : "
                f"`{ctx.prefix}{command_name}`"
            )

        if rows:
            content.set_footer(text=f"Total {total} commands")
            await self.bot.dummy_paginator(ctx, content, rows)
        else:
            content.description = "No data :("
            await ctx.send(embed=content)

    async def commandstats_single(self, ctx: commands.Context, command_name):
        """Stats of a single command"""
        command = self.bot.get_command(command_name)
        if command is None:
            raise commands.CommandError(
                f"Command `{ctx.prefix}{command_name}` does not exist!"
            )

        content = discord.Embed(
            title=f":bar_chart: `{ctx.prefix}{command.qualified_name}`"
        )

        # set command name to be tuple of subcommands if this is a command group
        group = hasattr(command, "commands")
        if group:
            command_name = tuple(
                [f"{command.name} {x.name}" for x in command.commands] + [command_name]
            )
        else:
            command_name = command.qualified_name

        total_uses: int = 0
        most_used_by_user_id: Optional[int] = None
        most_used_by_user_amount: int = 0
        most_used_by_guild_amount: int = 0
        most_used_by_guild_id: Optional[int] = None

        global_use_data = await self.bot.db.fetchrow(
            """
            SELECT SUM(uses) as total, user_id, MAX(uses) FROM command_usage
                WHERE command_type = 'internal'
                  AND command_name = ANY($1)
                GROUP BY user_id
            """,
            command_name,
        )
        if global_use_data:
            total_uses, most_used_by_user_id, most_used_by_user_amount = global_use_data

        content.add_field(name="Uses", value=total_uses)

        uses_by_guild_data = await self.bot.db.fetchrow(
            """
            SELECT guild_id, MAX(uses) FROM command_usage
                WHERE command_type = 'internal'
                  AND command_name = ANY($1)
                GROUP BY guild_id
            """,
            command_name,
        )
        if uses_by_guild_data:
            most_used_by_guild_id, most_used_by_guild_amount = uses_by_guild_data

        if ctx.guild:
            uses_in_this_server = (
                await self.bot.db.fetchval(
                    """
                    SELECT SUM(uses) FROM command_usage
                        WHERE command_type = 'internal'
                          AND command_name = ANY($1)
                          AND guild_id = $2
                    GROUP BY guild_id
                    """,
                    command_name,
                    ctx.guild.id,
                )
                or 0
            )
            content.add_field(name="on this server", value=uses_in_this_server)

        # show the data in embed fields
        if most_used_by_guild_id:
            content.add_field(
                name="Server most used in",
                value=f"{self.bot.get_guild(most_used_by_guild_id)} ({most_used_by_guild_amount})",
                inline=False,
            )

        if most_used_by_user_id:
            content.add_field(
                name="Most total uses by",
                value=f"{self.bot.get_user(most_used_by_user_id)} ({most_used_by_user_amount})",
            )

        # additional data for command groups
        if group:
            content.description = "Command Group"
            subcommands_tuple = tuple(
                f"{command.name} {x.name}" for x in command.commands
            )
            subcommand_usage = await self.bot.db.fetch(
                """
                SELECT command_name, SUM(uses) FROM command_usage
                    WHERE command_type = 'internal'
                      AND command_name = ANY($1)
                GROUP BY command_name ORDER BY SUM(uses) DESC
                """,
                subcommands_tuple,
            )
            if subcommand_usage:
                content.add_field(
                    name="Subcommand usage",
                    value="\n".join(f"{s[0]} - **{s[1]}**" for s in subcommand_usage),
                    inline=False,
                )

        await ctx.send(embed=content)

    @commands.command(name="authorize", aliases=["auth", "authorization"], hidden=True)
    @commands.is_owner()
    async def authorize(self, ctx, guild_id: int):
        if await self.bot.db.fetchrow(
            """SELECT * FROM auth WHERE guild_id = $1""", guild_id
        ):
            await self.bot.db.execute(
                """DELETE FROM auth WHERE guild_id = $1""", guild_id
            )
            s = "unauthorized"
        else:
            await self.bot.db.execute(
                """INSERT INTO auth (guild_id, ts) VALUES($1,$2) ON CONFLICT(guild_id) DO NOTHING""",
                guild_id,
                int(datetime.datetime.now().timestamp()),
            )
            s = "authorized"
        return await ctx.success(f"Successfully **{s}** the guild id `{guild_id}`")

    @commands.command(name="traceback", aliases=["tb", "trace"])
    @commands.is_owner()
    async def traceback(self, ctx: Context, code: str):
        data = await self.bot.db.fetchrow(
            """SELECT * FROM traceback WHERE error_code = $1""", code
        )
        if not data:
            return await ctx.fail(f"no error under code **{code}**")
        self.bot.get_guild(data.guild_id)  # type: ignore
        self.bot.get_channel(data.channel_id)  # type: ignore
        self.bot.get_user(data.user_id)  # type: ignore
        embed = discord.Embed(
            title=f"Error Code {code}", description=f"```{data.error_message}```"
        )
        embed.add_field(name="Context", value=f"`{data.content}`", inline=False)
        return await ctx.send(embed=embed)

    @commands.command(name="reset", description="reset term agreement process")
    async def reset(self, ctx: Context, *, member: discord.Member = None):
        if member:
            if ctx.author.id not in self.bot.owner_ids:
                return
            await self.bot.db.execute(
                """DELETE FROM terms_agreement WHERE user_id = $1""", member.id
            )
            return await ctx.success(
                f" {member.mention}'s **Agreement policy** has been **reset**"
            )
        await self.bot.db.execute(
            "DELETE FROM terms_agreement WHERE user_id = $1", ctx.author.id
        )
        return await ctx.success("**Agreement policy** has been **reset**")

    @commands.command(name="restart", hidden=True)
    @commands.is_owner()
    async def restart(self, ctx):
        await ctx.success("**Restarting bot...**")
        os.execv(sys.executable, ["python"] + sys.argv)

    @commands.command(name="globalban", hidden=True)
    @commands.is_owner()
    async def globalban(self, ctx, user: Union[User, Member], *, reason: str):
        if await self.bot.db.fetch(
            """SELECT reason FROM globalbans WHERE user_id = $1""", user.id
        ):
            await self.bot.db.execute(
                """DELETE FROM globalbans WHERE user_id = $1""", user.id
            )
            return await ctx.success(
                f"successfully unglobally banned {user.mention} ({user.id})"
            )
        else:
            await self.bot.db.execute(
                """INSERT INTO globalbans (user_id, reason) VALUES ($1, $2)""",
                user.id,
                reason,
            )
            bans = await self.do_global_ban(user, reason)
            return await ctx.success(
                f"**Global banned** {user.mention} ({user.id}) from **{bans} guilds**"
            )

    @commands.command(aliases=["guilds"], hidden=True)
    @commands.is_owner()
    async def guildlist(
        self, ctx, s: Optional[Union[discord.Member, discord.User]] = None
    ):
        if s is None:
            m = self.bot.guilds
            n = self.bot.user.name
        else:
            m = s.mutual_guilds
            n = s.name
        if len(m) == 0:
            return await ctx.fail("no guilds in mutuals")
        embeds = []
        ret = []
        num = 0
        pagenum = 0

        for i in sorted(m, key=lambda x: len(x.members), reverse=True):
            num += 1
            ret.append(f"`{num}.` **{i.name}**(``{i.id}``) - {len(i.members):,}")
            pages = [p for p in discord.utils.as_chunks(ret, 10)]

        for page in pages:
            pagenum += 1
            embeds.append(
                discord.Embed(
                    color=self.bot.color,
                    title=f"{n}'s guilds",
                    description="\n".join(page),
                )
                .set_author(
                    name=ctx.author.display_name, icon_url=ctx.author.display_avatar
                )
                .set_footer(
                    text=f"Page {pagenum}/{len(pages)}({len(self.bot.guilds)} entries)"
                )
            )

        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0])

        return await ctx.paginate(embeds)

    @commands.command(name="unbanowner", hidden=True)
    @commands.is_owner()
    async def unban_owner(self, ctx, guild_id: int):
        """
        Unban the owner of the bot from a guild.

        Parameters:
        - guild_id (int): The ID of the guild to unban the owner from.
        """
        guild = self.bot.get_guild(guild_id)

        if not guild:
            return await ctx.fail(
                "Invalid guild ID. Make sure the bot is in the specified guild."
            )

        owner_id = await self.bot.application_info()
        owner_id = owner_id.owner.id

        try:
            await guild.unban(discord.Object(owner_id))
            await ctx.success(
                f"Successfully unbanned the bot owner from {guild.name}({guild.id})"
            )
        except discord.HTTPException:
            await ctx.fail(
                "Failed to unban the bot owner. Check the bot's permissions."
            )

    @commands.command(hidden=True)
    @commands.is_owner()
    async def leaveserver(self, ctx, guild: discord.Guild):
        await guild.leave()
        await ctx.success(f"Left **{guild.name}** (`{guild.id}`)")

    @commands.command(aliases=["link"], hidden=True)
    @commands.is_owner()
    async def guildinvite(self, ctx, *, guild: discord.Guild):
        guild = self.bot.get_guild(guild.id)
        link = await random.choice(guild.text_channels).create_invite(
            max_age=0, max_uses=0
        )
        await ctx.send(link)

    @commands.command(name="eval", hidden=True)
    @commands.is_owner()
    async def _eval(self, ctx, *, argument: codeblock_converter):
        await ctx.invoke(self.bot.get_command("jishaku py"), argument=argument)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sql(self, ctx, *, query: str):
        from jishaku.codeblocks import codeblock_converter as cc

        parts = query.split(" | ")
        query = parts[0]
        if len(parts) == 2:
            parts[1].split()  # type: ignore

        if "select" in query.lower():
            method = "fetch"
        else:
            method = "execute"
        await ctx.invoke(
            self.bot.get_command("eval"),
            argument=cc(f"""await bot.db.{method}(f'{query.split(' || ')[0]}')"""),
        )

    @commands.group(name="blacklist", invoke_without_command=True, hidden=True)
    @commands.is_owner()
    async def blacklist(self, ctx):
        """Blacklist users from using the bot"""

        return await ctx.send_help()

    @blacklist.command(name="add", hidden=True)
    @commands.is_owner()
    async def blacklist_add(
        self,
        ctx,
        user: Union[discord.User, discord.Guild, int],
        note: str = "No reason specified",
    ):
        """Blacklist someone from using the bot"""
        if isinstance(user, (discord.Guild, int)):
            object_id = user.id or user
            object_type = "guild_id"
        else:
            object_id = user.id
            object_type = "user_id"
        try:
            await self.bot.db.execute(
                """ 
                INSERT INTO blacklisted
                (object_id, object_type, blacklist_author, reason)
                VALUES ($1, $2, $3, $4)
                """,
                object_id,
                object_type,
                ctx.author.id,
                note,
            )

        except Exception:
            return await ctx.fail(f"User {user.mention} is already **blacklisted**")

        else:
            return await ctx.success(
                f"User {user.mention} has been **blacklisted** - {note}"
            )

    @blacklist.command(name="remove", hidden=True)
    @commands.is_owner()
    async def blacklist_remove(
        self, ctx, user: Union[discord.User, discord.Guild, int]
    ):
        """Unblacklist a user"""
        if isinstance(user, (discord.Guild, int)):
            object_id = user.id or user
            object_type = "guild_id"
            m = object_id
        else:
            object_id = user.id
            m = user.mention
            object_type = "user_id"
        if data := await self.bot.db.fetch(  # type: ignore  # noqa: F841
            """
            SELECT object_id
            FROM blacklisted
            WHERE object_id = $1
            """,
            object_id,
        ):
            await self.bot.db.execute(
                """
                DELETE FROM blacklisted
                WHERE object_id = $1
                """,
                object_id,
            )

            return await ctx.success(
                f"{'User' if object_type == 'user_id' else 'Guild'} {m} {user.mention} has been **unblacklisted**"
            )

        else:
            return await ctx.fail(
                f"{'User' if object_type == 'user_id' else 'Guild'} {m} isn't ** blacklisted**, maybe you meant to do `, reset`?"
            )

    @blacklist.command(name="list", aliases=["show", "view"], hidden=True)
    @commands.is_owner()
    async def blacklist_list(self, ctx):
        """View blacklisted users"""

        if data := await self.bot.db.fetch(
            """
            SELECT *
            FROM blacklisted
            """
        ):
            num = 0
            page = 0
            users = []
            for table in data:
                if table["object_type"] == "guild_id":
                    m = table["object_id"]
                else:
                    m = (await self.bot.fetch_user(table[0])).mention
                note = table[1]
                num += 1
                users.append(f"`{num}` {m} ({note})")

            embeds = []
            users = [m for m in discord.utils.as_chunks(users, 10)]

            for lines in users:
                page += 1
                embed = discord.Embed(
                    title="Blacklist",
                    description="\n".join(lines),
                    color=self.bot.color,
                )

                embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar)

                embed.set_footer(
                    text=f"Page {page}/{len(users)} ({len(data[0])} entries)"
                )

                embeds.append(embed)
            if len(data[0]) < 10:
                await ctx.send(embed=embed)

            else:
                await ctx.paginate(embeds)

        else:
            return await ctx.fail("Nobody is **blacklisted**")

    @commands.hybrid_command(name="changepfp", aliases=["setpfp"], hidden=True)
    @commands.is_owner()
    async def changepfp(self, ctx, url):
        """Change the bot's pfp"""

        session = await self.bot.session.get(url)
        await self.bot.user.edit(avatar=await session.read())
        await ctx.success(f"Changed the bot's pfp to **[image]({url})**")


async def setup(bot):
    await bot.add_cog(Owner(bot))
