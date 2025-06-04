import discord
from discord.ext import commands
from discord.ui import View, Button

class ServersView(View):
    def __init__(self, servers, author, custom_emojis):
        super().__init__(timeout=60)  # Embed interaction lasts 60 seconds
        self.servers = servers
        self.author = author
        self.current_page = 0
        self.items_per_page = 10
        self.custom_emojis = custom_emojis

    def get_embed(self):
        embed = discord.Embed(title="Bot's Servers", color=discord.Color.blurple())
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        servers_page = self.servers[start:end]

        server_lines = [f"{guild.name} `({guild.id})`" for guild in servers_page]
        embed.description = "\n".join(server_lines)  # Compact description

        embed.set_footer(
            text=f"Page {self.current_page + 1}/{(len(self.servers) - 1) // self.items_per_page + 1}"
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
        if (self.current_page + 1) * self.items_per_page < len(self.servers):
            self.current_page += 1
            await self.update_message(interaction)


class ServersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="servers")
    async def servers(self, ctx):
        # Get the list of all guilds the bot is in
        servers = self.bot.guilds
        custom_emojis = {
            "left": "<:left:1307448382326968330>",
            "right": "<:right:1307448399624405134>",
            "close": "<:cancel:1307448502913204294>"
        }
        # Create a view for pagination
        view = ServersView(servers, ctx.author, custom_emojis)
        embed = view.get_embed()
        await ctx.send(embed=embed, view=view)

    @commands.command(name="getinvite")
    async def invite(self, ctx, guild_id: int):
        """
        Generates an invite link for the specified guild (server).
        Usage: ,invite <guild_id>
        """
        # Check if the user has the required permissions
        if ctx.author.id != 785042666475225109:  # Replace with your own owner ID
            await ctx.reply("You don't have permission to use this command.", mention_author=True)
            return

        # Get the guild (server) by ID
        guild = self.bot.get_guild(guild_id)
        if not guild:
            await ctx.reply("I could not find the server with the given ID, which means I'm probably not in there.", mention_author=True)
            return

        # Try to create a temporary invite link
        try:
            invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True, temporary=True)
            invite_url = invite.url
            await ctx.reply(f"{invite_url}")
        except Exception as e:
            await ctx.reply(f"Could not generate an invite for **{guild.name}**. Error: {e}")

async def setup(bot):
    await bot.add_cog(ServersCog(bot))
