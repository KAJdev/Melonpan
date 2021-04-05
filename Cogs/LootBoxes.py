import ast
import discord
import config
import traceback
import datetime
import random
import asyncio
import uuid

from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

class LootBoxes(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def open_command(self, ctx):
        user = self.bot.mongo.get_user(ctx.author.id)

        box = None
        for i in user['inventory']:
            if i['index'] == 14:
                box = i
                break
        if box is None:
            await config.reply(ctx, "<:melonpan:815857424996630548> `You do not have any BreadBoxes. Buy some from the 'pan shop'.`")
            return

        msg = await config.reply(ctx, embed=discord.Embed(title="Opening a breadbox...", color=config.MAINCOLOR))

        await asyncio.sleep(1.5)

        user = self.bot.mongo.get_user(ctx.author.id)
        server = self.bot.mongo.get_server(ctx.guild.id)

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
            b = server.create_bread(_)
            special_string = b.get('special', None)
            if special_string is not None:
                special_string = f" `{special_string}`"
            else:
                special_string = ""
            desc += f"+ {_['emoji']} **{_['name']}**{special_string}\n"
            to_add.append(b)

        self.bot.mongo.update_user(user, {'$push': {'inventory': {'$each': to_add}}})
        self.bot.mongo.update_user(user, {'$pull': {'inventory': box}})

        embed = discord.Embed(title="BreadBox", color=config.MAINCOLOR, description=desc)
        embed.set_footer(text="react with 💲 to sell these breads")
        await msg.edit(embed=embed)
        config.SELL_BREAD_CACHE.append((msg, user, to_add))
        await msg.add_reaction("💲")

    @commands.command()
    async def open(self, ctx):
        await self.open_command(ctx)

    @cog_ext.cog_slash(name="open",
        description="Open a BreadBox item.")
    async def open_slash(self, ctx: SlashContext):
        await self.open_command(ctx)


def setup(bot):
    bot.add_cog(LootBoxes(bot))