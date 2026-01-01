#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, shlex, sys

def send(msg: str, title: str="Bybit Bot"):
    # Nutzt macOS Notification Center via osascript
    # Escaping für Anführungszeichen:
    msg = msg.replace('"', r'\"')
    title = title.replace('"', r'\"')
    cmd = f'''osascript -e 'display notification "{msg}" with title "{title}"' '''
    try:
        subprocess.run(shlex.split(cmd), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print({"notify_error": str(e)})
        return False

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or "Test-Benachrichtigung OK ✅"
    send(text)
