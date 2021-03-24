import discord
import config
import datetime

from discord.ext import commands, tasks, menus

class Guilds(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['server', 'g', 'discord', 'company', 'com', 'group', 'clan'])
    async def guild(self, ctx):
        server = config.get_server(ctx.guild.id)
        embed = discord.Embed(title="Server Info", color=config.MAINCOLOR)
        embed.set_author(icon_url=str(ctx.guild.icon_url), name=str(ctx.guild.name))
        embed.add_field(name=server.name, value=f"BreadCoin Value: **{server.money:,}**\nTax: **{round(server.tax*100, 2)}%**\nUnique Chance: **{round(server.one_of_a_kind_bread_chance*100, 2)}%**\nDrop Cooldown: **{server.drop_cooldown_min} min.**")

        embed.set_footer(text="Value is collected from taxes and donations.")

        embed.description = "`This Server has reached max level.`"
        if server.money_until_next_level is not None:
            embed.description = f"`{server.money_until_next_level} BreadCoin until server upgrade.`"
        
        await ctx.send(embed=embed)
        

def setup(bot):
    bot.add_cog(Guilds(bot))