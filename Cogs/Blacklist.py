import ast
import discord
import config
import traceback
import datetime
import market

from discord.ext import commands

class Blacklist(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['bl'], ignore_extra=True)
    async def blacklist(self, ctx, channel:discord.TextChannel=None):
        if ctx.guild is None:
            await ctx.reply_safe("<:melonpan:815857424996630548> `This command can only be used in a guild.`")
            return
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.reply_safe("<:melonpan:815857424996630548> `You must have the 'manage guild' permission to use this command.`")
            return
        server = config.get_server(ctx.guild.id)
        if channel is None:
            desc = ""
            for entry in server.blacklist:
                c = ctx.guild.get_channel(entry)
                if c is not None:
                    desc += f" • {c.mention}\n"
            if desc == "":
                desc = "No blacklisted channels. Add/Remove one with `pan blacklist <channel>`"
            embed = discord.Embed(title="Blacklisted Channels", color=config.MAINCOLOR, description=desc)
            await ctx.reply_safe(embed=embed)
        else:
            if channel.id in server.blacklist:
                server.update({'$pull': {'blacklist': channel.id}})
                await ctx.reply_safe(f"{channel.mention} was unblacklisted. Commands **will** work there once again.")
            else:
                server.update({'$push': {'blacklist': channel.id}})
                await ctx.reply_safe(f"{channel.mention} was blacklisted. Commands will **no longer** work there.")
    
    @blacklist.error
    async def blacklist_error(self, ctx, error):
        if isinstance(error, commands.errors.UserInputError):
            await ctx.reply_safe("You must specify a channel.")
        else:
            raise error


def setup(bot):
    bot.add_cog(Blacklist(bot))