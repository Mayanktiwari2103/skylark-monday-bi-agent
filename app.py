import json
import os
import re
from dotenv import load_dotenv
from google import genai
import pandas as pd
import requests
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="Skylark Drones - Executive BI Agent",
    page_icon="🦅",
    layout="wide",
)

# -----------------------------------------------------------------------------
# 1. MONDAY.COM DATA INGESTION & DATA RESILIENCE LAYER
# -----------------------------------------------------------------------------

def fetch_monday_board(api_key: str, board_id: str) -> pd.DataFrame:
  url = "https://api.monday.com/v2"
  headers = {
      "Authorization": api_key,
      "Content-Type": "application/json",
      "API-Version": "2024-01",
  }

  query = """
    query ($boardId: [ID!]) {
      boards (ids: $boardId) {
        name
        columns {
          id
          title
          type
        }
        items_page (limit: 500) {
          items {
            id
            name
            column_values {
              id
              text
              value
            }
          }
        }
      }
    }
    """
  response = requests.post(
      url,
      json={"query": query, "variables": {"boardId": [str(board_id)]}},
      headers=headers,
      timeout=15,
  )

  if response.status_code != 200:
    raise Exception(f"Monday API Error {response.status_code}: {response.text}")

  res_json = response.json()
  if "errors" in res_json:
    raise Exception(f"GraphQL Error: {res_json['errors']}")

  boards = res_json.get("data", {}).get("boards", [])
  if not boards:
    raise Exception(f"No board found for ID: {board_id}")

  board_data = boards[0]
  col_map = {c["id"]: c["title"] for c in board_data.get("columns", [])}

  rows = []
  for item in board_data.get("items_page", {}).get("items", []):
    row_dict = {"Item Name": item.get("name")}
    for cv in item.get("column_values", []):
      col_title = col_map.get(cv["id"], cv["id"])
      row_dict[col_title] = cv.get("text")
    rows.append(row_dict)

  return pd.DataFrame(rows)


def clean_numeric(val):
  if pd.isna(val) or val is None or str(val).strip() == "":
    return None
  val_str = str(val).replace(",", "").replace("$", "").replace("₹", "").strip()
  match = re.search(r"[-+]?\d*\.?\d+", val_str)
  if match:
    try:
      return float(match.group(0))
    except ValueError:
      return None
  return None


def clean_deals_df(df: pd.DataFrame) -> pd.DataFrame:
  if df.empty:
    return df
  clean = df.copy()

  for col in clean.columns:
    if "value" in col.lower() or "amount" in col.lower():
      clean[col + "_cleaned"] = clean[col].apply(clean_numeric)
    if "date" in col.lower():
      clean[col + "_parsed"] = pd.to_datetime(clean[col], errors="coerce")

  return clean


def clean_work_orders_df(df: pd.DataFrame) -> pd.DataFrame:
  if df.empty:
    return df
  clean = df.copy()

  for col in clean.columns:
    if any(
        k in col.lower()
        for k in ["amount", "value", "quantity", "collected", "receivable"]
    ):
      clean[col + "_cleaned"] = clean[col].apply(clean_numeric)
    if "date" in col.lower() or "month" in col.lower():
      clean[col + "_parsed"] = pd.to_datetime(clean[col], errors="coerce")

  return clean

# -----------------------------------------------------------------------------
# 2. BUSINESS INTELLIGENCE CONTEXT GENERATOR
# -----------------------------------------------------------------------------

