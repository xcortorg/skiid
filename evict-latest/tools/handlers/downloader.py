from yt_dlp import YoutubeDL
import asyncio
import os
from typing import Dict, Optional, Tuple
import discord
from datetime import datetime
import re
import aiohttp
from yarl import URL
from json import loads


def create_downloader():
    """Factory function to create a downloader instance"""
    return Downloader()


class Downloader:
    SUPPORTED_PLATFORMS = {
        "youtube.com": "YouTube",
        "youtu.be": "YouTube",
        "instagram.com": "Instagram",
        "tiktok.com": "TikTok",
        "twitter.com": "Twitter",
        "x.com": "Twitter",
        "facebook.com": "Facebook",
        "fb.watch": "Facebook",
        "reddit.com": "Reddit",
        "redd.it": "Reddit",
        "soundcloud.com": "SoundCloud",
        "vimeo.com": "Vimeo",
        "twitch.tv": "Twitch",
        "vm.tiktok.com": "TikTok",
        "pinterest.com": "Pinterest",
        "pin.it": "Pinterest",
        "tumblr.com": "Tumblr",
        "dailymotion.com": "Dailymotion",
        "imgur.com": "Imgur",
        "gfycat.com": "Gfycat",
        "streamable.com": "Streamable",
        "liveleak.com": "LiveLeak",
        "bitchute.com": "BitChute",
        "tiktok.com/@": "TikTok",
        "threads.net": "Threads",
    }

    def __init__(self):
        self.base_opts = {
            "format": "best",
            "outtmpl": "downloads/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/json",
                "Accept-Language": "en-US,en;q=0.9",
            },
            "format_sort": ["res:1080", "ext:mp4:m4a"],
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
            "max_duration": 180,
            "extractor_args": {
                "tiktok": {
                    "embed_api": "true",
                    "api_hostname": "api16-normal-c-useast1a.tiktokv.com",
                    "app_version": "v26.1.3",
                    "manifest_app_version": "26.1.3",
                }
            }
        }

    def _get_platform(self, url: str) -> str:
        """Identify the platform from URL"""
        for domain, platform in self.SUPPORTED_PLATFORMS.items():
            if domain in url:
                return platform
        return "Unknown Platform"

    async def _extract_info(
        self, url: str, download: bool = True
    ) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            platform = self._get_platform(url)

            if platform == "TikTok" and "/photo/" not in url:
                opts = self.base_opts.copy()
                with YoutubeDL(opts) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, url, download=True)
                    filename = ydl.prepare_filename(info)
                    info["local_file"] = filename
                    return info, filename

            if platform == "TikTok":
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, allow_redirects=True) as resp:
                        final_url = str(resp.url)
                        
                        if not final_url.startswith("/@"):
                            parts = URL(final_url).parts
                            if len(parts) < 4:
                                raise Exception("Invalid TikTok URL")
                            aweme_id = parts[3]
                            
                            async with session.get(
                                f"https://www.tiktok.com/@i/video/{aweme_id}",
                                headers={
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/",
                                },
                            ) as api_resp:
                                if not api_resp.ok:
                                    raise Exception("Failed to fetch TikTok data")

                                text = await api_resp.text()
                                data = loads(
                                    text.split(
                                        '<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">'
                                    )[1].split("</script>")[0]
                                )
                                post = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]

                                if "imagePost" in post and "images" in post["imagePost"]:
                                    return {
                                        "webpage_url": final_url,
                                        "title": post["desc"] or "TikTok Photo",
                                        "duration": 0,
                                        "ext": "jpg",
                                        "uploader": post["author"]["nickname"],
                                        "like_count": post["stats"]["diggCount"],
                                        "view_count": post["stats"]["playCount"],
                                        "comment_count": post["stats"]["commentCount"],
                                        "images": [
                                            image["imageURL"]["urlList"][-1]
                                            for image in post["imagePost"]["images"]
                                        ],
                                        "_type": "photo"
                                    }, None
                                
                                url = post["video"]["playAddr"]
                                if not url:
                                    raise Exception("No video URL found")

            opts = self.base_opts.copy()
            if platform == "Instagram":
                opts["extract_flat"] = True
            elif platform == "Twitter":
                opts["extract_flat"] = True
            elif platform == "Reddit":
                opts["extract_flat"] = True

            with YoutubeDL(opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=download)

                if info.get("_type") == "playlist":
                    if platform in ["Instagram", "Reddit", "Twitter"]:
                        info = info["entries"][0]

                if info.get("duration", 0) > 180:
                    raise Exception("Video exceeds 3 minutes limit")

                if download:
                    filename = ydl.prepare_filename(info)
                    return info, filename
                return info, None

        except Exception as e:
            error_msg = str(e).lower()
            if "unsupported url" in error_msg:
                raise Exception("This URL is not supported")
            elif "captcha" in error_msg:
                raise Exception("A captcha was detected. Please try again later.")
            elif "copyright" in error_msg:
                raise Exception(
                    "This content is not available due to copyright restrictions."
                )
            elif "private" in error_msg:
                raise Exception("This content is private or requires authentication.")
            elif "unavailable" in error_msg:
                raise Exception("This content is no longer available.")
            elif "rate limit" in error_msg:
                raise Exception("Rate limited by platform. Please try again later.")
            else:
                raise Exception(f"Download failed: {str(e)}")

    def _create_embed(self, info: Dict) -> discord.Embed:
        platform = self._get_platform(info.get("webpage_url", ""))

        embed = discord.Embed(
            title=info.get("title", "Unknown Title"),
            description=info.get("description", "No description available")[:2000],
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )

        if thumbnail := info.get("thumbnail"):
            embed.set_thumbnail(url=thumbnail)

        if uploader := info.get("uploader"):
            embed.set_author(name=f"{uploader} ({platform})")

        stats = []
        if likes := info.get("like_count"):
            stats.append(f"👍 {likes:,}")
        if views := info.get("view_count"):
            stats.append(f"👀 {views:,}")
        if comments := info.get("comment_count"):
            stats.append(f"💬 {comments:,}")
        if repost := info.get("repost_count"):
            stats.append(f"🔄 {repost:,}")

        if duration := info.get("duration"):
            minutes = int(duration) // 60
            seconds = int(duration) % 60
            stats.append(f"⏱️ {minutes}:{seconds:02d}")

        if stats:
            embed.set_footer(text=" | ".join(stats))

        return embed

    async def download(
        self, url: str, max_size: int = 8_000_000
    ) -> Tuple[Optional[Dict], Optional[discord.Embed]]:
        """
        Downloads content and returns info dict and info embed
        For photos: returns (info_dict, embed)
        For videos: returns (info_dict with filename, embed)
        """
        try:
            info, filename = await self._extract_info(url, download=False)

            if info.get("_type") == "photo":
                return info, self._create_embed(info)

            if filesize := info.get("filesize"):
                if filesize > max_size:
                    raise Exception(
                        f"File too large ({filesize/1_000_000:.1f}MB). Maximum size is {max_size/1_000_000:.1f}MB"
                    )

            info, filename = await self._extract_info(url, download=True)
            if filename:
                if os.path.getsize(filename) > max_size:
                    os.remove(filename)
                    raise Exception(f"Downloaded file exceeds size limit")
                info["local_file"] = filename

            return info, self._create_embed(info)

        except Exception as e:
            if filename and os.path.exists(filename):
                os.remove(filename)
            raise Exception(str(e))

    async def get_info(self, url: str) -> discord.Embed:
        """Just gets info without downloading"""
        info, _ = await self._extract_info(url, download=False)
        return self._create_embed(info)

    def cleanup(self, filename: str):
        """Cleanup downloaded files"""
        if os.path.exists(filename):
            os.remove(filename)
