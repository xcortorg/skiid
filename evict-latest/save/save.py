"""
Code that isn't important that is broken will be pasted here.
Mostly irrelevant code that is broken or not needed.
However, it could be worth fixing or using in the future.

-- sin
"""

    # LINKVERTISE_PATTERN = re.compile(
    #     r"https?://(?:www\.)?(?:linkvertise\.com|link-target\.net)/(?P<id>\d+)/(?P<name>[a-zA-Z0-9-]+)(?:\?o=sharing)?"
    # )

    #     @Cog.listener("on_message_without_command")
    #     async def linkvertise_listener(self, ctx: Context) -> Optional[Message]:
    #         match = LINKVERTISE_PATTERN.search(ctx.message.content)
    #         if not match:
    #             return

    #         async with ctx.typing():
    #             response = await self.bot.session.get(
    #                 URL.build(
    #                     scheme="https",
    #                     host="bypass.pm",
    #                     path="/bypass2",
    #                     query={"url": match.group()},
    #                 ),
    #                 proxy=config.CLIENT.WARP,
    #             )
    #             data = await response.json()
    #             if not data.get("success"):
    #                 return await ctx.warn(
    #                     "Failed to get **Linkvertise** destination!", delete_after=5
    #                 )

    #             return await ctx.send(data["destination"])

    # @command(name="lyrics", example="never gonna give you up")
    # @max_concurrency(1, wait=True)
    # async def lyrics(self, ctx: Context, *, query: str) -> Message:
    #     """Get lyrics for a song using Genius or AZLyrics"""
    #     async with ctx.typing():
    #         try:
    #             async with self.bot.session.get(
    #                 f"https://genius.com/api/search/song?q={urllib.parse.quote(query)}"
    #             ) as resp:
    #                 if resp.status != 200:
    #                     raise ValueError("Failed to fetch from Genius")
                        
    #                 data = await resp.json()
    #                 if not data["response"]["sections"][0]["hits"]:
    #                     raise ValueError("No results found on Genius")
                    
    #                 song = data["response"]["sections"][0]["hits"][0]["result"]
                    
    #                 async with self.bot.session.get(song["url"]) as resp:
    #                     if resp.status != 200:
    #                         raise ValueError("Failed to fetch lyrics page")
                            
    #                     html = await resp.text()
    #                     soup = BeautifulSoup(html, "html.parser")
    #                     lyrics_div = soup.find("div", {"data-lyrics-container": "true"})
                        
    #                     if not lyrics_div:
    #                         raise ValueError("No lyrics found on page")

    #                     lyrics = lyrics_div.get_text(separator="\n").strip()
    #                     lyrics = re.sub(r'\[.*?\]', lambda m: f"\n**{m.group(0)}**", lyrics) 
    #                     lyrics = re.sub(r'\((.*?)\)', r'*(\1)*', lyrics)  
    #                     lyrics = re.sub(r'\n\s*\n+', '\n\n', lyrics)

    #                     chunks = []
    #                     current_chunk = []
    #                     current_length = 0
                        
    #                     for line in lyrics.split('\n'):
    #                         if current_length + len(line) > 1000:
    #                             chunks.append('\n'.join(current_chunk))
    #                             current_chunk = []
    #                             current_length = 0
    #                         current_chunk.append(line)
    #                         current_length += len(line) + 1
                        
    #                     if current_chunk:
    #                         chunks.append('\n'.join(current_chunk))

    #                     embeds = []
    #                     for i, chunk in enumerate(chunks, 1):
    #                         embed = Embed(
    #                             title=song["title"],
    #                             url=song["url"],
    #                             description=chunk,
    #                             color=ctx.color
    #                         )
                            
    #                         if i == 1:
    #                             if song.get("song_art_url"):
    #                                 embed.set_thumbnail(url=song["song_art_url"])
                                    
    #                             embed.set_author(
    #                                 name=song["artist_names"],
    #                                 url=song["primary_artist"]["url"],
    #                                 icon_url=song["primary_artist"].get("image_url")
    #                             )
                            
    #                         embed.set_footer(text=f"Page {i}/{len(chunks)}")
    #                         embeds.append(embed)

    #                     paginator = Paginator(
    #                         ctx,
    #                         embeds=embeds
    #                     )
    #                     return await paginator.start()

    #         except Exception as e:
    #             try:
    #                 search_url = f"https://search.azlyrics.com/search.php?q={urllib.parse.quote(query)}"
                    
    #                 async with self.bot.session.get(
    #                     search_url, 
    #                     headers={"User-Agent": "Mozilla/5.0"}
    #                 ) as resp:
    #                     if resp.status != 200:
    #                         return await ctx.warn("Failed to find lyrics")
                            
    #                     html = await resp.text()
    #                     soup = BeautifulSoup(html, "html.parser")
                        
    #                     result = soup.select_one("td.text-left a")
    #                     if not result:
    #                         return await ctx.warn("No lyrics found")
                            
    #                     song_url = result["href"]
    #                     if not song_url.startswith("https:"):
    #                         song_url = "https:" + song_url
                            
    #                     async with self.bot.session.get(
    #                         song_url,
    #                         headers={"User-Agent": "Mozilla/5.0"}
    #                     ) as resp:
    #                         if resp.status != 200:
    #                             return await ctx.warn("Failed to fetch lyrics")
                                
    #                         html = await resp.text()
    #                         soup = BeautifulSoup(html, "html.parser")
                            
    #                         lyrics_div = soup.find("div", class_=None, id=None)
    #                         if not lyrics_div:
    #                             return await ctx.warn("No lyrics found")
                                
    #                         lyrics = lyrics_div.get_text().strip()
                            
    #                         chunks = [lyrics[i:i+1000] for i in range(0, len(lyrics), 1000)]
                            
    #                         title = soup.find("title").text.split(" - ")[0].strip()
    #                         artist = soup.find("title").text.split(" - ")[1].split(" Lyrics")[0].strip()
                            
    #                         embeds = []
    #                         for i, chunk in enumerate(chunks, 1):
    #                             embed = Embed(
    #                                 title=title,
    #                                 url=song_url,
    #                                 description=chunk,
    #                                 color=ctx.color
    #                             )
                                
    #                             if i == 1:
    #                                 embed.set_author(name=artist)
                                
    #                             embed.set_footer(text=f"Page {i}/{len(chunks)} • Lyrics from AZLyrics")
    #                             embeds.append(embed)

    #                         paginator = Paginator(
    #                             ctx,
    #                             embeds=embeds
    #                         )
    #                         return await paginator.start()
                            
    #             except Exception as e:
    #                 return await ctx.warn(f"Failed to find lyrics {e}")