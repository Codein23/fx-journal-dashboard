#!/usr/bin/env python3
"""Fetch trades from a Notion database and compute analytics into data.json.

Reproduces the fxjournalstats embed panels (calendar / time / risk / discipline)
entirely from the user's own Notion TRADES DB so the dashboard is self-owned.

Env:
  NOTION_TOKEN   integration token (kept secret; never shipped to the client)
  NOTION_DB_ID   trades database id
Output:
  data.json  (written next to index.html, at repo root by default)
"""
import os
import json
import sys
import datetime as dt
from collections import defaultdict
from urllib import request, error

OUT = os.environ.get("OUT_PATH", os.path.join(os.path.dirname(__file__), "..", "data.json"))
API = "https://api.notion.com/v1"


def _headers():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("NOTION_TOKEN env var required", file=sys.stderr)
        sys.exit(1)
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _post(url, payload):
    data = json.dumps(payload).encode()
    req = request.Request(url, data=data, headers=_headers(), method="POST")
    with request.urlopen(req) as r:
        return json.loads(r.read())


def query_all():
    db_id = os.environ.get("NOTION_DB_ID")
    if not db_id:
        print("NOTION_DB_ID env var required", file=sys.stderr)
        sys.exit(1)
    rows = []
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        res = _post(f"{API}/databases/{db_id}/query", payload)
        rows.extend(res["results"])
        if not res.get("has_more"):
            break
        cursor = res["next_cursor"]
    return rows


def prop(props, name):
    return props.get(name) or {}


def pval(p):
    """Extract a python value from a Notion property object."""
    t = p.get("type")
    if t == "number":
        return p.get("number")
    if t == "checkbox":
        return p.get("checkbox")
    if t == "select":
        s = p.get("select")
        return s.get("name") if s else None
    if t == "multi_select":
        return [x["name"] for x in p.get("multi_select", [])]
    if t == "date":
        d = p.get("date")
        return d.get("start") if d else None
    if t == "formula":
        f = p.get("formula", {})
        ft = f.get("type")
        return f.get(ft)
    if t == "title":
        return "".join(x["plain_text"] for x in p.get("title", []))
    if t == "rich_text":
        return "".join(x["plain_text"] for x in p.get("rich_text", []))
    return None


def parse_trades(rows):
    trades = []
    for r in rows:
        pr = r["properties"]
        pl = pval(prop(pr, "Profit/Loss"))
        date = pval(prop(pr, "Date"))
        if pl is None or not date:
            continue  # skip empty/placeholder rows
        d = date[:10]
        trades.append({
            "date": d,
            "pl": float(pl),
            "win": bool(pval(prop(pr, "WIN"))),
            "be": bool(pval(prop(pr, "BE"))),
            "dow": pval(prop(pr, "DOW")),
            "pair": pval(prop(pr, "Pairs")),
            "direction": pval(prop(pr, "Direction")),
            "session": pval(prop(pr, "Session")),
            "entry_window": pval(prop(pr, "Entry Window")),
            "model": pval(prop(pr, "Model")),
            "followed": bool(pval(prop(pr, "Followed rules"))),
            "pos_tags": pval(prop(pr, "Positive tags")) or [],
            "neg_tags": pval(prop(pr, "Negative tags")) or [],
        })
    trades.sort(key=lambda t: t["date"])
    return trades


