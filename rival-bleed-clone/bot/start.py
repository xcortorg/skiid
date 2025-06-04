from lib.main import Bot
from var.config import CONFIG
from discord import utils
from gc import get_referents
import builtins
from lib.classes.builtins import calculate_, maximum, minimum, maximum_, minimum_, positive, positive_, hyperlink, shorten as shorten_, ObjectTransformer, catch, asDict, suppress_error, get_error, boolean_to_emoji, humanize, human_join, humanize_, humanize__, ordinal  # type: ignore

# hi
builtins.boolean_to_emoji = boolean_to_emoji
builtins.calculate = calculate_
builtins.catch = catch
builtins.get_error = get_error
builtins.suppress_error = suppress_error
builtins.hyperlink = hyperlink
builtins.ObjectTransformer = ObjectTransformer
builtins.human_join = human_join
builtins.asDict = asDict
_float = get_referents(float.__dict__)[0]
_str = get_referents(str.__dict__)[0]
_int = get_referents(int.__dict__)[0]
__str = get_referents(builtins.str.__dict__)[0]
__float = get_referents(builtins.float.__dict__)[0]
__int = get_referents(builtins.int.__dict__)[0]
_float["maximum"] = maximum
_float["minimum"] = minimum
_float["positive"] = positive
__float["maximum"] = maximum
__float["minimum"] = minimum
__float["positive"] = positive
_int["maximum"] = maximum_
_int["humanize"] = humanize
_int["ordinal"] = ordinal
_int["minimum"] = minimum_
_int["positive"] = positive_
__int["maximum"] = maximum_
__int["ordinal"] = ordinal
__int["minimum"] = minimum_
__int["positive"] = positive_
__int["humanize"] = humanize
_str["shorten"] = shorten_
__str["shorten"] = shorten_
_str["humanize"] = humanize_
__str["humanize"] = humanize_
_float["humanize"] = humanize__
__float["humanize"] = humanize__
utils.setup_logging(level="INFO")

bot = Bot(CONFIG)

if __name__ == "__main__":
    bot.run()
