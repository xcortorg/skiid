import io
import re
from typing import Optional

import discord
from discord.ext import commands
from managers.bot import Luma


class Messages(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot
        self.cooldown = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.channel
        )

    def rate_limit(self: "Messages", message: discord.Message) -> Optional[int]:
        bucket = self.cooldown.get_bucket(message)
        return bucket.update_rate_limit()

    @commands.Cog.listener("on_message")
    async def on_autoresponder(self: "Messages", message: discord.Message):
        if message.author.bot and not message.guild:
            return

        for check in await self.bot.db.fetch(
            "SELECT * FROM autoresponder WHERE guild_id = $1", message.guild.id
        ):
            if str(check["trigger"]).lower() == message.content.lower():
                ctx = await self.bot.get_context(message)
                x = await self.bot.embed.convert(ctx.author, check["response"])
                await ctx.send(**x)

    @commands.Cog.listener("on_message_delete")
    async def on_snipe(self: "Messages", message: discord.Message):
        if message.author.bot:
            return

        snipes = self.bot.cache.get(f"{message.channel.id}-snipe") or []
        snipes.append(message)
        return await self.bot.cache.add(f"{message.channel.id}-snipe", snipes, 3600)

    @commands.Cog.listener("on_message")
    async def tiktok_repost(self: "Messages", message: discord.Message):
        if (
            message.guild
            and not message.author.bot
            and message.content.startswith("luma")
        ):
            if re.search(
                r"\bhttps?:\/\/(?:m|www|vm)\.tiktok\.com\/\S*?\b(?:(?:(?:usr|v|embed|user|video)\/|\?shareId=|\&item_id=)(\d+)|(?=\w{7})(\w*?[A-Z\d]\w*)(?=\s|\/$))\b",
                message.content[len("luma") + 1 :],
            ):
                cd = self.rate_limit(message)
                if not cd:
                    url = message.content[len("luma") + 1 :]

                    async with message.channel.typing():
                        x = await self.bot.session.get(
                            "https://tikwm.com/api/", params={"url": url}
                        )

                        if x["data"]["images"]:
                            embeds = []
                            for img in x["data"]["images"]:
                                embed = (
                                    discord.Embed(color=self.bot.color)
                                    .set_author(
                                        name=f"@{x['data']['author']['unique_id']}",
                                        icon_url=x["data"]["author"]["avatar"],
                                        url=url,
                                    )
                                    .set_image(url=img)
                                    .set_footer(
                                        text=f"❤️ {x['data']['digg_count']:,} 💬 {x['data']['comment_count']:,}"
                                    )
                                )
                            embeds.append(embed)
                            ctx = await self.bot.get_context(message)
                            return await ctx.paginator(embeds)
                        else:
                            video = x.content["data"]["play"]
                            videobytes = await self.bot.session.get(video)
                            file = discord.File(
                                fp=io.BytesIO(videobytes), filename="lumatiktok.mp4"
                            )

                            embed = (
                                discord.Embed(
                                    color=self.bot.color,
                                    description=f"[{x['data']['title']}]({url})",
                                )
                                .set_author(
                                    name=f"@{x['data']['author']['unique_id']}",
                                    icon_url=x["data"]["author"]["avatar"],
                                )
                                .set_footer(
                                    text=f"❤️ {x['data']['digg_count']:,} 💬 {x['data']['comment_count']:,} 👀 {x['data']['play_count']:,} | {message.author.name}"
                                )
                            )

                            await message.channel.send(embed=embed, file=file)
                            try:
                                await message.delete()
                            except:
                                pass


async def setup(bot: Luma):
    return await bot.add_cog(Messages(bot))
