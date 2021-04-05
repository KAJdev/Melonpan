import ast
import discord
import config
import traceback
import datetime
import market

from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

class Badges(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def badges_command(self, ctx):
        on_sale = list((config.badges[x['index']], x['price'], x['index']) for x in config.current_collectables)

        embed = discord.Embed(
            title="Badge Shop",
            description="Badges will be displayed on your `pan stats` page, and are only available for a limited amount of time.",
            color=config.MAINCOLOR
        )

        for x in on_sale:
            embed.add_field(name=f"{x[0]['emoji']} {x[0]['name']}", value=f"Cost: **{x[1]}** <:BreadCoin:815842873937100800>\n`pan badge buy {x[2]}`")

        await ctx.send(embed=embed)

    async def badges_buy_command(self, ctx, index):
        user = self.bot.mongo.get_user(ctx.author.id)

        try:
            index = int(index)
        except:
            index = None

        if index is None:
            await config.reply(ctx, "<:melonpan:815857424996630548> `You must tell me the badge index you would like to purchase: e.g. 'pan badge buy 0'`")
            return

        chosen = None
        for x in config.current_collectables:
            if x['index'] == index:
                chosen = x

        if chosen is None:
            await config.reply(ctx, "<:melonpan:815857424996630548> `I don't see that badge on sale.`")
            return

        if user['money'] < chosen['price']:
            await config.reply(ctx, "<:melonpan:815857424996630548> `You don't have enough BreadCoin for this badge.`")
            return

        if index in user['badges']:
            await config.reply(ctx, "<:melonpan:815857424996630548> `You already have this badge.`")
            return

        self.bot.mongo.users.update_user(user, {'$inc': {'money': -chosen['price']}, '$push': {'badges': index}})

        chosen_badge = config.badges[index]

        await config.reply(ctx, f"Congratulations! You have purchased the {chosen_badge['emoji']} **{chosen_badge['name']}** Badge!")

    @commands.group(aliases=['collectables', 'badge', 'collect'])
    async def badges(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.badges_command(ctx)

    @badges.command()
    async def buy(self, ctx, index:str=None):
        await self.badges_buy_command(ctx, index)

    @cog_ext.cog_slash(name="badges",
        description="List all the badges you can buy.",
        options=[
           create_option(
             name="badge",
             description="Purchase a specific badge",
             option_type=3,
             required=False,
             choices = config.badge_choices
           )
         ])
    async def badges_slash(self, ctx: SlashContext, badge=None):
        if badge is None:
            await self.badges_command(ctx)
        else:
            await self.badges_buy_command(ctx, str(badge))


def setup(bot):
    bot.add_cog(Badges(bot))