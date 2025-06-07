import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.command()
    async def kick(self, ctx, user: discord.Member, reason=None):
        await user.kick(reason=reason)

    @commands.command()
    async def ban(self, ctx, user: discord.Member, reason=None):
        await user.ban(reason=reason)