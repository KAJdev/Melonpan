import numpy as np
import datetime
import random
import math

def get_day_of_year():
    return datetime.datetime.now().timetuple().tm_yday

class ItemPrice():

    def __init__(self, initial, volatilty, seed):
        self.i = initial  # Item default price
        self.current = initial  # Item default price
        #self.interest = interest
        self.v = volatilty
        self.seed = seed
        self.cache = []

    def get_price(self, time):
        # np.random.seed(self.seed)
        # day_year = np.sqrt(1./365.)
        # inner_expression = (self.interest - 0.5 * self.volatilty ** 2) * day_year
        # self.current *= np.prod(np.exp(np.random.normal(0, 1, time) * self.volatilty * day_year + inner_expression))
        random.seed(self.seed)
        s = math.sin((time * 2) + random.random())
        random.seed(s)
        s += random.random() * self.v
        self.current = self.i + s

        return self.current

    def get_graph(self, time):
        pass