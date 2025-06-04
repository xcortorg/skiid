import asyncio

from core.Mono import Mono

if __name__ == "__main__":
    bot = Mono()
    asyncio.run(bot.start_bot())
