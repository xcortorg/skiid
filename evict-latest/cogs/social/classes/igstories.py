import discord
import asyncio

from managers.paginator import Paginator
from core.client import Context

from typing import List, Optional
from discord import (
    Message, 
    Interaction, 
    Button, 
    Embed, 
    HTTPException
)

from contextlib import suppress


class StoryPaginator(Paginator):
    def __init__(
        self,
        ctx: Context,
        *,
        entries: List[str] | List[dict] | List[Embed],
        files: List[Optional[discord.File]],
        **kwargs
    ):
        super().__init__(ctx, entries=entries, **kwargs)
        self.files = files

    async def start(self, content: str = None) -> Message:
        if not self.entries:
            raise ValueError("No entries were provided.")

        page = self.entries[self.index]
        current_file = self.files[self.index] if self.files else None

        if len(self.entries) == 1:
            self.message = await self.ctx.send(
                content=content if content else None,
                embed=page,
                file=current_file if current_file else None
            )
        
        else:
            self.message = await self.ctx.send(
                content=content if content else None,
                embed=page,
                view=self,
                file=current_file if current_file else None
            )

        return self.message

    async def callback(self, interaction: Interaction, button: Button):
        
        await interaction.response.defer()

        if button.custom_id == "previous":
            self.index = len(self.entries) - 1 if self.index <= 0 else self.index - 1
        
        elif button.custom_id == "next":
            self.index = 0 if self.index >= (len(self.entries) - 1) else self.index + 1
        
        elif button.custom_id == "navigation":
            await self.disable_buttons()
            await self.message.edit(view=self)

            embed = Embed(
                title="Page Navigation",
                description="Reply with the page to skip to.",
            )
            
            prompt = await interaction.followup.send(
                embed=embed, ephemeral=True, wait=True
            )
            
            response: Optional[Message] = None

            try:
                response = await self.ctx.bot.wait_for(
                    "message",
                    timeout=6,
                    check=lambda m: (
                        m.author == interaction.user
                        and m.channel == interaction.channel
                        and m.content.isdigit()
                        and int(m.content) <= len(self.entries)
                    ),
                )
            
            except asyncio.TimeoutError:
                ...
            
            else:
                self.index = int(response.content) - 1
            
            finally:
                for child in self.children:
                    child.disabled = False

                with suppress(HTTPException):
                    await prompt.delete()
                    if response:
                        await response.delete()
        
        elif button.custom_id == "cancel":
            with suppress(HTTPException):
                await self.message.delete()
                await self.ctx.message.delete()
                self.stop()
            
            return

        page = self.entries[self.index]
        current_file = self.files[self.index] if self.files else None
        
        with suppress(HTTPException):
            await self.message.edit(
                embed=page,
                view=self,
                attachments=[current_file] if current_file else []
            )
