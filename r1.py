#from datamodel import OrderDepth, UserID, TradingState, Order
import numpy as np
from collections import deque
import pandas as pd
import matplotlib.pyplot as plt

prices = ["prices0.csv", "prices1.csv", "prices2.csv"]
trades = ["trades0.csv", "trades1.csv", "trades2.csv"]

class Trader:
    
    def bid(self):
        pass
    
    def run(self, state):
        
        POSITION_LIMIT = 80
        result = {}
        # program goes here

        #print("traderData: " + state.traderData)
        #print("Observations: " + str(state.observations))
        for product in state.order_depths: # key = product
            order_depth = state.order_depths[product] # value = order_depth
            orders = []

            # build long positions
            if len(order_depth.sell_orders) != 0: # i.e. if there are buyers
                # buy logic for osmium
                pass
                # buy logic for peppers
            
            if len(order_depth.buy_orders) != 0: # i.e. if there are sellers
                # sell logic for osmium
                pass
                # sell logic for peppers
                pass
        
            result[product] = orders
    """
    inherited subclasses of TradingState to use are: 
    OrderDepth -> access via state.order_depths
    Observations -> access via state.observations
    traderData (str) ?

    
    """
    def get_data(self) -> None:
        self.df = pd.read_csv(self.prices[0], sep=';')
        self.df=  self.df[self.df["mid_price"] != 0]
        print(self.df.describe())
    
    def show_price_history(self) -> None:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
        self.df[self.df["product"] == "INTARIAN_PEPPER_ROOT"].plot(x="timestamp", y="mid_price", ax=ax1, legend=False)
        ax1.set_ylabel("Pepper (stable)")
        ax1.set_title("INTARIAN_PEPPER_ROOT")
        self.df[self.df["product"] == "ASH_COATED_OSMIUM"].plot(x="timestamp", y="mid_price", ax=ax2, legend=False)
        ax2.set_ylabel("Osmium (unstable)")
        ax2.set_title("ASH_COATED_OSMIUM")
        plt.tight_layout()
    def get_best_bid_ask(self) -> tuple[int, int]:
        best_bid = best_ask = None


engine = Trader("Engine", prices)
engine.get_data()
engine.show_price_history()
plt.show()


"""
Supported libraries:

pandas, numpy, statistics, math, typing, jsonpickle
"""