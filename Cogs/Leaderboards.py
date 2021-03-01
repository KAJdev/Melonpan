import ast
import discord
import config
import datetime
import random
import asyncio
import pymongo
from prettytable import PrettyTable
from prettytable import MARKDOWN

from discord.ext import commands, tasks

class Leaderboards(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.user_cache = {}

    @commands.command(aliases=['t', 'leaderboard', 'leaderboards', 'rich', 'fame'])
    async def top(self, ctx):
        top_global = list(config.USERS.find({}).sort('money', pymongo.DESCENDING).limit(15))

        to_remove = []
        amount = 1
        desc = ""
        x = PrettyTable()
        for user in top_global:
            if amount >= 11: break
            if user['id'] in self.user_cache.keys():
                user['user_object'] = self.user_cache[user['id']]
            else:
                try:
                    found = await self.bot.fetch_user(user['id'])
                except:
                    to_remove.append(user)
                    continue

                user['user_object'] = found
                self.user_cache[user['id']] = found
            x.add_row([f"#{amount}", user['user_object'].name, f"{user['money']} BreadCoin"])
            #desc += f"`#{amount}` **{user['user_object'].name}**#{user['user_object'].discriminator}      {user['money']} Orth      {user['found_artifacts']} Relics Collected\n"
            amount += 1

        x.header = False
        x.align = "l"

        embed = discord.Embed(
            title="Richest Bakers",
            color=config.MAINCOLOR,
            description="```\n" + x.get_string() + "```"
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Leaderboards(bot))