def generate_bi_context(deals_df: pd.DataFrame, wo_df: pd.DataFrame) -> str:
  context_blocks = []

  if not deals_df.empty:
    deal_val_col = next((c for c in deals_df.columns if "masked deal value" in c.lower() and c.endswith("_cleaned")), None)
    stage_col = next((c for c in deals_df.columns if "stage" in c.lower()), None)
    sector_col = next((c for c in deals_df.columns if "sector" in c.lower()), None)

    total_deals = len(deals_df)
    total_pipeline_val = deals_df[deal_val_col].sum() if deal_val_col else "N/A"
    missing_values_count = deals_df[deal_val_col].isna().sum() if deal_val_col else 0

    sector_breakdown = deals_df.groupby(sector_col)[deal_val_col].sum().to_dict() if (sector_col and deal_val_col) else {}
    stage_breakdown = deals_df[stage_col].value_counts().to_dict() if stage_col else {}

    deals_summary = f"""
=== DEALS / SALES PIPELINE DATA ===
- Total Deals: {total_deals}
- Aggregate Pipeline Value: ₹{total_pipeline_val:,.2f} (Note: {missing_values_count} deals have missing/unspecified values)
- Pipeline by Sector: {json.dumps(sector_breakdown, default=str)}
- Deals by Stage: {json.dumps(stage_breakdown, default=str)}
"""
    context_blocks.append(deals_summary)

  if not wo_df.empty:
    wo_val_col = next((c for c in wo_df.columns if "amount in rupees (excl" in c.lower() and c.endswith("_cleaned")), None)
    billed_col = next((c for c in wo_df.columns if "billed value" in c.lower() and c.endswith("_cleaned")), None)
    exec_status_col = next((c for c in wo_df.columns if "execution status" in c.lower()), None)
    wo_sector_col = next((c for c in wo_df.columns if "sector" in c.lower()), None)

    total_wos = len(wo_df)
    total_wo_val = wo_df[wo_val_col].sum() if wo_val_col else 0
    total_billed = wo_df[billed_col].sum() if billed_col else 0
    status_dist = wo_df[exec_status_col].value_counts().to_dict() if exec_status_col else {}
    sector_ops = wo_df.groupby(wo_sector_col)[wo_val_col].sum().to_dict() if (wo_sector_col and wo_val_col) else {}

    wo_summary = f"""
=== WORK ORDERS / PROJECT EXECUTION DATA ===
- Total Work Orders: {total_wos}
- Total Work Order Committed Value (Excl GST): ₹{total_wo_val:,.2f}
- Total Value Billed to Date: ₹{total_billed:,.2f}
- Execution Status Distribution: {json.dumps(status_dist, default=str)}
- Work Order Value by Sector: {json.dumps(sector_ops, default=str)}
"""
    context_blocks.append(wo_summary)

  return "\n".join(context_blocks)

# -----------------------------------------------------------------------------
# 3. AI AGENT REASONING ENGINE (GEMINI 2.5 FLASH)
# -----------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are Skylark Drones' Executive Business Intelligence AI Agent.
You serve founders and C-suite leadership by synthesizing live data from Monday.com boards (Deals & Work Orders).

Your core guidelines:
1. Deliver executive-ready, strategic insights with concise takeaways, not just raw numbers.
2. Cross-reference Deals (Sales) and Work Orders (Operations) to assess revenue health, delivery risk, and sector performance.
3. Be resilient to messy real-world data: highlight data caveats, missing metrics, or format assumptions directly.
4. If a founder query is overly ambiguous, provide the best logical interpretation first, then ask a precise clarifying follow-up question.
5. Format responses with clean Markdown: bullet points, clear metric highlights, and tables where comparative data adds clarity.
"""

def query_agent(messages, deals_df: pd.DataFrame, wo_df: pd.DataFrame, gemini_api_key: str) -> str:
  """Interprets business queries and provides insights using Google Gemini API."""
  client = genai.Client(api_key=gemini_api_key)

  bi_context = generate_bi_context(deals_df, wo_df)
  deals_sample = deals_df.head(10).to_dict(orient="records")
  wo_sample = wo_df.head(10).to_dict(orient="records")
  
  history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages[:-1]])
  current_user_query = messages[-1]['content']

  full_prompt = f"""{SYSTEM_PROMPT}

LIVE DATASET CONTEXT FROM MONDAY.COM:
{bi_context}

SAMPLE DATA RECORDS:
Deals: {json.dumps(deals_sample, default=str)}
Work Orders: {json.dumps(wo_sample, default=str)}

---
CONVERSATION HISTORY:
{history_text}

