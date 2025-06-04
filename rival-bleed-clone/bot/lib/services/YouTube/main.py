from pydantic import BaseModel
from typing import Optional, Union, List, Dict, Any
from discord import Client, Message
from var.variables import YOUTUBE_WILDCARD
from lib.worker import offloaded
from .models.response import YouTubeVideo
from aiohttp import ClientSession

import json


@offloaded
def download(url: str, length_limit: Optional[int] = None, download: Optional[bool] = False) -> dict:
	from pytubefix import YouTube, Channel
	from tuuid import tuuid
	import traceback
	import inspect
	import functools
	import re
	try:
		from .models.data import YouTubeResponse
	except ImportError:
		from models.data import YouTubeResponse
	data = {}

	NUMBER_RE = r'\d+(?:\.\d+)?'

	def partial_application(func):
		sig = inspect.signature(func)
		required_args = [
			param.name for param in sig.parameters.values()
			if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
			if param.default is inspect.Parameter.empty
		]

		@functools.wraps(func)
		def wrapped(*args, **kwargs):
			if set(required_args[len(args):]).difference(kwargs):
				return functools.partial(func, *args, **kwargs)
			return func(*args, **kwargs)

		return wrapped

	@partial_application
	def int_or_none(v, scale=1, default=None, get_attr=None, invscale=1, base=None):
		if get_attr and v is not None:
			v = getattr(v, get_attr, None)
		if invscale == 1 and scale < 1:
			invscale = int(1 / scale)
			scale = 1
		try:
			return (int(v) if base is None else int(v, base=base)) * invscale // scale
		except (ValueError, TypeError, OverflowError):
			return default


	def str_or_none(v, default=None):
		return default if v is None else str(v)

	def str_to_int(int_str):
		""" A more relaxed version of int_or_none """
		if isinstance(int_str, int):
			return int_str
		elif isinstance(int_str, str):
			int_str = re.sub(r'[,\.\+]', '', int_str)
			return int_or_none(int_str)
		
	def lookup_unit_table(unit_table, s, strict=False):
		num_re = NUMBER_RE if strict else NUMBER_RE.replace(R'\.', '[,.]')
		units_re = '|'.join(re.escape(u) for u in unit_table)
		m = (re.fullmatch if strict else re.match)(
			rf'(?P<num>{num_re})\s*(?P<unit>{units_re})\b', s)
		if not m:
			return None

		num = float(m.group('num').replace(',', '.'))
		mult = unit_table[m.group('unit')]
		return round(num * mult)

	def format_value(s):
		if s is None:
			return None

		s = re.sub(r'^[^\d]+\s', '', s).strip()

		if re.match(r'^[\d,.]+$', s):
			return str_to_int(s)

		_UNIT_TABLE = {
			'k': 1000,
			'K': 1000,
			'm': 1000 ** 2,
			'M': 1000 ** 2,
			'kk': 1000 ** 2,
			'KK': 1000 ** 2,
			'b': 1000 ** 3,
			'B': 1000 ** 3,
		}

		ret = lookup_unit_table(_UNIT_TABLE, s)
		if ret is not None:
			return ret

		mobj = re.match(r'([\d,.]+)(?:$|\s)', s)
		if mobj:
			return str_to_int(mobj.group(1))
	
	video = YouTube(url)
	info = YouTubeResponse(**video.vid_info)
	details = info.videoDetails
	if length_limit:
		if int(details.lengthSeconds) >= int(length_limit):
			raise Exception(f"video is longer than {length_limit} seconds")
	channel = Channel(f"https://youtube.com/channel/{details.channelId}")
	c = {"name": channel.channel_name, "id": channel.channel_id, "url": channel.vanity_url or f"https://youtube.com/channel/{channel.channel_id}"}
	avatars = sorted(channel.initial_data["header"]["pageHeaderRenderer"]["content"]["pageHeaderViewModel"]["image"]["decoratedAvatarViewModel"]["avatar"]["avatarViewModel"]["image"]["sources"], key = lambda x: x["width"] + x["height"], reverse = True)
	metadata = channel.initial_data["header"]["pageHeaderRenderer"]["content"]["pageHeaderViewModel"]["metadata"]["contentMetadataViewModel"]["metadataRows"]
	row = metadata[-1]
	try:
		subscribers = format_value(row["metadataParts"][0]["text"]["content"].split(" ", 1)[0])
	except Exception:
		subscribers = 0
	try:
		videos = format_value(row["metadataParts"][1]["text"]["content"].split(" ", 1)[0])
	except Exception:
		videos = 0
	try:
		likes = format_value(video.initial_data["contents"]["twoColumnWatchNextResults"]["results"]["results"]["contents"][0]["videoPrimaryInfoRenderer"]["videoActions"]["menuRenderer"]["topLevelButtons"][0]["segmentedLikeDislikeButtonViewModel"]["likeButtonViewModel"]["likeButtonViewModel"]["toggleButtonViewModel"]["toggleButtonViewModel"]["defaultButtonViewModel"]["buttonViewModel"]["title"])
	except Exception as error:
		exc = "".join(
			traceback.format_exception(type(error), error, error.__traceback__)
		)
		c["error"] = exc
		likes = 0
	try:
		v = video.initial_data["engagementPanels"][0]["engagementPanelSectionListRenderer"]["header"]["engagementPanelTitleHeaderRenderer"]["contextualInfo"]["runs"][0]["text"]
		try:
			comments = int(v)
		except Exception:
			comments = format_value(v)
	except Exception:
		comments = 0
	statistics = {"likes": likes, "comments": comments}
	c["avatar"] = avatars[0]
	c["statistics"] = {"subscribers": subscribers, "videos": videos, "views": channel.views}
	c["description"] = channel.description
	downloadAddr = video.streams.get_highest_resolution()
	if download:
		data["file"] = downloadAddr.download("files/videos", filename = f"{tuuid()}.mp4")
	filesize = downloadAddr.filesize_approx
	downloadAddr = downloadAddr.url
	for key, value in details.dict().items():
		if key == "thumbnail":
			data["thumbnails"] = value.get("thumbnails", [])
		elif key == "shortDescription":
			if not data.get("description"):
				data["description"] = value
			else:
				data["description"] = value
		elif key == "viewCount":
			statistics["views"] = int(value)
		elif key == "lengthSeconds":
			data["length"] = int(value)
		elif key in ("channelId", "author"):
			continue
		else:
			data[key] = value
	data["statistics"] = statistics
	data["downloadAddr"] = downloadAddr
	data["filesize"] = filesize
	data["channel"] = c
	return data       

