import json
import asyncio

from typing import Literal, Optional

from discord import Embed, User, Member, File
from discord.ext.commands import Cog, group, command

from modules import config
from modules.styles import emojis, colors
from modules.predicates import has_perks, lastfm_user_exists
from modules.handlers.lastfm import Handler
from modules.validators import ValidLastFmName
from modules.helpers import EvelinaContext
from modules.evelinabot import Evelina

class Lastfm(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.lastfmhandler = Handler(self.bot, config.API.LASTFM)

    async def lastfm_replacement(self, user: str, params: str) -> str:
        a = await self.lastfmhandler.get_tracks_recent(user, 1)
        userinfo = await self.lastfmhandler.get_user_info(user)
        userpfp = self.bot.misc.url_encode(userinfo["user"]["image"][2]["#text"])
        artist = a["recenttracks"]["track"][0]["artist"]["#text"]
        try:
            albumplays = await self.lastfmhandler.get_album_playcount(user, a["recenttracks"]["track"][0])
        except:
            albumplays = "N/A"
        artistplays = await self.lastfmhandler.get_artist_playcount(user, artist)
        trackplays = (await self.lastfmhandler.get_track_playcount(user, a["recenttracks"]["track"][0]) or "N/A")
        album = (a["recenttracks"]["track"][0]["album"]["#text"].replace(" ", "+") or "N/A")
        params = (
            params.replace("{track.name}", a["recenttracks"]["track"][0]["name"])
            .replace("{lower(track.name)}", a["recenttracks"]["track"][0]["name"].lower())
            .replace("{track.url}", self.bot.misc.url_encode(a["recenttracks"]["track"][0]["url"]))
            .replace("{artist.name}", a["recenttracks"]["track"][0]["artist"]["#text"])
            .replace("{lower(artist.name)}", a["recenttracks"]["track"][0]["artist"]["#text"].lower())
            .replace("{artist.url}", self.bot.misc.url_encode(f"https://last.fm/music/{artist.replace(' ', '+')}"))
            .replace("{track.image}", self.bot.misc.url_encode(a["recenttracks"]["track"][0]["image"][3]["#text"]))
            .replace("{artist.plays}", str(artistplays))
            .replace("{album.plays}", str(albumplays))
            .replace("{track.plays}", str(trackplays))
            .replace("{album.name}", a["recenttracks"]["track"][0]["album"]["#text"] or "N/A")
            .replace("{lower(album.name)}", (a["recenttracks"]["track"][0]["album"]["#text"].lower() if a["recenttracks"]["track"][0]["album"]["#text"] else "N/A"))
            .replace("{album.url}", self.bot.misc.url_encode(f"https://www.last.fm/music/{artist.replace(' ', '+')}/{album.replace(' ', '+')}") or "https://none.none")
            .replace("{username}", user)
            .replace("{scrobbles}", a["recenttracks"]["@attr"]["total"])
            .replace("{useravatar}", userpfp)
            .replace("{lastfm.color}", "#ffff00")
            .replace("{lastfm.emoji}", f"{emojis.LASTFM}")
            .replace("{album.image}", self.bot.misc.url_encode(a["recenttracks"]["track"][0]["image"][3]["#text"]))
            .replace("{artist.image}", self.bot.misc.url_encode(userinfo["user"]["image"][3]["#text"]))
        )
        return params

    @group(name="lastfm", aliases=["lf"], description="Use the Last.fm API integration with evelina", invoke_without_command=True, case_insensitive=True)
    async def lastfm(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @lastfm.command(name="set", aliases=["login", "connect"], usage="lastfm set worldstar", description="Login and authenticate evelina to use your account")
    async def lf_set(self, ctx: EvelinaContext, *, username: ValidLastFmName):
        mes = await ctx.send(embed=Embed(color=colors.LOADING, description=f"{emojis.LOADING} {ctx.author.mention}: Logging in and fetching all informations..."))
        await asyncio.sleep(1)
        embed = Embed(
            color=colors.SUCCESS,
            description = (
                f"{emojis.APPROVE} {ctx.author.mention}: "
                f"Logged in as [**{username['user']['name']}**]({username['user']['url']})"
                f" with `{int(username['user']['playcount']):,}` Scrobbles")        
            )
        await mes.edit(embed=embed)

    @lastfm.command(name="unset", aliases=["logout", "disconnect"], usage="lastfm unset", description="Logout and disconnect evelina from your account")
    @lastfm_user_exists()
    async def lf_remove(self, ctx: EvelinaContext):
        await self.bot.db.execute("DELETE FROM lastfm WHERE user_id = $1", ctx.author.id)
        return await ctx.lastfm_send("Removed your **Last.Fm** account")

    @lastfm.command(name="chart", aliases=["c"], usage="lastfm chart comminate 3x3 7day", description="View a collage of your most listened to albums")
    async def lf_chart(self, ctx: EvelinaContext, member: Optional[Member] = None, size: str = "3x3", period: Literal["overall", "7day", "1month", "3month", "6month", "12month"] = "overall"):
        if member is None:
            member = ctx.author
        username = await self.bot.db.fetchval("SELECT username FROM lastfm WHERE user_id = $1", member.id)
        try:
            image_buffer = await self.lastfmhandler.lastfm_chart(username, size, period)
        except Exception:
            return await ctx.send_warning(f"You havn't scrobbled any songs yet")
        chart_file = File(image_buffer, filename="chart.png")
        await ctx.reply(f"{member.mention}'s Last.FM **{size}** album chart ({period})", file=chart_file)

    @lastfm.command(name="plays", aliases=["p"], usage="lastfm plays comminate", description="Get the total amount of plays of a user for certain artist")
    async def lf_plays(self, ctx: EvelinaContext, user: Optional[Member] = None, *, artist: str = None):
        if user is None:
            user = ctx.author
        username = await self.bot.db.fetchval("SELECT username FROM lastfm WHERE user_id = $1", user.id)
        if not username:
            return await ctx.lastfm_send(f"{'You don' if user == ctx.author else f'**{user.mention}** doesn'}'t have a **last.fm** account connected")
        if artist is None:
            a = await self.lastfmhandler.get_tracks_recent(username, 1)
            if not a.get("recenttracks") or not a["recenttracks"].get("track"):
                return await ctx.lastfm_send("Couldn't retrieve the recent track for your Last.fm account")
            recent_tracks = a["recenttracks"]["track"]
            artist = recent_tracks[0].get("artist", {}).get("#text", None)
            if not artist:
                return await ctx.lastfm_send("Couldn't retrieve artist information from the recent track")
        plays = await self.lastfmhandler.get_artist_playcount(username, artist)
        if not plays:
            return await ctx.send_warning(f"Couldn't retrieve the amount of plays for **{artist}**")
        return await ctx.lastfm_send(f"**{user.name}** has **{int(plays):,}** plays for **{artist}**")

    @lastfm.command(name="customcommand", aliases=["cc"], usage="lastfm customcommand bfm", description="Set a custom command for nowplaying")
    async def lf_customcommand(self, ctx: EvelinaContext, *, cmd: str):
        check = await self.bot.db.fetchrow("SELECT * FROM lastfm WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.lastfm_send(f"You don't have a **Last.fm** account set.\n> Use `{ctx.clean_prefix}lastfm set` to login into your account")
        if cmd.lower() == "none":
            if not check["customcmd"]:
                return await ctx.lastfm_send("You don't have any **custom command**")
            else:
                await self.bot.db.execute("UPDATE lastfm SET customcmd = $1 WHERE user_id = $2", None, ctx.author.id)
                return await ctx.lastfm_send("Removed your **Last.Fm** custom command")
        await self.bot.db.execute("UPDATE lastfm SET customcmd = $1 WHERE user_id = $2", cmd, ctx.author.id)
        return await ctx.lastfm_send(f"You **Last.Fm** custom command set to: {cmd}")

    @lastfm.group(name="mode", aliases=["embed"], description="Use a different embed for now playing or create your own", invoke_without_command=True, case_insensitive=True)
    async def lf_mode(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @lf_mode.command(name="set", brief="donator", usage="lastfm mode set Listening to **{track.name}**", description="Set a custom embed for nowplaying")
    @lastfm_user_exists()
    @has_perks()
    async def lf_mode_set(self, ctx: EvelinaContext, *, code: str):
        template = await self.bot.db.fetchval("SELECT embed FROM embeds_templates WHERE code = $1", code)
        if template:
            code = template
        await self.bot.db.execute("UPDATE lastfm SET embed = $1 WHERE user_id = $2", code, ctx.author.id)
        return await ctx.lastfm_send(f"Your custom **Last.Fm** embed is configured to\n```{code}```")

    @lf_mode.command(name="remove", brief="donator", description="Remove your custom lastfm embed")
    @lastfm_user_exists()
    @has_perks()
    async def lf_mode_remove(self, ctx: EvelinaContext):
        await self.bot.db.execute("UPDATE lastfm SET embed = $1 WHERE user_id = $2", None, ctx.author.id)
        return await ctx.lastfm_send("Removed your **Last.Fm** custom embed")

    @lf_mode.command(name="reply", brief="donator", usage="lastfm mode reply on", description="Enable or disable if bot should reply with lastfm message")
    @lastfm_user_exists()
    @has_perks()
    async def lf_mode_reply(self, ctx: EvelinaContext, option: str):
        if option.lower() == "on":
            await self.bot.db.execute("UPDATE lastfm SET reply = $1 WHERE user_id = $2", True, ctx.author.id)
            return await ctx.send_success("Enabled **Last.Fm** reply for custom embed")
        elif option.lower() == "off":
            await self.bot.db.execute("UPDATE lastfm SET reply = $1 WHERE user_id = $2", False, ctx.author.id)
            return await ctx.send_success("Disabled **Last.Fm** reply for custom embed")
        else:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")

    @lf_mode.command(name="view", brief="donator", usage="lastfm mode view comminate", description="View your custom lastfm embed or someone's lastfm embed")
    @has_perks()
    async def lf_mode_view(self, ctx: EvelinaContext, *, member: Optional[User] = None):
        if member is None:
            member = ctx.author
        check = await self.bot.db.fetchrow("SELECT embed FROM lastfm WHERE user_id = $1", member.id)
        if not check:
            return await ctx.lastfm_send("The member provided doesn't have a **Last.Fm** account connected")
        embed = Embed(color=colors.NEUTRAL, title=f"{member.name}'s custom lastfm embed", description=f"```\n{check[0]}```")
        await ctx.send(embed=embed)

    @lf_mode.command(name="steal", brief="donator", usage="lastfm mode steal comminate", description="Steal someone's lastfm embed")
    @has_perks()
    async def lf_mode_steal(self, ctx: EvelinaContext, *, member: Member):
        if member is ctx.author:
            return await ctx.send_warning("Stealing from yourself doesn't make sense")
        check = await self.bot.db.fetchrow("SELECT embed FROM lastfm WHERE user_id = $1", member.id)
        if not check:
            return await ctx.lastfm_send("This member doesn't have a custom embed")
        await self.bot.db.execute("UPDATE lastfm SET embed = $1 WHERE user_id = $2", check[0], ctx.author.id)
        return await ctx.lastfm_send(f"Stolen {member.mention}'s **Last.Fm** custom embed")

    @lastfm.command(name="reactions", usage="lastfm reactions 🔥 🗑️", description="Set custom reactions for the nowplaying command")
    @lastfm_user_exists()
    async def lf_reactions(self, ctx: EvelinaContext, *, reactions: str):
        reactions_list = reactions.split()
        if len(reactions_list) == 0:
            return await ctx.send_help(ctx.command)
        elif len(reactions_list) == 1:
            if reactions_list[0] == "default":
                reacts = ["🔥", "🗑️"]
            elif reactions_list[0] == "none":
                reacts = []
            else:
                reacts = reactions_list
        else:
            reacts = reactions_list
        to_dump = json.dumps(reacts)
        await self.bot.db.execute("UPDATE lastfm SET reactions = $1 WHERE user_id = $2", to_dump, ctx.author.id)
        return await ctx.lastfm_send(f"Your **Last.Fm** reactions are set as {' '.join(reacts) if len(reacts) > 0 else 'none'}")

    @lastfm.command(name="spotify", aliases=["sp"], usage="lastfm spotify comminate", description="Look up for your nowplaying lastfm song on spotify")
    async def lf_spotify(self, ctx: EvelinaContext, *, member: Optional[Member] = None):
        if member is None:
            member = ctx.author
        check = await self.bot.db.fetchrow("SELECT * FROM lastfm WHERE user_id = $1", member.id)
        if not check:
            return await ctx.lastfm_send("There is no **last.fm** account linked for this member")
        user = check["username"]
        a = await self.lastfmhandler.get_tracks_recent(user, 1)
        if not a['recenttracks']['track']:
            return await ctx.send_warning("You haven't scrobbled any songs yet")
        track_name = a['recenttracks']['track'][0]['name']
        artist_name = a['recenttracks']['track'][0]['artist']['#text']
        query = f"{track_name} {artist_name}"
        data = await self.bot.session.get_json(f"https://api.evelina.bot/spotify/track?q={query}&key=X3pZmLq82VnHYTd6Cr9eAw")
        if 'message' in data:
            await ctx.send_warning(f"Couldn't get information about **{user}**")
            return
        track_info = data.get('track', {})
        artist_info = data.get('artist', {})
        album_info = data.get('album', {})
        track_name = track_info.get('name', 'Unknown Track')
        track_url = track_info.get('url', '#')
        artist_name = artist_info.get('name', 'Unknown Artist')
        artist_url = artist_info.get('url', '#')
        album_name = album_info.get('name', 'Unknown Album')
        album_url = album_info.get('url', '#')
        await ctx.send(f"{track_url}")

    @lastfm.command(name="topartists", aliases=["ta", "tar"], usage="lastfm topartists comminate", description="Get the top artists of a user")
    async def lf_topartists(self, ctx: EvelinaContext, member: Optional[Member] = None,):
        if member is None:
            member = ctx.author
        check = await self.bot.db.fetchrow("SELECT * FROM lastfm WHERE user_id = $1", member.id)
        if check:
            user = check["username"]
            data = await self.lastfmhandler.get_top_artists(user, 10)
            artists = data.get('topartists', {}).get('artist', [])
            num_artists = min(10, len(artists))
            if num_artists == 0:
                return await ctx.send_warning("No top artists found for this user")
            mes = "\n".join(
                f"`{i+1}.` **[{artists[i]['name']}]({artists[i]['url']})** {int(artists[i]['playcount']):,} plays" 
                for i in range(num_artists)
            )
            embed = Embed(description=mes, color=colors.NEUTRAL)
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.set_author(name=f"{user}'s overall top artists", icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
            return await ctx.send(embed=embed)
        return await ctx.lastfm_send("There is no **last.fm** account linked for this member")

    @lastfm.command(name="toptracks", aliases=["tt"], usage="lastfm toptracks comminate", description="Get the top tracks of a user")
    async def lf_toptracks(self, ctx: EvelinaContext, *, member: Optional[Member] = None):
        if member is None:
            member = ctx.author
        check = await self.bot.db.fetchrow("SELECT * FROM lastfm WHERE user_id = $1", member.id)
        if check:
            user = check["username"]
            jsonData = await self.lastfmhandler.get_top_tracks(user, 10)
            tracks = jsonData.get('toptracks', {}).get('track', [])
            num_tracks = min(10, len(tracks))
            if num_tracks == 0:
                return await ctx.send_warning("No top tracks found for this user")
            embed = Embed(
                description="\n".join(
                    f"`{i+1}.` **[{tracks[i]['name']}]({tracks[i]['url']})** {int(tracks[i]['playcount']):,} plays"
                    for i in range(num_tracks)
                ), 
                color=colors.NEUTRAL
            )
            embed.set_thumbnail(url=ctx.author.avatar)
            embed.set_author(name=f"{user}'s overall top tracks", icon_url=ctx.author.avatar)
            return await ctx.send(embed=embed)
        return await ctx.lastfm_send("There is no **last.fm** account linked for this member")

    @lastfm.command(name="topalbums", aliases=["tal"], usage="lastfm topalbums comminate", description="Get the top albums of a user")
    async def lf_topalbums(self, ctx: EvelinaContext, *, member: Optional[Member] = None):
        if member is None:
            member = ctx.author
        check = await self.bot.db.fetchrow("SELECT * FROM lastfm WHERE user_id = $1", member.id)
        if check:
            user = check["username"]
            jsonData = await self.lastfmhandler.get_top_albums(user, 10)
            albums = jsonData.get('topalbums', {}).get('album', [])
            num_albums = min(10, len(albums))
            if num_albums == 0:
                return await ctx.send_warning("No top albums found for this user")
            embed = Embed(
                description="\n".join(
                    f"`{i+1}.` **[{albums[i]['name']}]({albums[i]['url']})** {int(albums[i]['playcount']):,} plays"
                    for i in range(num_albums)
                ), 
                color=colors.NEUTRAL
            )
            embed.set_thumbnail(url=ctx.author.avatar)
            embed.set_author(name=f"{user}'s overall top albums", icon_url=ctx.author.avatar)
            return await ctx.send(embed=embed)
        return await ctx.lastfm_send("There is no **last.fm** account linked for this member")

    @lastfm.command(name="howto", help="lastfm", description="A short guide on how to register your lastfm account")
    async def lf_howto(self, ctx: EvelinaContext):
        embed = Embed(title="Last.fm Tutorial", color=colors.LASTFM,
            description=(
                f"1) create an account at [**last.fm**](https://last.fm)\n"
                f"2) link your **spotify** account to your [**last.fm**](https://www.last.fm/settings/applications) account\n"
                f"3) use the command `{ctx.clean_prefix}lf set [your lastfm username]`\n"
                f"4) while you listen to your songs, you can use the `{ctx.clean_prefix}nowplaying` command"
            )
        )
        return await ctx.send(embed=embed)

    @lastfm.command(name="user", aliases=["ui", "profile"], usage="lastfm user comminate", description="Get information about a user's lastfm account")
    async def lf_user(self, ctx: EvelinaContext, member: Optional[User] = None):
        if member is None:
            member = ctx.author
        async with ctx.typing():
            check = await self.bot.db.fetchrow("SELECT username FROM lastfm WHERE user_id = $1", member.id)
            if not check:
                return await ctx.lastfm_send(f"{'You don' if member == ctx.author else f'**{member.mention}** doesn'}'t have a **last.fm** account connected")
            username = check["username"]
            info = await self.lastfmhandler.get_user_info(username)
            try:
                i = info["user"]
                name = i["name"]
                url = i["url"]
                age = int(i["age"])
                subscriber = f"{'false' if i['subscriber'] == '0' else 'true'}"
                realname = i["realname"]
                playcount = int(i["playcount"])
                artistcount = int(i["artist_count"])
                trackcount = int(i["track_count"])
                albumcount = int(i["album_count"])
                image = i["image"][3]["#text"]
                embed = Embed(color=colors.NEUTRAL, title=name, url=url)
                embed.set_thumbnail(url=image)
                embed.add_field(name=f"Plays", value=f"**artists:** {artistcount:,}\n**plays:** {playcount:,}\n**tracks:** {trackcount:,}\n**albums:** {albumcount:,}", inline=True)
                embed.add_field(name=f"Info", value=f"**name:** {realname}\n**registered:** <t:{int(i['registered']['#text'])}:R>\n**subscriber:** {subscriber}\n**age:** {age:,}", inline=True)
                await ctx.send(embed=embed)
            except TypeError:
                return await ctx.lastfm_send("This user doesn't have a **last.fm** account connected")

    @lastfm.command(name="whoknows", aliases=["wk"], usage="lastfm whoknows yeat", description="Get the top listeners of a certain artist from the server")
    async def lf_whoknows(self, ctx: EvelinaContext, *, artist: str = None):
        check = await self.bot.db.fetchrow("SELECT username FROM lastfm WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.lastfm_send(f"You don't have a **Last.fm** account set.\n> Use `{ctx.clean_prefix}lastfm set` to login into your account")
        if artist is None:
            a = await self.lastfmhandler.get_tracks_recent(check[0], 1)
            if not a.get("recenttracks") or not a["recenttracks"].get("track"):
                return await ctx.lastfm_send("Couldn't retrieve the recent track for your Last.fm account")
            recent_tracks = a["recenttracks"]["track"]
            artist = recent_tracks[0].get("artist", {}).get("#text", None)
            if not artist:
                return await ctx.lastfm_send("Couldn't retrieve artist information from the recent track")
        artist_info = await self.lastfmhandler.get_artist_info(artist)
        artist_image = artist_info.get("artist", {}).get("image", [])[3].get("#text", None) if artist_info.get("artist", {}).get("image", []) else None
        async with ctx.typing():
            wk = []
            results = await self.bot.db.fetch(f"SELECT * FROM lastfm WHERE user_id IN ({','.join([str(m.id) for m in ctx.guild.members])})")
            tasks = []
            user_data = []
            for r in results:
                member = ctx.guild.get_member(r["user_id"])
                if member:
                    tasks.append(self.lastfmhandler.get_artist_playcount(r["username"], artist))
                    user_data.append((r["username"], member.name, f"https://last.fm/user/{r['username']}"))
            playcounts = await asyncio.gather(*tasks, return_exceptions=True)
            for (username, member_name, profile_url), playcount in zip(user_data, playcounts):
                if isinstance(playcount, Exception) or not isinstance(playcount, (int, str)) or int(playcount) == 0:
                    continue
                wk.append((member_name, int(playcount), profile_url))
            if not wk:
                return await ctx.send_warning(f"No one in the server has listened to **{artist}**")
        pagination_content = [f"[**{result[0]}**]({result[2]}) has **{int(result[1]):,}** plays" for result in sorted(wk, key=lambda m: int(m[1]), reverse=True)]
        if not pagination_content:
            return await ctx.send_warning(f"No one in the server has listened to **{artist}**")
        return await ctx.paginate(pagination_content, f"Who knows {artist}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None}, image=artist_image)

    @lastfm.command(name="globalwhoknows", aliases=["gwk"], usage="lastfm globalwhoknows yeat", description="Get the top listeners of a certain artist from the server")
    async def lf_globalwhoknows(self, ctx: EvelinaContext, *, artist: str = None):
        check = await self.bot.db.fetchrow("SELECT username FROM lastfm WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.lastfm_send(f"You don't have a **Last.fm** account set.\n> Use `{ctx.clean_prefix}lastfm set` to login into your account")
        if artist is None:
            a = await self.lastfmhandler.get_tracks_recent(check[0], 1)
            if not a.get("recenttracks") or not a["recenttracks"].get("track"):
                return await ctx.lastfm_send("Couldn't retrieve the recent track for your Last.fm account")
            recent_tracks = a["recenttracks"]["track"]
            artist = recent_tracks[0].get("artist", {}).get("#text", None)
            if not artist:
                return await ctx.lastfm_send("Couldn't retrieve artist information from the recent track")
        artist_info = await self.lastfmhandler.get_artist_info(artist)
        artist_image = artist_info.get("artist", {}).get("image", [])[3].get("#text", None) if artist_info.get("artist", {}).get("image", []) else None
        async with ctx.typing():
            wk = []
            results = await self.bot.db.fetch("SELECT * FROM lastfm")
            tasks = []
            user_data = []
            for r in results:
                user = self.bot.get_user(r["user_id"])
                if user:
                    tasks.append(self.lastfmhandler.get_artist_playcount(r["username"], artist))
                    user_data.append((r["username"], user.name, user.id, f"https://last.fm/user/{r['username']}"))
            playcounts = await asyncio.gather(*tasks, return_exceptions=True)
            for (username, member_name, user_id, profile_url), playcount in zip(user_data, playcounts):
                if isinstance(playcount, Exception) or not isinstance(playcount, (int, str)) or int(playcount) == 0:
                    continue
                wk.append((member_name, user_id, int(playcount), profile_url))
            if not wk:
                return await ctx.lastfm_send(f"No one has listened to **{artist}**")
        wk = sorted(wk, key=lambda x: int(x[2]), reverse=True)
        pagination_content = [f"[**{result[0]}**]({result[3]}) has **{int(result[2]):,}** plays" for result in wk]
        await ctx.paginate(pagination_content, f"Global who knows {artist}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None}, image=artist_image)
        top_user_id, top_user_name = wk[0][1], wk[0][0]
        check_crown = await self.bot.db.fetchrow("SELECT user_id FROM lastfm_crowns WHERE artist = $1", artist)
        if check_crown:
            if check_crown["user_id"] == top_user_id:
                return
            await self.bot.db.execute("UPDATE lastfm_crowns SET user_id = $1 WHERE artist = $2", top_user_id, artist)
            previous_user = self.bot.get_user(check_crown["user_id"])
            return await ctx.embed(f"**{top_user_name}** took the crown from **{previous_user}** for **{artist}**!", color=colors.WARNING, emoji="👑")
        else:
            await self.bot.db.execute("INSERT INTO lastfm_crowns (artist, user_id) VALUES ($1, $2)", artist, top_user_id)
            return await ctx.embed(f"**{top_user_name}** took the crown for **{artist}**!", color=colors.WARNING, emoji="👑")

    @lastfm.command(name="whoknowsalbum", aliases=["wka"], usage="lastfm whoknowsalbum yeat", description="Get the top listeners of a certain album from the server")
    async def lf_whoknowsalbum(self, ctx: EvelinaContext, *, album: str = None):
        check = await self.bot.db.fetchrow("SELECT username FROM lastfm WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.lastfm_send(f"You don't have a **Last.fm** account set.\n> Use `{ctx.clean_prefix}lastfm set` to login into your account")
        if album is None:
            a = await self.lastfmhandler.get_tracks_recent(check[0], 1)
            if not a.get("recenttracks") or not a["recenttracks"].get("track"):
                return await ctx.lastfm_send("Couldn't retrieve the recent track for your Last.fm account")
            recent_tracks = a["recenttracks"]["track"]
            album = recent_tracks[0].get("album", {}).get("#text", None)
            if not album:
                return await ctx.lastfm_send("Couldn't retrieve album information from the recent track")
        async with ctx.typing():
            wk = []
            results = await self.bot.db.fetch(f"SELECT * FROM lastfm WHERE user_id IN ({','.join([str(m.id) for m in ctx.guild.members])})")
            tasks = []
            user_data = []
            for r in results:
                member = ctx.guild.get_member(r["user_id"])
                if member:
                    tasks.append(self.lastfmhandler.get_album_playcount(r["username"], recent_tracks[0]))
                    user_data.append((r["username"], member.name, f"https://last.fm/user/{r['username']}"))
            playcounts = await asyncio.gather(*tasks, return_exceptions=True)
            for (username, member_name, profile_url), playcount in zip(user_data, playcounts):
                if isinstance(playcount, Exception) or not isinstance(playcount, (int, str)) or int(playcount) == 0:
                    continue  
                wk.append((member_name, int(playcount), profile_url))
            if not wk:
                return await ctx.send_warning(f"No one in the server has listened to **{album}**")
        pagination_content = [f"[**{result[0]}**]({result[2]}) has **{int(result[1]):,}** plays" for result in sorted(wk, key=lambda m: int(m[1]), reverse=True)]
        if not pagination_content:
            return await ctx.send_warning(f"No one in the server has listened to **{album}**")
        return await ctx.paginate(pagination_content, f"Who knows {album}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @lastfm.command(name="globalwkalbum", aliases=["gwka"], usage="lastfm globalwkalbum yeat", description="Get the top listeners of a certain album from the server")
    async def lf_globalwkalbum(self, ctx: EvelinaContext, *, album: str = None):
        check = await self.bot.db.fetchrow("SELECT username FROM lastfm WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.lastfm_send(f"You don't have a **Last.fm** account set.\n> Use `{ctx.clean_prefix}lastfm set` to login into your account")
        if album is None:
            a = await self.lastfmhandler.get_tracks_recent(check[0], 1)
            if not a.get("recenttracks") or not a["recenttracks"].get("track"):
                return await ctx.lastfm_send("Couldn't retrieve the recent track for your Last.fm account")
            recent_tracks = a["recenttracks"]["track"]
            album = recent_tracks[0].get("album", {}).get("#text", None)
            if not album:
                return await ctx.lastfm_send("Couldn't retrieve album information from the recent track")
        async with ctx.typing():
            wk = []
            results = await self.bot.db.fetch("SELECT * FROM lastfm")
            tasks = []
            user_data = []
            for r in results:
                user = self.bot.get_user(r["user_id"])
                if user:
                    tasks.append(self.lastfmhandler.get_album_playcount(r["username"], recent_tracks[0]))
                    user_data.append((r["username"], user.name, f"https://last.fm/user/{r['username']}"))
            playcounts = await asyncio.gather(*tasks, return_exceptions=True)
            for (username, member_name, profile_url), playcount in zip(user_data, playcounts):
                if isinstance(playcount, Exception) or not isinstance(playcount, (int, str)) or int(playcount) == 0:
                    continue  
                wk.append((member_name, int(playcount), profile_url))
            if not wk:
                return await ctx.lastfm_send(f"No one has listened to **{album}**")
        pagination_content = [f"[**{result[0]}**]({result[2]}) has **{int(result[1]):,}** plays" for result in sorted(wk, key=lambda m: int(m[1]), reverse=True)]
        if not pagination_content:
            return await ctx.send_warning(f"No one has listened to **{album}**")
        return await ctx.paginate(pagination_content, f"Who knows {album}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @lastfm.command(name="whoknowstrack", aliases=["wkt"], usage="lastfm whoknowstrack yeat", description="Get the top listeners of a certain track from the server")
    async def lf_whoknowstrack(self, ctx: EvelinaContext, *, track: str = None):
        check = await self.bot.db.fetchrow("SELECT username FROM lastfm WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.lastfm_send(f"You don't have a **Last.fm** account set.\n> Use `{ctx.clean_prefix}lastfm set` to login into your account")
        if track is None:
            a = await self.lastfmhandler.get_tracks_recent(check[0], 1)
            if not a.get("recenttracks") or not a["recenttracks"].get("track"):
                return await ctx.lastfm_send("Couldn't retrieve the recent track for your Last.fm account")
            recent_tracks = a["recenttracks"]["track"]
            track = recent_tracks[0].get("name", None)
            if not track:
                return await ctx.lastfm_send("Couldn't retrieve track information from the recent track")
        async with ctx.typing():
            wk = []
            results = await self.bot.db.fetch(f"SELECT * FROM lastfm WHERE user_id IN ({','.join([str(m.id) for m in ctx.guild.members])})")
            tasks = []
            user_data = []
            for r in results:
                member = ctx.guild.get_member(r["user_id"])
                if member:
                    tasks.append(self.lastfmhandler.get_track_playcount(r["username"], recent_tracks[0]))
                    user_data.append((r["username"], member.name, f"https://last.fm/user/{r['username']}"))
            playcounts = await asyncio.gather(*tasks, return_exceptions=True)
            for (username, member_name, profile_url), playcount in zip(user_data, playcounts):
                if isinstance(playcount, Exception) or not isinstance(playcount, (int, str)) or int(playcount) == 0:
                    continue  
                wk.append((member_name, int(playcount), profile_url))
            if not wk:
                return await ctx.send_warning(f"No one in the server has listened to **{track}**")
        pagination_content = [f"[**{result[0]}**]({result[2]}) has **{int(result[1]):,}** plays" for result in sorted(wk, key=lambda m: int(m[1]), reverse=True)]
        if not pagination_content:
            return await ctx.send_warning(f"No one in the server has listened to **{track}**")
        return await ctx.paginate(pagination_content, f"Who knows {track}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @lastfm.command(name="globalwktrack", aliases=["gwkt"], usage="lastfm globalwktrack yeat", description="Get the top listeners of a certain track from the server")
    async def lf_globalwktrack(self, ctx: EvelinaContext, *, track: str = None):
        check = await self.bot.db.fetchrow("SELECT username FROM lastfm WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.lastfm_send(f"You don't have a **Last.fm** account set.\n> Use `{ctx.clean_prefix}lastfm set` to login into your account")
        if track is None:
            a = await self.lastfmhandler.get_tracks_recent(check[0], 1)
            if not a.get("recenttracks") or not a["recenttracks"].get("track"):
                return await ctx.lastfm_send("Couldn't retrieve the recent track for your Last.fm account")
            recent_tracks = a["recenttracks"]["track"]
            track = recent_tracks[0].get("name", None)
            if not track:
                return await ctx.lastfm_send("Couldn't retrieve track information from the recent track")
        async with ctx.typing():
            wk = []
            results = await self.bot.db.fetch("SELECT * FROM lastfm")
            tasks = []
            user_data = []
            for r in results:
                user = self.bot.get_user(r["user_id"])
                if user:
                    tasks.append(self.lastfmhandler.get_track_playcount(r["username"], recent_tracks[0]))
                    user_data.append((r["username"], user.name, f"https://last.fm/user/{r['username']}"))
            playcounts = await asyncio.gather(*tasks, return_exceptions=True)
            for (username, member_name, profile_url), playcount in zip(user_data, playcounts):
                if isinstance(playcount, Exception) or not isinstance(playcount, (int, str)) or int(playcount) == 0:
                    continue  
                wk.append((member_name, int(playcount), profile_url))
            if not wk:
                return await ctx.lastfm_send(f"No one has listened to **{track}**")
        pagination_content = [f"[**{result[0]}**]({result[2]}) has **{int(result[1]):,}** plays" for result in sorted(wk, key=lambda m: int(m[1]), reverse=True)]
        if not pagination_content:
            return await ctx.send_warning(f"No one has listened to **{track}**")
        return await ctx.paginate(pagination_content, f"Who knows {track}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @lastfm.command(name="taste", usage="lastfm taste comminate", description="Compare your music taste between you and someone else")
    async def lf_taste(self, ctx: EvelinaContext, member: Member):
        user1 = await self.bot.db.fetchval("SELECT username FROM lastfm WHERE user_id = $1", ctx.author.id)
        user2 = await self.bot.db.fetchval("SELECT username FROM lastfm WHERE user_id = $1", member.id)
        if not user1:
            return await ctx.lastfm_send(f"You don't have a **Last.fm** account set. Use `{ctx.clean_prefix}lastfm set` to login to your account.")
        if not user2:
            return await ctx.lastfm_send(f"{member.mention} doesn't have a **Last.fm** account set.")
        async with ctx.typing():
            data_user1, data_user2 = await asyncio.gather(
                self.lastfmhandler.get_top_artists(user1, 100),
                self.lastfmhandler.get_top_artists(user2, 100)
            )
            artists_user1 = {artist['name']: int(artist['playcount']) for artist in data_user1.get('topartists', {}).get('artist', [])}
            artists_user2 = {artist['name']: int(artist['playcount']) for artist in data_user2.get('topartists', {}).get('artist', [])}
            common_artists = set(artists_user1.keys()).intersection(artists_user2.keys())
            if not common_artists:
                return await ctx.send_warning(f"{ctx.author.mention} and {member.mention} have no artists in common.")
            common_artists_list = sorted(common_artists, key=lambda artist: (artists_user1[artist] + artists_user2[artist]), reverse=True)
            artists_lines = []
            play_counts_lines = []
            for artist in common_artists_list:
                artists_lines.append(artist)
                play_counts_lines.append(f"{artists_user1[artist]:,} > {artists_user2[artist]:,}")
            chunk_size = 10
            chunks = [(artists_lines[i:i + chunk_size], play_counts_lines[i:i + chunk_size]) for i in range(0, len(artists_lines), chunk_size)]
            embeds = []
            for i, (artists_chunk, play_counts_chunk) in enumerate(chunks):
                embed = Embed(color=colors.NEUTRAL, title=f"Taste comparison - {ctx.author.name} v {member.name}")
                embed.description = f"You both have **{len(common_artists)} artists** in common"
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                embed.add_field(name="Artists", value="\n".join(artists_chunk), inline=True)
                embed.add_field(name="Play Counts", value="\n".join(play_counts_chunk), inline=True)
                embed.set_footer(text=f"Page: {i + 1}/{len(chunks)} ({len(common_artists)} entries)")
                embeds.append(embed)

        return await ctx.paginator(embeds)
    @lastfm.command(name="cover", aliases=["image"], usage="lastfm cover comminate", description="Get the cover image of your lastfm song")
    async def lf_cover(self, ctx: EvelinaContext, *, member: Optional[Member] = None):
        if member is None:
            member = ctx.author
        check = await self.bot.db.fetchrow("SELECT username FROM lastfm WHERE user_id = $1", member.id)
        if check is None:
            return await ctx.lastfm_send(f"{'You don' if member == ctx.author else f'{member.mention} doesn'}'t have a **last.fm** account connected")
        user = check[0]
        a = await self.lastfmhandler.get_tracks_recent(user, 1)
        try:
            a = await self.lastfmhandler.get_tracks_recent(user, 1)
            track_info = a.get("recenttracks", {}).get("track", [{}])[0]
            image_url = track_info.get("image", [{}])[3].get("#text", "")
            if not image_url or not image_url.startswith("http"):
                return await ctx.send_warning(f"Could not fetch a image from last.fm API for the track **{track_info.get('name', 'Unknown')}**")
            file = File(await self.bot.getbyte(image_url), filename="cover.png")
            return await ctx.send(f"**{track_info['name']}**", file=file)
        except KeyError:
            return await ctx.send_warning("Unexpected response structure from **Last.fm**. Please try again later.")
        except Exception:
            return await ctx.send_warning("An error occurred while processing your request")

    @lastfm.command(name="recent", usage="lastfm recent comminate", description="Get the most recent songs of a user")
    async def lf_recent(self, ctx: EvelinaContext, *, member: Optional[Member] = None):
        if member is None:
            member = ctx.author
        username = await self.bot.db.fetchval("SELECT username FROM lastfm WHERE user_id = $1", member.id)
        if not username:
            return await ctx.lastfm_send(f"{'You don' if member == ctx.author else f'{member.mention} doesn'}'t have a **last.fm** account connected")
        if cache := await self.bot.cache.get(f"lf-recent-{member.id}"):
            tracks = cache
        else:
            recents = await self.lastfmhandler.get_tracks_recent(username)
            tracks = [f"[**{a['name']}**](https://last.fm/music/{a['name'].replace(' ', '+')}) by {a['artist']['#text']}" for a in list({v["name"]: v for v in recents["recenttracks"]["track"]}.values())]
            await self.bot.cache.set(f"lf-recent-{member.id}", tracks, 60 * 5)
        await ctx.paginate(tracks, title=f"{member.name}'s recent tracks", author={"name": ctx.author.name, "icon_url": ctx.author.avatar.url})

    @command(aliases=["np", "fm"], usage="nowplaying comminate", description="Get the latest song scrobbled on Last.Fm")
    async def nowplaying(self, ctx: EvelinaContext, *, member: Optional[Member] = None):
        if member is None:
            member = ctx.author
        try:
            check = await self.bot.db.fetchrow("SELECT username, reactions, embed, reply FROM lastfm WHERE user_id = $1", member.id)
            if not check:
                return await ctx.lastfm_send(f"{'You don' if member.id == ctx.author.id else f'{member.mention} doesn'}'t have a **Last.Fm** account connected")
            user = check[0]
            if check[2]:
                x = await self.bot.embed_build.convert(ctx, await self.lastfm_replacement(user, check[2]))
                kwargs = {"reference": ctx.message.to_reference(), "mention_author": False}
                try:
                    mes = await ctx.send(**x, **kwargs)
                except Exception:
                    mes = await ctx.send(**x)
            else:
                try:
                    a, u = await asyncio.gather(
                        asyncio.wait_for(self.lastfmhandler.get_tracks_recent(user, 1), timeout=15),
                        asyncio.wait_for(self.lastfmhandler.get_user_info(user), timeout=15)
                    )
                except asyncio.TimeoutError:
                    return await ctx.send_warning("Could not connect to LastFM servers. Please try again later")
                except Exception as e:
                    return await ctx.send_warning(f"An unexpected error occurred: {str(e)}")
                if not a["recenttracks"]["track"]:
                    return await ctx.send_warning("No recent tracks found")
                try:
                    first_track = a["recenttracks"]["track"][0]
                    album = first_track.get("album", {}).get("#text", "Unknown album")
                    track_name = first_track.get("name", "Unknown track")
                    artist_name = first_track.get("artist", {}).get("#text", "Unknown artist")
                    playcount = await self.lastfmhandler.get_track_playcount(user, first_track)
                    total_scrobbles = a["recenttracks"]["@attr"]["total"]
                    embed = (
                        Embed(color=colors.NEUTRAL)
                        .set_author(name=user, url=f"https://last.fm/user/{user}", icon_url=u["user"]["image"][2]["#text"])
                        .set_thumbnail(url=first_track["image"][2]["#text"])
                        .add_field(name="Track", value=f"[**{track_name}**](https://last.fm/music/{track_name.replace(' ', '+')})", inline=True)
                        .add_field(name="Artist", value=f"[**{artist_name}**](https://last.fm/artist/{artist_name.replace(' ', '+')})", inline=True)
                        .set_footer(text=f"Playcount: {playcount} ∙ Total Scrobbles: {total_scrobbles} {f'∙ Album: {album}' if album else ''}")
                    )
                    mes = await ctx.send(embed=embed)
                except KeyError as e:
                    return await ctx.send_warning(f"An error occurred while processing the track information: {str(e)}")
            if check[1] and ctx.guild.me.guild_permissions.add_reactions:
                reactions = json.loads(check[1])
                for r in reactions:
                    await mes.add_reaction(r)
                    await asyncio.sleep(0.5)
        except IndexError:
            return await ctx.send_warning("You haven't scrobbled any songs yet")
        except Exception as e:
            return await ctx.send_warning(f"An unexpected error occurred: {str(e)}")

    @lastfm.command(name="playing", description="See what song everyone is listening to in a server")
    async def lf_playing(self, ctx: EvelinaContext):
        async def fetch_member_info(member):
            if member.bot:
                return None
            user_data = await self.bot.db.fetchrow("SELECT username FROM lastfm WHERE user_id = $1", member.id)
            if not user_data:
                return None
            username = user_data["username"]
            try:
                recent_tracks = await self.lastfmhandler.get_tracks_recent(username, 1)
                if not recent_tracks["recenttracks"]["track"]:
                    return None
                current_track = recent_tracks["recenttracks"]["track"][0]
                if "@attr" not in current_track or "nowplaying" not in current_track["@attr"]:
                    return None
                track_name = current_track["name"]
                track_url = current_track["url"]
                artist_name = current_track["artist"]["#text"]
                artist_url = f"https://www.last.fm/music/{str(artist_name).replace(' ', '+')}"
                return (member, track_name, track_url, artist_name, artist_url)
            except Exception:
                return None
        async with ctx.typing():
            tasks = [fetch_member_info(member) for member in ctx.guild.members]
            results = await asyncio.gather(*tasks)
            members_listening = [result for result in results if result]
            if not members_listening:
                return await ctx.send_warning("No one is currently listening to a song on last.fm")
            paginated_content = [f"**{member[0].name}** is listening to [**{member[1]}**]({member[2]}) by [**{member[3]}**]({member[4]})" for member in members_listening]
            return await ctx.paginate(paginated_content, "Currently Listening on Last.fm", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @lastfm.command(name="crowns", aliases=["crown"], description="Get users with the most crowns")
    async def lf_crowns(self, ctx: EvelinaContext):
        crowns = await self.bot.db.fetch("SELECT user_id, COUNT(*) as crown_count FROM lastfm_crowns GROUP BY user_id ORDER BY crown_count DESC")
        if not crowns:
            return await ctx.send_warning("No crowns have been set yet")
        crown_list = [f"**{self.bot.get_user(crown['user_id']).name}** has `{crown['crown_count']} crowns`" for crown in crowns if self.bot.get_user(crown["user_id"])]
        return await ctx.paginate(crown_list, "Users with the most crowns", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Lastfm(bot))