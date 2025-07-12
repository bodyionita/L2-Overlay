from datetime import datetime
import os
import sys

last_error = ""

def log_action(message):
    log_error("[ACTION] " + message)

def log_error(message):
    global last_error
    last_error = message
    ts = f"[{datetime.now()}] "
    msg = ts + message.strip()
    print("Logging:", msg)
    try:
        log_file = os.path.join(os.path.dirname(sys.argv[0]), "logs.txt")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

def get_last_error():
    global last_error
    return last_error
