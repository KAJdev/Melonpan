import ast
import discord
import config
import traceback
import datetime
import market

from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

class Core(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.bot_invite = "https://discord.com/api/oauth2/authorize?client_id=815835732979220501&permissions=314433&redirect_uri=https%3A%2F%2Fdiscord.gg%2FueYyZVJGcf&scope=bot%20applications.commands"

    @commands.command(aliases=['settings', 'h'])
    async def help(self, ctx):
        await ctx.send(embed=discord.Embed(
            title="Melonpan Commands",
            color=config.MAINCOLOR,
            description=f"[Invite]({self.bot_invite}) | [Support](https://discord.gg/ueYyZVJGcf) | [Vote](https://top.gg/bot/815835732979220501/vote) | [Patreon](https://www.patreon.com/MelonpanBot)"
        ).add_field(
            name="Information",
            value="`inventory`, `stats`, `bal`, `badges`, `breads`, `guild`",
            inline=False
        ).add_field(
            name="Bakery",
            value="`bakery`, `bake`, `bakeall`, `plate`, `build`, `expand`, `open`",
            inline=False
        ).add_field(
            name="Market",
            value="`sell`, `sellall`, `buy`, `shop`, `donate`, `trade`",
            inline=False
        ).add_field(
            name="Misc",
            value="`help`, `info`, `invite`, `top`, `remind`, `reminders`, `blacklist`, `vote`",
            inline=False
        ).set_thumbnail(url=self.bot.user.avatar_url))

    @commands.command(aliases = ['join'])
    async def invite(self, ctx):
        await ctx.send(embed=discord.Embed(description=f"[**Invite Link**]({self.bot_invite}) 🔗", color = config.MAINCOLOR))

    @cog_ext.cog_slash(name = "invite", description="Invite Melonpan to your server.")
    async def invite_slash(self, ctx):
        await ctx.send(embed=discord.Embed(description=f"[**Invite Link**]({self.bot_invite}) 🔗", color = config.MAINCOLOR))

def setup(bot):
    bot.add_cog(Core(bot))