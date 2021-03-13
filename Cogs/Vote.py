import dbl
import discord
from discord.ext import commands, tasks
import os
import asyncio
import datetime
import logging
import config


class Vote(commands.Cog):
    """Handles interactions with the top.gg API"""

    def __init__(self, bot):
        self.bot = bot
        self.token = os.environ.get("MELONPAN_TOPGG") # set this to your DBL token
        self.dblpy = dbl.DBLClient(self.bot, self.token, webhook_path='/webhook-melon', webhook_auth=os.environ.get("MELONPAN_TOPGGSECRET"), webhook_port=25565)
        #self.update_stats.start()

    def cog_unload(self):
        self.update_stats.cancel()

    @tasks.loop(minutes=30.0)
    async def update_stats(self):
        """This function runs every 30 minutes to automatically update your server count"""
        logger.info('Attempting to post server count')
        try:
            await self.dblpy.post_guild_count()
            logger.info('Posted server count ({})'.format(self.dblpy.guild_count()))
        except Exception as e:
            logger.exception('Failed to post server count\n{}: {}'.format(type(e).__name__, e))

    @commands.command()
    async def vote(self, ctx):
        user = config.get_user(ctx.author.id)
        vote_string = ""
        can_vote = False
        if user.get('last_vote', None) is None:
            can_vote = True
            vote_string = "[**Vote Now!**](https://top.gg/bot/815835732979220501/vote)"
        else:
            s = (datetime.datetime.utcnow() - user.get('last_vote')).total_seconds()
            hours, remainder = divmod(s, 3600)
            minutes, seconds = divmod(remainder, 60)
            vote_string = f"[`You can vote again in {hours}h {minutes}m {seconds}s.`](https://top.gg/bot/815835732979220501)"
        embed = discord.Embed(title="Voting", color=config.MAINCOLOR, description=f"{vote_string}\n```\n-- REWARDS --```\n+ `100`x <:BreadCoin:815842873937100800> **BreadCoin**\n+ `1`x <:breadbox:819132627843416074> **BreadBox**\n+ `1`x <:question:820117437022208040> Mystery Bread")
        if can_vote:
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/814990535956889612.png?v=1")
        else:
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/814990535751106660.png?v=1")
        embed.set_footer(text="You can vote every 12 hours.")
        await ctx.reply_safe(embed=embed)


    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        user = config.get_user(int(data['user']))
        print(f"VOTE: {data['user']}")
        amount = 1 if data['isWeekend'] else 2

        to_add = []
        for _ in range(amount):
            if len(to_add) + len(user['inventory']) >= user['inventory_capacity']:
                break
            to_add.append(config.create_bread(config.breads[14]))
            if len(to_add) + len(user['inventory']) >= user['inventory_capacity']:
                break
            to_add.append(config.create_bread(config.create_drop()))


        config.USERS.update_one({'id': user['id']}, {'$inc': {'money': amount * 100}, '$push': {'inventory': {'$each': to_add}}, '$set': {'last_vote': datetime.datetime.utcnow()}})


def setup(bot):
    global logger
    logger = logging.getLogger('bot')
    bot.add_cog(Vote(bot))