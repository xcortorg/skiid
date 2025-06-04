from .emojitools import EmojiTools


async def setup(bot):
    await bot.add_cog(EmojiTools(bot))
