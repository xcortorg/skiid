from typing import Optional

from grief.core.utils.chat_formatting import humanize_timedelta

EMOJI_REGEX = r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
LINK_REGEX = (
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)


def emoji_converter(bot, emoji) -> Optional[str]:
    """General emoji converter"""
    if not emoji:
        return
    if isinstance(emoji, int) or emoji.isdigit():
        return bot.get_emoji(int(emoji))
    emoji = emoji.strip()
    return emoji


def shorten_line(a_line: str) -> str:
    if len(a_line) < 70:
        return a_line
    return a_line[:67] + "..."


def get_perms(command):
    final_perms = ""
    neat_format = lambda x: " ".join(
        i.capitalize() for i in x.replace("_", " ").split()
    )

    user_perms = []
    if perms := getattr(command.requires, "user_perms"):
        user_perms.extend(neat_format(i) for i, j in perms if j)
    if perms := command.requires.privilege_level:
        if perms.name != "NONE":
            user_perms.append(neat_format(perms.name))

    if user_perms:
        final_perms += "" + ", ".join(user_perms) + "\n"

    return final_perms


def get_cooldowns(command):
    cooldowns = []
    if s := command._buckets._cooldown:
        txt = f"{s.rate} time{'s' if s.rate>1 else ''} in {humanize_timedelta(seconds=s.per)}"
        try:
            txt += f" per {s.type.name.capitalize()}"
        except AttributeError:
            pass
        cooldowns.append(txt)

    if s := command._max_concurrency:
        cooldowns.append(
            f"Max concurrent uses: {s.number} per {s.per.name.capitalize()}"
        )

    return cooldowns


def get_aliases(command, original):
    if alias := list(command.aliases):
        if original in alias:
            alias.remove(original)
            alias.append(command.name)
        return alias


async def get_category_page_mapper_chunk(
    formatter, get_pages, ctx, cat, help_settings, page_mapping
):
    if not get_pages:
        if cat_page := await formatter.format_category_help(
            ctx, cat, help_settings=help_settings, get_pages=True
        ):
            page_mapping[cat] = cat_page
        else:
            return False
    return True
