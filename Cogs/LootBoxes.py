import ast
import discord
import config
import traceback
import datetime
import random
import asyncio
import uuid

from discord.ext import commands

class LootBoxes(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def open(self, ctx):
        user = config.get_user(ctx.author.id)

        box = None
        for i in user['inventory']:
            if i['index'] == 14:
                box = i
                break
        if box is None:
            await ctx.reply_safe("<:melonpan:815857424996630548> `You do not have any BreadBoxes. Buy some from the 'pan shop'.`")
            return
        
        msg = await ctx.reply_safe(embed=discord.Embed(title="Opening a breadbox...", color=config.MAINCOLOR))

        await asyncio.sleep(1.5)

        user = config.get_user(ctx.author.id)

        box = None
        for i in user['inventory']:
            if i['index'] == 14:
                box = i
                break
        if box is None:
            await msg.edit(content="<:melonpan:815857424996630548> `You do not have any BreadBoxes. Buy some from the 'pan shop'.`", embed=None)
            return
        
        seed = box.get('uuid', box.get('created', box.get('quality', 0)))
        if isinstance(seed, datetime.datetime):
            seed = seed.timestamp()
        if isinstance(seed, str):
            seed = uuid.UUID(seed)
        seed = int(seed)

        random.seed(seed)
        loot = random.choices(config.breads, k=random.randrange(2, 5))

        if len(loot) + len(user['inventory']) > user.get('inventory_capacity', 25):
            await msg.edit(content="<:melonpan:815857424996630548> `This BreadBox holds more bread than you can fit in your bag.`", embed=None)
            return

        desc = ""
        to_add = []
        for _ in loot:
            b = config.create_bread(_)
            special_string = b.get('special', None)
            if special_string is not None:
                special_string = f" `{special_string}`"
            else:
                special_string = ""
            desc += f"+ {_['emoji']} **{_['name']}**{special_string}\n"
            to_add.append(b)

        config.USERS.update_one({'id': user['id']}, {'$push': {'inventory': {'$each': to_add}}})
        config.USERS.update_one({'id': user['id']}, {'$pull': {'inventory': box}})
        
        embed = discord.Embed(title="BreadBox", color=config.MAINCOLOR, description=desc)
        embed.set_footer(text="react with 💲 to sell these breads")
        await msg.edit(embed=embed)
        config.SELL_BREAD_CACHE.append((msg, user, to_add))
        await msg.add_reaction("💲")
    

def setup(bot):
    bot.add_cog(LootBoxes(bot))