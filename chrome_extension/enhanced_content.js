// OriginSteward Enhanced Content Script with Insights and Consumption Features

// --- Configuration ---
const API_BASE_URL = "http://localhost:5002/api";
const DROP_URL = "http://localhost:5002/drop";

// --- State Management ---
let lastCaptureStatus = null;
let isProcessing = false;
let consumptionPanel = null;

// --- UI Injection ---
function injectUI() {
    // Main container
    const container = document.createElement('div');
    container.id = 'origin-steward-container';

    // Capture button
    const button = document.createElement('div');
    button.id = 'origin-steward-btn';
    button.title = "Drag content here or Paste (Ctrl+V)";

    // SVG Icon with status indicator
    button.innerHTML = `
        <svg id="origin-steward-icon" viewBox="0 0 24 24">
            <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
        </svg>
        <div id="origin-steward-status" class="status-dot"></div>
    `;

    // Toast notifications
    const toast = document.createElement('div');
    toast.id = 'origin-steward-toast';

    // Consumption panel (initially hidden)
    const consumptionPanel = createConsumptionPanel();

    container.appendChild(button);
    container.appendChild(toast);
    container.appendChild(consumptionPanel);
    document.body.appendChild(container);

    return { button, toast, consumptionPanel };
}

// --- Consumption Panel ---
function createConsumptionPanel() {
    const panel = document.createElement('div');
    panel.id = 'origin-steward-consumption-panel';
    panel.className = 'hidden';

    panel.innerHTML = `
        <div class="panel-header">
            <h4>Recent Captures</h4>
            <button id="close-panel" class="close-btn">&times;</button>
        </div>
        <div id="consumption-list" class="consumption-list">
            <div class="loading">Loading recent captures...</div>
        </div>
        <div class="panel-footer">
            <button id="view-dashboard" class="dashboard-btn">View Dashboard</button>
            <button id="mark-all-reviewed" class="mark-btn">Mark All Reviewed</button>
        </div>
    `;

    // Event listeners
    panel.querySelector('#close-panel').addEventListener('click', () => {
        panel.classList.add('hidden');
    });

    panel.querySelector('#view-dashboard').addEventListener('click', () => {
        chrome.runtime.sendMessage({ action: "openDashboard" });
    });

    panel.querySelector('#mark-all-reviewed').addEventListener('click', () => {
        markAllCapturesReviewed();
    });

    return panel;
}

// --- Initialize ---
const { button, toast, consumptionPanel } = injectUI();

// --- Status Indicator ---
function updateStatus(type, message) {
    const statusDot = document.getElementById('origin-steward-status');
    statusDot.className = `status-dot ${type}`;

    if (message) {
        showToast(message, type);
    }

    lastCaptureStatus = type;
}

// --- Enhanced Toast Helper ---
function showToast(message, type = 'info', duration = 3000) {
    toast.textContent = message;
    toast.className = type;
    toast.classList.add('show');

    // Add visual indicators based on type
    if (type === 'success') {
        updateStatus('success', null);
    } else if (type === 'error') {
        updateStatus('error', null);
    }

    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

// --- Drag & Drop Logic ---
button.addEventListener('dragover', (e) => {
    e.preventDefault();
    button.classList.add('drag-over');
});

button.addEventListener('dragleave', (e) => {
    e.preventDefault();
    button.classList.remove('drag-over');
});

button.addEventListener('drop', (e) => {
    e.preventDefault();
    button.classList.remove('drag-over');

    handleDrop(e.dataTransfer);
});

// --- Enhanced Click Handler ---
button.addEventListener('click', (e) => {
    if (e.shiftKey) {
        // Shift+Click shows consumption panel
        consumptionPanel.classList.toggle('hidden');
        if (!consumptionPanel.classList.contains('hidden')) {
            loadRecentCaptures();
        }
    } else if (e.ctrlKey || e.metaKey) {
        // Ctrl/Cmd+Click captures current page
        captureCurrentPage();
    } else {
        // Regular click focuses for paste
        button.focus();
    }
});

// --- Paste Logic ---
button.addEventListener('mouseenter', () => {
    document.addEventListener('paste', handlePaste);
});

button.addEventListener('mouseleave', () => {
    document.removeEventListener('paste', handlePaste);
});

function handlePaste(e) {
    e.preventDefault();
    const items = e.clipboardData.items;
    processItems(items);
}

function handleDrop(dataTransfer) {
    const items = dataTransfer.items;
    processItems(items);
}

// --- Capture Current Page ---
function captureCurrentPage() {
    const title = document.title;
    const url = window.location.href;
    const selection = window.getSelection().toString();

    let content = url;
    let note = `Page: ${title}`;

    if (selection) {
        content = selection;
        note += ` | Selection: "${selection.substring(0, 100)}${selection.length > 100 ? '...' : ''}"`;
    }

    performDrop('url', content, note, url, title);
}

// --- Enhanced Processing Logic ---
async function processItems(items) {
    if (isProcessing) {
        showToast("Already processing...", "warning");
        return;
    }

    if (!items || items.length === 0) return;

    isProcessing = true;
    showToast("Processing...", "info");

    try {
        const results = [];

        for (let item of items) {
            if (item.kind === 'string') {
                if (item.type === 'text/plain') {
                    const text = await getAsString(item);
                    const isUrl = text.match(/^https?:\/\//);
                    results.push({
                        type: isUrl ? 'url' : 'text',
                        content: text,
                        note: `${isUrl ? 'URL' : 'Text'} from clipboard`
                    });
                } else if (item.type.startsWith('text/uri-list')) {
                    const uri = await getAsString(item);
                    results.push({
                        type: 'url',
                        content: uri,
                        note: 'URI from clipboard'
                    });
                }
            } else if (item.kind === 'file') {
                const file = item.getAsFile();
                if (file.type.startsWith('image/')) {
                    const base64 = await fileToBase64(file);
                    results.push({
                        type: 'image',
                        content: base64,
                        note: `Image: ${file.name}`,
                        filename: file.name
                    });
                }
            }
        }

        // Send all results
        for (const result of results) {
            await performDrop(
                result.type,
                result.content,
                result.note,
                window.location.href,
                document.title,
                result.filename
            );
        }

        showToast(`Saved ${results.length} item${results.length > 1 ? 's' : ''}`, "success");

        // Update capture count
        updateCaptureCount();

    } catch (error) {
        console.error("Processing failed:", error);
        showToast(`Failed: ${error.message}`, "error");
    } finally {
        isProcessing = false;
    }
}

// --- Helper Functions ---
function getAsString(item) {
    return new Promise((resolve) => {
        item.getAsString(resolve);
    });
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// --- API Functions ---
async function performDrop(type, content, note, sourceUrl, sourceTitle, filename = null) {
    try {
        updateStatus('processing');

        const formData = new FormData();
        formData.append('payload', content);
        formData.append('note', `${note} | Source: ${sourceTitle} (${sourceUrl})`);

        if (filename) {
            formData.append('filename', filename);
        }

        const response = await fetch(DROP_URL, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        updateStatus('success');
        return true;
    } catch (error) {
        console.error("Drop failed:", error);
        updateStatus('error');
        throw error;
    }
}

// --- Recent Captures ---
async function loadRecentCaptures() {
    const list = document.getElementById('consumption-list');
    list.innerHTML = '<div class="loading">Loading recent captures...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/consumption/queue?limit=5`);
        const data = await response.json();

        if (data.success && data.queue.length > 0) {
            list.innerHTML = data.queue.map(item => createCaptureItem(item)).join('');

            // Add event listeners to consumption buttons
            list.querySelectorAll('.consume-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const artifactId = e.target.dataset.artifactId;
                    const status = e.target.dataset.status;
                    updateConsumptionStatus(artifactId, status);
                });
            });
        } else {
            list.innerHTML = '<div class="empty">No recent captures</div>';
        }
    } catch (error) {
        console.error('Failed to load captures:', error);
        list.innerHTML = '<div class="error">Failed to load captures</div>';
    }
}