---
CURRENT QUERY:
User: {current_user_query}
Assistant:"""

  response = client.models.generate_content(
      model="gemini-2.5-flash",
      contents=full_prompt,
  )
  
  return response.text

# -----------------------------------------------------------------------------
# 4. STREAMLIT USER INTERFACE
# -----------------------------------------------------------------------------

# Load credentials securely in the background
api_key = os.getenv("MONDAY_API_KEY", "")
deals_id = os.getenv("DEALS_BOARD_ID", "")
wo_id = os.getenv("WORK_ORDERS_BOARD_ID", "")
gemini_key = os.getenv("GEMINI_API_KEY", "")

with st.sidebar:
  st.header("⚡ Leadership Actions")

  refresh_btn = st.button("🔄 Sync Live Monday.com Data", use_container_width=True)

  st.markdown("---")
  st.markdown("### 📊 Quick Query Presets")
  q_pipeline = st.button("📈 Energy Pipeline Health", use_container_width=True)
  q_exec_summary = st.button("📑 Leadership Briefing", use_container_width=True)
  q_revenue_leakage = st.button("⚠️ Unbilled Work Orders & AR Risk", use_container_width=True)

  st.markdown("---")
  st.caption("🔒 Connected via Secure Backend Secrets")

if "deals_df" not in st.session_state or refresh_btn:
  if api_key and deals_id and wo_id:
    with st.spinner("Dynamically querying Monday.com GraphQL API..."):
      try:
        raw_deals = fetch_monday_board(api_key, deals_id)
        raw_wo = fetch_monday_board(api_key, wo_id)

        st.session_state.deals_df = clean_deals_df(raw_deals)
        st.session_state.wo_df = clean_work_orders_df(raw_wo)
        st.sidebar.success(f"✅ Synced: {len(st.session_state.deals_df)} Deals | {len(st.session_state.wo_df)} Work Orders")
      except Exception as e:
        st.sidebar.error(f"Error fetching data: {str(e)}")
  else:
    st.sidebar.warning("Please ensure your `.env` file contains the Monday API Key and Board IDs.")

st.title("🦅 Skylark Drones - Monday.com BI Agent")
st.caption("Conversational Executive Assistant & Cross-Board Analytics for Founders")

if "messages" not in st.session_state:
  st.session_state.messages = [{
      "role": "assistant",
      "content": "Hello! I am your Skylark Drones BI Agent, powered by Google Gemini 2.5 Flash. How can I assist with pipeline health, operational metrics, or leadership reports today?",
  }]

for msg in st.session_state.messages:
  with st.chat_message(msg["role"]):
    st.markdown(msg["content"])

def process_user_query(user_prompt: str):
  st.session_state.messages.append({"role": "user", "content": user_prompt})
  with st.chat_message("user"):
    st.markdown(user_prompt)

  if "deals_df" not in st.session_state or st.session_state.deals_df is None or not gemini_key:
    with st.chat_message("assistant"):
      st.error("Please verify Monday.com data is synced and your Gemini API Key is configured in your `.env` file.")
    return

  with st.chat_message("assistant"):
    with st.spinner("Analyzing cross-board intelligence..."):
      try:
        agent_reply = query_agent(
            st.session_state.messages,
            st.session_state.deals_df,
            st.session_state.wo_df,
            gemini_key,
        )
        st.markdown(agent_reply)
        st.session_state.messages.append({"role": "assistant", "content": agent_reply})
      except Exception as err:
        st.error(f"Agent execution failed: {str(err)}")

if q_pipeline:
  process_user_query("How is our sales pipeline looking for the energy/powerline/renewables sector this quarter? Provide revenue projections and stage distribution.")
elif q_exec_summary:
  process_user_query("Generate an executive briefing for our leadership update. Include top-line pipeline numbers, active operational work order status, and key data caveats.")
elif q_revenue_leakage:
  process_user_query("Identify potential revenue leakage: which work orders are completed but have unbilled balances or high accounts receivable (AR) risk?")

if prompt := st.chat_input("Ask a question (e.g. 'What is our total unbilled work order value across Mining?')"):
  process_user_query(prompt)