from datamodel import OrderDepth, TradingState, Order
import math
from collections import deque

# ── Black-Scholes (stdlib only) ──────────────────────────────────────────────

def _ncdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def bs_call(S: float, K: float, T: float, sigma: float) -> float:
    """European call price (r = 0)."""
    if T < 1e-9:
        return max(S - K, 0.0)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * _ncdf(d1) - K * _ncdf(d2)

# ── Calibrated constants ─────────────────────────────────────────────────────

# Vol smile parabola: IV(m) = A·m² + B·m + C  where m = ln(S/K)
# Fitted from 3 days of historical data using dynamic TTE (TTE decreases within day).
_SMILE_A =  0.086624
_SMILE_B = -0.000768
_SMILE_C =  0.012537

# Per-strike IV bias corrections (mean IV_observed − IV_smile for each strike).
# VEV_5400 is systematically cheap (~−0.061% vol); others are small or slightly rich.
_STRIKE_BIAS = {
    5000: -0.000041,
    5100: -0.000044,
    5200:  0.000146,
    5300:  0.000270,
    5400: -0.000609,
    5500:  0.000278,
}

def smile_iv(S: float, K: float) -> float:
    """Smile-adjusted implied vol for strike K given spot S."""
    m = math.log(S / K)
    base = _SMILE_A * m * m + _SMILE_B * m + _SMILE_C
    return max(base + _STRIKE_BIAS.get(K, 0.0), 1e-6)

def smile_fair(S: float, K: float, T: float) -> float:
    return bs_call(S, K, T, smile_iv(S, K))

# ── Position limits ──────────────────────────────────────────────────────────

_STRIKES = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]
_ACTIVE_STRIKES = {5000, 5100, 5200, 5300, 5400, 5500}

POSITION_LIMITS = {
    'HYDROGEL_PACK': 200,
    'VELVETFRUIT_EXTRACT': 200,
    **{f'VEV_{k}': 300 for k in _STRIKES},
}

# ── Mean-reversion EMA parameters (calibrated from historical data) ──────────
# Both products show negative lag-1 autocorrelation (HYDROGEL −0.13, VEV −0.16)
# and empirical half-lives of ~300 ticks (timestamps spaced 100 apart).
# EMA time constant: 300 ticks → α = exp(−1/300) ≈ 0.9967.
# Rolling-vol window: 50 ticks.

_EMA_ALPHA_HYD = 0.9967   # HYDROGEL: half-life 300 ticks
_EMA_ALPHA_VEV = 0.9964   # VEV:       half-life 279 ticks
_ROLLING_WINDOW = 50

# Market-making quote parameters
_MM_SPREAD_HYD = 3        # half-spread for HYDROGEL passive quotes
_MM_SPREAD_VEV = 2        # half-spread for VEV passive quotes
_MM_BASE_SIZE = 10
_MM_MAX_SIZE = 40
_MM_MAX_SKEW = 4          # max inventory-skew ticks

# Option scalping: take aggressively if price deviates > TAKE_THRESH from smile fair
_OPT_TAKE_THRESH = 0.75   # ticks
_OPT_PASSIVE_SPREAD = 1   # tick on each side of smile fair for passive quotes
_OPT_PASSIVE_SIZE = 15

# TTE constants for Round 3
_TTE_START = 5.0           # TTE at timestamp 0 of round 3
_TICKS_PER_DAY = 1_000_000  # 10 000 obs × 100 timestamp units each


# ── Helper ───────────────────────────────────────────────────────────────────

def _mid(od: OrderDepth):
    if od.buy_orders and od.sell_orders:
        return (max(od.buy_orders) + min(od.sell_orders)) / 2.0
    if od.buy_orders:
        return float(max(od.buy_orders))
    if od.sell_orders:
        return float(min(od.sell_orders))
    return None


# ── Trader ───────────────────────────────────────────────────────────────────

