import numpy as np
import datetime
import random
import math
from perlin_noise import PerlinNoise

def get_day_of_year():
    return datetime.datetime.now().timetuple().tm_yday

def get_minute_of_year():
    day = get_day_of_year()
    midnight = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    delta = datetime.datetime.utcnow() - midnight
    minute = (delta.total_seconds()/60) * day
    return minute

def get_day_of_year_active():
    day = get_day_of_year()
    midnight = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    delta = datetime.datetime.utcnow() - midnight
    minute = (delta.total_seconds()/60/60/24) + day
    return minute

class ItemPrice():

    def __init__(self, initial, volatilty, seed):
        self.i = initial  # Item default price
        self.c = initial
        self.v = volatilty
        self.s = seed

    def get_price(self, time):
        noise = PerlinNoise(octaves=10, seed=self.s + 1)
        s = (noise(time * 4) - 0.5) * 2
        s *= (self.v * self.i) * 0.5
        self.c = self.i + s

        #self.c = (self.i * 2) * (sum([PerlinNoise(octaves=8**j,seed=j + 69)(i/100)/(3**j) for j in range(10)]) + 0.5)

        if self.c < 1:
            self.c = 1
        return self.c