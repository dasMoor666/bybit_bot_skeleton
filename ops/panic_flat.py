#!/usr/bin/env python3
import json, sys
sys.path.insert(0, ".")  # damit 'bot' importierbar ist

from bot.exchange_utils import force_flat_now

def main():
    res = force_flat_now()
    print(json.dumps({
        "status": res["status"],
        "symbol": res["meta"]["symbol"],
        "pos_size": res["pos"]["size"],
        "pos_side": res["pos"]["side"],
        "opens_count": len(res["opens"]["result"]["list"]) if "result" in res.get("opens", {}) else None,
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
