import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"{bot.user.name} is online!")

@bot.command()
async def greet(ctx):
    await ctx.send(f"Hello, {ctx.author.mention}!")

@bot.tree.command(name="ping")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message("Slash command pong!")

bot.run("OTI3Mjg5NzQ0NDM2NjU4MTg4.GJnr9C.hUP7WK8PlTvs86zBJLhUJeAO06C9_IeX6SqjHs")