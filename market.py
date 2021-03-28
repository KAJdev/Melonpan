import numpy as np
import datetime
import random
import math
from perlin_noise import PerlinNoise
import matplotlib
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline, BSpline

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

    def get_graph(self, days):
        prices = []
        for _ in range(1, 60):
            day = get_day_of_year() - _
            if day <= 0:
                day += 365
            prices.append(int(self.get_price(day)))
        prices.append(int(self.get_price(get_day_of_year_active())))

        fig, ax = plt.subplots(figsize=(8, 2),frameon=False)
        plt.text(60, prices[len(prices) - 1], " Price", fontsize=14, color=(224/255, 1, 186/255))
        #ax.axis('off')
        fig.patch.set_visible(False)

        x = np.array(list(range(1, 61)))
        y = np.array(prices)

        #define x as 200 equally spaced values between the min and max of original x
        xnew = np.linspace(x.min(), x.max(), 125)

        #define spline
        spl = make_interp_spline(x, y, k=3)
        y_smooth = spl(xnew)

        ax.plot(xnew, y_smooth, color=(224/255, 1, 186/255))
        #ax.plot(x, y)

        ax.spines["top"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.yaxis.label.set_color('white')
        ax.xaxis.label.set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')

        return fig