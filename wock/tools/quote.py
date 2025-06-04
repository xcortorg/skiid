import textwrap
from asyncio import Lock
from asyncio import to_thread as thread
from collections import defaultdict
from io import BytesIO
from typing import Optional

from discord import File, Message  # type: ignore # type: ignore # type: ignore
from discord.ext.commands import Cog, Context  # type: ignore
from PILL import Image, ImageDraw, ImageFont  # type: ignore


class Quotes(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.locks = defaultdict(Lock)

    async def get_caption(self, ctx: Context, message: Optional[Message] = None):
        if message is None:
            msg = ctx.message.reference
            if msg is None:
                return await ctx.fail("no **message** or **reference** provided")
            id = msg.message_id
            message = await self.bot.fetch_message(ctx.channel, id)
        image = BytesIO(await message.author.display_avatar.read())
        image.seek(0)
        if message.content.replace("\n", "").isascii():
            para = textwrap.wrap(message.clean_content, width=26)
        else:
            para = textwrap.wrap(message.clean_content, width=13)

        def do_caption(para, image, message):
            icon = Image.open(image)
            haikei = Image.open("/root/assets/grad.jpeg")
            black = Image.open("/root/assets/black.jpeg")
            w, h = (680, 370)
            w1, h1 = icon.size  # type: ignore # type: ignore
            haikei = haikei.resize((w, h))
            black = black.resize((w, h))
            icon = icon.resize((h, h))
            new = Image.new(mode="RGBA", size=(w, h))
            icon = icon.convert("RGBA")
            black = black.convert("RGBA")
            haikei = haikei.convert("L")
            new = Image.new(mode="L", size=(w, h))
            icon = icon.convert("L")
            black = black.convert("L")
            icon = icon.crop((40, 0, 680, 370))
            new.paste(icon)
            sa = Image.composite(new, black, haikei)
            draw = ImageDraw.Draw(sa)
            fnt = ImageFont.truetype("/root/assets/Arial.ttf", 28)
            w2, h2 = draw.textsize("a", font=fnt)
            i = (int(len(para) / 2) * w2) + len(para) * 5
            current_h, pad = 120 - i, 0
            for line in para:
                if message.content.replace("\n", "").isascii():
                    w3, h3 = draw.textsize(
                        line.ljust(int(len(line) / 2 + 11), " "), font=fnt
                    )
                    draw.text(
                        (11 * (w - w3) / 13 + 10, current_h + h2),
                        line.ljust(int(len(line) / 2 + 11), " "),
                        font=fnt,
                        fill="#FFF",
                    )
                else:
                    w3, h3 = draw.textsize(
                        line.ljust(int(len(line) / 2 + 5), "　"), font=fnt
                    )
                    draw.text(
                        (11 * (w - w3) / 13 + 10, current_h + h2),
                        line.ljust(int(len(line) / 2 + 5), "　"),
                        font=fnt,
                        fill="#FFF",
                    )
                current_h += h3 + pad
            dr = ImageDraw.Draw(sa)
            font = ImageFont.truetype("/root/assets/Arial.ttf", 15)
            authorw, authorh = dr.textsize(f"-{str(message.author)}", font=font)  # type: ignore
            output = BytesIO()
            dr.text(
                (480 - int(authorw / 2), current_h + h2 + 10),
                f"-{str(message.author)}",
                font=font,
                fill="#FFF",
            )
            sa.save(output, format="PNG")
            output.seek(0)
            return output

        output = await thread(do_caption, para, image, message)
        file = File(fp=output, filename="quote.png")
        return await ctx.send(file=file)
