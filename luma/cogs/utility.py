import datetime
import re
from typing import Union

import discord
from discord import app_commands
from discord.ext import commands
from managers.bot import Luma
from managers.helpers import Context
from shazamio import Shazam


class Utility(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot

    @commands.command()
    async def upload(self: "Utility", ctx: Context, *, attachment: discord.Attachment):
        """
        Upload an image to our cdn
        (the image only works for 6 hours)
        """
        url = await self.bot.upload_cdn(attachment.url, key=attachment.filename)
        return await ctx.reply(url)

    @commands.hybrid_command(aliases=["av", "pfp"])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def avatar(
        self: "Utility", ctx: Context, *, member: discord.User = commands.Author
    ):
        """
        Get the avatar of a member
        """
        embed = discord.Embed(
            color=await ctx.dominant(member.display_avatar),
            title=f"avatar for {member.name}",
            url=member.display_avatar.url,
        ).set_image(url=member.display_avatar.url)
        await ctx.reply(embed=embed)

    @commands.command()
    async def roles(self: "Utility", ctx: Context):
        """
        Get a list with the server roles
        """
        await ctx.paginate(
            [f"{role.name} - {len(role.members)} members" for role in ctx.guild.roles],
            title=f"Roles ({len(ctx.guild.roles)})",
        )

    @commands.command()
    async def bots(self: "Utility", ctx: Context):
        """
        Get a list with the bots in the server
        """
        await ctx.paginate(
            [f"{m.name} - `({m.id})`" for m in ctx.guild.members if m.bot],
            title=f"Bots ({len(m for m in ctx.guild.members if m.bot)})",
        )

    @commands.command()
    async def bans(self: "Utility", ctx: Context):
        """
        Get a list with the banned members in the server
        """
        bans = [m async for m in ctx.guild.bans()]
        if len(bans) == 0:
            return await ctx.error("No one is banned in this server")

        await ctx.paginate(
            [f"**{m.user}** - `{m.reason or 'No reason provided'}`" for m in bans],
            f"Bans ({len(bans)})",
        )

    @commands.command()
    async def muted(self: "Utility", ctx: Context):
        """
        Get a list of the muted members
        """
        muted = [m for m in ctx.guild.members if m.is_timed_out()]
        if len(muted) == 0:
            return await ctx.error("There are no muted members")

        await ctx.paginate(
            [
                f"{member} - <t:{member.timed_out_until.timestamp()}:R>"
                for member in muted
            ],
            f"Muted members ({len(muted)})",
        )

    @commands.hybrid_command(aliases=["ui", "whois"])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def userinfo(
        self: "Utility",
        ctx: Context,
        member: Union[discord.Member, discord.User] = commands.Author,
    ) -> discord.Message:
        """
        View info abt an user
        """
        about = ""
        if member.activity:
            if isinstance(member.activity, discord.Spotify):
                about += f"<:spotify:1125451479239630929> {member.activity.type.name.capitalize()} to [**{member.activity.title}**]({member.activity.track_url}) by {member.activity.artist}\n"
            else:
                about += f"🎮 {member.activity.type.name.capitalize()} {member.activity.name}\n"

        about += f"Created: {discord.utils.format_dt(member.created_at, style='R')}\n"

        if isinstance(member, discord.Member):
            about += f"Joined: {discord.utils.format_dt(member.joined_at, style='R')}\n"
            if member.premium_since:
                about += f"Boosted: {discord.utils.format_dt(member.premium_since, style='R')}"

        embed = (
            discord.Embed(
                color=await ctx.dominant(member.display_avatar),
                title=member,
                description=about,
            )
            .set_author(
                name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url
            )
            .set_thumbnail(url=member.display_avatar.url)
            .set_footer(text=f"mutuals: {len(member.mutual_guilds)}")
        )
        if isinstance(member, discord.Member):
            if roles := member.roles[1:][::-1]:
                embed.add_field(
                    name=f"Roles ({len(roles)})",
                    value=f"{', '.join(map(str, roles[:5])) + f' (+{len(roles)-5})' if len(roles) > 5 else ', '.join(map(str, roles[:5]))}",
                    inline=False,
                )
        await ctx.reply(embed=embed)

    @commands.command()
    async def shazam(self: "Utility", ctx: Context, *, attachment: discord.Attachment):
        """
        Get the video song
        """
        if not attachment.content_type.startswith("video"):
            return await ctx.error("This is not a video")

        try:
            song = await Shazam().recognize_song(await attachment.read())
            name = song["track"]["share"]["text"]
            link = song["track"]["share"]["href"]
            return await ctx.reply(
                f"<:shazam:1133831097445269504> {ctx.author.mention}: Found [**{name}**]({link})"
            )
        except:
            return await ctx.error("No track found")

    @commands.hybrid_command(aliases=["hex"])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def dominant(
        self: "Utility", ctx: Context, *, attachment: discord.Attachment
    ):
        """
        Get the dominant color of an image
        """
        if not attachment.content_type.startswith("image"):
            return await ctx.error("This is not an image")

        color = hex(await ctx.dominant(attachment.read()))[2:]
        hex_info = await self.bot.session.get(
            "https://www.thecolorapi.com/id", params={"hex": color}
        )
        hex_image = f"https://singlecolorimage.com/get/{color}/200x200"

        embed = (
            discord.Embed(color=int(color, 16))
            .set_author(name=hex_info["name"]["value"], icon_url=hex_image)
            .set_thumbnail(url=hex_image)
            .add_field(name="hex", value=hex_info["hex"]["value"])
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["mc"])
    async def membercount(self: "Utility", ctx: Context):
        """
        Get the membercount
        """
        embed = (
            discord.Embed(color=self.bot.color)
            .set_author(
                name=f"{ctx.guild.name} membercount (+{len([m for m in ctx.guild.members if (datetime.datetime.now() - m.joined_at.replace(tzinfo=None)).total_seconds() < 360*24])})",
                icon_url=ctx.guild.icon,
            )
            .add_field(name="total", value=f"{ctx.guild.member_count:,}")
            .add_field(
                name="members",
                value=f"{len(set(m for m in ctx.guild.members if not m.bot)):,}",
            )
            .add_field(
                name="bots",
                value=f"{len(set(m for m in ctx.guild.members if m.bot)):,}",
            )
        )
        await ctx.reply(embed=embed)

    @commands.command()
    async def inrole(self: "Utility", ctx: Context, *, role: discord.Role):
        """
        See how many people have that role
        """
        if len(role.members) == 0:
            return await ctx.error("No members has this role")

        await ctx.paginate(
            [f"{member} - {member.id}" for member in role.members],
            title=f"Members in {role.name} ({len(role.members)})",
        )

    @commands.command(aliases=["s"])
    async def snipe(self: "Utility", ctx: Context, *, index=1):
        """
        See the latest deleted message
        """
        if not self.bot.cache.get(f"{ctx.channel.id}-snipe"):
            return await ctx.error("No deleted messages in this channel")

        snipes = self.bot.cache.get(f"{ctx.channel.id}-snipe")

        if index > len(snipes):
            return await ctx.error(f"There are only {len(snipes)} snipes here")

        sniped: discord.Message = snipes[::-1][index - 1]
        content = sniped.content
        if sniped.embeds or sniped.attachments:
            content = "This message contains an embeds or an attachment"
        elif re.search(
            r"(https?://)?(www.|canary.|ptb.)?(discord.(gg|io|me|li)|discordapp.com/invite|discord.com/invite)/?[a-zA-Z0-9]+/?",
            sniped.content,
        ):
            content = "This message contains a discord invite"

        embed = (
            discord.Embed(
                color=self.bot.color, description=content, timestamp=sniped.created_at
            )
            .set_author(
                name=sniped.author.name, icon_url=sniped.author.display_avatar.url
            )
            .set_footer(text=f"{index}/{len(snipes)}")
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["cs"])
    @commands.has_guild_permissions(manage_messages=True)
    async def clearsnipes(self: "Utility", ctx: Context):
        """
        Clear the snipes registered in this channel
        """
        self.bot.cache.delete(f"{ctx.channel.id}-snipe")
        await ctx.send("👍")

    @commands.hybrid_command(aliases=["ig"])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def instagram(self: "Utility", ctx: Context, user: str):
        """
        Checks someones instagram
        """
        x = await self.bot.session.get(
            "https://api.fulcrum.lol/instagram", params={"username": user}
        )

        if x.get("detail"):
            return await ctx.error(x["detail"])

        badges = []
        biolinks = []
        if x["is_private"]:
            badges.append("🔒")
        if x["is_verified"]:
            badges.append("<:verified:1140291032987213945>")
        for name, url in x["biolinks"].items():
            biolinks.append(f"{name} - {url}")

        embed = (
            discord.Embed(
                color=self.bot.color,
                title=f"@{x['username']} {''.join(badges)}",
                url=x["url"],
                description=x["bio"],
            )
            .set_thumbnail(url=x["avatar_url"])
            .add_field(name="followers", value=f"{x['followers']:,}")
            .add_field(name="following", value=f"{x['following']:,}")
            .add_field(name="posts", value=x["posts"])
        )

        view = discord.ui.View()
        if x["biolinks"]:
            button = discord.ui.Button(label="biolinks")

            async def callback(interaction: discord.Interaction):
                e = discord.Embed(
                    color=self.bot.color,
                    title=f"@{x['username']} biolinks",
                    description="\n".join(biolinks),
                    url=x["url"],
                ).set_thumbnail(url=x["avatar_url"])

                return await interaction.response.send_message(embed=e, ephemeral=True)

            button.callback = callback
            view.add_item(button)

        await ctx.reply(embed=embed, view=view)


async def setup(bot: Luma):
    return await bot.add_cog(Utility(bot))
