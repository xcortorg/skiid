import discord
from discord.ext import commands
import random
import json
import os
from discord.ui import Button, View

class Diplodoculus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_file = "./json/user_xp.json"
        self.outcome_file = "./json/outcomes.json"
        self.user_dino_file = "./json/user_dinos.json"  # To store user's owned Diplodocus

        # Ensure the necessary files exist
        os.makedirs("./json", exist_ok=True)
        if not os.path.exists(self.xp_file):
            with open(self.xp_file, "w") as f:
                json.dump({}, f)
        
        if not os.path.exists(self.outcome_file):
            with open(self.outcome_file, "w") as f:
                json.dump([], f)

        if not os.path.exists(self.user_dino_file):
            with open(self.user_dino_file, "w") as f:
                json.dump({}, f)

    def load_xp(self):
        """Loads the user XP data."""
        with open(self.xp_file, "r") as f:
            return json.load(f)

    def save_xp(self, data):
        """Saves user XP data."""
        with open(self.xp_file, "w") as f:
            json.dump(data, f, indent=4)

    def add_xp(self, user_id, xp_amount):
        """Adds XP to a user."""
        xp_data = self.load_xp()
        xp_data[str(user_id)] = xp_data.get(str(user_id), 0) + xp_amount
        self.save_xp(xp_data)

    def calculate_level(self, xp):
        """Calculates level based on XP."""
        level = 0
        while xp >= ((level + 1) ** 2) * 50:
            level += 1
        return level

    def load_outcomes(self):
        """Loads battle outcomes from the JSON file."""
        if not os.path.exists(self.outcome_file):
            with open(self.outcome_file, "w") as f:
                json.dump([], f)  # Creates the empty file if it doesn't exist
        with open(self.outcome_file, "r") as f:
            return json.load(f)

    def save_outcomes(self, outcomes):
        """Saves battle outcomes to the JSON file."""
        with open(self.outcome_file, "w") as f:
            json.dump(outcomes, f, indent=4)

    def load_user_dinos(self):
        """Loads the user's Diplodocus ownership data."""
        with open(self.user_dino_file, "r") as f:
            return json.load(f)

    def save_user_dinos(self, data):
        """Saves the user's Diplodocus ownership data."""
        with open(self.user_dino_file, "w") as f:
            json.dump(data, f, indent=4)

    @commands.command(name="tame")
    async def tame(self, ctx):
        """Attempts to tame a Diplodoculus."""
        outcomes = [
            "Diplodoculus looks at you suspiciously and runs away. You fail to tame it.",
            "You offer Diplodoculus some food, and it considers your offer. It's a draw!",
            "Diplodoculus playfully lets you ride on its back. You win and tame it!",
            "Diplodoculus is too wild and escapes into the forest. You lose!",
            "Diplodoculus challenges you to a dance-off, and you impress it! You win!",
            "Diplodoculus isn't interested in taming today. You lose!",
        ]
        
        outcome = random.choice(outcomes)
        
        # Check if the user successfully tamed the Diplodoculus
        if "You win" in outcome:
            user_dinos = self.load_user_dinos()
            user_dinos[str(ctx.author.id)] = "Diplodoculus"
            self.save_user_dinos(user_dinos)
            embed_color = discord.Color.green()
        elif "It's a draw" in outcome:
            embed_color = discord.Color.yellow()
        else:
            embed_color = discord.Color.red()
        
        # Display outcome and add XP
        xp_reward = 10 if "win" in outcome else 5 if "draw" in outcome else 0
        self.add_xp(ctx.author.id, xp_reward)
        
        embed = discord.Embed(
            title="Tame Diplodoculus",
            description=outcome,
            color=embed_color
        )
        embed.add_field(name="XP Earned", value=f"{xp_reward} XP", inline=True)
        embed.set_thumbnail(url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="summon")
    async def summon(self, ctx):
        """Summons Diplodoculus if the user owns one."""
        user_dinos = self.load_user_dinos()
        
        if str(ctx.author.id) not in user_dinos:
            await ctx.send("You don't own a Diplodoculus, try to tame one first!")
            return
        
        summon_outcomes = [
            "Diplodoculus majestically appears, its long neck swaying gracefully.",
            "Diplodoculus stomps the ground and lets out a mighty roar!",
            "Diplodoculus emerges from the forest, carrying a bundle of leaves.",
            "Diplodoculus appears with a playful demeanor, ready for fun.",
            "Diplodoculus charges in dramatically, scattering the nearby grass.",
            "Diplodoculus gracefully swims through a nearby river to meet you.",
            "Diplodoculus winks at you and strikes a heroic pose.",
            "Diplodoculus appears with an entourage of smaller dinos.",
            "Diplodoculus munches on leaves while greeting you with a gentle nudge.",
            "Diplodoculus stands tall, blocking the sun, casting a mighty shadow."
        ]

        outcome = random.choice(summon_outcomes)
        embed = discord.Embed(
            title="Summoning Diplodoculus",
            description=outcome,
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="name")
    async def name(self, ctx, *, pet_name: str):
        """Names your Diplodocus."""
        user_dinos = self.load_user_dinos()
        
        if str(ctx.author.id) not in user_dinos:
            await ctx.send("You don't own a Diplodoculus, try to tame one first!")
            return
        
        user_dinos[str(ctx.author.id)] = pet_name
        self.save_user_dinos(user_dinos)
        await ctx.send(f"Your Diplodoculus is now named **{pet_name}**!")

    @commands.command(name="pets")
    async def pets(self, ctx):
        """Shows how many pets the user owns."""
        user_dinos = self.load_user_dinos()
        pet_count = len(user_dinos)
        
        embed = discord.Embed(
            title="Pet Count",
            description=f"You own {pet_count} Diplodocus(es)! 🦕",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command(name="battle")
    async def battle(self, ctx):
        """Starts a battle with Diplodoculus."""
        outcomes = self.load_outcomes()
        if not outcomes:
            await ctx.send("No battle outcomes available! Please add some using the `add-outcome` command.")
            return

        outcome = random.choice(outcomes)
        
        # Add XP based on outcome
        if "You win" in outcome:
            self.add_xp(ctx.author.id, 10)  # Award 10 XP for wins
            embed_color = discord.Color.green()
        elif "You lose" in outcome:
            self.add_xp(ctx.author.id, 5)  # Award 5 XP for losses
            embed_color = discord.Color.red()
        else:
            self.add_xp(ctx.author.id, 2)  # Award 2 XP for draws
            embed_color = discord.Color.yellow()

        embed = discord.Embed(
            title="Battle Outcome",
            description=outcome,
            color=embed_color
        )
        embed.add_field(name="XP Earned", value=f"{'10 XP' if 'win' in outcome else '5 XP' if 'lose' in outcome else '2 XP'}", inline=True)
        embed.set_thumbnail(url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="xp")
    async def xp(self, ctx, member: discord.Member = None):
        """Displays the user's XP and level."""
        # If no member is mentioned, default to the author
        member = member or ctx.author

        xp_data = self.load_xp()
        user_xp = xp_data.get(str(member.id), 0)
        user_level = self.calculate_level(user_xp)

        embed = discord.Embed(
            title=f"{member.name}'s XP and Level",
            color=discord.Color.green()
        )
        embed.add_field(name="XP", value=user_xp, inline=True)
        embed.add_field(name="Level", value=user_level, inline=True)
        embed.set_thumbnail(url=member.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="diplodraw")
    async def diplodraw(self, ctx):
        """Shares an ASCII art of Diplodoculus."""
        art = (
            "         🦕\n"
            "         Diplodoculus in its majestic glory!\n"
            "           \\       /            \n"
            "           ( o_o )\n"
            "           (     )\n"
            "           /     \\ "
        )
        await ctx.send(f"```{art}```")

    @commands.command(name="add-outcome")
    async def add_outcome(self, ctx, *, outcome: str):
        """Adds a new outcome to the battle outcomes."""
        # Ensure the user has the required permissions to add outcomes
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You do not have permission to add new outcomes.")
            return

        outcomes = self.load_outcomes()
        outcomes.append(outcome)
        self.save_outcomes(outcomes)

        await ctx.send(f"New outcome added: {outcome}")

    @commands.command(name="diplometer")
    async def diplodometer(self, ctx):
        """Rates how Diplodoculus-like the user is."""
        score = random.randint(1, 100)
        await ctx.send(f"{ctx.author.mention}, you are {score}% Diplodoculus!")

    @commands.command(name="1v1")
    async def one_v_one(self, ctx, opponent: discord.Member):
        """Challenges another user to a Diplodocus battle."""
        if ctx.author.id == opponent.id:
            await ctx.send("You can't 1v1 yourself!")
            return

        user_dinos = self.load_user_dinos()
        if str(ctx.author.id) not in user_dinos:
            await ctx.send("You don't own a Diplodoculus, try to tame one first!")
            return
        if str(opponent.id) not in user_dinos:
            await ctx.send(f"{opponent.mention} doesn't own a Diplodoculus!")
            return

        # Create buttons
        class ConfirmBattle(View):
            def __init__(self, author, opponent):
                super().__init__()
                self.author = author
                self.opponent = opponent

            @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
            async def yes(self, interaction: discord.Interaction, button: Button):
                if interaction.user.id != self.opponent.id:
                    await interaction.response.send_message("This challenge isn't for you!", ephemeral=True)
                    return

                battle_outcomes = [
                    f"{ctx.author.mention}'s Diplodoculus unleashes a powerful tail whip and wins!",
                    f"{opponent.mention}'s Diplodoculus dodges an attack and counters for the win!",
                    "Both Diplodocuses roar and call it a draw!",
                    f"{ctx.author.mention}'s Diplodoculus charges ahead and dominates the battlefield!",
                    f"{opponent.mention}'s Diplodoculus showcases its agility and secures victory!"
                ]
                outcome = random.choice(battle_outcomes)
                embed = discord.Embed(
                    title="Battle Outcome",
                    description=outcome,
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                self.stop()

            @discord.ui.button(label="No", style=discord.ButtonStyle.red)
            async def no(self, interaction: discord.Interaction, button: Button):
                if interaction.user.id != self.opponent.id:
                    await interaction.response.send_message("This challenge isn't for you!", ephemeral=True)
                    return
                await interaction.response.send_message(f"{opponent.mention} declined the challenge.")
                self.stop()

        embed = discord.Embed(
            title="Diplodoculus 1v1 Challenge",
            description=f"{ctx.author.mention} wants to 1v1 you, {opponent.mention}. Do you accept?",
            color=discord.Color.gold()
        )
        view = ConfirmBattle(ctx.author, opponent)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Diplodoculus(bot))
