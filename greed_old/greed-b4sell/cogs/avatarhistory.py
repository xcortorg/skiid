from discord.ext.commands import Cog, command, group, CommandError
from discord import User, Member, Guild, Embed, File, Client, utils
from aiohttp import ClientSession
from typing import Union, Optional, List
from tool.important.subclasses.context import Context
from tool.worker import offloaded
from io import BytesIO


@offloaded
def collage_(_images: List[bytes]) -> List[bytes]:
    from math import sqrt
    from PIL import Image
    from io import BytesIO

    def _collage_paste(image: Image, x: int, y: int, background: Image):
        background.paste(
            image,
            (
                x * 256,
                y * 256,
            ),
        )

    if not _images:
        return None

    def open_image(image: bytes):
        return Image.open(BytesIO(image)).convert("RGBA").resize((300, 300))
    
    images = [open_image(i) for i in _images]
    rows = int(sqrt(len(images)))
    columns = (len(images) + rows - 1) // rows

    background = Image.new(
        "RGBA",
        (
            columns * 256,
            rows * 256,
        ),
    )
    for i, image in enumerate(images):
        _collage_paste(image, i % columns, i // columns, background)

    buffer = BytesIO()
    background.save(
        buffer,
        format="png",
    )
    buffer.seek(0)

    background.close()
    for image in images:
        image.close()
    return buffer.getvalue()

class AvatarHistory(Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    async def get_data(self, user: User) -> tuple:
        async with ClientSession() as session:
            async with session.get(user.display_avatar.url) as response:
                data = await response.read()
                content_type = response.headers.get('Content-Type')
                if not content_type:
                    content_type = 'image/png'  # default fallback
        return data, content_type

    # @Cog.listener("on_user_update")
    # async def on_avatar_change(self, before: User, after: User):
    #     guild = self.bot.get_guild(1301617147964821524)
    #     if not guild or not guild.get_member(after.id):
    #         return
    #     if before.display_avatar == after.display_avatar:
    #         return
    #     avatar, content_type = await self.get_data(after)
    #     await self.bot.db.execute(
    #         """INSERT INTO avatars (user_id, content_type, avatar, id) VALUES($1, $2, $3, $4)""",
    #         after.id, content_type, avatar, after.display_avatar.key
    #     )


    @command(name = "avatarhistory", aliases = ["avatars", "avh"], brief = "view past avatar changes with a user", example = ",avh @aiohttp")
    async def avatarhistory(self, ctx: Context, *, user: Optional[Union[User, Member]] = None):
        is_booster = await self.bot.db.fetchrow(
            "SELECT 1 FROM boosters WHERE user_id = $1", ctx.author.id
        )

        if not is_booster:
            await ctx.fail(
                "You are not boosting [/greedbot](https://discord.gg/greedbot). Boost this server to use this command."
            )
            return
        user = user or ctx.author
        rows = await self.bot.db.fetch("""SELECT id, avatar, content_type, ts FROM avatars WHERE user_id = $1 ORDER BY ts DESC""", user.id)
        if not rows:
            raise CommandError(f"no avatars have been **saved** for {user.mention}")
        url = f"https://cdn.greed.rocks/avatars/{user.id}"
        title = f"here's a list of {user.name}'s avatar history"
        embed = Embed(title=title, url=url).set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        collage = await collage_([row.avatar for row in rows])
        file = File(fp = BytesIO(collage), filename = "collage.png")
        embed.set_image(url = "attachment://collage.png")
        return await ctx.send(embed=embed, file = file)

    @command(name = "clearavatars", aliases = ["clavs", "clavh", "clearavh"], brief = "clear your avatar history")
    async def clearavatars(self, ctx: Context):
        await self.bot.db.execute("""DELETE FROM avatars WHERE user_id = $1""", ctx.author.id)
        return await ctx.success("cleared your **avatar history**")

async def setup(bot: Client):
    await bot.add_cog(AvatarHistory(bot))
