import asyncio
from system.marly import Marly
import gc

async def main():
    marly = None
    try:
        gc.enable()
        marly = Marly()
        await marly.start()
    except KeyboardInterrupt:
        if marly:
            await marly.close()
    finally:
        if marly:
            await marly.close()

if __name__ == "__main__":
    asyncio.run(main())