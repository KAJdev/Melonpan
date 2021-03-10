import ast
import discord
import config
import traceback
import datetime
import market
import asyncio

from discord.ext import commands

class LootBoxes(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    

def setup(bot):
    bot.add_cog(LootBoxes(bot))