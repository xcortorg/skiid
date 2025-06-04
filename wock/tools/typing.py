import asyncio

import discord
from discord.ext import commands


def _typing_done_callback(fut: asyncio.Future) -> None:
    # just retrieve any exception and call it a day
    try:
        fut.exception()
    except (asyncio.CancelledError, Exception):
        pass


class Typing:
    def __init__(self, ctx: commands.Context) -> None:
        self.loop: asyncio.AbstractEventLoop = ctx._state.loop
        self.messageable: discord.Message = ctx.message
        self.command: commands.Command = ctx.command
        self.bot = ctx.bot
        self.guild: discord.Guild = ctx.guild
        self.author: discord.Member = ctx.author
        self.channel: discord.TextChannel = ctx.channel
        self.ctx = ctx

    async def wrapped_typer(self) -> None:
        await self.channel._state.http.send_typing(self.channel.id)

    def __await__(self):
        return self.wrapped_typer().__await__()

    async def do_typing(self) -> None:
        typing = self.channel._state.http.send_typing

        while True:
            await asyncio.sleep(5)
            await typing(self.channel.id)

    async def __aenter__(self) -> None:
        await self.channel._state.http.send_typing(self.channel.id)
        self.task: asyncio.Task[None] = self.loop.create_task(self.do_typing())
        self.task.add_done_callback(_typing_done_callback)

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ) -> None:
        if hasattr(self, "task"):
            self.task.cancel()
        return
