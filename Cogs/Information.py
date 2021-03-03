import ast
import discord
import config
import traceback
import datetime
import market

from discord.ext import commands, tasks

class Information(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.timer_loop.start()
    
    def cog_unload(self):
        self.timer_loop.cancel()

    @tasks.loop(minutes=1)
    async def timer_loop(self):
        sent_timers = []
        expired_timers = []
        for timer in config.TIMERS.find({'time': {'$lte': datetime.datetime.utcnow()}, 'expired': False}):
            expired_timers.append(timer)
            user = self.bot.get_user(timer['owner'])
            if user is None:
                try:
                    user = await self.bot.fetch_user(timer['owner'])
                except:
                    continue
            embed = discord.Embed(color=config.MAINCOLOR, title="Time's up!", description=timer['message'], timestamp=timer['created'])
            embed.set_footer(text="This timer was scheduled at >")

            try:
                await user.send(embed=embed)
                sent_timers.append(timer)
            except:
                continue
        config.TIMERS.update_many({'_id': {'$in': list(x['_id'] for x in expired_timers)}}, {'$set': {'expired': True}})
        config.TIMERS.update_many({'_id': {'$in': list(x['_id'] for x in sent_timers)}}, {'$set': {'sent': True}})

    @commands.command(aliases=['i', 'inv', 'items', 'in', 'bag', 'breads', 'bread'])
    async def inventory(self, ctx):
        user = config.get_user(ctx.author.id)
        desc = ""
        if len(user['inventory']) < 1:
            desc = "You have no bread. Try managing your bakery with `bakery`."
        else:
            for a in user['inventory']:
                item = config.breads[a['index']]
                desc+=f"`{config.quality_levels[a['quality']]}` · **{item['name']}**\n"
        embed = discord.Embed(
            title="Bread Inventory",
            color=config.MAINCOLOR,
            description=desc
        )
        embed.set_footer(text=f"Storing {len(user['inventory'])}/25 breads")
        await ctx.reply(embed=embed)

    @commands.command(aliases=['timer', 'time', 'r'])
    async def remind(self, ctx, *, args:str=None):
        user = config.get_user(ctx.author.id)

        if args is None:
            await ctx.reply("<:melonpan:815857424996630548> `Please tell me the timer length and note: e.g. 'remind 1h 2m 4s take out the bread'`")
            return

        splitted = args.split(" ")
        time = {"h": 0, "m": 0, "s": 0, "d": 0}
        message = []
        for word in splitted:
            if word[len(word) - 1].lower() in ['h', 'm', 's', 'd']:
                try:
                    time[word[len(word) - 1].lower()] += int(word[:len(word) - 2])
                except Exception as e:
                    raise e
                    message.append(word)
            else:
                message.append(word)
        remind_time = datetime.datetime.utcnow() + datetime.timedelta(days=time['d'], hours=time['h'], minutes=time['m'], seconds=time['s'])
        message = " ".join(message)

        embed = discord.Embed(color=config.MAINCOLOR, timestamp=remind_time)
        embed.set_footer(text=f"I will send you a DM to remind you to: '{message}' at >")

        config.TIMERS.insert_one({'owner': ctx.author.id, 'time': remind_time, 'created': datetime.datetime.utcnow(), 'message': message, 'id': ctx.message.id, 'sent': False, 'expired': False})

        await ctx.reply(embed=embed)


    @commands.command(aliases=['money', 'balance'])
    async def bal(self, ctx, member : discord.Member = None):
        if member is None:
            member = ctx.author

        user = config.get_user(member.id)

        assets = 0
        for item in user['inventory']:
            r = config.breads[item['index']]
            item_price = market.ItemPrice(r['price'], 5, item['index'])
            today_price = round(item_price.get_price(market.get_day_of_year()))
            assets += today_price

        embed=discord.Embed(
            title="Baker Balance",
            description=f"**Pocket**: `{user['money']}` <:BreadCoin:815842873937100800>\n**Bread Worth**: `{assets}` <:BreadCoin:815842873937100800> [<:BreadWarning:815842874226245643>]({ctx.message.jump_url} \"This value is based on the market and will change.\")\n**Total Assets**: `{user['money'] + assets}` <:BreadCoin:815842873937100800>",
            color=config.MAINCOLOR
        )

        await ctx.reply(embed=embed)

    @commands.command(aliases=['s', 'stat', 'info', 'profile', 'user'])
    async def stats(self, ctx, member : discord.Member = None):
        if member is None:
            member = ctx.author

        user = config.get_user(member.id)
        embed=discord.Embed(
            title="Baker Info",
            color=config.MAINCOLOR
        )
        embed.set_thumbnail(url=member.avatar_url)
        if member.guild != 814958240009420830:
            guild = self.bot.get_guild(814958240009420830)
            try:
                mem = await guild.fetch_member(member.id)
            except:
                mem = None
        else:
            mem = member
        if mem is not None:
            if 814964592076652554 in [x.id for x in mem.roles]:
                if 7 not in user['badges']:
                    user['badges'].append(7)

        if len(user.get('badges', [])) > 0:
            embed.description = " ".join(config.badges[x]['emoji'] for x in user.get('badges', []))

        fav = {'name': "None", 'amount': 0}
        total = 0
        for x, y in user['baked'].items():
            total += y
            if y > fav['amount']:
                fav = {'name': config.breads[int(x)]['name'], 'amount': y}

        embed.add_field(name="Baking Stats", value=f"Favorite Bread: **{fav['name']}** ({fav['amount']} bakes)\nBreads Baked: **{total}**\nBreadCoin: **{user['money']}** <:BreadCoin:815842873937100800>\nOvens: **{user['oven_count']}**")

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Information(bot))