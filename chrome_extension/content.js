// OriginSteward Content Script

// --- Configuration ---
const API_URL = "http://localhost:5002/drop";

// --- UI Injection ---
function injectUI() {
    const container = document.createElement('div');
    container.id = 'origin-steward-container';
    
    const button = document.createElement('div');
    button.id = 'origin-steward-btn';
    button.title = "Drag content here or Paste (Ctrl+V)";
    
    // Simple SVG Icon (Inbox/Down Arrow)
    button.innerHTML = `
        <svg id="origin-steward-icon" viewBox="0 0 24 24">
            <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
        </svg>
    `;
    
    const toast = document.createElement('div');
    toast.id = 'origin-steward-toast';
    
    container.appendChild(button);
    container.appendChild(toast);
    document.body.appendChild(container);
    
    return { button, toast };
}

const { button, toast } = injectUI();

// --- Toast Helper ---
function showToast(message, type = 'info') {
    toast.textContent = message;
    toast.className = type;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
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

// --- Paste Logic ---
// Listen for paste globally when button is hovered or focused? 
// Or just globally? "Zero friction" implies globally might be annoying if it conflicts.
// Let's listen globally BUT only if the user has interacted with our button recently OR if they explicitly paste ON the button?
// Requirement says: "Cmd/Ctrl + V when button is focused"
// Since it's a div, we need to make it focusable or just listen to document paste and check if mouse is over button.
// Let's try: Mouse over button -> Paste works.

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

// --- Processing Logic ---
function processItems(items) {
    if (!items || items.length === 0) return;
    
    showToast("Processing...", "info");
    
    // Prioritize: Image > URL > Text
    // This is a simplification. We might want to loop and send all?
    // For now, let's pick the "best" single item.
    
    let payload = null;
    let type = "text";
    let note = "";
    
    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        
        if (item.type.indexOf("image") !== -1) {
            // It's an image
            // We can't easily send Blob via JSON to our current simple endpoint without FormData
            // Current app.py expects JSON payload.
            // For v1, let's skip binary images unless we convert to Base64.
            // Let's try Base64 for now.
            const blob = item.getAsFile();
            const reader = new FileReader();
            reader.onload = function(event) {
                const base64 = event.target.result;
                sendToBrain("image", base64, "Image from clipboard/drop");
            };
            reader.readAsDataURL(blob);
            return; // Async handle
        } else if (item.type === "text/uri-list") {
            item.getAsString((str) => {
                sendToBrain("url", str, "Dropped URL");
            });
            return;
        } else if (item.type === "text/plain") {
             item.getAsString((str) => {
                // Check if it looks like a URL
                if (str.startsWith("http")) {
                    sendToBrain("url", str, "Dropped Text URL");
                } else {
                    sendToBrain("text", str, "Dropped Text");
                }
            });
            return;
        }
    }
}

// --- API Communication ---
function sendToBrain(type, content, note) {
    // We send message to background script to handle the actual fetch (CORS/Auth context)
    chrome.runtime.sendMessage({
        action: "drop",
        data: {
            type: type,
            payload: content,
            note: note,
            source_url: window.location.href,
            source_title: document.title
        }
    }, (response) => {
        if (response && response.success) {
            showToast("Saved to Brain!", "success");
        } else {
            showToast("Failed to save.", "error");
            console.error("Brain Error:", response ? response.error : "Unknown");
        }
    });
}
