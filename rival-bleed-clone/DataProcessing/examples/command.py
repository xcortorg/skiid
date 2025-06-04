from discord.ext.commands import Context, Cog, command
from discord import Embed, Client
from discord.utils import chunk_list
from DataProcessing import ServiceManager
from DataProcessing.models.authentication import Credentials


class Information(Cog):
    def __init__(self: "Information", bot: Client):
        self.bot = bot
        self.bot.services = ServiceManager(self.bot.redis)

    @command(name="google", description="get a google search result")
    async def google(self: "Information", ctx: Context, *, query: str):
        safe = True if not ctx.channel.is_nsfw() else False
        try:
            results = await self.bot.services.bing.search(query, safe)
        except Exception as e:
            if ctx.author.id == 352190010998390796:
                raise e
            return await ctx.fail(
                f"**{query[:20]}** has **no results or google is currently ratelimiting us**",
            )
        embeds_ = []
        page_start = 0
        res = chunk_list(results.results, 3)
        pages = len(res)
        if results.knowledge_panel:
            if results.knowledge_panel.title:
                try:
                    embed = Embed(
                        color=self.bot.color,
                        title=results.knowledge_panel.title,
                        url=results.knowledge_panel.url or "https://wock.bot",
                        description=results.knowledge_panel.description,
                    )
                    embed.set_footer(
                        text=f"Page 1/{pages+1} of Google Search {'(Safe Mode)' if safe else ''} {'(Cached)' if results.cached else ''}",
                        icon_url="https://cdn4.iconfinder.com/data/icons/logos-brands-7/512/google_logo-google_icongoogle-512.png",
                    )
                    for key, value in results.knowledge_panel.additional_info.items():
                        embed.add_field(
                            name=key.title(), value=str(value), inline=False
                        )
                    embeds_.append(embed)
                    page_start += 1
                except Exception:
                    pass
        embeds = [
            Embed(
                title="Search Results",
                description="\n\n".join(
                    f"**[{result.title[:255]}](https://{result.domain})**\n{result.description}"
                    for result in page
                ),
                color=self.bot.color,
            )
            .set_footer(
                text=f"Page {i+page_start}/{pages+page_start} of Google Search {'(Safe Mode)' if safe else ''} {'(Cached)' if results.cached else ''}",
                icon_url="https://cdn4.iconfinder.com/data/icons/logos-brands-7/512/google_logo-google_icongoogle-512.png",
            )
            .set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
            for i, page in enumerate(res, start=1)
        ]
        embeds_.extend(embeds)
        return await ctx.paginate(
            embeds_,
        )

    @command(name="image", description="get google image results")
    async def image(self, ctx: Context, *, query: str):
        if ctx.channel.is_nsfw():
            safe = False

        else:
            safe = True

        try:
            results = await self.bot.services.bing.image_search(query, safe)

        except Exception as e:
            return await ctx.fail(f"no results for **{query}**")

        embeds = [
            Embed(
                title=f"results for {query}",
                description=f"[{result.content} - ({result.source})]({result.url})",
                color=self.bot.color,
            )
            .set_image(url=result.thumbnail)
            .set_footer(text=f"Page {i}/{len(results.results)} of Google Images")
            for i, result in enumerate(results.results, start=1)
        ]

        return await ctx.paginate(embeds)


async def setup(bot: Client):
    return await bot.add_cog(Information(bot))