class Trader:

    def __init__(self):
        # EMA fair values (seeded lazily on first observation)
        self._vev_ema: float | None = None
        self._hyd_ema: float | None = None

        # Rolling price buffers for volatility estimation
        self._vev_buf: deque = deque(maxlen=_ROLLING_WINDOW)
        self._hyd_buf: deque = deque(maxlen=_ROLLING_WINDOW)

        # Last mid prices (to compute tick returns)
        self._vev_last: float | None = None
        self._hyd_last: float | None = None

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self, state: TradingState):
        result = {}

        # TTE decreases from 5 to ~4 across the 10 000 ticks of round 3
        tte = max(_TTE_START - state.timestamp / _TICKS_PER_DAY, 0.01)

        vev_od = state.order_depths.get('VELVETFRUIT_EXTRACT')
        hyd_od = state.order_depths.get('HYDROGEL_PACK')

        # Update EMAs and rolling-vol buffers
        vev_mid = _mid(vev_od) if vev_od else None
        hyd_mid = _mid(hyd_od) if hyd_od else None

        if vev_mid is not None:
            if self._vev_ema is None:
                self._vev_ema = vev_mid
            else:
                if self._vev_last is not None:
                    self._vev_buf.append(vev_mid - self._vev_last)
                self._vev_ema = _EMA_ALPHA_VEV * self._vev_ema + (1 - _EMA_ALPHA_VEV) * vev_mid
            self._vev_last = vev_mid

        if hyd_mid is not None:
            if self._hyd_ema is None:
                self._hyd_ema = hyd_mid
            else:
                if self._hyd_last is not None:
                    self._hyd_buf.append(hyd_mid - self._hyd_last)
                self._hyd_ema = _EMA_ALPHA_HYD * self._hyd_ema + (1 - _EMA_ALPHA_HYD) * hyd_mid
            self._hyd_last = hyd_mid

        vev_fair = self._vev_ema or 5250.0
        hyd_fair = self._hyd_ema or 9990.0

        # Rolling vol (std of tick returns); fall back to historical tick stds
        vev_vol = (max((sum(x*x for x in self._vev_buf)/len(self._vev_buf))**0.5, 0.01)
                   if self._vev_buf else 1.13)
        hyd_vol = (max((sum(x*x for x in self._hyd_buf)/len(self._hyd_buf))**0.5, 0.01)
                   if self._hyd_buf else 2.17)

        # Use raw current mid (not EMA) for instantaneous option pricing
        vev_now = vev_mid or vev_fair

        for product, od in state.order_depths.items():
            pos = state.position.get(product, 0)
            limit = POSITION_LIMITS.get(product, 200)
            try:
                if product == 'HYDROGEL_PACK':
                    result[product] = self._mr_orders(
                        product, od, pos, limit,
                        hyd_fair, hyd_vol, _MM_SPREAD_HYD,
                    )
                elif product == 'VELVETFRUIT_EXTRACT':
                    result[product] = self._mr_orders(
                        product, od, pos, limit,
                        vev_fair, vev_vol, _MM_SPREAD_VEV,
                    )
                elif product in [f'VEV_{k}' for k in _ACTIVE_STRIKES]:
                    k = int(product.split('_')[1])
                    fair = smile_fair(vev_now, k, tte)
                    result[product] = self._option_orders(product, od, pos, limit, fair)
                # VEV_4000/4500: wide spreads (~20 ticks), skip
                # VEV_6000/6500: price ≈ 0, skip
            except Exception:
                pass

        return result, 0, ""

    # ── Mean-reversion market-making (HYDROGEL, VEV) ──────────────────────

    def _mr_orders(self, product, od, pos, limit, fair, vol, spread):
        """
        Quote around the EMA fair value.
        - Inventory skew shifts quotes toward the unwinding side.
        - Z-score (deviation / rolling_vol) scales quote size up on strong signals.
        - Aggressively lift/hit when market crosses our passive levels.
        """
        orders = []
        buy_cap = limit - pos
        sell_cap = limit + pos

        mid = _mid(od)
        z = abs(mid - fair) / max(vol, 0.1) if mid is not None else 1.0

        skew = (pos / limit) * _MM_MAX_SKEW
        bid_px = round(fair - spread - skew)
        ask_px = round(fair + spread - skew)
        size = min(int(_MM_BASE_SIZE * (1.0 + z)), _MM_MAX_SIZE)

        # Aggressive: take if the market offers better than our passive level
        if od.sell_orders and buy_cap > 0:
            for px in sorted(od.sell_orders):
                if px > bid_px:
                    break
                qty = min(-od.sell_orders[px], buy_cap)
                if qty > 0:
                    orders.append(Order(product, px, qty))
                    buy_cap -= qty

        if od.buy_orders and sell_cap > 0:
            for px in sorted(od.buy_orders, reverse=True):
                if px < ask_px:
                    break
                qty = min(od.buy_orders[px], sell_cap)
                if qty > 0:
                    orders.append(Order(product, px, -qty))
                    sell_cap -= qty

        # Passive quotes
        if buy_cap > 0:
            orders.append(Order(product, bid_px, min(size, buy_cap)))
        if sell_cap > 0:
            orders.append(Order(product, ask_px, -min(size, sell_cap)))

        return orders

    # ── Smile-adjusted BS options scalping ────────────────────────────────

    def _option_orders(self, product, od, pos, limit, fair):
        """
        Fair value = BS(spot, K, TTE, smile_iv(spot, K) + per_strike_bias).
        - Take aggressively when market deviates > _OPT_TAKE_THRESH from fair.
        - Post passive quotes at fair ± _OPT_PASSIVE_SPREAD.
        - VEV_5400 is systematically cheap (bias −0.061% vol) so we lean long.
        Positions are liquidated at end of round at approx BS fair value,
        so holding an option near fair incurs no P&L risk from non-expiry.
        """
        orders = []
        buy_cap = limit - pos
        sell_cap = limit + pos

        bid_px = max(round(fair - _OPT_PASSIVE_SPREAD), 1)
        ask_px = round(fair + _OPT_PASSIVE_SPREAD)

        # Aggressive take
        if od.sell_orders and buy_cap > 0:
            best_ask = min(od.sell_orders)
            if best_ask < fair - _OPT_TAKE_THRESH:
                qty = min(-od.sell_orders[best_ask], buy_cap)
                if qty > 0:
                    orders.append(Order(product, best_ask, qty))
                    buy_cap -= qty

        if od.buy_orders and sell_cap > 0:
            best_bid = max(od.buy_orders)
            if best_bid > fair + _OPT_TAKE_THRESH:
                qty = min(od.buy_orders[best_bid], sell_cap)
                if qty > 0:
                    orders.append(Order(product, best_bid, -qty))
                    sell_cap -= qty

        # Passive market-making around smile fair
        if buy_cap > 0 and bid_px >= 1:
            orders.append(Order(product, bid_px, min(_OPT_PASSIVE_SIZE, buy_cap)))
        if sell_cap > 0:
            orders.append(Order(product, ask_px, -min(_OPT_PASSIVE_SIZE, sell_cap)))

        return orders
