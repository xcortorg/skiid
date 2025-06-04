import discord
import random
import asyncio
import aiohttp
import config

from core.client.context import Context
from main import Evict

from discord.ext import tasks
from discord import (
    Embed, 
    Member, 
    Interaction, 
    ButtonStyle, 
    TextChannel
)

from discord.ext.commands import (
    Cog, 
    command, 
    group,
    has_permissions,
)

from datetime import datetime, timedelta
from typing import Optional

class Yugioh(Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = "Yu-Gi-Oh! Card collection commands."
        self.session = aiohttp.ClientSession()
        self.card_drops.start()
        self.active_drops = {}
        self.api_base = "https://db.ygoprodeck.com/api/v7"
        self.packs = {
            "starter pack": {"price": 1000, "cards": 5, "guaranteed_rare": True},
            "premium pack": {"price": 2500, "cards": 5, "guaranteed_super": True},
            "ultimate pack": {"price": 5000, "cards": 5, "guaranteed_ultra": True}
        }

    async def cog_unload(self):
        await self.session.close()
        self.card_drops.cancel()

    async def fetch_random_card(self, target_rarity: str) -> Optional[dict]:
        """
        Fetch a random card of specific rarity.
        """
        rarity_codes = {
            "Common": "Common",
            "Rare": "Rare",
            "Super Rare": "Super Rare",
            "Ultra Rare": "Ultra Rare"
        }
        
        params = {
            "num": 1,
            "offset": random.randint(0, 100),
            "sort": "random",
            "misc": "yes",
            "rarity": rarity_codes[target_rarity]
        }
        
        
        async with self.session.get(f"{self.api_base}/cardinfo.php", params=params) as resp:
            if resp.status == 200:
                try:
                    text = await resp.text()
                    data = await resp.json()
                    if data.get('data') and len(data['data']) > 0:
                        card = data['data'][0]
                        return card
                    else:
                        return None
                except Exception as e:
                    return None
            else:
                return None
        return None

    def determine_card_rarity(self, card: dict) -> str:
        """
        Determine card rarity based on card properties.
        """
        if card.get('type', '').startswith('Link') or card.get('type', '').startswith('Synchro'):
            return "Ultra Rare"
        elif card.get('type', '').startswith('Fusion') or card.get('type', '').startswith('XYZ'):
            return "Super Rare"
        elif card.get('type', '').startswith('Effect') or card.get('level', 0) >= 7:
            return "Rare"
        else:
            return "Common"

    @tasks.loop(minutes=30)
    async def card_drops(self):
        """
        Create random card drops in designated channels.
        """
        channels = await self.bot.db.fetch(
            """
            SELECT channel_id 
            FROM card_drop_channels
            """
        )
        
        rarities = ["Common", "Rare", "Super Rare", "Ultra Rare"]
        weights = [60, 25, 10, 5]  
        
        for channel_data in channels:
            channel = self.bot.get_channel(channel_data['channel_id'])
            if channel and channel.id not in self.active_drops:
                rarity = random.choices(rarities, weights=weights)[0]
                card = await self.fetch_random_card(rarity)
                
                if card:
                    embed = Embed(
                        title="⚔️ A Wild Yu-Gi-Oh! Card Appears!",
                        description=(
                            f"**Rarity:** {rarity}\n"
                            "React with ⚔️ to claim this card!"
                        ),
                        color=discord.Color.gold()
                    )
                    embed.set_image(url=card['card_images'][0]['image_url'])
                    
                    msg = await channel.send(embed=embed)
                    await msg.add_reaction("⚔️")
                    
                    self.active_drops[channel.id] = {
                        'message': msg,
                        'card': card,
                        'claimed': False,
                        'rarity': rarity
                    }

    @group(name="cards", invoke_without_command=True)
    async def cards(self, ctx: Context):
        """
        Yu-Gi-Oh! card collection commands.
        """
        await ctx.send_help(ctx.command)

    @cards.command(name="search")
    async def search_cards(self, ctx: Context, *, query: str):
        """
        Search for Yu-Gi-Oh! cards.
        """
        async with self.session.get(
            f"{self.api_base}/cardinfo.php",
            params={"fname": query}
        ) as resp:
            data = await resp.json()
            
        if not data.get('data'):
            return await ctx.warn("No cards found!")
            
        embed = Embed(
            title=f"🔍 Search Results: {query}",
            description="Here are the cards matching your search:",
            color=discord.Color.blue()
        )
        
        first_card = data['data'][0]
        embed.set_thumbnail(url=first_card['card_images'][0]['image_url'])
        
        for card in data['data'][:10]:  
            card_text = (
                f"Type: {card['type']}\n"
                f"ATK: {card.get('atk', 'N/A')} / DEF: {card.get('def', 'N/A')}\n"
                f"Level: {card.get('level', 'N/A')}\n"
                f"Description: {card['desc'][:300]}..." if len(card['desc']) > 300 else card['desc']
            )
            
            embed.add_field(
                name=f"{card['name']}",
                value=card_text,
                inline=False
            )
            
        embed.set_footer(text="Use ;cards view <card name> to see more details")
        await ctx.send(embed=embed)

    @cards.command(name="view")
    async def view_card(self, ctx: Context, *, card_name: str):
        """
        View detailed card information.
        """
        async with self.session.get(
            f"{self.api_base}/cardinfo.php",
            params={"name": card_name}
        ) as resp:
            data = await resp.json()
            
        if not data.get('data'):
            return await ctx.warn("Card not found!")
            
        card = data['data'][0]
        embed = Embed(
            title=card['name'],
            description=card['desc'],
            color=discord.Color.blue()
        )
        
        embed.set_image(url=card['card_images'][0]['image_url'])
        
        stats = []
        if 'type' in card:
            stats.append(f"**Type:** {card['type']}")
        if 'race' in card:
            stats.append(f"**Race:** {card['race']}")
        if 'attribute' in card:
            stats.append(f"**Attribute:** {card['attribute']}")
        if 'atk' in card:
            stats.append(f"**ATK/DEF:** {card['atk']}/{card['def']}")
        if 'level' in card:
            stats.append(f"**Level:** {'⭐' * card['level']}")
        
        embed.add_field(
            name="Card Information",
            value="\n".join(stats),
            inline=False
        )
        
        if 'card_prices' in card:
            price = card['card_prices'][0]
            embed.add_field(
                name="Market Prices",
                value=f"TCGPlayer: ${price['tcgplayer_price']}\nCardMarket: €{price['cardmarket_price']}",
                inline=False
            )
            
        await ctx.send(embed=embed)

    @cards.command(name="collection", aliases=["inv", "inventory"])
    async def view_collection(self, ctx: Context, member: Member = None):
        """
        View your or someone else's card collection.
        """
        member = member or ctx.author
        
        cards = await self.bot.db.fetch(
            """
            SELECT card_id, quantity 
            FROM user_cards 
            WHERE user_id = $1 
            ORDER BY card_id
            """,
            member.id
        )
        
        if not cards:
            return await ctx.warn(f"{'You don\'t' if member == ctx.author else f'{member.name} doesn\'t'} have any cards!")

        class CollectionView(discord.ui.View):
            def __init__(self, pages):
                super().__init__(timeout=60)
                self.pages = pages
                self.current_page = 0

            @discord.ui.button(label="Previous", emoji=config.EMOJIS.PAGINATOR.PREVIOUS, style=ButtonStyle.primary)
            async def previous_page(self, interaction: Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    return await interaction.warn("This is not your collection!")
                self.current_page = (self.current_page - 1) % len(self.pages)
                await interaction.response.edit_message(embed=self.pages[self.current_page])

            @discord.ui.button(label="Next", emoji=config.EMOJIS.PAGINATOR.NEXT, style=ButtonStyle.primary)
            async def next_page(self, interaction: Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    return await interaction.warn("This is not your collection!")
                self.current_page = (self.current_page + 1) % len(self.pages)
                await interaction.response.edit_message(embed=self.pages[self.current_page])

        pages = []
        cards_per_page = 5
        
        for i in range(0, len(cards), cards_per_page):
            embed = Embed(
                title=f"🎴 {member.name}'s Collection",
                color=discord.Color.blue()
            )
            
            page_cards = cards[i:i + cards_per_page]
            
            if page_cards:
                async with self.session.get(
                    f"{self.api_base}/cardinfo.php",
                    params={"id": page_cards[0]['card_id']}
                ) as resp:
                    data = await resp.json()
                    if data.get('data'):
                        embed.set_thumbnail(url=data['data'][0]['card_images'][0]['image_url'])
            
            for card in page_cards:
                async with self.session.get(
                    f"{self.api_base}/cardinfo.php",
                    params={"id": card['card_id']}
                ) as resp:
                    card_data = await resp.json()
                    if card_data.get('data'):
                        card_info = card_data['data'][0]
                        embed.add_field(
                            name=f"{card_info['name']} (x{card['quantity']})",
                            value=(
                                f"**Type:** {card_info['type']}\n"
                                f"**ATK/DEF:** {card_info.get('atk', 'N/A')}/{card_info.get('def', 'N/A')}"
                            ),
                            inline=False
                        )
            
            embed.set_footer(text=f"Page {i//cards_per_page + 1}/{(len(cards) + cards_per_page - 1)//cards_per_page}")
            pages.append(embed)
        
        if pages:
            view = CollectionView(pages)
            await ctx.send(embed=pages[0], view=view)

    @cards.command(name="stats")
    async def card_stats(self, ctx, member: discord.Member = None):
        """
        View card collection statistics.
        """
        member = member or ctx.author
        
        stats = await self.bot.db.fetchrow(
            """SELECT 
                COUNT(DISTINCT card_id) as unique_cards,
                SUM(quantity) as total_cards,
                SUM(CASE WHEN rarity = 'Common' THEN quantity ELSE 0 END) as common_cards,
                SUM(CASE WHEN rarity = 'Rare' THEN quantity ELSE 0 END) as rare_cards,
                SUM(CASE WHEN rarity = 'Super Rare' THEN quantity ELSE 0 END) as super_rare_cards,
                SUM(CASE WHEN rarity = 'Ultra Rare' THEN quantity ELSE 0 END) as ultra_rare_cards
            FROM user_cards 
            WHERE user_id = $1""",
            member.id
        )
        
        embed = Embed(
            title=f"📊 {member.name}'s Card Statistics",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Unique Cards", value=f"{stats['unique_cards']:,}")
        embed.add_field(name="Total Cards", value=f"{stats['total_cards']:,}")
        embed.add_field(name="Common Cards", value=f"{stats['common_cards']:,}")
        embed.add_field(name="Rare Cards", value=f"{stats['rare_cards']:,}")
        embed.add_field(name="Super Rare Cards", value=f"{stats['super_rare_cards']:,}")
        embed.add_field(name="Ultra Rare Cards", value=f"{stats['ultra_rare_cards']:,}")
        
        value = (
            (stats['common_cards'] or 0) * 100 +
            (stats['rare_cards'] or 0) * 250 +
            (stats['super_rare_cards'] or 0) * 500 +
            (stats['ultra_rare_cards'] or 0) * 1000
        )
        embed.add_field(name="Collection Value", value=f"{value:,} coins")
        
        await ctx.send(embed=embed)

    @cards.command(name="gift")
    async def gift_card(self, ctx: Context, member: Member, *, card_name: str):
        """
        Gift a card to another member.
        """
        if member.bot:
            return await ctx.warn("You can't gift cards to bots!")
        if member == ctx.author:
            return await ctx.warn("You can't gift cards to yourself!")

        async with self.session.get(
            f"{self.api_base}/cardinfo.php",
            params={"fname": card_name}
        ) as resp:
            data = await resp.json()
            
        if not data.get('data'):
            return await ctx.warn("Card not found!")
            
        card_id = data['data'][0]['id']
        
        sender_card = await self.bot.db.fetchrow(
            """
            SELECT * FROM user_cards 
            WHERE user_id = $1 
            AND card_id = $2
            """,
            ctx.author.id, 
            card_id
        )
        
        if not sender_card:
            return await ctx.warn("You don't have this card!")
        if sender_card['quantity'] <= 1:
            return await ctx.warn("You only have one copy of this card!")

        if sender_card['quantity'] <= 2:
            await self.bot.db.execute(
                """
                DELETE FROM user_cards 
                WHERE user_id = $1 
                AND card_id = $2
                """,
                ctx.author.id, 
                card_id
            )
        else:
            await self.bot.db.execute(
                """
                UPDATE user_cards 
                SET quantity = quantity - 1 
                WHERE user_id = $1 AND card_id = $2
                """,
                ctx.author.id, 
                card_id
            )
                
            await self.bot.db.execute(
                """
                INSERT INTO user_cards (user_id, card_id, rarity, quantity)
                VALUES ($1, $2, $3, 1)
                ON CONFLICT (user_id, card_id) 
                DO UPDATE SET quantity = user_cards.quantity + 1
                """,
                member.id, 
                card_id, 
                sender_card['rarity']
            )

        embed = Embed(
            title="🎁 Card Gifted!",
            description=f"Successfully gifted {data['data'][0]['name']} to {member.name}!",
            color=self.get_rarity_color(sender_card['rarity'])
        )
        embed.set_thumbnail(url=data['data'][0]['card_images'][0]['image_url'])
        
        await ctx.send(embed=embed)

    @cards.command(name="sell")
    async def sell_card(self, ctx: Context, card_name: str, amount: int = 1):
        """
        Sell a card for coins.
        """
        if amount < 1:
            return await ctx.warn("Amount must be positive!")

        card_data = await self.bot.db.fetchrow(
            """
            SELECT * FROM user_cards 
            WHERE user_id = $1 
            AND card_name = $2
            """,
            ctx.author.id, 
            card_name
        )
        
        if not card_data or card_data['quantity'] < amount:
            return await ctx.warn("You don't have enough copies of this card!")

        values = {
            "Common": 100,
            "Rare": 250,
            "Super Rare": 500,
            "Ultra Rare": 1000
        }
        
        value = values.get(card_data['rarity'], 100) * amount

        if card_data['quantity'] == amount:
            await self.bot.db.execute(
                """
                DELETE FROM user_cards 
                WHERE user_id = $1 
                AND card_name = $2
                """,
                ctx.author.id, 
                card_name
            )
        
        else:
            await self.bot.db.execute(
                """
                UPDATE user_cards 
                SET quantity = quantity - $1 
                WHERE user_id = $2 
                AND card_name = $3
                """,
                amount, 
                ctx.author.id, 
                card_name
            )
                
            await self.bot.db.execute(
                """
                UPDATE economy 
                SET wallet = wallet + $1 
                WHERE user_id = $2
                """,
                value, 
                ctx.author.id
            )

        await ctx.approve(f"Successfully sold {amount}x {card_name} for {value:,} coins!")

    @cards.command(name="top")
    async def card_leaderboard(self, ctx: Context, category: str = "total"):
        """
        View the card leaderboard
        Categories: total, unique
        """
        category = category.lower()
        if category not in ["total", "unique"]:
            return await ctx.warn("Invalid category! Choose from: total, unique")

        order_by = "total_cards" if category == "total" else "unique_cards"

        results = await self.bot.db.fetch(
            f"""
            SELECT
                user_id,
                COUNT(*) as unique_cards,
                SUM(quantity) as total_cards
            FROM user_cards
            GROUP BY user_id
            GROUP BY {order_by} DESC
            LIMIT 10
            """
        )

        if not results:
            return await ctx.warn("No data available for the leaderboard.")

        embed = Embed(
            title=f"🏆 Card Leaderboard - {category.title()}",
            color=discord.Color.gold()
        )

        for i, result in enumerate(results, 1):
            member = ctx.guild.get_member(result['user_id'])
            if member:
                value = result[order_by]
                embed.add_field(
                    name=f"#{i} {member.name}",
                    value=f"{value:,} {category}",
                    inline=False
                )

        await ctx.send(embed=embed)

    @command()
    @has_permissions(manage_channels=True)
    async def cardchannel(self, ctx: Context, channel: TextChannel = None):
        """
        Set the current channel as a card drop channel.
        """
        channel = channel or ctx.channel
        
        await self.bot.db.execute(
            """
            INSERT INTO card_drop_channels (channel_id, guild_id, added_by)
            VALUES ($1, $2, $3)
            ON CONFLICT (channel_id) DO NOTHING
            """,
            channel.id, 
            ctx.guild.id, 
            ctx.author.id
        )
        
        await ctx.approve(f"Set {channel.mention} as a card drop channel!")

    @cards.group(name="packs", invoke_without_command=True)
    async def card_packs(self, ctx: Context):
        """
        View and open card packs.
        """
        embed = Embed(
            title="🎴 Available Card Packs",
            description="Use `;cards packs open <pack_name>` to open a pack!",
            color=discord.Color.blue()
        )
        
        for name, info in self.packs.items():
            guaranteed = "Rare" if info.get("guaranteed_rare") else \
                        "Super Rare" if info.get("guaranteed_super") else \
                        "Ultra Rare" if info.get("guaranteed_ultra") else "None"
            
            embed.add_field(
                name=name.title(),
                value=f"💰 Price: {info['price']:,} coins\n"
                      f"📦 Cards: {info['cards']}\n"
                      f"✨ Guaranteed: {guaranteed}",
                inline=False
            )
            
        await ctx.send(embed=embed)

    @card_packs.command(name="open")
    async def open_pack(self, ctx: Context, *, pack_name: str):
        """
        Open a card pack.
        """
        pack = self.packs.get(pack_name.lower())
        if not pack:
            return await ctx.warn("Invalid pack name!")
            
        balance = await self.bot.db.fetchval(
            """
            SELECT wallet 
            FROM economy 
            WHERE user_id = $1
            """,
            ctx.author.id
        )
        
        if balance < pack['price']:
            return await ctx.warn(f"You need {pack['price']:,} coins to buy this pack!")

        await ctx.send("🎴 Fetching your cards... This might take a few seconds!")
            
        cards = []
        rarities = ["Common", "Rare", "Super Rare", "Ultra Rare"]
        
        if "guaranteed_ultra" in pack:
            weights = [0, 0, 0, 100]
        elif "guaranteed_super" in pack:
            weights = [0, 0, 70, 30]
        elif "guaranteed_rare" in pack:
            weights = [0, 60, 30, 10]
        else:
            weights = [60, 25, 10, 5]
            
        for _ in range(pack['cards']):
            rarity = random.choices(rarities, weights=weights)[0]
            card = await self.fetch_random_card(rarity)
            if card:
                cards.append((card, rarity))
                
        if not cards:
            return await ctx.warn("Failed to generate cards! Please try again.")
            
        await self.bot.db.execute(
                    """
                    UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2
                    """,
                    pack['price'], 
                    ctx.author.id
                )
                
        await self.bot.db.execute(
                    """
                    INSERT INTO user_transactions (user_id, type, amount, created_at)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                    """,
                    ctx.author.id, 
                    f"card_pack_{pack_name.lower().replace(' ', '_')}", -pack['price']
                )
                
        for card, rarity in cards:
            await self.bot.db.execute(
                    """
                    INSERT INTO user_cards (user_id, card_id, quantity)
                    VALUES ($1, $2, 1)
                    ON CONFLICT (user_id, card_id) 
                    DO UPDATE SET quantity = user_cards.quantity + 1
                    """,
                    ctx.author.id, 
                    str(card['id'])
                )
                    
        await self.animate_pack_opening(ctx, cards)

    def get_rarity_color(self, rarity: str) -> discord.Color:
        """
        Get embed color based on card rarity.
        """
        return {
            "Common": discord.Color.light_grey(),
            "Rare": discord.Color.blue(),
            "Super Rare": discord.Color.purple(),
            "Ultra Rare": discord.Color.gold()
        }.get(rarity, discord.Color.default())

    async def animate_pack_opening(self, ctx: Context, cards):
        """
        Create an animated pack opening experience.
        """
        loading_msg = await ctx.neutral("Opening pack...")

        class NavigationButton(discord.ui.Button):
            def __init__(self, direction: str):
                style = discord.ButtonStyle.primary
                if direction == "previous":
                    super().__init__(label="Previous Card", emoji=config.EMOJIS.PAGINATOR.PREVIOUS, style=style)
                else:
                    super().__init__(label="Next Card", emoji=config.EMOJIS.PAGINATOR.NEXT, style=style)
                self.direction = direction
                
            async def callback(self, interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    return await interaction.warn("This is not your pack!")
                
                view = self.view
                if self.direction == "previous":
                    if view.current_card <= 0:
                        return await interaction.response.defer()
                    view.current_card -= 1
                else:
                    if view.current_card >= len(cards) - 1:
                        await self.view.send_summary()
                        return await interaction.response.defer()
                    view.current_card += 1
                
                card, rarity = cards[view.current_card]
                embed = create_card_embed(card, rarity, view.current_card + 1, len(cards))
                await interaction.response.edit_message(embed=embed)

        def create_card_embed(card, rarity, current, total):
            embed = Embed(
                title=f"📦 Pack Opening - Card {current}/{total}",
                color=self.get_rarity_color(rarity)
            )
            embed.set_image(url=card['card_images'][0]['image_url'])
            
            rarity_display = {
                "Common": "⚪",
                "Rare": "🔵",
                "Super Rare": "🟣",
                "Ultra Rare": "⭐"
            }.get(rarity, "⚪")
            
            embed.add_field(
                name=f"{rarity_display} {card['name']} ({rarity})",
                value=f"Type: {card['type']}\n"
                      f"ATK: {card.get('atk', 'N/A')} / DEF: {card.get('def', 'N/A')}\n"
                      f"Description: {card['desc'][:100]}..." if len(card['desc']) > 100 else card['desc']
            )
            return embed

        class PackOpeningView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.current_card = -1
                self.add_item(NavigationButton("previous"))
                self.add_item(NavigationButton("next"))
                self.summary_sent = False

            async def send_summary(self):
                if self.summary_sent:
                    return
                self.summary_sent = True
                
                summary_embed = Embed(
                    title="🎉 Pack Opening Complete!",
                    description=f"You got {len(cards)} new cards!",
                    color=discord.Color.gold()
                )
                
                for card, rarity in cards:
                    rarity_display = {
                        "Common": "⚪",
                        "Rare": "🔵",
                        "Super Rare": "🟣",
                        "Ultra Rare": "⭐"
                    }.get(rarity, "⚪")
                    
                    summary_embed.add_field(
                        name=f"{rarity_display} {card['name']}",
                        value=f"Rarity: {rarity}\nType: {card['type']}",
                        inline=True
                    )
                
                await ctx.send(embed=summary_embed)

        reveal_embed = discord.Embed(
            title="📦 Pack Opening",
            description="Click Next to reveal your cards!",
            color=discord.Color.gold()
        )
        reveal_embed.set_image(url="https://i.imgur.com/UjbK2Wb.png")
        
        view = PackOpeningView()
        msg = await ctx.send(embed=reveal_embed, view=view)
        await loading_msg.delete()

        summary_embed = discord.Embed(
            title="🎉 Pack Opening Complete!",
            description=f"You got {len(cards)} new cards!",
            color=discord.Color.gold()
        )
        
        for card, rarity in cards:
            rarity_display = {
                "Common": "⚪",
                "Rare": "🔵",
                "Super Rare": "🟣",
                "Ultra Rare": "⭐"
            }.get(rarity, "⚪")
            
            summary_embed.add_field(
                name=f"{rarity_display} {card['name']}",
                value=f"Rarity: {rarity}\nType: {card['type']}",
                inline=True
            )
        
        await ctx.send(embed=summary_embed)

    def create_card_embed(self, card, rarity, current, total):
        embed = Embed(
            title=f"📦 Pack Opening - Card {current}/{total}",
            color=self.get_rarity_color(rarity)
        )
        embed.set_image(url=card['card_images'][0]['image_url'])
        
        rarity_display = {
            "Common": "⚪",
            "Rare": "🔵",
            "Super Rare": "🟣",
            "Ultra Rare": "⭐"
        }.get(rarity, "⚪")
        
        embed.add_field(
            name=f"{rarity_display} {card['name']} ({rarity})",
            value=f"Type: {card['type']}\n"
                  f"ATK: {card.get('atk', 'N/A')} / DEF: {card.get('def', 'N/A')}\n"
                  f"Description: {card['desc'][:100]}..." if len(card['desc']) > 100 else card['desc']
        )
        return embed

    @cards.group(name="market", invoke_without_command=True)
    async def card_market(self, ctx):
        """View the card market"""
        listings = await self.bot.db.fetch(
            """SELECT cm.*, uc.card_name, uc.rarity 
            FROM card_market cm 
            JOIN user_cards uc ON uc.user_id = cm.seller_id AND uc.card_id = cm.card_id 
            ORDER BY cm.listed_at DESC 
            LIMIT 10"""
        )
        
        if not listings:
            return await ctx.warn("No cards are currently listed on the market!")
            
        embed = discord.Embed(
            title="🏪 Card Market",
            description="Use `;cards market buy <listing_id>` to purchase a card!",
            color=discord.Color.blue()
        )
        
        for listing in listings:
            seller = ctx.guild.get_member(listing['seller_id'])
            embed.add_field(
                name=f"{listing['card_name']} (ID: {listing['listing_id']})",
                value=f"💰 Price: {listing['price']:,} coins\n"
                      f"✨ Rarity: {listing['rarity']}\n"
                      f"👤 Seller: {seller.name if seller else 'Unknown'}",
                inline=False
            )
            
        await ctx.send(embed=embed)

    @card_market.command(name="list")
    async def market_list(self, ctx, card_name: str, price: int):
        """List a card on the market"""
        if price < 1:
            return await ctx.warn("Price must be positive!")
            
        card = await self.bot.db.fetchrow(
            """SELECT * FROM user_cards 
            WHERE user_id = $1 AND card_name = $2""",
            ctx.author.id, card_name
        )
        
        if not card:
            return await ctx.warn("You don't have this card!")
            
        await self.bot.db.execute(
            """INSERT INTO card_market (seller_id, card_id, price)
            VALUES ($1, $2, $3)""",
            ctx.author.id, card['card_id'], price
        )
        
        await ctx.approve(f"Listed {card_name} for {price:,} coins!")

    @card_market.command(name="buy")
    async def market_buy(self, ctx, listing_id: int):
        """Buy a card from the market"""
        listing = await self.bot.db.fetchrow(
            """SELECT * FROM card_market WHERE listing_id = $1""",
            listing_id
        )
        
        if not listing:
            return await ctx.warn("Invalid listing ID!")
            
        if listing['seller_id'] == ctx.author.id:
            return await ctx.warn("You can't buy your own card!")
            
        balance = await self.bot.db.fetchval(
            """SELECT wallet FROM economy WHERE user_id = $1""",
            ctx.author.id
        )
        
        if balance < listing['price']:
            return await ctx.warn(f"You need {listing['price']:,} coins to buy this card!")
            
        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """DELETE FROM card_market WHERE listing_id = $1""",
                    listing_id
                )
                
                card_data = await conn.fetchrow(
                    """SELECT * FROM user_cards 
                    WHERE user_id = $1 AND card_id = $2""",
                    listing['seller_id'], listing['card_id']
                )
                
                await conn.execute(
                    """INSERT INTO user_cards (user_id, card_id, card_name, rarity, quantity)
                    VALUES ($1, $2, $3, $4, 1)
                    ON CONFLICT (user_id, card_id) 
                    DO UPDATE SET quantity = user_cards.quantity + 1""",
                    ctx.author.id, card_data['card_id'], 
                    card_data['card_name'], card_data['rarity']
                )
                
                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2""",
                    listing['price'], ctx.author.id
                )
                
                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet + $1 
                    WHERE user_id = $2""",
                    listing['price'], listing['seller_id']
                )
                
        await ctx.approve(f"Successfully bought {card_data['card_name']} for {listing['price']:,} coins!")

    @cards.command(name="daily")
    async def daily_card(self, ctx):
        """Claim your daily free card"""
        last_claim = await self.bot.db.fetchval(
            """SELECT last_claim FROM card_daily WHERE user_id = $1""",
            ctx.author.id
        )
        
        if last_claim and (datetime.now() - last_claim).total_seconds() < 86400:
            time_left = timedelta(seconds=86400 - (datetime.now() - last_claim).total_seconds())
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)
            return await ctx.warn(f"You can claim your next card in {hours}h {minutes}m!")

        rarities = ["Common", "Rare", "Super Rare", "Ultra Rare"]
        weights = [70, 20, 8, 2]  
        
        rarity = random.choices(rarities, weights=weights)[0]
        card = await self.fetch_random_card(rarity)
        
        if not card:
            return await ctx.warn("Failed to generate card! Please try again.")
            
        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """INSERT INTO user_cards (user_id, card_id, quantity)
                    VALUES ($1, $2, 1)
                    ON CONFLICT (user_id, card_id) 
                    DO UPDATE SET quantity = user_cards.quantity + 1""",
                    ctx.author.id, str(card['id'])
                )
                
                await conn.execute(
                    """INSERT INTO card_daily (user_id, last_claim)
                    VALUES ($1, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET last_claim = NOW()""",
                    ctx.author.id
                )
        
        embed = discord.Embed(
            title="🎁 Daily Card Reward",
            description=f"You received a {rarity} card!",
            color=self.get_rarity_color(rarity)
        )
        embed.set_image(url=card['card_images'][0]['image_url'])
        embed.add_field(
            name=card['name'],
            value=f"Type: {card['type']}\nATK: {card.get('atk', 'N/A')} / DEF: {card.get('def', 'N/A')}"
        )
        
        await ctx.send(embed=embed)

    @cards.command(name="trade")
    async def trade_cards(self, ctx, member: discord.Member):
        """Start a card trade with another member"""
        if member.bot:
            return await ctx.warn("You can't trade with bots!")
        if member == ctx.author:
            return await ctx.warn("You can't trade with yourself!")
            
        trade_session = {
            'initiator': {'id': ctx.author.id, 'cards': []},
            'target': {'id': member.id, 'cards': []},
            'status': 'selecting'
        }
        
        embed = discord.Embed(
            title="🔄 Card Trade Session",
            description=(
                f"Trade between {ctx.author.mention} and {member.mention}\n"
                "Use `;trade add <card_name>` to add cards\n"
                "Use `;trade remove <card_name>` to remove cards\n"
                "Use `;trade confirm` when ready\n"
                "Use `;trade cancel` to cancel"
            ),
            color=discord.Color.blue()
        )
        
        trade_msg = await ctx.send(embed=embed)
        
        def check(m):
            return (
                m.author in [ctx.author, member] and 
                m.channel == ctx.channel and 
                m.content.startswith(";trade")
            )
            
        while trade_session['status'] == 'selecting':
            try:
                msg = await self.bot.wait_for('message', timeout=300.0, check=check)
                command = msg.content.split()[1]
                
                if command == 'cancel':
                    await ctx.send("Trade cancelled!")
                    return
                    
                elif command == 'confirm':
                    if msg.author.id == ctx.author.id:
                        trade_session['initiator']['confirmed'] = True
                    else:
                        trade_session['target']['confirmed'] = True
                        
                    if trade_session.get('initiator', {}).get('confirmed') and trade_session.get('target', {}).get('confirmed'):
                        trade_session['status'] = 'confirmed'
                        break
                        
                elif command == 'add':
                    card_name = " ".join(msg.content.split()[2:])
                    
                embed = discord.Embed(
                    title="🔄 Card Trade Session",
                    description="Current trade status:",
                    color=discord.Color.blue()
                )
                
                for side in ['initiator', 'target']:
                    user = ctx.guild.get_member(trade_session[side]['id'])
                    cards = trade_session[side]['cards']
                    confirmed = "✅" if trade_session[side].get('confirmed') else "❌"
                    
                    card_list = "\n".join(f"- {card['name']}" for card in cards) or "No cards added"
                    embed.add_field(
                        name=f"{user.name}'s Offer {confirmed}",
                        value=card_list,
                        inline=True
                    )
                    
                await trade_msg.edit(embed=embed)
                
            except asyncio.TimeoutError:
                await ctx.send("Trade cancelled due to inactivity!")
                return
                
        if trade_session['status'] == 'confirmed':
            async with self.bot.db.acquire() as conn:
                async with conn.transaction():
                    pass
                    
            await ctx.approve("Trade completed successfully!")