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
        server = config.get_server(ctx.guild.id)

        if amount is None:
            amount = "1"
        if item is None:
            await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to buy: e.g. 'pan buy 4 baguette'`")
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
        elif not selected['buyable']:
            await ctx.send("<:melonpan:815857424996630548> `That cannot be purchased.`")
        else:
            try:
                amount = abs(int(amount))
            except:
                await ctx.send("<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan buy 4 baguette'`")
                return

            item_price = market.ItemPrice(selected['price'], selected['volitility'], config.breads.index(selected))
            today_price = round(item_price.get_price(market.get_day_of_year_active()))

            if user['money'] < today_price * amount:
                await ctx.send("<:melonpan:815857424996630548> `It doesn't look like you have enough for this item.`")
            elif len(user['inventory']) + amount > user.get('inventory_capacity', 25):
                await ctx.send("<:melonpan:815857424996630548> `It doesn't look like you have enough space in your bag.`")
            else:
                new_relics = []
                for _ in range(amount):
                    new_relics.append(server.create_bread(selected))

                config.USERS.update_one({'id': ctx.author.id}, {'$push': {'inventory': {'$each': new_relics}}, '$inc': {'money': -today_price * amount}})

                total = amount * today_price

                desc = f"```************\nCASH RECEIPT\n************\nDescription\n- {amount}x {selected['name']}\n\n============\nTOTAL AMOUNT: {total} BreadCoin\nTAX: 0 BreadCoin\n============\nTHANK YOU!```"

                await ctx.reply_safe(embed=discord.Embed(
                    title="Bread Market Exchange Receipt",
                    color=discord.Color(0xebeae8),
                    description=desc,
                    timestamp=datetime.datetime.utcnow()
                ))

    @commands.command(aliases=['d', 'give', 'trash'])
    async def donate(self, ctx, amount: str = None, *, item : str = None):
        user = config.get_user(ctx.author.id)
        server = config.get_server(ctx.guild.id)

        if amount is None:
            amount = "1"
        if item is None:
            await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to donate: e.g. 'pan donate 4 baguette'`")
            return

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
            await ctx.send("<:melonpan:815857424996630548> `That bread doesn't look like it exists...`")
        else:
            try:
                amount = abs(int(amount))
            except:
                await ctx.send("<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan donate 4 baguette'`")
                return

            selling = []
            sorted_list = []
            for _ in user['inventory']:
                if _.get('special', None) is None:
                    sorted_list.insert(0, _)
                else:
                    sorted_list.append(_)

            for their_item in sorted_list:
                if their_item['index'] == config.breads.index(selected):
                    selling.append(their_item)
                if len(selling) >= amount:
                    break
            if len(selling) < amount:
                await ctx.send(f"<:melonpan:815857424996630548> `It looks like you only have {len(selling)} of that bread in your bag.`")
            else:
                total = 0
                for selling_item in selling:
                    __ = config.breads[selling_item['index']]
                    item_price = market.ItemPrice(__['price'], __['volitility'], selling_item['index'])
                    total += round(item_price.get_price(market.get_day_of_year_active()))

                    user['inventory'].remove(selling_item)

                server.add_money(total)

                config.USERS.update_one({'id': ctx.author.id}, {'$set': {'inventory': user['inventory']}})

                desc = f"```**********\nDONATE RECEIPT\n**********\nDescription\n- {amount}x {selected['name']}\n\nTHANK YOU!```"

                await ctx.reply_safe(embed=discord.Embed(
                    title="Bread Market Donation Receipt",
                    color=discord.Color(0xebeae8),
                    description=desc,
                    timestamp=datetime.datetime.utcnow()
                ))

    @commands.command(aliases=['se', 's'])
    async def sell(self, ctx, amount: str = None, *, item : str = None):
        if ctx.guild is None:
            await ctx.send("<:melonpan:815857424996630548> `This command cannot be used in Direct Messages.`")
            return
        user = config.get_user(ctx.author.id)
        server = config.get_server(ctx.guild.id)
        selected = None

        if amount is None:
            amount = "1"
        else:
            special = None
            check_string = amount
            if item is not None:
                check_string += " " + item
            for i in user['inventory']:
                if i.get('special', None) == check_string:
                    special = i
                    break
            if special is not None:
                __ = config.breads[special['index']]
                item_price = market.ItemPrice(__['price'], __['volitility'], special['index'])
                today_price = round(item_price.get_price(market.get_day_of_year_active()))
                tax = round(today_price * server.tax)
                today_price -= tax
                today_price = round(today_price)

                server.add_money(tax)

                config.USERS.update_one({'id': ctx.author.id}, {'$pull': {'inventory': special}, '$inc': {'money': today_price}})

                desc = f"```************\nSOLD RECEIPT\n************\nDescription\n- 1x {__['name']}\n\n============\nTOTAL AMOUNT: {int(today_price)} BreadCoin\nTAX: {int(tax)} BreadCoin\n============\nTHANK YOU!```"

                await ctx.reply_safe(embed=discord.Embed(
                    title="Bread Market Exchange Receipt",
                    color=discord.Color(0xebeae8),
                    description=desc,
                    timestamp=datetime.datetime.utcnow()
                ))
                return

        if item is None:
            try:
                amount = abs(int(amount))
                await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to sell: e.g. 'pan sell 4 baguette'`")
                return
            except:
                item = amount
                amount = "1"
            
        if selected is None:
            today = datetime.datetime.now().timetuple().tm_yday
            random.seed(today)
            display = random.sample(config.breads, k=9)
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
        elif not selected['sellable']:
            await ctx.send("<:melonpan:815857424996630548> `That cannot be sold.`")
        else:
            try:
                amount = abs(int(amount))
            except:
                await ctx.send("<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan sell 4 baguette'`")
                return

            item_price = market.ItemPrice(selected['price'], selected['volitility'], config.breads.index(selected))
            today_price = round(item_price.get_price(market.get_day_of_year_active()))

            selling = []
            sorted_list = []
            for _ in user['inventory']:
                if _.get('special', None) is None:
                    sorted_list.insert(0, _)
                else:
                    sorted_list.append(_)

            for their_item in sorted_list:
                if their_item['index'] == config.breads.index(selected):
                    selling.append(their_item)
                if len(selling) >= amount:
                    break
            if len(selling) < amount:
                await ctx.send(f"<:melonpan:815857424996630548> `It looks like you only have {len(selling)} of that bread in your bag.`")
            else:
                total = amount * today_price
                tax = round(total * server.tax)
                total -= tax
                total = round(total)

                for selling_item in selling:
                    user['inventory'].remove(selling_item)

                server.add_money(tax)

                config.USERS.update_one({'id': ctx.author.id}, {'$set': {'inventory': user['inventory']}, '$inc': {'money': total}})

                desc = f"```************\nSOLD RECEIPT\n************\nDescription\n- {amount}x {selected['name']}\n\n============\nTOTAL AMOUNT: {int(total)} BreadCoin\nTAX: {int(tax)} BreadCoin\n============\nTHANK YOU!```"

                await ctx.reply_safe(embed=discord.Embed(
                    title="Bread Market Exchange Receipt",
                    color=discord.Color(0xebeae8),
                    description=desc,
                    timestamp=datetime.datetime.utcnow()
                ))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) == "💲":
            event = None
            for _ in config.SELL_BREAD_CACHE:
                if _[0].id == payload.message_id and _[1]['id'] == payload.user_id:
                    event = _
                    break
            if event is None:
                return
            config.SELL_BREAD_CACHE.remove(event)
            user = config.get_user(payload.user_id)
            server = config.get_server(payload.guild_id)
            today = datetime.datetime.now().timetuple().tm_yday
            random.seed(today)
            display = random.sample(config.breads, k=9)
            selling = []
            total = 0
            desc = "```************\nSOLD RECEIPT\n************\nDescription"
            for on_sale in display:
                if not on_sale['sellable']:
                    continue
                item_price = market.ItemPrice(on_sale['price'], on_sale['volitility'], config.breads.index(on_sale))
                today_price = round(item_price.get_price(market.get_day_of_year_active()))

                this_selling = []
                for their_item in user['inventory']:
                    if their_item['index'] == config.breads.index(on_sale):
                        can_sell = False
                        for _ in event[2]:
                            if _['uuid'] == their_item.get('uuid', None):
                                can_sell = True
                                break
                        if can_sell:
                            this_selling.append(their_item)
                            selling.append(their_item)
                total += len(this_selling) * today_price
                if len(this_selling) > 0:
                    desc += f"\n- {len(this_selling)}x {on_sale['name']}"

            for selling_item in selling:
                user['inventory'].remove(selling_item)

            print(f"QUICK SELL: ({event[1]['id']})")
            
            if len(selling) > 0:
                tax = round(total * server.tax)
                total -= tax
                total = round(total)

                server.add_money(tax)

                config.USERS.update_one({'id': payload.user_id}, {'$set': {'inventory': user['inventory']}, '$inc': {'money': total}})

                desc += f"\n\n============\nTOTAL AMOUNT: {int(total)} BreadCoin\nTAX: {int(tax)} BreadCoin\n============\nTHANK YOU!```"
                embed = event[0].embeds[0]
                embed.description += "\n\n**Bread Market Exchange Receipt**\n" + desc
                embed.timestamp=datetime.datetime.utcnow()
                embed.set_footer()
                await event[0].edit(embed=embed)
                await event[0].clear_reactions()
            else:
                embed = event[0].embeds[0]
                embed.set_footer()
                embed.description += "\n\n<:melonpan:815857424996630548> `There was nothing sellable in your inventory.`"
                await event[0].edit(embed=embed)
                await event[0].clear_reactions()


    @commands.command(aliases=['sa'])
    async def sellall(self, ctx, *, item : str = None):
        if ctx.guild is None:
            await ctx.send("<:melonpan:815857424996630548> `This command cannot be used in Direct Messages.`")
            return
        user = config.get_user(ctx.author.id)
        server = config.get_server(ctx.guild.id)

        if item is None:
            today = datetime.datetime.now().timetuple().tm_yday
            random.seed(today)
            display = random.sample(config.breads, k=9)
            selling = []
            total = 0
            desc = "```************\nSOLD RECEIPT\n************\nDescription"
            for on_sale in display:
                if not on_sale['sellable']:
                    continue
                item_price = market.ItemPrice(on_sale['price'], on_sale['volitility'], config.breads.index(on_sale))
                today_price = round(item_price.get_price(market.get_day_of_year_active()))

                this_selling = []
                for their_item in user['inventory']:
                    if their_item['index'] == config.breads.index(on_sale) and their_item.get('special', None) is None:
                        this_selling.append(their_item)
                        selling.append(their_item)
                total += len(this_selling) * today_price
                if len(this_selling) > 0:
                    desc += f"\n- {len(this_selling)}x {on_sale['name']}"

            for selling_item in selling:
                user['inventory'].remove(selling_item)

            
            if len(selling) > 0:
                tax = round(total * server.tax)
                total -= tax
                total = round(total)

                server.add_money(tax)

                config.USERS.update_one({'id': ctx.author.id}, {'$set': {'inventory': user['inventory']}, '$inc': {'money': total}})

                desc += f"\n\n============\nTOTAL AMOUNT: {int(total)} BreadCoin\nTAX: {int(tax)} BreadCoin\n============\nTHANK YOU!```"

                await ctx.reply_safe(embed=discord.Embed(
                    title="Bread Market Exchange Receipt",
                    color=discord.Color(0xebeae8),
                    description=desc,
                    timestamp=datetime.datetime.utcnow()
                ))
            else:
                await ctx.reply_safe("<:melonpan:815857424996630548> `There was nothing sellable in your inventory.`")
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
            elif not selected['sellable']:
                await ctx.send("<:melonpan:815857424996630548> `That cannot be sold.`")
            else:
                item_price = market.ItemPrice(selected['price'], selected['volitility'], config.breads.index(selected))
                today_price = round(item_price.get_price(market.get_day_of_year_active()))

                selling = []
                for their_item in user['inventory']:
                    if their_item['index'] == config.breads.index(selected) and their_item.get('special', None) is None:
                        selling.append(their_item)
                total = len(selling) * today_price

                for selling_item in selling:
                    user['inventory'].remove(selling_item)

                tax = round(total * server.tax)
                total -= tax
                total = round(total)

                server.add_money(tax)

                config.USERS.update_one({'id': ctx.author.id}, {'$set': {'inventory': user['inventory']}, '$inc': {'money': total}})

                desc = f"```************\nSOLD RECEIPT\n************\nDescription\n- {len(selling)}x {selected['name']}\n\n============\nTOTAL AMOUNT: {int(total)} BreadCoin\nTAX: {int(tax)} BreadCoin\n============\nTHANK YOU!```"

                await ctx.reply_safe(embed=discord.Embed(
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
            if ctx.guild is not None:
                server_tax = str(int(round(config.get_server(ctx.guild.id).tax*100))) + "%"
            else:
                server_tax = "N/A"

            embed = discord.Embed(
                title="Bread Market",
                color=config.MAINCOLOR,
                description=f"Use the `pan buy` and `pan sell` commands to exchange Breads.\n*These are the tradable breads for today*\n\nuse `pan shop <item>` to view a specific item\n\n**Guild Tax:** `{server_tax}`"
            )
            for i in display:
                item = market.ItemPrice(i['price'], i['volitility'], config.breads.index(i))
                yesterday = market.get_day_of_year_active() - 1
                if yesterday < 1: yesterday = 1

                yesterday_price = round(item.get_price(yesterday))
                today_price = round(item.get_price(market.get_day_of_year_active()))

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
            change = reset_time - datetime.datetime.now()

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
                if selected['bake_time'] is not None:
                    bake_time_string = f"Bake Time: **{selected['bake_time']} min.**"
                else:
                    bake_time_string = "This cannot be baked."

                embed = discord.Embed(
                    title="Bread info",
                    color=config.MAINCOLOR,
                    description=f"**{selected['name']}**\n```{selected['description']}```\n{bake_time_string}"
                )

                if selected['buyable'] or selected['sellable']:
                    item = market.ItemPrice(selected['price'], selected['volitility'], config.breads.index(selected))

                    prices = []
                    for _ in range(1, 61):
                        day = market.get_day_of_year_active() - _
                        if day < 1:
                            day += 365
                        prices.append(item.get_price(day))

                    fig, ax = plt.subplots(figsize=(8, 2),frameon=False)
                    #ax.axis('off')
                    fig.patch.set_visible(False)

                    x = np.array(list(range(1, 61)))
                    y = np.array(prices)

                    #define x as 200 equally spaced values between the min and max of original x
                    xnew = np.linspace(x.min(), x.max(), 125)

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
                    embed.set_image(url="attachment://tempgraph.png")
                    embed.description += f"\nCurrent Price: **{round(item.get_price(market.get_day_of_year_active()))}** <:BreadCoin:815842873937100800>"

                    random.seed(today)
                    display = random.sample(config.breads, k=9)
                    if selected not in display:
                        embed.description += "\n*Currently not for sale.*"

                    if not selected['buyable']:
                        embed.description += "\n\n**Can only be sold**"
                    elif not selected['sellable']:
                        embed.description += "\n\n**Can only be purchased**"    
                embed.set_thumbnail(url=selected['image'])

                await ctx.send(embed=embed, file=file)






def setup(bot):
    bot.add_cog(Market(bot))