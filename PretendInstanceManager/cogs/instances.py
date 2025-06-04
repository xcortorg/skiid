import os
from asyncio import create_subprocess_shell
from copy import copy
from subprocess import PIPE

from discord import ButtonStyle, Embed, Interaction, Member, Message
from discord.ext import commands
from discord.ext.commands import hybrid_command, hybrid_group
from discord.ui import Button, View, button
from helpers.bot import PretendInstances
from helpers.context import Context


class ConfirmView(View):
    def __init__(self, ctx: Context, id: int):
        super().__init__()
        self.ctx = ctx
        self.id = id

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.followup.send(
                f"You can't manage this embed.", ephemeral=True
            )
            return False
        return True

    @button(label="Approve", style=ButtonStyle.green)
    async def approve(self, interaction: Interaction, button: Button):
        try:
            os.system(f"pm2 stop {self.id}")
        except Exception as e:
            return await interaction.response.edit_message(
                content=f"Couldn't stop `{self.id}`: {e}", view=None, embed=None
            )

        await interaction.response.edit_message(
            embed=Embed(
                description=f"{interaction.user.mention}: Stopped instance with ID `{self.id}`",
                color=0x808080,
            ),
            view=None,
        )

    @button(label="Decline", style=ButtonStyle.danger)
    async def decline(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(content="ok bai", view=None, embed=None)


class Instances(commands.Cog):
    def __init__(self, bot: PretendInstances):
        self.bot = bot

    async def cog_check(self, ctx: Context):
        if not ctx.author.id in self.bot.owner_ids:
            return False
        return True

    @hybrid_command(name="createinstance", brief="owner only")
    async def createinstance(
        self,
        ctx: Context,
        token: str,
        name: str,
        owner: Member,
        avatar: str,
        banner: str = None,
    ):
        """
        Create an instance of pretend
        """

        async with ctx.channel.typing():
            await create_subprocess_shell(
                f"""
                cd ..
                mkdir instance-{name}
                cd instance-{name}
                git init
                git remote add origin https://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@github.com/PretendServices/PretendInstances.git
                git pull origin main
                echo "token = {token}" >> .env
                echo "proxy_url = http://cekiqbfy-rotate:o3zr0h3c11qe@p.webshare.io:80" >> .env
                echo "\n" >> .env
                echo "port = 5432" >> .env
                echo "password = ak47negro1337" >> .env
                echo "user = postgres" >> .env
                echo "database = {name}" >> .env
                echo "host = localhost" >> .env
                echo "\n" >> .env
                echo "JISHAKU_NO_UNDERSCORE = True" >> .env
                echo "JISHAKU_NO_DM_TRACEBACK = True" >> .env
                echo "\n" >> .env
                echo "weather = 64581e6f1d7d49ae83414270923080" >> .env
                echo "pretend_key = 5447e58a8d549945b51608923f2f748506defafc68a711cf860e377327580873" >> .env
                sudo -i -u postgres psql -c "CREATE DATABASE {name};"
                sudo -i -u postgres
                psql -U postgres -d {name} -f schema.sql
                pm2 start main.py --interpreter=python3 --name=instance-{name}
                """,
                stdout=PIPE,
                stderr=PIPE,
            )
            # os.system("cd ..")
            # os.system(f"mkdir {name}")
            # os.system(f"cd {name}")
            # os.system("git init")
            # os.system("git remote add origin https://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@github.com/PretendServices/Pretendbot.git")
            # os.system("git pull origin master")
            # os.system(f'echo "token = {token}" >> .env')
            # os.system(f'echo "proxy_url = " >> .env')
            # os.system(f'echo "\n" >> .env')
            # os.system(f'echo "port = 5432" >> .env')
            # os.system(f'echo "password = ak47negro1337" >> .env')
            # os.system(f'echo "user = postgres" >> .env')
            # os.system(f'echo "database = {name}" >> .env')
            # os.system(f'echo "host = localhost" >> .env')
            # os.system(f'echo "\n" >> .env')
            # os.system(f'echo "JISHAKU_NO_UNDERSCORE = True" >> .env')
            # os.system(f'echo "JISHAKU_NO_DM_TRACEBACK = True" >> .env')
            # os.system(f'echo "\n" >> .env')
            # os.system(f'echo "weather = 64581e6f1d7d49ae83414270923080" >> .env')
            # os.system(f'echo "pretend_key = 5447e58a8d549945b51608923f2f748506defafc68a711cf860e377327580873" >> .env')
            # os.system(f"sudo -i -u postgres")
            # os.system(f"psql")
            # os.system(f"CREATE DATABASE {name};")
            # os.system("exit")
            # os.system(f"psql -U postgres -d {name} -f schema.sql")
            # os.system("exit")
            # os.system(f"pm2 start main.py --interpreter=python3 --name=instance-{name}")

    @hybrid_command(name="instances", brief="owner only")
    async def instances(self, ctx: Context):
        """
        Get a list of active instances
        """

        message = copy(ctx.message)
        message.content = message.content.replace(
            ctx.invoked_with, "jishaku shell pm2 list"
        )

        await self.bot.process_commands(message)

    @hybrid_group(name="instance", brief="owner only", invoke_without_command=True)
    async def instance(self, ctx: Context):
        """
        Manage instances
        """

        await ctx.send(f"`;instance stop <id>` `;instance start <id>`")

    @instance.command(name="start", brief="owner only")
    async def instance_start(self, ctx: Context, id: int):
        try:
            os.system(f"pm2 start {id}")
        except Exception as e:
            return await ctx.send(f"Couldn't start {id}: {e}")

        await ctx.send_success(f"Started instance `{id}`")

    @instance.command(name="stop", brief="owner only")
    async def instance_stop(self, ctx: Context, id: int):
        """
        Stop an instance with pm2
        """

        view = ConfirmView(ctx, id)
        await ctx.send(
            embed=Embed(
                description=f"Are you sure you want to **stop** the instance with ID `{id}`?",
                color=0x808080,
            ),
            view=view,
        )

    @instance.command(name="restart", brief="owner only")
    async def instance_restart(self, ctx: Context, id: int):
        """
        Restart an instance
        """

        async with ctx.channel.typing():
            os.system(f"pm2 restart {id}")
            await ctx.message.add_reaction("✅")


async def setup(bot: PretendInstances):
    await bot.add_cog(Instances(bot))
