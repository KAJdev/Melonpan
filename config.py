# Imports
import pymongo
import datetime
import discord
import random
import os
import uuid
from random_word import RandomWords
import string

## MongoDB
myclient = pymongo.MongoClient(os.environ.get("MELONPAN_MONGO"))

USERS = myclient["main"]['users']
SERVERS = myclient["main"]["servers"]
TIMERS = myclient["main"]["timers"]

# Owner IDS (People who have access to restart the bot)
OWNERIDS = [684155404078415890,
            282565295351136256]

DEBUG_PRINTS = True

MESSAGES_PER_SECOND_AVG = []
COMMANDS_LOG = []
CURRENT_MESSAGE_SECOND_COUNT = 0

# Cache of opened breadBox/Plate messages and the users
SELL_BREAD_CACHE = []

# MEMBER CACHE
MEMBER_CACHE = []

# SERVER CACHE
SERVER_CACHE = {}

# Main Color (Replace the part after 0x with a hex code)
MAINCOLOR = discord.Colour(0xe0ffba)

# Error Color (Replace the part after the 0x with a hex code)
ERRORCOLOR = 0xED4337

def log(*args):
    if DEBUG_PRINTS: print(str(" ".join([str(elem) for elem in args])))

def get_avg_commands(minutes=1, user=None, command=None):
    total = 0
    compare = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes)
    for _ in COMMANDS_LOG:
        if _[1] < compare:
            continue
        if user is not None and _[0].author.id != user:
            continue
        if command is not None and _[0].command.name != command:
            continue
        total += 1
    return total / (minutes*60)

def gen_bread_id():
    random.seed()
    type_of_id = random.randint(0, 2)
    if type_of_id == 0:
        return str(RandomWords().get_random_word(maxLength = 15))
    elif type_of_id == 1:
        return str(random.randint(0, 99999))
    elif type_of_id == 2:
        return "".join(random.choices(string.ascii_letters, k=6))

def get_avg_messages():
    total = 0
    for c in MESSAGES_PER_SECOND_AVG:
        total += c
    if total == 0 or len(MESSAGES_PER_SECOND_AVG) == 0:
        return 0
    return total/len(MESSAGES_PER_SECOND_AVG)

def cache_member(member):
    for c_member in MEMBER_CACHE:
        if member.id == c_member.id:
            return

    MEMBER_CACHE.append(member)

async def get_member(id, bot):
    member = get_cached_member(id)
    if member is None:
        try:
            member = await bot.fetch_user(id)
            cache_member(member)
        except:
            return None
    return member

def get_cached_member(id):
    for member in MEMBER_CACHE:
        if member.id == id:
            return member
    return None

def get_prefix(id):
    server = PREFIXES.find_one({'id': id})
    if server is None:
        server = {'id': id, 'prefix': "pan "}
    return server

def get_user(id):
    user = USERS.find_one({'id': id})
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
        USERS.insert_one(user)
    return user

def get_server(id):
    cached = SERVER_CACHE.get(id, None)
    if cached is not None:
        return cached

    server = dict(SERVERS.find_one({'id': id}))
    if server is None:
        random.seed()
        server = {
            'id': id,
            'blacklist': [],
            'prefix': 'pan ',
            'tax': round(random.random() * 0.2, 2),
            'money': 0
        }
        SERVERS.insert_one(server)
    server = Server(server)
    SERVER_CACHE[id] = server
    return server

def create_bread(bread):
    random.seed()
    bread = {
        'index': breads.index(bread),
        'quality': random.randint(1, 5),
        'created': datetime.datetime.utcnow(),
        'uuid': str(uuid.uuid4())
    }
    if random.random() <= one_of_a_kind_bread_chance:
        bread['special'] = gen_bread_id()
    return bread

def create_drop():
    return random.choice(breads)

