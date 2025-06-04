import asyncio

import discord

from grief.core.utils.chat_formatting import escape
from grief.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta
from .exceptions import *
from .fmmixin import FMMixin

command_fm = FMMixin.command_fm
command_fm_server = FMMixin.command_fm_server


class RecentMixin(MixinMeta):
    """Recent Commands"""

    @command_fm.command(name="recent", aliases=["recents", "re"], usage="[amount]")
    async def command_recent(self, ctx, size: int = 15):
        """Tracks you have recently listened to."""
        conf = await self.config.user(ctx.author).all()
        name = conf["lastfm_username"]
        self.check_if_logged_in(conf)
        async with ctx.typing():
            data = await self.api_request(
                ctx, {"user": name, "method": "user.getrecenttracks", "limit": size}
            )
            user_attr = data["recenttracks"]["@attr"]
            tracks = data["recenttracks"]["track"]

            if not tracks or not isinstance(tracks, list):
                return await ctx.send("You have not listened to anything yet!")

            rows = []
            for i, track in enumerate(tracks):
                if i >= size:
                    break
                name = escape(track["name"], formatting=True)
                track_url = track["url"]
                artist_name = escape(track["artist"]["#text"], formatting=True)
                if track.get("@attr") and track["@attr"].get("nowplaying"):
                    extra = ":musical_note:"
                else:
                    extra = f"(<t:{track['date']['uts']}:R>)"
                rows.append(f"[**{artist_name}** — **{name}**]({track_url}) {extra}")

            image_url = tracks[0]["image"][-1]["#text"]

            content = discord.Embed(color=await self.bot.get_embed_color(ctx.channel))
            content.set_thumbnail(url=image_url)
            content.set_footer(text=f"Total scrobbles: {user_attr['total']}")
            content.set_author(
                name=f"{user_attr['user']} — Recent tracks",
                icon_url=ctx.message.author.display_avatar.url,
            )

            pages = await self.create_pages(content, rows)
            if len(pages) > 1:
                await menu(ctx, pages[:15], DEFAULT_CONTROLS)
            else:
                await ctx.send(embed=pages[0])
