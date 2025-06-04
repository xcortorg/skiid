import distributed
import asyncio
import os
import psutil
from tornado import gen
from typing import Callable
from loguru import logger
import os

GLOBAL_DASK = {}


def get_dask() -> distributed.Client:
    return GLOBAL_DASK.get("client")


async def start_dask(bot, address: str) -> distributed.Client:
    if "client" in GLOBAL_DASK:
        logger.info("Using existing Dask client")
        return GLOBAL_DASK["client"]

    scheduler_file = "scheduler.json"

    # Check if port 8787 is already in use
    port_in_use = any(conn.laddr.port == 8787 for conn in psutil.net_connections())

    if port_in_use:
        logger.info(f"Port in using binding dask now...")
        for i in range(5):
            try:
                client = await distributed.Client(
                    scheduler_file=scheduler_file, asynchronous=True, name="greed"
                )
                break
            except Exception as e:
                if i == 4:
                    raise e
                await asyncio.sleep(3)
        GLOBAL_DASK["client"] = client
    else:
        client = await distributed.Client(
            distributed.LocalCluster(
                dashboard_address="127.0.0.1:8787",
                asynchronous=True,
                processes=True,
                threads_per_worker=4,
                n_workers=12,
            ),
            direct_to_workers=True,
            asynchronous=True,
            name="greed",
        )
        client.write_scheduler_file(scheduler_file)
        GLOBAL_DASK["client"] = client
    logger.info("Dask client started successfully")
    return client


def submit_coroutine(func: Callable, *args, **kwargs):
    worker_loop: asyncio.AbstractEventLoop = distributed.get_worker().loop.asyncio_loop
    task = asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop=worker_loop)
    return task.result()