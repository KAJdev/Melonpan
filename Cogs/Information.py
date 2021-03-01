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
            today_price = round(item_price.get_price())
            assets += today_price

        embed=discord.Embed(
            title="Baker Balance",
            description=f"**Pocket**: `{user['money']}` <:BreadCoin:815842873937100800>\n**Bread Worth**: `{assets}` <:BreadCoin:815842873937100800> [<:BreadWarning:815842874226245643>]({ctx.message.jump_url} \"This value is based on the market and will change.\")\n**Total Assets**: `{user['money'] + assets}` <:BreadCoin:815842873937100800>",
            color=config.MAINCOLOR
        )

        await ctx.reply(embed=embed)

    @commands.command(aliases=['s', 'stat', 'info', 'profile', 'user'])
    async def stats(self, ctx, member : discord.Member = None):
        await ctx.send("This command is still in the oven ;)")
        return
        if member is None:
            member = ctx.author

        user = config.get_user(member.id)

        desc = f"This delver has participated in **{user['dives']}** dives, and died **{user['deaths']}** times.\nThey have survived **{user['encounters']}** encounters with beings in the abyss.\nThey have found **{user['found_artifacts']}** artifacts and sold **{len(user['sold'])}** artifacts in Orth.\nThey have **{user['money']}** Orth to their name."
        if user['current_action'] != None:
            desc+= f"\nThey are currently exploring **{config.layers[config.calculate_layer(user['current_depth'])]['name']}**."
        else:
            desc+= f"\nThey are currently visiting Orth."

        embed=discord.Embed(
            title="Delver Info",
            description="Information for the delver " + member.mention + f" {config.get_whistle(user['max_depth'])['emoji']}\n\n" + desc,
            color=config.MAINCOLOR
        )
        embed.set_thumbnail(url=member.avatar_url)

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Information(bot))