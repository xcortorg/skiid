import datetime
import re

import google.generativeai as genai
from discord import AllowedMentions, Embed, Interaction, Member, User, utils
from discord.ext import commands
from discord.ext.commands import (Cog, bot_has_guild_permissions, command,
                                  group, has_guild_permissions, hybrid_command,
                                  max_concurrency)
from tools.bot import Akari
from tools.converters import NoStaff
from tools.helpers import AkariContext
from tools.predicates import create_reskin, has_perks
from tools.validators import ValidReskinName


class Donor(Cog):
    def __init__(self, bot: Akari):
        self.bot = bot
        self.description = "Premium commands"

        genai.configure(api_key="AIzaSyCDSm6b1aI84TJtzWKzdb6oVozeWe3etD8")
        self.model = genai.GenerativeModel("gemini-pro")

    def shorten(self, value: str, length: int = 32):
        if len(value) > length:
            value = value[: length - 2] + ("..." if len(value) > length else "").strip()
        return value

    @Cog.listener()
    async def on_user_update(self, before: User, after: User):
        if before.discriminator == "0":
            if before.name != after.name:
                if not self.bot.cache.get("pomelo"):
                    await self.bot.cache.set(
                        "pomelo",
                        [
                            {
                                "username": before.name,
                                "time": utils.format_dt(
                                    datetime.datetime.now(), style="R"
                                ),
                            }
                        ],
                    )
                else:
                    lol = self.bot.cache.get("pomelo")
                    lol.append(
                        {
                            "username": before.name,
                            "time": utils.format_dt(datetime.datetime.now(), style="R"),
                        }
                    )
                    await self.bot.cache.set("pomelo", lol)

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if str(before.nick) != str(after.nick):
            if nickname := await self.bot.db.fetchval(
                "SELECT nickname FROM force_nick WHERE guild_id = $1 AND user_id = $2",
                before.guild.id,
                before.id,
            ):
                if after.nick != nickname:
                    await after.edit(
                        nick=nickname, reason="Force nickname applied to this member"
                    )

    @command(aliases=["pomelo", "handles"], brief="donor")
    @has_perks()
    async def lookup(self, ctx: AkariContext):
        """get the most recent handles"""
        if not self.bot.cache.get("pomelo"):
            return await ctx.error("There is nothing to see here")
        pomelo = self.bot.cache.get("pomelo")
        return await ctx.paginate(
            [f"{m['username']} - {m['time']}" for m in pomelo[::-1]],
            f"Pomelo Usernames ({len(pomelo)})",
        )

    @command(aliases=["sp"], brief="donor")
    @has_perks()
    async def selfpurge(self, ctx: AkariContext, amount: int = 100):
        """delete your own messages"""
        await ctx.channel.purge(
            limit=amount,
            check=lambda m: m.author.id == ctx.author.id and not m.pinned,
            bulk=True,
        )

    @command(
        brief="manage nicknames & donor",
        aliases=["forcenick", "fn"],
    )
    @has_perks()
    @has_guild_permissions(manage_nicknames=True)
    @bot_has_guild_permissions(manage_nicknames=True)
    async def forcenickname(
        self, ctx: AkariContext, member: NoStaff, *, nickname: str = None
    ):
        """lock a nickname to a member"""
        if not nickname:
            if await self.bot.db.fetchrow(
                "SELECT * FROM force_nick WHERE guild_id = $1 AND user_id = $2",
                ctx.guild.id,
                member.id,
            ):
                await self.bot.db.execute(
                    "DELETE FROM force_nick WHERE guild_id = $1 AND user_id = $2",
                    ctx.guild.id,
                    member.id,
                )
                await member.edit(
                    nick=None, reason="Removed the force nickname from this member"
                )
                return await ctx.success("Removed the nickname from this member")
            else:
                return await ctx.send_help(ctx.command)
        else:
            if await self.bot.db.fetchrow(
                "SELECT * FROM force_nick WHERE guild_id = $1 AND user_id = $2",
                ctx.guild.id,
                member.id,
            ):
                await self.bot.db.execute(
                    "UPDATE force_nick SET nickname = $1 WHERE guild_id = $2 AND user_id = $3",
                    nickname,
                    ctx.guild.id,
                    member.id,
                )
                await member.edit(
                    nick=nickname, reason="Force nickname applied to this member"
                )
            else:
                await member.edit(
                    nick=nickname, reason="Force nickname applied to this member"
                )
                await self.bot.db.execute(
                    "INSERT INTO force_nick VALUES ($1,$2,$3)",
                    ctx.guild.id,
                    member.id,
                    nickname,
                )
            await ctx.success(f"Force nicknamed {member.mention} to **{nickname}**")

    @group(invoke_without_command=True)
    async def reskin(self, ctx: AkariContext):
        await ctx.create_pages()

    @reskin.command(name="enable", brief="donor")
    @has_perks()
    async def reskin_enable(self, ctx: AkariContext):
        """Enable reskin"""

        reskin = await self.bot.db.fetchrow(
            "SELECT * FROM reskin_user WHERE user_id = $1 AND toggled = $2",
            ctx.author.id,
            False,
        )

        if reskin == None or reskin["toggled"] == False:

            if not await self.bot.db.fetchrow(
                "SELECT * FROM reskin_user WHERE user_id = $1", ctx.author.id
            ):
                await self.bot.db.execute(
                    "INSERT INTO reskin_user (user_id, toggled, name, avatar) VALUES ($1, $2, $3, $4)",
                    ctx.author.id,
                    True,
                    ctx.author.name,
                    ctx.author.avatar.url,
                )

            else:
                await self.bot.db.execute(
                    "UPDATE reskin_user SET toggled = $1 WHERE user_id = $2",
                    True,
                    ctx.author.id,
                )

            return await ctx.success("**Reskin** has been **enabled**.")

        return await ctx.warning("**Reskin** is already **enabled**.")

    @reskin.command(name="disable", brief="donor")
    @has_perks()
    async def reskin_disable(self, ctx: AkariContext):
        """Disable the reskin feature for yourself"""
        if not await self.bot.db.fetchrow(
            "SELECT * FROM reskin_user WHERE user_id = $1", ctx.author.id
        ):
            return await ctx.warning("Reskin is **not** enabled")

        await self.bot.db.execute(
            "DELETE FROM reskin_user WHERE user_id = $1", ctx.author.id
        )
        return await ctx.success("Reskin is now disabled")

    @reskin.command(name="name", brief="donor")
    @has_perks()
    @create_reskin()
    async def reskin_name(self, ctx: AkariContext, *, name: ValidReskinName):
        """Edit your reskin name"""
        await self.bot.db.execute(
            "UPDATE reskin_user SET user = $1 WHERE user_id = $2", name, ctx.author.id
        )
        return await ctx.success(f"Updated your reskin name to **{name}**")

    @reskin.command(name="avatar", brief="donor", aliases=["icon", "pfp", "av"])
    @has_perks()
    @create_reskin()
    async def reskin_avatar(self, ctx: AkariContext, url: str = None):
        """change your reskin's avatar"""
        if url is None:
            url = await ctx.get_attachment()
            if not url:
                return ctx.send_help(ctx.command)
            else:
                url = url.url

        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        if not re.findall(regex, url):
            return await ctx.error("The image provided is not an url")

        await self.bot.db.execute(
            "UPDATE reskin_user SET avatar = $1 WHERE user_id = $2", url, ctx.author.id
        )
        return await ctx.success(f"Updated your reskin [**avatar**]({url})")

    @reskin.command(name="remove", brief="donor", aliases=["delete", "reset"])
    async def reskin_delete(self, ctx: AkariContext):
        """Delete your reskin"""

        async def yes_callback(interaction: Interaction):
            await self.bot.db.execute(
                "DELETE FROM reskin_user WHERE user_id = $1", ctx.author.id
            )
            await interaction.response.edit_message(
                embed=Embed(
                    description=f"{self.bot.yes} {ctx.author.mention}: Removed your **reskin**",
                    color=self.bot.yes_color,
                ),
                view=None,
            )

        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(
                embed=Embed(
                    description=f"{ctx.author.mention}: Cancelling action...",
                    color=self.bot.color,
                ),
                view=None,
            )

        return await ctx.confirmation_send(
            f"Are you sure you want to **remove** your reskin?",
            yes_callback,
            no_callback,
        )

    @hybrid_command(name="chatgpt", aliases=["chat", "gpt", "ask"], brief="donor")
    @has_perks()
    @max_concurrency(1, commands.BucketType.user, wait=True)
    async def chatgpt(self, ctx: AkariContext, *, query: str):
        """
        Talk to AI
        """

        async with ctx.channel.typing():
            response = await self.bot.loop.run_in_executor(
                self.bot.executor, self.model.generate_content, query
            )
            await ctx.reply(response.text, allowed_mentions=AllowedMentions.none())

    @command(brief="donor")
    @has_perks()
    async def uwulock(self, ctx: AkariContext, user: User):
        """uwulock"""
        if await self.bot.db.fetchrow(
            "SELECT * FROM uwu_lock WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            user.id,
        ):
            await self.bot.db.execute(
                "DELETE FROM uwu_lock WHERE guild_id = $1 AND user_id = $2",
                ctx.guild.id,
                user.id,
            )
            return await ctx.success(f"{user.mention} is no longer uwulocked")
        await self.bot.db.execute(
            "INSERT INTO uwu_lock VALUES ($1, $2)", ctx.guild.id, user.id
        )
        return await ctx.success(f"{user.mention} is now uwulocked")


async def setup(bot: Akari) -> None:
    await bot.add_cog(Donor(bot))
