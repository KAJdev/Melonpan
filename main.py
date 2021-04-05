print("Bot Writen By: KAJ7#0001")
# Imports
import asyncio
import config
import discord
import datetime
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
import discord_slash
import os
import logging
import random
import traceback
import sys
import inspect

logging.basicConfig(level = logging.INFO, format="Melonpan [%(levelname)s] | %(message)s")

async def get_prefix(bot, message):
    li = ['pan ', 'Pan ', 'PaN ', 'pAn ', 'paN ', 'PAn ', 'PaN ', 'PAn ', 'PAN ']
    return commands.when_mentioned_or(*li)(bot, message)

intents = discord.Intents.default()
#intents.members = True

# Set prefix and set case insensitive to true so the a command will work if miscapitlized
bot = commands.Bot(command_prefix = get_prefix, case_insensitive = True, intents=intents)
slash = SlashCommand(bot, sync_commands=True)

# Remove default help command
bot.remove_command("help")

@bot.event
async def on_message(message):
    if message.content.lower().startswith("pan sell all"):
        message.content = "pan sellall" + message.content[12:]
    ctx = await bot.get_context(message)
    await bot.invoke(ctx)

@bot.event
async def on_message_edit(before, after):
    if after.content.lower().startswith("pan sell all"):
        after.content = "pan sellall" + after.content[12:]
    ctx = await bot.get_context(after)
    await bot.invoke(ctx)

# Cogs
cogs = ["Eval", "Information", "Market", "Bakery", "StatCord", "Leaderboards", "Badges", "Blacklist", "Drops", "LootBoxes", "Vote", "Guilds", "Trading", "Core"]

# Starts all cogs
for cog in cogs:
    bot.load_extension("Cogs." + cog)

@bot.check
def check_for_blacklist(ctx):
    if ctx.guild is not None:
        server = config.get_server(ctx.guild.id)
        return not (ctx.channel.id in server.blacklist)
    else:
        return True

@bot.event
async def on_guild_join(guild):
    logging.info("JOINED guild " + guild.name + " | current guilds: " + str(len(bot.guilds)))

@bot.event
async def on_guild_remove(guild):
    logging.info("LEFT guild " + guild.name + " | current guilds: " + str(len(bot.guilds)))

# Command error
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, discord.errors.Forbidden):
        logging.error("Forbidden action: " + str(error))
    elif isinstance(error, commands.errors.CheckFailure):
        pass
    elif isinstance(error, commands.errors.UserInputError):
        pass
    elif isinstance(error, commands.errors.MemberNotFound):
        embed = discord.Embed(
            title = "User not found",
            #description = f"An error has occured while executing this command, please join the support server and report the issue!",
            color = config.ERRORCOLOR
        )
        await ctx.send(embed = embed)
    else:
        await ctx.send(content="An error has occured while executing this command.\nPlease join the support server and report the issue!\ndiscord.gg/rMgtgdavPh")
        raise error

# On ready
@bot.event
async def on_ready():
    logging.info(f"Bot has started succesfully in {len(bot.guilds)} server(s) with {len(bot.users)} users!")

    await bot.change_presence(activity = discord.Activity(type=discord.ActivityType.watching, name="pan help"))


# Starts bot
bot.run(os.environ.get("MELONPAN_TOKEN"))
