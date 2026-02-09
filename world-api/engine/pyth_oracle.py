"""
Pyth Network Oracle - Real-time MON/USD price feed.

Fetches MON/USD from Pyth Hermes API and applies price effects to in-game market.

How it works:
  1. At game start, fetch MON/USD and store as baseline
  2. Each tick, compare current price to baseline
  3. Amplify the change with per-resource sensitivity (30x-100x)
  4. Clamp: prices can rise to 3x or drop to 25% of starting value
  5. Stack on top of supply/demand and event effects

Sensitivity rationale:
  - Fish (100x): Perishable, highly speculative
  - Iron (60x):  Industrial, moderate correlation
  - Wood (30x):  Construction, stable commodity
"""
import os
import time
import requests
from typing import Optional, Dict


# Pyth MON/USD feed ID (mainnet)
MON_USD_FEED_ID = "31491744e2dbf6df7fcf4ac0820d18a609b49076d45066d3568424e62f686cd1"
PYTH_HERMES_URL = "https://hermes.pyth.network"

# Per-resource sensitivity amplifiers
RESOURCE_SENSITIVITY = {
    "fish": 100,   # Perishable, highly speculative
    "iron": 60,    # Industrial, moderate correlation
    "wood": 30,    # Construction, stable commodity
}

# Price effect clamp: min 0.25x, max 3.0x of base price
EFFECT_MIN = 0.25
EFFECT_MAX = 3.0


class PythPriceFeed:
    """
    Fetch real-time MON/USD price from Pyth Network.
    Used to make in-game market prices react to real-world MON price movements.
    """

    def __init__(self):
        self._cached_price: Optional[float] = None
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 30.0  # seconds
        self.baseline_price: Optional[float] = None
        self._initialized = False

    def get_mon_usd_price(self) -> Optional[float]:
        """Fetch current MON/USD price from Pyth Hermes API."""
        now = time.time()

        # Return cached if fresh
        if self._cached_price and (now - self._cache_timestamp) < self._cache_ttl:
            return self._cached_price

        try:
            url = (
                f"{PYTH_HERMES_URL}/v2/updates/price/latest"
                f"?ids[]={MON_USD_FEED_ID}"
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("parsed") and len(data["parsed"]) > 0:
                price_data = data["parsed"][0]["price"]
                price = int(price_data["price"]) * (10 ** int(price_data["expo"]))
                self._cached_price = price
                self._cache_timestamp = now

                # Set baseline on first successful fetch
                if not self._initialized:
                    self.baseline_price = price
                    self._initialized = True
                    print(f"[Pyth] Baseline MON/USD: ${price:.4f}")

                return price

        except Exception as e:
            print(f"[Pyth] Price fetch error: {e}")

        return self._cached_price  # Return stale on error

    def get_price_effects(self) -> Dict[str, float]:
        """
        Calculate per-resource price multipliers based on MON/USD change.

        Returns dict like: {"fish": 1.15, "iron": 1.09, "wood": 1.03}
        A multiplier of 1.0 = no effect, >1.0 = price up, <1.0 = price down.
        """
        current = self.get_mon_usd_price()
        if not current or not self.baseline_price:
            return {r: 1.0 for r in RESOURCE_SENSITIVITY}

        # Percentage change from baseline
        pct_change = (current - self.baseline_price) / self.baseline_price

        effects = {}
        for resource, sensitivity in RESOURCE_SENSITIVITY.items():
            # Amplify the change
            amplified = 1.0 + (pct_change * sensitivity)
            # Clamp
            amplified = max(EFFECT_MIN, min(EFFECT_MAX, amplified))
            effects[resource] = round(amplified, 4)

        return effects

    def get_status(self) -> dict:
        """Get oracle status for debugging/display."""
        current = self.get_mon_usd_price()
        change_pct = 0.0
        if current and self.baseline_price:
            change_pct = ((current - self.baseline_price) / self.baseline_price) * 100
        return {
            "mon_usd": current,
            "baseline": self.baseline_price,
            "change_pct": round(change_pct, 4),
            "effects": self.get_price_effects(),
            "initialized": self._initialized,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_pyth_feed: Optional[PythPriceFeed] = None


def get_pyth_feed() -> PythPriceFeed:
    """Get PythPriceFeed singleton."""
    global _pyth_feed
    if _pyth_feed is None:
        _pyth_feed = PythPriceFeed()
    return _pyth_feed
