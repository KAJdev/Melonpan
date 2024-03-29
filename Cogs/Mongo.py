import ast
import discord
import config
import traceback
import datetime
import pymongo
import random

from discord.ext import commands, tasks
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice
import os
import uuid
from random_word import RandomWords
import string

mongo_instance = None

class Server():
    def __init__(self, server):
        for k,v in server.items():
            setattr(self, k, v)
        self.mongo = mongo_instance
        self.id = server.get('id', None)
        self.blacklist = server.get('blacklist', [])
        self.prefix = server.get('prefix', 'pan ')
        self.tax = server.get('tax', round(random.random() * 0.2, 2))
        self.money = server.get('money', 0)
        level = self.get_level()
        self.name = level.get('name', None)
        self.one_of_a_kind_bread_chance = level.get('one_of_a_kind_droprate', config.one_of_a_kind_bread_chance)
        self.tax *= level.get('tax_ratio', 1)
        self.drop_cooldown_min = level.get('drop_cooldown', config.drop_cooldown_min)
        i = config.guild_money_levels.index(level)
        if i >= len(config.guild_money_levels) - 1:
            self.money_until_next_level = None
            self.next_level = None
        else:
            self.money_until_next_level = level['max'] - self.money
            self.next_level = config.guild_money_levels[i + 1]

    def get_level(self):
        for _ in config.guild_money_levels:
            if self.money < _['max']:
                return _
        return config.guild_money_levels[len(config.guild_money_levels) - 1]

    def create_bread(self, bread):
        random.seed()
        bread = {
            'index': config.breads.index(bread),
            'quality': random.randint(1, 5),
            'created': datetime.datetime.utcnow(),
            'uuid': str(uuid.uuid4())
        }
        if random.random() <= self.one_of_a_kind_bread_chance:
            bread['special'] = config.gen_bread_id()
        return bread

    def update(self, change):
        """
        Updates a discord server object in the MongoDB and stores result in the cache
        """
        if self.mongo is not None:
            after = self.mongo.db.servers.find_one_and_update({'id': self.id}, change, return_document=pymongo.ReturnDocument.AFTER)
            self.__init__(after)
        else:
            raise NameError("Mongo instance has not been Initialized yet.")

class Mongo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.cluster = pymongo.MongoClient(os.environ.get("MELONPAN_MONGO"))
        self.db = self.cluster.main
        self.SERVER_CACHE = {}
        self.USER_CACHE = {}
        global mongo_instance
        mongo_instance = self

    def get_user(self, id):
        cached = self.USER_CACHE.get(id, None)
        if cached is not None:
            return cached

        user = self.db.users.find_one({'id': id})
        if user is None:
            user = {
                'id': id,
                'inventory': [],
                'inventory_capacity': 25,
                'money': 0,
                'baked': {},
                'ovens': [],
                'oven_count': 2,
                'badges': [],
                'last_vote': None
            }
            self.db.users.insert_one(user)
        self.USER_CACHE[id] = user
        return user

    def get_server(self, id):
        cached = self.SERVER_CACHE.get(id, None)
        if cached is not None:
            return cached

        server = self.db.servers.find_one({'id': id})
        if server is None:
            random.seed()
            server = {
                'id': id,
                'blacklist': [],
                'prefix': 'pan ',
                'tax': round(random.random() * 0.2, 2),
                'money': 0
            }
            self.db.servers.insert_one(server)
        server = Server(server)
        self.SERVER_CACHE[id] = server
        return server

    def update_server(self, server, change):
        after = self.db.servers.find_one_and_update({'id': server.id}, change, return_document=pymongo.ReturnDocument.AFTER)
        server.__init__(after)

    def update_user(self, user, change):
        if isinstance(user, int):
            id = user
        elif isinstance(user, dict):
            id = user['id']
        after = self.db.users.find_one_and_update({'id': id}, change, return_document=pymongo.ReturnDocument.AFTER)
        self.USER_CACHE[id] = after

    def add_money_to_server(self, server, amount):
        self.update_server(server, {'$inc': {'money': amount}})

def setup(bot):
    bot.add_cog(Mongo(bot))