async def extract(content: str, *args: Any, **kwargs: Any):
    if not (match := YOUTUBE_WILDCARD.search(content)):
        return None
    data = await download(match.string, *args, **kwargs)
    return YouTubeVideo(**data)


def repost(bot: Client, message: Message) -> Optional[str]:
    if not (match := YOUTUBE_WILDCARD.search(message.content)):
        return None
    else:
        bot.dispatch("youtube_repost", message, match.string)


YOUTUBE_HEADERS = {"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9", "cache-control": "no-cache", "pragma": "no-cache", "priority": "u=0, i", "referer": "https://www.youtube.com/results?search_query=your+mom", "sec-ch-ua": "\"Brave\";v=\"129\", \"Not=A?Brand\";v=\"8\", \"Chromium\";v=\"129\"", "sec-ch-ua-arch": "\"x86\"", "sec-ch-ua-bitness": "\"64\"", "sec-ch-ua-full-version-list": "\"Brave\";v=\"129.0.0.0\", \"Not=A?Brand\";v=\"8.0.0.0\", \"Chromium\";v=\"129.0.0.0\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-model": "\"\"", "sec-ch-ua-platform": "\"Windows\"", "sec-ch-ua-platform-version": "\"15.0.0\"", "sec-ch-ua-wow64": "?0", "sec-fetch-dest": "document", "sec-fetch-mode": "navigate", "sec-fetch-site": "same-origin", "sec-fetch-user": "?1", "sec-gpc": "1", "service-worker-navigation-preload": "true", "upgrade-insecure-requests": "1", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"}

async def search(query: str) -> list:
    async with ClientSession() as session:
        async with session.get(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}", headers = YOUTUBE_HEADERS) as response:
            data = await response.text()
    data = json.loads(data.split("var ytInitialData = ")[1].split(';</script><script nonce="')[0])
    results = []
    search_results = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"]
    for _r in search_results:
        try:
            r = _r["videoRenderer"]
            results.append({"title": r["title"]["runs"][0]["text"], "url":f'https://www.youtube.com/watch?v={r["videoId"]}'})
        except Exception:
            pass
    return results

