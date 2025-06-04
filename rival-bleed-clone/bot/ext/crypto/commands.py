import orjson
import re
import asyncio

from decimal import Decimal
from discord.ext.commands import CommandError, command, group, Cog, Converter
from discord import Embed, Client, File, utils
from lib.classes.builtins import shorten
from aiohttp import ClientSession
from lib.patch.context import Context
from discord.ext.tasks import loop
from .models.coin import CryptoResponse
from typing import Optional
from io import BytesIO
from playwright.async_api import async_playwright
from lxml import html
from datetime import datetime
from math import ceil


PROXY_IP = "185.199.228.220"
USERNAME = "yxfishgz-3"
PASSWORD = "v5n82upbqy1r"
PROXY = f"http://{USERNAME}:{PASSWORD}@p.webshare.io"


class Coin(Converter):
    async def convert(self, ctx: Context, argument: str):
        async with ClientSession() as session:
            async with session.get(
                "https://api.cryptocompare.coindesk.com/asset/v1/search",
                params={
                    "search_string": argument.lower(),
                    "limit": 10,
                    "response_format": "JSON",
                },
            ) as response:
                data = await response.json()
        return data["Data"]["LIST"][0]["SYMBOL"]


class Transaction(Converter):
    async def convert(self, ctx: Context, argument: str):
        async with ClientSession() as session:
            async with session.request(
                "POST",
                "https://www.blockchain.com/explorer/search",
                json={"search": argument},
            ) as response:
                data = await response.json()


async def get_transaction(txid: str):
    async with ClientSession() as session:
        async with session.get(
            f"https://mempool.space/api/tx/{txid.replace(' ', '')}/status"
        ) as response:
            if response.status != 200:
                raise CommandError(f"`{txid.replace(' ', '')}` is an **invalid hash**")
            data = await response.json()
    return data, txid.replace(" ", "")


async def scrape_btc(browser, txid: str):
    try:
        coin = "btc"
        url = f"https://www.blockchain.com/explorer/transactions/{coin}/{txid}"
        data = {}
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(1)
        tree = html.fromstring(await page.content())
        confirmations = int(
            "".join(
                f
                for f in tree.xpath(
                    '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/div/section/div[2]/a/div/div/text()[1]'
                )[0].split(".", 1)[0]
                if f.isdigit()
            )
        )
        data["confirmations"] = confirmations
        data["total_value"] = {
            "coin": float(
                tree.xpath(
                    '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/div/section/div[1]/div[7]/div[2]/span[1]/text()'
                )[0]
            ),
            "usd": tree.xpath(
                '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/div/section/div[1]/div[7]/div[2]/span[2]/text()'
            )[0]
            .replace("•", "")
            .replace(" ", ""),
        }
        data["sender"] = {
            "address": tree.xpath(
                '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/section/div[2]/div[2]/div/div/div[1]/div[2]/div/div/div[2]/div[1]/a/div/text()'
            )[0]
        }
        data["seen"] = datetime.strptime(
            tree.xpath(
                '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/div/section/div[1]/div[3]/text()'
            )[0].replace("Broadcasted on ", "")[:-7],
            "%d %b %Y %H:%M:%S",
        )
        data["fee_info"] = {
            "vb": tree.xpath(
                '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/section/section/div[2]/div[11]/div[2]/div/div/text()'
            )[0].strip(),
            "usd": tree.xpath(
                '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/section/section/div[2]/div[10]/div[2]/div[2]/text()'
            )[0].strip(),
        }
        data["size"] = int(
            "".join(
                f
                for f in tree.xpath(
                    '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/section/section/div[2]/div[13]/div[2]/div/div/text()'
                )[0]
                if f.isdigit()
            )
        )

        data["weight"] = int(
            tree.xpath(
                '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/section/section/div[2]/div[14]/div[2]/div/div/text()'
            )[0]
        )
        data["virtual"] = ceil(data["weight"] / 4)
        await page.close()
        data["logo"] = (
            "https://www.blockchain.com/explorer/_next/static/media/btc.a6006067.png"
        )
        data["coin"] = "Bitcoin"
        return data
    except Exception:
        return None


