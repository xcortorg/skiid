from pydantic import BaseModel
from typing import Optional, Any, List, Dict, Any, Union
from cashews import cache
import aiohttp, orjson, asyncio, os, ffmpeg
from tools import thread

#
from yt_dlp import DownloadError, YoutubeDL
from logging import getLogger, ERROR

from loguru import logger

cache.setup("mem://")


class YouTubeChannel(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    channel_url: Optional[str] = None
    is_live: Optional[bool] = False
    follower_count: Optional[int] = None


class YouTubePost(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    description: Optional[str] = None
    full_title: Optional[str] = None
    was_live: Optional[bool] = None
    url: Optional[str] = None
    file: Optional[str] = None
    duration: Optional[int] = None
    fps: Optional[int] = None
    created_at: Optional[int] = None
    author: Optional[YouTubeChannel] = None
    view_count: Optional[int] = None
    original_url: Optional[str] = None
    comment_count: Optional[int] = None


@thread
def extract_data(url: str):
    """
    Asynchronously run YouTubeDL.
    """
    from typing import Optional
    from yt_dlp import DownloadError, YoutubeDL

    data: Optional[dict]
    kwargs = {
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",  # Optional: convert to mp4 format
                "options": {
                    "vcodec": "libx264",  # Specify H.264 codec
                    "acodec": "aac",  # Optional: specify audio codec (AAC)
                },
            }
        ],
        "outtmpl": "%(title)s.%(ext)s",  # Template for output file name
    }
    ytdl = YoutubeDL({"quiet": True, "logger": logger, "verbose": True}.update(kwargs))
    try:
        data = ytdl.extract_info(
            url=str(url),
            download=True,
        )
        if "entries" in data:  # In case of a playlist, pick the first entry
            video = data["entries"][0]
        else:
            video = data
        data["file"] = video["requested_downloads"][0]["filepath"]
    except DownloadError as e:
        raise e

    attempts = 0
    while True:
        try:
            attempts += 1
            if attempts == 10:
                break

            i = ffmpeg.input(data["file"])
            out = i.output(
                "greedyoutube.mp4",
                vcodec="libx264",
                acodec="aac",
                preset="ultrafast",
                threads=10,
            )
            out.run(overwrite_output=True)
            os.remove(data["file"])
            data["file"] = "greedyoutube.mp4"
            break
        except Exception:
            pass
    return data


async def youtube_post(url: str, proxy: str = None, **kwargs) -> Optional[dict]:
    if data := await extract_data(url, **kwargs):
        #        with open("yt.json", "wb") as file: file.write(orjson.dumps(data))
        if not data.get("url"):
            for d in data["formats"][::-1]:
                if (
                    d.get("video_ext", "") == "mp4"
                    and d.get("container", "") == "mp4_dash"
                ):
                    data["url"] = d["url"]
        channel_data = {
            "id": data["channel_id"],
            "name": data["uploader"],
            "channel_url": data["uploader_url"],
            "is_live": data["is_live"],
            "follower_count": data["channel_follower_count"],
        }
        post_data = {
            "id": data["id"],
            "file": data["file"],
            "title": data["title"],
            "full_title": data["fulltitle"],
            "description": data["description"],
            "was_live": data["was_live"],
            "url": data["url"],
            "duration": data["duration"],
            "fps": data["fps"],
            "created_at": int(data["upload_date"]),
            "author": YouTubeChannel(**channel_data),
            "view_count": int(data["view_count"]),
            "original_url": data["original_url"],
            "comment_count": int(data["comment_count"]),
        }
        #        logger.error(post_data)
        d = YouTubePost(**post_data)
        #       async with aiohttp.ClientSession() as session:
        #            async with session.get(d.url) as response:
        #              asset = await response.read()
        #     d = d.dict()
        #    d["asset_data"] = asset
        return d.dict()


# async def test():
#    url = "https://youtube.com/shorts/h9N9b5fsc0w?si=jXfN3SxJ2SJSDUcz"
#    d = await youtube_post(url, format= "bestvideo+bestaudio/best")

# asyncio.run(test())
