import ast
import discord
import config
import traceback
import datetime
import random
import asyncio
import market
import matplotlib
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline, BSpline
import numpy as np

from discord.ext import commands, tasks

class Market(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['b', 'purchase'])
    async def buy(self, ctx, amount: str = None, *, item : str = None):
        user = config.get_user(ctx.author.id)

        if amount is None:
            amount = "1"
        if item is None:
            await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to buy: e.g. 'buy 4 baguette'`")
            return

        today = datetime.datetime.now().timetuple().tm_yday
        random.seed(today)
        display = random.sample(config.breads, k=9)
        selected = None
        for r in display:
            if item.lower() in r['name'].lower():
                selected = r
                break
            try:
                index = int(item)
                if index == config.breads.index(r):
                    selected = r
                    break
            except:
                pass
        if selected is None:
            await ctx.send("<:melonpan:815857424996630548> `That bread doesn't look like it's on sale today...`")
        else:
            try:
                amount = abs(int(amount))
            except:
                await ctx.send("<:melonpan:815857424996630548> `Amount must be a number: e.g. 'buy 4 baguette'`")
                return

            item_price = market.ItemPrice(selected['price'], 5, config.breads.index(selected))
            today_price = round(item_price.get_price(today))

            if user['money'] < today_price * amount:
                await ctx.send("<:melonpan:815857424996630548> `It doesn't look like you have enough for this item.`")
            elif len(user['inventory']) + amount > 25:
                await ctx.send("<:melonpan:815857424996630548> `It doesn't look like you have enough space in your bag.`")
            else:
                new_relics = []
                for _ in range(amount):
                    new_relics.append({
                            'index': config.breads.index(selected),
                            'quality': random.randint(1, 5)
                        }
                    )

                config.USERS.update_one({'id': ctx.author.id}, {'$push': {'inventory': {'$each': new_relics}}, '$inc': {'money': -today_price * amount}})

                total = amount * today_price

                desc = f"```************\nCASH RECEIPT\n************\nDescription\n- {amount}x {selected['name']}\n\n============\nTOTAL AMOUNT: {total} BreadCoin\nTAX: 0 BreadCoin\n============\nTHANK YOU!```"

                await ctx.reply(embed=discord.Embed(
                    title="Bread Market Exchange Receipt",
                    color=discord.Color(0xebeae8),
                    description=desc,
                    timestamp=datetime.datetime.utcnow()
                ))

    @commands.command(aliases=['se', 's'])
    async def sell(self, ctx, amount: str = None, *, item : str = None):
        user = config.get_user(ctx.author.id)

        if amount is None:
            amount = "1"
        if item is None:
            await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to sell: e.g. 'sell 4 baguette'`")
            return

        today = datetime.datetime.now().timetuple().tm_yday
        random.seed(today)
        display = random.sample(config.breads, k=9)
        selected = None
        for r in display:
            if item.lower() in r['name'].lower():
                selected = r
                break
            try:
                index = int(item)
                if index == config.breads.index(r):
                    selected = r
                    break
            except:
                pass
        if selected is None:
            await ctx.send("<:melonpan:815857424996630548> `That bread doesn't look like it's on the market today...`")
        else:
            try:
                amount = abs(int(amount))
            except:
                await ctx.send("<:melonpan:815857424996630548> `Amount must be a number: e.g. 'sell 4 baguette'`")
                return

            item_price = market.ItemPrice(selected['price'], 5, config.breads.index(selected))
            today_price = round(item_price.get_price(today))

            selling = []
            for their_item in user['inventory']:
                if their_item['index'] == config.breads.index(selected):
                    selling.append(their_item)
                if len(selling) >= amount:
                    break
            if len(selling) < amount:
                await ctx.send(f"<:melonpan:815857424996630548> `It looks like you only have {len(selling)} of that bread in your bag.`")
            else:
                total = amount * today_price

                for selling_item in selling:
                    user['inventory'].remove(selling_item)

                config.USERS.update_one({'id': ctx.author.id}, {'$set': {'inventory': user['inventory']}, '$inc': {'money': total}})

                desc = f"```************\nSOLD RECEIPT\n************\nDescription\n- {amount}x {selected['name']}\n\n============\nTOTAL AMOUNT: {total} BreadCoin\nTAX: 0 BreadCoin\n============\nTHANK YOU!```"

                await ctx.reply(embed=discord.Embed(
                    title="Bread Market Exchange Receipt",
                    color=discord.Color(0xebeae8),
                    description=desc,
                    timestamp=datetime.datetime.utcnow()
                ))


    @commands.command(aliases=['sa'])
    async def sellall(self, ctx, *, item : str = None):
        user = config.get_user(ctx.author.id)

        if item is None:
            today = datetime.datetime.now().timetuple().tm_yday
            random.seed(today)
            display = random.sample(config.breads, k=9)
            selling = []
            total = 0
            desc = "```************\nSOLD RECEIPT\n************\nDescription"
            for on_sale in display:
                item_price = market.ItemPrice(on_sale['price'], 5, config.breads.index(on_sale))
                today_price = round(item_price.get_price(today))

                this_selling = []
                for their_item in user['inventory']:
                    if their_item['index'] == config.breads.index(on_sale):
                        this_selling.append(their_item)
                        selling.append(their_item)
                total += len(this_selling) * today_price
                if len(this_selling) > 0:
                    desc += f"\n- {len(this_selling)}x {on_sale['name']}"

            for selling_item in selling:
                user['inventory'].remove(selling_item)

            
            if len(selling) > 0:
                config.USERS.update_one({'id': ctx.author.id}, {'$set': {'inventory': user['inventory']}, '$inc': {'money': total}})

                desc += f"\n\n============\nTOTAL AMOUNT: {total} BreadCoin\nTAX: 0 BreadCoin\n============\nTHANK YOU!```"

                await ctx.reply(embed=discord.Embed(
                    title="Bread Market Exchange Receipt",
                    color=discord.Color(0xebeae8),
                    description=desc,
                    timestamp=datetime.datetime.utcnow()
                ))
            else:
                await ctx.reply("<:melonpan:815857424996630548> `There was nothing sellable in your inventory.`")
        else:
            today = datetime.datetime.now().timetuple().tm_yday
            random.seed(today)
            display = random.sample(config.breads, k=9)
            selected = None
            for r in display:
                if item.lower() in r['name'].lower():
                    selected = r
                    break
                try:
                    index = int(item)
                    if index == config.breads.index(r):
                        selected = r
                        break
                except:
                    pass
            if selected is None:
                await ctx.send("<:melonpan:815857424996630548> `That bread doesn't look like it's on the market today...`")
            else:
                item_price = market.ItemPrice(selected['price'], 5, config.breads.index(selected))
                today_price = round(item_price.get_price(today))

                selling = []
                for their_item in user['inventory']:
                    if their_item['index'] == config.breads.index(selected):
                        selling.append(their_item)
                total = len(selling) * today_price

                for selling_item in selling:
                    user['inventory'].remove(selling_item)

                config.USERS.update_one({'id': ctx.author.id}, {'$set': {'inventory': user['inventory']}, '$inc': {'money': total}})

                desc = f"```************\nSOLD RECEIPT\n************\nDescription\n- {len(selling)}x {selected['name']}\n\n============\nTOTAL AMOUNT: {total} BreadCoin\nTAX: 0 BreadCoin\n============\nTHANK YOU!```"

                await ctx.reply(embed=discord.Embed(
                    title="Bread Market Exchange Receipt",
                    color=discord.Color(0xebeae8),
                    description=desc,
                    timestamp=datetime.datetime.utcnow()
                ))

    @commands.command(aliases=['sh', 'store', 'shopping', 'market', 'markets'])
    async def shop(self, ctx, *, item : str = None):
        today = datetime.datetime.now().timetuple().tm_yday
        if item is None:
            random.seed(today)
            display = random.sample(config.breads, k=9)

            embed = discord.Embed(
                title="Bread Market",
                color=config.MAINCOLOR,
                description="Use the `buy` and `sell` commands to exchange Breads.\n*These are the tradable breads for today*\n\nuse `shop <item>` to view a specific item"
            )
            for i in display:
                item = market.ItemPrice(i['price'], 5, config.breads.index(i))
                yesterday = today - 1
                if yesterday < 1: yesterday = 1

                yesterday_price = round(item.get_price(yesterday))
                today_price = round(item.get_price(today))

                last_price = ""
                if today_price > yesterday_price:
                    last_price = "<:up:792989132069797909> +" + str(today_price - yesterday_price)
                elif today_price < yesterday_price:
                    last_price = "🔻 -" + str(yesterday_price - today_price)
                else:
                    last_price = "🔸 0"

                embed.add_field(
                    name=f"{i['name']}",
                    value=f"`{today_price}` <:BreadCoin:815842873937100800>\n{last_price}"
                )
            reset_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
            change = reset_time - reset_time

            hours, remainder = divmod(change.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)

            embed.set_footer(text=f"Shop changes in {round(hours)}h {round(minutes)}m {round(seconds)}s")
            await ctx.send(embed=embed)
        else:
            random.seed(today)
            selected = None
            for r in config.breads:
                if item.lower() in r['name'].lower():
                    selected = r
                    break
                try:
                    index = int(item)
                    if index == config.breads.index(r):
                        selected = r
                        break
                except:
                    pass
            if selected is None:
                await ctx.send("<:melonpan:815857424996630548> `That bread hasn't been heard of before...`")
            else:
                item = market.ItemPrice(selected['price'], 5, config.breads.index(selected))

                prices = []
                for _ in range(1, 31):
                    day = today - _
                    if day < 1:
                        day += 365
                    prices.append(item.get_price(day))

                fig, ax = plt.subplots(figsize=(8, 2),frameon=False)
                #ax.axis('off')
                fig.patch.set_visible(False)

                x = np.array(list(range(1, 31)))
                y = np.array(prices)

                #define x as 200 equally spaced values between the min and max of original x
                xnew = np.linspace(x.min(), x.max(), 65)

                #define spline
                spl = make_interp_spline(x, y, k=3)
                y_smooth = spl(xnew)

                ax.plot(xnew, y_smooth)
                #ax.plot(x, y)

                #ax.set(ylabel='Price (Orth)')

                ax.spines['bottom'].set_color('white')
                ax.spines['top'].set_color('white')
                ax.spines['right'].set_color('white')
                ax.spines['left'].set_color('white')
                ax.yaxis.label.set_color('white')
                ax.xaxis.label.set_color('white')
                ax.tick_params(axis='x', colors='white')
                ax.tick_params(axis='y', colors='white')

                fig.savefig("tempgraph.png", transparent=True, bbox_inches='tight')

                file = discord.File("tempgraph.png") # an image in the same folder as the main bot file

                embed = discord.Embed(
                    title="Bread info",
                    color=config.MAINCOLOR,
                    description=f"**{selected['name']}**\n```{selected['description']}```\nCurrent Price: **{round(item.get_price(today))}** <:BreadCoin:815842873937100800>\nBake Time: **{selected['bake_time']} min.**"
                )
                embed.set_image(url="attachment://tempgraph.png")
                embed.set_thumbnail(url=selected['image'])

                await ctx.send(embed=embed, file=file)






def setup(bot):
    bot.add_cog(Market(bot))