# music.py
from mmap import PAGESIZE

import discord
from discord.ext import commands
from discord import ui
import asyncio
import random
import lavalink
from lavalink.events import TrackStartEvent, QueueEndEvent
from lavalink.errors import ClientError
from lavalink.filters import LowPass
from lavalink.server import LoadType
from lavalink import Client
import re
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

url_rx = re.compile(r'https?://(?:www\.)?.+')

class LavalinkVoiceClient(discord.VoiceProtocol):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False

        if not hasattr(self.client, 'lavalink'):
            # Instantiate a client if one doesn't exist.
            # We store it in `self.client` so that it may persist across cog reloads,
            # however this is not mandatory.
            self.client.lavalink = lavalink.Client(client.user.id)
            #self.client.lavalink.add_node(host='localhost', port=2333, password='alaa2000',
            #                             region='us', name='default-node')
            self.client.lavalink.add_node(host='lava-v4.ajieblogs.eu.org', port=443, password="https://dsc.gg/ajidevserver")

        # Create a shortcut to the Lavalink client here.
        self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        channel_id = data['channel_id']

        if not channel_id:
            await self._destroy()
            return

        self.channel = self.client.get_channel(int(channel_id))

        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }

        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        await self._destroy()

    async def _destroy(self):
        self.cleanup()

        if self._destroyed:
            # Idempotency handling, if `disconnect()` is called, the changed voice state
            # could cause this to run a second time.
            return

        self._destroyed = True

        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except ClientError:
            pass

PAGE_SIZE = 10

