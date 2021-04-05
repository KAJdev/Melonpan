import discord
import config
import datetime

from discord.ext import commands, tasks, menus
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

class Guilds(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def guild_command(self, ctx):
        if ctx.guild is None:
            await ctx.send("<:melonpan:815857424996630548> `This isn't a guild, silly.`")
            return
        server = self.bot.mongo.get_server(ctx.guild.id)
        embed = discord.Embed(title="Server Info", color=config.MAINCOLOR)
        embed.set_author(icon_url=str(ctx.guild.icon_url), name=str(ctx.guild.name))
        embed.add_field(name=server.name, value=f"BreadCoin Value: **{server.money:,}**\nTax: **{round(server.tax*100, 2)}%**\nUnique Chance: **{round(server.one_of_a_kind_bread_chance*100, 2)}%**\nDrop Cooldown: **{server.drop_cooldown_min} min.**")

        embed.set_footer(text="Value is collected from taxes and donations.")

        embed.description = "`This Server has reached max level.`"
        if server.money_until_next_level is not None:
            embed.description = f"`{server.money_until_next_level} BreadCoin until server upgrade.`"

        await ctx.send(embed=embed)

    @commands.command(aliases=['server', 'g', 'discord', 'company', 'com', 'group', 'clan'])
    async def guild(self, ctx):
        await self.guild_command(ctx)

    @cog_ext.cog_slash(name="guild",
        description="View guild info.")
    async def guild_slash(self, ctx: SlashContext):
        await self.guild_command(ctx)



def setup(bot):
    bot.add_cog(Guilds(bot))