import discord
from discord.ext import commands
from datetime import datetime

class JailCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.case_count = 0

    @commands.command(name="jail-setup")
    @commands.has_permissions(administrator=True)
    async def jail_setup(self, ctx):
        """Sets up the jail system with required roles and channels."""
        guild = ctx.guild

        jail_category = discord.utils.get(guild.categories, name="Jail")
        if not jail_category:
            jail_category = await guild.create_category("Jail")
        
        jail_channel = discord.utils.get(guild.text_channels, name="jail")
        if not jail_channel:
            jail_channel = await jail_category.create_text_channel("jail")
        
        jail_logs_channel = discord.utils.get(guild.text_channels, name="jail-logs")
        if not jail_logs_channel:
            jail_logs_channel = await jail_category.create_text_channel("jail-logs")

        jailed_role = discord.utils.get(guild.roles, name="Jailed")
        if not jailed_role:
            jailed_role = await guild.create_role(name="Jailed")

        for channel in guild.channels:
            await channel.set_permissions(jailed_role, read_messages=False, send_messages=False)
        
        await jail_channel.set_permissions(jailed_role, read_messages=True, send_messages=True)

        await ctx.send("Jail setup completed successfully.")

    @commands.command(name="jail")
    @commands.has_permissions(moderate_members=True)
    async def jail(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Jails a user, applying the jailed role and logging the event."""
        guild = ctx.guild
        jailed_role = discord.utils.get(guild.roles, name="Jailed")
        jail_logs_channel = discord.utils.get(guild.text_channels, name="jail-logs")

        if not jailed_role:
            await ctx.send("Jailed role does not exist. Run `,jail setup` first.")
            return
        if not jail_logs_channel:
            await ctx.send("Jail logs channel does not exist. Run `,jail setup` first.")
            return

        await member.add_roles(jailed_role)

        self.case_count += 1

        embed = discord.Embed(title="Jail-Logs Entry", color=discord.Color.green())
        embed.add_field(name="Information", value=(
            f"**Case #{self.case_count} | Jail**\n"
            f"**User:** {member.mention} (`{member.id}`)\n"
            f"**Moderator:** {ctx.author.mention} (`{ctx.author.id}`)\n"
            f"**Reason:** {reason}\n"
            f"{datetime.utcnow().strftime('%m/%d/%y %I:%M %p')} UTC"
        ))
        await jail_logs_channel.send(embed=embed)

        await ctx.send(f"{member.mention} has been jailed. Reason: {reason}")

    @commands.command(name="unjail")
    @commands.has_permissions(moderate_members=True)
    async def unjail(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Removes the jailed role from a user and logs the event."""
        guild = ctx.guild
        jailed_role = discord.utils.get(guild.roles, name="Jailed")
        jail_logs_channel = discord.utils.get(guild.text_channels, name="jail-logs")

        if not jailed_role:
            await ctx.send("Jailed role does not exist.")
            return
        if not jail_logs_channel:
            await ctx.send("Jail logs channel does not exist.")
            return

        await member.remove_roles(jailed_role)

        self.case_count += 1

        embed = discord.Embed(title="Jail-Logs Entry", color=discord.Color.green())
        embed.add_field(name="Information", value=(
            f"**Case #{self.case_count} | Remove Jail**\n"
            f"**User:** {member.mention} (`{member.id}`)\n"
            f"**Moderator:** {ctx.author.mention} (`{ctx.author.id}`)\n"
            f"**Reason:** {reason}\n"
            f"{datetime.utcnow().strftime('%m/%d/%y %I:%M %p')} UTC"
        ))
        await jail_logs_channel.send(embed=embed)

        await ctx.send(f"{member.mention} has been unjailed. Reason: {reason}")

async def setup(bot):
    await bot.add_cog(JailCog(bot))
