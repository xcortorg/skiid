from typing import Sequence


def remove(value: str, *args: str) -> str:
    for arg in args:
        value = value.replace(arg, "")

    return value


def codeblock(value: str, language: str = "") -> str:
    return f"```{language}\n{value}```"


def sanitize(value: str) -> str:
    return remove(value, "`", "*", "_", "~", "|", ">", "<" "/", "\\")


def human_join(seq: Sequence[str], delim: str = ", ", final: str = "or") -> str:
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return f"{delim.join(seq[:-1])} {final} {seq[-1]}"
