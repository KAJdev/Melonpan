import ast
import discord
import config
import traceback
import datetime
import random
import asyncio
import market

from discord.ext import commands, tasks, menus
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

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
        embed.set_footer(text=f"pan bake <bread> | pan plate\n\nShowing {menu.current_page + 1}/{menu._source.get_max_pages()}")
        return embed

class CustomMenuManager(menus.MenuPages):
    async def send_initial_message(self, ctx, channel):
        """|coro|
        The default implementation of :meth:`Menu.send_initial_message`
        for the interactive pagination session.
        This implementation shows the first page of the source.
        """
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        return await config.reply(ctx, **kwargs)

class Bakery(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def bakery_command(self, ctx):
        user = self.bot.mongo.get_user(ctx.author.id)

        baking = len(user['ovens'])
        for o in user['ovens']:
            if o is None:
                baking -= 1

        for _ in range(user.get('oven_count', 2)):
            try:
                x = user['ovens'][_]
            except IndexError:
                user['ovens'].append(None)

        menuClass = BakeryMenu(user['ovens'], user['oven_count'], baking, user)
        pages = CustomMenuManager(source=menuClass, clear_reactions_after=True)
        await pages.start(ctx)

    async def build_command(self, ctx):
        user = self.bot.mongo.get_user(ctx.author.id)

        # if user['oven_count'] >= 24:
        #     await config.reply(ctx, "<:melonpan:815857424996630548> `You have built the maximum amount of ovens!`")
        #     return

        cost = user['oven_count'] * config.oven_cost

        if user['money'] < cost:
            await config.reply(ctx, "<:melonpan:815857424996630548> `You don't have enough BreadCoin to build a new oven.`")
            return

        self.bot.mongo.update_user(user, {'$inc': {'money': -cost, 'oven_count': 1}})
        await config.reply(ctx, "<:melonpan:815857424996630548> You have built a new oven! View it with `pan bakery`.")

    async def expand_command(self, ctx):
        user = self.bot.mongo.get_user(ctx.author.id)

        # if user.get('inventory_capacity', 25) >= 100:
        #     await config.reply(ctx, "<:melonpan:815857424996630548> `You have expanded your storage capacity to the max!`")
        #     return

        cost = int((user.get('inventory_capacity', 25)/config.expand_amount) * config.expand_cost)

        if user['money'] < cost:
            await config.reply(ctx, "<:melonpan:815857424996630548> `You don't have enough BreadCoin to expand your storage capacity.`")
            return

        if 'inventory_capacity' in user.keys():
            self.bot.mongo.update_user(user, {'$inc': {'money': -cost, 'inventory_capacity': config.expand_amount}})
        else:
            self.bot.mongo.update_user(user, {'$inc': {'money': -cost}, '$set': {'inventory_capacity': 25 + config.expand_amount}})
        await config.reply(ctx, f"<:melonpan:815857424996630548> You have expanded your inventory capacity by `{config.expand_amount}` slots. You can now store `{user.get('inventory_capacity', 25) + config.expand_amount}` items.")

    async def bakeall_command(self, ctx, bread):
        user = self.bot.mongo.get_user(ctx.author.id)

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

            self.bot.mongo.update_user(user, {'$set': {'ovens': user['ovens'], 'baked': user['baked']}})
            await config.reply(ctx, f"{config.stove_burning[True]} {amount} **{selected.get('plural_name', selected['name']) if amount > 1 else selected['name']}** {'are' if amount > 1 else 'is'} now baking! use `pan bakery` to check on {'them' if amount > 1 else 'it'}, and `pan plate` to take {'them' if amount > 1 else 'it'} out when {'they are' if amount > 1 else 'it is'} done.")

    async def bake_command(self, ctx, bread):
        # get user from DB/cache
        user = self.bot.mongo.get_user(ctx.author.id)

        active = 0
        # count ovens with bread in them
        for o in user['ovens']:
            if o is not None:
                active += 1
        
        # stop the command if there are no open ovens
        if active >= user['oven_count']:
            await ctx.send("<:melonpan:815857424996630548> `You have bread in all of your ovens already!`")
            return

        if bread is None:
            await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to bake: e.g. 'pan bake baguette'`")
            return

        # try to parse an integer at the end of the string. a.k.a `pan bake bread 5`
        try:
            # get the end
            parsed = bread.split(" ")[-1]

            # try to int parse
            amount = int(parsed)

            # remove amount from bread string
            bread = bread[:len(bread) - (len(parsed) + 2)]
        except (IndexError, ValueError):
            amount = 1

        # make sure it's under the current open oven count
        if amount > user['oven_count'] - active:
            amount = user['oven_count'] - active

        # find the actual bread object from config
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
            # insert each bread with UUID into user obj
            bake_obj = {
                'name': selected['name'],
                'index': config.breads.index(selected),
                'done': datetime.datetime.utcnow() + datetime.timedelta(minutes=selected['bake_time']),
                'burn': datetime.datetime.utcnow() + datetime.timedelta(minutes=selected['bake_time'] * config.burn_time_multipier)
            }
            entered = amount
            for o in user['ovens']:
                if o is None:
                    user['ovens'][user['ovens'].index(o)] = bake_obj
                    entered -= 1
                    if entered == 0: break
            if entered > 0:
                for _ in range(entered):
                    user['ovens'].append(bake_obj)

            # count stats
            user['baked'][str(bake_obj['index'])] = user['baked'].get(str(bake_obj['index']), 0) + amount

            # save data
            self.bot.mongo.update_user(user, {'$set': {'ovens': user['ovens']}})
            extra = ""
            if config.get_avg_commands(minutes=0.2, user=ctx.author.id, command=str(ctx.command)) >= 0.6:
                extra = "\n\n**TIP:** Use `pan bakeall <bread>` to fill all of your empty ovens!"
            await config.reply(ctx, f"{config.stove_burning[True]} {amount} **{selected.get('plural_name', selected['name']) if amount > 1 else selected['name']}** {'are' if amount > 1 else 'is'} now baking! use `pan bakery` to check on {'them' if amount > 1 else 'it'}, and `pan plate` to take {'them' if amount > 1 else 'it'} out when {'they are' if amount > 1 else 'it is'} done.")

    async def plate_command(self, ctx):
        user = self.bot.mongo.get_user(ctx.author.id)

        ending = ""
        cutoff = False
        to_add = []

        regular = {}
        special = []
        special_burned = []
        burned = {}

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
                    if 'special' in new_bread.keys():
                        special.append(new_bread)
                    else:
                        regular[o['index']] = regular.get(o['index'], 0) + 1
                    user['inventory'].append(new_bread)
                    to_add.append(new_bread)
                    user['ovens'][user['ovens'].index(o)] = None
                elif s <= 0 and b <= 0:
                    if len(user['inventory']) >= user.get('inventory_capacity', 25):
                        cutoff = True
                        break
                    new_bread = config.create_bread(config.breads[12])
                    if 'special' in new_bread.keys():
                        special_burned.append(new_bread)
                    else:
                        burned[o['index']] = burned.get(o['index'], 0) + 1
                    user['inventory'].append(new_bread)
                    to_add.append(new_bread)
                    user['ovens'][user['ovens'].index(o)] = None

        for index, amount in regular.items():
            ending += f"+ `{amount}x` {config.breads[index]['emoji']} **{config.breads[index]['name']}**\n"
        for index, amount in burned.items():
            ending += f"+ `{amount}x` {config.breads[12]['emoji']} **Burned {config.breads[index]['name']}** (Charcoal)\n"
        for b in special:
            special_string = b.get('special', None)
            if special_string is not None:
                special_string = f" `{special_string}`"
            else:
                special_string = ""
            ending += f"+ {config.breads[b['index']]['emoji']} **{config.breads[b['index']]['name']}**{special_string}\n"
        for b in special_burned:
            special_string = b.get('special', None)
            if special_string is not None:
                special_string = f" `{special_string}`"
            else:
                special_string = ""
            ending += f"+ {config.breads[12]['emoji']} **Burned {config.breads[b['index']]['name']}** (Charcoal){special_string}\n"

        self.bot.mongo.update_user(user, {'$set': {'inventory': user['inventory'], 'ovens': user['ovens']}})

        if ending == "":
            ending = "No bread was plated."

        embed = discord.Embed(color=config.MAINCOLOR, title="Plated Bread", description=ending)
        if cutoff:
            embed.description += "\n*Some ovens were not emptied because your bread storage is full. Please sell some bread.*"

        if not ending == "No bread was plated.":
            embed.set_footer(text="react with 💲 to sell these breads")

        msg = await config.reply(ctx, embed=embed)
        if not ending == "No bread was plated.":
            config.SELL_BREAD_CACHE.append((msg, user, to_add))
            await msg.add_reaction("💲")

    @cog_ext.cog_slash(name="bakery",
        description="Show your bakery.")
    async def bakery_slash(self, ctx: SlashContext):
        await self.bakery_command(ctx)

    @cog_ext.cog_slash(name="build",
        description="Build a new oven.")
    async def build_slash(self, ctx: SlashContext):
        await self.build_command(ctx)

    @cog_ext.cog_slash(name="expand",
        description="Expand your inventory space.")
    async def expand_slash(self, ctx: SlashContext):
        await self.expand_command(ctx)

    @cog_ext.cog_slash(name="bake",
        description="Bake some bread!",
        options=[
            create_option(
              name="bread",
              description="The bread to bake.",
              option_type=3,
              required=True,
              choices = config.bread_choices
            ),
            create_option(
                name="amount",
                description="The amount of bread to bake.",
                option_type=4,
                required=False
            )
        ])
    async def bake_slash(self, ctx: SlashContext, bread:str, amount:int=1):
        await self.bake_command(ctx, bread + " " + str(amount))

    @cog_ext.cog_slash(name="bakeall", description="Bake all the bread!",
        options=[
            create_option(
              name="bread",
              description="The bread to bake.",
              option_type=3,
              required=True,
              choices = config.bread_choices
            )
        ])
    async def bakeall_slash(self, ctx: SlashContext, bread:str):
        await self.bakeall_command(ctx, bread)

    @cog_ext.cog_slash(name="plate",
        description="Take bread out of the oven.")
    async def plate_slash(self, ctx: SlashContext):
        await self.plate_command(ctx)

    @commands.command()
    async def bakery(self, ctx):
        await self.bakery_command(ctx)

    @commands.command()
    async def build(self, ctx):
        await self.build_command(ctx)

    @commands.command()
    async def expand(self, ctx):
        await self.expand_command(ctx)

    @commands.command(aliases=['ba'])
    async def bakeall(self, ctx, *, bread:str=None):
        await self.bakeall_command(ctx, bread)

    @commands.command()
    async def bake(self, ctx, *, bread:str=None):
        await self.bake_command(ctx, bread)

    @commands.command(aliases=['p'])
    async def plate(self, ctx):
        await self.plate_command(ctx)



def setup(bot):
    bot.add_cog(Bakery(bot))
