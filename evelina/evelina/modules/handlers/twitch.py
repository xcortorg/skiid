import time

from modules import config
from modules.misc.session import Session

class TwitchHelper:
    def __init__(self, session: Session):
        self.session = session
        self.auth_token = None
        self.token_expiry = 0

    async def generate_twitch_token(self):
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": config.TWITCH.TWITCH_CLIENT_ID,
            "client_secret": config.TWITCH.TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        res, status = await self.session.post_json(url, params=params, return_status=True)
        if status == 200:
            self.auth_token = res['access_token']
            self.token_expiry = time.time() + res['expires_in']
        else:
            pass
    
    async def fetch_stream_data(self, streamer: str):
        if not self.auth_token or time.time() >= self.token_expiry:
            await self.generate_twitch_token()
        url = "https://api.twitch.tv/helix/streams"
        headers = {
            "Client-Id": config.TWITCH.TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {self.auth_token}"
        }
        params = {"user_login": streamer}
        res, status = await self.session.get_json(url, headers=headers, params=params, return_status=True)
        if status == 200:
            data = res.get("data", [])
            if data:
                stream_info = data[0]
                return {
                    "is_live": True,
                    "viewers": stream_info.get("viewer_count"),
                    "game": stream_info.get("game_name"),
                    "thumbnail_url": stream_info.get("thumbnail_url"),
                    "stream_id": stream_info.get("id"),
                    "title": stream_info.get("title"),
                }
            return {"is_live": False}
        elif status == 401:
            await self.generate_twitch_token()
            return await self.fetch_stream_data(streamer)
        elif status == 404:
            return {"is_live": False}
        else:
            return {"is_live": False}