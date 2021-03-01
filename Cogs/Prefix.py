import pymongo
import asyncio
import config
import discord
import datetime
from discord.ext import commands, tasks
import logging

class Prefix(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def prefix(self, ctx, *, new_prefix : str = None):
        if not ctx.author.guild_permissions.manage_guild:
            new_prefix = None

        # get a server object with the id and prefix. Don't store it unless it's changed
        server = config.PREFIXES.find_one({'id': ctx.guild.id})

        # if they did not specify a prefix, then tell them what it is.
        if new_prefix is None:
            if server is None:
                server = {'id': ctx.guild.id, 'prefix': "n!"}
            await ctx.send(embed=discord.Embed(
                color=config.MAINCOLOR,
                description=f"This server's prefix is `{server['prefix']}`",
                title="Prefix"
            ))
            return

        # They did specify a prefix, validate it, and then update it.
        if len(new_prefix) > 20:
            await ctx.send(embed=discord.Embed(
                color=config.ERRORCOLOR,
                description="That is quite long. Are you sure you could even remember that? Why don't you try again.",
                title="Prefix Too Long"
            ))
            return

        # insert or update the prefix setting
        if server is not None:
            config.PREFIXES.update_one({'id': ctx.guild.id}, {'$set': {'prefix': new_prefix}})
        else:
            config.PREFIXES.insert_one({'id': ctx.guild.id, 'prefix': new_prefix})

        # anddd result!
        await ctx.send(embed=discord.Embed(
            color=config.MAINCOLOR,
            description=f"Your server's prefix is now `{new_prefix}`",
            title="Prefix Updated"
        ))


def setup(bot):
    bot.add_cog(Prefix(bot))