import discord
from discord.ext import commands

class OnJoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 785042666475225109

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """
        Event triggered when the bot joins a new server (guild).
        """
        inviter = None
        try:
            audit_logs = await guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add).flatten()
            if audit_logs:
                inviter = audit_logs[0].user
        except Exception as e:
            print(f"Could not retrieve inviter for {guild.name}: {e}")

        if inviter:
            embed = discord.Embed(
                title="Thanks for Choosing Heresy!",
                description=(
                    "Hello! Thank you for inviting Heresy to your server.\n"
                    "To see all available commands, use `,help`.\n\n"
                    "If you have any questions, join discord.gg/Heresy for more info on Heresy."
                ),
                color=discord.Color.green()
            )
            embed.set_footer(text="I am in your walls.")
            try:
                await inviter.send(embed=embed)
            except Exception as e:
                print(f"Could not DM inviter {inviter}: {e}")

        invite_link = "Unable to generate invite"
        try:
            invite = await guild.text_channels[0].create_invite(max_age=3600, max_uses=1, unique=True)
            invite_link = invite.url
        except Exception as e:
            print(f"Could not create invite for {guild.name}: {e}")

        owner_dm_content = (
            f"Hello <@785042666475225109>, I was added to **{guild.name}** by "
            f"{inviter.mention if inviter else 'an unauthorized user'}.\n\n"
            f"If you did not authorize this action, feel free to revoke access. Invite link: {invite_link}"
        )
        try:
            owner_user = await self.bot.fetch_user(self.owner_id)
            await owner_user.send(owner_dm_content)
        except Exception as e:
            print(f"Could not DM owner: {e}")


async def setup(bot):
    await bot.add_cog(OnJoin(bot))
