import re
from datetime import datetime
from typing import Optional

from aiohttp import ClientSession
from discord import Color
from discord.ext.commands import CommandError
from pydantic import BaseModel, Field
from typing_extensions import Self
from yarl import URL

from core.client.context import Context
from pydantic import BaseModel, Field

PATTERN = {
    "btc": r"^[0-9a-fA-F]{64}$",
    "eth": r"^0x[0-9a-fA-F]{64}$",
    "ltc": r"^[0-9a-fA-F]{64}$",
    "doge": r"^[0-9a-fA-F]{64}$"
}

class Transaction(BaseModel):
    id: str = Field(..., alias="hash")
    currency: str
    created_at: datetime = Field(..., alias="received")
    confirmations: int
    from_address: str
    to_address: str
    amount: int
    fee: int


async def usd_price(session: ClientSession, currency: str) -> float:
    """
    Fetch the current USD price of a currency.
    """
    async with session.get(
        URL.build(
            scheme="https",
            host="min-api.cryptocompare.com",
            path="/data/price",
            query={
                "fsym": currency.upper(),
                "tsyms": "USD",
            },
        ),
    ) as response:
        if response.status != 200:
            return 0.0
            
        data = await response.json()
        return float(data.get("USD", 0.0))


class Transaction(BaseModel):
    id: str = Field(..., alias="hash")
    currency: str
    created_at: datetime = Field(..., alias="received")
    confirmations: int
    from_address: str
    to_address: str
    amount: int
    fee: int
    outputs: list = []

    @property
    def url(self) -> str:
        if self.currency == "LTC":
            return f"https://live.blockcypher.com/ltc/tx/{self.id}"

        return f"https://www.blockchain.com/explorer/transactions/{self.currency.lower()}/{self.id}"

    @property
    def color(self) -> Color:
        return Color.red() if self.confirmations <= 0 else Color.green()

    @classmethod
    async def fetch(cls, session: ClientSession, currency: str, txid: str) -> Optional[Transaction]:
        """Fetch transaction details from blockchain.info"""
        
        networks = {
            "BTC": "btc/main",
            "LTC": "ltc/main",
            "DOGE": "doge/main"
        }
        
        if not currency:
            if txid.startswith("0x"):
                currency = "ETH"
            elif len(txid) == 64: 
                for curr in networks:
                    async with session.get(f"https://api.blockcypher.com/v1/{networks[curr]}/txs/{txid}") as response:
                        if response.status == 200:
                            currency = curr
                            break
            
        if currency in networks:
            async with session.get(f"https://api.blockcypher.com/v1/{networks[currency]}/txs/{txid}") as response:
                if response.status != 200:
                    return None
                    
                data = await response.json()
                
                return cls(
                    hash=data["hash"],
                    currency=currency,
                    received=datetime.fromisoformat(data["received"].replace('Z', '+00:00')),
                    confirmations=data.get("confirmations", 0),
                    from_address=data["inputs"][0].get("addresses", ["Unknown"])[0],
                    to_address=data["outputs"][0].get("addresses", ["Unknown"])[0],
                    amount=sum(out.get("value", 0) for out in data["outputs"]),
                    fee=data.get("fees", 0),
                    outputs=data["outputs"]
                )

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        sliced = argument.split(":")
        if len(sliced) == 2:
            tx_type, id = sliced
            tx = await cls.fetch(
                ctx.bot.session,
                tx_type.upper(),
                id,
            )
            if tx:
                return tx
            
        for tx_type in ["BTC", "LTC", "DOGE", "ETH"]:
            tx = await cls.fetch(
                ctx.bot.session,
                tx_type,
                argument,
            )
            if tx:
                return tx

        raise CommandError("That doesn't look like a valid **transaction ID**!")

        for tx_type, pattern in PATTERN.items():
            if match := re.search(pattern, argument):
                tx = await cls.fetch(
                    ctx.bot.session,
                    tx_type,
                    match.group(),
                )
                if tx:
                    return tx

        raise CommandError("That doesn't look like a valid **transaction ID**!")
