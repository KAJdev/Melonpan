import ast
import discord
import config
import traceback
import datetime
import market

from discord.ext import commands

class Badges(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    

def setup(bot):
    bot.add_cog(Badges(bot))