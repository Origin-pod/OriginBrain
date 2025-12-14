# Troubleshooting OriginSteward

## Chrome Extension Issues

### 1. "Extension doesn't seem to be working"
*   **Symptom**: Floating button doesn't appear or nothing happens when you drop content.
*   **Fix**:
    1.  Go to `chrome://extensions`.
    2.  Find **OriginSteward Capture**.
    3.  Click the **Refresh** (circular arrow) icon.
    4.  **Refresh your web pages**. The extension cannot inject itself into tabs that were already open before it was installed/reloaded.

### 2. "Not getting successfully updated"
*   **Symptom**: You drop content, but don't see a "Saved to Brain!" toast message.
*   **Fix**:
    1.  Ensure the backend is running: `sh start_brain.sh`.
    2.  Check if `http://localhost:5002` is accessible.
    3.  If you see "Failed to save", check the backend logs: `tail -f app.log`.

### 3. "Icon missing"
*   **Symptom**: Error loading extension due to missing icon.
*   **Fix**: We generated a placeholder icon. Reload the extension in `chrome://extensions`.

## Sync Issues

### 1. "Last synced" time not updating
*   **Fix**:
    1.  Ensure the daemon is running (`ps aux | grep ingest_daemon`).
    2.  Check `daemon.log` for errors.
    3.  The Web App polls every 2 seconds. If you just dropped something, give it a moment.
