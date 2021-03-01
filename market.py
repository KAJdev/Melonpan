import numpy as np
import time
import random
import math
from perlin_noise import PerlinNoise

class ItemPrice():

    def __init__(self, initial, volatilty, seed):
        self.i = initial  # Item default price
        self.current = initial  # Item default price
        self.v = volatilty/10
        self.seed = seed
        self.cache = []

    def get_price(self, time=time.time()):
        # s = math.sin((time * 2) + random.random())
        random.seed(self.seed)
        # s += random.random() * self.v
        # self.current = self.i + s
        noise = PerlinNoise(octaves=10, seed=self.seed)
        return int(((noise(time/1000) + 1.5) / 2) * self.i * (random.random() * self.v * self.i))