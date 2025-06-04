import json
import asyncio
import discord

from discord import Embed, ButtonStyle, Interaction
from discord.ui import View, Button, button

from modules.styles import emojis, colors

class GiveawayView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(emoji="🎉", style=ButtonStyle.blurple, custom_id="persistent:join_gw")
    async def join_gw(self, interaction: Interaction, button: Button):
        try:
            await interaction.response.defer(ephemeral=True)
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            return
        try:
            check = await interaction.client.db.fetchrow("SELECT * FROM giveaway WHERE guild_id = $1 AND message_id = $2", interaction.guild.id, interaction.message.id)
            if check is None:
                return await interaction.followup.send("This giveaway does not exist or has been removed.", ephemeral=True)
            if check["required_ignore"] is not None:
                required_ignore = interaction.guild.get_role(int(check["required_ignore"]))
                if required_ignore in interaction.user.roles:
                    return await interaction.followup.send(f"You can't join this giveaway with {required_ignore.mention} role.", ephemeral=True)
            if check["required_role"] is not None:
                required_role = interaction.guild.get_role(int(check["required_role"]))
                if required_role not in interaction.user.roles:
                    return await interaction.followup.send(f"You need the {required_role.mention} role to join this giveaway.", ephemeral=True)
            if check["required_messages"] is not None:
                required_messages = check["required_messages"]
                user_messages = await interaction.client.db.fetchval("SELECT SUM(message_count) FROM activity_messages WHERE user_id = $1 AND server_id = $2", interaction.user.id, interaction.guild.id)
                if user_messages is None or user_messages < required_messages:
                    return await interaction.followup.send(f"You need to send **{required_messages} messages** in this server to join this giveaway.", ephemeral=True)
            if check["required_level"] is not None:
                required_level = check["required_level"]
                user_level = await interaction.client.db.fetchval("SELECT level FROM level_user WHERE user_id = $1 AND guild_id = $2", interaction.user.id, interaction.guild.id)
                if user_level is None or user_level < required_level:
                    return await interaction.followup.send(f"You need to be **level {required_level}** to join this giveaway.", ephemeral=True)
            lis = json.loads(check["members"])
            double_chance = False
            if check["required_bonus"] is not None:
                bonus_role_id = int(check["required_bonus"])
                bonus_role = interaction.guild.get_role(bonus_role_id)
                if bonus_role and bonus_role in interaction.user.roles:
                    double_chance = True
            if check["required_invites"] is not None:
                required_invites = check["required_invites"]
                invites = await self.bot.db.fetchrow("SELECT * FROM invites WHERE guild_id = $1 AND user_id = $2", interaction.guild.id, interaction.user.id)
                if invites:
                    user_invites = invites['regular_count'] + invites['bonus']
                else:
                    user_invites = 0
                if user_invites is None or user_invites < required_invites:
                    return await interaction.followup.send(f"You need to invite **{required_invites} members** to this server to join this giveaway.", ephemeral=True)
            if interaction.user.id in lis:
                button1 = Button(label="Leave the Giveaway", style=ButtonStyle.danger)
                async def button1_callback(inter: Interaction):
                    try:
                        await inter.response.defer(ephemeral=True)
                        lis[:] = [user for user in lis if user != interaction.user.id]
                        await interaction.client.db.execute(
                            "UPDATE giveaway SET members = $1 WHERE guild_id = $2 AND message_id = $3", 
                            json.dumps(lis), inter.guild.id, interaction.message.id
                        )
                        try:
                            embed = interaction.message.embeds[0]
                            embed.set_field_at(0, name="Entries", value=f"{len(set(lis))}")
                            await interaction.message.edit(embed=embed)
                        except discord.errors.HTTPException as e:
                            if e.code == 429:
                                await asyncio.sleep(2)
                                try:
                                    embed = interaction.message.embeds[0]
                                    embed.set_field_at(0, name="Entries", value=f"{len(set(lis))}")
                                    await interaction.message.edit(embed=embed)
                                except Exception:
                                    pass
                        
                        left_embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: You left the giveaway")
                        await inter.followup.send(embed=left_embed, ephemeral=True)
                    except (discord.errors.NotFound, discord.errors.InteractionResponded):
                        pass
                button1.callback = button1_callback
                vi = View()
                vi.add_item(button1)
                already_embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are already in this giveaway")
                return await interaction.followup.send(embed=already_embed, view=vi, ephemeral=True)
            lis.append(interaction.user.id)
            if double_chance:
                lis.append(interaction.user.id)
            await interaction.client.db.execute(
                "UPDATE giveaway SET members = $1 WHERE guild_id = $2 AND message_id = $3", 
                json.dumps(lis), interaction.guild.id, interaction.message.id
            )
            try:
                embed = interaction.message.embeds[0]
                embed.set_field_at(0, name="Entries", value=f"{len(set(lis))}")
                await interaction.message.edit(embed=embed)
            except discord.errors.HTTPException as e:
                if e.code == 429:
                    await asyncio.sleep(2)
                    try:
                        embed = interaction.message.embeds[0]
                        embed.set_field_at(0, name="Entries", value=f"{len(set(lis))}")
                        await interaction.message.edit(embed=embed)
                    except Exception:
                        pass
            joined_embed = Embed(
                color=colors.SUCCESS, 
                description=f"{emojis.APPROVE} {interaction.user.mention}: You joined the giveaway with **double chances**!" 
                if double_chance else f"{emojis.APPROVE} {interaction.user.mention}: You joined the giveaway"
            )
            await interaction.followup.send(embed=joined_embed, ephemeral=True)
        except Exception as e:
            try:
                error_msg = f"An error occurred: {str(e)}"
                if not interaction.response.is_done():
                    await interaction.followup.send(error_msg, ephemeral=True)
            except:
                pass

    @button(label="Participants", style=ButtonStyle.secondary, custom_id="persistent:show_participants")
    async def show_participants(self, interaction: Interaction, button: Button):
        try:
            await interaction.response.defer(ephemeral=True)
            ctx = await self.bot.get_context(interaction.message)
            check = await interaction.client.db.fetchrow("SELECT members FROM giveaway WHERE guild_id = $1 AND message_id = $2", interaction.guild.id, interaction.message.id)
            if not check:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: This giveaway does not exist or has been removed."), ephemeral=True)
            members = json.loads(check["members"])
            member_count = {}
            for member_id in members:
                if member_id not in member_count:
                    member_count[member_id] = 1
                else:
                    member_count[member_id] += 1
            member_mentions = [f"<@{mid}> {'(Bonus)' if count > 1 else ''}" for mid, count in member_count.items()]
            if not member_mentions:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Giveaway has no participants yet."), ephemeral=True)
            try:
                await ctx.paginate(member_mentions, title="Giveaway Participants", author={"name": interaction.guild.name, "icon_url": interaction.guild.icon.url if interaction.guild.icon else None}, author_only=False, interaction=interaction, ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Error displaying participants: {str(e)}", ephemeral=True)
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            return
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
            except:
                pass

class GiveawayEndedView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Participants", style=ButtonStyle.secondary, custom_id="persistent:show_participants_ended")
    async def show_participants(self, interaction: Interaction, button: Button):
        try:
            await interaction.response.defer(ephemeral=True)
            ctx = await self.bot.get_context(interaction.message)
            check = await interaction.client.db.fetchrow("SELECT members FROM giveaway_ended WHERE channel_id = $1 AND message_id = $2", interaction.channel.id, interaction.message.id)
            if not check:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: This giveaway does not exist."), ephemeral=True)
            members = json.loads(check["members"])
            member_count = {}
            for member_id in members:
                if member_id not in member_count:
                    member_count[member_id] = 1
                else:
                    member_count[member_id] += 1
            member_mentions = [f"<@{mid}> {'(Bonus)' if count > 1 else ''}" for mid, count in member_count.items()]
            if not member_mentions:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Giveaway has no participants."), ephemeral=True)
            try:
                await ctx.paginate(member_mentions, title="Giveaway Participants", author={"name": interaction.guild.name, "icon_url": interaction.guild.icon.url if interaction.guild.icon else None}, author_only=False, interaction=interaction, ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Error displaying participants: {str(e)}", ephemeral=True)
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            return
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
            except:
                pass