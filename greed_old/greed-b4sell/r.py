from loguru import logger
from discord.globals import set_global

set_global("logger", logger)

from gc import get_referents
import builtins
from _types import calculate_, maximum, minimum, maximum_, minimum_, positive, positive_, hyperlink, shorten as shorten_, ObjectTransformer, catch, asDict, suppress_error, get_error  # type: ignore

# hi
builtins.calculate = calculate_
builtins.catch = catch
builtins.get_error = get_error
builtins.suppress_error = suppress_error
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

from tool.greed import Greed  # type: ignore  # noqa: E402
from asyncio import run  # noqa: E402
from config import CONFIG_DICT  # noqa: E402
from discord import utils  # noqa: E402

utils.setup_logging()

bot = Greed(CONFIG_DICT)


if __name__ == "__main__":
    run(bot.go())
