import discord
import config
import datetime

from discord.ext import commands, tasks, menus

class Trading(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.active_trades = {}

    def create_trade_embed(self, trade):
        embed = discord.Embed(title=f"Trade ({trade['author']} - {trade['member']})", color=config.MAINCOLOR, description="**How to trade:**\n `pan offer <amount> <bread|id>` - offer bread\n `pan unoffer <amount> <bread|id>` - unoffer bread\n `pan offer|unoffer <amount> breadcoin` - offer BreadCoin\n `pan exit` - cancel trade\n\nReact with <a:check:824804284398698496> to accept the trade.")

        trader_breads = {}
        tradee_breads = {}
        for _ in trade.get('trader_offers', []):
            trader_breads[_['index']] = trader_breads.get(_['index'], 0) + 1
        for _ in trade.get('tradee_offers', []):
            tradee_breads[_['index']] = tradee_breads.get(_['index'], 0) + 1

        trader_offers_string = f"{trade['trader_coins']} <:BreadCoin:815842873937100800>\n"
        tradee_offers_string = f"{trade['tradee_coins']} <:BreadCoin:815842873937100800>\n"
        for index,amount in trader_breads.items():
            trader_offers_string += f"> `{amount}x` {config.breads[index]['emoji']} **{config.breads[index]['name']}**\n"
        for index,amount in tradee_breads.items():
            tradee_offers_string += f"> `{amount}x` {config.breads[index]['emoji']} **{config.breads[index]['name']}**\n"

        embed.add_field(name=f"{trade['author']} Offers", value=trader_offers_string, inline=True)
        embed.add_field(name=f"{trade['member']} Offers", value=tradee_offers_string, inline=True)

        return embed

    async def check_reactions(self, trade):
        users = None
        for _ in trade['message'].reactions:
            if str(_) == "<a:check:824804284398698496>":
                users = await _.users().flatten()
        
        if users is None:
            return False
        
        only_ids = list(x.id for x in users)
        return trade['member'].id in only_ids and trade['author'].id in only_ids

    async def countdown(self, trade):
        colors = {0: 0x32a852, 1: 0xcc2316}
        for _ in range(5, 5, -1):
            embed = self.create_trade_embed(trade)
            embed.color = colors[_ % 2]
            embed.set_author(name=f"Trade Completing in {_}...")
            try:
                await trade['message'].edit(embed=embed)
            except:
                del self.active_trades[trade['message'].id]
        if await self.check_reactions(trade):
            try:
                await self.complete_trade(trade)
            except:
                embed = discord.Embed(title="Trade Failed", color=config.ERRORCOLOR, description="An unknown error occured while completing the trade.")
                await trade['message'].edit(embed=embed)
            finally:
                del self.active_trades[trade['message'].id]
        else:
            embed = self.create_trade_embed(trade)
            embed.set_author(name=f"Trade Canceled")
            try:
                await trade['message'].edit(embed=embed)
            except:
                del self.active_trades[trade['message'].id]

    async def update_trade(self, trade):
        embed = self.create_trade_embed(trade)
        try:
            await trade['message'].edit(embed=embed)
        except:
            del self.active_trades[trade['message'].id]

    async def complete_trade(self, trade):
        trader = config.get_user(trade['author'].id)
        tradee = config.get_user(trade['member'].id)

        if (not all(list(x in trader['inventory'] for x in trade['trader_offers']))) or (not all(list(x in tradee['inventory'] for x in trade['tradee_offers']))) or (trade['trader_coins'] > trader['money']) or (trade['tradee_coins'] > tradee['money']):
            embed = discord.Embed(title="Trade Failed", color=config.ERRORCOLOR, description="Some or all items and BreadCoins offered by one or both parties were not found.")
            try:
                await trade['message'].edit(embed=embed)
            finally:
                del self.active_trades[trade['message'].id]
            return
        
        for _ in trade['trader_offers']:
            trader['inventory'].remove(_)
            tradee['inventory'].append(_)
        for _ in trade['tradee_offers']:
            trader['inventory'].append(_)
            tradee['inventory'].remove(_)
        trader['money'] += trade['tradee_coins']
        trader['money'] -= trade['trader_coins']

        tradee['money'] += trade['trader_coins']
        tradee['money'] -= trade['tradee_coins']

        if len(trader['inventory']) > trader.get('inventory_capacity', 25) or len(tradee['inventory']) > tradee.get('inventory_capacity', 25) or trader['money'] < 0 or tradee['money'] < 0:
            embed = discord.Embed(title="Trade Failed", color=config.ERRORCOLOR, description="One or both parties didn't have enough Storage Space or BreadCoin to complete the trade.")
            try:
                await trade['message'].edit(embed=embed)
            finally:
                del self.active_trades[trade['message'].id]
            return

        config.USERS.update_one({'id': trader['id']}, {'$set': {'inventory': trader['inventory'], 'money': trader['money']}})
        config.USERS.update_one({'id': tradee['id']}, {'$set': {'inventory': tradee['inventory'], 'money': tradee['money']}})

        embed = self.create_trade_embed(trade)
        embed.color = 0x22cc12
        embed.description="Trade Completed"
        try:
            await trade['message'].edit(embed=embed)
            await trade['message'].clear_reactions()
        except:
            pass

    def get_trade(self, id):
        trade = None
        for _ in self.active_trades.values():
            if _['trader']['id'] == id:
                trade = ('trader', _)
            elif _['tradee']['id'] == id:
                trade = ('tradee', _)
        return trade

    @commands.command(aliases=['cancel', 'quit'])
    async def exit(self, ctx):
        user = config.get_user(ctx.author.id)
        trade = self.get_trade(ctx.author.id)
        if trade is None:
            await ctx.send("<:melonpan:815857424996630548> `You are not trading with anyone. Start trading with 'pan trade <member>'`")
            return

        embed = discord.Embed(title="Trade Canceled", color=config.ERRORCOLOR, description="A party has exited the trade.")
        try:
            await trade['message'].edit(embed=embed)
        finally:
            del self.active_trades[trade['message'].id]

        m = await ctx.reply_safe("<:check2:824842637381992529> `Trade Canceled.`")
        await m.delete(delay=5)
        try:
            await ctx.message.delete()
        except:
            return
        return

    @commands.command(aliases=['o'])
    async def offer(self, ctx, amount:str=None, *, item:str=None):
        user = config.get_user(ctx.author.id)
        trade = self.get_trade(ctx.author.id)
        other = {'tradee': "trader", 'trader': "tradee"}
        other = other[trade[0]]
        if trade is None:
            await ctx.send("<:melonpan:815857424996630548> `You are not trading with anyone. Start trading with 'pan trade <member>'`")
            return

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
                if special in trade[1][trade[0] + "_offers"]:
                    m = await ctx.send("<:xx:824842660106731542> `This item is already being offered.`")
                    await m.delete(delay=5)
                    try:
                        await ctx.message.delete()
                    except:
                        return
                    return
                checking = config.get_user(trade[1][other]['id'])
                if len(checking['inventory']) + len(trade[1][trade[0] + "_offers"]) < checking.get('inventory_capacity', 25):
                    trade[1][trade[0] + "_offers"].append(special)
                    await self.update_trade(trade[1])
                    m = await ctx.send("<:check2:824842637381992529> `Offer placed.`")
                    await m.delete(delay=5)
                    try:
                        await ctx.message.delete()
                    except:
                        return
                    return
                else:
                    m = await ctx.send("<:xx:824842660106731542> `The other party would not have enough storage to hold this item.`")
                    await m.delete(delay=5)
                    try:
                        await ctx.message.delete()
                    except:
                        return
                    return

        if item is None:
            try:
                amount = abs(int(amount))
                await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to offer: e.g. 'pan offer 4 baguette'`")
                return
            except:
                item = amount
                amount = "1"

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
            if item.lower() in ['breadcoin', 'breadcoin', 'bread coins', 'breadcoins', 'coin', 'coins']:
                try:
                    amount = abs(int(amount))
                except:
                    await ctx.send("<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan offer 4 breadcoin'`")
                    return

                if amount + trade[1][trade[0] + "_coins"] > user['money']:
                    await ctx.send(f"<:xx:824842660106731542> `You only have {user['money']} BreadCoin.`")
                    return

                trade[1][trade[0] + "_coins"] += amount
                await self.update_trade(trade[1])
                m = await ctx.send("<:check2:824842637381992529> `BreadCoin offer placed.`")
                await m.delete(delay=5)
                try:
                    await ctx.message.delete()
                except:
                    return
                return
            else:
                await ctx.send("<:melonpan:815857424996630548> `That bread doesn't look like it exists...`")
        else:
            try:
                amount = abs(int(amount))
            except:
                await ctx.send("<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan offer 4 baguette'`")
                return

            offering = []
            sorted_list = []
            for _ in user['inventory']:
                if _.get('special', None) is None:
                    sorted_list.insert(0, _)
                else:
                    sorted_list.append(_)

            for their_item in sorted_list:
                if their_item['index'] == config.breads.index(selected):
                    offering.append(their_item)
                if len(offering) >= amount:
                    break
            if len(offering) < amount:
                await ctx.send(f"<:melonpan:815857424996630548> `It looks like you only have {len(offering)} of that bread in your bag.`")
            else:
                final_offering = []
                for _ in offering:
                    if _ not in trade[1][trade[0] + "_offers"]:
                        final_offering.append(_)

                checking = config.get_user(trade[1][other]['id'])
                if len(checking['inventory']) + len(final_offering) <= checking.get('inventory_capacity', 25):
                    trade[1][trade[0] + "_offers"].extend(final_offering)
                    await self.update_trade(trade[1])
                    m = await ctx.send("<:check2:824842637381992529> `Offer placed.`")
                    await m.delete(delay=5)
                    try:
                        await ctx.message.delete()
                    except:
                        return
                    return
                else:
                    m = await ctx.send("<:xx:824842660106731542> `The other party would not have enough storage to hold these items.`")
                    await m.delete(delay=5)
                    try:
                        await ctx.message.delete()
                    except:
                        return
                    return

    @commands.command(aliases=['uo', 'u'])
    async def unoffer(self, ctx, amount:str=None, *, item:str=None):
        user = config.get_user(ctx.author.id)
        trade = self.get_trade(ctx.author.id)
        other = {'tradee': "trader", 'trader': "tradee"}
        other = other[trade[0]]
        if trade is None:
            await ctx.send("<:melonpan:815857424996630548> `You are not trading with anyone. Start trading with 'pan trade <member>'`")
            return

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
                if special not in trade[1][trade[0] + "_offers"]:
                    m = await ctx.send("<:xx:824842660106731542> `This item is not being offered.`")
                    await m.delete(delay=5)
                    try:
                        await ctx.message.delete()
                    except:
                        return
                    return
                
                trade[1][trade[0] + "_offers"].remove(special)
                await self.update_trade(trade[1])
                m = await ctx.send("<:check2:824842637381992529> `Offer removed.`")
                await m.delete(delay=5)
                try:
                    await ctx.message.delete()
                except:
                    return
                return

        if item is None:
            try:
                amount = abs(int(amount))
                await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to stop offering: e.g. 'pan unoffer 4 baguette'`")
                return
            except:
                item = amount
                amount = "1"

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
            if item.lower() in ['breadcoin', 'breadcoin', 'bread coins', 'breadcoins', 'coin', 'coins']:
                try:
                    amount = abs(int(amount))
                except:
                    await ctx.send("<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan offer 4 breadcoin'`")
                    return

                trade[1][trade[0] + "_coins"] -= amount
                if trade[1][trade[0] + "_coins"] < 0:
                    trade[1][trade[0] + "_coins"] = 0
                await self.update_trade(trade[1])
                m = await ctx.send("<:check2:824842637381992529> `BreadCoin offer removed.`")
                await m.delete(delay=5)
                try:
                    await ctx.message.delete()
                except:
                    return
                return
            else:
                await ctx.send("<:melonpan:815857424996630548> `That bread doesn't look like it exists...`")
        else:
            try:
                amount = abs(int(amount))
            except:
                await ctx.send("<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan unoffer 4 baguette'`")
                return

            unoffering = []
            sorted_list = []
            for _ in trade[1][trade[0] + "_offers"]:
                if _.get('special', None) is None:
                    sorted_list.insert(0, _)
                else:
                    sorted_list.append(_)

            for their_item in sorted_list:
                if their_item['index'] == config.breads.index(selected):
                    unoffering.append(their_item)
                if len(unoffering) >= amount:
                    break
            if len(unoffering) < amount:
                await ctx.send(f"<:melonpan:815857424996630548> `You are only offering {len(unoffering)} of that item.`")
            else:
                for _ in unoffering:
                    trade[1][trade[0] + "_offers"].remove(_)
                await self.update_trade(trade[1])
                m = await ctx.send("<:check2:824842637381992529> `Offers removed.`")
                await m.delete(delay=5)
                try:
                    await ctx.message.delete()
                except:
                    return
                return

    @commands.command(aliases=['give'])
    async def trade(self, ctx, member:discord.Member=None):
        if member is None or member == ctx.author:
            await ctx.send("<:melonpan:815857424996630548> `You must mention someone to trade bread with!`")
            return

        if self.get_trade(ctx.author.id) is not None:
            await ctx.send("<:melonpan:815857424996630548> `You are already trading somewhere else!`")
            return

        trader = config.get_user(ctx.author.id)
        tradee = config.get_user(member.id)

        trader_offers = []
        tradee_offers = []
        trader_coins = 0
        tradee_coins = 0

        trade_obj = {
            "trader": trader,
            "tradee": tradee,
            "author": ctx.author,
            "member": member,
            "trader_offers": trader_offers,
            "trader_coins": trader_coins,
            "tradee_offers": tradee_offers,
            "tradee_coins": tradee_coins,
            "channel": ctx.channel
        }

        embed = self.create_trade_embed(trade_obj)
        msg = await ctx.send(embed=embed)
        trade_obj['message'] = msg

        self.active_trades[msg.id] = trade_obj

        await msg.add_reaction("<a:check:824804284398698496>")

        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) == "<a:check:824804284398698496>":
            trade_obj = self.active_trades.get(payload.message_id, None)
            if trade_obj is None:
                return
            
            if await self.check_reactions(trade_obj):
                await self.countdown(trade_obj)
            

def setup(bot):
    bot.add_cog(Trading(bot))