quality_levels = {1: "☆☆☆☆", 2: "★☆☆☆", 3: "★★☆☆", 4: "★★★☆", 5: "★★★★"}
stove_burning = {True: "<:stove_burning:815877702410043432>", False: "<:stove:815875824376610837>"}
oven_cost = 150
expand_cost = 250
expand_amount = 5
burn_time_multipier = 1.5
drop_message_count = 40
drop_time_constraint = 2
one_of_a_kind_bread_chance = 0.03
drop_cooldown_min = 5
special_drop = {True: 0xfcba03, False: 0xd3e647}

guild_money_levels = [
    {# starts at 0 breadcoin
        "max": 1000,
        "name": "Small Bakery",
        "one_of_a_kind_droprate": one_of_a_kind_bread_chance,
        "tax_ratio": 1,
        "drop_cooldown": drop_cooldown_min
    },
    {# starts at 1,000 breadcoin
        "max": 5000,
        "name": "Retail Bakery",
        "one_of_a_kind_droprate": one_of_a_kind_bread_chance + (one_of_a_kind_bread_chance * 0.4),
        "tax_ratio": 0.66,
        "drop_cooldown": drop_cooldown_min - 1
    },
    {# starts at 5,000 breadcoin
        "max": 20000,
        "name": "Wholesale Bakery",
        "one_of_a_kind_droprate": one_of_a_kind_bread_chance + (one_of_a_kind_bread_chance * 0.8),
        "tax_ratio": 0.33,
        "drop_cooldown": drop_cooldown_min - 2
    },
    {# starts at 20,000 breadcoin
        "max": 0,
        "name": "Commercial Bakery",
        "one_of_a_kind_droprate": one_of_a_kind_bread_chance + (one_of_a_kind_bread_chance * 1.2),
        "tax_ratio": 0,
        "drop_cooldown": drop_cooldown_min - 3
    }
]

class Server():
    def __init__(self, server):
        for k,v in server.items():
            setattr(self, k, v)
        self.id = server.get('id', None)
        self.blacklist = server.get('blacklist', [])
        self.prefix = server.get('prefix', 'pan ')
        self.tax = server.get('tax', round(random.random() * 0.2, 2))
        self.money = server.get('money', 0)
        level = self.get_level()
        self.name = level.get('name', None)
        self.one_of_a_kind_bread_chance = level.get('one_of_a_kind_droprate', one_of_a_kind_bread_chance)
        self.tax *= level.get('tax_ratio', 1)
        self.drop_cooldown_min = level.get('drop_cooldown', drop_cooldown_min)
        i = guild_money_levels.index(level)
        if i >= len(guild_money_levels) - 1:
            self.money_until_next_level = None
            self.next_level = None
        else:
            self.money_until_next_level = level['max'] - self.money
            self.next_level = guild_money_levels[i + 1]
    
    def update(self, change):
        after = SERVERS.find_one_and_update({'id': self.id}, change, return_document=pymongo.ReturnDocument.AFTER)
        self.__init__(after)
    
    def get_level(self):
        for _ in guild_money_levels:
            if self.money < _['max']:
                return _
        return guild_money_levels[len(guild_money_levels) - 1]
    
    def add_money(self, amount):
        self.update({'$inc': {'money': amount}})

    def create_bread(bread):
        random.seed()
        bread = {
            'index': breads.index(bread),
            'quality': random.randint(1, 5),
            'created': datetime.datetime.utcnow(),
            'uuid': str(uuid.uuid4())
        }
        if random.random() <= self.one_of_a_kind_bread_chance:
            bread['special'] = gen_bread_id()
        return bread

current_collectables = [
    {'index': 6, 'price': 1500},
    {'index': 2, 'price': 750},
    {'index': 4, 'price': 750}
]

badges = [
    {
        'name': "Bread Hunter",
        'emoji': "<:BreatHunter:815484321573896212>"
    },
    {
        'name': "Hype Bread",
        'emoji': "<:BreadHype:815484321711521813>"
    },
    {
        'name': "Bread Cap",
        'emoji': "<:BreadCap:815775727084765216>"
    },
    {
        'name': "Bread Developer",
        'emoji': "<:BreadStaff:815484321590804491>"
    },
    {
        'name': "Magic Bread",
        'emoji': "<:BreadWand:816044739966140426>"
    },
    {
        'name': "Bread Love",
        'emoji': "<:BreadHeart:816044739865346068>"
    },
    {
        'name': "Star Bread",
        'emoji': "<:BreadStars:815776828932358204>"
    },
    {
        'name': "Bread Booster",
        'emoji': "<:BreadBooster:815484321371783229>"
    }
]

