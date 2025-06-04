import logging
import random
from random import randint
from typing import Optional

import discord

from grief.core import Config, commands
from grief.core.bot import Grief

log = logging.getLogger("grief.roleplay")


class Roleplay(commands.Cog):
    """
    Perform different actions, like cuddle, poke etc.
    """

    def __init__(self, bot: Grief):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=8423644625413, force_registration=True
        )
        default_member = {
            "cuddle_s": 0,
            "poke_s": 0,
            "kiss_s": 0,
            "hug_s": 0,
            "slap_s": 0,
            "pat_s": 0,
            "tickle_s": 0,
            "lick_s": 0,
            "spank_s": 0,
            "feed_s": 0,
            "punch_s": 0,
            "highfive_s": 0,
            "kill_s": 0,
            "bite_s": 0,
            "dance": 0,
            "yeet_s": 0,
            "nut_s": 0,
            "fuck_s": 0,
        }
        default_target = {
            "cuddle_r": 0,
            "poke_r": 0,
            "kiss_r": 0,
            "hug_r": 0,
            "slap_r": 0,
            "pat_r": 0,
            "tickle_r": 0,
            "lick_r": 0,
            "spank_r": 0,
            "feed_r": 0,
            "punch_r": 0,
            "highfive_r": 0,
            "kill_r": 0,
            "bite_r": 0,
            "yeet_r": 0,
            "nut_r": 0,
            "fuck_r": 0,
        }
        self.config.register_user(**default_member)
        self.config.init_custom("Target", 2)
        self.config.register_custom("Target", **default_target)
        self.cache = {}

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command()
    async def cuddle(self, ctx: commands.Context, user: discord.Member):
        """
        Cuddles a user.
        """

        images = (
            f"https://cdn.slit.sh/roleplay/cuddle/cuddle{random.randint(1, 20)}.gif"
        )

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just cuddled {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).cuddle_r()
        used = await self.config.user(ctx.author).fuck_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total cuddles: {used + 1} | {ctx.author.name} has cuddled {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).cuddle_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).cuddle_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command()
    async def poke(self, ctx: commands.Context, user: discord.Member):
        """
        Pokes a user.
        """

        images = f"https://cdn.slit.sh/roleplay/poke/poke{random.randint(1, 15)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just poked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).poke_r()
        used = await self.config.user(ctx.author).poke_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total pokes: {used + 1} | {ctx.author.name} has poked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).poke_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).poke_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command()
    async def kiss(self, ctx: commands.Context, user: discord.Member):
        """
        Kiss a user.
        """

        images = f"https://cdn.slit.sh/roleplay/kiss/kiss{random.randint(1, 20)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just kissed {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).kiss_r()
        used = await self.config.user(ctx.author).kiss_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total kisses: {used + 1} | {ctx.author.name} has kissed {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).kiss_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).kiss_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command()
    async def hug(self, ctx: commands.Context, user: discord.Member):
        """
        Hugs a user.
        """

        images = f"https://cdn.slit.sh/roleplay/hug/hug{random.randint(1, 19)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just hugged {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).hug_r()
        used = await self.config.user(ctx.author).hug_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total hugs: {used + 1} | {ctx.author.name} has hugged {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).hug_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).hug_r.set(target + 1)

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command()
    async def pat(self, ctx: commands.Context, user: discord.Member):
        """
        Pats a user.
        """

        images = f"https://cdn.slit.sh/roleplay/pat/pat{random.randint(1, 19)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just patted {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).hug_r()
        used = await self.config.user(ctx.author).pat_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total pats: {used + 1} | {ctx.author.name} has patted {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).pat_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).pat_r.set(target + 1)

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command()
    async def tickle(self, ctx: commands.Context, user: discord.Member):
        """
        Tickles a user.
        """

        images = (
            f"https://cdn.slit.sh/roleplay/tickle/tickle{random.randint(1, 18)}.gif"
        )

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just tickled {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).hug_r()
        used = await self.config.user(ctx.author).tickle_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total tickles: {used + 1} | {ctx.author.name} has tickled {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).tickle_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).tickle_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command()
    async def lick(self, ctx: commands.Context, user: discord.Member):
        """
        Licks a user.
        """

        images = f"https://cdn.slit.sh/roleplay/lick/lick{random.randint(1, 16)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just licked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).lick_r()
        used = await self.config.user(ctx.author).lick_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total licks: {used + 1} | {ctx.author.name} has licked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).lick_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).lick_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command()
    async def slap(self, ctx: commands.Context, user: discord.Member):
        """
        Slaps a user.
        """

        images = f"https://cdn.slit.sh/roleplay/slap/slap{random.randint(1, 15)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just slapped {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).slap_r()
        used = await self.config.user(ctx.author).lick_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total slaps: {used + 1} | {ctx.author.name} has slapped {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).slap_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).slap_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="spank")
    async def spank(self, ctx: commands.Context, user: discord.Member):
        """
        Spanks a user.
        """

        images = f"https://cdn.slit.sh/roleplay/spank/spank{random.randint(1, 13)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just spanked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).spank_r()
        used = await self.config.user(ctx.author).spank_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total spanks: {used + 1} | {ctx.author.name} has spanked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).spank_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).spank_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="feed")
    async def feed(self, ctx: commands.Context, user: discord.Member):
        """
        Feeds a user.
        """

        images = f"https://cdn.slit.sh/roleplay/feed/feed{random.randint(1, 11)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** feeds {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).feed_r()
        used = await self.config.user(ctx.author).feed_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total feeds: {used + 1} | {ctx.author.name} has feeded {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).feed_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).feed_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="punch")
    async def punch(self, ctx: commands.Context, user: discord.Member):
        """
        Punch a user.
        """

        images = f"https://cdn.slit.sh/roleplay/punch/punch{random.randint(1, 19)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** punches {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).feed_r()
        used = await self.config.user(ctx.author).punch_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total punches: {used + 1} | {ctx.author.name} has punched {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).punch_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).punch_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="highfive")
    async def highfive(self, ctx: commands.Context, user: discord.Member):
        """
        Highfive a user.
        """

        images = (
            f"https://cdn.slit.sh/roleplay/highfive/highfive{random.randint(1, 10)}.gif"
        )

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** highfives {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).highfive_r()
        used = await self.config.user(ctx.author).highfive_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total highfives: {used + 1} | {ctx.author.name} has highfived {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).highfive_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).highfive_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="kill")
    async def kill(self, ctx: commands.Context, user: discord.Member):
        """
        Kill a user.
        """

        images = f"https://cdn.slit.sh/roleplay/kill/kill{random.randint(1, 13)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** kills {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).kill_r()
        used = await self.config.user(ctx.author).kill_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total kills: {used + 1} | {ctx.author.name} has killed {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).kill_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).kill_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="bite")
    async def bite(self, ctx: commands.Context, user: discord.Member):
        """
        Bite a user.
        """

        images = f"https://cdn.slit.sh/roleplay/bite/bite{random.randint(1, 31)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** bites {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).bite_r()
        used = await self.config.user(ctx.author).bite_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total bites: {used + 1} | {ctx.author.name} has bit {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).bite_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).bite_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="yeet")
    async def yeet(self, ctx: commands.Context, user: discord.Member):
        """
        Yeet a user.
        """

        images = f"https://cdn.slit.sh/roleplay/yeet/yeet{random.randint(1, 7)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** yeeted {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).yeet_r()
        used = await self.config.user(ctx.author).yeet_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total yeets: {used + 1} | {ctx.author.name} has yeeted {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).yeet_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).yeet_r.set(
            target + 1
        )

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="nutkick", aliases=["kicknuts"])
    async def kicknuts(self, ctx: commands.Context, user: discord.Member):
        """
        Kick a user in the balls.
        """

        images = (
            f"https://cdn.slit.sh/roleplay/nutkick/nutkick{random.randint(1, 8)}.gif"
        )

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just kicked nuts of {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).nut_r()
        used = await self.config.user(ctx.author).nut_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total nutkicks: {used + 1} | {ctx.author.name} has nutkicked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).nut_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).nut_r.set(target + 1)

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command()
    async def fuck(self, ctx: commands.Context, user: discord.Member):
        """
        Fuck a user.
        """

        images = f"https://cdn.slit.sh/roleplay/fuck/fuck{random.randint(1, 11)}.gif"

        embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            description=f"**{ctx.author.mention}** just fucked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=images)
        target = await self.config.custom("Target", ctx.author.id, user.id).fuck_r()
        used = await self.config.user(ctx.author).fuck_s()
        embed.set_footer(
            text=f"{ctx.author.name}'s total fucks: {used + 1} | {ctx.author.name} has fucked {user.name} {target + 1} times"
        )
        await send_embed(self, ctx, embed, user)
        await self.config.user(ctx.author).fuck_s.set(used + 1)
        await self.config.custom("Target", ctx.author.id, user.id).fuck_r.set(
            target + 1
        )


async def send_embed(
    self,
    ctx: commands.Context,
    embed: discord.Embed,
    user: Optional[discord.Member] = None,
):
    await ctx.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(Roleplay(bot))
