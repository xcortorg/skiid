import time
from datetime import datetime, timedelta

import asyncpg
import discord
from config import color, emoji
from discord.ext import commands
from system.base.context import Context


class Vanityroles(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.cache = {}

    @commands.group(
        description="Give out roles on a specific presence", aliases=["vanity", "vr"]
    )
    @commands.has_permissions(manage_channels=True)
    async def vanityroles(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @vanityroles.command(name="set", description="Set on/off the vanityroles")
    async def vanityroles_set(self, ctx, status: str):
        if status.lower() == "on":
            await self.client.pool.execute(
                "INSERT INTO vanityroles (guild_id, enabled) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET enabled = TRUE",
                ctx.guild.id,
                True,
            )
            await ctx.agree("**Enabled** the vanityroles system")
        elif status.lower() == "off":
            await self.client.pool.execute(
                "UPDATE vanityroles SET enabled = FALSE WHERE guild_id = $1",
                ctx.guild.id,
            )
            await ctx.agree("**Disabled** the vanityroles system")
        else:
            await ctx.deny("**Invalid option,** use on/off")

    @vanityroles.command(
        name="string", description="Set the vanity string", aliases=["message", "msg"]
    )
    async def vanityroles_string(self, ctx, *, vanity_string: str):
        if not vanity_string.startswith(".gg/") and not vanity_string.startswith("/"):
            await ctx.send("**Vanity string** needs to start with .gg/ or /")
            return

        await self.client.pool.execute(
            "UPDATE vanityroles SET text = $1 WHERE guild_id = $2",
            vanity_string,
            ctx.guild.id,
        )
        await ctx.agree(f"**Set** the vanity string to: `{vanity_string}`")

    @vanityroles.command(name="add", description="Add a role to vanityroles")
    async def vanityroles_add(self, ctx, *, role: discord.Role):
        await self.client.pool.execute(
            "INSERT INTO vanityroles_roles (guild_id, role_id) VALUES ($1, $2) ON CONFLICT (guild_id, role_id) DO NOTHING",
            ctx.guild.id,
            role.id,
        )
        await ctx.agree(f"**Added** {role.mention} to vanityroles")

    @vanityroles.command(name="remove", description="Remove a role from vanityroles")
    async def vanityroles_remove(self, ctx, *, role: discord.Role):
        await self.client.pool.execute(
            "DELETE FROM vanityroles_roles WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        )
        await ctx.agree(f"**Removed** {role.mention} from vanityroles")

    @vanityroles.command(name="clear", description="Clear all vanityroles settings")
    async def vanityroles_clear(self, ctx):
        await self.client.pool.execute(
            "DELETE FROM vanityroles WHERE guild_id = $1", ctx.guild.id
        )
        await self.client.pool.execute(
            "DELETE FROM vanityroles_roles WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.agree("**Cleared** all vanity settings")

    @vanityroles.command(
        name="settings", description="Check our your vanityroles settings"
    )
    async def vanityroles_settings(self, ctx):
        data = await self.client.pool.fetchrow(
            "SELECT enabled, text FROM vanityroles WHERE guild_id = $1", ctx.guild.id
        )
        roles = await self.client.pool.fetch(
            "SELECT role_id FROM vanityroles_roles WHERE guild_id = $1", ctx.guild.id
        )

        if data:
            status = "Enabled" if data["enabled"] else "Disabled"
            string = data["text"] or "None"
            roles = [
                ctx.guild.get_role(role["role_id"]).mention
                for role in roles
                if ctx.guild.get_role(role["role_id"])
            ]

            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed = discord.Embed(
                description=f"> **Vanity status:** `{status}` \n> **Vanity string:** `{string}` \n> **Assigned Roles:** {', '.join(roles) if roles else 'None'}",
                color=color.default,
            )
            embed.set_author(
                name=f"{ctx.author.name} | Vanityroles settings", icon_url=user_pfp
            )
            await ctx.send(embed=embed)
        else:
            await ctx.deny("**Could not** find any settings")

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if not after.guild:
            return

        guild_id = after.guild.id

        if guild_id in self.cache:
            cached_data = self.cache[guild_id]
            if time.time() - cached_data["timestamp"] > 1000:
                cached_data = await self.update_cache(guild_id)
        else:
            cached_data = await self.update_cache(guild_id)

        if not cached_data:
            return

        vanity_string = cached_data["vanity_string"]
        role_ids = cached_data["roles"]

        if not vanity_string or not role_ids:
            return

        activity = after.activity.name if after.activity else ""
        for role_id in role_ids:
            role = after.guild.get_role(role_id)
            if role:
                if vanity_string in activity:
                    if role not in after.roles:
                        await after.add_roles(role)
                else:
                    if role in after.roles:
                        await after.remove_roles(role)

    async def update_cache(self, guild_id):
        data = await self.client.pool.fetchrow(
            "SELECT * FROM vanityroles WHERE guild_id = $1 AND enabled = TRUE", guild_id
        )
        if not data:
            return None

        roles = await self.client.pool.fetch(
            "SELECT role_id FROM vanityroles_roles WHERE guild_id = $1", guild_id
        )

        self.cache[guild_id] = {
            "vanity_string": data["text"],
            "roles": [role["role_id"] for role in roles],
            "timestamp": time.time(),
        }

        return self.cache[guild_id]


async def setup(client):
    await client.add_cog(Vanityroles(client))
