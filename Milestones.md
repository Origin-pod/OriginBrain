# OriginSteward: Project Plan & Milestones

> **Strategy:** Build the "Ingestion Engine" first. If we can't get data *in* effortlessly, the system is useless.

---

## Milestone 1: The Foundation & "Drop Zone"
**Goal:** Establish the local storage structure and the mechanism for receiving data from the outside world.

### User Stories
*   **US-1.1:** As a user, I want a defined folder structure (`Inbox`, `Archive`, `Error`) so that I know where to put files.
*   **US-1.2:** As a user, I want a Python script that watches the `Inbox` folder for new `.json` or `.md` files.
*   **US-1.3:** As a user, I want the system to move processed files to `Archive` and failed files to `Error` with a log.

### Verification (Proof of Work)
1.  **Manual:** Drop a file named `test.json` into `Inbox/`.
2.  **Result:** File disappears from `Inbox/` and appears in `Archive/YYYY-MM-DD/`.
3.  **Automated:** Run `pytest tests/test_daemon.py`.

### Deliverables
*   `ingest_daemon.py` (File watcher).
*   Directory structure setup script.

---

## Milestone 2: The Connectors (Ingestion)
**Goal:** Build the logic to transform URLs and Tweets into clean Markdown.

### User Stories
*   **US-2.1 (Web):** As a user, when I drop a URL into the Inbox, the system should fetch the page, strip the HTML boilerplate, and save the main content as Markdown.
*   **US-2.2 (Twitter):** As a user, when I drop a Tweet URL, the system should (via `yt-dlp`) fetch the Tweet text and Author.
*   **US-2.3 (Text):** As a user, when I drop a text snippet, it is saved directly.

### Verification (Proof of Work)
1.  **Web Test:** Drop JSON `{ "type": "url", "payload": "https://example.com" }`.
    *   *Result:* `Archive/.../Example Domain.md` created with content.
2.  **Twitter Test:** Drop JSON `{ "type": "url", "payload": "https://twitter.com/..." }`.
    *   *Result:* `Archive/.../tweet_123.md` created with text and author.
3.  **Automated:** Run `pytest tests/test_connectors.py`.

### Deliverables
*   `connectors/web_scraper.py`
*   `connectors/twitter_fetcher.py`

---

## Milestone 3: The Brain (Chroma Integration)
**Goal:** Make the data searchable and "smart".

### User Stories
*   **US-3.1:** As a system, when a file is successfully ingested, I automatically generate a vector embedding for it.
*   **US-3.2:** As a system, I store this embedding in a local ChromaDB collection.
*   **US-3.3:** As a user, I can run a CLI command `os search "query"` and get semantically relevant results.

### Verification (Proof of Work)
1.  **Ingest:** Process 3 distinct notes (e.g., about "Apples", "SpaceX", "React").
2.  **Search:** Run `python main.py search "fruit"`.
3.  **Result:** The "Apples" note is returned as the top result.

### Deliverables
*   `brain/vector_store.py` (Chroma wrapper).
*   `brain/embedder.py` (Embedding model wrapper).

---

## Milestone 4: The Mobile Bridge (Client Side)
**Goal:** Enable "Capture on the Go".

### User Stories
*   **US-4.1:** As a user, I want an iOS Shortcut that accepts a "Share" input (URL/Text) and saves it as a file to my iCloud `OriginSteward/Inbox` folder.
*   **US-4.2:** As a user, I want a simple local web page (running on my Mac) where I can paste a URL if I'm on desktop.

### Deliverables
*   iOS Shortcut file (or instructions).
*   Simple Flask/Streamlit "Drop" page.

---

## Milestone 5: The Steward (Resurfacing)
**Goal:** Proactive value.

### User Stories
*   **US-5.1:** As a user, I want a "Daily Digest" that shows me 3 random or relevant notes from the past.
*   **US-5.2:** As a user, I want to ask "What have I read about X?" and get a synthesized answer (RAG).

### Deliverables
*   `steward/digest.py`
*   `steward/chat.py`
