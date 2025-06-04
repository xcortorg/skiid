from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from functools import partial
from typing import Awaitable, Callable, TypeVar, TYPE_CHECKING
from typing_extensions import ParamSpec

import distributed.client
from tornado import gen
import dill
from .dask import get_dask, start_dask

if TYPE_CHECKING:
    from tool.greed import Greed


P = ParamSpec("P")
T = TypeVar("T")


def strtobool(val) -> bool:
    if not val:
        return False
    val = str(val)
    val = val.lower()
    if val in {"y", "yes", "t", "true", "on", "1"}:
        return True
    elif val in {"n", "no", "f", "false", "off", "0"}:
        return False
    else:
        msg = f"invalid truth value {val!r}"
        raise ValueError(msg)


DEBUG = strtobool(os.getenv("DEBUG", "OFF"))


@gen.coroutine
def cascade_future(future: distributed.Future, cf_future: asyncio.Future):
    result = yield future._result(raiseit=False)
    status = future.status
    if status == "finished":
        with suppress(asyncio.InvalidStateError):
            cf_future.set_result(result)
    elif status == "cancelled":
        cf_future.cancel()
        cf_future.set_running_or_notify_cancel()
    else:
        try:
            typ, exc, tb = result
            raise exc.with_traceback(tb)
        except BaseException as exc:
            cf_future.set_exception(exc)


def cf_callback(future):
    cf_future = future._cf_future
    if cf_future.cancelled() and future.status != "cancelled":
        asyncio.ensure_future(future.cancel())


def offloaded(f: Callable[P, T], batch_size: int = None) -> Callable[P, Awaitable[T]]:
    """Offload a function to run on Dask cluster with optional batching support.

    Args:
        f: Function to offload
        batch_size: Optional batch size for processing multiple items at once
    """

    _semaphore = asyncio.Semaphore(32)

    async def offloaded_task(*a, **ka):
        loop = asyncio.get_running_loop()

        # Handle batching if input is iterable and batch_size specified
        if batch_size and a and isinstance(a[-1], (list, tuple)):
            data = a[-1]
            other_args = a[:-1]

            # Split into batches
            batches = [
                data[i : i + batch_size] for i in range(0, len(data), batch_size)
            ]

            async def process_batch(batch):
                args = (*other_args, batch)
                async with _semaphore:
                    return await _submit_to_dask(f, args, ka, loop)

            # Process all batches with concurrency control
            results = await asyncio.gather(*[process_batch(batch) for batch in batches])
            return [item for batch in results for item in batch]

        async with _semaphore:
            return await _submit_to_dask(f, a, ka, loop)

    async def _submit_to_dask(f, a, ka, loop):
        retries = 3
        backoff_factor = 1.5
        
        for attempt in range(retries):
            cf_future = loop.create_future()
            
            dask = get_dask()
            if dask is None or dask.status in ("closed", "closing"):
                try:
                    dask = await start_dask("greed", "127.0.0.1:8787")
                    if dask.status != "running":
                        raise RuntimeError(
                            f"Dask client is in {dask.status} state after restart"
                        )
                except Exception as e:
                    if attempt == retries - 1:
                        raise RuntimeError(
                            f"Failed to restart Dask after {retries} attempts: {e}"
                        )
                    await asyncio.sleep(backoff_factor ** attempt)
                    continue

            try:
                if dask.status != "running":
                    if attempt == retries - 1:
                        raise RuntimeError(f"Dask client is in {dask.status} state")
                    await asyncio.sleep(backoff_factor ** attempt)
                    continue

                meth = partial(f, *a, **ka)
                dask_future = dask.submit(meth, pure=False)
                dask_future._cf_future = cf_future
                dask_future.add_done_callback(cf_callback)
                cascade_future(dask_future, cf_future)
                
                return await cf_future
            except (
                distributed.client.TimeoutError,
                distributed.client.CancelledError,
            ) as e:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(backoff_factor ** attempt)
                continue
            except Exception as e:
                if "after closing" in str(e) or "closed" in str(e):
                    if attempt == retries - 1:
                        raise RuntimeError(f"Dask client closed unexpectedly: {e}")
                    await asyncio.sleep(backoff_factor ** attempt)
                    continue
                raise

    return offloaded_task
