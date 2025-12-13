import json
import os
import time

INBOX_DIR = "Inbox"

def drop_test_file():
    payload = {
        "type": "url",
        "payload": "https://example.com/quick-test",
        "timestamp": time.time(),
        "note": "Quick manual test"
    }
    
    filename = f"quick_test_{int(time.time())}.json"
    filepath = os.path.join(INBOX_DIR, filename)
    
    print(f"Dropping {filename} into {INBOX_DIR}...")
    with open(filepath, "w") as f:
        json.dump(payload, f, indent=2)
    print("Done. Check the daemon output!")

if __name__ == "__main__":
    if not os.path.exists(INBOX_DIR):
        os.makedirs(INBOX_DIR)
    drop_test_file()
