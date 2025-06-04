from modules import config

class SocialHelper:
    def __init__(self, bot):
        self.bot = bot

    async def fetch_twitter_post(self, username: str):
        data = await self.bot.session.get_json(f"https://twitter-api45.p.rapidapi.com/timeline.php?screenname={username}&rapidapi-key={config.RAPIDAPI}")
        if data is not None and 'timeline' in data and data['timeline']:
            return data['timeline'][0]
        return None
        
    async def fetch_youtube_channel(self, username: str):
        data = await self.bot.session.get_json(f"https://youtube-v2.p.rapidapi.com/channel/id?channel_name={username}&rapidapi-key={config.RAPIDAPI}")
        if data is not None and 'channel_id' in data and data['channel_id']:
            return data['channel_id']
        return None
        
    async def fetch_youtube_video(self, channel_id: str):
        data = await self.bot.session.get_json(f"https://youtube-v2.p.rapidapi.com/channel/videos?channel_id={channel_id}&rapidapi-key={config.RAPIDAPI}")
        if data is not None and 'videos' in data and data['videos']:
            return data['videos'][0]
        return None
    
    async def fetch_tiktok_video(self, username: str):
        data = await self.bot.session.get_json(f"https://tiktok-best-experience.p.rapidapi.com/user/{username}/feed?rapidapi-key={config.RAPIDAPI}")
        if data is None or 'data' not in data or 'aweme_list' not in data['data'] or not data['data']['aweme_list']:
            return None
        return data['data']['aweme_list'][0]
    
    async def fetch_instagram_post(self, username: str):
        data = await self.bot.session.get_json(f"https://social-api4.p.rapidapi.com/v1/posts?username_or_id_or_url={username}&url_embed_safe=true", headers={"x-rapidapi-key": f"{config.RAPIDAPI}"})
        if data is not None and 'data' in data and data['data']:
            for item in data['data']['items']:
                if not item.get('is_pinned', False):
                    return item
        return None
    
    async def fetch_instagram_post_details(self, code: str):
        data = await self.bot.session.get_json(f"https://social-api4.p.rapidapi.com/v1/post_info?code_or_id_or_url={code}&include_insights=true", headers={"x-rapidapi-key": f"{config.RAPIDAPI}"})
        if data is not None and 'data' in data and data['data']:
            return data['data']
        return None