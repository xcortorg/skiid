import math
import os
import dotenv
import discord
import datetime
import signal
import sys
import aiohttp
import asyncio
import time
import argparse

from loguru import logger
from contextlib import suppress

from typing import Dict, Union, List
from modules.evelinabot import EvelinaContext, Evelina

parser = argparse.ArgumentParser()
parser.add_argument("--shard-start", type=int, required=True)
parser.add_argument("--shard-end", type=int, required=True)
parser.add_argument("--shard-count", type=int, required=True)
parser.add_argument("--heartbeat-host", type=str, default="0.0.0.0")
parser.add_argument("--heartbeat-port", type=int, default=8000)
args = parser.parse_args()
bot = Evelina(shard_count=args.shard_count, shard_ids=list(range(args.shard_start, args.shard_end)))

dotenv.load_dotenv(verbose=True)


@bot.event
async def on_command(ctx: EvelinaContext):
    if not ctx.bot.is_ready():
        return
    start_time = time.time()
    try:
        full_command_name = ctx.command.qualified_name
        invoked_with = ctx.invoked_with
        command_start_index = len(ctx.prefix) + ctx.message.content[
            len(ctx.prefix) :
        ].find(invoked_with)
        command_length = command_start_index + len(invoked_with)
        arguments = ctx.message.content[command_length:].strip()
        server_id = ctx.guild.id if ctx.guild else None
        user_id = ctx.author.id
        channel_id = ctx.channel.id
        timestamp = datetime.datetime.now(datetime.timezone.utc).timestamp()

        execution_time = round((time.time() - start_time) * 1000, 2)
        await ctx.bot.db.execute(
            "INSERT INTO command_stats (command, user_id, guild_id, channel_id, execution_time, timestamp) VALUES ($1, $2, $3, $4, $5, $6)",
            full_command_name,
            user_id,
            server_id,
            channel_id,
            execution_time,
            datetime.datetime.now(),
        )

        logger.info(
            f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO    ] command: {full_command_name} | guild: {ctx.guild.name if ctx.guild else 'DM'} ({ctx.guild.id if ctx.guild else 'N/A'}) | channel: {ctx.channel.name if isinstance(ctx.channel, discord.TextChannel) else 'DM'} ({ctx.channel.id}) | user: {ctx.author} ({ctx.author.id}) | time: {execution_time / 1000:.2f}s"
        )
    except Exception as e:
        logger.error(f"Error logging command: {str(e)}")


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if not interaction.client.is_ready():
        return
    if interaction.type == discord.InteractionType.application_command:
        if interaction.command is None:
            return
        full_command_name = interaction.command.qualified_name
        arguments = " ".join(
            [
                (
                    f"{option['name']}: {option['value']}"
                    if "value" in option
                    else option["name"]
                )
                for option in interaction.data.get("options", [])
            ]
        )
        server_id = interaction.guild.id if interaction.guild else None
        user_id = interaction.user.id
        channel_id = interaction.channel_id
        timestamp = datetime.datetime.now(datetime.timezone.utc).timestamp()
        await interaction.client.db.execute(
            "INSERT INTO command_history (command, arguments, server_id, user_id, channel_id, timestamp) VALUES ($1, $2, $3, $4, $5, $6)",
            full_command_name,
            arguments,
            server_id,
            user_id,
            channel_id,
            timestamp,
        )


# *** Added guild join/leave logging ***
@bot.event
async def on_guild_join(guild: discord.Guild):
    # log when bot joins a guild
    channel = bot.get_channel(bot.logging_joinleave)
    if channel and channel.permissions_for(guild.me).send_messages:
        await channel.send(f"➡️ **BOT JOINED**: {guild.name} (`{guild.id}`)")

@bot.event
async def on_guild_remove(guild: discord.Guild):
    # log when bot is removed from a guild
    channel = bot.get_channel(bot.logging_joinleave)
    if channel and channel.permissions_for(guild.me).send_messages:
        await channel.send(f"⬅️ **BOT LEFT**: {guild.name} (`{guild.id}`)")
# *** End additions ***


def handle_exit(*args):
    asyncio.create_task(bot.close())
    sys.exit(0)


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


async def get_shard_stats(
    bot: Evelina, shard_id: int, shard
) -> Dict[str, Union[int, float, str]]:
    raw_latency = shard.latency or float("inf")
    latency = raw_latency if not math.isinf(raw_latency) else 999

    users = sum(
        len(guild.members) for guild in bot.guilds if guild.shard_id == shard_id
    )
    guilds = sum(1 for guild in bot.guilds if guild.shard_id == shard_id)

    return {
        "shard_id": shard_id,
        "latency": latency,
        "users": users,
        "guilds": guilds,
        "uptime": hasattr(bot, "uptime") and bot.uptime or "Neverrr",
    }


async def heartbeat_loop(bot: Evelina, host: str, port: int) -> None:
    url = f"http://{host}:{port}/heartbeat"
    async with aiohttp.ClientSession() as session:
        while True:
            for shard_id, shard in bot.shards.items():
                data = await get_shard_stats(bot, shard_id, shard)
                await session.post(url, json=data)

            await asyncio.sleep(5)


async def startup():
    asyncio.create_task(heartbeat_loop(bot, args.heartbeat_host, args.heartbeat_port))
    await bot.start(token=os.environ["BOT_TOKEN"])


if __name__ == "__main__":
    with suppress(
            RuntimeError,
            KeyboardInterrupt,
            ProcessLookupError,
    ):
        asyncio.run(startup())