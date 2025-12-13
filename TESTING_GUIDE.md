# OriginSteward: Testing Guide

This guide helps you verify the end-to-end functionality of OriginSteward, from dropping a file to searching for it.

## Prerequisites
1.  Ensure you are in the project root.
2.  Activate the virtual environment: `source venv/bin/activate`.

## Step 1: Start the Daemon
Open a terminal and run:
```bash
python ingest_daemon.py
```
*Leave this running.*

## Step 2: Ingest Data (The "Drop")
Open a **new terminal tab** (keep the daemon running in the first one).

### Test 1: Web Capture
Drop a JSON payload representing a URL.
```bash
# Create a test payload
echo '{"type": "url", "payload": "https://example.com", "timestamp": 123}' > Inbox/web_test.json
```
**Verify:**
*   Check the Daemon terminal: Should say `New file detected` -> `Processing payload type: url` -> `Indexed artifact`.
*   Check `Archive/YYYY-MM-DD/`: You should see `web_test.md`.

### Test 2: Twitter Capture
Drop a JSON payload representing a Tweet.
```bash
# Create a test payload
echo '{"type": "url", "payload": "https://twitter.com/jack/status/20", "timestamp": 123}' > Inbox/tweet_test.json
```
**Verify:**
*   Check the Daemon terminal.
*   Check `Archive/YYYY-MM-DD/`: You should see `tweet_test.md` containing "just setting up my twttr".

## Step 3: Search (The Brain)
Now that data is ingested and indexed, search for it.

```bash
python cli.py search "example"
```
*Expect:* The Web Capture artifact.

```bash
python cli.py search "twttr"
```
*Expect:* The Tweet artifact.

## Troubleshooting
*   **Logs:** Check `Error/*.log` if files disappear from Inbox but don't appear in Archive.
*   **Dependencies:** If `yt-dlp` fails, ensure you have internet access.
