import datetime

from decimal import Decimal
from datetime import datetime

from discord import Embed, utils, User
from discord.ui import View, Button
from discord.ext.commands import Cog, group, is_owner, cooldown, BucketType

from modules.styles import emojis, colors
from modules.evelinabot import EvelinaContext, Evelina
from modules.predicates import create_account
from modules.economy.functions import EconomyMeasures

class Vote(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.vote_color = 0xFF819F
        self.topggAPI = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJib3QiOiJ0cnVlIiwiaWQiOiIxMjQyOTMwOTgxOTY3NzU3NDUyIiwiaWF0IjoiMTc0NTM4OTIxMiJ9.twqlMYKpxHJ84sAaXZq9M-BL5lx-m-0wmQdggQIzVGI'
        self.economy = EconomyMeasures(self.bot)

    async def process_vote(self, user):
        winnings = await self.bot.db.fetchrow("SELECT * FROM economy_config WHERE active = True")
        vote_amount = winnings['vote']
        company = await self.economy.get_user_company(user.id)
        if company:
            company_voters = await self.bot.db.fetchrow("SELECT * FROM company_voters WHERE company_id = $1 AND user_id = $2", company['id'], user.id)
            if company_voters:
                await self.bot.db.execute("UPDATE company_voters SET votes = votes + 1 WHERE company_id = $1 AND user_id = $2", company['id'], user.id)
            else:
                await self.bot.db.execute("INSERT INTO company_voters VALUES ($1,$2,$3)", user.id, company['id'], 1)
            await self.bot.db.execute("UPDATE company SET votes = votes + 1 WHERE id = $1", company['id'])
        current_balance = await self.bot.db.fetchval('SELECT cash FROM economy WHERE user_id = $1', user.id)
        vote_data = await self.bot.db.fetchrow('SELECT * FROM votes WHERE user_id = $1', user.id)
        vote_until = utils.utcnow().timestamp() + 43200
        if current_balance is None:
            new_balance = vote_amount
            await self.bot.db.execute('INSERT INTO economy (user_id, cash) VALUES ($1, $2)', user.id, new_balance)
        else:
            new_balance = current_balance + vote_amount
            await self.bot.db.execute('UPDATE economy SET cash = $1 WHERE user_id = $2', new_balance, user.id)
        if vote_data is None:
            await self.bot.db.execute('INSERT INTO votes (user_id, vote_until, vote_count) VALUES ($1, $2, 1)', user.id, vote_until)
        else:
            await self.bot.db.execute('UPDATE votes SET vote_until = $1, vote_count = vote_count + 1 WHERE user_id = $2', vote_until, user.id)

    @group(name="vote", invoke_without_command=True, case_insensitive=True)
    @create_account()
    async def vote(self, ctx: EvelinaContext):
        """Command that sends the vote link for top.gg"""
        result = await self.bot.db.fetchrow('SELECT vote_until, vote_count FROM votes WHERE user_id = $1', ctx.author.id)
        if result is None:
            cooldown, count = None, 0
        else:
            cooldown, count = result['vote_until'], result['vote_count']
        def format_cd(cd, is_topgg=False):
            if cd is None:
                return f"[`Available`](https://top.gg/bot/1242930981967757452/vote)" if is_topgg else "`Available`"
            now = datetime.utcnow()
            try:
                cooldown_time = datetime.utcfromtimestamp(int(cd))
            except ValueError:
                cooldown_time = datetime.strptime(cd, '%Y-%m-%d %H:%M:%S')
            if now > cooldown_time:
                return f"[`Available`](https://top.gg/bot/1242930981967757452/vote)" if is_topgg else "`Available`"
            return f"<t:{int(cooldown_time.timestamp())}:R>"
        cooldown_text = format_cd(cooldown, is_topgg=True)
        embed = Embed(
            description=f"**Vote for Evelina on** [**top.gg**](https://top.gg/bot/1242930981967757452/vote)",
            color=colors.NEUTRAL
        )
        winnings = await self.bot.db.fetchrow("SELECT * FROM economy_config WHERE active = True")
        vote_amount = f"{self.bot.misc.humanize_clean_number(winnings['vote'])}"
        embed.add_field(name="Rewards", value=f"> {vote_amount} 💵 & Donator (12h)")
        embed.add_field(name="Votes", value=f"> {count}")
        embed.add_field(name="Cooldown", value=f"> {cooldown_text}")
        embed.set_footer(text="You need to run ;vote claim to claim your reward")
        view = View()
        view.add_item(Button(label="Vote here", url="https://top.gg/bot/1242930981967757452/vote"))
        await ctx.send(embed=embed, view=view)
    
    @vote.command(name="claim", cooldown=10)
    @cooldown(1, 10, BucketType.user)
    async def vote_claim(self, ctx: EvelinaContext):
        """Claim the vote reward"""
        result = await self.bot.session.get_json(f"https://top.gg/api/bots/1242930981967757452/check?userId={ctx.author.id}", headers={"Authorization": self.topggAPI})
        if result is None:
            return await ctx.send_warning("Top.gg API running slow, please try again later")
        else:
            try:
                if result['voted'] == 0:
                    return await ctx.send_warning("You have not voted for Evelina on [**top.gg**](https://top.gg/bot/1242930981967757452/vote)")
                if result['voted'] == 1:
                    check = await self.bot.db.fetchrow('SELECT vote_until FROM votes WHERE user_id = $1', ctx.author.id)
                    if check is not None and check['vote_until'] is not None:
                        if check['vote_until'] > utils.utcnow().timestamp():
                            return await ctx.send_warning("You have already claimed your vote reward")
                    elif check is None or check['vote_until'] is None:
                        await self.bot.db.execute('INSERT INTO votes (user_id, vote_until, vote_count) VALUES ($1, $2, $3)', ctx.author.id, utils.utcnow().timestamp(), 0)
            except KeyError:
                return await ctx.send_warning("Top.gg API running slow, please try again later")
        await self.process_vote(ctx.author)
        winnings = await self.bot.db.fetchrow("SELECT * FROM economy_config WHERE active = True")
        vote_amount = f"{self.bot.misc.humanize_clean_number(winnings['vote'])}"
        embed = Embed(color=self.vote_color, description=f"{emojis.HEART} Thank you for voting! You have received **{vote_amount} 💵**\n{emojis.REPLY} You gain access to donator perks for 12 hours",)
        vote_view = View()
        vote_view.add_item(Button(label="Vote on Top.gg", url="https://top.gg/bot/1242930981967757452"))
        await self.economy.logging(ctx.author, Decimal(winnings['vote']), "collect", "vote")
        return await ctx.send(embed=embed, view=vote_view)

    @vote.command(name="leaderboard")
    async def vote_leaderboard(self, ctx: EvelinaContext):
        """Leaderboard for top.gg votes"""
        votes = await self.bot.db.fetch("SELECT user_id, vote_count FROM votes WHERE vote_count > 0 ORDER BY vote_count DESC")
        total = await self.bot.db.fetch("SELECT SUM(vote_count) as total FROM votes")
        to_show = [f"**{self.bot.get_user(vote['user_id'])}** - Votes: {vote['vote_count']}" for vote in votes if self.bot.get_user(vote['user_id'])]
        await ctx.paginate(to_show, title=f"Top.gg Votes ({total[0]['total'] if total else 0})", author={"name": ctx.author, "icon_url": ctx.author.avatar})

    @vote.command(name="remind")
    async def vote_remind(self, ctx: EvelinaContext):
        """Remind the user to vote for Evelina"""
        check = await self.bot.db.fetchrow('SELECT vote_until, vote_reminder FROM votes WHERE user_id = $1', ctx.author.id)
        if check is None:
            await self.bot.db.execute('INSERT INTO votes (user_id, vote_until, vote_count, vote_reminder) VALUES ($1, $2, $3, $4)', ctx.author.id, None, 0, True)
            return await ctx.send_success("You will now receive a reminder to vote for Evelina")
        elif check["vote_reminder"] == True:
            return await ctx.send_warning("You are already receiving reminders to vote for Evelina")
        else:
            await self.bot.db.execute('UPDATE votes SET vote_reminder = True WHERE user_id = $1', ctx.author.id)
            return await ctx.send_success("You will now receive a reminder to vote for Evelina")
        
    @vote.command(name="add")
    @is_owner()
    async def vote_add(self, ctx: EvelinaContext, user: User):
        """Add a vote to a user"""
        await self.process_vote(user)
        return await ctx.send_success(f"Added a vote to {user.mention}")

async def setup(bot: Evelina) -> None:
    await bot.add_cog(Vote(bot))