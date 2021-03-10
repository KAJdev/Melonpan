import ast
import discord
import config
import traceback
import datetime
import random
import asyncio
import market

from discord.ext import commands, tasks, menus

class BakeryMenu(menus.ListPageSource):
    def __init__(self, data, total, baking, user):
        super().__init__(data, per_page=9)
        self.total = total
        self.baking = baking
        self.free = total - baking
        self.user = user

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        embed = discord.Embed(title="Your Bakery", color=config.MAINCOLOR, description = f"{config.stove_burning[False]} `{self.total}` Total Ovens\n{config.stove_burning[True]} `{self.baking}` Baking Ovens\n{config.stove_burning[False]} `{self.free}` Free Ovens")
        for i, v in enumerate(entries, start=offset):
            try:
                current = self.user['ovens'][i]
            except IndexError:
                current = None

            if current is None:
                embed.add_field(name=f"{config.stove_burning[False]}", value=f"Oven is empty.\n-")
            else:
                s = (current['done'] - datetime.datetime.utcnow()).total_seconds()
                if 'burn' in current.keys():
                    b = (current['burn'] - datetime.datetime.utcnow()).total_seconds()
                else:
                    b = 1
                if s > 0 and b > 0:
                    hours, remainder = divmod(s, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    embed.add_field(name=f"{config.stove_burning[True]}", value=f"**{current['name']}**\n{round(hours)}h {round(minutes)}m {round(seconds)}s")
                elif s <= 0 and b > 0:
                    embed.add_field(name=f"{config.stove_burning[True]}", value=f"**{current['name']}**\nplate with `pan plate`.")
                elif s <= 0 and b <= 0:
                    embed.add_field(name=f"{config.stove_burning[False]} <:BreadWarning:815842874226245643> `BURNED`", value=f"**{current['name']}**\nplate with `pan plate`.")
        embed.add_field(name=f"<:BreadStaff:815484321590804491>", value=f"`pan build`\nCost: `{self.user['oven_count'] * config.oven_cost}` <:BreadCoin:815842873937100800>", inline=False)
        embed.set_footer(text=f"Showing {menu.current_page + 1}/{menu._source.get_max_pages()}\n\npan bake <bread> | pan plate")
        return embed

class Bakery(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def bakery(self, ctx):
        user = config.get_user(ctx.author.id)

        baking = len(user['ovens'])
        for o in user['ovens']:
            if o is None:
                baking -= 1

        for _ in range(user.get('oven_count', 2)):
            try:
                x = user['ovens'][_]
            except IndexError:
                user['ovens'].append(None)

        pages = menus.MenuPages(source=BakeryMenu(user['ovens'], user['oven_count'], baking, user), clear_reactions_after=True)
        await pages.start(ctx)

    @commands.command()
    async def build(self, ctx):
        user = config.get_user(ctx.author.id)

        # if user['oven_count'] >= 24:
        #     await ctx.reply_safe("<:melonpan:815857424996630548> `You have built the maximum amount of ovens!`")
        #     return

        cost = user['oven_count'] * config.oven_cost

        if user['money'] < cost:
            await ctx.reply_safe("<:melonpan:815857424996630548> `You don't have enough BreadCoin to build a new oven.`")
            return
        
        config.USERS.update_one({'id': user['id']}, {'$inc': {'money': -cost, 'oven_count': 1}})
        await ctx.reply_safe("<:melonpan:815857424996630548> You have built a new oven! View it with `pan bakery`.")

    @commands.command()
    async def expand(self, ctx):
        user = config.get_user(ctx.author.id)

        # if user.get('inventory_capacity', 25) >= 100:
        #     await ctx.reply_safe("<:melonpan:815857424996630548> `You have expanded your storage capacity to the max!`")
        #     return

        cost = int((user.get('inventory_capacity', 25)/config.expand_amount) * config.expand_cost)

        if user['money'] < cost:
            await ctx.reply_safe("<:melonpan:815857424996630548> `You don't have enough BreadCoin to expand your storage capacity.`")
            return

        if 'inventory_capacity' in user.keys():
            config.USERS.update_one({'id': user['id']}, {'$inc': {'money': -cost, 'inventory_capacity': config.expand_amount}})
        else:
            config.USERS.update_one({'id': user['id']}, {'$inc': {'money': -cost}, '$set': {'inventory_capacity': 25 + config.expand_amount}})
        await ctx.reply_safe(f"<:melonpan:815857424996630548> You have expanded your inventory capacity by `{config.expand_amount}` slots. You can now store `{user.get('inventory_capacity', 25) + config.expand_amount}` items.")

    @commands.command(aliases=['ba'])
    async def bakeall(self, ctx, *, bread:str=None):
        user = config.get_user(ctx.author.id)

        active = 0
        for o in user['ovens']:
            if o is not None:
                active += 1
        if active >= user['oven_count']:
            await ctx.send("<:melonpan:815857424996630548> `You have bread in all of your ovens already!`")
            return

        if bread is None:
            await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to bake: e.g. 'pan bakeall baguette'`")
            return
        
        selected = None
        for r in config.breads:
            if bread.lower() in r['name'].lower():
                selected = r
                break
            try:
                index = int(bread)
                if index == config.breads.index(r):
                    selected = r
                    break
            except:
                pass
        if selected is None:
            await ctx.send("<:melonpan:815857424996630548> `That bread doesn't look like it exists...`")
        elif not selected['bakeable']:
            await ctx.send("<:melonpan:815857424996630548> `You can't bake this.`")
        else:
            bake_obj = {
                'name': selected['name'],
                'index': config.breads.index(selected),
                'done': datetime.datetime.utcnow() + datetime.timedelta(minutes=selected['bake_time']),
                'burn': datetime.datetime.utcnow() + datetime.timedelta(minutes=selected['bake_time'] * config.burn_time_multipier)
            }
            amount = 0
            for _ in range(user['oven_count']):
                try:
                    if user['ovens'][_] is None:
                        user['ovens'][_] = bake_obj
                        amount += 1
                except IndexError:
                    user['ovens'].append(bake_obj)
                    amount += 1
            
            user['baked'][str(bake_obj['index'])] = user['baked'].get(str(bake_obj['index']), 0) + amount

            config.USERS.update_one({'id': user['id']}, {'$set': {'ovens': user['ovens'], 'baked': user['baked']}})
            await ctx.reply_safe(f"{config.stove_burning[True]} {amount} **{bake_obj['name']}s** are now baking! use `pan bakery` to check on them, and `pan plate` to take them out when they are done.")


    @commands.command()
    async def bake(self, ctx, *, bread:str=None):
        user = config.get_user(ctx.author.id)

        active = 0
        for o in user['ovens']:
            if o is not None:
                active += 1
        if active >= user['oven_count']:
            await ctx.send("<:melonpan:815857424996630548> `You have bread in all of your ovens already!`")
            return

        if bread is None:
            await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to bake: e.g. 'pan bake baguette'`")
            return
        
        selected = None
        for r in config.breads:
            if bread.lower() in r['name'].lower():
                selected = r
                break
            try:
                index = int(bread)
                if index == config.breads.index(r):
                    selected = r
                    break
            except:
                pass
        if selected is None:
            await ctx.send("<:melonpan:815857424996630548> `That bread doesn't look like it exists...`")
        elif not selected['bakeable']:
            await ctx.send("<:melonpan:815857424996630548> `You can't bake this.`")
        else:
            bake_obj = {
                'name': selected['name'],
                'index': config.breads.index(selected),
                'done': datetime.datetime.utcnow() + datetime.timedelta(minutes=selected['bake_time']),
                'burn': datetime.datetime.utcnow() + datetime.timedelta(minutes=selected['bake_time'] * config.burn_time_multipier)
            }
            entered = False
            for o in user['ovens']:
                if o is None:
                    user['ovens'][user['ovens'].index(o)] = bake_obj
                    entered = True
                    break
            if not entered:
                user['ovens'].append(bake_obj)

            user['baked'][str(bake_obj['index'])] = user['baked'].get(str(bake_obj['index']), 0) + 1
            
            config.USERS.update_one({'id': user['id']}, {'$set': {'ovens': user['ovens']}})
            await ctx.reply_safe(f"{config.stove_burning[True]} Your **{bake_obj['name']}** is now baking! use `pan bakery` to check on it, and `pan plate` to take it out when it's done.")

    @commands.command(aliases=['p'])
    async def plate(self, ctx):
        user = config.get_user(ctx.author.id)

        ending = ""
        cutoff = False

        for o in user['ovens']:
            if o is not None:
                s = (o['done'] - datetime.datetime.utcnow()).total_seconds()
                if 'burn' in o.keys():
                    b = (o['burn'] - datetime.datetime.utcnow()).total_seconds()
                else:
                    b = 1
                if s <= 0 and b > 0:
                    if len(user['inventory']) >= user.get('inventory_capacity', 25):
                        cutoff = True
                        break
                    new_bread = config.create_bread(config.breads[o['index']])
                    user['inventory'].append(new_bread)
                    ending += f"+ `{config.quality_levels[new_bread['quality']]}` **{o['name']}**\n"
                    user['ovens'][user['ovens'].index(o)] = None
                elif s <= 0 and b <= 0:
                    if len(user['inventory']) >= user.get('inventory_capacity', 25):
                        cutoff = True
                        break
                    new_bread = config.create_bread(config.breads[12])
                    user['inventory'].append(new_bread)
                    ending += f"+ `{config.quality_levels[new_bread['quality']]}` **Burned {o['name']}** (Charcoal)\n"
                    user['ovens'][user['ovens'].index(o)] = None

        
        config.USERS.update_one({'id': user['id']}, {'$set': {'inventory': user['inventory'], 'ovens': user['ovens']}})

        if ending == "":
            ending = "No bread was plated."
        
        embed = discord.Embed(color=config.MAINCOLOR, title="Plated Bread", description=ending)
        if cutoff:
            embed.description += "\n*Some ovens were not emptied because your bread storage is full. Please sell some bread.*"
        await ctx.reply_safe(embed=embed)
        



            


def setup(bot):
    bot.add_cog(Bakery(bot))