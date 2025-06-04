import discord
from discord.ext import commands
from discord.ui import View, Button


class RolesView(View):
    def __init__(self, roles, author, custom_emojis):
        super().__init__(timeout=60)  # Embed interaction lasts 60 seconds
        self.roles = roles
        self.author = author
        self.current_page = 0
        self.items_per_page = 10
        self.custom_emojis = custom_emojis

    def get_embed(self):
        embed = discord.Embed(title="Server Roles", color=discord.Color.blurple())
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        roles_page = self.roles[start:end]

        role_lines = [f"{role.name} `({role.id})`" for role in roles_page]
        embed.description = "\n".join(role_lines)  # Compact description

        embed.set_footer(
            text=f"Page {self.current_page + 1}/{(len(self.roles) - 1) // self.items_per_page + 1}"
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
            await interaction.response.send_message("You can't interact with this embed, womp womp", ephemeral=True)
            return
        await interaction.response.edit_message(content="Embed closed.", embed=None, view=None)

    @discord.ui.button(emoji="<:right:1307448399624405134>", style=discord.ButtonStyle.primary)
    async def right_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You can't interact with this embed, womp womp", ephemeral=True)
            return
        if (self.current_page + 1) * self.items_per_page < len(self.roles):
            self.current_page += 1
            await self.update_message(interaction)


class RolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="roles")
    async def roles(self, ctx):
        roles = sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True)
        custom_emojis = {
            "left": "<:left:1307448382326968330>",
            "right": "<:right:1307448399624405134>",
            "close": "<:cancel:1307448502913204294>"
        }
        view = RolesView(roles, ctx.author, custom_emojis)
        embed = view.get_embed()
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(RolesCog(bot))
