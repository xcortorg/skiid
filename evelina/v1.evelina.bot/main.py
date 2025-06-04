import warnings

from modules.evelinabot import Evelina

bot = Evelina()
warnings.simplefilter('ignore', DeprecationWarning)

if __name__ == "__main__":
    bot.run()