from discord.ext.commands import Cog, CommandError
from discord import User, Member, Embed, Client


class Events(Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    @Cog.listener("on_transaction_confirmed")
    async def confirmed(self, user: User, txid: str):
        try:
            await user.send(
                embed=Embed(
                    description=f"The [**transaction**](https://www.blockchain.com/btc/tx/{txid}) has received atleast **one confirmation**"
                ).set_footer(
                    text=f"{txid}",
                    icon_url="https://cdn.discordapp.com/emojis/956969145092677653.png",
                )
            )
        except Exception:
            pass
