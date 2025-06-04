import sys

from loguru import logger

logger.remove()

logger.add(
    sys.stderr,
    level="DEBUG",
    format="<cyan>{process}</cyan>:<level>{level: <9}</level> (<magenta>{time:YYYY-MM-DD hh:mm A}</magenta>) <white>@</white> <red>{module: <9}</red> -> {message}",
)

logger.add(
    "logs/bot.log",
    level="INFO",
    format="<cyan>{process}</cyan>:<level>{level: <9}</level> (<magenta>{time:YYYY-MM-DD hh:mm A}</magenta>) <white>@</white> <red>{module: <9}</red> -> {message}",
    rotation="10 MB",
    retention="10 days",
    compression="zip",
)

ignore = (
    "pomice",
    "client",
    "web_log",
    "network",
    "gateway",
    "launcher",
)
for module in ignore:
    logger.disable(module)
