import ast
import discord
import config
import traceback
import datetime
import market
import os
import psutil

from discord.ext import commands, tasks, menus

class InventoryMenu(menus.ListPageSource):
    def __init__(self, data, max=25):
        super().__init__(data, per_page=10)
        self.max = max
        self.og = data

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        desc = ""
        for i, v in enumerate(entries, start=offset):
            n = config.breads[v['index']]['name']
            desc += f"`{config.quality_levels[v['quality']]}` · **{n}**\n"
        embed = discord.Embed(
            title="Bread Inventory",
            color=config.MAINCOLOR,
            description=desc
        )
        e_cost = int((self.max/config.expand_amount) * config.expand_cost)
        embed.add_field(name="<:BreadStaff:815484321590804491> Storage Expansion", value=f"`pan expand`\nCost: `{e_cost}` <:BreadCoin:815842873937100800>\n*(+{config.expand_amount} slots)*")
        embed.set_footer(text=f"Showing {menu.current_page + 1}/{menu._source.get_max_pages()} | Storage Capacity: {len(self.og)}/{self.max}")
        return embed

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
            if timer['message'].strip(" ") == "":
                timer['message'] = "No message provided."
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
            desc = "You have no bread. Try managing your bakery with `pan bakery`."
            embed = discord.Embed(
                title="Bread Inventory",
                color=config.MAINCOLOR,
                description=desc
            )
            embed.set_footer(text=f"Showing 0/0")
            await ctx.reply(embed=embed)
        else:
            pages = menus.MenuPages(source=InventoryMenu(user['inventory'], max=user.get('inventory_capacity', 25)), clear_reactions_after=True)
            await pages.start(ctx)

    @commands.command(aliases=['timer', 'time', 'r'])
    async def remind(self, ctx, *, args:str=None):
        user = config.get_user(ctx.author.id)

        if args is None:
            await ctx.reply("<:melonpan:815857424996630548> `Please tell me the timer length and note: e.g. 'pan remind 1h 2m 4s take out the bread'`")
            return

        splitted = args.split(" ")
        time = {"h": 0, "m": 0, "s": 0, "d": 0}
        message = []
        for word in splitted:
            if word[len(word) - 1].lower() in ['h', 'm', 's', 'd']:
                try:
                    time[word[len(word) - 1].lower()] += int(word[:len(word) - 1])
                except:
                    message.append(word)
            else:
                message.append(word)
        remind_time = datetime.datetime.utcnow() + datetime.timedelta(days=time['d'], hours=time['h'], minutes=time['m'], seconds=time['s'])
        message = " ".join(message)

        embed = discord.Embed(color=config.MAINCOLOR, timestamp=remind_time)
        embed.set_footer(text=f"I will DM you about '{message}' at >")

        config.TIMERS.insert_one({'owner': ctx.author.id, 'time': remind_time, 'created': datetime.datetime.utcnow(), 'message': message, 'id': ctx.message.id, 'sent': False, 'expired': False})

        await ctx.reply(embed=embed)

    @commands.command(aliases=['timers'])
    async def reminders(self, ctx):
        timers = config.TIMERS.find({'owner': ctx.author.id, 'expired': False})

        desc = ""
        for timer in timers:
            msg = timer['message']
            if len(msg) > 35:
                msg = msg[:32] + "..."

            s = (timer['time'] - datetime.datetime.utcnow()).total_seconds()
            hours, remainder = divmod(s, 3600)
            minutes, seconds = divmod(remainder, 60)

            desc += f" • {msg} - **{round(hours)}h {round(minutes)}m {round(seconds)}s**\n"
        if desc == "":
            desc = "You have no timers. Create one with `pan timer <time> <message>`\ne.g. `pan timer 120m 30s take out the sourdough bread`"

        embed = discord.Embed(color=config.MAINCOLOR, title="Timers", description = desc)

        await ctx.reply(embed=embed)

    @commands.command(aliases=['money', 'balance', 'm'])
    async def bal(self, ctx, member : discord.Member = None):
        if member is None:
            member = ctx.author

        user = config.get_user(member.id)

        assets = 0
        for item in user['inventory']:
            r = config.breads[item['index']]
            item_price = market.ItemPrice(r['price'], r['volitility'], item['index'])
            today_price = round(item_price.get_price(market.get_day_of_year_active()))
            assets += today_price

        embed=discord.Embed(
            title="Baker Balance",
            description=f"**Pocket**: `{user['money']}` <:BreadCoin:815842873937100800>\n**Bread Worth**: `{assets}` <:BreadCoin:815842873937100800> [<:BreadWarning:815842874226245643>]({ctx.message.jump_url} \"This value is based on the market and will change.\")\n**Total Assets**: `{user['money'] + assets}` <:BreadCoin:815842873937100800>",
            color=config.MAINCOLOR
        )

        await ctx.reply(embed=embed)

    @commands.command(aliases=['about'])
    async def info(self, ctx):
        embed = discord.Embed(title="Melonpan Bot Info", color=config.MAINCOLOR, timestamp=datetime.datetime.utcnow())
        embed.set_thumbnail(url=str(self.bot.user.avatar_url))

        u = 0
        for g in self.bot.guilds:
            u+=g.member_count
        embed.add_field(name="Discord Stats", value=f"Guilds: `{len(self.bot.guilds)}`\nUsers: `{u}`\nAvg MSG/s: `{round(config.get_avg_messages(), 3)}`")

        pid = os.getpid()
        py = psutil.Process(pid)
        memoryUse = py.memory_info()[0]/2.**30  # memory use in GB...I think
        cpuUse = py.cpu_percent()
        embed.add_field(name="System Usage", value=f"Memory: `{round(memoryUse*1000, 3)} MB`\nCPU: `{round(cpuUse, 3)} %`")

        embed.set_footer(text=f"discord.py v{discord.__version__}")
        await ctx.send(embed=embed)

    @commands.command(aliases=['stat', 'profile', 'user'])
    async def stats(self, ctx, member : discord.Member = None):
        if member is None:
            member = ctx.author

        user = config.get_user(member.id)
        embed=discord.Embed(
            title="Baker Info",
            color=config.MAINCOLOR
        )
        embed.set_thumbnail(url=member.avatar_url)
        if isinstance(member, discord.Member) and member.guild != 814958240009420830:
            guild = self.bot.get_guild(814958240009420830)
            try:
                mem = await guild.fetch_member(member.id)
            except:
                mem = None
        elif isinstance(member, discord.User):
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

        embed.add_field(name="Baking Stats", value=f"Favorite Bread: **{fav['name']}** ({fav['amount']} bakes)\nBreads Baked: **{total}**\nBreadCoin: **{user['money']}** <:BreadCoin:815842873937100800>\nOvens: **{user['oven_count']}**\nInventory Capacity: **{user.get('inventory_capacity', 25)}**")

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Information(bot))