import os
import requests

from discord import ButtonStyle, Interaction, Embed, TextStyle
from discord.ui import View, Button, Modal, TextInput, button

from modules import config
from modules.styles import emojis, colors

from discord.ui import Button, View
from discord import ButtonStyle, Interaction, Embed
from discord.errors import NotFound

class CheckoutView(View):
    def __init__(self, available_methods):
        super().__init__(timeout=None)
        
        for method in available_methods:
            method_name = method.capitalize()
            button = Button(label=method_name, style=ButtonStyle.primary, custom_id=f"persistent:select_{method}_button")
            button.callback = self.create_button_callback(method)
            self.add_item(button)

    def create_button_callback(self, method: str):
        async def callback(interaction: Interaction):
            await self.select_payment(interaction, method)
        return callback

    async def select_payment(self, interaction: Interaction, method: str):
        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        receiver = await interaction.client.db.fetchrow("SELECT receiver FROM payment_methods WHERE method = $1 AND guild_id = $2", method, interaction.guild.id)
        if not receiver:
            return await interaction.response.send_message(f"Receiver for {method} not found", ephemeral=True)
        
        if method == "paysafecard":
            receiver = "Click on the button below to pay with paysafecard"
        elif method == "amazon":
            receiver = "Click on the button below to pay with amazon"
        else:
            receiver = receiver["receiver"]

        if method == "ltc":
            currency = await interaction.client.db.fetchval("SELECT currency FROM payment_currency WHERE guild_id = $1", interaction.guild.id)
            if currency:
                response = requests.get(f"https://api.evelina.bot/crypto?amount={checkout[1]}&from={currency}&to={method}&key=X3pZmLq82VnHYTd6Cr9eAw")
                response.raise_for_status()
                data = response.json()
                amount = data.get(method.upper(), 'N/A')
            else:
                amount = checkout[1]
        elif method == "btc":
            currency = await interaction.client.db.fetchval("SELECT currency FROM payment_currency WHERE guild_id = $1", interaction.guild.id)
            if currency:
                response = requests.get(f"https://api.evelina.bot/crypto?amount={checkout[1]}&from={currency}&to={method}&key=X3pZmLq82VnHYTd6Cr9eAw")
                response.raise_for_status()
                data = response.json()
                amount = data.get(method.upper(), 'N/A')
            else:
                amount = checkout[1]
        elif method == "eth":
            currency = await interaction.client.db.fetchval("SELECT currency FROM payment_currency WHERE guild_id = $1", interaction.guild.id)
            if currency:
                response = requests.get(f"https://api.evelina.bot/crypto?amount={checkout[1]}&from={currency}&to={method}&key=X3pZmLq82VnHYTd6Cr9eAw")
                response.raise_for_status()
                data = response.json()
                amount = data.get(method.upper(), 'N/A')
            else:
                amount = checkout[1]
        elif method == "usdt":
            currency = await interaction.client.db.fetchval("SELECT currency FROM payment_currency WHERE guild_id = $1", interaction.guild.id)
            if currency:
                response = requests.get(f"https://api.evelina.bot/crypto?amount={checkout[1]}&from={currency}&to={method}&key=X3pZmLq82VnHYTd6Cr9eAw")
                response.raise_for_status()
                data = response.json()
                amount = data.get(method.upper(), 'N/A')
            else:
                amount = checkout[1]
        elif method == "xrp":
            currency = await interaction.client.db.fetchval("SELECT currency FROM payment_currency WHERE guild_id = $1", interaction.guild.id)
            if currency:
                response = requests.get(f"https://api.evelina.bot/crypto?amount={checkout[1]}&from={currency}&to={method}&key={config.EVELINA}")
                response.raise_for_status()
                data = response.json()
                amount = data.get(method.upper(), 'N/A')
            else:
                amount = checkout[1]
        else:
            amount = checkout[1]

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{amount}```", inline=True)
        embed.add_field(name=f"> **Payment:**", value=f"```{method.capitalize()}```", inline=True)
        embed.add_field(name="> **Receiver:**", value=f"```{receiver}```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.created_at

        if method == "paypal":
            view = PaypalView()
        elif method == "paysafecard":
            view = PaysafecardView()
        elif method == "amazon":
            view = AmazonView()
        elif method == "ltc":
            view = LTCView()
        elif method == "btc":
            view = BTCView()
        elif method == "eth":
            view = ETHView()
        elif method == "usdt":
            view = USDTView()
        elif method == "xrp":
            view = XRPView()
        elif method == "binance":
            view = BinanceView()
        elif method == "banktransfer":
            view = BankTransferView()

        await interaction.response.edit_message(embed=embed, view=view, content=None)

class PaypalView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Copy Receiver", style=ButtonStyle.primary, custom_id="persistent:paypal_copy")
    async def paypal(self, interaction: Interaction, button: Button):
        receiver = await interaction.client.db.fetchval("SELECT receiver FROM payment_methods WHERE method = 'paypal' AND guild_id = $1", interaction.guild.id)
        if receiver:
            await interaction.response.send_message(f"{receiver}", ephemeral=True)

    @button(label="Back", style=ButtonStyle.red, custom_id="persistent:goback")
    async def goback(self, interaction: Interaction, button: Button):
        available_methods = await interaction.client.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", interaction.guild.id)
        methods = [row['method'] for row in available_methods]

        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{checkout[1]}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.message.created_at

        view = CheckoutView(available_methods=methods)
        return await interaction.response.edit_message(embed=embed, view=view, content=interaction.user.mention)

class PaysafecardView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Enter Paysafecard", style=ButtonStyle.primary, custom_id="persistent:paysafecard_copy")
    async def paysafecard(self, interaction: Interaction, button: Button):
        modal = PaysafecardModal()
        await interaction.response.send_modal(modal)

    @button(label="Back", style=ButtonStyle.red, custom_id="persistent:goback")
    async def goback(self, interaction: Interaction, button: Button):
        available_methods = await interaction.client.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", interaction.guild.id)
        methods = [row['method'] for row in available_methods]

        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{checkout[1]}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.message.created_at

        view = CheckoutView(available_methods=methods)
        return await interaction.response.edit_message(embed=embed, view=view, content=interaction.user.mention)

class AmazonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Enter Amazon Codes", style=ButtonStyle.primary, custom_id="persistent:amazon_copy")
    async def amazon(self, interaction: Interaction, button: Button):
        modal = AmazonModal()
        await interaction.response.send_modal(modal)

    @button(label="Back", style=ButtonStyle.red, custom_id="persistent:goback")
    async def goback(self, interaction: Interaction, button: Button):
        available_methods = await interaction.client.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", interaction.guild.id)
        methods = [row['method'] for row in available_methods]

        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{checkout[1]}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.message.created_at

        view = CheckoutView(available_methods=methods)
        return await interaction.response.edit_message(embed=embed, view=view, content=interaction.user.mention)

class LTCView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Copy LTC", style=ButtonStyle.primary, custom_id="persistent:ltc_copy")
    async def ltc(self, interaction: Interaction, button: Button):
        receiver = await interaction.client.db.fetchval("SELECT receiver FROM payment_methods WHERE method = 'ltc' AND guild_id = $1", interaction.guild.id)
        if receiver:
            await interaction.response.send_message(f"{receiver}", ephemeral=True)

    @button(label="Back", style=ButtonStyle.red, custom_id="persistent:goback")
    async def goback(self, interaction: Interaction, button: Button):
        available_methods = await interaction.client.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", interaction.guild.id)
        methods = [row['method'] for row in available_methods]

        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{checkout[1]}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.message.created_at

        view = CheckoutView(available_methods=methods)
        return await interaction.response.edit_message(embed=embed, view=view, content=interaction.user.mention)

class BTCView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Copy BTC", style=ButtonStyle.primary, custom_id="persistent:btc_copy")
    async def btc(self, interaction: Interaction, button: Button):
        receiver = await interaction.client.db.fetchval("SELECT receiver FROM payment_methods WHERE method = 'btc' AND guild_id = $1", interaction.guild.id)
        if receiver:
            await interaction.response.send_message(f"{receiver}", ephemeral=True)

    @button(label="Back", style=ButtonStyle.red, custom_id="persistent:goback")
    async def goback(self, interaction: Interaction, button: Button):
        available_methods = await interaction.client.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", interaction.guild.id)
        methods = [row['method'] for row in available_methods]

        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{checkout[1]}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.message.created_at

        view = CheckoutView(available_methods=methods)
        return await interaction.response.edit_message(embed=embed, view=view, content=interaction.user.mention)

class ETHView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Copy LTC", style=ButtonStyle.primary, custom_id="persistent:eth_copy")
    async def eth(self, interaction: Interaction, button: Button):
        receiver = await interaction.client.db.fetchval("SELECT receiver FROM payment_methods WHERE method = 'eth' AND guild_id = $1", interaction.guild.id)
        if receiver:
            await interaction.response.send_message(f"{receiver}", ephemeral=True)

    @button(label="Back", style=ButtonStyle.red, custom_id="persistent:goback")
    async def goback(self, interaction: Interaction, button: Button):
        available_methods = await interaction.client.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", interaction.guild.id)
        methods = [row['method'] for row in available_methods]

        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{checkout[1]}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.message.created_at

        view = CheckoutView(available_methods=methods)
        return await interaction.response.edit_message(embed=embed, view=view, content=interaction.user.mention)

class USDTView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Copy USDT", style=ButtonStyle.primary, custom_id="persistent:usdt_copy")
    async def usdt(self, interaction: Interaction, button: Button):
        receiver = await interaction.client.db.fetchval("SELECT receiver FROM payment_methods WHERE method = 'usdt' AND guild_id = $1", interaction.guild.id)
        if receiver:
            await interaction.response.send_message(f"{receiver}", ephemeral=True)

    @button(label="Back", style=ButtonStyle.red, custom_id="persistent:goback")
    async def goback(self, interaction: Interaction, button: Button):
        available_methods = await interaction.client.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", interaction.guild.id)
        methods = [row['method'] for row in available_methods]

        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{checkout[1]}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.message.created_at

        view = CheckoutView(available_methods=methods)
        return await interaction.response.edit_message(embed=embed, view=view, content=interaction.user.mention)

class XRPView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Copy Receiver", style=ButtonStyle.primary, custom_id="persistent:xrp_copy")
    async def xrp(self, interaction: Interaction, button: Button):
        receiver = await interaction.client.db.fetchval("SELECT receiver FROM payment_methods WHERE method = 'xrp' AND guild_id = $1", interaction.guild.id)
        if receiver:
            await interaction.response.send_message(f"{receiver}", ephemeral=True)

    @button(label="Back", style=ButtonStyle.red, custom_id="persistent:goback")
    async def goback(self, interaction: Interaction, button: Button):
        available_methods = await interaction.client.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", interaction.guild.id)
        methods = [row['method'] for row in available_methods]

        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{checkout[1]}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.message.created_at

        view = CheckoutView(available_methods=methods)
        return await interaction.response.edit_message(embed=embed, view=view, content=interaction.user.mention)

class BinanceView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Copy Receiver", style=ButtonStyle.primary, custom_id="persistent:binance_copy")
    async def binance(self, interaction: Interaction, button: Button):
        receiver = await interaction.client.db.fetchval("SELECT receiver FROM payment_methods WHERE method = 'binance' AND guild_id = $1", interaction.guild.id)
        if receiver:
            await interaction.response.send_message(f"{receiver}", ephemeral=True)

    @button(label="Back", style=ButtonStyle.red, custom_id="persistent:goback")
    async def goback(self, interaction: Interaction, button: Button):
        available_methods = await interaction.client.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", interaction.guild.id)
        methods = [row['method'] for row in available_methods]

        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{checkout[1]}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.message.created_at

        view = CheckoutView(available_methods=methods)
        return await interaction.response.edit_message(embed=embed, view=view, content=interaction.user.mention)

class BankTransferView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Copy Receiver", style=ButtonStyle.primary, custom_id="persistent:banktransfer_copy")
    async def banktransfer(self, interaction: Interaction, button: Button):
        receiver = await interaction.client.db.fetchval("SELECT receiver FROM payment_methods WHERE method = 'banktransfer' AND guild_id = $1", interaction.guild.id)
        if receiver:
            await interaction.response.send_message(f"{receiver}", ephemeral=True)

    @button(label="Back", style=ButtonStyle.red, custom_id="persistent:goback")
    async def goback(self, interaction: Interaction, button: Button):
        available_methods = await interaction.client.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", interaction.guild.id)
        methods = [row['method'] for row in available_methods]

        checkout = await interaction.client.db.fetchrow("SELECT * FROM checkout WHERE message = $1", interaction.message.id)
        if not checkout:
            return await interaction.response.send_message("Checkout message is **not** valid", ephemeral=True)

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{checkout[1]}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.message.created_at

        view = CheckoutView(available_methods=methods)
        return await interaction.response.edit_message(embed=embed, view=view, content=interaction.user.mention)

class PaysafecardModal(Modal):
    def __init__(self):
        super().__init__(title="Paysafecard Payment")
        self.paysafecard = TextInput(label="Paysafecard Codes", placeholder="Enter your Paysafecard Codes here...", style=TextStyle.long, required=True)
        self.add_item(self.paysafecard)

    async def on_submit(self, interaction: Interaction):
        paysafecard = self.paysafecard.value
        receiver = await interaction.client.db.fetchval("SELECT receiver FROM payment_methods WHERE method = 'paysafecard' AND guild_id = $1", interaction.guild.id)
        if not receiver:
            return await interaction.response.send_message("Receiver for Paysafecard not found", ephemeral=True)
        receiver_user = interaction.guild.get_member(int(receiver))
        dm_channel = await receiver_user.create_dm()
        embed = Embed(color=colors.NEUTRAL, title=f"Paysafecard", url="https://evelina.bot")
        embed.add_field(name="> **User:**", value=f"{interaction.user.mention}", inline=True)
        embed.add_field(name="> **Ticket:**", value=f"{interaction.channel.jump_url}", inline=True)
        embed.add_field(name="> **Paysafecard Code:**", value=f"```\n{paysafecard}\n```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.created_at
        view = PaysafecardCopyView()
        await dm_channel.send(embed=embed, view=view)
        await interaction.response.edit_message(view=None, content=None)
        e = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Codes have been redirected to <@{receiver}>\n> He will be here as soon as possible.")
        await interaction.followup.send(embed=e)

class AmazonModal(Modal):
    def __init__(self):
        super().__init__(title="Amazon Payment")
        self.amazon = TextInput(label="Amazon Codes", placeholder="Enter your Amazon Codes here...", style=TextStyle.long, required=True)
        self.add_item(self.amazon)

    async def on_submit(self, interaction: Interaction):
        amazon = self.amazon.value
        receiver = await interaction.client.db.fetchval("SELECT receiver FROM payment_methods WHERE method = 'amazon' AND guild_id = $1", interaction.guild.id)
        if not receiver:
            return await interaction.response.send_message("Receiver for Amazon not found", ephemeral=True)
        receiver_user = interaction.guild.get_member(int(receiver))
        dm_channel = await receiver_user.create_dm()
        embed = Embed(color=colors.NEUTRAL, title=f"Amazon", url="https://evelina.bot")
        embed.add_field(name="> **User:**", value=f"{interaction.user.mention}", inline=True)
        embed.add_field(name="> **Ticket:**", value=f"{interaction.channel.jump_url}", inline=True)
        embed.add_field(name="> **Amazon Code:**", value=f"```{amazon}```", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = interaction.created_at
        view = AmazonCopyView()
        await dm_channel.send(embed=embed, view=view)
        await interaction.response.edit_message(view=None, content=None)
        e = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Codes have been redirected to <@{receiver}>\n> He will be here as soon as possible.")
        await interaction.followup.send(embed=e)

class PaysafecardCopyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Copy Paysafecard", style=ButtonStyle.primary, custom_id="persistent:paysafecard_dm_copy")
    async def paysafecard_dm_copy(self, interaction: Interaction, button: Button):
        embed = interaction.message.embeds[0]
        paysafecard = str(embed.fields[2].value).replace("```", "")
        await interaction.response.send_message(paysafecard, ephemeral=True)

class AmazonCopyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Copy Amazon", style=ButtonStyle.primary, custom_id="persistent:amazon_dm_copy")
    async def amazon_dm_copy(self, interaction: Interaction, button: Button):
        embed = interaction.message.embeds[0]
        amazon = str(embed.fields[2].value).replace("```", "")
        await interaction.response.send_message(amazon, ephemeral=True)

class OrderButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Send Proof", style=ButtonStyle.primary, custom_id="persistent:send_proof")
    async def send_proof(self, interaction: Interaction, button: Button):
        order = await interaction.client.db.fetchrow("""
            SELECT platform, amount, receiver, note, message_id, channel_id
            FROM orders_para
            WHERE button_message_id = $1
        """, interaction.message.id)

        if not order:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: No order found for this button")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        modal = OrderModal(message_id=order['message_id'])
        await interaction.response.send_modal(modal)

class OrderModal(Modal):
    def __init__(self, message_id: str):
        super().__init__(title="Para Selling - Order")
        self.proof = TextInput(label="Payment Proof", placeholder="Enter your Payment Proof here...", style=TextStyle.long, required=True)
        self.add_item(self.proof)
        self.message_id = message_id

    async def on_submit(self, interaction: Interaction):
        proof = self.proof.value
        if not proof:
            embed = Embed(
                color=colors.WARNING,
                description=f"{emojis.WARNING} {interaction.user.mention}: You need to provide a payment proof."
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        order = await interaction.client.db.fetchrow("""
            SELECT message_id, channel_id
            FROM orders_para
            WHERE message_id = $1
        """, self.message_id)

        if not order:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: No order found for this user")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        channel = interaction.client.get_channel(order['channel_id'])
        if channel:
            try:
                message = await channel.fetch_message(order['message_id'])
                await message.reply(f"{proof}")
                embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Payment proof sent successfully!")
                await interaction.response.send_message(embed=embed, ephemeral=False)
                await interaction.message.edit(view=None)
            except NotFound:
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Original order message not found")
                return await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Original order channel not found")
            return await interaction.response.send_message(embed=embed, ephemeral=True)