# OriginBrain Enhanced Chrome Extension

## Overview

The OriginBrain Enhanced Chrome Extension provides advanced capture and consumption management capabilities, seamlessly integrating with your OriginBrain instance to make knowledge capture and review frictionless.

## New Features in v2.0

### 1. Real-time Sync Status
- Visual indicators showing connection status
- Automatic health checks with server
- Badge notifications for sync status

### 2. Consumption Management
- Quick consumption panel showing recent captures
- One-click status updates (Reading, Reviewed, Applied)
- Visual indicators for importance scores
- Queue count badge on extension icon

### 3. Enhanced Capture Options
- High-priority marking for important content
- Save for later review option
- Bulk capture support
- Image capture with metadata

### 4. Keyboard Shortcuts
- `Ctrl/Cmd+Shift+S`: Quick capture current page
- `Ctrl/Cmd+Shift+P`: Toggle consumption panel
- `Ctrl/Cmd+V` on button: Paste content

### 5. Export Functionality
- Export artifacts directly from context menu
- Support for JSON and Markdown formats
- One-click download

### 6. Visual Enhancements
- Red/Green consumption status indicators
- Animated status dots
- Responsive design for all screen sizes
- Modern gradient design

## Installation

1. Clone or download the OriginBrain repository
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" in the top right
4. Click "Load unpacked" and select the `chrome_extension` directory
5. Ensure the enhanced files are being used:
   - `enhanced_manifest.json`
   - `enhanced_background.js`
   - `enhanced_content.js`
   - `enhanced_styles.css`

## Usage

### Basic Capture
- **Drag & Drop**: Drag content onto the capture button
- **Paste**: Hover over button and press Ctrl/Cmd+V
- **Context Menu**: Right-click any content and select "Save to Brain"
- **Keyboard**: Press Ctrl/Cmd+Shift+S to capture current page

### Enhanced Features
- **High Priority Save**: Right-click → "Save as High Priority"
- **For Review**: Right-click → "Save for Later Review"
- **View Queue**: Click extension icon with Shift or use context menu
- **Update Status**: Open consumption panel and click status buttons

### Consumption Panel
1. **Shift+Click** the capture button or use Ctrl/Cmd+Shift+P
2. View your recent captures with importance scores
3. Click status buttons to update consumption status
4. Use "Mark All Reviewed" for bulk updates
5. Click "View Dashboard" for detailed management

## Visual Indicators

### Status Dots
- 🟢 **Green**: Online and synced
- 🟡 **Yellow**: Processing/syncing
- 🔴 **Red**: Offline or error
- ⚪ **Gray**: Disconnected

### Consumption Status
- 🔴 **Red**: Unconsumed
- 🟡 **Yellow**: Reading
- 🔵 **Blue**: Reviewed
- 🟢 **Green**: Applied

### Importance Scores
- 🔴 **High** (8-10): Critical content
- 🟠 **Medium-High** (6-7): Important
- 🟡 **Medium** (4-5): Useful
- 🟢 **Low** (0-3): Reference

## Context Menu Options

### Capture Options
- **Save to Brain**: Standard save
- **Save as High Priority**: Mark with importance 9/10
- **Save for Later Review**: Mark with importance 5/10

### Actions
- **Open OriginBrain Dashboard**: Launch web interface
- **View Consumption Queue**: Open queue view
- **Export Artifacts as JSON**: Download JSON export
- **Export Artifacts as Markdown**: Download Markdown export

## Configuration

### Server Settings
Update the API URLs in the enhanced files if your OriginBrain instance runs on different ports:
- `enhanced_background.js`: Lines 3-4
- `enhanced_content.js`: Line 4

### Permissions
The extension requires:
- `activeTab`: Access current tab content
- `contextMenus`: Add right-click options
- `storage`: Save preferences
- `scripting`: Inject UI elements
- `notifications`: Show save confirmations
- `downloads`: Handle exports
- `tabs`: Open dashboard

## Troubleshooting

### Extension Not Working
1. Check if OriginBrain server is running on localhost:5002
2. Verify all enhanced files are in place
3. Reload the extension from chrome://extensions/

### Sync Issues
1. Check badge color (should be green)
2. Verify network connectivity
3. Check browser console for errors

### Consumption Panel Not Loading
1. Check API connection
2. Verify consumption endpoints are working
3. Look for console errors

## Development

### File Structure
```
chrome_extension/
├── enhanced_manifest.json     # Manifest v3 with new permissions
├── enhanced_background.js     # Background service worker
├── enhanced_content.js        # Content script with UI
├── enhanced_styles.css        # Styling for new features
├── icon.png                   # Extension icon
├── README_ENHANCED.md         # This file
└── original files...          # Backup of v1.0 files
```

### Testing
1. Load extension in developer mode
2. Open OriginBrain dashboard
3. Test various capture methods
4. Verify consumption panel updates
5. Check export functionality

## Updates from v1.0

### Added
- Real-time sync status
- Consumption management panel
- Keyboard shortcuts
- Export functionality
- Enhanced context menu options
- Visual status indicators
- Badge count updates
- Importance score display
- Bulk operations

### Improved
- Faster processing
- Better error handling
- Responsive design
- Modern UI aesthetics
- More capture options

## Support

For issues or feature requests:
1. Check the OriginBrain documentation
2. Review console errors in browser
3. Verify server connectivity
4. Report issues on GitHub

## Privacy

The extension:
- Only communicates with your local OriginBrain instance
- Does not send data to external services
- Stores minimal preferences locally
- Requires explicit user action for captures