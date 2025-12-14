// OriginSteward Background Script

const API_URL = "http://127.0.0.1:5002/drop";

// --- Context Menu ---
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "save-to-brain",
        title: "Save to Brain",
        contexts: ["selection", "link", "image", "page"]
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    let type = "text";
    let content = "";
    let note = "Context Menu";

    if (info.menuItemId === "save-to-brain") {
        if (info.linkUrl) {
            type = "url";
            content = info.linkUrl;
            note = "Link from Context Menu";
        } else if (info.selectionText) {
            type = "text";
            content = info.selectionText;
            note = "Selection from Context Menu";
        } else if (info.srcUrl) {
            type = "url"; // Treat image URL as URL for now, or fetch and base64?
            content = info.srcUrl;
            note = "Image URL from Context Menu";
        } else if (info.pageUrl) {
            type = "url";
            content = info.pageUrl;
            note = "Page URL from Context Menu";
        }

        if (content) {
            performDrop(type, content, note, tab.url, tab.title);
        }
    }
});

// --- Message Listener ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "drop") {
        const d = request.data;
        performDrop(d.type, d.payload, d.note, d.source_url, d.source_title)
            .then(success => sendResponse({ success: success }))
            .catch(err => sendResponse({ success: false, error: err.message }));

        return true; // Keep channel open for async response
    }
});

// --- API Logic ---
async function performDrop(type, content, note, sourceUrl, sourceTitle) {
    try {
        // Construct form data as app.py expects
        // app.py expects: payload, note
        // It determines type internally, but we can hint via note or just let it be.
        // Wait, app.py logic: type_ = "url" if payload.startswith("http") else "text"
        // If we send base64 image, it starts with "data:image...", so it will be "text" unless we update app.py

        // Let's treat everything as payload for now.
        // We might need to update app.py to handle explicit types if we want to support images better.

        const formData = new FormData();
        formData.append('payload', content);
        formData.append('note', `${note} | Source: ${sourceTitle} (${sourceUrl})`);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        return true;
    } catch (error) {
        console.error("Drop failed:", error);
        return false; // This will trigger "Failed to save" in content.js
    }
}
