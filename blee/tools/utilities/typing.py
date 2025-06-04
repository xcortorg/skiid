from asyncio import AbstractEventLoop, CancelledError, Future, Task, sleep
from contextlib import suppress

from discord import Guild, Member, Message, TextChannel
from discord.ext.commands import Context


def _typing_done_callback(fut: Future):
    # just retrieve any exception and call it a day
    with suppress(CancelledError, Exception):
        fut.exception()


class Typing:
    def __init__(self, ctx: Context):
        self.loop: AbstractEventLoop = ctx._state.loop
        self.messageable: Message = ctx.message
        self.channel: TextChannel = ctx.channel

    async def wrapped_typer(self):
        await self.channel._state.http.send_typing(self.channel.id)

    def __await__(self):
        return self.wrapped_typer().__await__()

    async def do_typing(self):
        typing = self.channel._state.http.send_typing

        while True:
            await sleep(5)
            await typing(self.channel.id)

    async def __aenter__(self):
        await self.channel._state.http.send_typing(self.channel.id)
        self.task: Task[None] = self.loop.create_task(self.do_typing())
        self.task.add_done_callback(_typing_done_callback)

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        if hasattr(self, "task"):
            self.task.cancel()
