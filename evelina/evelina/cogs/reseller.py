import discord

from discord import User, Embed
from discord.ext.commands import Cog, command, group, has_guild_permissions

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.persistent.checkout import CheckoutView

class Reseller(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
    
    @group(name="payment", invoke_without_command=True, case_insensitive=True)
    async def payment(self, ctx: EvelinaContext):
        """Manage payment methods"""
        return await ctx.create_pages()
    
    @payment.command(name="add", aliases=["create"], brief="manage guild", usage="payment add paypal payment@evelina.bot")
    @has_guild_permissions(manage_guild=True)
    async def payment_add(self, ctx: EvelinaContext, method: str, receiver: str):
        """Add a payment method to guild"""
        if method.lower() not in ["paypal", "paysafecard", "amazon", "ltc", "btc", "eth", "usdt", "xrp", "binance", "banktransfer"]:
            return await ctx.send_warning(f"Invalid payment method.\n> **Supported methods:** `PayPal`, `Paysafecard`, `Amazon`, `LTC`, `BTC`, `ETH`, `USDT`, `Binance`, `Banktransfer`")
        if method.lower() == "paysafecard":
            try:
                paysafe_user = ctx.guild.get_member(int(receiver))
            except ValueError:
                paysafe_user = None
            if paysafe_user is None:
                return await ctx.send_warning(f"User with ID **{receiver}** not found\n> **Usage:** `{ctx.clean_prefix}payment add paysafecard user.id`")
        if method.lower() == "amazon":
            try:
                amazon_user = ctx.guild.get_member(int(receiver))
            except ValueError:
                amazon_user = None
            if amazon_user is None:
                return await ctx.send_warning(f"User with ID **{receiver}** not found\n> **Usage:** `{ctx.clean_prefix}payment add amazon user.id`")
        if await self.bot.db.fetchrow("SELECT * FROM payment_methods WHERE guild_id = $1 AND method = $2", ctx.guild.id, method.lower()):
            return await ctx.send_warning(f"A payment method for **{str(method).lower()}** already exists!")
        await self.bot.db.execute("INSERT INTO payment_methods VALUES ($1, $2, $3, $4)", ctx.guild.id, method.lower(), receiver, True)
        await ctx.send_success(f"Added payment method for **{str(method).lower()}**")

    @payment.command(name="remove", aliases=["delete", "del"], brief="manage guild", usage="payment remove paypal")
    @has_guild_permissions(manage_guild=True)
    async def payment_remove(self, ctx: EvelinaContext, method: str):
        """Remove a payment method from guild"""
        if not await self.bot.db.fetchrow("SELECT * FROM payment_methods WHERE guild_id = $1 AND method = $2", ctx.guild.id, method.lower()):
            return await ctx.send_warning(f"That is **not** an existing payment method")
        await self.bot.db.execute("DELETE FROM payment_methods WHERE guild_id = $1 AND method = $2", ctx.guild.id, method.lower())
        await ctx.send_success(f"Deleted the payment method **{str(method).lower()}**")

    @payment.command(name="edit", brief="manage guild", usage="payment edit paypal payment@evelina.bot")
    @has_guild_permissions(manage_guild=True)
    async def payment_edit(self, ctx: EvelinaContext, method: str, receiver: str):
        """Edit a payment method"""
        if method.lower() not in ["paypal", "paysafecard", "ltc", "btc", "eth", "usdt", "xrp", "binance", "banktransfer"]:
            return await ctx.send_warning(f"Invalid payment method.\n> **Supported methods:** `PayPal`, `Paysafecard`, `LTC`, `BTC`, `ETH`, `USDT`, `Binance`, `Banktransfer`")
        if method.lower() == "paysafecard":
            paysafe_user = ctx.guild.get_member(int(receiver))
            if paysafe_user is None:
                return await ctx.send_warning(f"User with ID **{receiver}** not found\n> **Usage:** `{ctx.clean_prefix}payment add paysafecard user.id`")
        check = await self.bot.db.fetchrow("SELECT * FROM payment_methods WHERE guild_id = $1 AND method = $2", ctx.guild.id, method.lower())
        if not check:
            return await ctx.send_warning(f"No payment method found for **{str(method).lower()}**")
        await self.bot.db.execute("UPDATE payment_methods SET receiver = $1 WHERE guild_id = $2 AND method = $3", receiver, ctx.guild.id, method.lower())
        await ctx.send_success(f"Updated payment method for **{str(method).lower()}**")

    @payment.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def payment_reset(self, ctx: EvelinaContext):
        """Reset every payment method for this guild"""
        if not await self.bot.db.fetchrow("SELECT * FROM payment_methods WHERE guild_id = $1", ctx.guild.id):
            return await ctx.send_warning(f"There are **no** payment methods set")
        async def yes_func(interaction: discord.Interaction):
            await self.bot.db.execute("DELETE FROM payment_methods WHERE guild_id = $1", interaction.guild.id)
            await interaction.response.edit_message(embed=discord.Embed(description=f"{emojis.APPROVE} {interaction.user.mention}: Removed all **payment methods**", color=colors.SUCCESS), view=None)
        async def no_func(interaction: discord.Interaction):
            await interaction.response.edit_message(embed=discord.Embed(description=f"{emojis.DENY} {interaction.user.mention}: Payment methods deletion got canceled", color=colors.NEUTRAL), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **delete** all payment methods?", yes_func, no_func)

    @payment.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def payment_list(self, ctx: EvelinaContext):
        """View a list of every payment method in guild"""
        results = await self.bot.db.fetch("SELECT * FROM payment_methods WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"There are **no** payment methods set")
        await ctx.paginate([f"{str(result['method']).lower()} - {result['receiver']}" for result in results], title=f"Payment Methods", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon or None})

    @payment.command(name="currency", brief="manage guild", usage="payment currency eur")
    @has_guild_permissions(manage_guild=True)
    async def payment_currency(self, ctx: EvelinaContext, currency: str):
        """Set the currency for the guild"""
        if currency.lower() not in ["eur", "usd"]:
            return await ctx.send_warning(f"Invalid currency. Supported currencies: `EUR` & `USD`")
        check = await self.bot.db.fetchrow("SELECT * FROM payment_currency WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await self.bot.db.execute("INSERT INTO payment_currency VALUES ($1, $2)", ctx.guild.id, currency.lower())
            return await ctx.send_success(f"Set the currency to **{currency.upper()}**")
        else:
            await self.bot.db.execute("UPDATE payment_currency SET currency = $1 WHERE guild_id = $2", currency.lower(), ctx.guild.id)
            return await ctx.send_success(f"Updated the currency to **{currency.upper()}**")

    @command(name="checkout", aliases=["co"], usage="checkout comminate 10.00€")
    @has_guild_permissions(manage_messages=True)
    async def checkout(self, ctx: EvelinaContext, user: User, amount: str) -> None:
        """Create a checkout for a user"""
        available_methods = await self.bot.db.fetch("SELECT method FROM payment_methods WHERE available = TRUE AND guild_id = $1", ctx.guild.id)
        methods = [row['method'] for row in available_methods]

        embed = Embed(color=colors.NEUTRAL, title=f"Checkout", url="https://evelina.bot")
        embed.add_field(name="> **Amount:**", value=f"```{amount}```", inline=False)
        embed.add_field(name="> **Information:**", value=f"```Click on one of the buttons below to select a payment method and complete your checkout.```", inline=False)
        embed.set_footer(text=f"{ctx.guild.name}", icon_url=ctx.guild.icon.url if ctx.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
        embed.timestamp = ctx.message.created_at

        view = CheckoutView(available_methods=methods)
        message = await ctx.send(embed=embed, view=view, content=user.mention)
        await self.bot.db.execute("INSERT INTO checkout (message, amount) VALUES ($1, $2)", message.id, amount)
        await ctx.message.delete()

async def setup(bot: Evelina) -> None:
	return await bot.add_cog(Reseller(bot))