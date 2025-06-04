from aiohttp import ClientSession as Session
from bs4 import BeautifulSoup
from random import choice, randrange
import langcodes
from ..models import TranslationResponse
from typing import Optional, Union, List, Any
from redis.asyncio import Redis
from .Base import BaseService, cache


def parse_language(language: str):
    if language == "auto":
        return language
    if len(language) == 2:
        return langcodes.get(language).language_name().lower()
    else:
        return langcodes.find(language).language


class TranslationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class TranslationService(BaseService):
    def __init__(self, redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("Translation", self.redis, self.ttl)

    async def get_translation(self, data: Any) -> Optional[str]:
        return (
            BeautifulSoup(data, "html.parser")
            .find("span", attrs={"id": "tw-answ-target-text"})
            .text
        )

    async def get_language(self, data: Any) -> Optional[str]:
        return (
            BeautifulSoup(data, "html.parser")
            .find("span", attrs={"id": "tw-answ-detected-sl-name"})
            .text
        )

    @cache()
    async def translate(
        self,
        text: str,
        source_language: Optional[str] = "auto",
        target_language: Optional[str] = "english",
        return_translation: Optional[bool] = False,
    ) -> Optional[TranslationResponse]:
        url = "https://www.google.com/async/translate"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
        }
        data = {
            "async": f"translate,sl:{parse_language(source_language) if source_language != 'auto' else source_language},tl:{parse_language(target_language)},st:{text},id:{-randrange(9e10)},qc:true,ac:true,_id:tw-async-translate,_pms:s,_fmt:pc"
        }
        error = None
        async with Session() as session:
            async with session.request(
                "POST", url, data=data, headers=headers
            ) as response:
                if response.status != 200:
                    error = TranslationError(
                        f"Could not parse the translated text into a translation to `{target_language}`"
                    )
                else:
                    data = await response.read()
        if error:
            raise error
        soup = BeautifulSoup(data, "html.parser")
        translation = soup.find("span", attrs={"id": "tw-answ-target-text"}).text
        target_language = langcodes.find(target_language).language_name()
        if return_translation:
            return translation
        source_language = soup.find(
            "span", attrs={"id": "tw-answ-detected-sl-name"}
        ).text
        return TranslationResponse(
            original=text,
            translated=translation,
            source=source_language,
            target=target_language,
        )
