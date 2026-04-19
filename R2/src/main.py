import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
test_dir = os.path.join(script_dir, "..", "test")
prices0_file = os.path.join(test_dir, "prices0.csv")
prices1_file = os.path.join(test_dir, "prices1.csv")
prices2_file = os.path.join(test_dir, "prices2.csv")
trades0_file = os.path.join(test_dir, "trades0.csv")
trades1_file = os.path.join(test_dir, "trades1.csv")
trades2_file = os.path.join(test_dir, "trades2.csv")

params = [prices0_file, prices1_file, prices2_file, trades0_file, trades1_file, trades2_file,]

class BackTester:

    def __init__(self, *params):
        self.prices = params[:3]
        self.trades = params[3:]
    
    def show_trends(self):
        """
        View pricing history of osmium or pepper root
        """
        self.dfs = []
        for i, f in enumerate(self.prices):
            self.df = pd.read_csv(f, sep=";")
            # make timestamp globally continuous: offset by 1_000_000 per day slot
            self.df["timestamp"] = self.df["timestamp"] + i * 1_000_000
            self.dfs.append(self.df)
        self.dfs = pd.concat(self.dfs, ignore_index=True)
        self.dfs = self.dfs[self.dfs["mid_price"] != 0]
        print(self.dfs)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6)) 
        self.dfs[self.dfs["product"] == "INTARIAN_PEPPER_ROOT"].plot(x="timestamp", y="mid_price", ax=ax1, legend=False)
        ax1.set_xlabel("timestamp")
        ax1.set_ylabel("mid_price")
        ax1.set_title("INTARIAN_PEPPER_ROOT")
        self.dfs[self.dfs["product"] == "ASH_COATED_OSMIUM"].plot(x="timestamp", y="mid_price", ax=ax2, legend=False)
        ax2.set_xlabel("timestamp")
        ax2.set_ylabel("ASH_COATED_OSMIUM")
        plt.tight_layout()
        plt.show()
        return dfs

backtest = BackTester(prices0_file, prices1_file, prices2_file, trades0_file, trades1_file, trades2_file)
backtest.show_trends()


from datamodel import OrderDepth, TradingState, Order

POSITION_LIMITS = {"INTARIAN_PEPPER_ROOT": 80, "ASH_COATED_OSMIUM": 80,}

OSMIUM_FAIR = 10000
OSMIUM_SPREAD = 2
OSMIUM_STD = 8.0    # historical std: range ~9977-10023, ~(46/6)
OSMIUM_BASE_SIZE = 10
OSMIUM_MAX_SIZE = 40
OSMIUM_MAX_SKEW = 3  # max price shift from inventory skewing

class Trader:

    def bid(self):
        pass

    def run(self, state: TradingState):
        result = {}
        for product in state.order_depths:
            try:
                od = state.order_depths[product]
                pos = state.position.get(product, 0)
                limit = POSITION_LIMITS.get(product, 80)

                if product == "INTARIAN_PEPPER_ROOT":
                    result[product] = self._pepper_orders(od, pos, limit)
                elif product == "ASH_COATED_OSMIUM":
                    result[product] = self._osmium_orders(od, pos, limit)
            except Exception as e:
                print(f"Error on {product}: {e}")

        return result, 0, ""
    
    def _pepper_orders(self, od, pos, limit):
        """Always hold max long — price trends up ~1000/day, never sell."""
        orders = []
        buy_capacity = limit - pos
        if buy_capacity > 0 and od.sell_orders:
            best_ask, best_ask_vol = min(od.sell_orders.items())
            qty = min(-best_ask_vol, buy_capacity)
            orders.append(Order("INTARIAN_PEPPER_ROOT", best_ask, qty))
        return orders

    def _osmium_orders(self, od, pos, limit):
        """Mean-reverts around 10000. Take extreme liquidity + skewed market making."""
        orders = []
        buy_capacity = limit - pos
        sell_capacity = limit + pos

        # Mid price for z-score (fall back to fair if one side missing)
        if od.buy_orders and od.sell_orders:
            mid = (max(od.buy_orders) + min(od.sell_orders)) / 2
        elif od.buy_orders:
            mid = max(od.buy_orders)
        elif od.sell_orders:
            mid = min(od.sell_orders)
        else:
            mid = OSMIUM_FAIR

        # Z-score: scale quote size up when price is far from fair (stronger signal)
        z = abs(mid - OSMIUM_FAIR) / OSMIUM_STD
        quote_size = min(int(OSMIUM_BASE_SIZE * (1 + z)), OSMIUM_MAX_SIZE)

        # Inventory skew: shift both quotes down when long, up when short
        # so the side that unwinds the position becomes more attractive to bots
        skew = (pos / limit) * OSMIUM_MAX_SKEW

        passive_bid = round(OSMIUM_FAIR - OSMIUM_SPREAD - skew)
        passive_ask = round(OSMIUM_FAIR + OSMIUM_SPREAD - skew)

        # Take liquidity aggressively when price crosses our passive levels
        if od.sell_orders and buy_capacity > 0:
            best_ask, best_ask_vol = min(od.sell_orders.items())
            if best_ask <= passive_bid:
                orders.append(Order("ASH_COATED_OSMIUM", best_ask, min(-best_ask_vol, buy_capacity)))

        if od.buy_orders and sell_capacity > 0:
            best_bid, best_bid_vol = max(od.buy_orders.items())
            if best_bid >= passive_ask:
                orders.append(Order("ASH_COATED_OSMIUM", best_bid, -min(best_bid_vol, sell_capacity)))

        # Passive quotes (z-score sized, inventory skewed)
        if buy_capacity > 0:
            orders.append(Order("ASH_COATED_OSMIUM", passive_bid, min(quote_size, buy_capacity)))

        if sell_capacity > 0:
            orders.append(Order("ASH_COATED_OSMIUM", passive_ask, -min(quote_size, sell_capacity)))

        return orders

    

