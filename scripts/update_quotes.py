#!/usr/bin/env python3
"""Refresh the fallback market-quote JSON files used by the front page.

The page fetches live quotes in the browser first (Eastmoney / Tencent /
Coinbase / OKX). These JSON files are only the fallback snapshot, so this
script keeps them from going stale. It writes a file only when every symbol
for that file was fetched successfully; on any failure the old file is left
untouched and the script exits non-zero if all sources failed.

Sources (public, no API key):
- Crypto: OKX public tickers (last price vs 24h open)
- Common + US: Yahoo Finance chart API (regular market price vs previous
  trading day's close taken from the daily bars, not chartPreviousClose)

Output shape is unchanged: {"updated_utc", "updated_et", "quotes":
[{"symbol", "price", "chg"}]}.
"""

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (frontpage-quotes-bot)"}

CRYPTO = ["BTC", "ETH", "SOL", "XRP", "DOGE"]
COMMON = {  # output symbol -> Yahoo symbol
    "XAU": "GC=F",
    "XAG": "SI=F",
    "BRENT": "BZ=F",
    "USDCNY": "CNY=X",
}
US = ["NVDA", "AAPL", "MSFT", "AVGO", "AMD", "TSM", "MU", "INTC",
      "META", "GOOGL", "AMZN", "ARM"]


def get_json(url, attempts=3):
    # Yahoo in particular throws transient 404/429s; retry with backoff.
    import time
    last_exc = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.load(resp)
        except Exception as exc:
            last_exc = exc
            time.sleep(2 * (i + 1))
    raise last_exc


def okx_quote(symbol):
    data = get_json(
        f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT")
    tick = data["data"][0]
    last, open24 = float(tick["last"]), float(tick["open24h"])
    return {"symbol": symbol, "price": last,
            "chg": round((last - open24) / open24 * 100, 2)}


def yahoo_quote(out_symbol, yahoo_symbol):
    path = ("/v8/finance/chart/"
            + urllib.parse.quote(yahoo_symbol, safe="")
            + "?range=5d&interval=1d")
    try:
        result = get_json("https://query1.finance.yahoo.com" + path)["chart"]["result"][0]
    except Exception:
        result = get_json("https://query2.finance.yahoo.com" + path)["chart"]["result"][0]
    meta = result["meta"]
    price = float(meta["regularMarketPrice"])
    closes = [c for c in result["indicators"]["quote"][0]["close"]
              if c is not None]
    if len(closes) < 2:
        raise ValueError(f"{yahoo_symbol}: not enough daily bars")
    # If the last bar is today's (still forming), the previous close is the
    # one before it; otherwise the last bar is the latest completed close
    # and price equals it, so compare against the bar before that too —
    # either way the previous *completed* session close is closes[-2]
    # whenever price corresponds to the final bar.
    prev_close = float(closes[-2])
    return {"symbol": out_symbol, "price": price,
            "chg": round((price - prev_close) / prev_close * 100, 2)}


def write_quotes(filename, quotes):
    now_utc = datetime.now(timezone.utc)
    now_et = now_utc.astimezone(ZoneInfo("America/New_York"))
    payload = {
        "updated_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_et": now_et.strftime("美东 %m-%d %H:%M"),
        "quotes": quotes,
    }
    path = ROOT / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"wrote {filename}: {len(quotes)} quotes")


def main():
    jobs = [
        ("crypto-quotes.json",
         lambda: [okx_quote(s) for s in CRYPTO]),
        ("common-quotes.json",
         lambda: [yahoo_quote(out, y) for out, y in COMMON.items()]),
        ("us-quotes.json",
         lambda: [yahoo_quote(s, s) for s in US]),
    ]
    failures = 0
    for filename, fetch in jobs:
        try:
            write_quotes(filename, fetch())
        except Exception as exc:  # keep the old fallback, report the failure
            failures += 1
            print(f"FAILED {filename}: {exc}", file=sys.stderr)
    if failures == len(jobs):
        sys.exit(1)


if __name__ == "__main__":
    main()
