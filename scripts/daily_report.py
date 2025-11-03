#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Report (18:00):
- holt 24h-Kurs (15m-Kerzen) von Bybit
- markiert Trades (Fills) der letzten 24h
- summiert realisierte PnL, zählt Alerts aus logs/
- optional: vergleicht "Forecasts" aus forecasts.jsonl (wenn vorhanden)
- erzeugt PNG-Chart + TXT-Zusammenfassung
"""
import os, sys, json, time, datetime as dt
from decimal import Decimal
from pybit.unified_trading import HTTP
from bot.config import SETTINGS as S

# ---- Config ----
SYM = "BTCUSDT"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
FORECASTS = os.path.join(os.path.dirname(__file__), "..", "forecasts.jsonl")  # optional

# -- plotting (matplotlib, keine Farben setzen) --
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- macOS Notification ---
def notify(msg: str, title: str="Bybit Bot – Daily"):
    try:
        import subprocess, shlex
        msg = msg.replace('"', r'\"')
        title = title.replace('"', r'\"')
        cmd = f'''osascript -e 'display notification "{msg}" with title "{title}"' '''
        subprocess.run(shlex.split(cmd), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def http():
    return HTTP(timeout=60,  api_key=S.bybit_api_key, api_secret=S.bybit_api_secret, testnet=S.bybit_testnet)

def utcnow():
    return dt.datetime.utcnow()

def ymd():
    return utcnow().strftime("%Y-%m-%d")

def log_lines_for_today():
    path = os.path.join(LOG_DIR, f"log-{utcnow().strftime('%Y%m%d')}.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]

def read_forecasts_window(since_ts):
    """Optional: forecasts.jsonl mit Schemas wie:
       {"ts": 1761600000, "symbol":"BTCUSDT", "h":3600, "dir":"+1", "note":"breakout long"}
       h=Prognosehorizont in Sekunden, dir = "+1" (up) oder "-1" (down)
    """
    if not os.path.exists(FORECASTS):
        return []
    rows = []
    with open(FORECASTS, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try:
                j=json.loads(line)
                if j.get("symbol")==SYM and int(j.get("ts",0))>= since_ts:
                    rows.append(j)
            except Exception:
                pass
    return rows

def kline_24h(s):
    # 24h zurück, 15m-Kerzen
    now_ms = int(time.time()*1000)
    since_ms = now_ms - 24*60*60*1000
    # pybit v5: get_kline(category="linear", symbol=SYM, interval="15", start=..., end=...)
    r = s.get_kline(category="linear", symbol=SYM, interval="15", start=since_ms, end=now_ms)
    lst = (r.get("result") or {}).get("list") or []
    # Bybit liefert oft jüngstes zuerst; wir sortieren nach openTime
    rows = []
    for it in lst:
        # unify fields: start, open, high, low, close
        # v5: it = [start, open, high, low, close, volume, turnover]
        try:
            rows.append({
                "t": int(it[0])//1000,
                "o": float(it[1]), "h": float(it[2]),
                "l": float(it[3]), "c": float(it[4])
            })
        except Exception:
            pass
    rows.sort(key=lambda x: x["t"])
    return rows

def fills_24h(s):
    # Executions der letzten 24h
    now_ms = int(time.time()*1000)
    since_ms = now_ms - 24*60*60*1000
    # unified endpoint: get_executions(category="linear", symbol=SYM, startTime=..., endTime=...)
    r = s.get_executions(category="linear", symbol=SYM, startTime=since_ms, endTime=now_ms)
    lst = (r.get("result") or {}).get("list") or []
    fills = []
    for it in lst:
        try:
            fills.append({
                "ts": int(it["execTime"])//1000,
                "side": it["side"],  # "Buy"/"Sell"
                "price": float(it["execPrice"]),
                "qty": float(it["execQty"]),
                "fee": float(it.get("execFee", 0.0)),
                "isMaker": bool(it.get("isMaker", False)),
                "orderType": it.get("orderType",""),
            })
        except Exception:
            pass
    fills.sort(key=lambda x: x["ts"])
    return fills

def realized_pnl_from_closed(s):
    # Optional: geschlossenes PnL (falls verfügbar)
    # Achtung: je nach Account kann get_closed_pnl leer sein; deshalb Fallback über fills.
    now_ms = int(time.time()*1000)
    since_ms = now_ms - 24*60*60*1000
    try:
        r = s.get_closed_pnl(category="linear", symbol=SYM, startTime=since_ms, endTime=now_ms)
        lst = (r.get("result") or {}).get("list") or []
        total = Decimal("0")
        for it in lst:
            # v5 returns "closedPnl"
            total += Decimal(str(it.get("closedPnl","0")))
        return float(total)
    except Exception:
        return None

def pnl_from_fills(fills):
    # sehr vereinfachtes PnL aus aufeinanderfolgenden Buys/Sells (kleines FIFO)
    pos = 0.0
    avg = 0.0
    realized = 0.0
    for f in fills:
        if f["side"] == "Buy":
            # position erhöhen
            total_cost = avg*pos + f["price"]*f["qty"]
            pos += f["qty"]
            if pos > 0:
                avg = total_cost/pos
        else:  # Sell
            qty = min(pos, f["qty"])
            realized += (f["price"] - avg)*qty
            pos -= qty
            if pos <= 1e-12:
                pos, avg = 0.0, 0.0
    return realized

def draw_chart(rows, fills, out_png, forecasts):
    if not rows:
        return
    ts = [dt.datetime.utcfromtimestamp(r["t"]) for r in rows]
    close = [r["c"] for r in rows]

    plt.figure(figsize=(10,4))
    plt.plot(ts, close, label="Close 15m")
    # Trades (nur Marker, keine Farbangaben)
    for f in fills:
        t = dt.datetime.utcfromtimestamp(f["ts"])
        y = f["price"]
        m = "^" if f["side"]=="Buy" else "v"
        plt.plot([t], [y], marker=m)

    # Forecast-Fenster (schraffiert)
    for fc in forecasts:
        t0 = dt.datetime.utcfromtimestamp(int(fc["ts"]))
        t1 = t0 + dt.timedelta(seconds=int(fc.get("h", 3600)))
        plt.axvspan(t0, t1, alpha=0.1)

    plt.title(f"{SYM} • letzte 24h")
    plt.xlabel("UTC Zeit")
    plt.ylabel("Preis")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()

def evaluate_forecasts(forecasts, rows):
    # grobe Trefferquote: Blick vom Forecast-Start (t0) bis t0+h – war der Nettoverlauf in prognostizierter Richtung?
    if not forecasts or not rows:
        return {"count":0, "hits":0, "hit_rate":None}
    idx_by_t = {r["t"]: r for r in rows}
    # Hilfsfunktion: finde close zum nächstliegenden Zeitstempel
    import bisect
    row_ts = [r["t"] for r in rows]

    def close_at(ts):
        i = bisect.bisect_left(row_ts, ts)
        if i >= len(row_ts): i = len(row_ts)-1
        if i < 0: i = 0
        return rows[i]["c"]

    hits = 0
    for fc in forecasts:
        t0 = int(fc["ts"])
        h = int(fc.get("h", 3600))
        dir_ = str(fc.get("dir","+1"))
        c0 = close_at(t0)
        c1 = close_at(t0+h)
        up = c1 - c0
        if (up > 0 and dir_ == "+1") or (up < 0 and dir_ == "-1"):
            hits += 1
    return {"count":len(forecasts), "hits":hits, "hit_rate": (hits/len(forecasts) if forecasts else None)}

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    s = http()

    # Daten holen
    kl = kline_24h(s)
    fills = fills_24h(s)
    closed = realized_pnl_from_closed(s)
    if closed is None:
        closed = pnl_from_fills(fills)

    # Alerts des Tages zählen
    alerts = 0
    lines = log_lines_for_today()
    for r in lines:
        if r.get("kind") in ("health","health_error"):
            d = r.get("data", {})
            alerts += len(d.get("alerts", [])) if isinstance(d.get("alerts"), list) else 0

    # Forecasts (optional) einlesen & bewerten (nur 24h)
    since_ts = int(time.time()) - 24*60*60
    forecasts = read_forecasts_window(since_ts)
    fc_eval = evaluate_forecasts(forecasts, kl)

    # Chart rendern
    out_png = os.path.abspath(os.path.join(OUT_DIR, f"daily-{ymd()}.png"))
    draw_chart(kl, fills, out_png, forecasts)

    # Text-Report
    realized_txt = f"{closed:.2f} (USDT)" if closed is not None else "n/a"
    fc_line = "keine Prognosen" if not forecasts else f"{fc_eval['hits']}/{fc_eval['count']} Treffer (Hit-Rate {fc_eval['hit_rate']:.0%})"
    summary = [
        f"BYBIT DAILY • {ymd()}",
        f"Symbol: {SYM}",
        f"Realisierte PnL (24h): {realized_txt}",
        f"Fills (24h): {len(fills)}",
        f"Alerts heute: {alerts}",
        f"Forecast-Qualität: {fc_line}",
        f"Chart: {out_png}",
        "",
        "Empfehlungen:",
        "- Hohe Alert-Anzahl? -> API/Netz prüfen, ggf. Rate-Limits.",
        "- Negative PnL + viele Fills? -> Slippage/Fees prüfen, Positionsgröße anpassen.",
        "- Forecast-Hit-Rate < 55%? -> Regel justieren (Signalfilter, Timeframe, Stop/TP).",
    ]
    out_txt = os.path.abspath(os.path.join(OUT_DIR, f"daily-{ymd()}.txt"))
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(summary))

    # kleine Notification
    notify(f"PnL 24h: {realized_txt} • Fills: {len(fills)} • Forecasts: {fc_line}", title="Bybit Bot – Daily Report")
    print(json.dumps({"png": out_png, "txt": out_txt, "fills": len(fills), "pnl": realized_txt, "forecast": fc_line}, ensure_ascii=False))

if __name__ == "__main__":
    main()
