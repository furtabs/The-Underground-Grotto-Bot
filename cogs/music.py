import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque
import imageio_ffmpeg

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # Server ID -> Queue of songs
        self.now_playing = {}  # Server ID -> Current song
        self.voice_clients = {}  # Server ID -> Voice client
        self.song_owners = {}  # Server ID -> User ID of who added the song
        self.music_channels = {}  # Server ID -> Channel ID for music messages
        self.volumes = {}  # Server ID -> 0.0-2.0

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    def has_dj_role(self, member):
        """Check if a member has the DJ role"""
        return any(role.name.lower() == 'dj' for role in member.roles)

    @commands.slash_command()
    async def play(self, ctx, query: str):
        """Play from URL (YouTube, SoundCloud, MP3, etc.) or search query"""
        if not ctx.author.voice:
            embed = discord.Embed(title="Error", description="You need to be in a voice channel!", color=discord.Color.red())
            await ctx.respond(embed=embed)
            return

        # Respond immediately to avoid interaction timeout
        embed = discord.Embed(title="Searching", description="Looking for your song...", color=discord.Color.blue())
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_response()

        # Store the channel where the command was used
        self.music_channels[ctx.guild.id] = ctx.channel.id

        # Get or create voice client (this can take time, so we respond first)
        try:
            if ctx.guild.id not in self.voice_clients:
                self.voice_clients[ctx.guild.id] = await ctx.author.voice.channel.connect()
            elif not self.voice_clients[ctx.guild.id].is_connected():
                self.voice_clients[ctx.guild.id] = await ctx.author.voice.channel.connect()
        except Exception as e:
            error_embed = discord.Embed(title="Error", description=f"Failed to connect to voice channel: {str(e)}", color=discord.Color.red())
            await message.edit(embed=error_embed)
            return

        # Detect direct URL vs search
        is_url = query.lower().startswith('http://') or query.lower().startswith('https://')

        # Configure yt-dlp options (extract bestaudio URL, do not download)
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'socket_timeout': 10,
            'extract_flat': False,
        }

        try:
            # Run yt-dlp operations in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            def extract_url_info(url):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            def extract_search_info(search_query):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(f"ytsearch5:{search_query}", download=False)
            
            def extract_video_info(video_id):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(video_id, download=False)
            
            if is_url:
                # Update message to show we're processing
                await message.edit(embed=discord.Embed(title="Processing", description=f"Extracting audio from URL...", color=discord.Color.blue()))
                info = await asyncio.wait_for(loop.run_in_executor(None, extract_url_info, query), timeout=30.0)
                # Handle playlists by taking first entry
                if info.get('_type') == 'playlist' and info.get('entries'):
                    info = info['entries'][0]
                title = info.get('title', 'Unknown Title')
                url2 = info.get('url')
                if not url2:
                    raise Exception('Unable to extract audio URL for this link.')

                # Add to queue
                queue = self.get_queue(ctx.guild.id)
                queue.append((title, url2))
                if ctx.guild.id not in self.song_owners:
                    self.song_owners[ctx.guild.id] = []
                self.song_owners[ctx.guild.id].append(ctx.author.id)

                if len(queue) == 1:
                    embed = discord.Embed(title="Added to Queue", description=f"Added {title} and starting playback!", color=discord.Color.green())
                    await message.edit(embed=embed)
                    await self.play_next(ctx.guild)
                else:
                    embed = discord.Embed(title="Added to Queue", description=title, color=discord.Color.green())
                    await message.edit(embed=embed)
                return

            # Otherwise perform YouTube search results flow
            await message.edit(embed=discord.Embed(title="Searching", description=f"Searching YouTube for: {query}...", color=discord.Color.blue()))
            search_info = await asyncio.wait_for(loop.run_in_executor(None, extract_search_info, query), timeout=30.0)
            search_results = search_info.get('entries', [])
            
            if not search_results:
                embed = discord.Embed(title="Error", description="No results found!", color=discord.Color.red())
                await message.edit(embed=embed)
                return

            # Create select menu options
            options = []
            for i, result in enumerate(search_results, 1):
                title = result['title']
                duration = result.get('duration', 'Unknown')
                if isinstance(duration, int):
                    minutes = duration // 60
                    seconds = duration % 60
                    duration = f"{minutes}:{seconds:02d}"
                options.append(discord.SelectOption(
                    label=f"{i}. {title[:100]}",  # Discord has a 100 char limit for labels
                    value=str(i-1),
                    description=f"Duration: {duration}"
                ))

            # Create select menu
            select = discord.ui.Select(
                placeholder="Choose a song",
                options=options
            )

            # Create view
            view = discord.ui.View()
            view.add_item(select)

            # Update message with select menu
            embed = discord.Embed(title="Search Results", description="Please select a song:", color=discord.Color.blue())
            await message.edit(embed=embed, view=view)

            # Wait for selection
            def check(interaction):
                return interaction.user == ctx.author and interaction.data['component_type'] == 3

            try:
                interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
                selected_index = int(interaction.data['values'][0])
                selected_video = search_results[selected_index]
                
                # Get the video URL
                await message.edit(embed=discord.Embed(title="Processing", description="Getting audio URL...", color=discord.Color.blue()))
                info = await asyncio.wait_for(loop.run_in_executor(None, extract_video_info, selected_video['id']), timeout=30.0)
                title = info['title']
                url2 = info['url']

                # Add to queue
                queue = self.get_queue(ctx.guild.id)
                queue.append((title, url2))
                # Store who added the song
                if ctx.guild.id not in self.song_owners:
                    self.song_owners[ctx.guild.id] = []
                self.song_owners[ctx.guild.id].append(ctx.author.id)

                if len(queue) == 1:  # If this is the first song
                    embed = discord.Embed(title="Added to Queue", description=f"Added {title} and starting playback!", color=discord.Color.green())
                    await message.edit(embed=embed, view=None)
                    await self.play_next(ctx.guild)
                else:
                    embed = discord.Embed(title="Added to Queue", description=title, color=discord.Color.green())
                    await message.edit(embed=embed, view=None)

            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timeout", description="You took too long to select a song!", color=discord.Color.red())
                await message.edit(embed=embed, view=None)
                return

        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timeout", description="The operation took too long. Please try again.", color=discord.Color.red())
            await message.edit(embed=embed, view=None)
        except Exception as e:
            embed = discord.Embed(title="Error", description=f"An error occurred: {str(e)}", color=discord.Color.red())
            await message.edit(embed=embed, view=None)

    async def play_next(self, guild):
        queue = self.get_queue(guild.id)
        if not queue:
            return

        title, url = queue[0]
        self.now_playing[guild.id] = title

        try:
            # Use Python-provided ffmpeg binary from imageio-ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            # Add reconnect flags for resilient streaming
            source = discord.FFmpegPCMAudio(
                url,
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                executable=ffmpeg_exe,
            )
            # Apply volume if set
            volume = self.volumes.get(guild.id, 1.0)
            source = discord.PCMVolumeTransformer(source, volume=volume)
            vc = self.voice_clients[guild.id]

            def _after_playback(error: Exception | None):
                try:
                    # Ensure ffmpeg process/file handles are released
                    if hasattr(vc, 'source') and vc.source and hasattr(vc.source, 'cleanup'):
                        vc.source.cleanup()
                except Exception:
                    pass
                asyncio.run_coroutine_threadsafe(self.play_next(guild), self.bot.loop)

            vc.play(source, after=_after_playback)
            if guild.id in self.music_channels:
                channel = guild.get_channel(self.music_channels[guild.id])
                if channel:
                    embed = discord.Embed(title="Now Playing", description=title, color=discord.Color.blue())
                    await channel.send(embed=embed)
            # Remove the current song from the queue
            queue.popleft()
            if guild.id in self.song_owners and self.song_owners[guild.id]:
                self.song_owners[guild.id].pop(0)
        except Exception as e:
            if guild.id in self.music_channels:
                channel = guild.get_channel(self.music_channels[guild.id])
                if channel:
                    embed = discord.Embed(title="Error", description=f"Error playing song: {str(e)}", color=discord.Color.red())
                    await channel.send(embed=embed)
            queue.popleft()
            if guild.id in self.song_owners and self.song_owners[guild.id]:
                self.song_owners[guild.id].pop(0)
            await self.play_next(guild)

    @commands.slash_command()
    async def skip(self, ctx):
        """Skip the current song"""
        if not ctx.guild.id in self.voice_clients or not self.voice_clients[ctx.guild.id].is_playing():
            embed = discord.Embed(title="Error", description="Nothing is playing!", color=discord.Color.red())
            await ctx.respond(embed=embed)
            return

        # Check if user has DJ role or is the song owner
        if not self.has_dj_role(ctx.author):
            if ctx.guild.id not in self.song_owners or not self.song_owners[ctx.guild.id]:
                embed = discord.Embed(title="Permission Denied", description="You need the DJ role to skip songs!", color=discord.Color.red())
                await ctx.respond(embed=embed)
                return
            if self.song_owners[ctx.guild.id][0] != ctx.author.id:
                embed = discord.Embed(title="Permission Denied", description="You can only skip your own songs unless you have the DJ role!", color=discord.Color.red())
                await ctx.respond(embed=embed)
                return

        self.voice_clients[ctx.guild.id].stop()
        if ctx.guild.id in self.song_owners and self.song_owners[ctx.guild.id]:
            self.song_owners[ctx.guild.id].pop(0)
            embed = discord.Embed(title="Skipped", description="Current song has been skipped!", color=discord.Color.green())
            await ctx.respond(embed=embed)

    @commands.slash_command()
    async def stop(self, ctx):
        """Stop playing and clear the queue"""
        if not self.has_dj_role(ctx.author):
            embed = discord.Embed(title="Permission Denied", description="You need the DJ role to stop playback!", color=discord.Color.red())
            await ctx.respond(embed=embed)
            return

        if ctx.guild.id in self.voice_clients:
            vc = self.voice_clients[ctx.guild.id]
            if vc.is_playing():
                vc.stop()
            # Cleanup current source if present
            try:
                if hasattr(vc, 'source') and vc.source and hasattr(vc.source, 'cleanup'):
                    vc.source.cleanup()
            except Exception:
                pass
            self.queues[ctx.guild.id] = deque()
            self.song_owners[ctx.guild.id] = []
            embed = discord.Embed(title="Stopped", description="Playback stopped and queue cleared!", color=discord.Color.green())
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="Nothing is playing!", color=discord.Color.red())
            await ctx.respond(embed=embed)

    @commands.slash_command()
    async def volume(self, ctx, percent: int):
        """Set playback volume (0-200%). Requires DJ role."""
        if percent < 0 or percent > 200:
            await ctx.respond(embed=discord.Embed(title="Error", description="Volume must be between 0 and 200.", color=discord.Color.red()))
            return
        if not self.has_dj_role(ctx.author):
            await ctx.respond(embed=discord.Embed(title="Permission Denied", description="You need the DJ role to change volume!", color=discord.Color.red()))
            return
        vol = max(0.0, min(2.0, percent / 100.0))
        self.volumes[ctx.guild.id] = vol
        vc = self.voice_clients.get(ctx.guild.id)
        if vc and vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = vol
        await ctx.respond(embed=discord.Embed(title="Volume", description=f"Set to {percent}%", color=discord.Color.green()))
    @commands.slash_command()
    async def queue(self, ctx):
        """Show the current queue"""
        queue = self.get_queue(ctx.guild.id)
        if not queue:
            embed = discord.Embed(title="Queue", description="The queue is empty!", color=discord.Color.blue())
            await ctx.respond(embed=embed)
            return

        embed = discord.Embed(title="Music Queue", color=discord.Color.blue())
        for i, (title, _) in enumerate(queue, 1):
            embed.add_field(name=f"{i}.", value=title, inline=False)

        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def leave(self, ctx):
        """Make the bot leave the voice channel"""
        if not self.has_dj_role(ctx.author):
            embed = discord.Embed(title="Permission Denied", description="You need the DJ role to make the bot leave!", color=discord.Color.red())
            await ctx.respond(embed=embed)
            return

        if ctx.guild.id in self.voice_clients:
            vc = self.voice_clients[ctx.guild.id]
            try:
                if hasattr(vc, 'source') and vc.source and hasattr(vc.source, 'cleanup'):
                    vc.source.cleanup()
            except Exception:
                pass
            await vc.disconnect()
            del self.voice_clients[ctx.guild.id]
            if ctx.guild.id in self.song_owners:
                del self.song_owners[ctx.guild.id]
            embed = discord.Embed(title="Left Channel", description="I've left the voice channel!", color=discord.Color.green())
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="I'm not in a voice channel!", color=discord.Color.red())
            await ctx.respond(embed=embed)

    def cog_unload(self):
        # Attempt to gracefully cleanup any active voice clients/sources
        for gid, vc in list(self.voice_clients.items()):
            try:
                if hasattr(vc, 'source') and vc.source and hasattr(vc.source, 'cleanup'):
                    vc.source.cleanup()
            except Exception:
                pass
            try:
                asyncio.run_coroutine_threadsafe(vc.disconnect(), self.bot.loop)
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(Music(bot)) 