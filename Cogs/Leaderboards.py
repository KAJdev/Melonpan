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
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

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
        # x = PrettyTable()
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
            # x.add_row([f"#{amount}", user['user_object'].name, f"{user['money']} BreadCoin"])
            desc += f"`#{amount}` • **{user['money']:,}** <:BreadCoin:815842873937100800> • {user['user_object'].name}{' ' if len(user.get('badges', [])) > 0 else ''}{''.join(config.badges[x]['emoji'] for x in user.get('badges', []))}\n"
            amount += 1

        # x.header = False
        # x.align = "l"

        embed = discord.Embed(
            title="Richest Bakers",
            color=config.MAINCOLOR,
            description = desc
            # description="```\n" + x.get_string() + "```"
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Leaderboards(bot))