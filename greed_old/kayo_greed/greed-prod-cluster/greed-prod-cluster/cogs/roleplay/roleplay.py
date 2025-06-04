from typing import cast

from discord import Embed, Member, User, Message, ButtonStyle, Interaction
from discord.ui import View, Button, button
from discord.ext.commands import Cog, command, hybrid_command
from humanize import ordinal

from cogs.roleplay import BASE_URL
from main import greed
from tools.client import Context

ACTIONS = {
    "bite": "bites",
    "cuddle": "cuddles",
    "feed": "feeds",
    "hug": "hugs",
    "kiss": "kisses",
    "pat": "pats",
    "poke": "pokes",
    "punch": "punches",
    "slap": "slaps",
    "smug": "smugs at",
    "tickle": "tickles",
    "shrug": "shrugs at",
    "stare": "stares at",
    "wave": "waves at",
    "smile": "smiles",
    "peck": "peck",
    "wink": "winks at",
    "blush": "blush because of",
    "highfive": "high fives",
    "feed": "feeds",
    "nod": "nods",
    "laugh": "laughs",
    "shoot": "shoots",
    "nope": "nopes",
    "handhold": "holds",
    "thumbsup": "thumbs up's",
}


class MarriageView(View):
    def __init__(self, bot, proposer: User, proposee: User):
        super().__init__(timeout=60.0)
        self.bot: greed = bot
        self.proposer = proposer
        self.proposee = proposee
        self.response = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @button(label="Accept", style=ButtonStyle.green, custom_id="accept_proposal")
    async def accept(self, interaction: Interaction, button: Button):

        if interaction.user.id != self.proposee.id:
            return await interaction.response.send_message(
                f"Only {self.proposee.mention} can respond to this proposal.",
                ephemeral=True,
            )

        self.response = True

        await self.bot.db.execute(
            "INSERT INTO marriages (user1_id, user2_id) VALUES ($1, $2)",
            self.proposer.id,
            self.proposee.id,
        )

        await interaction.response.edit_message(
            embed=Embed(
                description=f"{self.proposee.mention} has accepted {self.proposer.mention}'s marriage proposal!"
            ),
            view=None,
        )
        self.stop()

    @button(label="Decline", style=ButtonStyle.red, custom_id="decline_proposal")
    async def decline(self, interaction: Interaction, button: Button):

        if interaction.user.id != self.proposee.id:
            return await interaction.response.send_message(
                f"Only {self.proposee.mention} can respond to this proposal.",
                ephemeral=True,
            )

        self.response = False

        await interaction.response.edit_message(
            embed=Embed(
                description=f"{self.proposee.mention} has declined {self.proposer.mention}'s marriage proposal."
            ),
            view=None,
        )
        self.stop()


