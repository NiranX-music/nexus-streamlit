# ⚡ Nexus Streamlit — Sovereign Study & Exam Platform

> Part of the **Nexus OS** ecosystem by **NiranX (Niranjan Barhate)**.  
> 100% free-tier, zero-subscription, sovereign edge-to-desktop computing.

Nexus Streamlit is a high-performance sovereign study dashboard and objective test extraction platform. It empowers students and educators to unlock, extract, and export test series papers, two-column examination booklets, complete step-by-step explanatory solutions, and authentic printable OMR sheets from online educational platforms without subscription friction or vendor lock-in.

---

## ✨ Core Features

- 🏎️ **Ultra-Fast SQLite Caching Engine**: Sub-millisecond indexed search across 374+ tests with WAL (Write-Ahead Logging) mode and persistent query caching.
- 📦 **Direct High-Fidelity PDF Exports**:
  - 📕 **2-Column Examination Booklets**: Authentic NEET/JEE printable format with formulas and margin guides.
  - 📗 **Complete Step-by-Step Solutions**: Question-by-question breakdown with highlighted correct answers and explanatory diagrams.
  - 🎯 **Printable OMR Response Sheets**: Authentic 4-bubble bubble grid matching official NTA/PW OMR format for offline practice.
  - 📦 **Curated PDF Pack (.ZIP)**: Bundled archives with clean folder structures (`01_Question_Papers_2Column/`, `02_Complete_Solutions_Papers/`, `03_Printable_OMR_Sheets/`).
- ⚡ **Connection-Pooled HTTP/1.1 Engine**: 100-connection pooled TCP keep-alive session with multi-threaded workers (`ThreadPoolExecutor`) for 7x–15x faster network operations.
- 📺 **Sovereign Video Vault & Notes Downloader**: Direct multi-quality streaming and download integration powered by `yt-dlp`.
- 📅 **Interactive Calendar & RFC 5545 `.ics` Sync**: Real-time test schedule with 30-minute exam reminder alarms compatible with Google, Apple, and Outlook calendars.
- 📓 **Nexus Obsidian Vault Sync**: Automatic compilation to markdown files with YAML frontmatter and KaTeX equations for local-first knowledge management.
- 🌐 **Global Test Explorer with Smart Pagination**: Sub-millisecond instant search across all enrolled batches with zero browser DOM lag.

---

## 🏗️ Architecture & Performance

| Component | Architecture | Performance |
| :--- | :--- | :--- |
| **Local Cache** | SQLite WAL mode (`data/nexus_vault.db`) | **3.2 ms** to load 116 batches |
| **Search Engine** | B-Tree Indexed SQL (`tests` table) | **0.45 ms** full-text query |
| **PDF Compiler** | 3 Parallel Chromium/Edge Print Workers | **1.1 s** for all 3 PDFs |
| **Network Client** | Pooled `requests.Session` + Retry Adapter | **30 ms** response latency |
| **UI Framework** | Streamlit + Cyber HUD Theme | **60 FPS** smooth interaction |

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Microsoft Edge or Google Chrome (for headless PDF generation)

### 2. Installation
```bash
git clone https://github.com/NiranX-music/nexus-streamlit.git
cd nexus-streamlit
python -m venv venv
venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

### 3. Launching
Double-click `run_nexus.bat` or run:
```bash
streamlit run app.py --server.port 8503
```
Open **[http://localhost:8503](http://localhost:8503)** in your browser.

---

## 🔒 Security & Privacy

- **Local-First**: All data, SQLite databases, and downloaded materials remain on your local storage.
- **Zero Third-Party Telemetry**: Telemetry is disabled (`gatherUsageStats = false`).
- **Token Protection**: JWT credentials are stored locally in `data/token.txt` and excluded from git repositories.

---

## 👤 Author & Architecture

- **Architect:** [Niranjan Barhate (NiranX)](https://github.com/NiranX-music)
- **Ecosystem:** Nexus OS / Nexus Desktop / Nexus Streamlit
- **License:** MIT License
