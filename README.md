# 🦅 Skylark Drones – Executive Monday.com BI Agent

An AI-powered conversational Business Intelligence assistant that bridges Monday.com sales pipeline and work order execution boards to provide real-time strategic insights for leadership.

---

## 🔗 Live Hosted Demo
* **Working Prototype Link:** [PASTE_YOUR_STREAMLIT_CLOUD_URL_HERE]
* *(No local setup required. Runs securely on Streamlit Community Cloud.)*

---

## 🏛️ Architecture Overview

```text
┌─────────────────────────┐       ┌─────────────────────────┐
│       Monday.com        │       │       Monday.com        │
│    Sales Deals Board    │       │   Work Orders Board     │
└────────────┬────────────┘       └────────────┬────────────┘
             │ (GraphQL API /v2)               │ (GraphQL API /v2)
             └────────────────┬────────────────┘
                              ▼
        ┌──────────────────────────────────────────────┐
        │  Data Ingestion & Resilience Layer (Python)  │
        │  - Regex currency sanitization               │
        │  - Date parsing & missing value detection    │
        │  - Deterministic aggregate generation        │
        └─────────────────────┬────────────────────────┘
                              ▼
        ┌──────────────────────────────────────────────┐
        │       AI Reasoning Engine (Google Gemini)    │
        │  - Gemini 2.5 Flash via `google-genai`       │
        │  - Dual-board correlation & synthesis        │
        │  - Leadership insight & risk detection       │
        └─────────────────────┬────────────────────────┘
                              ▼
        ┌──────────────────────────────────────────────┐
        │        Streamlit Conversational UI           │
        │  - Executive quick query triggers            │
        │  - Interactive follow-up chat                │
        └──────────────────────────────────────────────┘

## ⚙️ Monday.com Configuration & Setup

### 1. Retrieve Monday.com API Token
1. Log in to your [Monday.com](https://monday.com) account.
2. Click your **Profile avatar** (bottom-left or top-right) $\rightarrow$ **Administration** (or **Developers**).
3. Navigate to **API** $\rightarrow$ Copy your **Personal API Token**.

### 2. Locate Board IDs
1. Open your **Deals** board in your browser.
2. Copy the numeric ID from the address bar: `https://<workspace>.monday.com/boards/<DEALS_BOARD_ID>`.
3. Open your **Work Orders** board and copy its numeric ID: `https://<workspace>.monday.com/boards/<WORK_ORDERS_BOARD_ID>`.

---

## 💻 Local Run Instructions

### Prerequisites
* Python 3.10+
* Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))
* Monday.com API Key & Board IDs

### Installation Steps
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/](https://github.com/)<your-username>/<your-repo-name>.git
   cd <your-repo-name>