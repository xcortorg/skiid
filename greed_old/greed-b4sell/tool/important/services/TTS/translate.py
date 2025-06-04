from aiohttp import ClientSession as cs
from bs4 import BeautifulSoup
import langcodes
from random import randrange
from pydantic import BaseModel
from typing import Optional
from cashews import cache

cache.setup("mem://")
BASE = "tw-answ-"
OBJ_CLASSES = {
    "input_supplied_source": "sl",
    "target_language": "tl",
    "source-text": "source-text",
    "target_text": "target-text",
    "target_feminine": "target-text-feminine",
    "target_masculine": "target-text-masculine",
    "romanization": "source-romanization",
    "source_romanization": "source-romanization",
    "detected_source_language": "detected-sl",
    "spelling": "spelling",
    "confident": "spelling-confident",
    "detected_source_name": "detected-sl-name",
    "language_detected": "language-detected",
    "verified": "community-verified",
}


class Translation(BaseModel):
    input_supplied_source: Optional[str] = None
    target_language: Optional[str] = None
    source_text: Optional[str] = None
    target_text: Optional[str] = None
    target_feminine: Optional[str] = None
    target_masculine: Optional[str] = None
    romanization: Optional[str] = None
    source_romanization: Optional[str] = None
    detected_source_language: Optional[str] = None
    spelling: Optional[str] = None
    confident: Optional[bool] = False
    detected_source_name: Optional[str] = None
    language_detected: Optional[str] = None
    verified: Optional[bool] = False
    detected_target_language: Optional[str] = None


@cache(300, "translation:{text}:{target_language}:{source_language}")
async def translate(
    text: str, target_language: str, source_language: Optional[str] = "auto"
) -> Translation:
    def parse_value(value: str):
        value = str(value)
        if value == "":
            return None
        elif any((value.lower() == "true", value.lower() == "true")):
            return True
        elif any((value.lower() == "false", value.lower() == "false")):
            return False
        elif any((value.lower() == "true", value.lower() == "false")):
            return bool(value.title())
        else:
            return value

    lang = langcodes.find(target_language).display_name()
    session = cs()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
    }
    data = await (
        await session.post(
            "https://www.google.com/async/translate",
            data={
                "async": f"translate,sl:{langcodes.find(source_language).language if source_language != 'auto' else source_language},tl:{langcodes.find(target_language).language},st:{text},id:{-randrange(9e10)},qc:true,ac:true,_id:tw-async-translate,_pms:s,_fmt:pc"
            },
            headers=headers,
        )
    ).read()
    s = BeautifulSoup(data, "html.parser")
    translation = {}
    for key, value in OBJ_CLASSES.items():
        val = None
        element = s.find("span", attrs={"id": f"{BASE}{value}"})
        if element:
            val = parse_value(element.text)
        translation[key] = val
    translation["detected_target_language"] = lang
    return Translation(**translation)
