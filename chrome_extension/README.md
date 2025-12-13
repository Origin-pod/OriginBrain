# OriginSteward Capture Extension

A frictionless Chrome Extension for capturing content into your OriginSteward Brain.

## Features
*   **Floating Button**: Drag & Drop text, links, or images.
*   **Context Menu**: Right-click any page, link, or selection -> "Save to Brain".
*   **Paste Support**: Hover over the button and press `Cmd+V` / `Ctrl+V`.

## Installation

1.  Open Chrome and navigate to `chrome://extensions`.
2.  Enable **Developer mode** (toggle in top right).
3.  Click **Load unpacked**.
4.  Select the `chrome_extension` folder in this project.

## Usage

1.  **Ensure the Backend is Running**:
    ```bash
    python app.py
    ```
    The extension communicates with `http://localhost:5002`.

2.  **Capture**:
    *   **Drag**: Drag a link or text selection onto the floating button (bottom right).
    *   **Context Menu**: Right-click and select "Save to Brain".
    *   **Paste**: Hover over the button and paste content.

3.  **Verify**:
    Check the `Inbox/` folder or search via the Web UI (`http://localhost:5002`).
