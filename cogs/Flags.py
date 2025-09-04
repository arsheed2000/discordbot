from pkgutil import get_data

"""UNFINISHED!!! WORK IN PROGRESS !!! UNFINISHED"""

import discord
from discord import ui
from discord.ext import commands
import urllib, json
import random

with urllib.request.urlopen("https://flagcdn.com/de/codes.json") as url:
    data = json.load(url)
flags = random.choices(list(data), k= 4)
class Flags(commands.Cog):

    def __init__(self, client):
        self.client = client


    @commands.command()
    async def quiz(self, ctx):
        random_flag = random.choice(list(data))
        print(random_flag)
        print(flags)
        embed = discord.Embed(title="What flag is this?")
        embed.set_image(url=f'https://flagcdn.com/256x192/{flags[0]}.png')
        embed.add_field(name=f'1- {data[flags[0]]}?', value='', inline=False)
        embed.add_field(name=f'2- {data[flags[1]]}?', value='', inline=False)
        embed.add_field(name=f'3- {data[flags[2]]}?', value='', inline=False)
        embed.add_field(name=f'4- {data[flags[3]]}?', value='', inline=False)

        await ctx.send(embed=embed)

class buttons(discord.ui.View, Flags):
    def __init__(self):
        super().__init__()


    def get_data(self):
            print(f'I got these flags: {flags}')
            return flags

    #for i in enumerate(Flags.flags):

    @ui.button(label="Click this", style=discord.ButtonStyle.blurple)
    async def button1(self , interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f'These are the flags{flags}')