DOW_ORDER = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def compute(trades):
    n = len(trades)
    out = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "trade_count": n,
        "trades": trades,
    }
    if n == 0:
        out.update({"empty": True})
        return out

    total = sum(t["pl"] for t in trades)
    wins = [t["pl"] for t in trades if t["pl"] > 0]
    losses = [t["pl"] for t in trades if t["pl"] < 0]

    # --- per-day aggregation ---
    by_day = defaultdict(float)
    for t in trades:
        by_day[t["date"]] += t["pl"]
    day_pls = list(by_day.values())
    n_days = len(by_day)

    # --- per-month ---
    by_month = defaultdict(float)
    for t in trades:
        by_month[t["date"][:7]] += t["pl"]
    n_months = len(by_month)

    # --- equity curve + drawdown (trade order) ---
    equity = []
    run = 0.0
    peak = 0.0
    max_dd = 0.0
    dd_series = []
    for t in trades:
        run += t["pl"]
        equity.append({"date": t["date"], "equity": round(run, 2)})
        peak = max(peak, run)
        dd = run - peak
        max_dd = min(max_dd, dd)
        dd_series.append({"date": t["date"], "drawdown": round(dd, 2)})

    # --- by DOW (P/L) ---
    dow = defaultdict(float)
    for t in trades:
        if t["dow"]:
            dow[t["dow"]] += t["pl"]
    dow_data = [{"label": d, "value": round(dow.get(d, 0.0), 2)} for d in DOW_ORDER]

    # --- by entry window ---
    ew = defaultdict(float)
    for t in trades:
        if t["entry_window"]:
            ew[t["entry_window"]] += t["pl"]
    ew_data = [{"label": k, "value": round(v, 2)} for k, v in sorted(ew.items(), key=lambda x: -x[1])]

    # --- by pair ---
    pair = defaultdict(float)
    for t in trades:
        if t["pair"]:
            pair[t["pair"]] += t["pl"]
    pair_data = [{"label": k, "value": round(v, 2)} for k, v in sorted(pair.items(), key=lambda x: -x[1])]

    # --- tags ---
    pos = defaultdict(float)
    neg = defaultdict(float)
    for t in trades:
        for tag in t["pos_tags"]:
            pos[tag] += t["pl"]
        for tag in t["neg_tags"]:
            neg[tag] += t["pl"]
    pos_data = [{"label": k, "value": round(v, 2)} for k, v in sorted(pos.items(), key=lambda x: -x[1])]
    neg_data = [{"label": k, "value": round(v, 2)} for k, v in sorted(neg.items(), key=lambda x: -x[1])]

    # --- discipline ---
    followed = [t for t in trades if t["followed"]]
    fwins = [t for t in followed if t["win"]]
    plan_adherence = 100.0 * len(followed) / n
    followed_pl = sum(t["pl"] for t in followed)
    followed_wr = (100.0 * len(fwins) / len(followed)) if followed else 0.0

    # --- consistency: % of profitable trading days ---
    profitable_days = sum(1 for v in day_pls if v > 0)
    consistency = 100.0 * profitable_days / n_days if n_days else 0.0

    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    rr = (avg_win / abs(avg_loss)) if avg_loss else 0.0
    recovery = (total / abs(max_dd)) if max_dd < 0 else 0.0
    win_rate = 100.0 * len([t for t in trades if t["win"]]) / n

    out["stats"] = {
        "total_pl": round(total, 2),
        "win_rate": round(win_rate, 1),
        "win_count": len(wins),
        "loss_count": len(losses),
        "be_count": len([t for t in trades if t["be"]]),
        # time
        "avg_pl_day": round(total / n_days, 2) if n_days else 0,
        "avg_pl_month": round(total / n_months, 2) if n_months else 0,
        "best_day": round(max(day_pls), 2),
        "worst_day": round(min(day_pls), 2),
        # risk
        "max_drawdown": round(max_dd, 2),
        "biggest_winner": round(max(t["pl"] for t in trades), 2),
        "biggest_loser": round(min(t["pl"] for t in trades), 2),
        "recovery_factor": round(recovery, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "risk_reward": round(rr, 2),
        "consistency": round(consistency, 1),
        # discipline
        "plan_adherence": round(plan_adherence, 1),
        "followed_pl": round(followed_pl, 2),
        "followed_win_rate": round(followed_wr, 1),
    }
    out["charts"] = {
        "dow": dow_data,
        "entry_window": ew_data,
        "pairs": pair_data,
        "pos_tags": pos_data,
        "neg_tags": neg_data,
        "equity": equity,
        "drawdown": dd_series,
        "daily": [{"date": k, "value": round(v, 2)} for k, v in sorted(by_day.items())],
    }
    return out


def main():
    rows = query_all()
    trades = parse_trades(rows)
    data = compute(trades)
    out_path = os.path.abspath(OUT)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}: {data['trade_count']} trades")


if __name__ == "__main__":
    try:
        main()
    except error.HTTPError as e:
        print("HTTP", e.code, e.read().decode(), file=sys.stderr)
        sys.exit(1)
