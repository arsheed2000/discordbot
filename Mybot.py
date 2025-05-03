import os
from dotenv import load_dotenv, dotenv_values
import discord
from discord import app_commands
from discord.ext import commands
from music import Music
from WelcomeMessage import WelcomeMessage
from Moderation import Moderation

load_dotenv()

client = commands.Bot(command_prefix = '!', intents = discord.Intents.all())



@client.event
async def on_ready():
    await client.tree.sync()
    print('Synced!')
    await client.add_cog(Music(client))
    await client.add_cog(WelcomeMessage(client))
    await client.add_cog(Moderation(client))
    print(f'logged in as{client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("hello")

    await client.process_commands(message)

#@client.tree.command(name="hello", description="Says penis")
#async def hello(interaction: discord.Interaction):
#    await interaction.response.send_message("Penis!!!")


@client.command()
async def nice(ctx):
    await ctx.send("nice")

@client.command()
async def hello(ctx):
    await ctx.send("nice")

@client.hybrid_command()
async def cock(ctx):
    await ctx.send("NICE")

@client.command()
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
