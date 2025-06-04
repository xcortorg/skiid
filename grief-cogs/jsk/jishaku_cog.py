import jishaku
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES

jishaku.Flags.RETAIN = True
jishaku.Flags.NO_DM_TRACEBACK = True
jishaku.Flags.FORCE_PAGINATOR = True
jishaku.Flags.NO_UNDERSCORE = True
jishaku.Flags.HIDE = True
jishaku.Flags.ALWAYS_DM_TRACEBACK = False


class Jishaku(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    """Jishaku"""
