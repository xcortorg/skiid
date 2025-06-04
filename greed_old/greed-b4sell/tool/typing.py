import asyncio
import discord
from discord.ext import commands
from typing import Optional


def handle_typing_task_completion(fut: asyncio.Future) -> None:
    """
    Callback for handling task completion or exceptions in typing tasks.
    """
    try:
        fut.exception()
    except (asyncio.CancelledError, Exception):
        pass


class Typing:
    """
    A context manager for handling typing indicators in a Discord channel.
    """

    def __init__(self, ctx: commands.Context) -> None:
        self.loop: asyncio.AbstractEventLoop = ctx.bot.loop
        self.channel: discord.TextChannel = ctx.channel
        self.task: Optional[asyncio.Task[None]] = None

    async def do_typing(self) -> None:
        """
        Sends typing indicator to the channel in a loop.
        """
        while True:
            await self.channel.trigger_typing()
            await asyncio.sleep(5)

    async def __aenter__(self) -> None:
        """
        Starts the typing task when entering the context.
        """
        await self.channel.trigger_typing()
        self.task = self.loop.create_task(self._send_typing())
        self.task.add_done_callback(handle_typing_task_completion)

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[asyncio.TracebackType],
    ) -> None:
        """
        Cancels the typing task when exiting the context.
        """
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def trigger_once(self) -> None:
        """
        Triggers a single typing indicator immediately.
        """
        await self.channel.trigger_typing()

    def __await__(self):
        return self.trigger_once().__await__()