async def scrape_eth(browser, txid: str):
    try:
        coin = "eth"
        url = f"https://www.blockchain.com/explorer/transactions/{coin}/{txid}"
        data = {}
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(1)
        tree = html.fromstring(await page.content())
        confirmations = int(
            tree.xpath(
                '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/section/section/div[2]/div[4]/div[2]/div/div/text()'
            )[0]
        )
        data["confirmations"] = confirmations
        coin_value = tree.xpath(
            '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/div/section/div[1]/div[7]/div[2]/span[1]/text()'
        )[0]
        usd_value = (
            tree.xpath(
                '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/div/section/div[1]/div[7]/div[2]/span[2]/text()'
            )[0]
            .strip("•")
            .replace(" ", "")
            .replace("•", "")
        )
        gwei = tree.xpath(
            '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/div/section/div[1]/div[7]/div[4]/span[1]/text()'
        )[0]
        fee = (
            tree.xpath(
                '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/div/section/div[1]/div[7]/div[4]/span[2]/text()'
            )[0]
            .strip("•")
            .replace(" ", "")
            .replace("•", "")
        )
        data["fee_info"] = {"gwei": f"{int(gwei[0])} gwei", "usd": fee.strip()}
        data["total_value"] = {"coin": coin_value.strip(), "usd": usd_value.strip()}
        sender_address = tree.xpath(
            '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/section/div[2]/div[2]/div/div/div[1]/div[2]/div/div/div[2]/div[1]/a/div/text()'
        )[0]
        receiver_address = tree.xpath(
            '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/section/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[2]/div[1]/a/div/text()'
        )[0]
        data["sender"] = {
            "address": sender_address,
            "url": f"https://etherscan.io/address/{sender_address}",
        }
        data["receiver"] = {
            "address": receiver_address,
            "url": f"https://etherscan.io/address/{receiver_address}",
        }
        seen = tree.xpath(
            '//*[@id="__next"]/div[2]/div[2]/main/div/div/section/div/section/div[1]/div[3]/text()'
        )[0].replace("Broadcasted on ", "")
        data["seen"] = datetime.strptime(seen[:-7], "%d %b %Y %H:%M:%S")
        await page.close()
        data["logo"] = (
            "https://www.blockchain.com/explorer/_next/static/media/eth.8b071eb3.png"
        )
        data["coin"] = "Ethereum"
        return data
    except Exception:
        return None


