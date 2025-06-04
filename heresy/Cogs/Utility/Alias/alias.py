import discord
from discord.ext import commands
import json
import os

ALIAS_FILE = os.path.join(os.path.dirname(__file__), "alias.json")

class Alias(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alias_data = self.load_alias_data()

    def load_alias_data(self):
        if os.path.exists(ALIAS_FILE):
            with open(ALIAS_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_alias_data(self):
        with open(ALIAS_FILE, 'w') as f:
            json.dump(self.alias_data, f, indent=4)

    async def cog_check(self, ctx):
        return ctx.message.content.startswith(",alias")

    @commands.command(name="alias-add")
    async def alias_add(self, ctx, alias: str, *, command: str):
        """Adds an alias for a command (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("Only administrators can add aliases.")
            return

        guild_id = str(ctx.guild.id)

        if guild_id not in self.alias_data:
            self.alias_data[guild_id] = {}

        if alias in self.alias_data[guild_id]:
            await ctx.send("Sorry, that alias is already being used.")
            return

        self.alias_data[guild_id][alias] = command
        self.save_alias_data()
        await ctx.send(f"Alias `{alias}` added for command `{command}`.")

    @commands.command(name="alias-remove")
    async def alias_remove(self, ctx, alias: str):
        """Removes an alias (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("Only administrators can remove aliases.")
            return

        guild_id = str(ctx.guild.id)

        if guild_id not in self.alias_data or alias not in self.alias_data[guild_id]:
            await ctx.send("Alias not found.")
            return

        del self.alias_data[guild_id][alias]
        self.save_alias_data()
        await ctx.send(f"Alias `{alias}` removed.")

    @commands.command(name="alist")
    async def alias_list(self, ctx):
        """Lists all aliases with pagination buttons"""
        guild_id = str(ctx.guild.id)

        if guild_id not in self.alias_data or not self.alias_data[guild_id]:
            await ctx.send("No aliases set for this server.")
            return

        aliases = self.alias_data[guild_id]
        entries = [f"`{alias}` invokes `{command}`" for alias, command in aliases.items()]
        pages = [entries[i:i+10] for i in range(0, len(entries), 10)]
        current_page = 0

        embed = discord.Embed(
            title="Aliases",
            description="\n".join(pages[current_page]),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Page {current_page + 1} of {len(pages)}")
        message = await ctx.send(embed=embed)

        class Paginator(discord.ui.View):
            def __init__(self, *, timeout=60):
                super().__init__(timeout=timeout)
                self.current_page = current_page

            @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
            async def previous_page(self, button: discord.ui.Button, interaction: discord.Interaction):
                if self.current_page > 0:
                    self.current_page -= 1
                    embed.description = "\n".join(pages[self.current_page])
                    embed.set_footer(text=f"Page {self.current_page + 1} of {len(pages)}")
                    await interaction.response.edit_message(embed=embed)

            @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
            async def next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
                if self.current_page < len(pages) - 1:
                    self.current_page += 1
                    embed.description = "\n".join(pages[self.current_page])
                    embed.set_footer(text=f"Page {self.current_page + 1} of {len(pages)}")
                    await interaction.response.edit_message(embed=embed)

        await message.edit(view=Paginator())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return

        guild_id = str(message.guild.id)
        content = message.content

        alias = content.split()[0].lstrip(",")
        
        if guild_id in self.alias_data and alias in self.alias_data[guild_id]:
            command_name = self.alias_data[guild_id][alias]
            command_message = "," + command_name + content[len(alias)+1:]
            message.content = command_message
            await self.bot.process_commands(message)


async def setup(bot):
    await bot.add_cog(Alias(bot))
