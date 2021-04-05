import asyncio
from importlib import reload
import config

import discord
import uvloop
from discord.ext import commands

import Cogs

uvloop.install()


async def determine_prefix(bot, message):
    li = ['pan ', 'Pan ', 'PaN ', 'pAn ', 'paN ', 'PAn ', 'PaN ', 'PAn ', 'PAN ']
    return commands.when_mentioned_or(*li)(bot, message)


def is_enabled(ctx):
    if not ctx.bot.enabled:
        raise commands.CheckFailure(DEFAULT_DISABLED_MESSAGE)
    return True


class ClusterBot(commands.AutoShardedBot):

    def __init__(self, **kwargs):
        self.cluster_name = kwargs.pop("cluster_name")
        self.cluster_idx = kwargs.pop("cluster_idx")
        self.config = config

        self.ready = False
        self.menus = {}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        super().__init__(**kwargs, loop=loop, command_prefix=determine_prefix)
        self.remove_command("help")

        # Load extensions
        for i in Cogs.default:
            self.load_extension(f"Cogs.{i}")

        def check_for_blacklist(ctx):
            if ctx.guild is not None:
                server = config.get_server(ctx.guild.id)
                return not (ctx.channel.id in server.blacklist)
            else:
                return True

        self.add_check(check_for_blacklist)

        # Run bot

        self.log.info(
            f'[Cluster#{self.cluster_name}] {kwargs["shard_ids"]}, {kwargs["shard_count"]}'
        )

        self.slash = SlashCommand(self, sync_commands=True)

        self.loop.create_task(self.do_startup_tasks())
        self.run(kwargs["token"])

    # Easy access to things
    @property
    def log(self):
        return self.get_cog("Logging").log

    @property
    def enabled(self):
        for cog in self.cogs.values():
            try:
                if not cog.ready:
                    return False
            except AttributeError:
                pass
        return self.ready

    # Other stuff

    async def do_startup_tasks(self):
        await self.wait_until_ready()
        self.ready = True
        self.log.info(f"Logged in as {self.user}")

    async def on_guild_join(self, guild):
        self.log.info(f"JOINED guild {guild.name} ({guild.member_count} members) | current guilds: {len(bot.guilds)}")

    async def on_guild_remove(self, guild):
        self.log.info(f"LEFT guild {guild.name} ({guild.member_count} members) | current guilds: {len(bot.guilds)}")

    async def on_ready(self):
        self.log.info(f"[Cluster#{self.cluster_name}] Ready called.")

    async def on_shard_ready(self, shard_id):
        self.log.info(f"[Cluster#{self.cluster_name}] Shard {shard_id} ready")

    async def on_message(self, message: discord.Message):
        message.content = (
            message.content.replace("—", "--").replace("'", "′").replace("‘", "′").replace("’", "′")
        )

        if message.content.lower().startswith("pan sell all"):
            message.content = "pan sellall" + message.content[12:]

        await self.process_commands(message)

    async def on_message_edit(self, before, after):
        after.content = (
            after.content.replace("—", "--").replace("'", "′").replace("‘", "′").replace("’", "′")
        )

        if after.content.lower().startswith("pan sell all"):
            after.content = "pan sellall" + after.content[12:]

        await self.process_commands(after)

    async def close(self):
        self.log.info("shutting down")
        await super().close()

    async def reload_modules(self):
        self.ready = False

        reload(Cogs)

        for i in Cogs.default:
            self.reload_extension(f"Cogs.{i}")

        await self.do_startup_tasks()