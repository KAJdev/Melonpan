import ast
import discord
import config
import traceback
import datetime
import market
import os
import psutil

from discord.ext import commands, tasks, menus
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

class Tutorial(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(Tutorial(bot))