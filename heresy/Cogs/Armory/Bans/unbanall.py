import discord
from discord.ext import commands
from discord.ui import View, Button

class BanListView(View):
    def __init__(self, bans, author):
        super().__init__(timeout=60)
        self.bans = bans
        self.author = author
        self.current_page = 0
        self.items_per_page = 10

    def get_embed(self):
        embed = discord.Embed(title="Ban List", color=discord.Color.red())
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        bans_page = self.bans[start:end]

        # Only display the Username and User ID
        ban_lines = [f"{ban.user} `(`{ban.user.id}`)`" for ban in bans_page]
        embed.description = "\n".join(ban_lines) if ban_lines else "No banned users found."

        total_bans = len(self.bans)
        embed.set_footer(
            text=f"Page: {self.current_page + 1}/{(total_bans - 1) // self.items_per_page + 1} | Showing {len(bans_page)}/{total_bans}"
        )
        return embed

    async def update_message(self, interaction):
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="<:left:1307448382326968330>", style=discord.ButtonStyle.primary)
    async def left_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You can't interact with this embed.", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(emoji="<:cancel:1307448502913204294>", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You can't interact with this embed.", ephemeral=True)
            return
        await interaction.response.edit_message(content="Ban list closed.", embed=None, view=None)

    @discord.ui.button(emoji="<:right:1307448399624405134>", style=discord.ButtonStyle.primary)
    async def right_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You can't interact with this embed.", ephemeral=True)
            return
        if (self.current_page + 1) * self.items_per_page < len(self.bans):
            self.current_page += 1
            await self.update_message(interaction)


class UnbanAll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='unbanall', aliases=['massunban', 'uba'], description="Unbans all members in the server.")
    @commands.has_permissions(administrator=True)
    async def unban_all(self, ctx):
        """Unban all members from the server."""
        unbanned_count = 0

        try:
            bans = [ban async for ban in ctx.guild.bans()]
            for ban_entry in bans:
                user = ban_entry.user
                try:
                    await ctx.guild.unban(user)
                    unbanned_count += 1
                except Exception as e:
                    await ctx.send(f"Failed to unban {user}: {e}")

            await ctx.send(embed=discord.Embed(
                title="Unban All Complete",
                description=f"Unbanned {unbanned_count} users.",
                color=discord.Color.green()
            ))
        except Exception as e:
            await ctx.send(embed=discord.Embed(
                title="Error",
                description=f"An error occurred while fetching the ban list: {e}",
                color=discord.Color.red()
            ))

    @commands.command(name='banlist', aliases=['bans'], description="Displays the server's ban list.")
    @commands.has_permissions(administrator=True)
    async def ban_list(self, ctx):
        """Display the server's ban list in a paginated embed."""
        try:
            bans = [ban async for ban in ctx.guild.bans()]
            if not bans:
                await ctx.send("There are no banned users in this server.")
                return

            view = BanListView(bans, ctx.author)
            embed = view.get_embed()
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            await ctx.send(embed=discord.Embed(
                title="Error",
                description=f"An error occurred while fetching the ban list: {e}",
                color=discord.Color.red()
            ))

async def setup(bot):
    await bot.add_cog(UnbanAll(bot))
