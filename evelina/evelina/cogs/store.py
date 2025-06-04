import secrets
import datetime

from discord import ButtonStyle, Entitlement, Embed
from discord.ui import Button, View
from discord.ext.commands import Cog, command

from modules.styles import emojis, colors
from modules.evelinabot import Evelina, EvelinaContext

class Store(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Subscription commands"

    @Cog.listener("on_entitlement_create")
    async def on_entitlement_create(self, entitlement: Entitlement):
        user = self.bot.get_user(entitlement.user_id) or await self.bot.fetch_user(entitlement.user_id)
        # 10.000.000 💵
        if entitlement.sku_id == 1341766457939460117:
            await self.bot.db.execute("UPDATE economy SET cash = cash + 10000000 WHERE user_id = $1", user.id)
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
            log_embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **10.000.000 💵** to {user.mention} (`{user.id}`)\n > **Key:** Discord Purchase"))
            await channel.send(embed=log_embed)
            user_embed = (Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {user.mention}: You have **redeemed** your **10.000.000 💵**\n> Use `;balance` to check your balance"))
            return await user.send(embed=user_embed)
        # 25 votes
        elif entitlement.sku_id == 1341770489709723658:
            company = await self.bot.db.fetchrow("SELECT * FROM company WHERE $1 = ANY(members)", user.id)
            if not company:
                user_embed = (Embed(color=colors.WARNING, description=f"{emojis.WARNING} {user.mention}: You are not in a company\n> Open a ticket on the support server to get help"))
                return await user.send(embed=user_embed)
            company_voters = await self.bot.db.fetchrow("SELECT * FROM company_voters WHERE company_id = $1 AND user_id = $2", company['id'], user.id)
            if company_voters:
                await self.bot.db.execute("UPDATE company_voters SET votes = votes + $1 WHERE company_id = $2 AND user_id = $3", 25, company['id'], user.id)
            else:
                await self.bot.db.execute("INSERT INTO company_voters VALUES ($1,$2,$3)", user.id, company['id'], 25)
            await self.bot.db.execute("UPDATE company SET votes = votes + $1 WHERE id = $2", 25, company['id'])
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
            embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **25 votes** to {user.mention} (`{user.id}`)\n > **Key:** Discord Purchase"))
            await channel.send(embed=embed)
            user_embed = (Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {user.mention}: You have **redeemed** your **25 votes** for your company"))
            return await user.send(embed=user_embed)
        # Donator
        elif entitlement.sku_id == 1341790105253318758:
            check_donator = await self.bot.db.fetchrow("SELECT * FROM donor WHERE user_id = $1", user.id)
            if not check_donator:
                await self.bot.db.execute("INSERT INTO donor VALUES ($1, $2, $3)", user.id, datetime.datetime.utcnow().timestamp(), "purchased")
                await self.bot.manage.add_role(user, 1242474452353290291)
                channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
                embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **donator** to {user.mention} `{user.name}`\n > **Key:** Discord Purchase"))
                await channel.send(embed=embed)
                user_embed = (Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {user.mention}: You have **redeemed** your **donator perks**"))
                return await user.send(embed=user_embed)
            elif check_donator["status"] == "boosted":
                await self.bot.db.execute("UPDATE donor SET status = $1 WHERE user_id = $2", "purchased", user.id)
                await self.bot.manage.add_role(user, 1242474452353290291)
                channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
                embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **donator** to {user.mention} `{user.name}`\n > **Key:** Discord Purchase"))
                await channel.send(embed=embed)
                user_embed = (Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {user.mention}: You have **redeemed** your **donator perks**"))
                return await user.send(embed=user_embed)
            else:
                parts = [secrets.token_hex(2).upper() for _ in range(4)]
                serial_code = "-".join(parts)
                await self.bot.db.execute("INSERT INTO store_orders (invoice_id, product_id, total_price, serial_code, claimed, claimed_by, paid) VALUES ($1, $2, $3, $4, $5, $6, $7)", str(entitlement.id), 1, 4.99, serial_code, False, None, True)
                user_embed = (Embed(color=colors.WARNING, description=f"{emojis.WARNING} {user.mention}: You already have a donator subscription\n> Please use `;claim {serial_code}` to claim your subscription"))
                return await user.send(embed=user_embed)
        # Premium
        elif entitlement.sku_id == 1341772208753737850:
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
            embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **premium** to {user.mention} (`{user.id}`)\n > **Key:** Discord Purchase"))
            await channel.send(embed=embed)
            user_embed = (Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {user.mention}: You have **redeemed** your **premium**\n> Please open a ticket in our [**Support Server**](https://discord.gg/evelina) to get started"))
            return await user.send(embed=user_embed)
        # Instance
        elif entitlement.sku_id == 1341773061136977971:
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
            embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **custom instance** to {user.mention} (`{user.id}`)\n > **Key:** Discord Purchase"))
            await channel.send(embed=embed)
            user_embed = (Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {user.mention}: You have **redeemed** your **custom instance**\n> Please open a ticket in our [**Support Server**](https://discord.gg/evelina) to get started"))
            return await user.send(embed=user_embed)
        # Instance Server
        elif entitlement.sku_id == 1341773925717250089:
            parts = [secrets.token_hex(2).upper() for _ in range(4)]
            serial_code = "-".join(parts)
            await self.bot.db.execute("INSERT INTO store_orders (invoice_id, product_id, total_price, serial_code, claimed, claimed_by, paid) VALUES ($1, $2, $3, $4, $5, $6, $7)", str(entitlement.id), 6, 4.99, serial_code, False, None, True)
            channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_keys)
            embed = (Embed(color=colors.NEUTRAL, description=f"{self.bot.user.mention}: Added **instance server** to {user.mention} (`{user.id}`)\n > **Key:** Discord Purchase"))
            await channel.send(embed=embed)
            user_embed = (Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {user.mention}: You have **redeemed** your **instance server**\n> Please use `;instance whitelist {serial_code}` to whitelist your server"))
            return await user.send(embed=user_embed)
        else:
            print(f"Unknown SKU: {entitlement.sku_id}")

    @command(name="store", aliases=["donation", "donator", "donate", "buy", "prices", "pricing"])
    async def store(self, ctx: EvelinaContext):
        """View evelina online shop"""
        embed = Embed(color=colors.NEUTRAL, url="https://evelina.bot/premium", title="Evelina - Shop", description="After you paid, run `;claim` and enter your key to gain your **product**.\n> If you need help, create a Ticket in our [**Support Server**](https://discord.gg/evelina)").set_footer(text="All payments go directly to the bot for hosting, API expenses and more", icon_url="https://cdn.discordapp.com/emojis/1049028656128864286.png")
        view = View()
        view.add_item(Button(style=ButtonStyle.premium, sku_id=1341790105253318758, row=0))
        view.add_item(Button(style=ButtonStyle.green, sku_id=1341772208753737850, row=0))
        view.add_item(Button(style=ButtonStyle.blurple, sku_id=1341773061136977971, row=0))
        view.add_item(Button(style=ButtonStyle.red, sku_id=1341766457939460117, row=1))
        view.add_item(Button(style=ButtonStyle.grey, sku_id=1341770489709723658, row=1))
        view.add_item(Button(style=ButtonStyle.grey, sku_id=1341773925717250089, row=1))
        await ctx.send(embed=embed)

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Store(bot))