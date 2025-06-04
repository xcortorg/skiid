from discord.ext.commands import group, has_permissions
from core.client.context import Context
from tools import CompositeMetaClass, MixinMeta
from datetime import datetime, timezone
import aiohttp
from logging import getLogger
from discord import Embed
from urllib.parse import quote

log = getLogger("evict/riot")

class Riot(MixinMeta, metaclass=CompositeMetaClass):
    """Riot API functionality"""
    

    def __init__(self, bot):
        try:
            super().__init__(bot)
            self.bot = bot
            self.name = "Riot API"
            self.riot_api_key = "RGAPI-067af8d4-d26f-4ab8-a91b-4738e2360d35" 
            self.riot_base_url = "https://api.riotgames.com"
        except Exception as e:
            log.error(f"Failed to initialize Recording cog: {e}")
            return

    async def cog_load(self) -> None:
        """Initialize when cog loads"""
        try:
            await super().cog_load()
        except Exception as e:
            log.error(f"Failed to load Recording cog: {e}")
            return

    async def cog_unload(self) -> None:
        """Cleanup when cog unloads"""
        try:
            for recording in self.active_recordings.values():
                await self.stop_recording(recording['channel'])
        except Exception as e:
            log.error(f"Failed to unload Recording cog: {e}")
            return
        
        try:
            await super().cog_unload()
        except Exception as e:
            log.error(f"Failed to unload Recording parent: {e}")
            return

    async def riot_request(self, endpoint: str, region: str = "na1") -> dict:
        """Make a request to the Riot Games API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://{region}.api.riotgames.com{endpoint}"
                headers = {
                    "X-Riot-Token": "RGAPI-067af8d4-d26f-4ab8-a91b-4738e2360d35"
                }
                
                log.info(f"Making Riot API request:")
                log.info(f"URL: {url}")
                log.info(f"Headers: {headers}")
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        log.error(f"Riot API request failed: {response.status}")
                        response_text = await response.text()
                        log.error(f"Response body: {response_text}")
                        return None
        except Exception as e:
            log.error(f"Error making Riot API request: {e}")
            return None

    @group(name="riot", invoke_without_command=True)
    @has_permissions(administrator=True)
    async def riot(self, ctx: Context):
        """Riot Games API commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @riot.command(name="summoner")
    async def summoner_lookup(self, ctx: Context, *, summoner_name: str):
        """
        Look up a summoner's information
        """
        try:
            clean_name = summoner_name.split('#')[0]
            encoded_name = quote(clean_name)
            endpoint = f"/lol/summoner/v4/summoners/by-name/{encoded_name}"
            
            log.info(f"Making request to endpoint: {endpoint}")
            result = await self.riot_request(endpoint)
            
            if not result:
                await ctx.send("❌ Could not find summoner or there was an API error.")
                return
                
            embed = Embed(title=f"Summoner: {result['name']}", color=0x00ff00)
            embed.add_field(name="Level", value=str(result['summonerLevel']), inline=True)
            embed.add_field(name="Account ID", value=result['accountId'], inline=True)
            embed.add_field(name="PUUID", value=result['puuid'], inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            log.error(f"Error in summoner lookup: {e}")
            await ctx.send("❌ An error occurred while looking up the summoner.")