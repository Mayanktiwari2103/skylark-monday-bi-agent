# Executive BI Agent – Architectural & Decision Log

**Project:** Skylark Drones Executive Monday.com BI Agent  
**Author:** Candidate  
**Date:** August 2024  

---

## 1. Interpretation of "Leadership Updates"
Leadership updates for executive stakeholders (Founders, CEO, C-suite) must not simply parrot raw database queries; they require actionable, synthesized intelligence across sales velocity and operational fulfillment.

* **Dual-Board Synthesis:** Ingested data is framed around two critical vectors:
  * **Top-of-Funnel Pipeline (Deals Board):** Quantifying aggregate pipeline volume, sector-wise concentration, and stage velocity.
  * **Operational Realization (Work Orders Board):** Measuring committed values, execution statuses, billed progress, and revenue realization velocity.
* **Risk & Exposure Flagging:** Leadership updates emphasize revenue leakage—specifically identifying completed work orders with unbilled amounts and flagging high Accounts Receivable (AR) exposures.
* **Executive Brevity & Data Caveats:** Formatted with high-level summaries and explicit notifications regarding data hygiene (e.g., highlighting missing deal values rather than omitting them).

---

## 2. Key Assumptions Made
1. **Schema Structure & Column Naming:** Assumed that board column titles contain semantic keywords (e.g., `deal value`, `stage`, `execution status`, `billed value`, `sector`). Dynamic regex matching is used rather than static column IDs to remain resilient to Monday.com schema mutations.
2. **Currency & Unit Consistency:** Ingested figures are assumed to be in INR (₹), with commas, dollar/rupee symbols, and trailing string annotations stripped deterministically.
3. **Data Completeness Caveats:** Assumed that missing deal values indicate incomplete data capture rather than zero-value deals; the agent explicitly reports these counts to prevent skewed averages.
4. **Session Scope:** Assumed executive sessions are query-driven; in-memory chat session states persist context across follow-ups without requiring external database persistence.

---

## 3. Trade-offs Chosen and Rationales

| Decision / Trade-off | Option Chosen | Alternative Considered | Rationale |
| :--- | :--- | :--- | :--- |
| **Data Ingestion Protocol** | Direct Monday.com GraphQL API (`/v2`) | Model Context Protocol (MCP) Server | Direct API integration removes external container dependencies, enables lightweight Streamlit deployment, and guarantees deterministic data hygiene pipelines. |
| **LLM Reasoning Engine** | Google Gemini 2.5 Flash via `google-genai` SDK | OpenAI GPT-4o / Local Ollama | Gemini 2.5 Flash offers low-latency inference, cost-effective pricing, and a native large context window to process tabular summaries and row-level samples simultaneously. |
| **UI & Hosting Framework** | Streamlit + Streamlit Community Cloud | React/Next.js + FastAPI | Allows full-stack Python development within the 6-hour time limit while natively providing reactive conversational components and secret management. |
| **Data Preprocessing Layer** | In-Memory Pandas + Regex Normalization | Raw LLM Text Parsing | Cleans malformed strings and pre-calculates aggregates deterministically before feeding context to the LLM, eliminating mathematical hallucinations. |

---

## 4. What Would Be Done Differently With More Time
1. **Relational Record Matching (Entity Resolution):** Implement fuzzy entity matching between Deals and Work Orders using Client Codes or Company Names to generate a unified, end-to-end deal-to-cash lifecycle graph.
2. **Automated Monday.com Webhooks:** Replace manual/interval polling with webhook triggers so board modifications automatically invalidate caches and update metrics in real time.
3. **Interactive Visualizations:** Integrate interactive Plotly charts directly inside agent responses to accompany textual summaries.
4. **Automated Monday.com Action Execution:** Expand agent capabilities to perform write operations (e.g., flagging stalled deals or triggering notification updates directly inside Monday.com via mutations).