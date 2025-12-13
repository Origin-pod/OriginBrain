# OriginSteward: Product Requirements Document (PRD)

> **Version:** 2.0 (Lean & Connector-Focused)  
> **Status:** Active  
> **Last Updated:** 2025-12-13  

---

## 1. Executive Summary

**OriginSteward** is a local-first, AI-assisted cognitive stewardship system. It solves "Context Decay" by ingesting your digital exhaust (Twitter bookmarks, web reading, random thoughts) and transforming it into a semantic knowledge base.

**The "One Thing" (Core Value):**
The system must **effortlessly ingest** content from anywhere (Mobile, Web) and **meaningfully resurface** it later. If capture is high-friction, the system fails. If retrieval is just keyword search, it fails.

---

## 2. The "Lean" Scope (Shreyas Doshi's Lens)

We are cutting all features that do not directly contribute to the **Ingest → Steward → Retrieve** loop.

*   **CUT:** "Emotional Context" tracking (Low leverage, high friction).
*   **CUT:** "Personal Agents" / Autonomous decision making (High complexity, unproven value).
*   **CUT:** Complex custom mobile app UI (High overhead). **REPLACE WITH:** iOS Shortcuts / PWA.
*   **FOCUS:** Robust Connectors & Vector Search.

---

## 3. Functional Requirements: The Connectors

The system is defined by its inputs. We need a unified "Ingestion Pipeline" that normalizes diverse data sources into a standard Artifact format.

### 3.1 Connector A: Twitter (High Priority)
*   **Constraint:** The user has **two specific Twitter accounts**.
*   **Primary Mechanism (Push):** User shares a Tweet URL to the system (via iOS Share Sheet or "Drop Zone").
    *   **Tooling:** System uses `yt-dlp` (which supports X/Twitter) to fetch the Tweet text, author, and media metadata.
    *   **Fallback:** If `yt-dlp` fails (e.g., rate limits), the system saves the raw URL with a `#to_read` tag.
*   **Secondary Mechanism (Pull - Future):** Periodic scraping of bookmarks is deferred due to API costs/instability.
*   **Data Captured:** Full text, Author Handle, Timestamp, Media URLs.

### 3.2 Connector B: The Web (Article/Link Dump)
*   **Source:** URLs dropped from Mobile or Desktop browsers.
*   **Action:**
    *   **Fetch:** System visits the URL using `requests`.
    *   **Parse:** Extracts main content using `readability-lxml` (removes ads/nav).
    *   **Format:** Converts HTML to Markdown using `markdownify`.
    *   **Store:** Saves as `Archive/YYYY-MM-DD/Title.md`.
*   **Input Methods:**
    *   **Mobile:** iOS Share Sheet -> Save JSON to iCloud Drive.
    *   **Desktop:** Copy URL -> Paste into local "Drop Zone" web interface.

### 3.3 Connector C: Raw Text / Quick Capture
*   **Source:** Mobile notes, quick thoughts, copy-pastes.
*   **Action:** Immediate storage as a timestamped "Note" artifact.
*   **Format:** Simple Markdown file with Frontmatter.

---

## 4. User Flows & Architecture

### 4.1 The "Drop Zone" Architecture (Bridging Mobile & Local)
To maintain "Local-First" sovereignty while enabling "Mobile Capture," we use a **Sync-Based Ingestion Queue**.

1.  **Capture (Mobile/Web):**
    *   User uses an **iOS Shortcut** or **Simple Web Form**.
    *   Data (URL or Text) is saved as a JSON/MD file to a cloud-synced folder (iCloud Drive / Dropbox) designated as the `Inbox`.
2.  **Ingestion (Mac Host):**
    *   OriginSteward Daemon watches the `Inbox` folder.
    *   **Detects** new file.
    *   **Processes** (Scrapes URL, Formats Tweet).
    *   **Embeds** (Vectorizes content via Chroma).
    *   **Moves** to permanent storage (`/Brain/Archive`).

### 4.2 Retrieval (The "Steward")
*   **Semantic Search:** "Show me that thread about distributed systems."
*   **Contextual Resurfacing:** "You are reading about React. Here are 3 Twitter bookmarks from 2023 about React Performance."

---

## 5. Data Model (Simplified)

Every input becomes an **Artifact**.

```json
{
  "id": "uuid",
  "type": "tweet | article | note",
  "content": "Full text content...",
  "source_url": "https://...",
  "created_at": "ISO-8601",
  "embedding_status": "indexed",
  "metadata": {
    "author": "@shreyas",
    "tags": ["product", "strategy"]
  }
}
```

---

## 6. Success Metrics (The "High Leverage" Check)

*   **Capture Friction:** Time to drop a link/tweet < 3 seconds.
*   **Ingest Reliability:** 100% of dropped links are processed or flagged with an error (no silent failures).
*   **Retrieval Accuracy:** Top 3 semantic results contain the target artifact 90% of the time.
