import logging
import os
import certifi
from dotenv import load_dotenv
import discord
from discord.ext import commands
from cogs.music import Music
from cogs.Moderation import Moderation
from cogs.music_slash import Music_slash
from cogs.Music_Lavalink import Music_lavalink

load_dotenv()
os.environ['SSL_CERT_FILE'] = certifi.where()

client = commands.Bot(command_prefix = '!', intents = discord.Intents.all())

GUILD_ID = discord.Object(id=911735471439220797)

blocked_user_id = 321688035555278848

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
    await client.add_cog(Music_slash(client))
    await client.add_cog(Music_lavalink(client))
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
    if isinstance(error, commands.CommandInvokeError):
        logging.error(f"Command failed: {str(error.original)}")

    if isinstance(error, commands.CheckFailure):
        await ctx.send("Fuck you")


@client.tree.command(name="hello", description="Says penis")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("Penis!!!")


@client.tree.command(name="nice", description="Nice!", guild=GUILD_ID)
async def nice(interaction: discord.Interaction):
    await interaction.response.send_message("Nice!")


@client.command()
async def penis(ctx):
    await ctx.send("HARD")

@client.command()
async def hello(ctx):
    await ctx.send("nice")

@client.hybrid_command()
async def cock(ctx):
    await ctx.send("NICE")

@client.command(aliases=["69"])
async def vnice(ctx):
    await ctx.send("VERY NICE")


@client.command(aliases=["j"])
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.message.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("Not gonna work buddy!")

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

client.run(os.getenv("TOKEN"))
