# music.py
import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = False
        self.queue = []
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt',  # Optional but recommended
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                }
            },
        }
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
            'options': '-vn -b:a 128k -threads 1'
        }

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Clean up resources when bot disconnects"""
        if member.id == self.bot.user.id and before.channel and not after.channel:
            self.queue = []
            # Forcefully clean up lingering processes
            if hasattr(self, '_player'):
                try:
                    self._player.stop()
                except:
                    pass



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
            with YoutubeDL(self.ydl_opts) as ydl:
                # Handle playlists
                if is_playlist:
                    info = ydl.extract_info(query, download=False)
                    if not info or 'entries' not in info:
                        await ctx.send("⚠️ Couldn't load playlist")
                        return

                    added_count = 0
                    for entry in info['entries']:
                        if entry:  # Skip unavailable videos
                            self.queue.append(entry)
                            added_count += 1

                    await ctx.send(f"🎵 Added {added_count} tracks from **{info['title']}**")

                # Handle single videos/searches
                else:
                    # Process as search query if not a URL
                    if not query.startswith(('http://', 'https://')):
                        query = f"ytsearch:{query}"

                    info = ydl.extract_info(query, download=False)

                    # Extract first result from searches
                    if 'entries' in info:
                        info = info['entries'][0]

                    self.queue.append(info)
                    await ctx.send(f"🎵 Added **{info['title']}** to queue")

            # Start playback if idle
            if not voice_client.is_playing() and not voice_client.is_paused():
                await self.play_next(ctx)

        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    async def play_next(self, ctx):
        # In play_next()
        if self.is_playing:
            return
        self.is_playing = True
        try:
            voice_client = ctx.voice_client
            # Handle unexpected disconnects

            if voice_client is None or not voice_client.is_connected():
                self.queue = []  # Clear queue
                return

            if self.queue:
                info = self.queue.pop(0)
                source = discord.FFmpegOpusAudio(info['url'], **self.ffmpeg_options)

                def after_playing(e):
                    if e:
                        print(f"Player error: {e}")
                        # Add delay before next track
                    asyncio.run_coroutine_threadsafe(
                        asyncio.sleep(0.5).__await__(),
                        self.bot.loop
                    )
                    asyncio.run_coroutine_threadsafe(
                        self.play_next(ctx),
                        self.bot.loop
                    )
                    # In after_playing callback
                    self.is_playing = False

                voice_client.play(source, after=after_playing)
                await ctx.send(f"Now playing: **{info['title']}**")
            else:
                await ctx.send("Queue is empty!")
        except Exception as e:
            print(f"Error: {e}")
            await ctx.send("Error playing track - skipping to next song.")
            await self.play_next(ctx)  # Skip on failure

    @commands.command()
    async def skip(self, ctx):
        """Skip current track with proper cleanup"""
        if ctx.voice_client:
            ctx.voice_client.stop()
            # Add slight delay to allow cleanup
            await asyncio.sleep(0.5)
        await self.play_next(ctx)

    @commands.command()
    async def disconnect(self, ctx):
        """Clean disconnect command"""
        self.queue = []
        if ctx.voice_client:
            # Stop player before disconnecting
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()

    @commands.command()
    async def pause(self, ctx):
        """Pause playback"""
        ctx.voice_client.pause()

    @commands.command()
    async def resume(self, ctx):
        """Resume playback"""
        ctx.voice_client.resume()

    @commands.command()
    async def queue(self, ctx):
        voice_client = ctx.voice_client
        """Show current queue"""
        if not self.queue and not voice_client.is_playing():
            await ctx.send("Queue1 is empty!")
            return

        """await ctx.send(f'Now playing: {info['title']}')"""
        queue_list = [f"{i + 1}. {item['title']}" for i, item in enumerate(self.queue)]
        await ctx.send("**Queue:**\n" + "\n".join(queue_list))

    @commands.command()
    async def shuffle(self, ctx):
        """Shuffle the queue"""
        import random
        random.shuffle(self.queue)
        await ctx.send("Queue shuffled!")


async def setup(bot):
    await bot.add_cog(Music(bot))

#Thomas