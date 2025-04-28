# music.py
import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
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
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -b:a 128k'  # Limit bitrate for stability
        }

    @commands.command()
    async def play(self, ctx, *, query: str):
        """Play audio from YouTube (link or search)"""
        voice_client = ctx.voice_client

        # Connect to voice if not already connected
        if not voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Join a voice channel first!")
                return

        # Add to queue
        with YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            self.queue.append(info)

        await ctx.send(f"Added **{info['title']}** to queue!")

        # Start playing if not already playing
        if not voice_client.is_playing():
            await self.play_next(ctx)

    async def play_next(self, ctx):
        try:
            if len(self.queue) > 0:
                voice_client = ctx.voice_client
                info = self.queue.pop(0)
                url = info['url']
                source = discord.FFmpegOpusAudio(url, **self.ffmpeg_options)

                voice_client.play(source,
                                  after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
                await ctx.send(f"Now playing: **{info['title']}**")
            else:
                await ctx.send("Queue is empty!")
        except Exception as e:
            print(f"Error: {e}")
            await ctx.send("Error playing track - skipping to next song.")
            await self.play_next(ctx)  # Auto-skip on failure

    @commands.command()
    async def skip(self, ctx):
        """Skip current track"""
        ctx.voice_client.stop()
        await self.play_next(ctx)

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
        """Show current queue"""
        if not self.queue:
            await ctx.send("Queue is empty!")
            return

        queue_list = [f"{i + 1}. {item['title']}" for i, item in enumerate(self.queue)]
        await ctx.send("**Queue:**\n" + "\n".join(queue_list))

    @commands.command()
    async def shuffle(self, ctx):
        """Shuffle the queue"""
        import random
        random.shuffle(self.queue)
        await ctx.send("Queue shuffled!")

    @commands.command()
    async def playlist(self, ctx, url: str):
        """Add a YouTube playlist to the queue"""
        with YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            for entry in info['entries']:
                self.queue.append(entry)
        await ctx.send(f"Added {len(info['entries'])} songs from playlist!")


async def setup(bot):
    await bot.add_cog(Music(bot))

#Thomas