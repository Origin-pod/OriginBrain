# OriginSteward: iOS Shortcut Guide

This guide explains how to create the "OriginSteward Drop" shortcut on your iPhone/iPad. This shortcut allows you to share URLs or Text from any app directly to your OriginSteward Inbox via iCloud Drive.

## Prerequisites
1.  **iCloud Drive** must be enabled on both your Mac and iPhone.
2.  The `OriginSteward/Inbox` folder must exist in your iCloud Drive.
    *   *Note:* If you are running this project in `~/Documents`, ensure `Desktop & Documents Folders` syncing is enabled in iCloud settings.

## Step-by-Step Creation

1.  Open the **Shortcuts** app on iOS.
2.  Tap **+** to create a new shortcut.
3.  Name it **"Drop to Brain"**.
4.  Enable **Show in Share Sheet**:
    *   Tap the "i" icon (bottom) -> Toggle "Show in Share Sheet".
    *   Set "Receive" to **URLs** and **Text**.

### The Logic Flow

Add the following actions in order:

**1. Set Variable (Input)**
*   Action: `Set Variable`
*   Name: `Payload`
*   Value: `Shortcut Input`

**2. Text (JSON Construction)**
*   Action: `Text`
*   Paste the following JSON template:
    ```json
    {
      "type": "url",
      "payload": "Payload_Variable",
      "timestamp": CurrentDate_As_Unix_Time,
      "note": "Shared from iOS"
    }
    ```
    *   *Tip:* Replace `Payload_Variable` by selecting the variable you created in Step 1.
    *   *Tip:* For `timestamp`, use the "Date" variable, tap it, and change format to "ISO 8601" or custom format `X` (Unix timestamp).

**3. Save File**
*   Action: `Save File`
*   Input: `Text` (the JSON from Step 2)
*   Destination: **iCloud Drive**
*   Path: `Documents/projects/.../Brain2.0/Inbox/` (Navigate to your actual Inbox folder).
*   Name: `mobile_drop.json` (You might want to append date to filename to avoid overwrites, e.g., `mobile_drop_CurrentDate.json`).

## How to Use
1.  Open Safari or Twitter.
2.  Tap **Share**.
3.  Select **Drop to Brain**.
4.  Wait a few seconds for iCloud to sync.
5.  Watch your Mac's daemon pick it up!
