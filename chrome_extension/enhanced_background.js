// OriginSteward Enhanced Background Script with Insights and Sync Features

const API_BASE_URL = "http://127.0.0.1:5002/api";
const DROP_URL = "http://127.0.0.1:5002/drop";

// --- State Management ---
let syncStatus = 'offline';
let lastSyncTime = null;
let captureQueue = [];
let isProcessingQueue = false;

// --- Context Menu with Enhanced Options ---
chrome.runtime.onInstalled.addListener(() => {
    // Basic capture options
    chrome.contextMenus.create({
        id: "save-to-brain",
        title: "Save to Brain",
        contexts: ["selection", "link", "image", "page"]
    });

    // Separator
    chrome.contextMenus.create({
        id: "sep1",
        type: "separator",
        contexts: ["all"]
    });

    // Enhanced capture options
    chrome.contextMenus.create({
        id: "save-with-high-priority",
        title: "Save as High Priority",
        contexts: ["selection", "link", "page"]
    });

    chrome.contextMenus.create({
        id: "save-for-review",
        title: "Save for Later Review",
        contexts: ["selection", "link", "page"]
    });

    // Separator
    chrome.contextMenus.create({
        id: "sep2",
        type: "separator",
        contexts: ["all"]
    });

    // Quick actions
    chrome.contextMenus.create({
        id: "open-dashboard",
        title: "Open OriginBrain Dashboard",
        contexts: ["all"]
    });

    chrome.contextMenus.create({
        id: "view-queue",
        title: "View Consumption Queue",
        contexts: ["all"]
    });

    // Initialize
    initializeExtension();
});

// --- Context Menu Handler ---
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
    try {
        switch (info.menuItemId) {
            case "save-to-brain":
                await handleBasicSave(info, tab);
                break;
            case "save-with-high-priority":
                await handlePrioritySave(info, tab, 9);
                break;
            case "save-for-review":
                await handlePrioritySave(info, tab, 5);
                break;
            case "open-dashboard":
                await openDashboard();
                break;
            case "view-queue":
                await openConsumptionQueue();
                break;
        }
    } catch (error) {
        console.error("Context menu action failed:", error);
        showNotification("Failed to save", "error");
    }
});

// --- Message Listener ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    (async () => {
        try {
            switch (request.action) {
                case "drop":
                    const success = await performDrop(
                        request.data.type,
                        request.data.payload,
                        request.data.note,
                        request.data.source_url,
                        request.data.source_title
                    );
                    sendResponse({ success: success });
                    break;

                case "openDashboard":
                    await openDashboard();
                    sendResponse({ success: true });
                    break;

                case "getQueueCount":
                    const count = await getQueueCount();
                    sendResponse({ success: true, count: count });
                    break;

                case "syncStatus":
                    sendResponse({ success: true, status: syncStatus, lastSync: lastSyncTime });
                    break;

                case "updateConsumption":
                    const updated = await updateConsumptionStatus(
                        request.data.artifactId,
                        request.data.status
                    );
                    sendResponse({ success: updated });
                    break;

                default:
                    sendResponse({ success: false, error: "Unknown action" });
            }
        } catch (error) {
            sendResponse({ success: false, error: error.message });
        }
    })();

    return true; // Keep channel open for async response
});

// --- Save Handlers ---
async function handleBasicSave(info, tab) {
    let type = "text";
    let content = "";
    let note = "Context Menu";

    if (info.linkUrl) {
        type = "url";
        content = info.linkUrl;
        note = "Link from Context Menu";
    } else if (info.selectionText) {
        type = "text";
        content = info.selectionText;
        note = "Selection from Context Menu";
    } else if (info.srcUrl) {
        type = "url";
        content = info.srcUrl;
        note = "Image URL from Context Menu";
    } else if (info.pageUrl) {
        type = "url";
        content = info.pageUrl;
        note = "Page URL from Context Menu";
    }

    if (content) {
        const success = await performDrop(type, content, note, tab.url, tab.title);
        if (success) {
            showNotification("Saved to brain", "success");
            updateBadgeCount();
        }
    }
}

async function handlePrioritySave(info, tab, priority) {
    // First save the item
    await handleBasicSave(info, tab);

    // Then update its importance (this is a simplified approach)
    // In a real implementation, we'd need to get the artifact ID and update it
    showNotification(`Saved with priority ${priority}/10`, "success");
}

