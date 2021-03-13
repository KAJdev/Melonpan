import ast
import discord
import config
import traceback
import datetime
import market
import os
import psutil

from discord.ext import commands, tasks, menus

class Tutorial(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(Tutorial(bot))