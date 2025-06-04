import random

import aiohttp
import discord
from discord.ext import commands
from tools.config import color
from tools.context import Context
from tools.paginator import Simple


class Fun(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.flavors = [
            "Strawberry Ice",
            "Blueberry Blast",
            "Mint Chill",
            "Vanilla Custard",
            "Mango Tango",
            "Watermelon Breeze",
            "Grape Escape",
            "Apple Frost",
            "Lemon Zest",
            "Peach Fizz",
            "Cherry Bomb",
            "Coconut Dream",
            "Berry Burst",
            "Pineapple Punch",
            "Cola Fizz",
            "Raspberry Rush",
            "Banana Split",
            "Tropical Twist",
            "Candy Crush",
            "Bubblegum Pop",
            "Chocolate",
            "Cinnamon",
            "Orange",
            "Pear",
            "Kiwi",
            "Pomegranate",
            "Honeydew",
            "Blackberry",
            "Lychee",
            "Green Tea",
            "Caramel Swirl",
            "Maple Syrup",
            "Cotton Candy",
            "Mojito Mint",
            "Vanilla Bean",
            "Lime Tart",
            "Sour Apple",
            "Fruit Punch",
            "Toasted Marshmallow",
            "Peppermint Patty",
            "Peanut Butter Cup",
            "Tiramisu",
            "Mango Sticky Rice",
            "Dragon Fruit",
            "Cactus Cooler",
            "Cinnamon Roll",
            "Almond Cookie",
            "Passion Fruit",
            "Chai Tea",
            "Milkshake",
            "Fruity Pebbles",
            "Lemonade Stand",
            "Ginger Snap",
            "Spiced Pumpkin",
            "Coffee Delight",
            "Brown Sugar Cinnamon",
            "Nutty Hazelnut",
            "Vanilla Toffee",
            "Raspberry Cheesecake",
            "Chocolate Mint",
            "Banana Cream Pie",
            "Pistachio Ice Cream",
            "Peanut Butter Banana",
            "Cookie Dough Bliss",
            "Strawberry Shortcake",
            "Apple Pie à la Mode",
            "Smores Delight",
            "Caramel Macchiato",
            "Vanilla Pudding",
            "Blueberry Muffin",
            "Cherry Almond Tart",
            "Tropical Coconut Cream",
            "Fudge Brownie",
            "Chocolate Raspberry Swirl",
            "Lemon Meringue Pie",
            "Vanilla",
        ]

    @commands.group(
        description="Get 'e-cancer' by 'e-vaping' :sob:",
        aliases=["v"],
        invoke_without_command=True,
    )
    async def vape(self, ctx: Context):
        await ctx.send_help(ctx.command.qualified_name)

    @vape.command()
    async def hit(self, ctx):
        async with self.client.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT flavor, hits FROM vape WHERE user_id = $1", ctx.author.id
            )

        if not result or not result["flavor"]:
            await ctx.deny(
                "You haven't set a flavor, use `-vape flavor <flavor>` to set one."
            )
            return

        flavor = result["flavor"]
        hits = result["hits"] + 1 if result["hits"] else 1

        async with self.client.pool.acquire() as conn:
            await conn.execute(
                "UPDATE vape SET hits = $1 WHERE user_id = $2 AND flavor = $3",
                hits,
                ctx.author.id,
                flavor,
            )

        embed = discord.Embed(
            description=f"> <:vape:1296191531241312326> {ctx.author.mention}: You hit the flavor **{flavor},** now have `{hits}` hits",
            color=color.default,
        )
        await ctx.send(embed=embed)

    @vape.command()
    async def flavors(self, ctx):
        embeds = []
        page_size = 7
        pages = [
            self.flavors[i : i + page_size]
            for i in range(0, len(self.flavors), page_size)
        ]

        for page in pages:
            flavor_list = "\n".join([f"> {flavor}" for flavor in page])
            embed = discord.Embed(
                title="Available Vape Flavors",
                description=flavor_list,
                color=color.default,
            )
            embeds.append(embed)

        paginator = Simple()
        await paginator.start(ctx, embeds)

    @vape.command()
    async def flavor(self, ctx, *, flavor: str):
        if flavor not in self.flavors:
            await ctx.deny("That flavor doesn't exist, use one from `-vape flavors`.")
            return

        async with self.client.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO vape (user_id, flavor, hits) VALUES ($1, $2, 0) ON CONFLICT (user_id) DO UPDATE SET flavor = $2",
                ctx.author.id,
                flavor,
            )

        await ctx.agree(f"You've chosen the flavor **{flavor}**")

    @vape.command(name="steal", aliases=["take"])
    async def vape_steal(self, ctx: commands.Context, member: discord.Member):
        """Steal the vape flavor from a member."""
        if member.id == ctx.author.id:
            await ctx.send("You cannot steal from yourself!")
            return

        stolen_flavors = getattr(self.client, "stolen_flavors", {})
        if member.id in stolen_flavors and ctx.author.id in stolen_flavors[member.id]:
            await ctx.warn(f"You have already stolen the flavor from {member.mention}!")
            return

        async with self.client.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT flavor FROM vape WHERE user_id = $1", member.id
            )

            if not result or not result["flavor"]:
                await ctx.warn(f"{member.mention} has no flavor to steal!")
                return

            stolen_flavor = result["flavor"]

            await conn.execute(
                "INSERT INTO vape (user_id, flavor, hits) VALUES ($1, $2, 0) ON CONFLICT (user_id) DO UPDATE SET flavor = $2",
                ctx.author.id,
                stolen_flavor,
            )
            await conn.execute(
                "UPDATE vape SET flavor = NULL WHERE user_id = $1", member.id
            )

            if member.id not in stolen_flavors:
                stolen_flavors[member.id] = set()
            stolen_flavors[member.id].add(ctx.author.id)
            self.client.stolen_flavors = stolen_flavors

        embed = discord.Embed(
            description=f"> {ctx.author.mention} has stolen **{stolen_flavor}** from {member.mention}!",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)

    @vape.command(name="hits")
    async def vape_hits(self, ctx: Context):
        """View the number of hits in the server."""
        async with self.client.pool.acquire() as conn:
            results = await conn.fetch(
                "SELECT user_id, hits FROM vape WHERE hits > 0 ORDER BY hits DESC"
            )

        if not results:
            await ctx.deny("No hits recorded in the server.")
            return

        hit_list = "\n".join(
            [f"<@{row['user_id']}>: `{row['hits']}` hits" for row in results]
        )

        embed = discord.Embed(
            title="Vape hits in the Server", description=hit_list, color=color.default
        )
        await ctx.send(embed=embed)

    @commands.command(description="Get a random joke", aliases=["j"])
    async def joke(self, ctx: Context):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://official-joke-api.appspot.com/jokes/random"
            ) as resp:
                if resp.status == 200:
                    joke_data = await resp.json()
                    joke = f"{joke_data['setup']} - {joke_data['punchline']}"
                    embed = discord.Embed(
                        description=f"> **Here's a joke for you:** `{joke}`",
                        color=color.default,
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.deny("Could not fetch a joke. Try again later!")

    @commands.command(description="Flip a coin", aliases=["cf"])
    async def coinflip(self, ctx: Context):
        result = random.choice(["Heads", "Tails"])
        embed = discord.Embed(
            description=f"The coin landed on **{result}!**", color=color.default
        )
        await ctx.send(embed=embed)

    @commands.command(description="Ask the magic 8ball", aliases=["8b"])
    async def eightball(self, ctx: Context, *, question: str):
        if not question:
            await ctx.deny("Please ask a question!")
            return
        responses = ["Yes", "No", "Maybe", "Ask again later"]
        answer = random.choice(responses)
        embed = discord.Embed(
            title="Magic 8-Ball",
            description=f"🎱 **Question:** {question}\n**The 8ball says:** {answer}",
            color=color.default,
        )
        await ctx.send(embed=embed)

    @commands.command(description="Send a virtual hug", aliases=["hg"])
    async def hug(self, ctx: Context, member: discord.Member):
        if member.id == ctx.author.id:
            await ctx.deny("You can't hug yourself!")
            return
        image_url = await self.fetch_anime_image("hug")
        embed = discord.Embed(
            description=f"**{ctx.author.mention}** gives a warm hug to **{member.mention}!** 🤗",
            color=color.default,
        )
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)

    @commands.command(description="Roast someone", aliases=["r"])
    async def roast(self, ctx: Context, member: discord.Member):
        if member.id == ctx.author.id:
            await ctx.deny("You can't roast yourself!")
            return
        roast = await self.fetch_roast()
        embed = discord.Embed(
            description=f"> **{ctx.author.mention}** roasts **{member.mention}**: `{roast}`",
            color=color.default,
        )
        await ctx.send(embed=embed)

    @commands.command(description="Give a compliment", aliases=["c"])
    async def compliment(self, ctx: Context, member: discord.Member):
        if member.id == ctx.author.id:
            await ctx.deny("You can't compliment yourself!")
            return
        compliments = ["You're amazing!", "You light up the room!"]
        compliment = random.choice(compliments)
        embed = discord.Embed(
            description=f"**{ctx.author.mention}** compliments **{member.mention}:** {compliment}",
            color=color.default,
        )
        await ctx.send(embed=embed)

    @commands.command(description="Slap someone", aliases=["sl"])
    async def slap(self, ctx: Context, member: discord.Member):
        if member.id == ctx.author.id:
            await ctx.deny("You can't slap yourself!")
            return
        image_url = await self.fetch_anime_image("slap")
        embed = discord.Embed(
            description=f"**{ctx.author.mention}** slaps **{member.mention}!** 👋",
            color=color.default,
        )
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)

    @commands.command(description="Give a high five", aliases=["hf"])
    async def highfive(self, ctx: Context, member: discord.Member):
        if member.id == ctx.author.id:
            await ctx.deny("You can't high five yourself!")
            return
        image_url = await self.fetch_anime_image("highfive")
        embed = discord.Embed(
            description=f"**{ctx.author.mention}** gives **{member.mention}** a high five! ✋",
            color=color.default,
        )
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)

    @commands.command(description="Start a dance party", aliases=["d"])
    async def dance(self, ctx: Context):
        async with aiohttp.ClientSession() as session:
            api_key = "PhdRFX2usNqyZo8KLmqOjAOHOSzpMuco"
            async with session.get(
                f"https://api.giphy.com/v1/gifs/random?api_key={api_key}&tag=dance"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    gif_url = data["data"]["images"]["original"]["url"]
                    embed = discord.Embed(
                        description=f"**{ctx.author.mention}** starts a dance party! 💃🕺",
                        color=color.default,
                    )
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)
                else:
                    await ctx.deny("Could not fetch a dance GIF. Try again later!")

    @commands.command(description="Pet someone", aliases=["p"])
    async def pet(self, ctx: Context, member: discord.Member):
        if member.id == ctx.author.id:
            await ctx.deny("You can't pet yourself!")
            return
        embed = discord.Embed(
            description=f"**{ctx.author.mention}** pets **{member.mention}!** 🐾",
            color=color.default,
        )
        await ctx.send(embed=embed)

    @commands.group(description="Play Truth or Dare", aliases=["td"])
    @commands.has_permissions(administrator=True)
    async def truthordare(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @truthordare.command(description="Choose a truth question")
    async def truth(self, ctx: Context):
        truths = [
            "What is your biggest secret?",
            "What was your most embarrassing moment?",
            "Have you ever cheated on a test?",
            "Who do you have a crush on?",
            "What is one thing you wish you could change about yourself?",
            "What’s the most embarrassing thing you’ve done in front of a crush?",
            "What is the most ridiculous lie you’ve ever told?",
            "What’s something you’ve never told anyone?",
            "What’s your biggest fear?",
            "What’s the worst date you’ve ever been on?",
        ]
        truth_question = random.choice(truths)
        embed = discord.Embed(
            description=f"**Truth:** {truth_question}", color=color.default
        )
        await ctx.send(embed=embed)

    @truthordare.command(description="Get a dare")
    async def dare(self, ctx: Context):
        dares = [
            "Dance with no music for 30 seconds.",
            "Text your crush and tell them you like them.",
            "Do 10 pushups.",
            "Sing a song chosen by the group.",
            "Let someone draw on your face.",
            "Speak in an accent for the next 3 rounds.",
            "Post a silly picture of yourself in chat.",
            "Imitate someone in the group until your next turn.",
            "Do a cartwheel (or attempt to!).",
            "Let someone else come up with a dare for you.",
        ]
        dare_challenge = random.choice(dares)
        embed = discord.Embed(
            description=f"**Dare:** {dare_challenge}", color=color.default
        )
        await ctx.send(embed=embed)

    @commands.command(description="Roll a six-sided die", aliases=["d6"])
    async def roll(self, ctx: Context):
        result = random.randint(1, 6)
        embed = discord.Embed(description=f"**Result:** {result}", color=color.default)
        await ctx.send(embed=embed)

    async def fetch_anime_image(self, category: str) -> str:
        url = f"https://api.waifu.pics/sfw/{category}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("url", "https://waifu.pics/image-placeholder")
                    else:
                        print(f"API returned non-200 status: {resp.status}")
                        return "https://waifu.pics/image-placeholder"
        except aiohttp.ClientConnectorError:
            print(f"Could not connect to {url}")
            return "https://waifu.pics/image-placeholder"
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "https://waifu.pics/image-placeholder"

    async def fetch_roast(self):
        url = "https://roastme.herokuapp.com/api"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("roast", "I have no roast for you!")
            except Exception as e:
                print(f"Error fetching roast: {e}")

        predefined_roasts = [
            "You're not stupid; you just have bad luck thinking!",
            "If I had a face like yours, I'd sue my parents.",
        ]
        return random.choice(predefined_roasts)


async def setup(client):
    await client.add_cog(Fun(client))
