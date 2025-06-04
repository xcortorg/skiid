import discord
from discord.ext import commands
from discord.ui import View, Button

class InRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="inrole", invoke_without_command=True)
    async def inrole(self, ctx, role: discord.Role):
        """Displays all members in a specific role with interactive buttons."""
        members = role.members
        if not members:
            await ctx.send(f"No members found in the role {role.mention}.")
            return

        member_chunks = [members[i:i + 10] for i in range(0, len(members), 10)]
        current_page = 0

        def create_embed(page):
            embed = discord.Embed(
                title=f"Members in {role.name} ({len(members)})",
                description="\n".join([f"- {member.mention}" for member in member_chunks[page]]),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Page {page + 1}/{len(member_chunks)}")
            return embed

        async def update(interaction, page):
            embed = create_embed(page)
            await interaction.response.edit_message(embed=embed, view=create_view(page))

        def create_view(page):
            view = View()
            if page > 0:
                view.add_item(Button(label="Previous", style=discord.ButtonStyle.primary, emoji="◀",
                                      custom_id="prev", callback=lambda i: update(i, page - 1)))
            if page < len(member_chunks) - 1:
                view.add_item(Button(label="Next", style=discord.ButtonStyle.primary, emoji="▶",
                                      custom_id="next", callback=lambda i: update(i, page + 1)))
            return view

        embed = create_embed(current_page)
        view = create_view(current_page)
        await ctx.send(embed=embed, view=view)

    @inrole.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def inrole_ban(self, ctx, role: discord.Role):
        """Bans all members in the mentioned role."""
        for member in role.members:
            try:
                await member.ban(reason=f"Mass ban by {ctx.author} via inrole ban")
                await ctx.send(f"Banned {member.mention}")
            except Exception as e:
                await ctx.send(f"Failed to ban {member.mention}: {e}")

    @inrole.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def inrole_kick(self, ctx, role: discord.Role):
        """Kicks all members in the mentioned role."""
        for member in role.members:
            try:
                await member.kick(reason=f"Mass kick by {ctx.author} via inrole kick")
                await ctx.send(f"Kicked {member.mention}")
            except Exception as e:
                await ctx.send(f"Failed to kick {member.mention}: {e}")

    @inrole.command(name="timeout")
    @commands.has_permissions(moderate_members=True)
    async def inrole_timeout(self, ctx, role: discord.Role):
        """Timeouts all members in the mentioned role."""
        for member in role.members:
            try:
                await member.timeout_for(duration=600, reason=f"Mass timeout by {ctx.author} via inrole timeout")
                await ctx.send(f"Timed out {member.mention}")
            except Exception as e:
                await ctx.send(f"Failed to timeout {member.mention}: {e}")

    @inrole.command(name="strip")
    @commands.has_permissions(manage_roles=True)
    async def inrole_strip(self, ctx, role: discord.Role):
        """Removes all roles from members in the mentioned role."""
        for member in role.members:
            try:
                await member.edit(roles=[], reason=f"Mass role removal by {ctx.author} via inrole strip")
                await ctx.send(f"Stripped roles from {member.mention}")
            except Exception as e:
                await ctx.send(f"Failed to strip roles from {member.mention}: {e}")

async def setup(bot):
    await bot.add_cog(InRole(bot))
