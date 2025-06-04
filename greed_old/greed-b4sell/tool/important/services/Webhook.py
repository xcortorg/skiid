from discord import Webhook, User, Member, Guild, TextChannel, WebhookMessage
from discord.abc import GuildChannel
from aiohttp import ClientSession
from typing import Optional, List, Dict, Any
from asyncio import gather
from async_timeout import Timeout as timeout
from cashews import cache

cache.setup("mem://")


@cache(ttl="60m", key="webhook:{url}")
async def get_webhook(url: str, token: str):
    session = ClientSession()
    webhook = Webhook.from_url(url, session=session, bot_token=token)
    return webhook


class Webhook:
    def __init__(self, bot):
        self.bot = bot

    async def setup_webhooks(self, guild: Guild, **kwargs: Any):
        webhooks = []
        for channel in guild.text_channels:
            data = [channel.id, []]
            channel_webhooks = await channel.webhooks()
            for webhook in channel_webhooks:
                await webhook.delete(reason="freeing up space for reskin")
            for i in range(14):
                data[1].append((await channel.create_webhook(**kwargs)).url)
        return webhooks

    async def get_webhooks(self, channel: GuildChannel):
        guild_id = channel.guild.id
        channel_id = channel.id
        server = await bot.db.fetchrow(
            """SELECT *
            FROM reskin.server
            WHERE guild_id = $1""",
            guild_id,
        )
        if server:
            data = json.loads(server["webhooks"])
            for entry in data:
                if entry[0] == channel.id or entry[1] == channel.name:
                    webhooks = entry[2]
                    break
            webhooks = await gather(
                *[get_webhook(w, self.bot.config["token"]) for w in webhooks]
            )
            return webhooks
        return None

    async def clear_webhooks(self, guild: Guild):
        for channel in guild.text_channels:
            if webhooks := await self.get_webhooks(channel):
                for webhook in webhooks:
                    await webhook.delete(reason="webhooks cleared")
        return True

    async def send(
        self, channel: GuildChannel, *args: Any, **kwargs: Any
    ) -> Optional[WebhookMessage]:
        webhooks = await self.get_webhooks(channel)
        if not webhooks:
            return None
        exception = None
        for webhook in webhooks:
            if webhook.channel.id != channel.id:
                await webhook.edit(channel=channel)
            try:
                async with timeout(3):
                    _ = await webhook.send(*args, **kwargs)
                    return _
            except TimeoutError:
                pass
            except Exception as e:
                exception = e
        raise exception
