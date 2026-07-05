#!/usr/bin/env python3
"""
Daily gold rate -> Telegram (KE Jewelry "Gold Rate Daily Update" topic).

Runs on GitHub Actions (no Mac required). It:
  1. Fetches the current gold spot price (USD per troy ounce) from a keyless API.
  2. Computes the price per chi = spot / 31.1035 * 3.75, rounded, + $5 local premium.
  3. Computes the 18K price per chi = local gold price per chi * 0.75  (2 decimals).
  4. Posts a formatted message to the Telegram group topic.

The bot token comes from the GitHub secret TELEGRAM_BOT_TOKEN.
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]                       # required (GitHub secret)
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1002361096127")  # KE Team group
THREAD_ID = os.environ.get("TELEGRAM_THREAD_ID", "48439")       # "Gold Rate Daily Update" topic

GRAMS_PER_OZ = 31.1035
GRAMS_PER_CHI = 3.75
LOCAL_PREMIUM = 5  # local rate = live gold price per chi + $5


def get_spot():
    """Return (usd_per_oz, source_url). Tries multiple keyless sources."""
    sources = [
        ("https://api.gold-api.com/price/XAU", lambda d: float(d["price"])),
        ("https://data-asg.goldprice.org/dbXRates/USD",
         lambda d: float(d["items"][0]["xauPrice"])),
    ]
    last_err = None
    for url, parse in sources:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            price = parse(data)
            if price and price > 0:
                return price, url
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"Could not fetch gold spot price: {last_err}")


def main():
    spot, src = get_spot()

    gold_per_chi = round(spot / GRAMS_PER_OZ * GRAMS_PER_CHI) + LOCAL_PREMIUM
    if not (100 <= gold_per_chi <= 2000):
        raise SystemExit(
            f"Sanity check failed: gold_per_chi={gold_per_chi} from spot={spot} "
            f"(source {src}). Not posting."
        )
    k18 = round(gold_per_chi * 0.75, 2)

    today = datetime.now(ZoneInfo("Asia/Phnom_Penh")).strftime("%B %-d, %Y")
    text = (
        f"Gold Rate Update — {today}\n"
        f"Gold Price: {gold_per_chi}/chi\n"
        f"18K Price: {k18:.2f}/chi"
    )

    params = {"chat_id": CHAT_ID, "message_thread_id": THREAD_ID, "text": text}
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        resp = json.load(r)
    if not resp.get("ok"):
        raise SystemExit(f"Telegram error: {resp}")

    print(f"Posted OK. spot=${spot:.2f}/oz ({src}) gold/chi={gold_per_chi} 18k/chi={k18:.2f}")


if __name__ == "__main__":
    main()
