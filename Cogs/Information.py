import ast
import discord
import config
import traceback
import datetime
import market

from discord.ext import commands

class Information(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['i', 'inv', 'items', 'in', 'bag', 'breads', 'bread'])
    async def inventory(self, ctx):
        user = config.get_user(ctx.author.id)
        desc = ""
        if len(user['inventory']) < 1:
            desc = "You have no bread. Try managing your bakery with `bakery`."
        else:
            for a in user['inventory']:
                item = config.breads[a['index']]
                desc+=f"`{config.quality_levels[a['quality']]}` · **{item['name']}**\n"
        embed = discord.Embed(
            title="Bread Inventory",
            color=config.MAINCOLOR,
            description=desc
        )
        embed.set_footer(text=f"Storing {len(user['inventory'])}/25 breads")
        await ctx.reply(embed=embed)

    @commands.command(aliases=['money', 'balance'])
    async def bal(self, ctx, member : discord.Member = None):
        if member is None:
            member = ctx.author

        user = config.get_user(member.id)

        assets = 0
        for item in user['inventory']:
            r = config.breads[item['index']]
            item_price = market.ItemPrice(r['price'], 5, item['index'])
            today_price = round(item_price.get_price(market.get_day_of_year()))
            assets += today_price

        embed=discord.Embed(
            title="Baker Balance",
            description=f"**Pocket**: `{user['money']}` <:BreadCoin:815842873937100800>\n**Bread Worth**: `{assets}` <:BreadCoin:815842873937100800> [<:BreadWarning:815842874226245643>]({ctx.message.jump_url} \"This value is based on the market and will change.\")\n**Total Assets**: `{user['money'] + assets}` <:BreadCoin:815842873937100800>",
            color=config.MAINCOLOR
        )

        await ctx.reply(embed=embed)

    @commands.command(aliases=['s', 'stat', 'info', 'profile', 'user'])
    async def stats(self, ctx, member : discord.Member = None):
        if member is None:
            member = ctx.author

        user = config.get_user(member.id)
        embed=discord.Embed(
            title="Baker Info",
            color=config.MAINCOLOR
        )
        embed.set_thumbnail(url=member.avatar_url)

        guild = self.bot.get_guild(814958240009420830)
        mem = await guild.fetch_member(member.id)
        if 814964592076652554 in [x.id for x in mem.roles]:
            if 7 not in user['badges']:
                user['badges'].append(7)

        if len(user.get('badges', [])) > 0:
            embed.description = " ".join(config.badges[x]['emoji'] for x in user.get('badges', []))

        fav = {'name': "None", 'amount': 0}
        total = 0
        for x, y in user['baked'].items():
            total += y
            if y > fav['amount']:
                fav = {'name': config.breads[int(x)]['name'], 'amount': y}

        embed.add_field(name="Baking Stats", value=f"Favorite Bread: **{fav['name']}** ({fav['amount']} bakes)\nBreads Baked: **{total}**\nBreadCoin: **{user['money']}** <:BreadCoin:815842873937100800>\nOvens: **{user['oven_count']}**")

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Information(bot))