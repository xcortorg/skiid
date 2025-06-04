import re
from io import BytesIO
from secrets import token_urlsafe
from typing import Optional

from cashews import cache
from core.client.context import Context
from core.Mono import Mono
from discord import Embed, File, Message
from extensions.socials.models.instagram.user import StoryItem, User
from extensions.socials.reposters.base import Reposter


class InstagramStory(Reposter):
    def __init__(self, bot: Mono):
        super().__init__(
            bot,
            name="Instagram Story",
            regex=[
                r"\<?(https?://(?:www\.)?instagram\.com(?:/[^/]+)?/stories/(?P<username>[^/?#&]+)/(?P<post_id>[^/?#&]+))\>?"
            ],
        )

    @cache(ttl="1h", prefix="instagram:story")
    async def fetch(self, url: str) -> Optional[StoryItem]:
        url, username, story_id = re.match(self.regex[0], url).groups()  # type: ignore
        user = await User.fetch(username)
        if not user:
            return

        stories = await User.stories(user.id)
        for story in stories:
            if story.id == int(story_id):
                return story

    async def dispatch(
        self,
        ctx: Context,
        data: StoryItem,
        buffer: BytesIO,
    ) -> Optional[Message]:
        embed = Embed(timestamp=data.created_at)
        embed.set_author(
            url=data.user.url,
            name=data.user.full_name or data.user.username,
            icon_url=data.user.avatar_url,
        )
        embed.set_footer(
            text="Story posted",
            icon_url="https://i.imgur.com/U31ZVlK.png",
        )

        return await ctx.send(
            embed=embed if ctx.settings.reposter_embed else None,
            file=File(
                buffer,
                filename=f"{self.name}{token_urlsafe(6)}.{data.ext}",
            ),
            no_reference=ctx.settings.reposter_delete,
        )
