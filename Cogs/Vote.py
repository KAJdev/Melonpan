import dbl
import discord
from discord.ext import commands, tasks
import os
import asyncio
import datetime
import logging
import config
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice


class Vote(commands.Cog):
    """Handles interactions with the top.gg API"""

    def __init__(self, bot):
        self.bot = bot
        if 0 in self.bot.shard_ids:
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

    async def vote_command(self, ctx):
        user = self.bot.mongo.get_user(ctx.author.id)
        vote_string = ""
        can_vote = False
        if user.get('last_vote', None) is None:
            can_vote = True
            vote_string = "[**Vote Now!**](https://top.gg/bot/815835732979220501/vote)"
        else:
            s = ((user.get('last_vote') + datetime.timedelta(hours=12)) - datetime.datetime.utcnow()).total_seconds()
            if s > 0:
                hours, remainder = divmod(s, 3600)
                minutes, seconds = divmod(remainder, 60)
                vote_string = f"[`You can vote again in {round(hours)}h {round(minutes)}m {round(seconds)}s.`](https://top.gg/bot/815835732979220501)"
            else:
                can_vote = True
                vote_string = "[**Vote Now!**](https://top.gg/bot/815835732979220501/vote)"
        embed = discord.Embed(title="Voting", color=config.MAINCOLOR, description=f"{vote_string}\n```\n-- REWARDS --```\n+ `100`x <:BreadCoin:815842873937100800> **BreadCoin**\n+ `1`x <:breadbox:819132627843416074> **BreadBox**\n+ `1`x <:question:820117437022208040> **Mystery Bread**")
        if can_vote:
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/814990535956889612.png?v=1")
        else:
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/814990535751106660.png?v=1")
        embed.set_footer(text="You can vote every 12 hours.")
        await config.reply(ctx, embed=embed)

    @commands.command(aliases=['v', 'topgg', 'rewards'])
    async def vote(self, ctx):
        await self.vote_command(ctx)

    @cog_ext.cog_slash(name="vote",
        description="Vote for Melonpan!")
    async def vote_slash(self, ctx: SlashContext):
        await self.vote_command(ctx)

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        user = self.bot.mongo.get_user(int(data['user']))
        print(f"VOTE: {data['user']}")
        amount = 1 if data['isWeekend'] else 2

        to_add = []
        for _ in range(amount):
            if len(to_add) + len(user['inventory']) >= user.get('inventory_capacity', 25):
                break
            to_add.append(config.create_bread(config.breads[14]))
            if len(to_add) + len(user['inventory']) >= user.get('inventory_capacity', 25):
                break
            to_add.append(config.create_bread(config.create_drop()))


        self.bot.mongo.update_user(user, {'$inc': {'money': amount * 100}, '$push': {'inventory': {'$each': to_add}}, '$set': {'last_vote': datetime.datetime.utcnow()}})


def setup(bot):
    global logger
    logger = logging.getLogger('bot')
    bot.add_cog(Vote(bot))
