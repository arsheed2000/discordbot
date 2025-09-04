import logging
import os
import certifi
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord.ext.commands import CommandInvokeError, CheckFailure
from cogs.music import Music
from cogs.Moderation import Moderation
from cogs.music_slash import Music_slash
from cogs.Music_Lavalink import Music_lavalink
from cogs.Flags import Flags
from cogs.FlightRadar.Flights import Flights

import cogs.Music_Lavalink

load_dotenv()
os.environ['SSL_CERT_FILE'] = certifi.where()

client = commands.Bot(command_prefix = '!', intents = discord.Intents.all())

GUILD_ID = discord.Object(id=911735471439220797)

blocked_user_id = 136829487459978458

@client.check
async def block_specific_user(ctx):
    return ctx.author.id != blocked_user_id

@client.event
async def on_ready():
    #await client.tree.sync()
    await client.tree.sync(guild=GUILD_ID)
    print('Synced!')
    #await client.add_cog(Music(client))
    await client.add_cog(Moderation(client))
    #await client.add_cog(Music_slash(client))
    await client.add_cog(Music_lavalink(client))
    await client.add_cog(Flags(client))
    await client.add_cog(Flights(client))
    print(f'logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("hello")

    await client.process_commands(message)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandInvokeError):
        logging.error(f"Command failed: {str(error.original)}")

    else:
        raise error


@client.tree.command(name="hello", description="Says penis")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("Penis!!!")


@client.tree.command(name="nice", description="Nice!", guild=GUILD_ID)
async def nice(interaction: discord.Interaction):
    await interaction.response.send_message("Nice!")



@client.command()
async def hello(ctx):
    await ctx.send("nice")


@client.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()

@client.command()
async def add(ctx, left:int, right:int):
    await ctx.send(left + right)

@client.command()
async def embed(ctx):
    embedded = discord.Embed(title="User info",)
    await ctx.send(embed=embedded)

@client.command()
async def commands(ctx):
    embed = discord.Embed(title='Available Commands', colour=discord.Colour.purple())
    embed.add_field(name="Prefix", value='the prefix is: ?', inline=False)
    embed.add_field(name="Join", value='join a voice channel', inline=False)
    embed.add_field(name="play", value='stream music from link', inline=False)
    embed.add_field(name="Skip", value='skip current song', inline=False)
    embed.add_field(name="loop", value='switch between 2 looping modes: Single and Queue', inline=False)
    embed.add_field(name="shuffle", value='shuffle Queue', inline=False)
    embed.add_field(name="disconnect", value='it disconnects', inline=False)
    embed.add_field(name="queue", value='display queue', inline=False)
    embed.add_field(name="clear", value='clear queue', inline=False)

    await ctx.send(embed=embed)


client.run(os.getenv("TOKEN"))
