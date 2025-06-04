import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, List, Literal, Optional

import discord
from discord.channel import TextChannel

from grief.core import Config, app_commands, commands
from grief.core.bot import Grief

from .components.setup import SetupModal, StartSetupView
from .poll import Poll
from .vexutils import format_help, format_info, get_vex_logger
from .vexutils.loop import VexLoop

log = get_vex_logger(__name__)


class ButtonPoll(commands.Cog):
    """Create polls using buttons."""

    def __init__(self, bot: Grief) -> None:
        self.bot = bot

        self.config: Config = Config.get_conf(
            self, 418078199982063626, force_registration=True
        )
        self.config.register_guild(
            poll_settings={},
            poll_user_choices={},
        )

        self.loop = bot.loop.create_task(self.buttonpoll_loop())
        self.loop_meta = VexLoop("ButtonPoll", 60.0)

        self.polls: List[Poll] = []

        self.plot_executor = ThreadPoolExecutor(
            max_workers=16, thread_name_prefix="buttonpoll_plot"
        )

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        for g_id, g_polls in (await self.config.all_guilds()).items():
            for poll_id, poll in g_polls["poll_user_choices"].items():
                for user, vote in poll.items():
                    if user == str(user_id):
                        async with self.config.guild_from_id(
                            g_id
                        ).poll_user_choices() as user_choices:
                            del user_choices[poll_id][user]

    async def cog_unload(self) -> None:
        self.loop.cancel()
        self.bot.remove_dev_env_value("bpoll")
        for poll in self.polls:
            poll.view.stop()

        self.plot_executor.shutdown(wait=False)

        log.verbose("buttonpoll successfully unloaded")

    async def cog_load(self) -> None:
        # re-initialise views
        all_polls = await self.config.all_guilds()
        for guild_polls in all_polls.values():
            for poll in guild_polls["poll_settings"].values():
                obj_poll = Poll.from_dict(poll, self)
                self.polls.append(obj_poll)
                self.bot.add_view(obj_poll.view, message_id=obj_poll.message_id)
                log.debug(f"Re-initialised view for poll {obj_poll.unique_poll_id}")

    @commands.guild_only()  # type:ignore
    @commands.bot_has_permissions(embed_links=True)
    @commands.mod_or_permissions(manage_messages=True)
    @commands.hybrid_command(name="poll")
    @app_commands.describe(
        chan="Optional channel. If not specified, the current channel is used."
    )
    @app_commands.default_permissions(manage_messages=True)
    async def buttonpoll(
        self, ctx: commands.Context, chan: Optional[TextChannel] = None
    ):
        """
        Start a button-based poll

        This is an interactive setup. By default the current channel will be used,
        but if you want to start a poll remotely you can send the channel name
        along with the buttonpoll command.
        """
        channel = chan or ctx.channel
        if TYPE_CHECKING:
            assert isinstance(channel, (TextChannel, discord.Thread))
            assert isinstance(ctx.author, discord.Member)

        # these two checks are untested :)
        if not channel.permissions_for(ctx.author).send_messages:
            return await ctx.send(
                f"You don't have permission to send messages in {channel.mention}, so I can't "
                "start a poll there."
            )
        if not channel.permissions_for(ctx.me).send_messages:
            return await ctx.send(
                f"I don't have permission to send messages in {channel.mention}, so I can't "
                "start a poll there."
            )

        if ctx.interaction:
            modal = SetupModal(author=ctx.author, channel=channel, cog=self)
            await ctx.interaction.response.send_modal(modal)
        else:
            view = StartSetupView(author=ctx.author, channel=channel, cog=self)
            await ctx.send("Click bellow to start a poll!", view=view)

    async def buttonpoll_loop(self):
        await self.bot.wait_until_red_ready()
        while True:
            try:
                log.verbose("ButtonPoll loop starting.")
                self.loop_meta.iter_start()
                await self.check_for_finished_polls()
                self.loop_meta.iter_finish()
                log.verbose("ButtonPoll loop finished.")
            except Exception as e:
                log.exception(
                    "Something went wrong with the ButtonPoll loop. Please report this in grief support server.",
                    exc_info=e,
                )
                self.loop_meta.iter_error(e)

            await self.loop_meta.sleep_until_next()

    async def check_for_finished_polls(self):
        polls = self.polls.copy()
        for poll in polls:
            if poll.poll_finish < datetime.datetime.now(datetime.timezone.utc):
                log.info(f"Poll {poll.unique_poll_id} has finished.")
                await poll.finish()
                poll.view.stop()
                self.polls.remove(poll)