function createCaptureItem(item) {
    const status = item.artifact.consumption_status || 'unconsumed';
    const importance = item.artifact.importance_score || 0;
    const title = item.artifact.title || 'Untitled';
    const summary = item.artifact.summary || '';

    return `
        <div class="capture-item ${status}">
            <div class="item-header">
                <h5 class="item-title">${escapeHtml(title)}</h5>
                <div class="item-meta">
                    <span class="importance ${getImportanceClass(importance)}">
                        ${importance.toFixed(1)}
                    </span>
                    <span class="status ${status}">${status}</span>
                </div>
            </div>
            ${summary ? `<p class="item-summary">${escapeHtml(summary.substring(0, 150))}...</p>` : ''}
            <div class="item-actions">
                <button class="consume-btn" data-artifact-id="${item.artifact.id}" data-status="reading">
                    Reading
                </button>
                <button class="consume-btn" data-artifact-id="${item.artifact.id}" data-status="reviewed">
                    Reviewed
                </button>
                <button class="consume-btn" data-artifact-id="${item.artifact.id}" data-status="applied">
                    Applied
                </button>
            </div>
        </div>
    `;
}

function getImportanceClass(score) {
    if (score >= 8) return 'high';
    if (score >= 6) return 'medium-high';
    if (score >= 4) return 'medium';
    return 'low';
}

async function updateConsumptionStatus(artifactId, status) {
    try {
        const response = await fetch(`${API_BASE_URL}/consumption/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ artifact_id: artifactId, status: status })
        });

        if (response.ok) {
            showToast(`Marked as ${status}`, "success");
            loadRecentCaptures(); // Refresh list
        } else {
            showToast("Failed to update status", "error");
        }
    } catch (error) {
        console.error('Failed to update status:', error);
        showToast("Failed to update status", "error");
    }
}

async function markAllCapturesReviewed() {
    const buttons = document.querySelectorAll('.capture-item .consume-btn[data-status="reviewed"]');
    for (const btn of buttons) {
        await updateConsumptionStatus(btn.dataset.artifactId, 'reviewed');
    }
}

// --- Capture Count ---
async function updateCaptureCount() {
    try {
        const response = await fetch(`${API_BASE_URL}/consumption/stats`);
        const data = await response.json();

        if (data.success) {
            const unconsumed = data.stats.queue_counts.unconsumed || 0;
            if (unconsumed > 0) {
                button.setAttribute('data-count', unconsumed);
            } else {
                button.removeAttribute('data-count');
            }
        }
    } catch (error) {
        console.error('Failed to update count:', error);
    }
}

// --- Keyboard Shortcuts ---
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd+Shift+S: Quick capture current page
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S') {
        e.preventDefault();
        captureCurrentPage();
    }
    // Ctrl/Cmd+Shift+P: Show consumption panel
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'P') {
        e.preventDefault();
        consumptionPanel.classList.toggle('hidden');
        if (!consumptionPanel.classList.contains('hidden')) {
            loadRecentCaptures();
        }
    }
});

// --- Utility ---
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// --- Initialize on load ---
updateCaptureCount();
setInterval(updateCaptureCount, 30000); // Update every 30 seconds

// Auto-sync status with server
setInterval(async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            updateStatus('online');
        } else {
            updateStatus('error');
        }
    } catch (error) {
        updateStatus('offline');
    }
}, 10000); // Check every 10 seconds