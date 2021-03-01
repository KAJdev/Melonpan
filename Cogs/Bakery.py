import ast
import discord
import config
import traceback
import datetime
import random
import asyncio
import market

from discord.ext import commands, tasks

class Bakery(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def bakery(self, ctx):
        user = config.get_user(ctx.author.id)

        embed = discord.Embed(title="Your Bakery", color=config.MAINCOLOR, description = f"{config.stove_burning[False]} `{user['oven_count']}` Total Ovens\n{config.stove_burning[True]} `{len(user['ovens'])}` Baking Ovens\n{config.stove_burning[False]} `{user['oven_count'] - len(user['ovens'])}` Free Ovens")

        for _ in range(user['oven_count']):
            try:
                current = user['ovens'][_]
            except IndexError:
                current = None

            if current is None:
                embed.add_field(name=f"{config.stove_burning[False]}", value=f"Oven is empty.\n-")
            else:
                s = (current['done'] - datetime.datetime.utcnow()).total_seconds()
                if s > 0:
                    hours, remainder = divmod(s, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    embed.add_field(name=f"{config.stove_burning[True]}", value=f"**{current['name']}**\n{round(hours)}h {round(minutes)}m {round(seconds)}s")
                else:
                    embed.add_field(name=f"{config.stove_burning[False]}", value=f"**{current['name']}**\nplate with `pan plate`.")
        
        embed.set_footer(text="pan bake <bread> | pan plate")
        await ctx.send(embed=embed)

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
            await ctx.send("<:melonpan:815857424996630548> `You must tell me an item you wish to bake: e.g. 'bake baguette'`")
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
        else:
            bake_obj = {
                'name': selected['name'],
                'index': config.breads.index(selected),
                'done': datetime.datetime.utcnow() + datetime.timedelta(minutes=selected['bake_time'])
            }
            entered = False
            for o in user['ovens']:
                if o is None:
                    user['ovens'][user['ovens'].index(o)] = bake_obj
                    entered = True
                    break
            if not entered:
                user['ovens'].append(bake_obj)
            config.USERS.update_one({'id': user['id']}, {'$set': {'ovens': user['ovens']}})
            await ctx.send(f"{config.stove_burning[True]} Your **{bake_obj['name']}** is now baking! use `pan bakery` to check on it, and `pan plate` to take it out when it's done.")

    @commands.command()
    async def plate(self, ctx):
        user = config.get_user(ctx.author.id)

        ending = ""
        cutoff = False

        for o in user['ovens']:
            if o is not None:
                s = (o['done'] - datetime.datetime.utcnow()).total_seconds()
                if s < 0:
                    if len(user['inventory']) >= 25:
                        cutoff = True
                        break
                    new_bread = config.create_bread(config.breads[o['index']])
                    user['inventory'].append(new_bread)
                    ending += f"+ `{config.quality_levels[new_bread['quality']]}` **{o['name']}**\n"
                    user['ovens'][user['ovens'].index(o)] = None
        
        config.USERS.update_one({'id': user['id']}, {'$set': {'inventory': user['inventory'], 'ovens': user['ovens']}})

        if ending == "":
            ending = "No bread was plated."
        
        embed = discord.Embed(color=config.MAINCOLOR, title="Plated Bread", description=ending)
        if cutoff:
            embed.description += "\n*Some ovens were not emptied because your bread storage is full. Please sell some bread.*"
        await ctx.send(embed=embed)
        



            


def setup(bot):
    bot.add_cog(Bakery(bot))