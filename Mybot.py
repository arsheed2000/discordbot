import discord
from discord.ext import commands




#client = discord.Client(intents=intents)
client = commands.Bot(command_prefix = '!', intents = discord.Intents.all())

@client.event
async def on_ready():
    print(f'logged in as{client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("hello")

    await client.process_commands(message)


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







client.run('')
