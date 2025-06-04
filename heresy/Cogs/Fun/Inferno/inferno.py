import discord
from discord.ext import commands
from discord.ui import View, Button

class InfernoView(View):
    def __init__(self, author, custom_emojis, start_circle=0):
        super().__init__(timeout=60)  # Interaction lasts 60 seconds
        self.author = author
        self.current_circle = start_circle
        self.custom_emojis = custom_emojis
        self.circles = [
            {
                "name": "First Circle: Limbo",
                "description": "Dante’s First Circle of Hell is resided by virtuous non-Christians and unbaptized pagans who are punished with eternity in an inferior form of Heaven. They live in a castle with seven gates which symbolize the seven virtues. Here, Dante sees many prominent people from classical antiquity such as Homer, Socrates, Aristotle, Cicero, Hippocrates and Julius Caesar."
            },
            {
                "name": "Second Circle: Lust",
                "description": "In the Second Circle of Hell, Dante and his companion Virgil find people who were overcome by lust. They are punished by being blown violently back and forth by strong winds, preventing them to find peace and rest. Strong winds symbolize the restlessness of a person who is led by desire for fleshly pleasures. Again, Dante sees many notable people from history and mythology including Cleopatra, Tristan, Helen of Troy and others who were adulterous during their lifetime."
            },
            {
                "name": "Third Circle: Gluttony",
                "description": "When reaching the Third Circle of Hell, Dante and Virgil find souls of gluttons who are overlooked by a worm-monster Cerberus. Sinners in this circle of Hell are punished by being forced to lie in a vile slush that is produced by never ending icy rain. The vile slush symbolizes personal degradation of one who overindulges in food, drink and other worldly pleasures, while the inability to see others lying nearby represents the gluttons’ selfishness and coldness. Here, Dante speaks to a character called Ciacco who also tells him that the Guelphs (a fraction supporting the Pope) will defeat and expel the Ghibellines (a fraction supporting the Emperor to which Dante adhered) from Florence which happened in 1302, before the poem was written (after 1308)."
            },
            {
                "name": "Fourth Circle: Greed",
                "description": "In the Fourth Circle of Hell, Dante and Virgil see the souls of people who are punished for greed. They are divided into two groups – those who hoarded possessions and those who lavishly spent it – jousting. They use great weights as a weapon, pushing it with their chests which symbolizes their selfish drive for fortune during lifetime. The two groups that are guarded by a character called Pluto (probably the ancient Greek ruler of the underworld) are so occupied with their activity that the two poets don’t try to speak to them. Here, Dante says to see many clergymen including cardinals and popes."
            },
            {
                "name": "Fifth Circle: Wrath",
                "description": "The Fifth Circle of Hell is where the wrathful and sullen are punished for their sins. Transported on a boat by Phlegyas, Dante and Virgil see the wrathful fighting each other on the surface of the river Styx and the sullen gurgling beneath the surface of the water. Again, the punishment reflects the type of the sin committed during lifetime. While passing through, the poets are approached by Filippo Argenti, a prominent Florentine politician who confiscated Dante’s property after his expulsion from Florence."
            },
            {
                "name": "Sixth Circle: Kybalion",
                "description": "When reaching the Sixth Circle of Hell, Dante and Virgil see heretics who are condemned to eternity in flaming tombs. Here, Dante talks with a couple of Florentines – Farinata degli Uberti and Cavalcante de’ Cavalcanti – but he also sees other notable historical figures including the ancient Greek philosopher Epicurus, Holy Roman Emperor Frederick II and Pope Anastasius II. The latter, however, is according to some modern scholars condemned by Dante as heretic by a mistake. Instead, as some scholars argue, the poet probably meant the Byzantine Emperor Anastasius I."
            },
            {
                "name": "Seventh Circle: Violence",
                "description": "The Seventh Circle of Hell is divided into three rings. The Outer Ring houses murderers and others who were violent to other people and property. Here, Dante sees Alexander the Great (disputed), Dionysius I of Syracuse, Guy de Montfort and many other notable historical and mythological figures such as the Centaurus, sank into a river of boiling blood and fire. In the Middle Ring, the poet sees suicides who have been turned into trees and bushes which are fed upon by harpies. But he also sees here profligates, chased and torn to pieces by dogs. In the Inner Ring are blasphemers and sodomites, residing in a desert of burning sand and burning rain falling from the sky."
            },
            {
                "name": "Eighth Circle: Fraud",
                "description": "The Eight Circle of Hell is resided by the fraudulent. Dante and Virgil reach it on the back of Geryon, a flying monster with different natures, just like the fraudulent. This circle of Hell is divided into 10 Bolgias or stony ditches with bridges between them. In Bolgia 1, Dante sees panderers and seducer. In Bolgia 2 he finds flatterers. After crossing the bridge to Bolgia 3, he and Virgil see those who are guilty of simony. After crossing another bridge between the ditches to Bolgia 4, they find sorcerers and false prophets. In Bolgia 5 are housed corrupt politicians, in Bolgia 6 are hypocrites and in the remaining 4 ditches, Dante finds hypocrites (Bolgia 7), thieves (Bolgia 7), evil counselors and advisers (Bolgia 8), divisive individuals (Bolgia 9) and various falsifiers such as alchemists, perjurers and counterfeits (Bolgia 10)."
            },
            {
                "name": "Ninth Circle: Treachery",
                "description": "The last Ninth Circle of Hell is divided into 4 Rounds according to the seriousness of the sin though all residents are frozen in an icy lake. Those who committed more severe sin are deeper within the ice. Each of the 4 Rounds is named after an individual who personifies the sin. Thus Round 1 is named Caina after Cain who killed his brother Abel, Round 2 is named Antenora after Anthenor of Troy who was Priam’s counselor during the Trojan War, Round 3 is named Ptolomaea after Ptolemy (son of Abubus), while Round 4 is named Judecca after Judas Iscariot, the apostle who betrayed Jesus with a kiss."
            }
        ]

    def get_embed(self):
        """Generate the embed for the current circle."""
        circle = self.circles[self.current_circle]
        embed = discord.Embed(
            title=circle["name"],
            description=circle["description"],
            color=discord.Color.dark_red()
        )
        embed.set_footer(
            text=f"Circle {self.current_circle + 1}/{len(self.circles)}"
        )
        return embed

    async def update_message(self, interaction):
        """Update the embed and view on interaction."""
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="<:left:1307448382326968330>", style=discord.ButtonStyle.primary)
    async def left_button(self, interaction: discord.Interaction, button: Button):
        """Handle the left button interaction."""
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You can't interact with this embed.", ephemeral=True)
            return
        if self.current_circle > 0:
            self.current_circle -= 1
            await self.update_message(interaction)

    @discord.ui.button(emoji="<:cancel:1307448502913204294>", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        """Handle the close button interaction."""
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You can't interact with this embed.", ephemeral=True)
            return
        await interaction.response.edit_message(content="Embed closed.", embed=None, view=None)

    @discord.ui.button(emoji="<:right:1307448399624405134>", style=discord.ButtonStyle.primary)
    async def right_button(self, interaction: discord.Interaction, button: Button):
        """Handle the right button interaction."""
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You can't interact with this embed.", ephemeral=True)
            return
        if self.current_circle < len(self.circles) - 1:
            self.current_circle += 1
            await self.update_message(interaction)


class InfernoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="inferno")
    async def inferno(self, ctx, *, circle_name=None):
        """
        Display Dante's Nine Circles of Hell.
        Use a circle name to start on that circle (e.g., `,inferno Kybalion`).
        """
        custom_emojis = {
            "left": "<:left:1307448382326968330>",
            "right": "<:right:1307448399624405134>",
            "close": "<:cancel:1307448502913204294>"
        }

        # Match the circle name (case insensitive)
        start_circle = 0  # Default to the first circle
        if circle_name:
            for i, circle in enumerate([
                "Limbo", "Lust", "Gluttony", "Greed", "Wrath", "Kybalion", "Violence", "Fraud", "Treachery"
            ]):
                if circle_name.lower() == circle.lower():
                    start_circle = i
                    break
            else:
                await ctx.send(f"Circle `{circle_name}` not found. Showing the first circle instead.")
        
        view = InfernoView(ctx.author, custom_emojis, start_circle)
        embed = view.get_embed()
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(InfernoCog(bot))
