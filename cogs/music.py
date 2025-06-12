# music.py
import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio
import concurrent.futures
import random


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.listen = self.listener()
        self.loop = False
        self.loop_queue = False
        self.queue = []
        self.current_song = None
        self.is_playing = False

        # UPDATED: Optimized yt-dlp options
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'ignoreerrors': True,  # Skip unplayable videos
            'no_check_certificate': True,  # Bypass SSL issues
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                }
            },
            'cachedir': False,  # Avoid cache corruption
            'socket_timeout': 15,  # Timeout protection
        }

        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
            'options': '-vn -b:a 128k -threads 1'
        }

    @commands.command()
    async def play(self, ctx, *, query: str):
        """Play audio from YouTube (video, search, or playlist)"""
        voice_client = ctx.voice_client

        # Connect to voice if needed
        if voice_client is None:
            if ctx.author.voice:
                voice_client = await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Join a voice channel first!")
                return

        # Detect playlist URLs
        is_playlist = "list=" in query and ("youtube.com" in query or "youtu.be" in query)

        try:
            # FIX: Run blocking operations in thread
            with YoutubeDL(self.ydl_opts) as ydl:
                def extract_info():
                    return ydl.extract_info(query, download=False)

                # Use thread pool for extraction
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, extract_info)

                if not info:
                    await ctx.send("⚠️ Couldn't find any results")
                    return

                # Handle playlists
                if is_playlist:
                    if 'entries' not in info:
                        await ctx.send("⚠️ Couldn't load playlist")
                        return

                    added_count = 0
                    for entry in info['entries']:
                        if entry:  # Skip unavailable videos
                            self.queue.append(entry)
                            added_count += 1

                    await ctx.send(f"🎵 Added {added_count} tracks from **{info.get('title', 'playlist')}**")

                # Handle single videos/searches
                else:
                    # Extract first result from searches
                    if 'entries' in info:
                        if not info['entries']:
                            await ctx.send("⚠️ No videos found")
                            return
                        info = info['entries'][0]

                    self.queue.append(info)
                    await ctx.send(f"🎵 Added **{info.get('title', 'Unknown track')}** to queue")

            # Start playback if idle
            if not voice_client.is_playing() and not voice_client.is_paused():
                await self.play_next(ctx)

        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)[:150]}")

    async def play_next(self, ctx):
        if self.is_playing:  # Prevent overlapping plays
            return

        self.is_playing = True
        try:
            # Always get fresh voice client
            voice_client = ctx.voice_client

            # Handle disconnects
            if not voice_client or not voice_client.is_connected():
                self.queue = []
                self.is_playing = False
                return

            # Skip invalid tracks
            while self.queue:
                info = self.queue.pop(0)
                if info.get('url'):
                    break
            else:
                await ctx.send("Queue is empty!")
                self.is_playing = False
                self.current_song = None
                self.loop = False
                return

            #self.current_song = info.get('title', 'Unknown track')
            self.current_song = info
            source = discord.FFmpegOpusAudio(
                info['url'],
                **self.ffmpeg_options
            )

            def after_playing(e):
                # Schedule next track in bot's thread
                async def _play_next():
                    self.is_playing = False # Reset FIRST
                    # Looping current song function
                    if self.loop and self.current_song:
                        self.queue.insert(0, self.current_song)
                    if self.loop_queue and self.current_song:
                        self.queue.append(self.current_song)
                    await self.play_next(ctx)  # Then trigger next

                asyncio.run_coroutine_threadsafe(
                    _play_next(),
                    self.bot.loop
                )

            voice_client.play(source, after=after_playing)
            await ctx.send(f"Now playing: **{self.current_song.get('title')}**")

        except Exception as e:
            print(f"Play error: {e}")
            self.is_playing = False
            if ctx.voice_client:
                ctx.voice_client.stop()
            await ctx.send("⚠️ Playback error, skipping track")

    @commands.command()
    async def skip(self, ctx):
        """Skip current track"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            await ctx.send("⏭ Skipped")
            ctx.voice_client.stop()
        else:
            await ctx.send("Nothing playing!")

    @commands.command()
    async def disconnect(self, ctx):
        """Clean disconnect command"""
        self.queue = []
        if ctx.voice_client:
            ctx.voice_client.stop()
            self.current_song = None
            self.loop = False
            await ctx.voice_client.disconnect()

    @commands.command()
    async def pause(self, ctx):
        """Pause playback"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()

    @commands.command()
    async def loop(self, ctx):
        if not ctx.voice_client:
            await ctx.send("Can't use loop while not connected to a voice channel")
            return
        else:
            if self.loop and ctx.voice_client.is_playing():
                self.loop = False
                await ctx.send("❌  Loop mode deactivated")

            elif not self.loop and ctx.voice_client.is_playing():
                self.loop = True
                await ctx.send("🔁 Loop mode activated")

            else:
                await ctx.send("No song is currently playing!")

    @commands.command()
    async def loopq(self, ctx):
        if not ctx.voice_client:
            await ctx.send("Can't use loop while not connected to a voice channel")
            return
        else:
            if self.loop_queue and ctx.voice_client.is_playing():
                self.loop_queue = False
                await ctx.send("❌  Loop mode deactivated")

            elif not self.loop_queue and ctx.voice_client.is_playing():
                self.loop_queue = True
                await ctx.send("🔁 Loop mode activated")

            else:
                await ctx.send("No song is currently playing!")

    @commands.command()
    async def resume(self, ctx):
        """Resume playback"""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()

    @commands.command(name="queue")  # Fixed: name conflict
    async def show_queue(self, ctx):
        """Show current queue"""
        if not self.queue and not (ctx.voice_client and ctx.voice_client.is_playing()):
            await ctx.send("Queue is empty!")
            self.loop = False
            return

        queue_list = [f"{i + 1}. {item.get('title', 'Unknown track')}"
                      for i, item in enumerate(self.queue)]

        current = self.current_song.get('title') or "Nothing"
        if self.loop and self.current_song:
            queue_list.append(f"***Currently looping: *** {current}")
        await ctx.send(
            f"**Now Playing:** {current}\n"
            f"**Queue:**\n" + "\n".join(queue_list[:10])  # Limit to first 10
        )

    @commands.command()
    async def shuffle(self, ctx):
        """Shuffle the queue"""
        random.shuffle(self.queue)
        await ctx.send("🔀 Queue shuffled!")


async def setup(bot):
    await bot.add_cog(Music(bot))