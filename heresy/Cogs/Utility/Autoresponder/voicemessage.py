import discord
from discord.ext import commands

class VoiceMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listens for specific phrases in messages and sends an MP3 file."""
        if message.author.bot:
            return

        trigger_phrases = ["nobody cares", "no one cares", "idc"]

        if any(phrase in message.content.lower() for phrase in trigger_phrases):
            file_path = "C:\\Users\\fnafl\\Downloads\\Heresy v2\\Assets\\MP3\\nobody cares nigga.mp3"

            await message.channel.send(
                file=discord.File(file_path, filename="VoiceMessage.mp3"),
                content="",
            )

async def setup(bot):
    await bot.add_cog(VoiceMessage(bot))
