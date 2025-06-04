import discord
import datetime
from discord.ui import View, Button, Modal
from discord import ButtonStyle, Interaction, Embed

class SuggestionView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def get_votes(self, message_id):
        votes = await self.bot.db.fetch(
            """SELECT vote_type FROM suggestion_votes 
            WHERE message_id = $1""",
            message_id
        )
        upvotes = len([v for v in votes if v['vote_type'] == 1])
        downvotes = len([v for v in votes if v['vote_type'] == -1])
        return upvotes, downvotes

    async def update_vote_count(self, message):
        upvotes, downvotes = await self.get_votes(message.id)
        embed = message.embeds[0]
        
        for i, field in enumerate(embed.fields):
            if field.name == "Votes":
                embed.set_field_at(
                    i,
                    name="Votes",
                    value=f"👍 `{upvotes}` • 👎 `{downvotes}`",
                    inline=False
                )
                break
        
        await message.edit(embed=embed)

    async def handle_vote(self, interaction: Interaction, vote_type: int):
        current_vote = await self.bot.db.fetchval(
            """SELECT vote_type FROM suggestion_votes 
            WHERE message_id = $1 AND user_id = $2""",
            interaction.message.id,
            interaction.user.id
        )

        embed = Embed(color=discord.Color.green())

        if current_vote == vote_type:  
            await self.bot.db.execute(
                """DELETE FROM suggestion_votes 
                WHERE message_id = $1 AND user_id = $2""",
                interaction.message.id,
                interaction.user.id
            )
            embed.description = "Your vote has been removed!"
        else:  
            await self.bot.db.execute(
                """INSERT INTO suggestion_votes (guild_id, message_id, user_id, vote_type)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (message_id, user_id) 
                DO UPDATE SET vote_type = $4""",
                interaction.guild.id,
                interaction.message.id,
                interaction.user.id,
                vote_type
            )
            embed.description = "Your vote has been recorded!"

        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.update_vote_count(interaction.message)

    @discord.ui.button(
        label="Upvote", 
        style=ButtonStyle.green, 
        custom_id="suggest_upvote",
        row=0
    )
    async def upvote(self, interaction: Interaction, button: Button):
        await self.handle_vote(interaction, 1)

    @discord.ui.button(
        label="Downvote", 
        style=ButtonStyle.red, 
        custom_id="suggest_downvote",
        row=0
    )
    async def downvote(self, interaction: Interaction, button: Button):
        await self.handle_vote(interaction, -1)

    @discord.ui.button(
        label="Create Suggestion", 
        style=ButtonStyle.blurple, 
        custom_id="suggest_create",
        row=0
    )
    async def create_suggestion(self, interaction: Interaction, button: Button):
        settings = await self.bot.db.fetchrow(
            "SELECT anonymous_allowed FROM suggestion WHERE guild_id = $1",
            interaction.guild.id
        )
        await interaction.response.send_modal(SuggestModal(
            anonymous_allowed=settings.get('anonymous_allowed', False)
        ))

class SuggestModal(Modal, title="Create a Suggestion"):
    def __init__(self, anonymous_allowed: bool = False):
        super().__init__()
        self.anonymous_allowed = anonymous_allowed

        self.add_item(discord.ui.TextInput(
            label="Title",
            placeholder="Brief summary of your suggestion (optional)",
            max_length=100,
            required=False,
            style=discord.TextStyle.short
        ))

        self.add_item(discord.ui.TextInput(
            label="Description",
            placeholder="Detailed explanation of your suggestion (No links allowed)",
            style=discord.TextStyle.long,
            required=True,
            max_length=4000
        ))

        if anonymous_allowed:
            self.add_item(discord.ui.TextInput(
                label="Anonymous Suggestion",
                placeholder="Type 'yes' to make anonymous (Server allows anonymous suggestions)",
                required=False,
                max_length=3,
                style=discord.TextStyle.short
            ))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if "http" in self.children[1].value.lower():
                return await interaction.response.send_message(
                    "Links are not allowed in suggestions!", ephemeral=True
                )

            suggestion_data = await interaction.client.db.fetchrow(
                """
                UPDATE suggestion 
                SET suggestion_id = COALESCE(suggestion_id, 0) + 1 
                WHERE guild_id = $1 
                RETURNING *
                """,
                interaction.guild.id
            )
            
            if not suggestion_data:
                return await interaction.response.send_message(
                    "Suggestions are not enabled in this server!", ephemeral=True
                )

            channel = interaction.guild.get_channel(suggestion_data["channel_id"])
            count = suggestion_data["suggestion_id"]
            is_anonymous = (
                self.anonymous_allowed and 
                len(self.children) > 2 and 
                self.children[2].value.lower() == "yes"
            )

            embed = Embed(
                description=self.children[1].value,
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            if self.children[0].value:
                embed.title = self.children[0].value

            embed.set_author(
                name=f"Suggestion #{count}" + (" (Anonymous)" if is_anonymous else ""),
                icon_url=interaction.guild.icon
            )

            embed.add_field(
                name="Votes",
                value=f"👍 `0` • 👎 `0`",
                inline=False
            )

            if not is_anonymous:
                embed.set_footer(
                    text=f"Suggested by {interaction.user}",
                    icon_url=interaction.user.display_avatar.url
                )
            else:
                embed.set_footer(text="Anonymous Suggestion")

            msg = None
            if isinstance(channel, discord.ForumChannel):
                thread_name = self.children[0].value if self.children[0].value else f"Suggestion #{count}"
                if not self.children[0].value:
                    thread_name = f"Suggestion #{count}"
                else:
                    thread_name = f"{self.children[0].value} #{count}"
                
                thread = await channel.create_thread(
                    name=thread_name,
                    content="",
                    embed=embed,
                    view=SuggestionView(interaction.client)
                )
                msg = thread.message
            else:
                msg = await channel.send(embed=embed, view=SuggestionView(interaction.client))
                if suggestion_data.get("thread_enabled", False):
                    await msg.create_thread(
                        name=f"Suggestion #{count} Discussion",
                        auto_archive_duration=1440
                    )

            await interaction.client.db.execute(
                """UPDATE suggestion 
                SET suggestion_id = $1 
                WHERE guild_id = $2""",
                count,
                interaction.guild.id
            )

            await interaction.client.db.execute(
                """INSERT INTO suggestion_entries 
                (guild_id, message_id, author_id, suggestion_id, is_anonymous)
                VALUES ($1, $2, $3, $4, $5)""",
                interaction.guild.id,
                msg.id if msg else 0,
                interaction.user.id,
                count,
                is_anonymous
            )

            success_embed = Embed(
                title="✅ Suggestion Posted",
                description=(
                    f"Your suggestion has been posted in {channel.mention}\n\n"
                    "**Note:** To include images in your suggestions, "
                    "please use the `/suggest` command instead."
                ),
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=success_embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"Error submitting suggestion: {str(e)}", ephemeral=True
            )