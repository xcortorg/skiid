from discord.globals import set_global
from loguru import logger

set_global("logger", logger)

import builtins
from gc import get_referents

from _types import (ObjectTransformer, asDict, calculate_, catch, hyperlink,
                    maximum, maximum_, minimum, minimum_, positive, positive_)
from _types import shorten as shorten_  # type: ignore

# hi
builtins.calculate = calculate_
builtins.catch = catch
builtins.hyperlink = hyperlink
builtins.ObjectTransformer = ObjectTransformer
builtins.asDict = asDict
_float = get_referents(float.__dict__)[0]
_str = get_referents(str.__dict__)[0]
_int = get_referents(int.__dict__)[0]
__float = get_referents(builtins.float.__dict__)[0]
__int = get_referents(builtins.int.__dict__)[0]
_float["maximum"] = maximum
_float["minimum"] = minimum
_float["positive"] = positive
__float["maximum"] = maximum
__float["minimum"] = minimum
__float["positive"] = positive
_int["maximum"] = maximum_
_int["minimum"] = minimum_
_int["positive"] = positive_
__int["maximum"] = maximum_
__int["minimum"] = minimum_
__int["positive"] = positive_
_str["shorten"] = shorten_

from asyncio import run  # noqa: E402

from config import CONFIG_DICT  # noqa: E402
from discord import utils  # noqa: E402
from tools.wock import Wock  # type: ignore  # noqa: E402

utils.setup_logging()

bot = Wock(CONFIG_DICT)


if __name__ == "__main__":
    run(bot.go())
