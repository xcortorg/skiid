import asyncio

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

class Handler(object):
    def __init__(self, bot, api_key: str):
        self.bot = bot
        self.apikey = api_key
        self.baseurl = "https://ws.audioscrobbler.com/2.0/"

    async def lastfm_user_exists(self, user: str) -> bool:
        a = await self.get_user_info(user)
        return "error" not in a
    
    async def read_image(self, url: str) -> Image:
        image_data, status = await self.bot.session.get_bytes(url, return_status=True)
        if status == 200:
            return Image.open(BytesIO(image_data)).convert("RGBA")
        else:
            raise Exception(f"Failed to read image with status {status}")

    async def do_request(self, data: dict):
        response, status = await self.bot.session.get_json(self.baseurl, params=data, return_status=True)
        if status == 200:
            return response
        else:
            raise Exception(f"Request failed with status {status}")

    async def get_track_playcount(self, user: str, track: dict) -> int:
        try:
            data = {
                "method": "track.getInfo",
                "api_key": self.apikey,
                "artist": track["artist"]["#text"],
                "track": track["name"],
                "format": "json",
                "username": user,
            }
            response = await self.do_request(data)
            if "error" in response:
                return 0
            return response["track"].get("userplaycount", 0)
        except KeyError:
            return 0
        except Exception as e:
            return 0

    async def get_album_playcount(self, user: str, track: dict) -> int:
        try:
            data = {
                "method": "album.getInfo",
                "api_key": self.apikey,
                "artist": track["artist"]["#text"],
                "album": track["album"]["#text"],
                "format": "json",
                "username": user,
            }
            response = await self.do_request(data)
            if "error" in response:
                return 0
            return response["album"].get("userplaycount", 0)
        except KeyError:
            return 0
        except Exception as e:
            return 0

    async def get_artist_playcount(self, user: str, artist: str) -> int:
        try:
            data = {
                "method": "artist.getInfo",
                "api_key": self.apikey,
                "artist": artist,
                "format": "json",
                "username": user,
            }
            response = await self.do_request(data)
            if "error" in response:
                return 0
            return response["artist"]["stats"].get("userplaycount", 0)
        except KeyError:
            return 0
        except Exception as e:
            return 0

    async def get_user_info(self, user: str) -> dict:
        try:
            data = {
                "method": "user.getinfo",
                "user": user,
                "api_key": self.apikey,
                "format": "json",
            }
            response = await self.do_request(data)
            if "error" in response:
                return {"error": "User not found"}
            return response
        except KeyError:
            return {"error": "Invalid response format"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
        
    async def get_artist_info(self, artist: str) -> dict:
        try:
            data = {
                "method": "artist.getinfo",
                "artist": artist,
                "api_key": self.apikey,
                "format": "json",
            }
            response = await self.do_request(data)
            if "error" in response:
                return {"error": "Artist not found"}
            return response
        except KeyError:
            return {"error": "Invalid response format"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    async def get_top_artists(self, user: str, count: int) -> dict:
        try:
            data = {
                "method": "user.getTopArtists",
                "user": user,
                "api_key": self.apikey,
                "format": "json",
                "limit": count,
            }
            response = await self.do_request(data)
            if "error" in response:
                return {"topartists": {"artist": []}}
            return response
        except Exception as e:
            return {"topartists": {"artist": []}}

    async def get_top_tracks(self, user: str, count: int) -> dict:
        try:
            data = {
                "method": "user.getTopTracks",
                "user": user,
                "api_key": self.apikey,
                "format": "json",
                "limit": count,
                "period": "overall",
            }
            response = await self.do_request(data)
            if "error" in response:
                return {"toptracks": {"track": []}}
            return response
        except Exception as e:
            return {"toptracks": {"track": []}}

    async def get_top_albums(self, user: str, count: int) -> dict:
        try:
            data = {
                "method": "user.getTopAlbums",
                "user": user,
                "api_key": self.apikey,
                "format": "json",
                "limit": count,
                "period": "overall",
            }
            response = await self.do_request(data)
            if "error" in response:
                return {"topalbums": {"album": []}}
            return response
        except Exception as e:
            return {"topalbums": {"album": []}}

    async def get_tracks_recent(self, user: str, count: int = 10) -> dict:
        try:
            data = {
                "method": "user.getrecenttracks",
                "user": user,
                "api_key": self.apikey,
                "format": "json",
                "limit": count,
            }
            response = await self.do_request(data)
            if "error" in response:
                return {"recenttracks": {"track": []}}
            return response
        except Exception as e:
            return {"recenttracks": {"track": []}}
    
    async def get_charts_top_albums(self, username: str, period: str, limit: int) -> dict:
        data = {
            "method": "user.getTopAlbums",
            "user": username,
            "api_key": self.apikey,
            "format": "json",
            "period": period,
            "limit": limit,
        }
        return await self.do_request(data)

    async def lastfm_chart(self, username: str, size: str = "3x3", period: str = "overall") -> BytesIO:
        try:
            cols, rows = map(int, size.split("x"))
        except ValueError:
            raise ValueError("Invalid size format. Must be in the format of '3x3', '6x6', '9x9', etc.")
        album_count = cols * rows
        if album_count > 50:
            raise ValueError("Your chart can't contain more than 50 albums.")
        top_albums = await self.get_charts_top_albums(username, period, album_count)
        if "topalbums" not in top_albums or "album" not in top_albums["topalbums"]:
            raise ValueError("No top albums found for the specified period.")
        albums = top_albums["topalbums"]["album"]

        async def fetch_image(album):
            img_url = album["image"][2]["#text"]
            if img_url:
                return await self.read_image(img_url)
            else:
                return await self.create_text_image(album["name"])

        tasks = [fetch_image(album) for album in albums[:album_count]]
        images = await asyncio.gather(*tasks)

        target_size = 300
        resized_images = [ImageOps.fit(img, (target_size, target_size), Image.Resampling.LANCZOS) for img in images]
        grid_width = cols * target_size
        grid_height = rows * target_size
        grid = Image.new("RGB", (grid_width, grid_height))
        for idx, img in enumerate(resized_images):
            x = (idx % cols) * target_size
            y = (idx // cols) * target_size
            grid.paste(img, (x, y))
        buffer = BytesIO()
        grid.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    async def create_text_image(self, text: str) -> Image:
        return await asyncio.get_event_loop().run_in_executor(None, self._sync_create_text_image, text)

    def _sync_create_text_image(self, upper_text: str) -> Image:
        text_image = Image.new("RGB", (200, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(text_image)
        font_size = 15        
        font_path = 'data/fonts/Heavitas.ttf'
        font = ImageFont.truetype(font_path, font_size)
        text_width, text_height = draw.textbbox((0, 0), upper_text, font=font)[2:]
        text_x = (200 - text_width) / 2 - 10
        text_y = 60 + 10
        draw.text((text_x, text_y), upper_text, fill="black", font=font)
        return text_image