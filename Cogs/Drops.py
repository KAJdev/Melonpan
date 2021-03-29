import ast
import discord
import config
import traceback
import datetime
import market
import asyncio

from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

class Drops(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.cache = {}

    async def send_drop_message(self, message, server):
        await asyncio.sleep(5)
        drop = config.create_drop()
        actual_bread = server.create_bread(drop)
        special_string = actual_bread.get('special', None)
        if special_string is not None:
            special_string = f" `{special_string}`"
        else:
            special_string = ""
        embed = discord.Embed(color=config.special_drop[drop['special']], title=drop['name'] + special_string)
        embed.set_footer(text="React first to claim the free bread!\n\nDisable commands/drops with pan blacklist")
        embed.set_author(name="Bread Drop")
        embed.set_thumbnail(url=drop['image'])

        msg = await message.channel.send(embed=embed)
        await msg.add_reaction("<:BreatHunter:815484321573896212>")

        def check(reaction, user):
            if user.id == self.bot.user.id:
                return False
            if reaction.message.id == msg.id and str(reaction.emoji) == "<:BreatHunter:815484321573896212>":
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
        print(f"DROP_CLAIM: #{message.channel.name} ({member})")
        config.USERS.update_one({'id': member.id}, {'$push': {'inventory': actual_bread}})
        embed.set_footer(text="This bread has already been claimed.\n\nDisable commands/drops with pan blacklist")
        embed.description = f"{member.mention} has claimed the **{drop['name']}**!"
        embed.color = 0x2f3136
        await msg.edit(embed=embed)

    @commands.command()
    async def forcedrop(self, ctx):
        if ctx.author.id in config.OWNERIDS:
            await self.send_drop_message(ctx.message, config.get_server(ctx.guild.id))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is not None:
            server = config.get_server(message.guild.id)
            if message.channel.id in server.blacklist:
                return
        else:
            return

        if message.guild is not None:
            if not message.channel.permissions_for(message.guild.me).send_messages:
                return

        obj = self.cache.get(message.channel.id, None)
        if obj is None:
            self.cache[message.channel.id] = ([], datetime.datetime.utcnow())

        self.cache[message.channel.id][0].append((message, datetime.datetime.utcnow()))

        if len(self.cache[message.channel.id][0]) > config.drop_message_count:
            self.cache[message.channel.id][0].pop(0)

        if datetime.datetime.utcnow() - self.cache[message.channel.id][1] >= datetime.timedelta(minutes=server.drop_cooldown_min):
            count = 0
            for x in self.cache[message.channel.id][0]:
                if datetime.datetime.utcnow() - x[1] <= datetime.timedelta(minutes=config.drop_time_constraint):
                    count += 1

            if count >= config.drop_message_count:
                self.cache[message.channel.id] = ([], datetime.datetime.utcnow())
                guild = "NO GUILD"
                if message.guild is not None: guild = message.guild.name
                print(f"DROP: #{message.channel.name} ({guild})")
                await self.send_drop_message(message, server)

def setup(bot):
    bot.add_cog(Drops(bot))