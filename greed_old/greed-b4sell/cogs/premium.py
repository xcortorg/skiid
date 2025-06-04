import base64
from datetime import datetime
import io
import os
from random import choice
import time
import discord
from discord.ext.commands import Cog, command, group, CommandError
from discord.ext import commands
from discord import User, Member, Embed, File, Client
from aiohttp import ClientSession
from typing import Union, Optional, List
from typing import Union, Optional, List
from tool.important.subclasses.context import Context
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import textwrap
import aiohttp
from tool.worker import offloaded
import json
import emoji  # For converting regular emojis
import re  # For detecting slurs and custom emojis
from anime_api.apis import HmtaiAPI
from anime_api.apis.hmtai.objects import Image
from anime_api.apis.hmtai.types import ImageCategory
from collections import defaultdict


@offloaded
def collage_(_images: List[bytes]) -> List[bytes]:
    from math import sqrt
    from PIL import Image
    from io import BytesIO

    def _collage_paste(image: Image, x: int, y: int, background: Image):
        background.paste(
            image,
            (
                x * 256,
                y * 256,
            ),
        )

    if not _images:
        return None

    def open_image(image: bytes):
        return Image.open(BytesIO(image)).convert("RGBA").resize((300, 300))
    
    images = [open_image(i) for i in _images]
    rows = int(sqrt(len(images)))
    columns = (len(images) + rows - 1) // rows

    background = Image.new(
        "RGBA",
        (
            columns * 256,
            rows * 256,
        ),
    )
    for i, image in enumerate(images):
        _collage_paste(image, i % columns, i // columns, background)

    buffer = BytesIO()
    background.save(
        buffer,
        format="png",
    )
    buffer.seek(0)

    background.close()
    for image in images:
        image.close()
    return buffer.getvalue()

class premium(commands.Cog):
    def __init__(self, bot: Client):
        self.bot = bot
        self.nsfw_embeds = defaultdict(list)
        self.api = HmtaiAPI()
        self.nickname_toggle_cache = {}
        self.gang_logs_webhook_url = "https://discord.com/api/webhooks/1330841749035417670/X8nCjROXq3CVMOuIlFtLdigomCmyG3Fwe7O1kWu2M7sZLhDw677dlG3Hx3QA5CWR2uqS"

    async def get_data(self, user: User) -> tuple:
        async with ClientSession() as session:
            async with session.get(user.display_avatar.url) as response:
                data = await response.read()
                content_type = response.headers.get('Content-Type')
                if not content_type:
                    content_type = 'image/png'  # default fallback
        return data, content_type
    
    async def cog_load(self):
        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS avatars (
                user_id BIGINT,
                content_type TEXT,
                avatar BYTEA,
                id TEXT,
                ts TIMESTAMP DEFAULT NOW()
            )
            """
        )
    

    # async def fetch_random_avatars(self, count: int):
    #     """Fetches random avatars from the database."""
    #     query = """
    #     SELECT avatar, content_type 
    #     FROM avatars 
    #     ORDER BY RANDOM() 
    #     LIMIT $1
    #     """
    #     return await self.bot.db.fetch(query, count)


    # Define the command template to minimize repetition:
    async def get_image(self, ctx, category: str, tag_name: str):
        """Helper function to fetch an image for any provided category."""
        # Check if the user is a booster
        result = await self.bot.db.fetchrow(
            """SELECT * FROM boosters WHERE user_id = $1""", ctx.author.id
        )
        if not result:
            await ctx.fail(
                f"You are not boosting [/greedbot](https://discord.gg/greedbot), boost the server to use this command"
            )
            return

        # Check if the command is invoked in an NSFW channel
        if not ctx.channel.is_nsfw():
            return await ctx.fail(
                f"This command can only be used in **NSFW** channels. Do ,nsfw to enable nsfw in a channel"
            )

        try:
            # Fetch random image based on the category tag without awaiting the Image object
            image: Image = self.api.get_random_image(
                getattr(ImageCategory.NSFW, tag_name.upper())
            )

            # Embed the image
            embed = Embed(
                title=f"enjoy some {tag_name}",
                color=self.bot.color,
                description=image.url,
            )
            embed.set_image(url=image.url)

            # Save embed for deletion later when channel switches to non-NSFW
            self.nsfw_embeds[ctx.channel.id].append(image.url)

            # Send the embed to the channel
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")


    async def is_premium(self, user: Member) -> bool:
        return await self.bot.db.fetchrow("SELECT * FROM premium_users WHERE user_id = $1", user.id)
    
    async def premium_only(self, ctx: commands.Context):
        if not await self.is_premium(ctx.author):
            await ctx.send("You need to be a **premium user** to use this command.")
            raise commands.CheckFailure

    # @commands.Cog.listener("on_user_update")
    # async def on_avatar_change(self, before: User, after: User):
    #     if before.display_avatar == after.display_avatar:
    #         return
    #     avatar, content_type = await self.get_data(after)
    #     await self.bot.db.execute(
    #         "INSERT INTO avatars (user_id, content_type, avatar, id) VALUES($1, $2, $3, $4)",
    #         after.id, content_type, avatar, after.display_avatar.key
    #     )



    @commands.group(name="random", invoke_without_command=True)
    async def random_group(self, ctx):
        """Group for random NSFW images."""
        return await ctx.send_help(ctx.command.qualified_name)

    @random_group.command(
        name="ass", brief="Get a random 'ass' image.", usage=",random ass"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomass(self, ctx):
        await self.get_image(ctx, "ass", "ASS")

    @random_group.command(
        name="anal", brief="Get a random 'anal' image.", usage=",random anal"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomanal(self, ctx):
        await self.get_image(ctx, "anal", "ANAL")

    @random_group.command(
        name="bdsm", brief="Get a random 'bdsm' image.", usage=",random bdsm"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randombdsm(self, ctx):
        await self.get_image(ctx, "bdsm", "BDSM")

    @random_group.command(
        name="classic", brief="Get a random 'nsfw' image.", usage=",random classic"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomclassic(self, ctx):
        await self.get_image(ctx, "classic", "CLASSIC")

    @random_group.command(
        name="cum", brief="Get a random 'nsfw' image.", usage=",random cum"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomcum(self, ctx):
        await self.get_image(ctx, "cum", "CUM")

    @random_group.command(
        name="creampie", brief="Get a random 'nsfw' image.", usage=",random creampie"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomcreampie(self, ctx):
        await self.get_image(ctx, "creampie", "CREAMPIE")

    @random_group.command(
        name="manga", brief="Get a random 'nsfw' image.", usage=",random manga"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randommanga(self, ctx):
        await self.get_image(ctx, "manga", "MANGA")

    @random_group.command(
        name="femdom", brief="Get a random 'nsfw' image.", usage=",random femdom"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomfemdom(self, ctx):
        await self.get_image(ctx, "femdom", "FEMDOM")

    @random_group.command(
        name="hentai", brief="Get a random 'nsfw' image.", usage=",random hentai"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomhentai(self, ctx):
        await self.get_image(ctx, "hentai", "HENTAI")

    @random_group.command(
        name="masturbation",
        brief="Get a random 'nsfw' image.",
        usage=",random masturbation",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randommasturbation(self, ctx):
        await self.get_image(ctx, "masturbation", "MASTURBATION")

    @random_group.command(
        name="pussy", brief="Get a random 'nsfw' image.", usage=",random pussy"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randompussy(self, ctx):
        await self.get_image(ctx, "pussy", "PUSSY")

    @random_group.command(
        name="blowjob", brief="Get a random 'nsfw' image.", usage=",random blowjob"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomblowjob(self, ctx):
        await self.get_image(ctx, "blowjob", "BLOWJOB")

    @random_group.command(
        name="boobjob", brief="Get a random 'nsfw' image.", usage=",random boobjob"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomboobjob(self, ctx):
        await self.get_image(ctx, "boobjob", "BOOBJOB")

    @random_group.command(
        name="boobs", brief="Get a random 'nsfw' image.", usage=",random boobs"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomboobs(self, ctx):
        await self.get_image(ctx, "boobs", "BOOBS")

    @random_group.command(
        name="thighs", brief="Get a random 'nsfw' image.", usage=",random thighs"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomthighs(self, ctx):
        await self.get_image(ctx, "thighs", "THIGHS")

    @random_group.command(
        name="ahegao", brief="Get a random 'nsfw' image.", usage=",random ahegao"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomahegao(self, ctx):
        await self.get_image(ctx, "ahegao", "AHEGAO")

    @random_group.command(
        name="tentacles", brief="Get a random 'nsfw' image.", usage=",random tentacles"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomtentacles(self, ctx):
        await self.get_image(ctx, "tentacles", "TENTACLES")

    @random_group.command(
        name="gif", brief="Get a random 'gif' image.", usage=",random gif"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def randomgif(self, ctx):
        await self.get_image(ctx, "gif", "GIF")


    @commands.group(invoke_without_command=True)
    async def gang(self, ctx):
        """Base command for the Gang system."""
        return await ctx.send_help(ctx.command.qualified_name)

    @gang.command(name="toggle")
    async def gang_toggle(self, ctx):
        """Toggle the nickname tag for the user based on their gang affiliation."""
        # Check if the user is in a gang
        user_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gang_members WHERE user_id = $1", ctx.author.id
        )

        if not user_gang:
            await ctx.fail("You are not in any gang.")
            return

        gang_name = user_gang["gang_name"]

        # Check if the user has the toggle state set
        user_toggle = await self.bot.db.fetchrow(
            "SELECT toggle FROM gang_members WHERE user_id = $1 AND gang_name = $2",
            ctx.author.id,
            gang_name,
        )

        # If no toggle setting, we'll assume it's off by default
        if user_toggle is None:
            await self.bot.db.execute(
                "INSERT INTO gang_members (user_id, gang_name, role, toggle) VALUES ($1, $2, $3, $4)",
                ctx.author.id,
                gang_name,
                "Member",
                "off",
            )
            user_toggle = {"toggle": "off"}  # Default to "off"

        # Toggle action: Switch between 'on' and 'off'
        if user_toggle["toggle"] == "off":
            # Toggle to 'on', change nickname
            new_nickname = f"[{gang_name[0].upper()}{gang_name[-1].upper()}] {ctx.author.display_name}"
            try:
                await ctx.author.edit(nick=new_nickname)
            except discord.Forbidden:
                await ctx.fail("I don't have permission to change your nickname.")
                return
            # Update toggle in the database
            await self.bot.db.execute(
                "UPDATE gang_members SET toggle = 'on' WHERE user_id = $1 AND gang_name = $2",
                ctx.author.id,
                gang_name,
            )
            await ctx.success(
                f"Your gang tag has been added to your nickname: {new_nickname}"
            )

        else:
            # Toggle to 'off', revert nickname
            # Remove the gang tag from their nickname
            new_nickname = ctx.author.display_name.replace(
                f"[{gang_name[0]}{gang_name[-1]}] ", ""
            )
            try:
                await ctx.author.edit(nick=new_nickname)
            except discord.Forbidden:
                await ctx.fail("I don't have permission to change your nickname.")
                return
            # Update toggle in the database
            await self.bot.db.execute(
                "UPDATE gang_members SET toggle = 'off' WHERE user_id = $1 AND gang_name = $2",
                ctx.author.id,
                gang_name,
            )
            await ctx.success(f"Your gang tag has been removed from your nickname.")

    @gang.command(name="tag")
    async def tag_info(self, ctx):
        """View your gang's tag."""
        user_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gang_members WHERE user_id = $1",
            ctx.author.id,
        )

        if not user_gang:
            await ctx.fail("You are not in a gang.")
            return

        gang_name = user_gang["gang_name"]
        tag = self.generate_tag(gang_name)
        await ctx.success(f"Your gang tag is **{tag}**.")

    @gang.command(name="create", aliases=["gangc"])
    async def gang_create(self, ctx, gang_name: str):
        """Create a new gang."""
        # Check if the user is a booster
        is_booster = await self.bot.db.fetchrow(
            "SELECT 1 FROM boosters WHERE user_id = $1", ctx.author.id
        )

        if not is_booster:
            await ctx.fail(
                "You are not boosting [/greedbot](http://discord.gg/greedbot). Only boosters can create gangs."
            )
            return

        # Check if the gang name is 5 characters or fewer
        if len(gang_name) > 5:
            await ctx.fail(
                "The gang name must be 5 characters or fewer. Please choose a shorter name."
            )
            return

        if not self.validate_gang_name(gang_name):
            await ctx.fail(
                "The gang name contains prohibited or offensive content. Please choose another name."
            )
            return

        # Check if the user already owns a gang
        existing_ownership = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gangs WHERE owner_id = $1", ctx.author.id
        )
        if existing_ownership:
            await ctx.warning(
                f"You already own the gang '{existing_ownership['gang_name']}'. Disband it to create a new one."
            )
            return

        # Check if the gang name is already taken
        existing_gang = await self.bot.db.fetchrow(
            "SELECT 1 FROM gangs WHERE gang_name = $1", gang_name
        )
        if existing_gang:
            await ctx.fail(
                f"A gang with the name **{gang_name}** already exists. Please choose another name."
            )
            return

        # Create the gang
        created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await self.bot.db.execute(
            """
            INSERT INTO gangs (gang_name, owner_id, created_at, banner_url)
            VALUES ($1, $2, $3, $4)
            """,
            gang_name,
            ctx.author.id,
            created_at,
            None,
        )
        await self.bot.db.execute(
            "INSERT INTO gang_members (user_id, gang_name, role) VALUES ($1, $2, $3)",
            ctx.author.id,
            gang_name,
            "Owner",
        )

        # Log the gang creation
        await self.send_gang_log(
            f"**Gang Created**: **{gang_name}** by {ctx.author} (ID: {ctx.author.id})"
        )
        await ctx.success(
            f"Gang **{gang_name}** has been successfully created by {ctx.author.mention}."
        )

    @gang.command(name="disband", aliases=["gangd"])
    async def gang_disband(self, ctx):
        """Disband your gang."""
        owner_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gangs WHERE owner_id = $1", ctx.author.id
        )

        if not owner_gang:
            await ctx.fail("You do not own a gang to disband.")
            return

        gang_name = owner_gang["gang_name"]

        await self.bot.db.execute("DELETE FROM gangs WHERE gang_name = $1", gang_name)
        await self.bot.db.execute(
            "DELETE FROM gang_members WHERE gang_name = $1", gang_name
        )

        await ctx.success(f"The gang **{gang_name}** has been disbanded.")

    @gang.command(name="setbanner", aliases=["gangsb"])
    async def gang_set_banner(self, ctx, banner_url: str):
        """Set a banner for your gang."""
        owner_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gangs WHERE owner_id = $1", ctx.author.id
        )
        if not owner_gang:
            await ctx.fail("You do not own a gang to set a banner.")
            return

        gang_name = owner_gang["gang_name"]
        await self.bot.db.execute(
            "UPDATE gangs SET banner_url = $1 WHERE gang_name = $2",
            banner_url,
            gang_name,
        )

        # Log the banner update
        await self.send_gang_log(
            f"**Banner Updated**: Gang **{gang_name}** by {ctx.author} (ID: {ctx.author.id}) - New Banner URL: {banner_url}"
        )
        await ctx.success(f"Banner for gang **{gang_name}** has been set.")

    @gang.command(name="leave", aliases=["gangleave"])
    async def gang_leave(self, ctx):
        """Leave your current gang."""
        # Check if the user is in a gang
        user_gang = await self.bot.db.fetchrow(
            "SELECT gang_name, role FROM gang_members WHERE user_id = $1", ctx.author.id
        )

        if not user_gang:
            await ctx.fail("You are not in any gang.")
            return

        gang_name = user_gang["gang_name"]
        user_role = user_gang["role"]

        # Prevent the owner from leaving their own gang
        if user_role == "Owner":
            await ctx.fail(
                f"You are the owner of the gang **{gang_name}**. You must transfer ownership or disband the gang before leaving."
            )
            return

        # Remove the user from the gang
        await self.bot.db.execute(
            "DELETE FROM gang_members WHERE user_id = $1 AND gang_name = $2",
            ctx.author.id,
            gang_name,
        )

        # Notify success
        await ctx.success(f"You have successfully left the gang **{gang_name}**.")

        # Log the action
        await self.send_gang_log(
            f"**Member Left**: {ctx.author} (ID: {ctx.author.id}) left the gang **{gang_name}**."
        )

    @gang.command(name="info", aliases=["gangi"])
    async def gang_info(self, ctx):
        """Display information about your gang."""
        user_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gang_members WHERE user_id = $1", ctx.author.id
        )

        if not user_gang:
            await ctx.fail("You are not in a gang.")
            return

        gang_name = user_gang["gang_name"]

        gang = await self.bot.db.fetchrow(
            "SELECT owner_id, banner_url, created_at FROM gangs WHERE gang_name = $1",
            gang_name,
        )

        if not gang:
            await ctx.fail("Could not retrieve gang details.")
            return

        owner_id, banner_url, created_at = gang

        created_at_formatted = datetime.strptime(
            created_at, "%Y-%m-%d %H:%M:%S"
        ).strftime("%B %d, %Y at %I:%M %p")
        owner = ctx.guild.get_member(owner_id) or f"<@{owner_id}>"

        embed = discord.Embed(description=f"**{gang_name}**", color=self.bot.color)

        if banner_url:
            embed.set_image(url=banner_url)

        embed.add_field(name="Owner", value=f"**{owner}** 👑", inline=False)

        members = await self.bot.db.fetch(
            "SELECT user_id, role FROM gang_members WHERE gang_name = $1", gang_name
        )

        member_list = "\n".join([f"<@{m[0]}> - {m[1]}" for m in members])
        embed.add_field(name="Members", value=member_list or "None", inline=False)

        embed.set_footer(text=f"Time Created: {created_at_formatted}")

        await ctx.send(embed=embed)

    @gang.command(name="promote", aliases=["gangp"])
    async def gang_promote(self, ctx, member: discord.Member):
        """Promote a gang member to admin."""
        owner_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gangs WHERE owner_id = $1", ctx.author.id
        )

        if not owner_gang:
            await ctx.fail("You must own a gang to promote members.")
            return

        gang_name = owner_gang["gang_name"]

        member_gang = await self.bot.db.fetchrow(
            "SELECT role FROM gang_members WHERE user_id = $1 AND gang_name = $2",
            member.id,
            gang_name,
        )

        if not member_gang or member_gang["role"] == "Admin":
            await ctx.fail(
                f"{member.mention} is either not in your gang or is already an Admin."
            )
            return

        await self.bot.db.execute(
            "UPDATE gang_members SET role = 'Admin' WHERE user_id = $1 AND gang_name = $2",
            member.id,
            gang_name,
        )

        await ctx.success(f"{member.mention} has been promoted to Admin.")

    @gang.command(name="invite", aliases=["ganginv"])
    async def gang_invite(self, ctx, member: discord.Member):
        """Send an invite to a user to join your gang."""
        inviter_gang = await self.bot.db.fetchrow(
            "SELECT gang_name, role FROM gang_members WHERE user_id = $1", ctx.author.id
        )

        if not inviter_gang or inviter_gang["role"] not in ("Owner", "Admin"):
            await ctx.fail("You must be an Owner or Admin of a gang to invite members.")
            return

        gang_name = inviter_gang["gang_name"]

        member_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gang_members WHERE user_id = $1", member.id
        )

        if member_gang:
            await ctx.fail(
                f"{member.mention} is already in a gang ({member_gang['gang_name']})."
            )
            return

        embed = discord.Embed(
            title=f"Gang Invite: {gang_name}",
            description=f"{member.mention}, you have been invited to join the gang **{gang_name}** by {ctx.author.mention}.",
            color=self.bot.color,
        )

        view = discord.ui.View()

        async def accept_callback(interaction: discord.Interaction):
            if interaction.user.id != member.id:
                await interaction.response.send_message(
                    "This invitation is not for you.", ephemeral=True
                )
                return

            await self.bot.db.execute(
                "INSERT INTO gang_members (user_id, gang_name, role) VALUES ($1, $2, 'Member')",
                member.id,
                gang_name,
            )

            embed.title = f"{member.display_name} joined {gang_name}!"
            embed.description = (
                f"{member.mention} has accepted the invitation to join **{gang_name}**."
            )
            embed.color = self.bot.color

            await interaction.response.edit_message(embed=embed, view=None)

        async def deny_callback(interaction: discord.Interaction):
            if interaction.user.id != member.id:
                await interaction.response.send_message(
                    "This invitation is not for you.", ephemeral=True
                )
                return

            embed.title = f"Invitation Declined: {gang_name}"
            embed.description = (
                f"{member.mention} declined the invitation to join **{gang_name}**."
            )
            embed.color = self.bot.color

            await interaction.response.edit_message(embed=embed, view=None)

        accept_button = discord.ui.Button(
            label="Accept", style=discord.ButtonStyle.green
        )
        accept_button.callback = accept_callback

        deny_button = discord.ui.Button(label="Decline", style=discord.ButtonStyle.red)
        deny_button.callback = deny_callback

        view.add_item(accept_button)
        view.add_item(deny_button)

        await ctx.send(embed=embed, view=view)

    @gang.command(name="transfer", aliases=["gangt"])
    async def gang_transfer(self, ctx, member: discord.Member):
        """Transfer gang ownership to another member."""
        owner_gang = await self.bot.db.fetchrow(
            "SELECT gang_name FROM gangs WHERE owner_id = $1", ctx.author.id
        )

        if not owner_gang:
            await ctx.fail("You must own a gang to transfer ownership.")
            return

        gang_name = owner_gang["gang_name"]

        member_gang = await self.bot.db.fetchrow(
            "SELECT role FROM gang_members WHERE user_id = $1 AND gang_name = $2",
            member.id,
            gang_name,
        )

        if not member_gang:
            await ctx.fail(f"{member.mention} is not a member of your gang.")
            return

        await self.bot.db.execute(
            "UPDATE gangs SET owner_id = $1 WHERE gang_name = $2", member.id, gang_name
        )
        await self.bot.db.execute(
            "UPDATE gang_members SET role = 'Owner' WHERE user_id = $1 AND gang_name = $2",
            member.id,
            gang_name,
        )
        await self.bot.db.execute(
            "UPDATE gang_members SET role = 'Member' WHERE user_id = $1 AND gang_name = $2",
            ctx.author.id,
            gang_name,
        )

        await ctx.success(
            f"Gang ownership of **{gang_name}** has been transferred to {member.mention}."
        )

    @commands.command(
        name="fuck",
        brief="fuck another user (nsfw)",
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def fuck(self, ctx, *, member: Member) -> None:
        """NSFW command to send a random NSFW gif from a local folder."""

        # Check if the user is a donator
        result = await self.bot.db.fetchrow(
            """SELECT * FROM boosters WHERE user_id = $1""", ctx.author.id
        )

        if not result:
            await ctx.fail(
                "You are not boosting [/greedbot](https://discord.gg/greedbot) boost the server to use this command"
            )
            return

        # Check if the command is invoked in an NSFW channel
        if not ctx.channel.is_nsfw():
            return await ctx.fail(
                "This command can only be used in **NSFW** channels. Do ,nsfw to enable nsfw in a channel"
            )

        # Check if the user is trying to interact with themselves
        if ctx.author == member:
            await ctx.fail("You can't interact with yourself! 😳")
            return

        # Path to the folder containing NSFW GIFs
        folder_path = "/root/greed/data/hentai"  # Replace with your folder's path

        try:
            # Get all GIF files from the folder
            gif_files = [f for f in os.listdir(folder_path) if f.endswith(".gif")]

            if not gif_files:
                await ctx.fail("No NSFW GIFs found in the folder.")
                return

            # Randomly select a GIF
            selected_gif = choice(gif_files)
            gif_path = os.path.join(folder_path, selected_gif)

            # Database logic to track interactions
            await self.bot.db.execute(
                """
                CREATE TABLE IF NOT EXISTS freaky (
                    user_id BIGINT,
                    target_id BIGINT,
                    times_fucked INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, target_id)
                )
                """
            )

            # Insert or update interaction in the database
            await self.bot.db.execute(
                """
                INSERT INTO freaky (user_id, target_id, times_fucked)
                VALUES ($1, $2, 1)
                ON CONFLICT(user_id, target_id)
                DO UPDATE SET times_fucked = freaky.times_fucked + 1
                """,
                ctx.author.id,
                member.id,
            )

            # Fetch the updated count of interactions
            result = await self.bot.db.fetchrow(
                """
                SELECT times_fucked FROM freaky
                WHERE user_id = $1 AND target_id = $2
                """,
                ctx.author.id,
                member.id,
            )

            # If no interaction, initialize it to 1
            times_fucked = result["times_fucked"] if result else 1

            # Create an embed message
            embed = Embed(
                description=f"**{ctx.author.mention}** is interacting with **{member.mention}**! 🔥",
                color=self.bot.color,
            )
            embed.set_footer(
                text=f"{ctx.author} has interacted with {member} {times_fucked} times."
            )

            # Attach the GIF to the embed
            with open(gif_path, "rb") as gif_file:
                file = File(gif_file, filename="nsfw.gif")
                embed.set_image(url="attachment://nsfw.gif")

            await ctx.send(embed=embed, file=file)

        except Exception as e:
            await ctx.fail(f"An error occurred: {str(e)}")


   
    # @commands.command(name="generate")
    # @commands.cooldown(1, 10, commands.BucketType.guild)
    # async def prefix_generate(self, ctx: commands.Context):
    #     is_booster = await self.bot.db.fetchrow(
    #         "SELECT 1 FROM boosters WHERE user_id = $1", ctx.author.id
    #     )

    #     if not is_booster:
    #         await ctx.fail(
    #             "You are not boosting [/greedbot](https://discord.gg/greedbot). Boost this server to use this command."
    #         )
    #         return

    #     """Generates a group of random avatars as attachments, only in NSFW channels."""
       
    #     if not ctx.channel.nsfw:
    #         await ctx.warning("This command can only be used in **NSFW** channels.")
    #         return

    #     try:
            
    #         avatars = await self.fetch_random_avatars(8)

            
    #         if not avatars:
    #             await ctx.fail("No avatars are available in the database.")
    #             return

    #         attachments = []
    #         for index, avatar in enumerate(avatars):
                
    #             avatar_data = avatar["avatar"]
    #             content_type = avatar["content_type"]
    #             file_extension = content_type.split("/")[-1]
    #             file_name = f"avatar_{index + 1}.{file_extension}"

    #             file = discord.File(BytesIO(avatar_data), filename=file_name)
    #             attachments.append(file)

            
    #         await ctx.send("Here are 8 random avatars:", files=attachments)

    #     except Exception as e:
    #         await ctx.warn(f"An error occurred: {str(e)}")
    #         raise e  #



    

async def setup(bot: Client):
    await bot.add_cog(premium(bot))