class QueuePaginator(ui.View):
    def __init__(self, ctx, queue):
        super().__init__(timeout=120.0)
        self.ctx      = ctx
        self.queue    = queue
        self.page     = 0
        self.max_page = (len(queue) - 1) // PAGE_SIZE

    def make_embed(self):
        start = self.page * PAGE_SIZE
        end   = start + PAGE_SIZE
        emb = discord.Embed(
            title=f"Queue — Page {self.page+1}/{self.max_page+1}",
            color=discord.Color.blurple()
        )
        if not self.queue:
            emb.description = "*The queue is empty.*"
            return emb

        for idx, track in enumerate(self.queue[start:end], start=start+1):
            # adjust this line to match your track metadata
            emb.add_field(
                name=f"{idx}. {track.title}",
                value=f"{track.author} — `{track.duration//60000}:{(track.duration//1000)%60:02d}`",
                inline=False
            )
        return emb

    async def update_message(self, interaction: discord.Interaction):
        # disable buttons when only one page
        self.first.disabled = self.prev.disabled = (self.page == 0)
        self.last.disabled  = self.next.disabled = (self.page == self.max_page)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @ui.button(label="⏮ First", style=discord.ButtonStyle.grey)
    async def first(self, interaction: discord.Interaction, button: ui.Button):
        self.page = 0
        await self.update_message(interaction)

    @ui.button(label="◀ Prev", style=discord.ButtonStyle.grey)
    async def prev(self, interaction: discord.Interaction, button: ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)

    @ui.button(label="Next ▶", style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        if self.page < self.max_page:
            self.page += 1
            await self.update_message(interaction)

    @ui.button(label="Last ⏭", style=discord.ButtonStyle.grey)
    async def last(self, interaction: discord.Interaction, button: ui.Button):
        self.page = self.max_page
        await self.update_message(interaction)

    async def on_timeout(self):
        # disable all buttons after timeout
        for btn in self.children:
            btn.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass


class Music_lavalink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.player = None
        self.nowplaying_tasks = {}  # Track per-guild update tasks
        self.playlist = None
        self._original_queues: dict[int, list] = {}

        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node(
                os.getenv('LAVALINK_HOST'),
                int(os.getenv('LAVALINK_PORT')),
                os.getenv('LAVALINK_PASSWORD'),
                'eu',
                'default-node'
            )

        self.lavalink: lavalink.Client = bot.lavalink
        self.lavalink.add_event_hooks(self)

    def cog_unload(self):
        """
        This will remove any registered event hooks when the cog is unloaded.
        They will subsequently be registered again once the cog is loaded.

        This effectively allows for event handlers to be updated when the cog is reloaded.
        """
        self.lavalink._event_hooks.clear()

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)
            # The above handles errors thrown in this cog and shows them to the user.
            # This shouldn't be a problem as the only errors thrown in this cog are from `ensure_voice`
            # which contain a reason string, such as "Join a voicechannel" etc. You can modify the above
            # if you want to do things differently.

    async def create_player(ctx: commands.Context):
        """
        A check that is invoked before any commands marked with `@commands.check(create_player)` can run.

        This function will try to create a player for the guild associated with this Context, or raise
        an error which will be relayed to the user if one cannot be created.
        """
        if ctx.guild is None:
            raise commands.NoPrivateMessage()

        player = ctx.bot.lavalink.player_manager.create(ctx.guild.id)
        # Create returns a player if one exists, otherwise creates.
        # This line is important because it ensures that a player always exists for a guild.

        # Most people might consider this a waste of resources for guilds that aren't playing, but this is
        # the easiest and simplest way of ensuring players are created.

        # These are commands that require the bot to join a voicechannel (i.e. initiating playback).
        # Commands such as volume/skip etc don't require the bot to be in a voicechannel so don't need listing here.
        should_connect = ctx.command.name in ('play', 'join')

        voice_client = ctx.voice_client

        if not ctx.author.voice or not ctx.author.voice.channel:
            # Check if we're in a voice channel. If we are, tell the user to join our voice channel.
            if voice_client is not None:
                raise commands.CommandInvokeError('You need to join my voice channel first.')

            # Otherwise, tell them to join any voice channel to begin playing music.
            raise commands.CommandInvokeError('Join a voicechannel first.')

        voice_channel = ctx.author.voice.channel

        if voice_client is None:
            if not should_connect:
                raise commands.CommandInvokeError("I'm not playing music.")

            permissions = voice_channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:
                raise commands.CommandInvokeError('I need the `CONNECT` and `SPEAK` permissions.')

            if voice_channel.user_limit > 0:
                # A limit of 0 means no limit. Anything higher means that there is a member limit which we need to check.
                # If it's full, and we don't have "move members" permissions, then we cannot join it.
                if len(voice_channel.members) >= voice_channel.user_limit and not ctx.me.guild_permissions.move_members:
                    raise commands.CommandInvokeError('Your voice channel is full!')

            player.store('channel', ctx.channel.id)
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        elif voice_client.channel.id != voice_channel.id:
            raise commands.CommandInvokeError('You need to be in my voicechannel.')

        return True

    @lavalink.listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        guild_id = event.player.guild_id
        channel_id = event.player.fetch('channel')
        guild = self.bot.get_guild(guild_id)

        if not guild:
            return await self.lavalink.player_manager.destroy(guild_id)

        channel = guild.get_channel(channel_id)

        if not channel:
            #await channel.send('Now playing: {} by {}'.format(event.track.title, event.track.author))
            return

        track = event.track
        embed = discord.Embed(
            title="Now Playing",
            description=f"[{track.title}]({track.uri})",
            color=0x2ecc71
        )
        print(track.artwork_url)
        print(track.plugin_info)
        embed.set_thumbnail(url=track.artwork_url)
        embed.add_field(name="Progress", value="🔘────────── 0:00", inline=False)
        embed.set_footer(text=f"Channel: {track.author}")

        message = await channel.send(embed=embed)

        # Cancel any existing updater task
        if guild_id in self.nowplaying_tasks:
            self.nowplaying_tasks[guild_id].cancel()

        task = self.bot.loop.create_task(self.update_nowplaying(event.player, message))
        self.nowplaying_tasks[guild_id] = task

    async def update_nowplaying(self, player, message):
        try:
            while player.is_playing:
                await asyncio.sleep(5)  # Update every X seconds

                track = player.current
                position = player.position
                duration = track.duration
                progress = lavalink.utils.format_time(position)
                total = lavalink.utils.format_time(duration)

                progress_percent = position / duration
                progress_index = int(progress_percent * 10)
                progress_bar = ["▬"] * 10
                if 0 <= progress_index < 10:
                    progress_bar[progress_index] = "🔘"
                bar = "".join(progress_bar)

                embed = message.embeds[0]
                embed.set_field_at(0, name="Progress", value=f"{bar} {progress}/{total}", inline=False)
                await message.edit(embed=embed)

        except (discord.NotFound, discord.Forbidden):
            pass  # Message deleted or can't be edited
        except asyncio.CancelledError:
            pass  # Task was canceled

    @lavalink.listener(QueueEndEvent)
    async def on_queue_end(self, event: QueueEndEvent):
        guild_id = event.player.guild_id

        # Cancel updater task
        if guild_id in self.nowplaying_tasks:
            self.nowplaying_tasks[guild_id].cancel()
            del self.nowplaying_tasks[guild_id]

        guild = self.bot.get_guild(guild_id)

        if guild is not None:
            await guild.voice_client.disconnect(force=True)

    @commands.command(aliases=['p'])
    @commands.check(create_player)
    async def play(self, ctx, *, query: str):
        """ Searches and plays a song from a given query. """



        # Get the player for this guild from cache.
        self.player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip('<>')

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        # SoundCloud searching is possible by prefixing "scsearch:" instead.
        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        # Get the results for the query from Lavalink.
        results = await self.player.node.get_tracks(query)

        embed = discord.Embed(color=discord.Color.blurple())

        # Valid load_types are:
        #   TRACK    - direct URL to a track
        #   PLAYLIST - direct URL to playlist
        #   SEARCH   - query prefixed with either "ytsearch:" or "scsearch:". This could possibly be expanded with plugins.
        #   EMPTY    - no results for the query (result.tracks will be empty)
        #   ERROR    - the track encountered an exception during loading
        if results.load_type == LoadType.EMPTY:
            return await ctx.send("I couldn'\t find any tracks for that query.")
        elif results.load_type == LoadType.PLAYLIST:
            tracks = results.tracks
            self.playlist = results
            print(f'Results load type: {results.load_type}')
            print(f'Info: {results.playlist_info}')
            print(len(tracks))

            # Add all of the tracks from the playlist to the queue.
            for track in tracks:
                # requester isn't necessary but it helps keep track of who queued what.
                # You can store additional metadata by passing it as a kwarg (i.e. key=value)
                self.player.add(track=track, requester=ctx.author.id)

            embed.title = 'Playlist Enqueued!'
            embed.description = f'{results.playlist_info.name} - {len(tracks)} tracks'
        else:
            track = results.tracks[0]


            metadata = {
                "title": track.title,
                "channel": track.author,
                "duration": datetime.timedelta(milliseconds=track.duration),
                "url": track.uri,
                "id": track.identifier,
                "thumbnail": f"https://img.youtube.com/vi/{track.identifier}/maxresdefault.jpg",
                "source": track.source_name
            }

            embed.title = metadata['title']
            embed.url = metadata['url']
            embed.description = 'Added to Queue'
            embed.set_thumbnail(url= metadata['thumbnail'])
            embed.add_field(name="Channel", value=metadata['channel'], inline=True)
            embed.add_field(name="Duration", value=metadata['duration'], inline=True)
            #embed.add_field(name="Position in queue", value=self.queue.index(info), inline=False)
            embed.set_author(name=ctx.author.display_name, url=None, icon_url=ctx.author.avatar)

            # requester isn't necessary but it helps keep track of who queued what.
            # You can store additional metadata by passing it as a kwarg (i.e. key=value)
            self.player.add(track=track, requester=ctx.author.id)



        await ctx.send(embed=embed)

        # We don't want to call .play() if the player is playing as that will effectively skip
        # the current track.
        if not self.player.is_playing:
            await self.player.play()


    @commands.command()
    @commands.check(create_player)
    async def nowplaying(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player or not player.current:
            return await ctx.send("Nothing playing!")
        track = player.current
        # Extract metadata
        metadata = {
            "title": track.title,
            "channel": track.author,
            "progress": lavalink.utils.format_time(player.position),
            "duration": lavalink.utils.format_time(track.duration),
            "thumbnail": f"https://img.youtube.com/vi/{track.identifier}/maxresdefault.jpg"
        }
        # Create progress bar
        progress_percent = player.position / track.duration
        progress_bar = "▬" * 10
        progress_index = int(progress_percent * 10)
        progress_bar = progress_bar[:progress_index] + "🔘" + progress_bar[progress_index + 1:]
        embed = discord.Embed(
            title="Now Playing",
            description=f"[{metadata['title']}]({track.uri})",
            color=0x2ecc71
        )
        embed.add_field(
            name="Progress",
            value=f"{progress_bar} {metadata['progress']}/{metadata['duration']}",
            inline=False
        )
        embed.set_thumbnail(url=metadata["thumbnail"])
        embed.set_footer(text=f"Channel: {metadata['channel']}")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.check(create_player)
    async def stream(self, ctx, *, query: str):
        self.player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        query = query.strip('<>')
        results = await self.player.node.get_tracks(query)
        track = results.tracks[0]
        await self.player.play(track)

    @commands.command(aliases=['lp'])
    @commands.check(create_player)
    async def lowpass(self, ctx, strength: float):
        """ Sets the strength of the low pass filter. """
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # This enforces that strength should be a minimum of 0.
        # There's no upper limit on this filter.
        strength = max(0.0, strength)

        # Even though there's no upper limit, we will enforce one anyway to prevent
        # extreme values from being entered. This will enforce a maximum of 100.
        strength = min(100, strength)

        embed = discord.Embed(color=discord.Color.blurple(), title='Low Pass Filter')

        # A strength of 0 effectively means this filter won't function, so we can disable it.
        if strength == 0.0:
            await player.remove_filter('lowpass')
            embed.description = 'Disabled **Low Pass Filter**'
            return await ctx.send(embed=embed)

        # Lets create our filter.
        low_pass = LowPass()
        low_pass.update(smoothing=strength)  # Set the filter strength to the user's desired level.

        # This applies our filter. If the filter is already enabled on the player, then this will
        # just overwrite the filter with the new values.
        await player.set_filter(low_pass)

        embed.description = f'Set **Low Pass Filter** strength to {strength}.'
        await ctx.send(embed=embed)

    @commands.command(aliases=['dc'])
    @commands.check(create_player)
    async def disconnect(self, ctx):
        """ Disconnects the player from the voice channel and clears its queue. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        # The necessary voice channel checks are handled in "create_player."
        # We don't need to duplicate code checking them again.

        # Clear the queue to ensure old tracks don't start playing
        # when someone else queues something.
        player.queue.clear()
        # Stop the current track so Lavalink consumes less resources.
        await player.stop()
        # Disconnect from the voice channel.
        await ctx.voice_client.disconnect(force=True)
        await ctx.send('✳ | Disconnected.')

    @commands.command(name="queue")
    @commands.check(create_player)
    async def queue(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        queue  = player.queue  # list of lavalink.Tracks
        print(type(player.queue))

        # 1) Empty?
        if not queue:
            embed = discord.Embed(title="🔊 The queue is empty!", colour=discord.Colour.dark_red())
            return await ctx.send(embed=embed)

        # 2) Only one page? (no need for buttons)
        if len(queue) <= PAGE_SIZE:
            embed = discord.Embed(
                title="Current Queue",
                color=discord.Color.blurple()
            )
            for idx, track in enumerate(queue, start=1):
                minutes, seconds = divmod(track.duration // 1000, 60)
                embed.add_field(
                    name=f"{idx}. {track.title}",
                    value=f"{track.author} — `{minutes}:{seconds:02d}`",
                    inline=False
                )
            return await ctx.send(embed=embed)

        # 3) Paginated
        paginator = QueuePaginator(ctx, queue)
        embed     = paginator.make_embed()
        message   = await ctx.send(embed=embed, view=paginator)
        paginator.message = message

    @commands.command()
    @commands.check(create_player)
    async def clear(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        queue = player.queue
        queue.clear()
        embed = discord.Embed(title="Queue cleared!", color=discord.Color.dark_red())
        await ctx.send(embed=embed)

    @commands.command()
    @commands.check(create_player)
    async def skip(self, ctx):
        await self.player.skip()

    @commands.command()
    @commands.check(create_player)
    async def loop(self, ctx):


        if self.player.loop == self.player.LOOP_NONE:
            self.player.set_loop(1)
            embed = discord.Embed(title="🔁 Loop mode activated",
                          description=f'{self.player.current.title} is looping.',
                          color=discord.Color.green())
            embed.set_footer(text='Loop mode: Single Track')

        elif self.player.loop == self.player.LOOP_SINGLE:
            self.player.set_loop(2)
            embed = discord.Embed(title="🔁 Loop mode changed",
                          description=f'Playlist {self.playlist.playlist_info.name} is looping.',
                          color=discord.Color.teal())
            embed.set_footer(text='Loop mode: Queue')
            await ctx.send(f'Queue is looping!')
        elif self.player.loop == self.player.LOOP_QUEUE:
            self.player.set_loop(0)
            embed = discord.Embed(title="🔁 Loop mode disabled",
                                  color=discord.Color.red())
            await ctx.send(f'Not looping!')

        await ctx.send(embed=embed)

    @commands.command(aliases=['sh'])
    @commands.check(create_player)
    async def shuffle(self, ctx):
        """
        Toggle manual shuffle:
         - On: save the current queue order, shuffle in-place, and ENSURE Lavalink shuffle = OFF.
         - Off: restore the saved order, and keep Lavalink shuffle = OFF.
        """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        queue = player.queue
        gid = ctx.guild.id

        if not queue:
            return await ctx.send("❌ Nothing in queue to shuffle!")

        # Are we currently “un‐shuffled”? (i.e. no stash)
        if gid not in self._original_queues:
            # **turn shuffle on**: stash & shuffle
            self._original_queues[gid] = list(queue)
            random.shuffle(queue)
            title = "🔀 Queue shuffled!"
            color = discord.Colour.green()
        else:
            # **turn shuffle off**: restore
            original = self._original_queues.pop(gid)
            queue.clear()
            queue.extend(original)
            title = "↩️ Queue order restored"
            color = discord.Colour.blurple()


        player.set_shuffle(False)

        embed = discord.Embed(title=title, color=color)
        embed.set_footer(text="Shuffle is now " + ("ON" if gid in self._original_queues else "OFF"))
        await ctx.send(embed=embed)

    @commands.command(name='join')
    @commands.check(create_player)
    async def join(self, ctx):
        await ctx.send("⋆⁺₊⋆ ☾⋆⁺₊⋆ | Joined Voice Channel.")

    @commands.command()
    async def test(self, ctx):
        case = int(input("Input what you want to test:\n 1- Is_connected \n 2- Is_playing\n 3- Is_Stream \n"))
        print(f'Case is: {case}')

        if case == 1:
            print(self.player.is_connected)
        elif case == 2:
            print(self.player.is_playing)
        elif case == 3:
            print(self.player.current.is_stream)
        else:
            print(f'Invalid input')

    """
    @commands.Cog.listener()
    async def on_disconnect(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        player.queue.clear()
        await player.stop
        await ctx.send("Player has disconnected")
    """


async def setup(bot):
    await bot.add_cog(Music_lavalink(bot))