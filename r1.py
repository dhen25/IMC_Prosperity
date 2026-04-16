#from datamodel import OrderDepth, UserID, TradingState, Order
import numpy as np
from collections import deque
import pandas as pd
import matplotlib.pyplot as plt

prices = ["prices0.csv", "prices1.csv", "prices2.csv"]
trades = ["trades0.csv", "trades1.csv", "trades2.csv"]

class Engine():
    def __init__(self, name: str, prices: list[str]) -> None:
        self.name = name
        self.prices = prices
    
    def get_data(self) -> None:
        self.df = pd.read_csv(self.prices[0], sep=';')
        print(self.df.describe())
    
    def show_price_history(self) -> None:
        self.df[self.df["product"] == "INTARIAN_PEPPER_ROOT"].plot(x="timestamp", y="mid_price")
        self.df[self.df["product"] == "ASH_COATED_OSMIUM"].plot(x="timestamp", y="mid_price")
    
    def get_best_bid_ask(self) -> tuple[int, int]:
        best_bid = best_ask = None


engine = Engine("Engine", prices)
engine.get_data()
engine.show_price_history()
plt.show()


