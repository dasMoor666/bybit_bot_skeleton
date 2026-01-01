#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, time, datetime as dt, subprocess, shlex
from pybit.unified_trading import HTTP
from bot.config import SETTINGS as S
from scripts.log_utils import log_event

# macOS Notification helper (leise wegstecken, wenn osascript nicht geht)
def notify(msg: str, title: str="Bybit Bot"):
    try:
        msg = msg.replace('"', r'\"'); title = title.replace('"', r'\"')
        cmd = f'''osascript -e 'display notification "{msg}" with title "{title}"' '''
        subprocess.run(shlex.split(cmd), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

SYM = "BTCUSDT"
STATE_PATH = os.path.join("logs", "health_state.json")
ALERT_LOG = os.path.join("logs", "alerts.log")

def http():
    return HTTP(timeout=60,  api_key=S.bybit_api_key, api_secret=S.bybit_api_secret, testnet=S.bybit_testnet)

def ok(ret): return isinstance(ret, dict) and ret.get("retCode") == 0

def load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {"error_streak":0, "last_ok_ts":0, "pos_seen_ts":0}

def save_state(st):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f: json.dump(st, f)

def append_alert_line(text: str):
    os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
    rec = {"ts": int(time.time()), "iso": dt.datetime.utcnow().isoformat()+"Z", "alert": text}
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def main():
    os.makedirs("logs", exist_ok=True)
    st = load_state()
    out = {"checks": {}, "alerts": [], "meta": {}}
    now = int(time.time())

    try:
        s = http()
        # --- API Checks ---
        r1 = s.get_server_time(); out["checks"]["server_time"] = {"ok": ok(r1), "msg": r1.get("retMsg") if isinstance(r1, dict) else str(r1)}
        r2 = s.get_tickers(category="linear", symbol=SYM); out["checks"]["ticker"] = {"ok": ok(r2)}
        if ok(r2):
            lst = (r2["result"] or {}).get("list") or []
            if lst: out["last_price"] = lst[0].get("lastPrice")

        r3 = s.get_positions(category="linear", symbol=SYM); out["checks"]["positions"] = {"ok": ok(r3)}
        pos_open = False
        if ok(r3):
            L = (r3["result"] or {}).get("list") or []
            P = next((p for p in L if float(p.get("size") or 0) > 0), None)
            if P:
                pos_open = True
                out["pos"] = {"side": P["side"], "size": P["size"], "unreal": P.get("unrealisedPnl")}
        out["pos_open"] = pos_open

        r4 = s.get_open_orders(category="linear", symbol=SYM); out["checks"]["orders"] = {"ok": ok(r4)}
        open_orders = 0
        if ok(r4): open_orders = len((r4["result"] or {}).get("list") or [])
        out["open_orders"] = open_orders

        # --- Fehler-Heuristik & State ---
        error_now = (not out["checks"]["server_time"]["ok"]) or (not out["checks"]["ticker"]["ok"]) \
                    or (not out["checks"]["positions"]["ok"]) or (not out["checks"]["orders"]["ok"])
        if error_now:
            st["error_streak"] = st.get("error_streak", 0) + 1
        else:
            st["error_streak"] = 0
            st["last_ok_ts"] = now

        if pos_open: st["pos_seen_ts"] = st.get("pos_seen_ts") or now
        else: st["pos_seen_ts"] = 0

        # --- Testschalter: FORCE_ALERT ---
        if os.environ.get("FORCE_ALERT"):
            out["alerts"].append("FORCE_ALERT_TEST")
            append_alert_line("FORCE_ALERT_TEST")

        # --- Schwellen/Benachrichtigungen ---
        if error_now:
            out["alerts"].append(f"API-Fehler (Streak {st['error_streak']})")
        if st["error_streak"] >= 3:
            notify("3x Health-Error in Folge – bitte Check (Netz/API/Keys)", title="Bybit Bot – HEALTH ⚠️")
        if st.get("pos_seen_ts"):
            minutes_open = (now - st["pos_seen_ts"]) // 60
            if minutes_open >= 15 and open_orders == 0:
                warn = f"Position seit {minutes_open} min offen (ohne Orders)"
                out["alerts"].append(warn); append_alert_line(warn); notify(warn, title="Bybit Bot – WATCH ⏱️")

        # --- Optional: Auto-Panic ---
        if os.environ.get("AUTO_PANIC_CLOSE","0") == "1" and (pos_open or open_orders>0) and st["error_streak"]>=3:
            proj = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            exe = os.path.join(proj, "scripts", "panic_close.py")
            try:
                subprocess.run([sys.executable, exe], capture_output=True, text=True, timeout=20)
                out["alerts"].append("AUTO_PANIC_EXECUTED"); append_alert_line("AUTO_PANIC_EXECUTED")
                notify("AUTO-PANIC ausgeführt", title="Bybit Bot – PANIC 🧯")
            except Exception as e:
                out["alerts"].append(f"AUTO_PANIC_ERR:{e}"); append_alert_line(f"AUTO_PANIC_ERR:{e}")
                notify(f"AUTO-PANIC Fehler: {e}", title="Bybit Bot – PANIC ❌")

        save_state(st)
        rec = log_event("health", out)
        print(json.dumps(rec, ensure_ascii=False))

    except Exception as e:
        st["error_streak"] = st.get("error_streak", 0) + 1
        save_state(st)
        rec = log_event("health_error", {"error": str(e)})
        if st["error_streak"] >= 3:
            notify(f"Health-Error (x{st['error_streak']}): {e}", title="Bybit Bot – HEALTH ❌")
        print(json.dumps(rec, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
