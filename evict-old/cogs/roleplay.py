import asyncio
import datetime
import random

import discord
from bot.bot import Evict
from bot.helpers import EvictContext
from bot.managers.emojis import Colors, Emojis
from discord.ext import commands
from discord.ui import Button, View
from patches.fun import DiaryModal, Joint, MarryView
from patches.permissions import Permissions


class roleplay(commands.Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.joint_emoji = "🍃"
        self.smoke = "🌬️"
        self.joint_color = 0x57D657
        self.book = "📖"

    async def joint_send(self, ctx: EvictContext, message: str) -> discord.Message:
        embed = discord.Embed(
            color=self.joint_color,
            description=f"{self.joint_emoji} {ctx.author.mention}: {message}",
        )
        return await ctx.reply(embed=embed)

    async def smoke_send(self, ctx: EvictContext, message: str) -> discord.Message:
        embed = discord.Embed(
            color=Colors.color,
            description=f"{self.smoke} {ctx.author.mention}: {message}",
        )
        return await ctx.reply(embed=embed)

    @commands.group(
        name="joint", invoke_without_command=True, description="have fun with a joint"
    )
    async def jointcmd(self, ctx):
        return await ctx.create_pages()

    @jointcmd.command(
        name="toggle", description="toggle the server joint", brief="manage guild"
    )
    @Permissions.has_permission(manage_guild=True)
    async def joint_toggle(self, ctx: EvictContext):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM joint WHERE guild_id = {}".format(ctx.guild.id)
        )
        if not check:
            await self.bot.db.execute(
                "INSERT INTO joint VALUES ($1,$2,$3)", ctx.guild.id, 0, ctx.author.id
            )
            return await self.joint_send(ctx, "The joint is yours")
        await self.bot.db.execute("DELETE FROM joint WHERE guild_id = $1", ctx.guild.id)
        return await ctx.reply(
            embed=discord.Embed(
                color=Colors.color,
                description=f"{self.smoke} {ctx.author.mention}: Got rid of the server's joint",
            )
        )

    @jointcmd.command(
        name="stats", description="check joint stats", aliases=["status", "settings"]
    )
    @Joint.check_joint()
    async def joint_stats(self, ctx: EvictContext):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM joint WHERE guild_id = $1", ctx.guild.id
        )
        embed = discord.Embed(
            color=self.joint_color,
            description=f"{self.smoke} hits: **{check['hits']}**\n{self.joint_emoji} Holder: <@{check['holder']}>",
        )
        embed.set_author(icon_url=ctx.guild.icon, name=f"{ctx.guild.name}'s joint")
        return await ctx.reply(embed=embed)

    @jointcmd.command(name="hit", description="hit the server joint")
    @Joint.check_joint()
    @Joint.joint_owner()
    async def joint_hit(self, ctx: EvictContext):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM joint WHERE guild_id = $1", ctx.guild.id
        )
        newhits = int(check["hits"] + 1)
        mes = await self.joint_send(ctx, "Hitting the **joint**.....")
        await asyncio.sleep(2)
        embed = discord.Embed(
            color=Colors.color,
            description=f"{self.smoke} {ctx.author.mention}: You just hit the **joint**. This server has a total of **{newhits}** hits!",
        )
        await mes.edit(embed=embed)
        await self.bot.db.execute(
            "UPDATE joint SET hits = $1 WHERE guild_id = $2", newhits, ctx.guild.id
        )

    @joint_hit.error
    async def on_error(self, ctx: EvictContext, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            return await self.joint_send(
                ctx, "You are getting too high! Please wait until you can hit again"
            )

    @jointcmd.command(
        name="pass", description="pass the joint to someone else", usage="[member]"
    )
    @Joint.check_joint()
    @Joint.joint_owner()
    async def joint_pass(self, ctx: EvictContext, *, member: discord.Member):
        if member.id == self.bot.user.id:
            return await ctx.reply("Thank you, but i do not smoke")
        elif member.bot:
            return await ctx.warning("Bots do not smoke")
        elif member.id == ctx.author.id:
            return await ctx.warning("You already have the **joint**")
        await self.bot.db.execute(
            "UPDATE joint SET holder = $1 WHERE guild_id = $2", member.id, ctx.guild.id
        )
        await self.joint_send(ctx, f"Passing the **joint** to **{member.name}**")

    @jointcmd.command(name="steal", description="steal the server's joint")
    @Joint.check_joint()
    async def joint_steal(self, ctx: EvictContext):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM joint WHERE guild_id = $1", ctx.guild.id
        )
        if check["holder"] == ctx.author.id:
            return await self.joint_send(ctx, "You already have the **joint**")
        chances = ["yes", "yes", "yes", "no", "no"]
        if random.choice(chances) == "no":
            return await self.smoke_send(
                ctx,
                f"You tried to steal the **joint** and **{(await self.bot.fetch_user(int(check['holder']))).name}** hit you",
            )
        await self.bot.db.execute(
            "UPDATE joint SET holder = $1 WHERE guild_id = $2",
            ctx.author.id,
            ctx.guild.id,
        )
        return await self.joint_send(ctx, "You got the server **joint**")

    @commands.command(description="cuddle a user", usage="[user]")
    async def cuddle(self, ctx: EvictContext, user: discord.Member):

        images = (
            f"https://r2.evict.cc/roleplay/cuddle/cuddle{random.randint(1, 30)}.gif"
        )

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just cuddled {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="poke a user", usage="[user]")
    async def poke(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/poke/poke{random.randint(1, 15)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just poked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="kiss a user", usage="[user]")
    async def kiss(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/kiss/kiss{random.randint(1, 20)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just kissed {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="hug a user", usage="[user]")
    async def hug(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/hug/hug{random.randint(1, 20)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just hugged {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="pat a user", usage="[user]")
    async def pat(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/pat/pat{random.randint(1, 20)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just patted {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="tickle a user", usage="[user]")
    async def tickle(self, ctx: EvictContext, user: discord.Member):

        images = (
            f"https://r2.evict.cc/roleplay/tickle/tickle{random.randint(1, 18)}.gif"
        )

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just tickled {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="lick a user", usage="[user]")
    async def lick(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/lick/lick{random.randint(1, 16)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just licked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="slap a user", usage="[user]")
    async def slap(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/slap/slap{random.randint(1, 15)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just slapped {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="spank a user", usage="[user]")
    async def spank(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/spank/spank{random.randint(1, 13)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just spanked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="feed a user", usage="[user]")
    async def feed(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/feed/feed{random.randint(1, 11)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just fed {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="punch a user", usage="[user]")
    async def punch(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/punch/punch{random.randint(1, 19)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just punched {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="highfive a user", usage="[user]")
    async def highfive(self, ctx: EvictContext, user: discord.Member):

        images = (
            f"https://r2.evict.cc/roleplay/highfive/highfive{random.randint(1, 10)}.gif"
        )

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just highfived {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="kill a user", usage="[user]")
    async def kill(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/kill/kill{random.randint(1, 13)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just killed {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)
        await ctx.reply(embed=embed)

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="bite", description="bite a user")
    async def bite(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/bite/bite{random.randint(1, 30)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just bit {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="nutkick a user", usage="[user]")
    async def nutkick(self, ctx: EvictContext, user: discord.Member):

        images = (
            f"https://r2.evict.cc/roleplay/nutkick/nutkick{random.randint(1, 8)}.gif"
        )

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just nutkicked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="fuck a user", usage="[user]")
    async def fuck(self, ctx: EvictContext, user: discord.Member):

        images = f"https://r2.evict.cc/roleplay/fuck/fuck{random.randint(1, 8)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just fucked {f'**{str(user.mention)}**' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="have a threesome", usage="[user]")
    async def threesome(
        self, ctx: EvictContext, user: discord.Member, user1: discord.Member
    ):

        images = f"https://r2.evict.cc/roleplay/spank/spank{random.randint(1, 13)}.gif"

        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just fucked {str(user.mention)} and {f'{str(user1.mention)}' if user else 'themselves'}!",
        )

        embed.set_author(
            name=ctx.author.name, icon_url=ctx.author.display_avatar
        )  # type: ignore

        embed.set_image(url=images)

        await ctx.reply(embed=embed)

    @commands.command(description="hump a user", usage="[user]")
    async def hump(self, ctx: EvictContext, user: discord.Member):
        headers = {"api-key": self.bot.evict_api}
        response = await self.bot.session.get_json(
            "https://api.evict.cc/roleplay/hump", headers=headers
        )
        embed = discord.Embed(
            colour=Colors.color,
            description=f"**{ctx.author.mention}** just humped **{user.mention}**!",
        )
        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_image(url=response["image_url"])
        await ctx.reply(embed=embed)

    @commands.command(description="marry an user", usage="[user]")
    async def marry(self, ctx: EvictContext, *, member: discord.Member):
        if member == ctx.author:
            return await ctx.error("You can't **marry** yourself")
        elif member.bot:
            return await ctx.error("robots can't consent marriage".capitalize())
        else:
            meri = await self.bot.db.fetchrow(
                "SELECT * FROM marry WHERE author = $1", member.id
            )
            if meri is not None:
                return await ctx.warning(f"**{member}** is already married")
            elif meri is None:
                mer = await self.bot.db.fetchrow(
                    "SELECT * FROM marry WHERE soulmate = $1", member.id
                )
                if mer is not None:
                    return await ctx.warning(f"**{member}** is already married")

            check = await self.bot.db.fetchrow(
                "SELECT * FROM marry WHERE author = $1", ctx.author.id
            )
            if check is not None:
                return await ctx.warning(
                    "You are already **married**. Are you trying to cheat?? 🤨"
                )
            elif check is None:
                check2 = await self.bot.db.fetchrow(
                    "SELECT * FROM marry WHERE soulmate = $1", ctx.author.id
                )
                if check2 is not None:
                    await ctx.warning(
                        "You are already **married**. Are you trying to cheat?? 🤨"
                    )
                else:
                    embed = discord.Embed(
                        color=Colors.color,
                        description=f"**{ctx.author.name}** wants to marry you. do you accept?",
                    )
                    view = MarryView(ctx, member)
                    view.message = await ctx.reply(
                        content=member.mention, embed=embed, view=view
                    )

    @commands.command(description="check an user's marriage", usage="<member>")
    async def marriage(self, ctx: EvictContext, *, member: discord.User = None):
        if member is None:
            member = ctx.author
        check = await self.bot.db.fetchrow(
            "SELECT * FROM marry WHERE author = $1", member.id
        )
        if check is None:
            check2 = await self.bot.db.fetchrow(
                "SELECT * FROM marry WHERE soulmate = $1", member.id
            )
            if check2 is None:
                return await ctx.error(
                    f"{'**You** are' if member == ctx.author else f'**{member.name}** is'} not **married**"
                )
            elif check2 is not None:
                embed = discord.Embed(
                    color=Colors.color,
                    description=f"💒 {f'**{member}** is' if member != ctx.author else '**You** are'} currently married to **{await self.bot.fetch_user(int(check2[0]))}** since **{self.bot.ext.relative_time(datetime.datetime.fromtimestamp(int(check2['time'])))}**",
                )
                return await ctx.reply(embed=embed)
        elif check is not None:
            embed = discord.Embed(
                color=Colors.color,
                description=f"💒 {f'**{member}** is' if member != ctx.author else '**You** are'} currently married to **{await self.bot.fetch_user(int(check[1]))}** since **{self.bot.ext.relative_time(datetime.datetime.fromtimestamp(int(check['time'])))}**",
            )
            return await ctx.reply(embed=embed)

    @commands.command(description="divorce with an user")
    async def divorce(self, ctx: EvictContext):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM marry WHERE author = $1", ctx.author.id
        )
        if check is None:
            check2 = await self.bot.db.fetchrow(
                "SELECT * FROM marry WHERE soulmate = $1", ctx.author.id
            )
            if check2 is None:
                return await ctx.error("**You** are not **married**")

        button1 = Button(emoji=Emojis.approve, style=discord.ButtonStyle.grey)
        button2 = Button(emoji=Emojis.deny, style=discord.ButtonStyle.grey)
        embed = discord.Embed(
            color=Colors.color,
            description=f"**{ctx.author.name}** are you sure you want to divorce?",
        )

        async def button1_callback(interaction):
            if interaction.user != ctx.author:
                return await self.bot.ext.warning(
                    interaction, "You are not the author of this embed", ephemeral=True
                )
            if check is None:
                if check2 is not None:
                    await self.bot.db.execute(
                        "DELETE FROM marry WHERE soulmate = $1", ctx.author.id
                    )
            elif check is not None:
                await self.bot.db.execute(
                    "DELETE FROM marry WHERE author = $1", ctx.author.id
                )
            embe = discord.Embed(
                color=Colors.color,
                description=f"**{ctx.author.name}** divorced with their partner",
            )
            await interaction.response.edit_message(content=None, embed=embe, view=None)

        button1.callback = button1_callback

        async def button2_callback(interaction):
            if interaction.user != ctx.author:
                return await self.bot.ext.warning(
                    interaction, "You are not the author of this embed", ephemeral=True
                )
            embe = discord.Embed(
                color=Colors.color,
                description=f"**{ctx.author.name}** you changed your mind",
            )
            await interaction.response.edit_message(content=None, embed=embe, view=None)

        button2.callback = button2_callback

        marry = View()
        marry.add_item(button1)
        marry.add_item(button2)
        await ctx.reply(embed=embed, view=marry)

    @commands.group(invoke_without_command=True)
    async def diary(self, ctx: EvictContext):
        return await ctx.create_pages()

    @diary.command(
        name="create", aliases=["add"], description="create a diary for today"
    )
    async def diary_create(self, ctx: EvictContext):
        now = datetime.datetime.now()
        date = f"{now.month}/{now.day}/{str(now.year)[2:]}"
        check = await ctx.bot.db.fetchrow(
            "SELECT * FROM diary WHERE user_id = $1 AND date = $2", ctx.author.id, date
        )
        if check:
            return await ctx.warning(
                "You **already** have a diary page created today! Please come back tomorrow or delete the diary page you created"
            )
        embed = discord.Embed(
            color=Colors.color,
            description=f"{self.book} Press the button below to create a diary page",
        )
        button = discord.ui.Button(emoji=self.book, style=discord.ButtonStyle.blurple)

        async def button_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.client.ext.warning(
                    interaction, "You are not the author of this embed"
                )
            mt = DiaryModal()
            return await interaction.response.send_modal(mt)

        button.callback = button_callback

        view = discord.ui.View()
        view.add_item(button)
        return await ctx.reply(embed=embed, view=view)

    @diary.command(name="view", description="view your diary book")
    async def diary_view(self, ctx: EvictContext):
        results = await self.bot.db.fetch(
            "SELECT * FROM diary WHERE user_id = $1", ctx.author.id
        )
        if len(results) == 0:
            return await ctx.warning("You don't have any diary page created")
        embeds = []
        for result in results:
            embeds.append(
                discord.Embed(
                    color=Colors.color,
                    title=result["title"],
                    description=result["text"],
                )
                .set_author(name=f"diary for {result['date']}")
                .set_footer(text=f"{results.index(result)+1}/{len(results)}")
            )
        return await ctx.paginator(embeds)

    @diary.command(name="delete", description="delete a diary page")
    async def diary_delete(self, ctx: EvictContext):
        options = []
        results = await self.bot.db.fetch(
            "SELECT * FROM diary WHERE user_id = $1", ctx.author.id
        )
        if len(results) == 0:
            return await ctx.warning("You don't have any diary page created")
        for result in results:
            try:
                options.append(
                    discord.SelectOption(
                        label=f"diary {results.index(result)+1} - {result['date']}",
                        value=result["date"],
                    )
                )
            except:
                continue
        embed = discord.Embed(
            color=Colors.color,
            description="Select the **dropdown** menu below to delete a diary page",
        )
        select = discord.ui.Select(options=options, placeholder="delete a diary page")

        async def select_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.client.ext.warning(
                    interaction, "You are not the author of this embed"
                )
            await self.bot.db.execute(
                "DELETE FROM diary WHERE user_id = $1 AND date = $2",
                ctx.author.id,
                select.values[0],
            )
            return await interaction.response.send_message(
                "Deleted a diary page", ephemeral=True
            )

        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        return await ctx.reply(embed=embed, view=view)


async def setup(bot: Evict) -> None:
    await bot.add_cog(roleplay(bot))