class Roleplay(Cog):
    def __init__(self, bot: greed):
        self.bot = bot

    async def send(
        self,
        ctx: Context,
        member: Member,
        category: str,
    ) -> Message:
        """
        Requests the API,
        and structures the embed.
        """

        response = await self.bot.session.get(
            BASE_URL.with_path(f"/api/v2/{category}"),
        )
        data = await response.json()
        if not data.get("results"):
            return await ctx.warn("Something went wrong, please try again later")

        amount = 0
        if member != ctx.author:
            amount = cast(
                int,
                await self.bot.db.fetchval(
                    """
                    INSERT INTO roleplay (user_id, target_id, category)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, target_id, category)
                    DO UPDATE SET amount = roleplay.amount + 1
                    RETURNING amount
                    """,
                    ctx.author.id,
                    member.id,
                    category,
                ),
            )

        embed = Embed(
            description=(
                f"> {ctx.author.mention} **{ACTIONS[category]}** {member.mention if member != ctx.author else 'themselves'}"
                + (
                    f" for the **{ordinal(amount)}** time"
                    if member != ctx.author and amount
                    else "... kinky"
                )
            ),
        )
        embed.set_image(url=data["results"][0]["url"])

        return await ctx.send(embed=embed)

    @command(name="marry", brief="@wtour")
    async def marry(self, ctx: Context, member: Member) -> Message:
        """Propose marriage to another user"""
        proposer = ctx.author
        proposee = member

        proposer_record = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user1_id = $1 OR user2_id = $1", proposer.id
        )
        if proposer_record:
            return await ctx.warn(f"{proposer.mention}, you are already married!")

        if proposee.bot:
            return await ctx.warn(f"{proposee.mention} is a bot and cannot be married.")

        proposee_record = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user1_id = $1 OR user2_id = $1", proposee.id
        )
        if proposee_record:
            return await ctx.warn(f"{proposee.mention} is already married!")

        return await ctx.send(
            embed=Embed(
                description=f"{proposer.mention} has proposed to {proposee.mention}!"
            ),
            view=MarriageView(self.bot, proposer, proposee),
        )

    @command(name="divorce")
    async def divorce(self, ctx: Context) -> Message:
        """Divorce your current spouse"""
        user = ctx.author

        marriage_record = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user1_id = $1 OR user2_id = $1", user.id
        )
        if not marriage_record:
            return await ctx.warn(f"{user.mention}, you are not married!")

        await self.bot.db.execute(
            "DELETE FROM marriages WHERE user1_id = $1 OR user2_id = $1", user.id
        )

        await ctx.approve(f"{user.mention}, you are now divorced.")

    @command(name="spouse")
    async def spouse(self, ctx: Context) -> Message:
        """Check who you are married to"""
        user = ctx.author

        marriage_record = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user1_id = $1 OR user2_id = $1", user.id
        )
        if not marriage_record:
            return await ctx.warn(f"{user.mention}, you are not married!")

        spouse_id = (
            marriage_record["user1_id"]
            if marriage_record["user2_id"] == user.id
            else marriage_record["user2_id"]
        )
        spouse = await self.bot.fetch_user(spouse_id)

        return await ctx.approve(
            f"{user.mention}, you are married to {spouse.mention}."
        )

    @hybrid_command(usage="[member]", brief="@66adam")
    async def bite(self, ctx: Context, member: Member) -> Message:
        """
        Bite someone.
        """

        return await self.send(ctx, member, "bite")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def cuddle(self, ctx: Context, member: Member) -> Message:
        """
        Cuddle someone.
        """

        return await self.send(ctx, member, "cuddle")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def feed(self, ctx: Context, member: Member) -> Message:
        """
        Feed someone.
        """

        return await self.send(ctx, member, "feed")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def hug(self, ctx: Context, member: Member) -> Message:
        """
        Hug someone.
        """

        return await self.send(ctx, member, "hug")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def kiss(self, ctx: Context, member: Member) -> Message:
        """
        Kiss someone.
        """

        return await self.send(ctx, member, "kiss")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def pat(self, ctx: Context, member: Member) -> Message:
        """
        Pat someone.
        """

        return await self.send(ctx, member, "pat")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def poke(self, ctx: Context, member: Member) -> Message:
        """
        Poke someone.
        """

        return await self.send(ctx, member, "poke")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def punch(self, ctx: Context, member: Member) -> Message:
        """
        Punch someone.
        """

        return await self.send(ctx, member, "punch")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def slap(self, ctx: Context, member: Member) -> Message:
        """
        Slap someone.
        """

        return await self.send(ctx, member, "slap")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def smug(self, ctx: Context, member: Member) -> Message:
        """
        Smug at someone.
        """

        return await self.send(ctx, member, "smug")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def tickle(self, ctx: Context, member: Member) -> Message:
        """
        Tickle someone.
        """

        return await self.send(ctx, member, "tickle")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def shrug(self, ctx: Context, member: Member) -> Message:
        """
        Shrug at someone.
        """

        return await self.send(ctx, member, "shrug")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def stare(self, ctx: Context, member: Member) -> Message:
        """
        Stares at someone.
        """

        return await self.send(ctx, member, "stare")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def wave(self, ctx: Context, member: Member) -> Message:
        """
        Waves at someone.
        """

        return await self.send(ctx, member, "wave")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def smile(self, ctx: Context, member: Member) -> Message:
        """
        Smiles at someone.
        """

        return await self.send(ctx, member, "smile")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def peck(self, ctx: Context, member: Member) -> Message:
        """
        Peck's someone.
        """

        return await self.send(ctx, member, "peck")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def wink(self, ctx: Context, member: Member) -> Message:
        """
        Wink's at someone.
        """

        return await self.send(ctx, member, "wink")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def blush(self, ctx: Context, member: Member) -> Message:
        """
        Blushes at someone.
        """

        return await self.send(ctx, member, "blush")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def highfive(self, ctx: Context, member: Member) -> Message:
        """
        High fives someone.
        """

        return await self.send(ctx, member, "highfive")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def feed(self, ctx: Context, member: Member) -> Message:
        """
        Feed's someone.
        """

        return await self.send(ctx, member, "feed")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def nod(self, ctx: Context, member: Member) -> Message:
        """
        Nods at someone.
        """

        return await self.send(ctx, member, "nod")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def laugh(self, ctx: Context, member: Member) -> Message:
        """
        Laughs at someone.
        """

        return await self.send(ctx, member, "laugh")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def shoot(self, ctx: Context, member: Member) -> Message:
        """
        Shoots someone.
        """

        return await self.send(ctx, member, "shoot")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def nope(self, ctx: Context, member: Member) -> Message:
        """
        Nopes at someone.
        """

        return await self.send(ctx, member, "nope")

    @hybrid_command(usage="[member]", brief="@66adam", aliases=["hold"])
    async def handhold(self, ctx: Context, member: Member) -> Message:
        """
        Holds someones hand.
        """

        return await self.send(ctx, member, "handhold")

    @hybrid_command(usage="[member]", brief="@66adam")
    async def thumbsup(self, ctx: Context, member: Member) -> Message:
        """
        Thumbsup someones.
        """

        return await self.send(ctx, member, "thumbsup")
