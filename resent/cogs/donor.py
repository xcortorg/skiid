from typing import Union

import discord
import uwuipy
from discord.ext import commands
from utils.permissions import Permissions

valid = [
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
]


def key(s):
    return s[2]


async def uwuthing(bot, text: str) -> str:
    uwu = uwuipy.uwuipy()
    return uwu.uwuify(text)


def premium():
    async def predicate(ctx: commands.Context):
        if ctx.command.name in ["hardban", "uwulock", "unhardban"]:
            if ctx.author.id == ctx.guild.owner_id:
                return True
        check = await ctx.bot.db.fetchrow(
            "SELECT * FROM donor WHERE user_id = {}".format(ctx.author.id)
        )
        res = await ctx.bot.db.fetchrow(
            "SELECT * FROM authorize WHERE guild_id = $1 AND tags = $2",
            ctx.guild.id,
            "true",
        )
        if check is None and res is None:
            await ctx.send_warning("Donator only")
            return False
        return True

    return commands.check(predicate)


class donor(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @commands.command(
        description="revoke the hardban from an user",
        help="donor",
        usage="[user]",
        brief="ban_members",
    )
    @Permissions.has_permission(administrator=True)
    async def hardunban(self, ctx: commands.Context, *, member: discord.User):
        che = await self.bot.db.fetchrow(
            "SELECT * FROM hardban WHERE guild_id = {} AND banned = {}".format(
                ctx.guild.id, member.id
            )
        )
        if che is None:
            return await ctx.send_warning(f"{member} is **not** hardbanned")
        await self.bot.db.execute(
            "DELETE FROM hardban WHERE guild_id = {} AND banned = {}".format(
                ctx.guild.id, member.id
            )
        )
        await ctx.guild.unban(member, reason="unhardbanned by {}".format(ctx.author))
        await ctx.message.add_reaction("<:approved:1209081187679862784>")

    @commands.command(
        description="hardunban an user from the server",
        help="donor",
        usage="[user]",
        brief="ban_members",
    )
    @Permissions.has_permission(administrator=True)
    async def hardban(
        self, ctx: commands.Context, *, member: Union[discord.Member, discord.User]
    ):
        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot hardban*{member.mention}")
        che = await self.bot.db.fetchrow(
            "SELECT * FROM hardban WHERE guild_id = {} AND banned = {}".format(
                ctx.guild.id, member.id
            )
        )
        if che is not None:
            return await ctx.send_warning(
                f"**{member}** has been hardbanned by **{await self.bot.fetch_user(che['author'])}**"
            )
        await ctx.guild.ban(member, reason="hardbanned by {}".format(ctx.author))
        await self.bot.db.execute(
            "INSERT INTO hardban VALUES ($1,$2,$3)",
            ctx.guild.id,
            member.id,
            ctx.author.id,
        )
        await ctx.message.add_reaction("<:approved:1209081187679862784>")

    @commands.command(
        description="uwuify a person's messages",
        help="donor",
        usage="[member]",
        brief="administrator",
    )
    @Permissions.has_permission(manage_messages=True)
    async def uwulock(self, ctx: commands.Context, *, member: discord.Member):
        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot uwulock*{member.mention}")
        check = await self.bot.db.fetchrow(
            "SELECT user_id FROM uwulock WHERE user_id = {} AND guild_id = {}".format(
                member.id, ctx.guild.id
            )
        )
        if check is None:
            await self.bot.db.execute(
                "INSERT INTO uwulock VALUES ($1,$2)", ctx.guild.id, member.id
            )
        else:
            await self.bot.db.execute(
                "DELETE FROM uwulock WHERE user_id = {} AND guild_id = {}".format(
                    member.id, ctx.guild.id
                )
            )
        return await ctx.message.add_reaction("<:approved:1209081187679862784>")

    @commands.command(
        aliases=["stfu"],
        description="delete a person's messages",
        help="donor",
        usage="[member]",
        brief="manage messages",
    )
    @Permissions.has_permission(manage_messages=True)
    async def shutup(self, ctx: commands.Context, *, member: discord.Member):
        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot shutup*{member.mention}")
        check = await self.bot.db.fetchrow(
            "SELECT user_id FROM shutup WHERE user_id = {} AND guild_id = {}".format(
                member.id, ctx.guild.id
            )
        )
        if check is None:
            await self.bot.db.execute(
                "INSERT INTO shutup VALUES ($1,$2)", ctx.guild.id, member.id
            )
        else:
            await self.bot.db.execute(
                "DELETE FROM shutup WHERE user_id = {} AND guild_id = {}".format(
                    member.id, ctx.guild.id
                )
            )
        return await ctx.message.add_reaction("<:approved:1209081187679862784>")

    @commands.command(
        description="force nicknames an user",
        help="donor",
        usage="[member] [nickname]\nif none is passed as nickname, the force nickname gets removed",
        aliases=["locknick"],
        brief="manage nicknames",
    )
    @Permissions.has_permission(manage_nicknames=True)
    async def forcenick(
        self, ctx: commands.Context, member: discord.Member, *, nick: str
    ):
        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot forcenick*{member.mention}")
        if nick.lower() == "none":
            check = await self.bot.db.fetchrow(
                "SELECT * FROM forcenick WHERE user_id = {} AND guild_id = {}".format(
                    member.id, ctx.guild.id
                )
            )
            if check is None:
                return await ctx.send_warning(f"**No** forcenick found for {member}")
            await self.bot.db.execute(
                "DELETE FROM forcenick WHERE user_id = {} AND guild_id = {}".format(
                    member.id, ctx.guild.id
                )
            )
            await member.edit(nick=None, reason="forcenick disabled")
            await ctx.message.add_reaction("<:approved:1209081187679862784>")
        else:
            check = await self.bot.db.fetchrow(
                "SELECT * FROM forcenick WHERE user_id = {} AND guild_id = {}".format(
                    member.id, ctx.guild.id
                )
            )
            if check is None:
                await self.bot.db.execute(
                    "INSERT INTO forcenick VALUES ($1,$2,$3)",
                    ctx.guild.id,
                    member.id,
                    nick,
                )
            else:
                await self.bot.db.execute(
                    "UPDATE forcenick SET nickname = '{}' WHERE user_id = {} AND guild_id = {}".format(
                        nick, member.id, ctx.guild.id
                    )
                )
            await member.edit(nick=nick, reason="forcenick enabled")
            await ctx.message.add_reaction("<:approved:1209081187679862784>")

    @commands.command(
        description="purges an amount of messages sent by you",
        help="donor",
        usage="[amount]",
    )
    async def selfpurge(self, ctx: commands.Context, amount: int):
        mes = []
        async for message in ctx.channel.history():
            if len(mes) == amount + 1:
                break
            if message.author == ctx.author:
                mes.append(message)

        await ctx.channel.delete_messages(mes)

    @commands.group(
        invoke_without_command=True, name="reskin", description="Reskin Settings"
    )
    async def reskin(self, ctx: commands.Context):
        return await ctx.create_pages()

    @reskin.command(
        name="enable", description="Reskin Enable", help="reskin", aliases=["on"]
    )
    async def reskin_enable(self, ctx: commands.Context):
        reskin = await self.bot.db.fetchrow(
            "SELECT * FROM reskin WHERE user_id = $1 AND toggled = $2",
            ctx.author.id,
            False,
        )

        # TODO: Clean this up
        if reskin == None or reskin["toggled"] == False:
            if not await self.bot.db.fetchrow(
                "SELECT * FROM reskin WHERE user_id = $1", ctx.author.id
            ):
                await self.bot.db.execute(
                    "INSERT INTO reskin (user_id, toggled, name, avatar) VALUES ($1, $2, $3, $4)",
                    ctx.author.id,
                    True,
                    ctx.author.name,
                    ctx.author.avatar.url,
                )
            else:
                await self.bot.db.execute(
                    "UPDATE reskin SET toggled = $1 WHERE user_id = $2",
                    True,
                    ctx.author.id,
                )
            return await ctx.send_success("**reskin** has been **enabled**.")

        return await ctx.send_warning("**reskin** is already **enabled**...")

    @reskin.command(
        name="disable", description="Reskin Disable", help="reskin", aliases=["off"]
    )
    async def reskin_disable(self, ctx: commands.Context):
        reskin = await self.bot.db.fetchrow(
            "SELECT * FROM reskin WHERE user_id = $1 AND toggled = $2",
            ctx.author.id,
            True,
        )

        if reskin != None and reskin["toggled"] == True:
            await self.bot.db.execute(
                "UPDATE reskin SET toggled = $1 WHERE user_id = $2",
                False,
                ctx.author.id,
            )
            return await ctx.send_success("**reskin** has been **disabled**.")

        await self.bot.db.execute(
            "UPDATE reskin SET toggled = $1 WHERE user_id = $2", False, ctx.author.id
        )
        return await ctx.send_warning("**reskin** is already **disabled**.")

    @reskin.command(name="name", description="Reskin Name", help="reskin")
    async def reskin_name(self, ctx: commands.Context, *, name: str = None):
        reskin = await self.bot.db.fetchrow(
            "SELECT * FROM reskin WHERE user_id = $1", ctx.author.id
        )

        ## TODO: Tidy
        if not reskin:
            await self.bot.db.execute(
                "INSERT INTO reskin (user_id, toggled, name, avatar) VALUES ($1, $2, $3, $4)",
                ctx.author.id,
                True,
                name,
                ctx.author.avatar.url,
            )
        else:
            await self.bot.db.execute(
                "UPDATE reskin SET name = $1 WHERE user_id = $2", name, ctx.author.id
            )

        if name == None or name.lower() == "none":
            return await ctx.send_success(f"Set **reskin** name to `{ctx.author.name}`")

        return await ctx.send_success(f"Set **reskin** name to `{name}`")

    @reskin.command(
        name="avatar", description="Reskin Avatar", aliases=["av"], help="reskin"
    )
    async def reskin_avatar(self, ctx: commands.Context, url: str = None):
        if url == None and len(ctx.message.attachments) == 0:
            return await ctx.send_warning(
                "You **need** to provide an avatar, either as a **file** or **url**"
            )

        if url == None and len(ctx.message.attachments) > 0:
            url = ctx.message.attachments[0].url

        reskin = await self.bot.db.fetchrow(
            "SELECT * FROM reskin WHERE user_id = $1", ctx.author.id
        )

        ## TODO: Tidy
        if not reskin:
            await self.bot.db.execute(
                "INSERT INTO reskin (user_id, toggled, name, avatar) VALUES ($1, $2, $3, $4)",
                ctx.author.id,
                True,
                ctx.author.name,
                url,
            )
        else:
            await self.bot.db.execute(
                "UPDATE reskin SET avatar = $1 WHERE user_id = $2", url, ctx.author.id
            )

        return await ctx.send_success(f"Set **reskin** avatar to [**image**]({url})")


async def setup(bot) -> None:
    await bot.add_cog(donor(bot))
