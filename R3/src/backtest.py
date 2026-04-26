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
        View pricing history of hydrogel, velvetfruit or VEV
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

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 6)) 
        self.dfs[self.dfs["product"] == "HYDROGEL_PACK"].plot(x="timestamp", y="mid_price", ax=ax1, legend=False)
        ax1.set_xlabel("timestamp")
        ax1.set_ylabel("mid_price")
        ax1.set_title("HYDROGEL_PACK")
        #ax1.set_ylim(12000, 12010)
        #ax1.set_xlim(1e6, 1.01e6)
        #ax1.set_xticks([1000000 + n*100 for n in range(101)])
        
        #self.dfs[self.dfs["product"] == "VEV_4000"].plot(x="timestamp", y="mid_price", ax=ax2, legend="4000")
        #self.dfs[self.dfs["product"] == "VEV_4500"].plot(x="timestamp", y="mid_price", ax=ax2, legend="4500")
        self.dfs[self.dfs["product"] == "VEV_5000"].plot(x="timestamp", y="mid_price", ax=ax2, legend="5000")
        ax2.set_xlabel("timestamp")
        ax2.set_ylabel("VEV")
        ax2.set_title("VEV")

        self.dfs[self.dfs["product"] == "VELVETFRUIT_EXTRACT"].plot(x="timestamp", y="mid_price", ax=ax3, legend=False)
        ax3.set_xlabel("timestamp")
        ax3.set_ylabel("mid_price")
        ax3.set_title("VELVETFRUIT_EXTRACT")

        plt.tight_layout()
        plt.show()
        return None

backtest = BackTester(prices0_file, prices1_file, prices2_file, trades0_file, trades1_file, trades2_file)
backtest.show_trends()

