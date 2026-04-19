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
    
    def show_trends(self) -> None:
        """
        View pricing history of osmium or pepper root
        """
        self.dfs = []
        for i, f in enumerate(self.prices):
            self.df = pd.read_csv(f, sep=";")
            # join historical data CSVs to continuous time series
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
        return None

backtest = BackTester(prices0_file, prices1_file, prices2_file, trades0_file, trades1_file, trades2_file)
backtest.show_trends()

