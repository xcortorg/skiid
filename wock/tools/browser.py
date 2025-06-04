import asyncio
import json

import zmq
from discord import Message
from discord.ext.commands import Cog


class SocketParser:
    def __init__(self, bot, raw_data: dict):
        self.bot = bot
        self.event = raw_data.get("t", None)
        self.data = raw_data.get("d", {})
        self._data_dispatch()

    def _data_dispatch(self):
        if self.event == "MESSAGE_CREATE":
            self.handle_message(self.data)
        return

    def handle_message(self, data: dict):
        guild = None
        if guild_id := data.get("guild_id"):
            guild = self.bot.get_guild(guild_id)
        self.bot.dispatch(
            "message", Message(state=self.bot._connection, data=data, guild=guild)
        )


class InteractionMirror:
    def __init__(self, bot):
        self.bot = bot
        self.ctx = None
        self.socket = None
        self.mirrored = False
        self.uri = "tcp://127.0.0.1:5555"

    @Cog.listener("on_socket_raw_receive")
    async def mirror_listener(self, payload: dict):
        if self.mirrored:
            asyncio.ensure_future(self.mirror())
        await self.socket.send_json()

    async def mirror(self):
        self.ctx = zmq.asyncio.Context()
        self.socket = self.ctx.socket(zmq.SUB)
        self.socket.connect(self.uri)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        while True:
            data = await self.socket.recv_json()
            try:
                data = json.loads(data)
            except Exception as e:
                self.bot.logger.info(f"Interaction Mirror raised {e}")
                continue
            SocketParser(self, data)
