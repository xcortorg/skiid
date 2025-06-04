import datetime
from platform import python_version

import git
from discord import Embed, Permissions, User, __version__, utils
from discord.ext.commands import Cog, command, hybrid_command
from discord.ui import Button, View
from tools.bot import Akari
from tools.helpers import AkariContext

REPO_PATH = "/root/AkariBot/.git"


class Info(Cog):
    def __init__(self, bot: Akari):
        self.bot = bot
        self.description = "Information commands"

    def create_bot_invite(self, user: User) -> View:
        """
        Create a view containing a button with the bot invite url
        """

        view = View()
        view.add_item(
            Button(
                label=f"invite {user.name}",
                url=utils.oauth_url(client_id=user.id, permissions=Permissions(8)),
            )
        )
        return view

    @hybrid_command(name="commands", aliases=["h", "cmds"])
    async def _help(self, ctx: AkariContext, *, command: str = None):
        """
        The help command menu
        """

        if not command:
            return await ctx.send_help()
        else:
            _command = self.bot.get_command(command)
            if (
                _command is None
                or (cog := _command.cog_name)
                and cog.lower() in ["jishaku", "owner", "auth"]
                or _command.hidden
            ):
                return await ctx.reply(f'No command called "{command}" found.')

            return await ctx.send_help(_command)

    @command()
    async def getbotinvite(self, ctx: AkariContext, *, member: User):
        """
        Get the bot invite based on it's id
        """

        if not member.bot:
            return await ctx.error("This is **not** a bot")

        await ctx.reply(ctx.author.mention, view=self.create_bot_invite(member))

    @hybrid_command()
    async def ping(self, ctx: AkariContext):
        """
        Displays the bot's latency
        """

        await ctx.reply(
            embed=Embed(
                color=self.bot.color,
                description=f"📡 {ctx.author.mention}: ping `{round(self.bot.latency * 1000)}ms`",
            )
        )

    @hybrid_command(aliases=["up"])
    async def uptime(self, ctx: AkariContext):
        """
        Displays how long has the bot been online for
        """

        return await ctx.reply(
            embed=Embed(
                color=self.bot.color,
                description=f"🕰️ {ctx.author.mention}: **{self.bot.uptime}**",
            )
        )

    @hybrid_command(aliases=["bi", "bot", "info", "about"])
    async def botinfo(self, ctx: AkariContext):
        """
        Displays information about the bot
        """

        repo = git.Repo(REPO_PATH)
        commit = repo.head.commit
        commit_hash = commit.hexsha[:7]

        embed = (
            Embed(
                color=self.bot.color,
                description=f"Premium multi-purpose Discord bot made by [**The Akari Team**](https://discord.gg/akaribot)\nUsed by **{sum(g.member_count for g in self.bot.guilds):,}** members in **{len(self.bot.guilds):,}** servers\nDevelopers: [Nick](https://discord.com/users/863914425445908490) **&** [Sin](https://discord.com/users/598125772754124823)",
                timestamp=datetime.datetime.now(),
            )
            .set_author(
                name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url
            )
            .add_field(
                name="System",
                value=f"**commands:** {len(set(self.bot.walk_commands()))}\n**discord.py:** {__version__}\n**Python:** {python_version()}\n**Lines:** {self.bot.lines:,}\n**Uptime:** {self.bot.uptime}",
            )
            .set_footer(text=f"Latest Commit: {commit_hash}")
            .set_thumbnail(url=self.bot.user.avatar.url)
        )

        await ctx.reply(embed=embed)

    @hybrid_command()
    async def shards(self, ctx: AkariContext):
        """
        Check status of each bot shard
        """

        embed = Embed(
            color=self.bot.color, title=f"Total shards ({self.bot.shard_count})"
        )

        for shard in self.bot.shards:
            guilds = [g for g in self.bot.guilds if g.shard_id == shard]
            users = sum([g.member_count for g in guilds])
            embed.add_field(
                name=f"Shard {shard}",
                value=f"**ping**: {round(self.bot.shards.get(shard).latency * 1000)}ms\n**guilds**: {len(guilds)}\n**users**: {users:,}",
                inline=False,
            )

        await ctx.reply(embed=embed)

    @hybrid_command(aliases=["inv", "link"])
    async def invite(self, ctx: AkariContext):
        """
        Send an invite link of the bot
        """

        await ctx.reply(ctx.author.mention, view=self.create_bot_invite(ctx.guild.me))

    @hybrid_command(name="credits")
    async def credits(self, ctx: AkariContext):
        """
        Get more specific credits for the bot
        """

        embed = Embed(
            description=f"[**Nick**](<https://discord.com/users/863914425445908490>): Developer\n[**Sin**](<https://discord.com/users/598125772754124823>): Developer\n[**Lina**](https://discord.com/users/1082206057213988864): Akari name idea",
            color=self.bot.color,
        ).set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)

        await ctx.reply(embed=embed)


async def setup(bot: Akari) -> None:
    return await bot.add_cog(Info(bot))
