from datamodel import OrderDepth, TradingState, Order

POSITION_LIMITS = {"INTARIAN_PEPPER_ROOT": 80, "ASH_COATED_OSMIUM": 80,}

OSMIUM_FAIR = 10000
OSMIUM_SPREAD = 3
OSMIUM_STD = 5.0    # empirical std: chart range ±20 ticks → std ≈ 5
OSMIUM_BASE_SIZE = 10
OSMIUM_MAX_SIZE = 40
OSMIUM_MAX_SKEW = 5  # max price shift from inventory skewing

class Trader:

    def bid(self):
        return 11

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
        if buy_capacity <= 0 or not od.sell_orders:
            return orders
        # Walk the ask book aggressively — spread is wide (~15 ticks) so passive bids never fill
        # in a trending market. Cost of 1 tick saved is dwarfed by the daily +1000 drift.
        for ask_price, ask_vol in sorted(od.sell_orders.items()):
            if buy_capacity <= 0:
                break
            qty = min(-ask_vol, buy_capacity)
            orders.append(Order("INTARIAN_PEPPER_ROOT", ask_price, qty))
            buy_capacity -= qty
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

        # Take liquidity aggressively when price crosses our passive levels — walk the book
        if od.sell_orders and buy_capacity > 0:
            for ask_price, ask_vol in sorted(od.sell_orders.items()):
                if ask_price > passive_bid:
                    break
                qty = min(-ask_vol, buy_capacity)
                orders.append(Order("ASH_COATED_OSMIUM", ask_price, qty))
                buy_capacity -= qty

        if od.buy_orders and sell_capacity > 0:
            for bid_price, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_price < passive_ask:
                    break
                qty = min(bid_vol, sell_capacity)
                orders.append(Order("ASH_COATED_OSMIUM", bid_price, -qty))
                sell_capacity -= qty

        # Passive quotes (z-score sized, inventory skewed)
        if buy_capacity > 0:
            orders.append(Order("ASH_COATED_OSMIUM", passive_bid, min(quote_size, buy_capacity)))

        if sell_capacity > 0:
            orders.append(Order("ASH_COATED_OSMIUM", passive_ask, -min(quote_size, sell_capacity)))

        return orders

    

