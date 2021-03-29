import discord
import config
import datetime
import asyncio

from discord.ext import commands, tasks, menus
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

class Trading(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.active_trades = {}

    def create_trade_embed(self, trade):
        embed = discord.Embed(title=f"Trade ({trade['author']} - {trade['member']})", color=config.MAINCOLOR, description="**How to trade:**\n `pan offer <amount> <bread|id>` - offer bread\n `pan unoffer <amount> <bread|id>` - unoffer bread\n `pan offer|unoffer <amount> breadcoin` - offer BreadCoin\n\nReact with <a:check:824804284398698496> to accept the trade.\nReact with <:xx:824842660106731542> to exit the trade.")

        trader_breads = {}
        tradee_breads = {}

        trader_special = []
        tradee_special = []
        for _ in trade.get('trader_offers', []):
            if _.get("special", None) is None:
                trader_breads[_['index']] = trader_breads.get(_['index'], 0) + 1
            else:
                trader_special.append(_)
        for _ in trade.get('tradee_offers', []):
            if _.get("special", None) is None:
                tradee_breads[_['index']] = tradee_breads.get(_['index'], 0) + 1
            else:
                tradee_special.append(_)

        trader_offers_string = f"{trade['trader_coins']} <:BreadCoin:815842873937100800>\n"
        tradee_offers_string = f"{trade['tradee_coins']} <:BreadCoin:815842873937100800>\n"
        for index,amount in trader_breads.items():
            trader_offers_string += f"> `{amount}x` {config.breads[index]['emoji']} **{config.breads[index]['name']}**\n"
        for index,amount in tradee_breads.items():
            tradee_offers_string += f"> `{amount}x` {config.breads[index]['emoji']} **{config.breads[index]['name']}**\n"

        for s in trader_special:
            trader_offers_string += f"> {config.breads[s['index']]['emoji']} **{config.breads[s['index']]['name']}** `{s['special']}`\n"
        for s in tradee_special:
            tradee_offers_string += f"> {config.breads[s['index']]['emoji']} **{config.breads[s['index']]['name']}** `{s['special']}`\n"

        embed.add_field(name=f"{trade['author'].name}'s Offers", value=trader_offers_string, inline=True)
        embed.add_field(name=f"{trade['member'].name}'s Offers", value=tradee_offers_string, inline=True)

        return embed

    async def check_reactions(self, trade):
        trade['message'] = await trade['channel'].fetch_message(trade['message'].id)
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
        for _ in range(5, 0, -1):
            embed = self.create_trade_embed(trade)
            embed.color = colors[_ % 2]
            embed.set_author(name=f"Trade Completing in {_}...")
            try:
                await trade['message'].edit(embed=embed)
            except:
                del self.active_trades[trade['message'].id]
                print("aborting")
            await asyncio.sleep(1)
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
    
    
    async def offer_command(self, ctx, amount, item):
        user = config.get_user(ctx.author.id)
        trade = self.get_trade(ctx.author.id)
        if trade is None:
            return "<:melonpan:815857424996630548> `You are not trading with anyone. Start trading with 'pan trade <member>'`"
        other = {'tradee': "trader", 'trader': "tradee"}
        other = other[trade[0]]

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
                    return "<:xx:824842660106731542> `This item is already being offered.`"
                    
                checking = config.get_user(trade[1][other]['id'])
                if len(checking['inventory']) + len(trade[1][trade[0] + "_offers"]) < checking.get('inventory_capacity', 25):
                    trade[1][trade[0] + "_offers"].append(special)
                    await self.update_trade(trade[1])
                    return "<:check2:824842637381992529> `Offer placed.`"
                else:
                    return "<:xx:824842660106731542> `The other party would not have enough storage to hold this item.`"

        if item is None:
            try:
                amount = abs(int(amount))
                return "<:melonpan:815857424996630548> `You must tell me an item you wish to offer: e.g. 'pan offer 4 baguette'`"
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
                    return "<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan offer 4 breadcoin'`"

                if amount + trade[1][trade[0] + "_coins"] > user['money']:
                    return f"<:xx:824842660106731542> `You only have {user['money']} BreadCoin.`"

                trade[1][trade[0] + "_coins"] += amount
                await self.update_trade(trade[1])
                return "<:check2:824842637381992529> `BreadCoin offer placed.`"
            else:
                return "<:melonpan:815857424996630548> `That bread doesn't look like it exists...`"
        else:
            try:
                amount = abs(int(amount))
            except:
                return "<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan offer 4 baguette'`"

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
                return f"<:melonpan:815857424996630548> `It looks like you only have {len(offering)} of that bread in your bag.`"
            else:
                final_offering = []
                for _ in offering:
                    if _ not in trade[1][trade[0] + "_offers"]:
                        final_offering.append(_)

                checking = config.get_user(trade[1][other]['id'])
                if len(checking['inventory']) + len(final_offering) <= checking.get('inventory_capacity', 25):
                    trade[1][trade[0] + "_offers"].extend(final_offering)
                    await self.update_trade(trade[1])
                    return "<:check2:824842637381992529> `Offer placed.`"
                else:
                    return "<:xx:824842660106731542> `The other party would not have enough storage to hold these items.`"
                                  
    async def unoffer_command(self, ctx, amount, item):
        user = config.get_user(ctx.author.id)
        trade = self.get_trade(ctx.author.id)
        if trade is None:
            return "<:melonpan:815857424996630548> `You are not trading with anyone. Start trading with 'pan trade <member>'`"
        other = {'tradee': "trader", 'trader': "tradee"}
        other = other[trade[0]]

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
                    return "<:xx:824842660106731542> `This item is not being offered.`"

                trade[1][trade[0] + "_offers"].remove(special)
                await self.update_trade(trade[1])
                return "<:check2:824842637381992529> `Offer removed.`"

        if item is None:
            try:
                amount = abs(int(amount))
                return "<:melonpan:815857424996630548> `You must tell me an item you wish to stop offering: e.g. 'pan unoffer 4 baguette'`"
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
                    return "<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan offer 4 breadcoin'`"

                trade[1][trade[0] + "_coins"] -= amount
                if trade[1][trade[0] + "_coins"] < 0:
                    trade[1][trade[0] + "_coins"] = 0
                await self.update_trade(trade[1])
                return "<:check2:824842637381992529> `BreadCoin offer removed.`"
            else:
                return "<:melonpan:815857424996630548> `That bread doesn't look like it exists...`"
        else:
            try:
                amount = abs(int(amount))
            except:
                return "<:melonpan:815857424996630548> `Amount must be a number: e.g. 'pan unoffer 4 baguette'`"

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
                return f"<:melonpan:815857424996630548> `You are only offering {len(unoffering)} of that item.`"
            else:
                for _ in unoffering:
                    trade[1][trade[0] + "_offers"].remove(_)
                await self.update_trade(trade[1])
                return "<:check2:824842637381992529> `Offers removed.`"      
                                   
    async def trade_command(self, ctx, member):
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
        await msg.add_reaction("<:xx:824842660106731542>")                           
                        
    @commands.command(aliases=['o'])
    async def offer(self, ctx, amount:str=None, *, item:str=None):
        e = await self.offer_command(ctx, amount, item)
        m = await ctx.send(e)
        await m.delete(delay=5)
        try:
            await ctx.message.delete()
        except:
            return

    @commands.command(aliases=['uo', 'u'])
    async def unoffer(self, ctx, amount:str=None, *, item:str=None):
        e = await self.unoffer_command(ctx, amount, item)
        m = await ctx.send(e)
        await m.delete(delay=5)
        try:
            await ctx.message.delete()
        except:
            return

    @commands.command(aliases=['give'])
    async def trade(self, ctx, member:discord.Member=None):
        await self.trade_command(ctx, member)
                                   
                                   
    @cog_ext.cog_slash(name="trade",
        description="Trade with another baker.",
        options=[
            create_option(
                name="member",
                description="The member to trade with.",
                option_type=6,
                required=True
            )
        ])
    async def trade_slash(self, ctx: SlashContext, member:discord.User):
        await self.trade_command(ctx, member)   
                                   
    @cog_ext.cog_slash(name="offer",
        description="Offer an item while in a trade.",
        options=[
            create_option(
                name="item",
                description="Choose an item to offer",
                option_type=3,
                required= True,
                choices = [create_choice(name="Bread Coin", value="breadcoin")] + config.bread_choices
            ),
            create_option(
                name="amount",
                description="How much?",
                option_type=4,
                required=False
            )
        ])
    async def offer_slash(self, ctx: SlashContext, item:str, amount:int=1):
        e = await self.offer_command(ctx, str(amount), item)
        await ctx.send(e, hidden=True)
                                   
                                   
    @cog_ext.cog_slash(name="unoffer",
        description="Remove an offer from a trade.",
        options=[
            create_option(
                name="item",
                description="Choose an item to remove",
                option_type=3,
                required= True,
                choices = [create_choice(name="Bread Coin", value="breadcoin")] + config.bread_choices
            ),
            create_option(
                name="amount",
                description="How much?",
                option_type=4,
                required=False
            )
        ])
    async def unoffer_slash(self, ctx: SlashContext, item:str, amount:int=1):
        e = await self.unoffer_command(ctx, str(amount), item)
        await ctx.send(e, hidden=True)                                  

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) == "<a:check:824804284398698496>":
            trade_obj = self.active_trades.get(payload.message_id, None)
            if trade_obj is None:
                return

            if await self.check_reactions(trade_obj):
                await self.countdown(trade_obj)
        if str(payload.emoji) == "<:xx:824842660106731542>":
            trade_obj = self.active_trades.get(payload.message_id, None)
            if trade_obj is None:
                return
            if payload.user_id not in [trade_obj['author'].id, trade_obj['member'].id]:
                return

            embed = discord.Embed(title="Trade Canceled", color=config.ERRORCOLOR, description="A party has exited the trade.")
            try:
                await trade_obj['message'].edit(embed=embed)
                await trade_obj['message'].clear_reactions()
            finally:
                del self.active_trades[trade_obj['message'].id]


def setup(bot):
    bot.add_cog(Trading(bot))
