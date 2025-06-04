from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Union

import config
from aiohttp import ClientSession
from discord import (Asset, Forbidden, HTTPException, Member, Message,
                     NotFound, User)
from discord.ext.commands import (BadArgument, CommandError, Converter,
                                  MemberConverter, MemberNotFound,
                                  UserConverter, UserNotFound)
from yarl import URL

if TYPE_CHECKING:
    from core.client.context import Context

MEDIA_URL_PATTERN = re.compile(
    r"(?:http\:|https\:)?\/\/.*\.(?P<mime>png|jpg|jpeg|webp|gif|mp4|mp3|mov|wav|ogg|zip)"
)
DURATION_PATTERN = r"\s?".join(
    [
        r"((?P<years>\d+?)\s?(years?|y))?",
        r"((?P<months>\d+?)\s?(months?|mo))?",
        r"((?P<weeks>\d+?)\s?(weeks?|w))?",
        r"((?P<days>\d+?)\s?(days?|d))?",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))?",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m(?!o)))?",
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))?",
    ]
)


class Status(Converter[bool]):
    async def convert(self, ctx: Context, argument: str) -> bool:
        return argument.lower() in {"enable", "yes", "on", "true"}


class StrictMember(MemberConverter):
    async def convert(self, ctx: Context, argument: str) -> Member:
        pattern = (
            r"<@!?\d+>$" if ctx.command.name.startswith("purge") else r"\d+$|<@!?\d+>$"
        )
        if re.match(pattern, argument):
            return await super().convert(ctx, argument)
        raise MemberNotFound(argument)


class StrictUser(UserConverter):
    async def convert(self, ctx: Context, argument: str) -> User:
        pattern = (
            r"<@!?\d+>$" if ctx.command.name.startswith("purge") else r"\d+$|<@!?\d+>$"
        )
        if re.match(pattern, argument):
            return await super().convert(ctx, argument)
        raise UserNotFound(argument)


class PartialAttachment:
    url: str
    buffer: bytes
    filename: str
    content_type: Optional[str]

    def __init__(
        self,
        url: Union[URL, Asset, str],
        buffer: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ):
        self.url = str(url)
        self.buffer = buffer
        self.extension = content_type.split("/")[-1] if content_type else "bin"
        self.filename = filename or f"unknown.{self.extension}"
        self.content_type = content_type

    def __str__(self) -> str:
        return self.filename

    def is_image(self) -> bool:
        return self.content_type.startswith("image") if self.content_type else False

    def is_video(self) -> bool:
        return self.content_type.startswith("video") if self.content_type else False

    def is_audio(self) -> bool:
        return self.content_type.startswith("audio") if self.content_type else False

    def is_gif(self) -> bool:
        return self.content_type == "image/gif" if self.content_type else False

    def is_archive(self) -> bool:
        return (
            self.content_type.startswith("application") if self.content_type else False
        )

    @staticmethod
    async def read(url: Union[URL, str]) -> tuple[bytes, str]:
        async with ClientSession() as client:
            async with client.get(url, proxy=config.WARP) as resp:
                if resp.content_length and resp.content_length > 50 * 1024 * 1024:
                    raise CommandError("Attachment exceeds the decompression limit!")
                if resp.status == 200:
                    buffer = await resp.read()
                    return buffer, resp.content_type
                if resp.status == 404:
                    raise NotFound(resp, "asset not found")
                if resp.status == 403:
                    raise Forbidden(resp, "cannot retrieve asset")
                raise HTTPException(resp, "failed to get asset")

    @classmethod
    def get_attachment(cls, message: Message) -> Optional[str]:
        if message.attachments:
            return message.attachments[0].url
        if message.stickers:
            return message.stickers[0].url
        if message.embeds:
            if message.embeds[0].image:
                return message.embeds[0].image.url
            if message.embeds[0].thumbnail:
                return message.embeds[0].thumbnail.url
        return None

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> PartialAttachment:
        try:
            member = await MemberConverter().convert(ctx, argument)
        except CommandError:
            pass
        else:
            buffer, content_type = await cls.read(member.display_avatar.url)
            return cls(member.display_avatar, buffer, None, content_type)

        if not MEDIA_URL_PATTERN.match(argument):
            raise BadArgument("The provided **URL** couldn't be validated!")

        url = argument
        buffer, content_type = await cls.read(url)
        return cls(url, buffer, None, content_type)

    @classmethod
    async def fallback(cls, ctx: Context) -> PartialAttachment:
        attachment_url = (
            cls.get_attachment(ctx.replied_message) if ctx.replied_message else None
        )

        if not attachment_url:
            async for message in ctx.channel.history():
                attachment_url = cls.get_attachment(message)
                if attachment_url:
                    break

        if not attachment_url:
            raise BadArgument("You must provide an attachment!")

        buffer, content_type = await cls.read(attachment_url)
        return cls(
            attachment_url,
            buffer,
            f"{ctx.author.id}.{attachment_url.split('.')[-1].split('?')[0]}",
            content_type,
        )


