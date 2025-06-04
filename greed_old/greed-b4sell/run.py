import asyncio
import uvloop
import argparse
from discord.utils import setup_logging
from loguru import logger
from tool.greed import Greed
from config import CONFIG_DICT
import aiohttp

setup_logging()


def chunk_list(data: list, amount: int) -> list[list]:
    # makes lists of a big list of values every x amount of values
    if len(data) < amount:
        _chunks = [data]
    else:
        chunks = zip(*[iter(data)] * amount)
        _chunks = list(list(_) for _ in chunks)
    from itertools import chain

    l = list(chain.from_iterable(_chunks))  # noqa: E741
    nul = [d for d in data if d not in l]
    if len(nul) > 0:
        _chunks.append(nul)
    return _chunks


TOKEN = CONFIG_DICT["token"]

parser = argparse.ArgumentParser(
    description="CLI tool for handling cluster IDs for Greed."
)
parser.add_argument("cluster", type=int, help="The ID of the cluster (1-4)")
args = parser.parse_args()
cluster_id = args.cluster

if not (1 <= cluster_id <= 4):
    logger.error("Cluster ID must be between 1 and 4.")
    exit(1)


async def main():
    ips = ["23.160.168.122", "23.160.168.124", "23.160.168.125", "23.160.168.126"]

    shard_count = 32
    clusters = 4
    per_cluster = (shard_count + clusters - 1) // clusters

    shards = list(range(shard_count))
    shard_chunks = chunk_list(shards, per_cluster)

    shard_array = shard_chunks[cluster_id - 1]
    local_addr = (ips[cluster_id - 1], 0)

    logger.info(f"Starting cluster {cluster_id} with shards: {shard_array}")

    bot = Greed(
        CONFIG_DICT,
        shard_count=shard_count,
        shard_ids=shard_array,
        local_address=local_addr,
    )
    await bot.go()


if __name__ == "__main__":
    asyncio.run(main())
