import os
import random
import requests
import humanize

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

from discord import Embed, User, Member, Interaction, File
from discord.ext.commands import Cog, Author, command, group

from modules import config
from modules.styles import emojis, colors
from modules.misc.views import MarryView
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import nsfw_channel
from modules.converters import AbleToMarry

class Roleplay(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.marry_color = 0xFF819F

    async def get_count(self, author_id, target_id, type) -> str:
        data = await self.bot.db.fetchrow("SELECT count FROM roleplay WHERE user_id = $1 AND target_id = $2 AND type = $3", author_id, target_id, type)
        if data is None:
            await self.bot.db.execute("INSERT INTO roleplay (user_id, target_id, type, count) VALUES ($1, $2, $3, $4)", author_id, target_id, type, 1)
            return "1st"
        else:
            await self.bot.db.execute("UPDATE roleplay SET count = count + 1 WHERE user_id = $1 AND target_id = $2 AND type = $3", author_id, target_id, type)
            count = data["count"] + 1
            suffix = "th" if 11 <= count % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(count % 10, "th")
            return f"{count}{suffix}"

    @command(name="kiss", usage="kiss comminate", description="Kiss a member")
    async def kiss(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning(f"You can't kiss yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/kiss?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Aww how cute!* **{ctx.author.name}** kissed **{member.name}** for the **{await self.get_count(ctx.author.id, member.id, 'kiss')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @command(name="lick", aliases=["slurp"], usage="lick comminate", description="Lick a member")
    async def lick(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't lick yourself silly")
        res = ["You slurp that mf.", "Lick Lick!", "Slurp!"]
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/lick?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*{random.choice(res)}* **{ctx.author.name}** licked **{member.name}** for the **{await self.get_count(ctx.author.id, member.id, 'lick')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @command(name="fuck", usage="fuck comminate", brief="NSFW Channel", description="Fuck a member")
    @nsfw_channel()
    async def fuck(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't fuck yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/fuck?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Oh fuck!* **{ctx.author.name}** fucked **{member.name}** for the **{await self.get_count(ctx.author.id, member.id, 'fucked')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @command(name="anal", usage="fuck comminate", brief="NSFW Channel", description="Fuck a member anal")
    @nsfw_channel()
    async def anal(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't fuck yourself anal silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/anal?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Oh fuck!* **{ctx.author.name}** fucked **{member.name}** anal for the **{await self.get_count(ctx.author.id, member.id, 'anal')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @command(name="blowjob", usage="blowjob comminate", brief="NSFW Channel", description="Blowjob a member")
    @nsfw_channel()
    async def blowjob(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't blowjob yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/blowjob?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Oh fuck!* **{ctx.author.name}** gave **{member.name}** a blowjob for the **{await self.get_count(ctx.author.id, member.id, 'blowjob')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @command(name="cum", usage="cum comminate", brief="NSFW Channel", description="Cum on a member")
    @nsfw_channel()
    async def cum(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't cum on yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/cum?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Oh fuck!* **{ctx.author.name}** cum on **{member.name}** for the **{await self.get_count(ctx.author.id, member.id, 'cum')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @command(name="pussylick", usage="pussylick comminate", brief="NSFW Channel", description="Pussylick a member")
    @nsfw_channel()
    async def pussylick(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't pussylick yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/pussylick?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Oh fuck!* **{ctx.author.name}** pussylicked **{member.name}** for the **{await self.get_count(ctx.author.id, member.id, 'pussylick')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @group(name="threesome", brief="NSFW Channel", description="Threesome commands", invoke_without_command=True, case_insensitive=True)
    @nsfw_channel()
    async def threesome(self, ctx: EvelinaContext):
        return await ctx.create_pages()
    
    @threesome.command(name="fff", usage="threesome fff comminate visics", brief="NSFW Channel", description="Threesome with only girls")
    @nsfw_channel()
    async def threesome_fff(self, ctx: EvelinaContext, member: Member, partner: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't threesome with yourself silly")
        if partner == ctx.author:
            return await ctx.send_warning("You can't threesome with yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/threesome_fff?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Oh yeah!* **{ctx.author.name}** started a threesome with **{member.name}** & **{partner.name}**")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @threesome.command(name="ffm", usage="threesome ffm comminate visics", brief="NSFW Channel", description="Threesome with two girls & one boy")
    @nsfw_channel()
    async def threesome_ffm(self, ctx: EvelinaContext, member: Member, partner: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't threesome with yourself silly")
        if partner == ctx.author:
            return await ctx.send_warning("You can't threesome with yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/threesome_ffm?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Oh yeah!* **{ctx.author.name}** started a threesome with **{member.name}** & **{partner.name}**")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @threesome.command(name="fmm", usage="threesome fmm comminate visics", brief="NSFW Channel", description="Threesome with one girl & two boys")
    @nsfw_channel()
    async def threesome_fmm(self, ctx: EvelinaContext, member: Member, partner: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't threesomew with yourself silly")
        if partner == ctx.author:
            return await ctx.send_warning("You can't threesomew with yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/threesome_fmm?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Oh yeah!* **{ctx.author.name}** started a threesome with **{member.name}** & **{partner.name}**")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @command(name="pinch",usage="pinch comminate", description="Pinch a member")
    async def pinch(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't pinch yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/pinch?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"**{ctx.author.name}** pinches **{member.name}** for the **{await self.get_count(ctx.author.id, member.id, 'pinch')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @command(name="cuddle", usage="cuddle comminate", description="Cuddle a member")
    async def cuddle(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't cuddle yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/cuddle?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Aww how cute!* **{ctx.author.name}** cuddles **{member.name}** for the **{await self.get_count(ctx.author.id, member.id, 'cuddle')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)

    @command(name="hug", usage="hug comminate", description="Hug a member")
    async def hug(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't hug yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/hug?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Aww how cute!* **{ctx.author.name}** hugged **{member.name}** for the **{await self.get_count(ctx.author.id, member.id, 'hug')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)

    @command(name="pat", usage="pat comminate", description="Pat a member")
    async def pat(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't pat yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/pat?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"*Aww how cute!* **{ctx.author.name}** pats **{member.name}** for the **{await self.get_count(ctx.author.id, member.id, 'pat')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)

    @command(name="slap", usage="slap comminate", description="Slap a member")
    async def slap(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("You can't slap yourself silly")
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/slap?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"**{ctx.author.name}** slaps **{member.name}** for the **{await self.get_count(ctx.author.id, member.id, 'slap')}** time")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)

    @command(name="laugh", description="Start laughing")
    async def laugh(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/laugh?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"**{ctx.author.name}** laughs")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)

    @command(name="cry", description="Start crying")
    async def cry(self, ctx: EvelinaContext):
        result = await self.bot.session.get_json(f"https://api.evelina.bot/fun/cry?key=X3pZmLq82VnHYTd6Cr9eAw")
        embed = Embed(color=colors.NEUTRAL, description=f"**{ctx.author.name}** cries")
        embed.set_image(url=result["url"])
        return await ctx.reply(embed=embed)
    
    @command(name="stfu", usage="stfu comminate", description="Tell a member to shut up")
    async def stfu(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send_warning("Why do you wan't to tell yourself to shut up")
        return await ctx.send(f"{member.mention} shut the fuck up! {emojis.MADGE}")

    @command(name="ship", usage="ship comminate curet", description="Check the ship rate between you and a member")
    async def ship(self, ctx: EvelinaContext, member: Member, partner: Member = None):
        if partner and (partner == member):
            return await ctx.send_warning("You can't ship the same person twice")
        if (member == ctx.author and partner == ctx.author):
            return await ctx.send_warning("You can't ship yourself with yourself")
        if not partner:
            if member == ctx.author:
                return await ctx.send_warning("You can't ship yourself")
            else:
                partner = ctx.author
        ship_percentage = random.randrange(100)
        progress_bar = self.create_progress_bar(ship_percentage)
        image_path = self.create_ship_image(member.avatar.url if member.avatar else member.default_avatar.url, partner.avatar.url if partner.avatar else partner.default_avatar.url, ship_percentage)
        with open(image_path, "rb") as image_file:
            file = File(image_file, filename="ship.png")
            embed = Embed(color=0xFF819F, description=f"**{member.name}** 💞 **{partner.name}**\n**{ship_percentage}%** {progress_bar}")
            embed.set_image(url=f"attachment://ship.png")
            return await ctx.send(embed=embed, file=file)

    def create_progress_bar(self, percentage):
        filled_blocks = percentage // 8
        half_block = 1 if percentage % 8 >= 4 and filled_blocks > 0 else 0
        empty_blocks = 12 - filled_blocks - half_block
        if filled_blocks > 0:
            progress_bar = f"{emojis.FULLLEFT}"
        else:
            progress_bar = f"{emojis.EMPTYLEFT}"
        progress_bar += f"{emojis.FULL}" * filled_blocks  
        if half_block:
            progress_bar += f"{emojis.HALF}"
        progress_bar += f"{emojis.EMPTY}" * empty_blocks  
        progress_bar += f"{emojis.FULLRIGHT}" if filled_blocks + half_block == 13 else f"{emojis.EMPTYRIGHT}"
        return progress_bar

    def create_ship_image(self, member_avatar, partner_avatar, ship_percentage):
        avatar1 = Image.open(BytesIO(requests.get(str(member_avatar)).content)).convert("RGBA")
        avatar2 = Image.open(BytesIO(requests.get(str(partner_avatar)).content)).convert("RGBA")
        avatar_size = (125, 125)
        avatar1 = avatar1.resize(avatar_size, Image.LANCZOS)
        avatar2 = avatar2.resize(avatar_size, Image.LANCZOS)
        mask = Image.new("L", avatar_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, avatar_size[0], avatar_size[1]), fill=255)
        avatar1.putalpha(mask)
        avatar2.putalpha(mask)
        file_brokenheart = "data/images/brokenheart.png"
        file_heart = "data/images/heart.png"
        heart_path = file_brokenheart if ship_percentage < 50 else file_heart
        heart = Image.open(heart_path).convert("RGBA")
        heart = heart.resize((75, 75), Image.LANCZOS)
        background = Image.new("RGBA", (280, 125), (255, 255, 255, 0))
        background.paste(avatar1, (0, 0), avatar1)
        background.paste(avatar2, (156, 0), avatar2)
        heart_x = (background.width - heart.width) // 2
        heart_y = (background.height - heart.height) // 2
        background.paste(heart, (heart_x, heart_y), heart)
        output_path = "data/images/tmp/ship.png"
        background.save(output_path, format="PNG")
        return output_path

    @command(name="marry", usage="marry comminate", description="Marry a member")
    async def marry(self, ctx: EvelinaContext, *, member: AbleToMarry):
        embed = Embed(color=self.marry_color, description=f"{emojis.HEART} {ctx.author.mention} wants to marry you. Do you accept?")
        view = MarryView(ctx, member)
        view.message = await ctx.reply(content=member.mention, embed=embed, view=view)

    @command(name="marriage", usage="marriage comminate", description="View your marriage or from a given user")
    async def marriage(self, ctx: EvelinaContext, *, user: User = Author):
        check = await self.bot.db.fetchrow("SELECT * FROM marry WHERE $1 IN (author, soulmate)", user.id)
        if check is None:
            return await ctx.send_warning(f"{'You are' if user == ctx.author else f'{user.mention} is'} not **married**")
        partner_id = check[1] if check[1] != user.id else check[0]
        partner = self.bot.get_user(partner_id)
        if partner is None:
            try:
                partner = await self.bot.fetch_user(partner_id)
            except Exception:
                return await ctx.send_warning("Failed to retrieve the partner's information. Please try again later.")
        async with ctx.typing():
            img = Image.open("data/images/marry.jpeg")
            draw = ImageDraw.Draw(img)
            name_font = ImageFont.truetype("data/fonts/name.ttf", 130)
            sign_font = ImageFont.truetype("data/fonts/sign.ttf", 130)
            date_font = ImageFont.truetype("data/fonts/date.ttf", 100)
            today = datetime.fromtimestamp(int(check['time']))
            date = f"Got married on the {today.day}th of {today.strftime('%B')}, In the year {today.year}"
            draw.text((1500, 1470), user.name, fill="#355482", font=name_font)
            draw.text((2900, 1470), partner.name, fill="#355482", font=name_font)
            draw.text((2400, 1750), date, fill="#95918F", font=date_font, anchor="mm")
            draw.text((1500, 2180), user.name, fill="#355482", font=sign_font)
            draw.text((2850, 2180), partner.name, fill="#355482", font=sign_font)
            buffer = BytesIO()
            img.save(buffer, 'PNG')
            buffer.seek(0)
            file = File(buffer, 'marriage.png')
            embed = Embed(color=self.marry_color, description=f"{emojis.HEART} {ctx.author.mention}: {f'{user.mention} is' if user != ctx.author else 'You are'} currently married to <@!{check[1] if check[1] != user.id else check[0]}> since **{self.bot.misc.humanize_date(datetime.fromtimestamp(int(check['time'])))}**")
            embed.set_image(url=f"attachment://marriage.png")
            return await ctx.reply(embed=embed, file=file)

    @command(name="divorce", description="Divorce from your partner")
    async def divorce(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM marry WHERE $1 IN (author, soulmate)", ctx.author.id)
        if check is None:
            return await ctx.send_warning("You are not **married**")
        async def button1_callback(interaction: Interaction) -> None:
            user = await self.bot.fetch_user(check["author"] if check["author"] != interaction.user.id else check["soulmate"])
            await interaction.client.db.execute("DELETE FROM marry WHERE $1 IN (author, soulmate)", interaction.user.id)
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Divorced with partner")
            try:
                dm_embed = Embed(color=0xFF819F, description=f"{emojis.BROKENHEART} It seems like your partner **{interaction.user}** decided to divorce :(\n> Your relationship with them lasted **{humanize.precisedelta(datetime.fromtimestamp(int(check['time'])), format=f'%0.0f')}**")
                await user.send(embed=dm_embed)
            except:
                pass
            await interaction.response.edit_message(content=None, embed=embed, view=None)
        async def button2_callback(interaction: Interaction) -> None:
            embed = Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Divorce got canceled")
            await interaction.response.edit_message(content=None, embed=embed, view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention} are you sure you want to divorce?", button1_callback, button2_callback)

    @command(name="married", usage="married comminate curet", description="Create a marriage certificate")
    async def married(self, ctx: EvelinaContext, member: User, partner: User):
        if partner and (partner == member):
            return await ctx.send_warning("You can't marry the same person twice.")
        if member == ctx.author and partner == ctx.author:
            return await ctx.send_warning("You can't marry yourself with yourself.")
        if not partner:
            if member == ctx.author:
                return await ctx.send_warning("You can't marry yourself.")
            else:
                partner = ctx.author
        
        async with ctx.typing():
            img = Image.open("data/images/marry.jpeg")
            draw = ImageDraw.Draw(img)

            name_font = ImageFont.truetype("data/fonts/name.ttf", 130)
            sign_font = ImageFont.truetype("data/fonts/sign.ttf", 130)
            date_font = ImageFont.truetype("data/fonts/date.ttf", 100)
            
            today = datetime.now()
            date = f"Got married on the {today.day}th of {today.strftime('%B')}, In the year {today.year}"

            draw.text((1500, 1470), member.name, fill="#355482", font=name_font)
            draw.text((2900, 1470), partner.name, fill="#355482", font=name_font)

            draw.text((2400, 1750), date, fill="#95918F", font=date_font, anchor="mm")

            draw.text((1500, 2180), member.name, fill="#355482", font=sign_font)
            draw.text((2850, 2180), partner.name, fill="#355482", font=sign_font)

            buffer = BytesIO()
            img.save(buffer, 'PNG')
            buffer.seek(0)
            
            file = File(buffer, 'marriage.png')
            await ctx.reply(file=file)

    @command(name="edater", description="List all married users")
    async def edater(self, ctx: EvelinaContext):
        rows = await self.bot.db.fetch("SELECT * FROM marry ORDER BY time DESC")
        if not rows:
            return await ctx.send_warning("There are no married users")
        content = []
        for row in rows:
            author = self.bot.get_user(row["author"])
            soulmate = self.bot.get_user(row["soulmate"])
            time = f"<t:{row['time']}:R>"
            if author and soulmate:
                content.append(f"**{author}** & **{soulmate}** - {time}")
        if not content:
            return await ctx.send_warning("There are no married users")
        await ctx.paginate(content, "Married Users", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Roleplay(bot))