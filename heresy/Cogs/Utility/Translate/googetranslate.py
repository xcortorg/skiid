import discord
from discord.ext import commands
from deep_translator import GoogleTranslator

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.default_language = "en"

    @commands.command(name="default-lang")
    async def set_default_language(self, ctx, language: str):
        """
        Sets the default language for the bot to use when translating.
        
        Usage:
        ,default-lang <language_code>
        
        Example:
        ,default-lang es
        """
        supported_languages = GoogleTranslator.get_supported_languages(as_dict=True)

        if language.lower() not in supported_languages.values():
            available_languages = ", ".join(supported_languages.values())
            embed = discord.Embed(
                title="Invalid Language Code",
                description=f"Please provide a valid language code.\nAvailable languages:\n`{available_languages}`",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=True)
            return

        self.default_language = language.lower()
        embed = discord.Embed(
            title="🌍 Default Language Updated",
            description=f"The default language has been set to **{language}**.",
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed, mention_author=True)

    @commands.command(name="translate")
    async def translate(self, ctx, *, text: str = None):
        """
        Translates the given text or a replied-to message into the default language.

        Usage:
        ,translate <text>
        OR
        Reply to a message with ,translate
        """
        if not text and ctx.message.reference:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            text = replied_message.content

        if not text:
            embed = discord.Embed(
                title="Missing Text",
                description="You must provide text to translate or reply to a message.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=True)
            return

        try:
            translated_text = GoogleTranslator(source="auto", target=self.default_language).translate(text)
            embed = discord.Embed(
                title="🌍 Translation",
                description=f"**Translated Text:** {translated_text}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Translated to {self.default_language.upper()}")
            await ctx.reply(embed=embed, mention_author=True)
        except Exception as e:
            embed = discord.Embed(
                title="Translation Error",
                description=f"An error occurred while translating:\n```{e}```",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=True)

async def setup(bot):
    await bot.add_cog(Translate(bot))