breads = [
    {
        "name": "White Bread",
        "emoji": "<:white_bread:819129168850583552>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 20,
        "plural_name": "White Bread",
        "volitility": 0.5,
        "bake_time": 35,
        "image": "https://i.imgur.com/ZAyk2Te.png",
        "description": "White bread typically refers to breads made from wheat flour from which the bran and the germ layers have been removed from the whole wheatberry as part of the flour grinding or milling process, producing a light-colored flour."
    },
    {
        "name": "Whole Wheat",
        "emoji": "<:whole_wheat:819131214594048030>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 17,
        "plural_name": "Whole Wheat",
        "volitility": 0.5,
        "bake_time": 30,
        "image": "https://i.imgur.com/ytSQ8Jb.png",
        "description": "Whole wheat bread or wholemeal bread is a type of bread made using flour that is partly or entirely milled from whole or almost-whole wheat grains, see whole-wheat flour and whole grain. It is one kind of brown bread."
    },
    {
        "name": "Toast",
        "emoji": "<:toast:819129414793166868>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 5,
        "plural_name": "Toasts",
        "volitility": 0.8,
        "bake_time": 5,
        "image": "https://i.imgur.com/Aw3he0x.png",
        "description": "Toast is bread that has been browned by exposure to radiant heat. The browning is the result of a Maillard reaction, altering the flavor of the bread and making it firmer so that it is easier to spread toppings on it."
    },
    {
        "name": "Banana Bread",
        "emoji": "<:banana_bread:819131489433419817>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 31,
        "plural_name": "Banana Bread",
        "volitility": 0.4,
        "bake_time": 60,
        "image": "https://i.imgur.com/k2syNWa.png",
        "description": "Banana bread is a type of bread made from mashed bananas. It is often a moist, sweet, cake-like quick bread; however there are some banana bread recipes that are traditional-style raised breads."
    },
    {
        "name": "Baguette",
        "emoji": "<:baguette:819131667037159464>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 25,
        "plural_name": "Baguettes",
        "volitility": 0.3,
        "bake_time": 30,
        "image": "https://i.imgur.com/S374hRf.png",
        "description": "A baguette is a long, thin loaf of French bread that is commonly made from basic lean dough. It is distinguishable by its length and crisp crust. A baguette has a diameter of about 5 to 6 centimetres and a usual length of about 65 cm, although a baguette can be up to 1 m long."
    },
    {
        "name": "Pita Bread",
        "emoji": "<:pita_bread:819131735010574337>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 10,
        "plural_name": "Pita Bread",
        "volitility": 0.5,
        "bake_time": 15,
        "image": "https://i.imgur.com/B9bc9YV.png",
        "description": "Pita or pitta, is a family of yeast-leavened round flatbreads baked from wheat flour, common in the Mediterranean, Middle East, and neighboring areas."
    },
    {
        "name": "Sourdough Bread",
        "emoji": "<:sourdough_bread:819131758300627014>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 91,
        "plural_name": "Sourdough Bread",
        "volitility": 0.2,
        "bake_time": 120,
        "image": "https://i.imgur.com/K7ZhxD4.png",
        "description": "Sourdough bread is made by the fermentation of dough using naturally occurring lactobacilli and yeast. The lactic acid produced by the lactobacilli gives it a more sour taste and improved keeping qualities."
    },
    {
        "name": "Bagel",
        "emoji": "<:bagel:819131780820107264>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 13,
        "plural_name": "Bagels",
        "volitility": 0.4,
        "bake_time": 35,
        "image": "https://i.imgur.com/CtxrhUn.png",
        "description": "A bagel, also historically spelled beigel, is a bread product originating in the Jewish communities of Poland. It is traditionally shaped by hand into the form of a ring from yeasted wheat dough, roughly hand-sized, that is first boiled for a short time in water and then baked."
    },
    {
        "name": "Melonpan",
        "emoji": "<:melonpan:819131804178055179>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 45,
        "plural_name": "Melonpan",
        "volitility": 0.45,
        "bake_time": 30,
        "image": "https://i.imgur.com/WWcYes4.png",
        "description": "A melonpan is a type of sweet bun from Japan, that is also popular in Taiwan and China. They are made from an enriched dough covered in a thin layer of crisp cookie dough. Their appearance resembles a melon, such as a rock melon."
    },
    {
        "name": "Garlic Bread",
        "emoji": "<:garlic_bread:819131821094338611>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 11,
        "plural_name": "Garlic Bread",
        "volitility": 0.5,
        "bake_time": 15,
        "image": "https://i.imgur.com/3am3Q5H.png",
        "description": "Garlic bread consists of bread, topped with garlic and olive oil or butter and may include additional herbs, such as oregano or chives. It is then either grilled or broiled until toasted or baked in a conventional or bread oven."
    },
    {
        "name": "Blueberry Muffin",
        "emoji": "<:blueberry_muffin:819132025176850445>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 16,
        "plural_name": "Blueberry Muffins",
        "volitility": 0.3,
        "bake_time": 24,
        "image": "https://i.imgur.com/jnHigb4.png",
        "description": "A muffin is an individual-sized, baked product. It can refer to two distinct items, a part-raised flatbread that is baked and then cooked on a griddle and a cupcake-like quickbread that is chemically leavened and then baked in a mold."
    },
    {
        "name": "Chocolate Muffin",
        "emoji": "<:chocolate_muffin:819132090820853760>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 16,
        "plural_name": "Chocolate Muffins",
        "volitility": 0.8,
        "bake_time": 24,
        "image": "https://i.imgur.com/efw2edL.png",
        "description": "A muffin is an individual-sized, baked product. It can refer to two distinct items, a part-raised flatbread that is baked and then cooked on a griddle and a cupcake-like quickbread that is chemically leavened and then baked in a mold."
    },
    {
        "name": "Charcoal",
        "emoji": "<:charcoal:819132229044928552>",
        "bakeable": False,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 1,
        "plural_name": "Charcoal",
        "volitility": 5,
        "bake_time": None,
        "image": "https://i.imgur.com/TNdRcis.png",
        "description": "Charcoal is a lightweight black carbon residue produced by strongly heating wood (or other animal and plant materials) in minimal oxygen to remove all water and volatile constituents. Created when bread burns."
    },
    {
        "name": "Brioche",
        "emoji": "<:brioche:819132331977736213>",
        "bakeable": False,
        "special": True,
        "sellable": True,
        "buyable": True,
        "price": 153,
        "plural_name": "Brioche",
        "volitility": 0.5,
        "bake_time": None,
        "image": "https://i.imgur.com/9JMqhd2.png",
        "description": "Brioche is a bread of French origin and whose high egg and butter content gives it a rich and tender crumb. Can only be obtained from bread drops in active channels."
    },
    {
        "name": "BreadBox",
        "emoji": "<:breadbox:819132627843416074>",
        "bakeable": False,
        "special": True,
        "sellable": False,
        "buyable": True,
        "price": 50,
        "plural_name": "BreadBoxes",
        "volitility": 0.5,
        "bake_time": None,
        "image": "https://i.imgur.com/7Vl2q0y.png",
        "description": "A container that holds bread. Can be opened with 'pan open'"
    },
    {
        "name": "English Muffin",
        "emoji": "<:english_muffin:819393900652396604>",
        "bakeable": True,
        "special": False,
        "sellable": True,
        "buyable": True,
        "price": 13,
        "plural_name": "English Muffins",
        "volitility": 0.5,
        "bake_time": 10,
        "image": "https://i.imgur.com/1X3fRCD.png",
        "description": "Small, round, thin, usually dusted with cornmeal and served split horizontally, toasted, buttered, eaten as a snack alone or part of meal, usually breakfast or, in the UK and Ireland, early-evening tea."
    }
]
