"""Run locally with no paid services; stops when the host is off."""
import json
import os
import time
from autopilot.discovery import run
from autopilot.storage import Ledger

def main():
    config = json.loads(os.environ["AUTOPILOT_CONFIG"])
    ledger = Ledger()
    try:
        while True:
            ledger.ingest(run(config))
            print(f"{len(ledger.pending())} jobs awaiting review", flush=True)
            time.sleep(4 * 3600)
    finally:
        ledger.close()

if __name__ == "__main__":
    main()
