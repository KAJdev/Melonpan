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

    async def top_command(self, ctx, field="money", side="<:BreadCoin:815842873937100800>", title="Richest Bakers"):
        top_global = list(self.bot.mongo.db.users.find({}).sort(field, pymongo.DESCENDING).limit(15))

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
            desc += f"`#{amount}` • **{user[field]:,}** {side} • {user['user_object'].name}{' ' if len(user.get('badges', [])) > 0 else ''}{''.join(config.badges[x]['emoji'] for x in user.get('badges', []))}\n"
            amount += 1

        # x.header = False
        # x.align = "l"

        embed = discord.Embed(
            title=title,
            color=config.MAINCOLOR,
            description = desc
            # description="```\n" + x.get_string() + "```"
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=['t', 'leaderboard', 'leaderboards', 'rich', 'fame'])
    async def top(self, ctx):
        await self.top_command(ctx)

    @cog_ext.cog_slash(name="leaderboard",
        description="Show the best bakers.",
        options=[
            create_option(
              name="skill",
              description="The skill to sort by",
              option_type=3,
              required=False,
              choices = [
                create_choice(name="Bread Coin", value="money"),
                create_choice(name="Oven Count", value="ovens"),
                create_choice(name="Inventory Space", value="inventory")
              ]
            )
        ])
    async def bake_slash(self, ctx: SlashContext, skill:str="money"):
        await ctx.defer()
        skills = {
            "money": {
                "field": "money",
                "side": '<:BreadCoin:815842873937100800>',
                "title": "Richest Bakers"
            },
            "baked": {
                "field": "baked",
                "side": 'Baked',
                "title": "Most Active Bakers"
            },
            "ovens": {
                "field": "oven_count",
                "side": "<:stove:815875824376610837>",
                "title": "Biggest Bakeries"
            },
            "inventory": {
                "field": "inventory_capacity",
                "side": "Storage",
                "title": "Biggest Inventories"
            }
        }
        await self.top_command(ctx, field=skills[skill]['field'], side=skills[skill]['side'], title=skills[skill]['title'])



def setup(bot):
    bot.add_cog(Leaderboards(bot))
