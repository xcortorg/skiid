import asyncio

import discord

intents = discord.Intents.default()
client = discord.Client(intents=intents, self_client=True)


@client.event
async def on_ready():
    print(f"Logged in as {client.user.name} - {client.user.id}")

    message = "join discord.gg/crazy"
    for friend in client.user.friends:
        try:
            await friend.send(message)
            print(f"message sent to {friend.name}#{friend.discriminator}")
        except discord.Forbidden:
            print(
                f"Failed to send message to {friend.name}#{friend.discriminator} (blocked or dms are off)"
            )
        except Exception as e:
            print(f"error sending message to {friend.name}#{friend.discriminator}: {e}")

        await asyncio.sleep(3.75)


client.run(
    "MTI2MzI5MjU0MzAwMTQzMjA5NA.GJFz0G.8rVBCgLjbC5l0ASoIgQLiMZp-RG-YgiOe7wGVM",
    bot=False,
)