async def get_details(txid: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        d = await asyncio.gather(
            *[scrape_btc(browser, txid), scrape_eth(browser, txid)]
        )
        await browser.close()
    for m in d:
        if m is not None:
            return m
    return None


async def get_coin(coin: str):
    async with ClientSession() as session:
        async with session.get(
            f"https://api.cryptocompare.coindesk.com/asset/v1/metadata?asset={coin.upper()}&asset_lookup_priority=SYMBOL&quote_asset={currency.upper()}&response_format=JSON"
        ) as response:
            data = await response.json()
    return data


class BitcoinTransaction(Converter):
    async def convert(self, ctx: Context, argument: str):
        data, txid = await self.get_transaction(argument)
        if data.get("confirmed", False) is True:
            raise CommandError(
                f"The provided [hash](https://www.blockchain.com/btc/tx/{txid}) has already received at least **one confirmation**"
            )
        return txid


class Commands(Cog):
    def __init__(self, bot: Client):
        self.bot = bot
        with open("var/html/candlestick_chart.html", "r", encoding="utf-8") as file:
            self.candlestick_chart_html = file.read()
        self.binance_intervals = [
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1M",
        ]

    async def chart(
        self,
        coin: str,
        currency: Optional[str] = "USDT",
        interval: Optional[str] = "1d",
        limit: Optional[int] = 50,
    ) -> File:
        if limit > 100:
            raise CommandError("less then 125 please")

        symbol = (coin + currency).upper()
        async with ClientSession() as session:
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            async with session.get(
                url, params=params, proxy=PROXY, verify_ssl=False
            ) as response:
                data = await response.json(loads=orjson.loads)
        if isinstance(data, dict):
            raise CommandError(data.get("msg"))

        candle_data = []
        for ticker in data:
            candle_data.append(str(ticker[:5]))

        current_price = Decimal(data[-1][4]).normalize()

        replacements = {
            "HEIGHT": 512,
            "TITLE": f"{coin.upper()} / {currency.upper()} | {interval} | {current_price:,f}",
            "DATA": ",".join(candle_data),
        }

        def dictsub(m):
            return str(replacements[m.group().strip("$")])

        formatted_html = re.sub(r"\$(\S*)\$", dictsub, self.candlestick_chart_html)
        async with ClientSession() as session:
            data = {
                "html": formatted_html,
                "width": 720,
                "height": 512,
                "imageFormat": "png",
            }
            async with session.post(
                "http://localhost:3000/html", data=data
            ) as response:
                data = await response.read()
            return File(fp=BytesIO(data), filename="chart.png")

    @loop(seconds=5)
    async def check_confirmations(self):
        for row in await self.bot.db.fetch("""SELECT user_id, txid FROM subscribe"""):
            if not (user := self.bot.get_user(row.user_id)):
                continue
            data, txid = await get_transaction(row.txid)
            if data.get("confirmed", False) is True:
                await self.bot.db.execute(
                    """DELETE FROM subscribe WHERE user_id = $1 AND txid = $2""",
                    row.user_id,
                    row.txid,
                )
                self.bot.dispatch("transaction_confirmed", user, txid)

    @command(
        name="subscribe",
        description="Subscribe to a bitcoin transaction for one confirmation",
        example=",subscribe a521bnafs...",
    )
    async def subscribe(self, ctx: Context, hash: BitcoinTransaction):
        await self.bot.db.execute(
            """INSERT INTO subscribe (guild_id, channel_id, user_id, txid) VALUES($1, $2, $3, $4) ON CONFLICT(guild_id, channel_id, user_id, txid) DO NOTHING""",
            ctx.guild.id,
            ctx.channel.id,
            ctx.author.id,
            hash,
        )
        return await ctx.success(
            f"Subscribing to the given transaction [hash](https://www.blockchain.com/btc/tx/{hash}) I will let you know when it has received **a confirmation**"
        )

    @command(
        name="crypto",
        description="Checks the current price of the specified cryptocurrency",
        example=",crypto BTC",
    )
    async def crypto(self, ctx: Context, crypto: Coin):
        symbol = "$"
        try:
            data = await CryptoResponse.from_coin(crypto, "USD")
        except Exception:
            raise CommandError("The **Crypto API** returned `500` - try again later")
        file = await self.chart(crypto)
        symbol = (crypto + "USD").upper()
        async with ClientSession(
            "https://api.binance.com/api/v3/ticker/24hr",
            params={"symbol": symbol},
            proxy=PROXY,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36"
            },
        ) as response:
            data = await response.json()

        embed = Embed(
            title=f"{crypto} in USD, Cryptocurrency",
            url="https://coindesk.com/",
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embed.add_field(
            name="Price",
            value=f"{symbol}{format(round(data.Data.price, 2), ',')} USD",
            inline=True,
        )
        embed.add_field(
            name="Market Cap",
            value=f"{symbol}{data.Data.TOTAL_MKT_CAP_USD.humanize()}",
            inline=True,
        )
        embed.add_field(
            name="Last Change",
            value=f"<t:{data.Data.PRICE_USD_LAST_UPDATE_TS}:R>",
            inline=True,
        )
        embed.add_field(
            name="Daily Change",
            value=f"{symbol}{format(round(data.Data.SPOT_MOVING_24_HOUR_CHANGE_USD, 2), ',')} USD ({format(round(data.Data.SPOT_MOVING_24_HOUR_CHANGE_PERCENTAGE_USD, 1), ',')}%)",
            inline=True,
        )
        embed.add_field(
            name="Daily Highest",
            value=f"{symbol}{Decimal(data.get('highPrice')).normalize():,f} USD",
            inline=True,
        )
        embed.add_field(
            name="Daily Lowest",
            value=f"{symbol}{Decimal(data.get('lowPrice')).normalize():,f} USD",
            inline=True,
        )
        embed.set_image(url="attachment://chart.png")
        embed.set_thumbnail(url=data.Data.LOGO_URL)
        return await ctx.send(embed=embed, file=file)

    @command(
        name="transaction", description="Get information about a BTC or ETH transaction"
    )
    async def transaction(self, ctx: Context, hash: str):
        hash = hash.replace(" ", "")
        try:
            data = await get_details(hash)
            if not data:
                raise TypeError()
        except Exception:
            raise CommandError(f"`{hash}` is an **invalid hash**")
        url_base = (
            "https://etherscan.io/tx/"
            if data.get("coin", "") == "Ethereum"
            else "https://mempool.space/tx/"
        )
        embed = Embed(title=f"{hash}", url=f"{url_base}{hash}")
        embed.add_field(
            name="Confirmations", value=data.get("confirmations", 0), inline=True
        )
        embed.add_field(
            name="Total Value",
            value=f"{data['total_value']['coin']} (`{data['total_value']['usd']}`)",
            inline=True,
        )
        embed.add_field(
            name="Fee Info",
            value=f"{list(data['fee_info'].values())[0]} (`{list(data['fee_info'].values())[1]}`)",
            inline=True,
        )
        if data.get("coin", "") == "Ethereum":
            embed.add_field(
                name="Sender",
                value=f"[`{shorten(data['sender']['address'], 17)}`]({data['sender']['address']})",
                inline=True,
            )
            embed.add_field(
                name="Receiver",
                value=f"[`{shorten(data['receiver']['address'], 17)}`]({data['receiver']['address']})",
                inline=True,
            )
        else:
            embed.add_field(
                name="Virtual Size",
                value=f"{data['virtual']} / {data['weight']}",
                inline=True,
            )
            embed.add_field(name="Size Base", value=f"{data['size']} / 85", inline=True)
        embed.add_field(
            name="Last Seen",
            value=f'{utils.format_dt(data["seen"], style="D")} ({utils.format_dt(data["seen"], style="R")}',
            inline=True,
        )
        embed.set_author(name=f"{data['coin']} Transaction", icon_url=data["logo"])
        return await ctx.send(embed=embed)