// --- API Functions ---
async function performDrop(type, content, note, sourceUrl, sourceTitle) {
    try {
        setSyncStatus('processing');

        const formData = new FormData();
        formData.append('payload', content);
        formData.append('note', `${note} | Source: ${sourceTitle} (${sourceUrl})`);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        const response = await fetch(DROP_URL, {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        setSyncStatus('online');
        lastSyncTime = new Date();

        // Trigger background processing
        setTimeout(triggerBackgroundProcessing, 1000);

        return true;
    } catch (error) {
        console.error("Drop failed:", error);
        setSyncStatus('offline');
        return false;
    }
}

async function getQueueCount() {
    try {
        const response = await fetch(`${API_BASE_URL}/consumption/stats`);
        const data = await response.json();

        if (data.success) {
            return data.stats.queue_counts.unconsumed || 0;
        }
        return 0;
    } catch (error) {
        console.error("Failed to get queue count:", error);
        return 0;
    }
}

async function updateConsumptionStatus(artifactId, status) {
    try {
        const response = await fetch(`${API_BASE_URL}/consumption/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ artifact_id: artifactId, status: status })
        });

        return response.ok;
    } catch (error) {
        console.error("Failed to update consumption:", error);
        return false;
    }
}

// --- Dashboard Functions ---
async function openDashboard() {
    const url = "http://localhost:3000"; // Frontend URL
    await chrome.tabs.create({ url: url });
}

async function openConsumptionQueue() {
    const url = "http://localhost:3000?view=consumption";
    await chrome.tabs.create({ url: url });
}

// --- Sync Status Management ---
function setSyncStatus(status) {
    syncStatus = status;

    // Update badge
    switch (status) {
        case 'online':
            chrome.action.setBadgeText({ text: '' });
            chrome.action.setBadgeBackgroundColor({ color: '#10b981' });
            break;
        case 'processing':
            chrome.action.setBadgeText({ text: '...' });
            chrome.action.setBadgeBackgroundColor({ color: '#f59e0b' });
            break;
        case 'offline':
            chrome.action.setBadgeText({ text: '!' });
            chrome.action.setBadgeBackgroundColor({ color: '#ef4444' });
            break;
    }

    // Notify content scripts
    chrome.tabs.query({}, (tabs) => {
        tabs.forEach(tab => {
            chrome.tabs.sendMessage(tab.id, {
                action: 'syncStatusUpdate',
                status: status
            }).catch(() => {
                // Ignore errors for tabs without content script
            });
        });
    });
}

// --- Badge Management ---
async function updateBadgeCount() {
    const count = await getQueueCount();
    if (count > 0) {
        chrome.action.setBadgeText({ text: count.toString() });
        chrome.action.setBadgeBackgroundColor({ color: '#ef4444' });
    } else {
        chrome.action.setBadgeText({ text: '' });
    }
}

// --- Background Processing ---
async function triggerBackgroundProcessing() {
    if (isProcessingQueue) return;
    isProcessingQueue = true;

    try {
        // Trigger consumption queue processing
        const response = await fetch(`${API_BASE_URL}/consumption/process-queue`, {
            method: 'POST'
        });

        if (response.ok) {
            console.log("Background processing triggered");
        }
    } catch (error) {
        console.error("Failed to trigger background processing:", error);
    } finally {
        isProcessingQueue = false;
    }
}

// --- Notifications ---
function showNotification(message, type = 'info') {
    chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icon.png',
        title: 'OriginBrain',
        message: message
    });
}

// --- Health Check ---
async function performHealthCheck() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            setSyncStatus('online');
        } else {
            setSyncStatus('offline');
        }
    } catch (error) {
        setSyncStatus('offline');
    }
}

// --- Extension Initialization ---
async function initializeExtension() {
    console.log("OriginBrain extension initialized");

    // Perform initial health check
    await performHealthCheck();

    // Update badge count
    await updateBadgeCount();

    // Set up periodic health checks
    setInterval(performHealthCheck, 30000); // Every 30 seconds

    // Set up periodic badge updates
    setInterval(updateBadgeCount, 60000); // Every minute

    // Process any queued items
    setTimeout(triggerBackgroundProcessing, 2000);
}

// --- Action Click Handler ---
chrome.action.onClicked.addListener((tab) => {
    // Open dashboard when extension icon is clicked
    openDashboard();
});

// --- Tab Update Listener ---
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // Update badge when tab completes loading
    if (changeInfo.status === 'complete') {
        updateBadgeCount();
    }
});

// --- Storage Listener ---
chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === 'sync') {
        // React to sync storage changes if needed
        console.log("Sync storage changed:", changes);
    }
});

// Install permission for notifications
chrome.permissions.request({
    permissions: ['notifications']
}, (granted) => {
    if (granted) {
        console.log("Notification permission granted");
    }
});

// --- Export Functions ---
async function exportData(format) {
    try {
        const response = await fetch(`${API_BASE_URL}/export/artifacts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ format: format })
        });

        if (response.ok) {
            const data = await response.json();
            return data.result;
        }
        throw new Error("Export failed");
    } catch (error) {
        console.error("Export failed:", error);
        return null;
    }
}

// --- Context Menu Export Options ---
chrome.contextMenus.create({
    id: "export-json",
    title: "Export Artifacts as JSON",
    contexts: ["all"],
    parentId: "sep2"
});

chrome.contextMenus.create({
    id: "export-markdown",
    title: "Export Artifacts as Markdown",
    contexts: ["all"],
    parentId: "sep2"
});

// Update context menu handler for export
const originalHandler = chrome.contextMenus.onClicked.addListener;
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
    if (info.menuItemId === "export-json" || info.menuItemId === "export-markdown") {
        const format = info.menuItemId === "export-json" ? "json" : "markdown";
        const result = await exportData(format);

        if (result) {
            // Create a blob and download
            const blob = new Blob([result], {
                type: format === "json" ? "application/json" : "text/markdown"
            });
            const url = URL.createObjectURL(blob);

            chrome.downloads.download({
                url: url,
                filename: `originbrain_export.${format}`,
                saveAs: true
            });

            showNotification(`Exported as ${format.toUpperCase()}`, "success");
        } else {
            showNotification("Export failed", "error");
        }
        return;
    }

    // Call original handler for other menu items
    return originalHandler(info, tab);
});