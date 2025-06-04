import random
import re
import string
from html import unescape
from typing import Any, Dict, List, Union
from urllib.parse import unquote

import orjson

REGEX_STRIP_TAGS = re.compile("<.*?>")


def _extract_vqd(html_bytes: bytes, keywords: str) -> str:
    """Extract vqd from html bytes."""
    for c1, c1_len, c2 in (
        (b'vqd="', 5, b'"'),
        (b"vqd=", 4, b"&"),
        (b"vqd='", 5, b"'"),
    ):
        try:
            start = html_bytes.index(c1) + c1_len
            end = html_bytes.index(c2, start)
            return html_bytes[start:end].decode()
        except ValueError:
            pass
    raise Exception(f"_extract_vqd() {keywords=} Could not extract vqd.")


def get_random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=int(length)))


def json_loads(obj: Union[str, bytes]) -> Any:
    try:
        return orjson.loads(obj)
    except Exception as ex:
        raise Exception(f"{type(ex).__name__}: {ex}") from ex


def _normalize(raw_html: str) -> str:
    """Strip HTML tags from the raw_html string."""
    return unescape(REGEX_STRIP_TAGS.sub("", raw_html)) if raw_html else ""


def _normalize_url(url: str) -> str:
    """Unquote URL and replace spaces with '+'."""
    return unquote(url).replace(" ", "+") if url else ""


def _text_extract_json(html_bytes: bytes, keywords: str) -> List[Dict[str, str]]:
    try:
        start = html_bytes.index(b"DDG.pageLayout.load('d',") + 24
        end = html_bytes.index(b");DDG.duckbar.load(", start)
        data = html_bytes[start:end]
        result: list[dict[str, str]] = json_loads(data)
        return result
    except Exception as ex:
        raise Exception(
            f"_text_extract_json() {keywords=} {type(ex).__name__}: {ex}"
        ) from ex
    raise Exception(f"_text_extract_json() {keywords=} return None")
