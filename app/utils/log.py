# app/utils/log.py
# Description: Simple event logger to file and stdout
# Requires: None

# import libraries
import json, datetime, os

# set log path
LOG_PATH = os.environ.get("LOKKATHA_LOG_PATH", "storyteller_log.txt")

# log event function
def log_event(event: str, meta: dict | None = None):
    payload = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "event": event}
    if meta: payload.update(meta)
    try: print(json.dumps(payload, ensure_ascii=False))
    except Exception: print(str(payload))
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception: pass