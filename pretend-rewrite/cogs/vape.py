import asyncpg
import discord
from discord.ext import commands
from discord.ext.commands import BucketType, CommandOnCooldown, cooldown


class VapeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hit_cooldown = commands.CooldownMapping.from_cooldown(
            1, 5, commands.BucketType.user
        )

    # Fetch list of available flavors
    async def get_flavors(self):
        return [
            "watermelon",
            "blueberry sour raspberry",
            "strawberry raspberry cherry ice",
            "cherry",
            "blue razz lemonade",
            "cherry cola",
            "pink lemonade",
            "tropical",
            "fruit punch",
            "peach mango",
            "mango",
            "apple",
            "banana",
            "crystalin",
            "marian`s cum",
        ]

    # Fetch user's current flavor choice
    async def get_user_flavor(self, user_id):
        async with self.bot.db.acquire() as conn:
            return await conn.fetchval(
                "SELECT flavor FROM vape_users WHERE user_id = $1", user_id
            )

    # Update or set user's flavor choice
    async def set_user_flavor(self, user_id, flavor):
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO vape_users (user_id, flavor) 
                VALUES ($1, $2) 
                ON CONFLICT (user_id) 
                DO UPDATE SET flavor = $2
                """,
                user_id,
                flavor,
            )

    # Get count of hits for a specific flavor
    async def get_user_count(self, user_id, flavor):
        async with self.bot.db.acquire() as conn:
            count = await conn.fetchval(
                "SELECT count FROM vape_counts WHERE user_id = $1 AND flavor = $2",
                user_id,
                flavor,
            )
            return count if count else 0

    # Increment hit count for user's selected flavor
    async def increment_user_count(self, user_id, flavor):
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO vape_counts (user_id, flavor, count) 
                VALUES ($1, $2, 1) 
                ON CONFLICT (user_id, flavor) 
                DO UPDATE SET count = vape_counts.count + 1
                """,
                user_id,
                flavor,
            )

    # Retrieve user's statistics for all flavors
    async def get_user_stats(self, user_id):
        async with self.bot.db.acquire() as conn:
            stats = await conn.fetch(
                "SELECT flavor, count FROM vape_counts WHERE user_id = $1", user_id
            )
            return {row["flavor"]: row["count"] for row in stats}

    @commands.command(name="flavour", aliases=["flavor"])
    async def set_flavour(self, ctx, *, chosen_flavor: str = None):
        flavors = await self.get_flavors()

        if not chosen_flavor:
            # Display flavor options if none is chosen
            flavor_list = "\n".join(f"> **{flavor}**" for flavor in flavors)
            embed = discord.Embed(
                title="Choose Your Flavor",
                description=f"Use `{ctx.clean_prefix}flavour <option>` to select a flavor.\n\n{flavor_list}",
                color=self.bot.color,
            )
            await ctx.send(embed=embed)
            return

        # Validate chosen flavor
        chosen_flavor = chosen_flavor.lower()
        if chosen_flavor not in flavors:
            await ctx.send_warning(
                "Invalid flavor. Please choose from the available options."
            )
            return

        await self.set_user_flavor(ctx.author.id, chosen_flavor)
        await ctx.send_success(f"Your vape flavor has been set to **{chosen_flavor}**!")

    @commands.command(name="hit")
    async def vape_hit(self, ctx):
        user_id = ctx.author.id
        flavor = await self.get_user_flavor(user_id)

        if not flavor:
            await ctx.send_warning(
                f"Please set a flavor first using `{ctx.clean_prefix}flavour`."
            )
            return

        bucket = self.hit_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            await ctx.send_warning(
                f"Please wait **{retry_after:.2f}** seconds before taking another hit."
            )
            return

        count = await self.get_user_count(user_id, flavor)
        await self.increment_user_count(user_id, flavor)

        await ctx.send_success(
            f"You took a hit of **{flavor}** flavored vape! Total hits: **{count + 1}**."
        )

    @commands.command(name="blunt", aliases=["smoke", "cig"])
    async def smoke(self, ctx):
        user_id = ctx.author.id
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO blunt_counts (user_id, count) 
                VALUES ($1, 1) 
                ON CONFLICT (user_id) 
                DO UPDATE SET count = blunt_counts.count + 1
                """,
                user_id,
            )
            count = await conn.fetchval(
                "SELECT count FROM blunt_counts WHERE user_id = $1", user_id
            )

        ordinal = (
            lambda n: f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
        )
        embed = discord.Embed(
            description=f"{ctx.author.mention} smoked a blunt for the **{ordinal(count)}** time!",
            color=self.bot.color,
        )
        await ctx.send(embed=embed)

    @vape_hit.error
    async def vape_hit_error(self, ctx, error):
        if isinstance(error, CommandOnCooldown):
            await ctx.send_warning(
                f"Cooldown in effect! Try again in **{error.retry_after:.2f}** seconds."
            )
        else:
            raise error

    @commands.command(name="stats")
    async def vape_stats(self, ctx):
        user_id = ctx.author.id
        flavor = await self.get_user_flavor(user_id)

        if not flavor:
            await ctx.send_warning(
                f"Set a flavor first using `{ctx.clean_prefix}flavour`."
            )
            return

        stats = await self.get_user_stats(user_id)
        if not stats:
            await ctx.send_warning("You have no recorded hits yet.")
            return

        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Vape Stats", color=self.bot.color
        )
        for flavor, count in sorted_stats:
            embed.add_field(
                name=flavor.capitalize(), value=f"Hits: {count}", inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="top", aliases=["addicts"])
    async def vape_leaderboard(self, ctx):
        async with self.bot.db.acquire() as conn:
            query = """
            SELECT user_id, SUM(count) AS total_hits
            FROM vape_counts
            GROUP BY user_id
            ORDER BY total_hits DESC
            LIMIT 10
            """
            leaderboard_data = await conn.fetch(query)

            if not leaderboard_data:
                await ctx.send_warning("No vape data found for the leaderboard.")
                return

            description = "\n".join(
                f"`{index}.` **{self.bot.get_user(entry['user_id']).display_name if self.bot.get_user(entry['user_id']) else 'ID: ' + str(entry['user_id'])}** - `{entry['total_hits']} hits`"
                for index, entry in enumerate(leaderboard_data, start=1)
            )

            embed = discord.Embed(
                title="Global Vape Leaderboard",
                description=description,
                color=self.bot.color,
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(VapeCog(bot))
