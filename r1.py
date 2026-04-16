import numpy as np
from collections import deque
import pandas as pd

prices = ["prices0.csv", "prices1.csv", "prices2.csv"]
trades = ["trades0.csv", "trades1.csv", "trades2.csv"]

class Engine():
    def __init__(self, name: str, prices: list[str]) -> None:
        self.name = name
        self.prices = prices
    
    def get_data(self) -> None:
        df = pd.dataframe(prices[0])
