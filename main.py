print("Bot Writen By: KAJ7#0001")
# Imports
import asyncio
import config
import discord
import datetime
from discord.ext import commands
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

# Remove default help command
bot.remove_command("help")

@bot.command(aliases=['settings', 'h'])
async def help(ctx):
    await ctx.send(embed=discord.Embed(
        title="Melonpan Commands",
        color=config.MAINCOLOR
    ).add_field(
        name="Information",
        value="`inventory`, `stats`, `bal`",
        inline=False
    ).add_field(
        name="Bakery",
        value="`bakery`, `bake`, `plate`, `build`",
        inline=False
    ).add_field(
        name="Market",
        value="`sell`, `buy`, `shop`",
        inline=False
    ).add_field(
        name="Misc",
        value="`help`, `invite`, `top`",
        inline=False
    ).set_thumbnail(url=bot.user.avatar_url))

@bot.command(aliases = ['join'])
async def invite(ctx):
    await ctx.send(embed=discord.Embed(description="[**Invite Link**](https://discord.com/api/oauth2/authorize?client_id=815835732979220501&permissions=314433&scope=bot) 🔗", color = config.MAINCOLOR))

# Cogs
cogs = ["Eval", "Information", "Market", "Bakery", "StatCord", "Leaderboards"]

# Starts all cogs
for cog in cogs:
    bot.load_extension("Cogs." + cog)

# Check to see if the user invoking the command is in the OWNERIDS config
def owner(ctx):
    return int(ctx.author.id) in config.OWNERIDS

# Restarts and reloads all cogs
@bot.command()
@commands.check(owner)
async def restart(ctx):
    """
    Restart the bot.
    """
    restarting = discord.Embed(
        title = "Restarting...",
        color = config.MAINCOLOR
    )
    msg = await ctx.send(embed = restarting)
    for cog in cogs:
        bot.reload_extension("Cogs." + cog)
        restarting.add_field(name = f"{cog}", value = "✅ Restarted!")
        await msg.edit(embed = restarting)
    restarting.title = "Bot Restarted"
    await msg.edit(embed = restarting)
    logging.info(f"Bot has been restarted succesfully in {len(bot.guilds)} server(s) with {len(bot.users)} users by {ctx.author.name}#{ctx.author.discriminator} (ID - {ctx.author.id})!")
    await msg.delete(delay = 3)
    if ctx.guild != None:
        await ctx.message.delete(delay = 3)

# Kills the bot
@bot.command()
@commands.check(owner)
async def kill(ctx):
    """
    kill the bot.
    """
    sys.exit(0)

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
    elif isinstance(error, commands.errors.MemberNotFound):
        embed = discord.Embed(
            title = "User not found",
            #description = f"An error has occured while executing this command, please join the support server and report the issue!",
            color = config.ERRORCOLOR
        )
        await ctx.send(embed = embed)
    else:
        await ctx.send(content="An error has occured while executing this command, please join the support server and report the issue!\n\ndiscord.gg/bread")
        raise error

# On ready
@bot.event
async def on_ready():
    logging.info(f"Bot has started succesfully in {len(bot.guilds)} server(s) with {len(bot.users)} users!")

    await bot.change_presence(activity = discord.Activity(type=discord.ActivityType.watching, name="pan help"))


# Starts bot
bot.run(os.environ.get("MELONPAN_TOKEN"))