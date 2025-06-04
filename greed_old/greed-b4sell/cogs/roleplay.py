from asyncio import sleep
from discord import Embed, Member, ButtonStyle, Interaction, app_commands
from discord.ext.commands import Cog, command, Context
from discord.ui import Button, View, button
import aiohttp
from discord import File, Embed
import os
import discord
from discord.ext import commands
from random import choice
from collections import defaultdict
from tool.greed import Greed


class MarryView(View):
    def __init__(self, bot: Greed, ctx: Context, proposer: Member, proposee: Member):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx
        self.proposer = proposer
        self.proposee = proposee

    async def on_timeout(self):
        await self.ctx.send("You took too long to respond, please try again.")
        self.stop()

    @button(label="Yes", style=ButtonStyle.green)
    async def yes(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.proposee.id:
            await interaction.response.send_message(
                "You are not the one being proposed to!", ephemeral=True
            )
            return

        await self.bot.db.execute(
            """
            INSERT INTO marriages (user1_id, user2_id)
            VALUES ($1, $2)
            ON CONFLICT (user1_id, user2_id)
            DO NOTHING;
            """,
            self.proposer.id,
            self.proposee.id,
        )
        await interaction.response.edit_message(
            content=None,
            embed=Embed(
                description=f"> {self.proposee.mention} has accepted {self.proposer.mention}'s proposal!"
            ),
            view=None,
        )
        self.stop()

    @button(label="No", style=ButtonStyle.red)
    async def no(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.proposee.id:
            await interaction.response.send_message(
                "You are not the one being proposed to!", ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content=f"{self.proposee.mention} has rejected {self.proposer.mention}'s proposal!",
            embed=None,
            view=None,
        )
        self.stop()


class Roleplay(Cog):
    def __init__(self, bot: Greed):
        self.bot = bot


    @staticmethod
    def ordinal(n: int) -> str:
        """Convert an integer into its ordinal representation, e.g., 1 -> 1st"""
        n = int(n)
        return "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )

    async def send(
        self,
        ctx: Context,
        user1: Member,
        user2: Member,
        interaction: str,
        response: str,
    ) -> None:
        """Send an embed for a roleplay interaction and update interaction count."""

        query = """
        INSERT INTO interactions (user1_id, user2_id, interaction, count)
        VALUES ($1, $2, $3, 1)
        ON CONFLICT (user1_id, user2_id, interaction)
        DO UPDATE SET count = interactions.count + 1
        RETURNING count;
        """
        record = await self.bot.db.fetchrow(query, user1.id, user2.id, interaction)
        interaction_count = record["count"]

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://nekos.best/api/v2/{interaction}") as resp:
                if resp.status != 200:
                    await ctx.send("Couldn't retrieve a GIF, please try again later.")
                    return
                data = await resp.json()
                gif_url = data["results"][0]["url"]

        embed = Embed(
            description=f"> {user1.mention} {response} {user2.mention} for the {self.ordinal(interaction_count)} time!",
        )
        embed.set_image(url=gif_url)

        await ctx.send(embed=embed)


    @Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        """Triggered when a channel's NSFW status is changed."""

        # Check if the channel was changed from NSFW to SFW
        if before.nsfw and not after.nsfw:
            # Get all messages in the channel and filter based on embed URLs
            embeds_to_delete = self.nsfw_embeds.get(before.id, [])

            async for message in before.history(
                limit=100
            ):  # Limit set to 100, adjust if needed
                for embed in message.embeds:
                    # If the embed URL matches one we saved, delete that message
                    if embed.url in embeds_to_delete:
                        await message.delete()

            # Clear the stored embeds for this channel after deletion
            self.nsfw_embeds[before.id].clear()

    @app_commands.command(
        name="kiss",
        description="Kiss another user.",
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(users=True, guilds=True)
    async def kiss_userapp(self, interaction: Interaction, user: Member) -> None:
        ctx = await Context.from_interaction(interaction)
        await self.kiss(ctx, user)

    @app_commands.command(
        name="hug",
        description="Hug another user.",
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(users=True, guilds=True)
    async def hug_userapp(self, interaction: Interaction, user: Member) -> None:
        ctx = await Context.from_interaction(interaction)
        await self.hug(ctx, user)

    @app_commands.command(
        name="smile",
        description="Smile at another user.",
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(users=True, guilds=True)
    async def smile_userapp(self, interaction: Interaction, user: Member) -> None:
        ctx = await Context.from_interaction(interaction)
        await self.smile(ctx, user)

    @app_commands.command(
        name="pat",
        description="Pat another user.",
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(users=True, guilds=True)
    async def pat_userapp(self, interaction: Interaction, user: Member) -> None:
        ctx = await Context.from_interaction(interaction)
        await self.pat(ctx, user)

    @app_commands.command(
        name="pout",
        description="Pout at another user.",
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(users=True, guilds=True)
    async def pout_userapp(self, interaction: Interaction, user: Member) -> None:
        ctx = await Context.from_interaction(interaction)
        await self.pout(ctx, user)

    @app_commands.command(
        name="nod",
        description="Nod at another user.",
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(users=True, guilds=True)
    async def nod_userapp(self, interaction: Interaction, user: Member) -> None:
        ctx = await Context.from_interaction(interaction)
        await self.nod(ctx, user)

    @command(
        name="propose",
        aliases=["marry"],
        brief="propose to another user.",
        example=",propose @wurri",
    )
    async def propose(self, ctx: Context, member: Member) -> None:
        """propose to another user."""
        proposer_res = await self.bot.db.fetchrow(
            """
            SELECT * FROM marriages
            WHERE user1_id = $1 OR user2_id = $1;
            """,
            ctx.author.id,
        )
        if proposer_res:
            return await ctx.send("You're already married to someone!")

        if member.id == ctx.author.id:
            return await ctx.fail("You can't marry yourself!")

        if member.bot:
            return await ctx.fail("You can't marry a bot!")

        proposee_res = await self.bot.db.fetchrow(
            """
            SELECT * FROM marriages
            WHERE user1_id = $1 OR user2_id = $1;
            """,
            member.id,
        )
        if proposee_res:
            return await ctx.fail(f"{member.mention} is already married to someone!")

        view = MarryView(self.bot, ctx, ctx.author, member)
        await ctx.send(
            content=member.mention,
            embed=Embed(description=f"{ctx.author.mention} has proposed to you!"),
            view=view,
        )

    @command(name="spouse", brief="check who your spouse is.")
    async def spouse(self, ctx: Context) -> None:
        """check who your spouse is."""
        res = await self.bot.db.fetchrow(
            """
            SELECT * FROM marriages
            WHERE user1_id = $1 OR user2_id = $1;
            """,
            ctx.author.id,
        )
        if not res:
            return await ctx.fail("You're not married to anyone!")

        spouse_id = (
            res["user1_id"] if res["user2_id"] == ctx.author.id else res["user2_id"]
        )
        spouse = ctx.guild.get_member(spouse_id)
        if spouse is None:
            return await ctx.fail("Your spouse is not in this server.")
        await ctx.normal(f"You are married to {spouse.name}!")

    @command(name="divorce", brief="divorce your spouse.")
    async def divorce(self, ctx: Context) -> None:
        """divorce your spouse."""
        res = await self.bot.db.fetchrow(
            """
            SELECT * FROM marriages
            WHERE user1_id = $1 OR user2_id = $1;
            """,
            ctx.author.id,
        )
        if not res:
            return await ctx.fail("You're not married to anyone!")

        spouse_id = (
            res["user1_id"] if res["user2_id"] == ctx.author.id else res["user2_id"]
        )
        await self.bot.db.execute(
            """
            DELETE FROM marriages
            WHERE user1_id = $1 OR user2_id = $1;
            """,
            ctx.author.id,
        )
        await ctx.normal(f"You are now divorced!")

    @command(name="kiss", brief="kiss another user.", example=",kiss @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def kiss(self, ctx: Context, member: Member) -> None:
        """kiss another user."""
        await self.send(ctx, ctx.author, member, "kiss", "kisses")

    @command(name="hug", brief="hug another user.", example=",hug @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def hug(self, ctx: Context, member: Member) -> None:
        """hug another user."""
        await self.send(ctx, ctx.author, member, "hug", "hugs")

    @command(name="smile", brief="smile at another user.", example=",smile @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def smile(self, ctx: Context, member: Member) -> None:
        """smile at another user."""
        await self.send(ctx, ctx.author, member, "smile", "smiles at")

    @command(name="pat", brief="pat another user.", example=",pat @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def pat(self, ctx: Context, member: Member) -> None:
        """pat another user."""
        await self.send(ctx, ctx.author, member, "pat", "pats")

    @command(name="pout", brief="pout at another user.", example=",pout @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def pout(self, ctx: Context, member: Member) -> None:
        """pout at another user."""
        await self.send(ctx, ctx.author, member, "pout", "pouts at")

    @command(name="nod", brief="nod at another user.", example=",nod @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def nod(self, ctx: Context, member: Member) -> None:
        """nod at another user."""
        await self.send(ctx, ctx.author, member, "nod", "nods at")

    @command(name="punch", brief="punch another user.", example=",punch @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def punch(self, ctx: Context, member: Member) -> None:
        """punch another user."""
        await self.send(ctx, ctx.author, member, "punch", "punches")

    @command(name="laugh", brief="laugh at another user.", example=",laugh @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def laugh(self, ctx: Context, member: Member) -> None:
        """laugh at another user."""
        await self.send(ctx, ctx.author, member, "laugh", "laughs at")

    @command(name="wink", brief="wink at another user.", example=",wink @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def wink(self, ctx: Context, member: Member) -> None:
        """wink at another user."""
        await self.send(ctx, ctx.author, member, "wink", "winks at")

    @command(name="blush", brief="blush at another user.", example=",blush @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def blush(self, ctx: Context, member: Member) -> None:
        """blush at another user."""
        await self.send(ctx, ctx.author, member, "blush", "blushes at")

    @command(name="cuddle", brief="cuddle with another user.", example=",cuddle @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cuddle(self, ctx: Context, member: Member) -> None:
        """cuddle with another user."""
        await self.send(ctx, ctx.author, member, "cuddle", "cuddles with")

    @command(name="slap", brief="slap another user.", example=",slap @wurri")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def slap(self, ctx: Context, member: Member) -> None:
        """slap another user."""
        await self.send(ctx, ctx.author, member, "slap", "slaps")

    @command(
        name="kill",
        brief="kill another user.",
        example=",kill @tourxp",
        aliases=["shoot"],
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def kill(self, ctx: Context, member: Member) -> None:
        """
        kill another user.
        """
        await self.send(ctx, ctx.author, member, "shoot", "kills")





async def setup(bot: "Greed"):
    await bot.add_cog(Roleplay(bot))
