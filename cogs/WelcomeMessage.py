import discord
from discord.ext import commands

class WelcomeMessage(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.client.get_channel(911735471938367489)
        await channel.send(f'hello! ' + member.name)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = self.client.get_channel(911735471938367489)
        await channel.send(f'Goodbye! ' + member.name)






