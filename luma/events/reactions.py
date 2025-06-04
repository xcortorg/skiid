import asyncio
import contextlib
from collections import defaultdict
from typing import Optional

import discord
from discord.ext import commands
from managers.bot import Luma


class Reactions(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)

    @commands.Cog.listener("on_raw_reaction_remove")
    async def on_starboard_remove(
        self: "Reactions", payload: discord.RawReactionActionEvent
    ):
        if panel_message_id := await self.bot.db.fetchval(
            """
      SELECT panel_message_id FROM starboard_message 
      WHERE guild_id = $1 AND channel_id = $2 
      AND message_id = $3 
      """,
            payload.guild_id,
            payload.channel_id,
            payload.message_id,
        ):
            if res := await self.bot.db.fetchrow(
                "SELECT * FROM starboard WHERE guild_id = $1", payload.guild_id
            ):
                if channel := self.bot.get_channel(res["channel_id"]):
                    if res["emoji"] == str(payload.emoji):
                        message = await self.bot.get_channel(
                            payload.channel_id
                        ).fetch_message(payload.message_id)
                        reaction = next(
                            r
                            for r in message.reactions
                            if str(r.emoji) == str(payload.emoji)
                        )
                        m = await channel.fetch_message(panel_message_id)
                        return await m.edit(
                            content=f"**#{reaction.count}** {payload.emoji}"
                        )

    @commands.Cog.listener("on_raw_reaction_add")
    async def on_starboard(self: "Reactions", payload: discord.RawReactionActionEvent):
        if result := await self.bot.db.fetchrow(
            "SELECT * FROM starboard WHERE guild_id = $1", payload.guild_id
        ):
            if channel := self.bot.get_channel(result.channel_id):
                if emoji := result.emoji:
                    if count := result.count:
                        if str(payload.emoji) == emoji:
                            if not await self.bot.db.fetchrow(
                                "SELECT * FROM starboard_message WHERE panel_message_id = $1",
                                payload.message_id,
                            ):
                                async with self.locks[
                                    f"{payload.emoji}-{payload.message_id}"
                                ]:
                                    message = await self.bot.get_channel(
                                        payload.channel_id
                                    ).fetch_message(payload.message_id)
                                    if (
                                        message.content != ""
                                        or len(message.attachments) > 0
                                    ):
                                        reaction = next(
                                            r
                                            for r in message.reactions
                                            if str(r.emoji) == str(payload.emoji)
                                        )
                                        if reaction.count >= count:
                                            author = self.bot.get_guild(
                                                payload.guild_id
                                            ).get_member(payload.message_author_id)
                                            content = f"**#{reaction.count}** {reaction.emoji}"
                                            file: Optional[discord.File] = None

                                            if re := await self.bot.db.fetchrow(
                                                """
                          SELECT * FROM starboard_message WHERE
                          guild_id = $1 AND channel_id = $2
                          AND message_id = $3 
                          """,
                                                payload.guild_id,
                                                payload.channel_id,
                                                payload.message_id,
                                            ):
                                                with contextlib.suppress(
                                                    discord.NotFound
                                                ):
                                                    m = await channel.fetch_message(
                                                        re.panel_message_id
                                                    )
                                                    return await m.edit(content=content)

                                            desc = message.content

                                            if ref := getattr(
                                                message.reference, "resolved", None
                                            ):
                                                desc += f"\nReplying to [{ref.author}]({ref.jump_url})"

                                            embed = discord.Embed(
                                                color=self.bot.color,
                                                description=desc,
                                                title=f"#{message.channel}",
                                                url=message.jump_url,
                                                timestamp=message.created_at,
                                            )

                                            if len(message.attachments) > 0:
                                                attachment = message.attachments[0]
                                                if attachment.filename.endswith(
                                                    tuple(["png", "gif", "jpeg", "jpg"])
                                                ):
                                                    embed.set_image(url=attachment.url)
                                                elif attachment.filename.endswith(
                                                    tuple(["mp4", "mov"])
                                                ):
                                                    file = discord.File(
                                                        await self.bot.bytes(
                                                            attachment.url
                                                        ),
                                                        filename=attachment.filename,
                                                    )

                                            embed.set_author(
                                                name=str(author),
                                                icon_url=author.display_avatar.url,
                                            )

                                            mes = await channel.send(
                                                content=content, embed=embed, file=file
                                            )

                                            await self.bot.db.execute(
                                                """
                          INSERT INTO starboard_message VALUES ($1,$2,$3,$4)
                          ON CONFLICT (guild_id, channel_id, message_id)
                          DO UPDATE SET panel_message_id = $4   
                          """,
                                                payload.guild_id,
                                                payload.channel_id,
                                                payload.message_id,
                                                mes.id,
                                            )


async def setup(bot: Luma):
    return await bot.add_cog(Reactions(bot))
