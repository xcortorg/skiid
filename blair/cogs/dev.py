import asyncpg
import discord
from discord.ext import commands
from tools.config import color, emoji
from tools.context import Context
from tools.paginator import Simple


class Dev(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.group(aliases=["dnr"])
    @commands.has_permissions(manage_channels=True)
    async def donor(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @donor.command()
    @commands.is_owner()
    async def add(self, ctx, member: discord.Member):
        if await self.is_donor(member.id):
            await ctx.deny(f"{member.mention} **has** already donor")
            return

        await self.update_donor_status(member.id, add=True)
        await ctx.agree(f"**Added** donor to {member.mention}")

    @donor.command()
    @commands.is_owner()
    async def remove(self, ctx, member: discord.Member):
        if not await self.is_donor(member.id):
            await ctx.deny(f"{member.mention} **dont** got donor")
            return

        await self.update_donor_status(member.id, add=False)
        await ctx.agree(f"**Revoked** donor from {member.mention}")

    @commands.command(description="Blacklist horrible people", aliases=["bl"])
    @commands.is_owner()
    async def blacklist(
        self, ctx, user: discord.User, *, reason: str = "No reason provided"
    ):
        async with self.client.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT 1 FROM blacklist WHERE user_id = $1", str(user.id)
            )
            if result:
                await ctx.deny(f"{user.mention} is **already** blacklisted.")
                return

            await conn.execute(
                "INSERT INTO blacklist (user_id, reason) VALUES ($1, $2)",
                str(user.id),
                reason,
            )
            await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Unblacklist nice people", aliases=["unbl"])
    @commands.is_owner()
    async def unblacklist(self, ctx, user: discord.User):
        async with self.client.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT 1 FROM blacklist WHERE user_id = $1", str(user.id)
            )
            if not result:
                await ctx.deny(f"{user.mention} isn't **blacklisted**")
                return

            await conn.execute("DELETE FROM blacklist WHERE user_id = $1", str(user.id))
            await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Check for all the blacklisted users")
    async def blacklisted(self, ctx: commands.Context):
        rows = await self.client.pool.fetch("SELECT user_id, reason FROM blacklist")

        if not rows:
            embed = discord.Embed(description="Nones blacklisted", color=color.default)
            return await ctx.send(embed=embed)

        embeds = []
        for i in range(0, len(rows), 10):
            embed = discord.Embed(title="Blacklisted", color=color.default)
            description = ""
            for row in rows[i : i + 10]:
                user_id = row["user_id"]
                reason = row["reason"]
                user = await self.client.fetch_user(user_id)
                description += f"> {user.mention} ({user.id}) blacklisted for the reason: {reason}\n\n"

            embed.description = description
            embed.set_footer(text=f"Page {i // 10 + 1}/{(len(rows) - 1) // 10 + 1}")
            embeds.append(embed)

        paginator = Simple()
        await paginator.start(ctx, embeds)

    async def is_donor(self, user_id: int) -> bool:
        result = await self.client.pool.fetchrow(
            "SELECT is_donor FROM donors WHERE user_id = $1", user_id
        )
        return result and result["is_donor"]

    async def update_donor_status(self, user_id: int, add: bool):
        if add:
            await self.client.pool.execute(
                "INSERT INTO donors (user_id, is_donor) VALUES ($1, TRUE) "
                "ON CONFLICT (user_id) DO UPDATE SET is_donor = TRUE",
                user_id,
            )
        else:
            await self.client.pool.execute(
                "UPDATE donors SET is_donor = FALSE WHERE user_id = $1", user_id
            )


async def setup(client):
    await client.add_cog(Dev(client))
