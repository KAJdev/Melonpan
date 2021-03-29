import ast
import discord
import config
import traceback
import datetime
import market

from discord.ext import commands, tasks
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

class BreadmojiEvent(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.delete.start()
        self.to_delete = []
        self.allowed = ['🥯', '🥖', '🫓', '🍞', '🥐', '🥨']
        self.channel = 816841054983946271
        self.guild = 814958240009420830

    def cog_unload(self):
        self.delete.cancel()

    @tasks.loop(seconds=0.5)
    async def delete(self):
        if isinstance(self.channel, int):
            g = self.bot.get_guild(self.guild)
            if g is not None:
                t = self.channel
                self.channel = g.get_channel(self.channel)
                if self.channel is None:
                    self.channel = t
                    print("couldn't get channel")
                    return

        if len(self.to_delete) > 0:
            def check(message):
                return message.id in self.to_delete

            deleted = await self.channel.purge(limit=100, check=check, bulk=True)
            for msg in deleted:
                if msg.id in self.to_delete:
                    self.to_delete.remove(msg.id)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == self.channel.id:
            if message.content is None or len(message.stickers) > 0 or len(message.content) > 20:
                self.to_delete.append(message.id)
                return
            for w in message.content:
                if w in [" ", "\n"]:
                    continue
                if w not in self.allowed:
                    self.to_delete.append(message.id)
                    return

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.content is None or len(after.stickers) > 0 or len(after.content) > 20:
                self.to_delete.append(after.id)
                return
        if after.channel.id == self.channel.id:
            for w in after.content:
                if w in [" ", "\n"]:
                    continue
                if w not in self.allowed:
                    self.to_delete.append(after.id)
                    return


def setup(bot):
    bot.add_cog(BreadmojiEvent(bot))