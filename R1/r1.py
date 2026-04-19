from datamodel import OrderDepth, TradingState, Order

POSITION_LIMITS = {
    "INTARIAN_PEPPER_ROOT": 80,
    "ASH_COATED_OSMIUM": 80,
}

OSMIUM_FAIR = 10000
OSMIUM_SPREAD = 2
OSMIUM_STD = 8.0    # historical std: range ~9977-10023, ~(46/6)
OSMIUM_BASE_SIZE = 10
OSMIUM_MAX_SIZE = 40
OSMIUM_MAX_SKEW = 3  # max price shift from inventory skewing


class Trader:

    def bid(self):
        pass

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

