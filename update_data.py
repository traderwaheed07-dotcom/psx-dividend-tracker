#!/usr/bin/env python3
"""Refresh data.json from the PSX Terminal API.

Runs inside GitHub Actions (daily). For every listed symbol it reads
GET {BASE}/dividends/{SYMBOL}, then:
  - payouts with ex-date >= today (Pakistan time)  -> "up"   (upcoming list)
  - payouts with ex-date <  today                  -> "hist" (past record)

Company name and the Shariah flag are kept from the previous data.json
("meta") because the dividends endpoint does not carry them.

Safety: if the API returns nothing usable, the script exits with an error
and leaves data.json untouched, so the live site never goes blank.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("PSX_API_BASE", "https://psxterminal.com/api").rstrip("/")
DELAY = float(os.environ.get("PSX_DELAY", "0.25"))
DEBUG_SYMBOL = os.environ.get("PSX_DEBUG_SYMBOL", "MARI")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data.json")
UA = "psx-dividend-tracker/1.0 (+GitHub Actions)"
PKT = dt.timezone(dt.timedelta(hours=5))


def get_json(path, retries=3):
    url = BASE + path
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # symbol has no dividend data
            last = e
        except Exception as e:  # network hiccup, bad JSON
            last = e
        time.sleep(1.5 * (i + 1))
    raise RuntimeError("GET %s failed: %s" % (url, last))


def as_list(j):
    """API may return a bare list or wrap it ({data: [...]}, {dividends: [...]})."""
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        for k in ("data", "dividends", "result", "results", "items", "payouts"):
            if k in j:
                v = as_list(j[k])
                if v:
                    return v
    return []


def first(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y")


def norm_date(v):
    if v is None:
        return ""
    if isinstance(v, (int, float)):  # epoch seconds or ms
        t = v / 1000 if v > 1e11 else v
        return dt.datetime.fromtimestamp(t, PKT).strftime("%Y-%m-%d")
    s = str(v).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    for f in DATE_FORMATS:
        try:
            return dt.datetime.strptime(s, f).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def norm_amount(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("Rs", "").replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_item(it):
    if not isinstance(it, dict):
        return None
    ex = norm_date(first(it, ["ex_date", "exDate", "ex_dividend_date", "exDividendDate", "xDate", "x_date", "date"]))
    amt = norm_amount(first(it, ["amount", "dividend", "dividend_amount", "dividendAmount", "cash", "cash_dividend", "value"]))
    if not ex or amt is None or amt <= 0:
        return None
    rec = norm_date(first(it, ["record_date", "recordDate", "book_closure", "bookClosure", "book_closure_from"]))
    pay = norm_date(first(it, ["payment_date", "paymentDate", "pay_date", "payDate"]))
    return ex, round(amt, 4), rec, pay


def symbol_list():
    j = get_json("/symbols")
    out = []
    for x in as_list(j):
        s = x if isinstance(x, str) else first(x, ["symbol", "ticker", "code", "s"]) if isinstance(x, dict) else None
        if s:
            out.append(str(s).strip().upper())
    return sorted(set(out))


def main():
    today = dt.datetime.now(PKT).strftime("%Y-%m-%d")
    try:
        old = json.load(open(DATA, encoding="utf-8"))
    except Exception:
        old = {}
    meta = old.get("meta", {})
    old_hist = old.get("hist", {})

    # Print one raw response so the format is visible in the Actions log.
    try:
        print("Sample /dividends/%s response:" % DEBUG_SYMBOL, json.dumps(get_json("/dividends/" + DEBUG_SYMBOL))[:800])
    except Exception as e:
        print("Sample fetch failed:", e)

    symbols = symbol_list()
    print("Symbols:", len(symbols))
    if len(symbols) < 50:
        sys.exit("Symbol list looks wrong (%d). data.json left unchanged." % len(symbols))

    up, hist, errors, parsed = [], {}, 0, 0
    for i, sym in enumerate(symbols):
        try:
            items = [p for p in (parse_item(x) for x in as_list(get_json("/dividends/" + sym))) if p]
        except Exception as e:
            errors += 1
            print("  error", sym, e)
            continue
        finally:
            time.sleep(DELAY)
        parsed += len(items)
        future = sorted([p for p in items if p[0] >= today])
        past = sorted([p for p in items if p[0] < today], reverse=True)[:40]
        if future:
            ex, amt, _, _ = future[0]
            m = meta.get(sym, {})
            up.append({"s": sym, "n": m.get("n", ""), "d": ex, "a": amt, "k": m.get("k", 0)})
            meta.setdefault(sym, {"n": "", "k": 0})
        # Merge by ex-date: API rows win, older hand-sourced rows (with record/pay dates) are kept.
        rows = {p[0]: [p[0], p[1], p[2], p[3]] for p in past}
        for r in old_hist.get(sym, []):
            if r[0] < today and r[0] not in rows:
                rows[r[0]] = r
        if rows:
            hist[sym] = sorted(rows.values(), key=lambda r: r[0], reverse=True)[:60]
        if (i + 1) % 100 == 0:
            print("  %d/%d done" % (i + 1, len(symbols)))

    print("Parsed payouts: %d, upcoming: %d, errors: %d" % (parsed, len(up), errors))
    if parsed == 0:
        sys.exit("No usable payout rows parsed (API format changed?). data.json left unchanged.")
    if errors > len(symbols) * 0.3:
        sys.exit("Too many request errors (%d). data.json left unchanged." % errors)

    up.sort(key=lambda u: (u["d"], u["s"]))
    new = {"up": up, "hist": hist, "meta": meta}
    if all(old.get(k) == new[k] for k in new):
        print("No changes.")
        return
    new["updated"] = dt.datetime.now(PKT).isoformat(timespec="minutes")
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(new, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("data.json updated.")


if __name__ == "__main__":
    main()