class Duration(Converter[timedelta]):
    def __init__(
        self,
        min: Optional[timedelta] = None,
        max: Optional[timedelta] = None,
        units: Optional[List[str]] = None,
    ):
        self.min = min
        self.max = max
        self.units = units or ["weeks", "days", "hours", "minutes", "seconds"]

    async def convert(self, ctx: Context, argument: str) -> timedelta:
        matches = re.fullmatch(DURATION_PATTERN, argument, re.IGNORECASE)
        if not matches:
            raise CommandError("The duration provided didn't pass validation!")

        units = {
            unit: int(amount) for unit, amount in matches.groupdict().items() if amount
        }
        for unit in units:
            if unit not in self.units:
                raise CommandError(f"The unit `{unit}` is not valid for this command!")

        try:
            duration = timedelta(**units)
        except OverflowError as exc:
            raise CommandError("The duration provided is too long!") from exc

        if self.min and duration < self.min:
            raise CommandError("The duration provided is too short!")
        if self.max and duration > self.max:
            raise CommandError("The duration provided is too long!")

        return duration


class Timezone(Converter[str]):
    async def convert(self, ctx: Context, argument: str) -> str:
        response = await ctx.bot.session.get(
            URL.build(
                scheme="https",
                host="api.weatherapi.com",
                path="/v1/timezone.json",
                query={"q": argument.lower(), "key": config.Api.WEATHER},
            ),
        )
        if not response.ok:
            raise CommandError(f"Timezone not found for **{argument}**!")

        data = await response.json()
        return data["location"]["tz_id"]


class Timeframe:
    period: Literal["overall", "7day", "1month", "3month", "6month", "12month"]

    def __init__(
        self,
        period: Literal["overall", "7day", "1month", "3month", "6month", "12month"],
    ):
        self.period = period

    def __str__(self) -> str:
        return {
            "7day": "weekly",
            "1month": "monthly",
            "3month": "past 3 months",
            "6month": "past 6 months",
            "12month": "yearly",
        }.get(self.period, "overall")

    @property
    def current(self) -> str:
        return {
            "7day": "week",
            "1month": "month",
            "3month": "3 months",
            "6month": "6 months",
            "12month": "year",
        }.get(self.period, "overall")

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Timeframe:
        period_map = {
            "weekly": "7day",
            "week": "7day",
            "1week": "7day",
            "7days": "7day",
            "7day": "7day",
            "7ds": "7day",
            "7d": "7day",
            "monthly": "1month",
            "month": "1month",
            "1month": "1month",
            "1m": "1month",
            "30days": "1month",
            "30day": "1month",
            "30ds": "1month",
            "30d": "1month",
            "3months": "3month",
            "3month": "3month",
            "3ms": "3month",
            "3m": "3month",
            "90days": "3month",
            "90day": "3month",
            "90ds": "3month",
            "90d": "3month",
            "halfyear": "6month",
            "6months": "6month",
            "6month": "6month",
            "6mo": "6month",
            "6ms": "6month",
            "6m": "6month",
            "180days": "6month",
            "180day": "6month",
            "180ds": "6month",
            "180d": "6month",
            "yearly": "12month",
            "year": "12month",
            "yr": "12month",
            "1year": "12month",
            "1y": "12month",
            "12months": "12month",
            "12month": "12month",
            "12mo": "12month",
            "12ms": "12month",
            "12m": "12month",
            "365days": "12month",
            "365day": "12month",
            "365ds": "12month",
            "365d": "12month",
        }
        return cls(period_map.get(argument, "overall"))


__all__ = (
    "Status",
    "Duration",
    "Timezone",
    "StrictUser",
    "StrictMember",
    "Timeframe",
)
