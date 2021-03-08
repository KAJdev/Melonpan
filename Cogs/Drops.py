import ast
import discord
import config
import traceback
import datetime
import market
import asyncio

from discord.ext import commands

class Drops(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
    
    async def send_drop_message(self, message):
        await asyncio.sleep(5)
        drop = config.create_drop()
        embed = discord.Embed(color=config.special_drop[drop['special']], title=drop['name'])
        embed.set_footer(text="React first to claim the free bread!")
        embed.set_author(name="Bread Drop")
        embed.set_image(url=drop['image'])

        msg = await message.channel.send(embed=embed)
        await msg.add_reaction("<:BreatHunter:815484321573896212>")

        def check(reaction, user):
            if user.id == self.bot.user.id:
                return False
            print(str(reaction.emoji))
            if reaction.message.id == msg.id and str(reaction.emoji) == <:BreatHunter:815484321573896212>:
                u = config.get_user(user.id)
                if len(u['inventory']) < u.get('inventory_capacity', 25):
                    return True
                return False
            return False

        try:
            reaction, member = await self.bot.wait_for('reaction_add', check=check, timeout=120)
        except asyncio.TimeoutError:
            await msg.delete()
            return

        try:
            await msg.clear_reactions()
        except:
            pass

        winner = config.get_user(member.id)
        config.USERS.update_one({'id': member.id}, {'$push': {'inventory': config.create_bread(drop)}})
        embed.set_footer(text="This bread has already been claimed.")
        embed.description = f"{member.mention} has claimed the **{drop['name']}**!"
        await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is not None:
            server = config.get_server(message.guild.id)
            if message.channel.id in server['blacklist']:
                return

        obj = self.cache.get(message.channel.id, None)
        if obj is None:
            self.cache[message.channel.id] = ([], datetime.datetime.utcnow())
        
        self.cache[message.channel.id][0].append((message, datetime.datetime.utcnow()))

        if len(self.cache[message.channel.id][0]) > config.drop_message_count:
            self.cache[message.channel.id][0].pop(0)
        
        if datetime.datetime.utcnow() - self.cache[message.channel.id][1] >= datetime.timedelta(minutes=config.drop_cooldown_min):
            count = 0
            for x in self.cache[message.channel.id][0]:
                if datetime.datetime.utcnow() - x[1] <= datetime.timedelta(minutes=config.drop_time_constraint):
                    count += 1
            print(count)
            
            if count >= config.drop_message_count:
                self.cache[message.channel.id] = ([], datetime.datetime.utcnow())
                await self.send_drop_message(message)
                
        print(len(self.cache), len(self.cache[message.channel.id][0]))

def setup(bot):
    bot.add_cog(Drops(bot))