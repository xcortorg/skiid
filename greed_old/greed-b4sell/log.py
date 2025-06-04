from __future__ import annotations
import logging
import os
import queue
import sys
import threading
from time import sleep

from limits import parse, strategies, storage
from loguru import logger

LOG_LEVEL = os.getenv("LOG_LEVEL") or "INFO"
LOG_LOCK = threading.Lock()


def hook():
    pass


def info_chunk(msg):
    logger.info(msg, file=sys.stderr, end="", flush=True)


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class AsyncLogEmitter:
    def __init__(self, name=None) -> None:
        self.name = name
        self.queue = queue.SimpleQueue()
        self.thread = threading.Thread(target=self.runner)
        self.thread.daemon = True
        self.thread.start()

    def test(self):
        while not self.window.test(self.per_sec, "global", "log"):
            sleep(0.01)
        self.window.hit(self.per_sec, "global", "log")

    def runner(self):
        discards = False
        self.per_sec = parse("55/second")
        self.storage = storage.MemoryStorage()
        self.window = strategies.MovingWindowRateLimiter(self.storage)
        while True:
            msg: str = self.queue.get()
            if self.name:
                msg = msg.replace("MainThread", self.name)

            while self.queue.qsize() > 250:
                if not discards:
                    logger.warning(
                        "Queue is at max! - Suppressing logging to prevent high CPU blockage."
                    )
                    discards = True
                msg = self.queue.get()
            discards = False
            self.test()
            logger.info(msg, file=sys.stderr, end="", flush=True)

    def emit(self, msg: str):
        self.queue.put(msg)


def make_dask_sink(name=None, log_emitter=None):
    if log_emitter:
        emitter = log_emitter
    else:
        _emitter = AsyncLogEmitter(name=name)
        emitter = _emitter.emit

    logger.configure(
        handlers=[
            dict(
                sink=emitter,
                colorize=True,
                backtrace=True,
                enqueue=False,
                level=LOG_LEVEL,
                diagnose=True,
                catch=True,
                format="|<level>{level:<7}</level>|<cyan>{name}</cyan>(<cyan>{function}</cyan>:<cyan>{line}</cyan>) <level>{message}</level>",
            )
        ]
    )
    logger.level(name="DEBUG", color="<magenta>")
    intercept = InterceptHandler()
    logging.basicConfig(handlers=[intercept], level=LOG_LEVEL, force=True)
    logging.captureWarnings(True)
    logger.success("Logger reconfigured")
    logger.disable("distributed.utils")
    return emitter, logger
