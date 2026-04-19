#from datamodel import OrderDepth, TradingState, Order
import pandas as pd
import matplotlib.pyplot
import numpy as np

prices = ["../test/prices0.csv", "../test/prices1.csv", "../test/prices2.csv"]
trades = ["..test/trades0.csv", "../test/trades1.csv", "../test/trades2.csv"]

class Trader:

    def __init__(self, prices, trades):
        self.prices = prices
        self.trades = trades
    
    def run(self):
        result = {}

    def bid(self):
        pass

    def show_trend(self):
        self.df = pd.read_csv(self.prices[0], sep=";")

    
