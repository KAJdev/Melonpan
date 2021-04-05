import ast
import discord
import config
import traceback
import datetime

from discord.ext import commands, tasks
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

class Eval(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.message_reset.start()

    def cog_unload(self):
        self.message_reset.cancel()

    @tasks.loop(seconds=1)
    async def message_reset(self):
        if len(config.MESSAGES_PER_SECOND_AVG) > 120:
            config.MESSAGES_PER_SECOND_AVG.pop(0)
        config.MESSAGES_PER_SECOND_AVG.append(config.CURRENT_MESSAGE_SECOND_COUNT)
        config.CURRENT_MESSAGE_SECOND_COUNT = 0

    def insert_returns(self, body):
        # insert return stmt if the last expression is a expression statement
        if isinstance(body[-1], ast.Expr):
            body[-1] = ast.Return(body[-1].value)
            ast.fix_missing_locations(body[-1])

        # for if statements, we insert returns into the body and the orelse
        if isinstance(body[-1], ast.If):
            insert_returns(body[-1].body)
            insert_returns(body[-1].orelse)

        # for with blocks, again we insert returns into the body
        if isinstance(body[-1], ast.With):
            insert_returns(body[-1].body)

    @commands.command()
    async def addmoney(self, ctx, user:discord.User=None, amount:int=None):
        if ctx.author.id in config.OWNERIDS:
            if user is None:
                await ctx.send("must supply user.")
            elif amount is None:
                await ctx.send("must supply amount.")
            else:
                u = self.bot.mongo.get_user(user.id)
                self.bot.mongo.db.users.update_one({'id': u['id']}, {'$inc': {'money': amount}})
                await ctx.send(f"BreadCoins updated for {user}. User now has {u['money'] + amount} BreadCoins.")

    @commands.command()
    async def toggle_logs(self, ctx):
        if ctx.author.id not in config.OWNERIDS:
            return
        config.DEBUG_PRINTS = not config.DEBUG_PRINTS
        await ctx.send(f"debug logs toggled to `{str(config.DEBUG_PRINTS)}`")

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.bot.log.info("CMD:", ctx.message.content, " - ", ctx.author)
        config.COMMANDS_LOG.append((ctx, datetime.datetime.utcnow()))
        if len(config.COMMANDS_LOG) > 1000:
            config.COMMANDS_LOG.pop(0)

    @commands.Cog.listener()
    async def on_slash_command(self, ctx: SlashContext):
        self.bot.log.info("SLASH_CMD:", ctx.command, " - ", ctx.author)
        config.COMMANDS_LOG.append((ctx, datetime.datetime.utcnow()))
        if len(config.COMMANDS_LOG) > 1000:
            config.COMMANDS_LOG.pop(0)

    @commands.Cog.listener()
    async def on_message(self, message):
        config.CURRENT_MESSAGE_SECOND_COUNT += 1

    @commands.command(name="eval")
    async def eval_fn(self, ctx, *, cmd):
        if ctx.author.id not in config.OWNERIDS:
            return
        """Evaluates input.
        Input is interpreted as newline seperated statements.
        If the last statement is an expression, that is the return value.
        Usable globals:
          - `bot`: the bot instance
          - `discord`: the discord module
          - `commands`: the discord.ext.commands module
          - `ctx`: the invokation context
          - `__import__`: the builtin `__import__` function
        Such that `>eval 1 + 1` gives `2` as the result.
        The following invokation will cause the bot to send the text '9'
        to the channel of invokation and return '3' as the result of evaluating
        >eval ```
        a = 1 + 2
        b = a * 2
        await ctx.send(a + b)
        a
        ```
        """
        fn_name = "_eval_expr"

        cmd = cmd.strip("` ")

        # add a layer of indentation
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

        # wrap in async def body
        body = f"async def {fn_name}():\n{cmd}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        self.insert_returns(body)

        env = {
            'bot': ctx.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            '__import__': __import__,
            'config': config
        }
        try:
            exec(compile(parsed, filename="<ast>", mode="exec"), env)

            result = (await eval(f"{fn_name}()", env))
            await ctx.send(result)
        except Exception as e:
            await ctx.send(f"Error occured while running eval:\n```{str(traceback.format_exc())}```")

def setup(bot):
    bot.add_cog(Eval(bot))