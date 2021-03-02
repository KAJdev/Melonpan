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

    @commands.group(aliases=['collectables', 'badge', 'collect'])
    async def badges(self, ctx):
        if ctx.invoked_subcommand is None:
            on_sale = list((config.badges[x['index']], x['price'], x['index']) for x in config.current_collectables)

            embed = discord.Embed(
                title="Badge Shop",
                description="Badges will be displayed on your `stats` page, and are only available for a limited amount of time.",
                color=config.MAINCOLOR
            )

            for x in on_sale:
                embed.add_field(name=f"{x[0]['emoji']} {x[0]['name']}", value=f"Cost: **{x[1]}** <:BreadCoin:815842873937100800>\n`pan badge buy {x[2]}`")

            await ctx.send(embed=embed)

    @badges.command()
    async def buy(self, ctx, name:str=None):
        pass


def setup(bot):
    bot.add_cog(Badges(bot))