"""
FuturesBot Live Terminal — app.py
Streamlit trading dashboard for the Binance Futures Demo Trading Bot.

Backend wiring:
  BinanceClient   — bot.client
  place_order     — bot.orders
  setup_logging   — bot.logging_config

Live prices are fetched from the Binance Futures Testnet public REST API
(no authentication required for ticker endpoints).
Order history is stored in Streamlit session state for the current session only.
"""

import os
import datetime
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from bot.client import BinanceClient, BinanceAPIError
from bot.logging_config import setup_logging
from bot.orders import place_order

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FuturesBot Live Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE  (no seeded / placeholder data)
# ─────────────────────────────────────────────────────────────────────────────
if "selected_symbol" not in st.session_state: st.session_state.selected_symbol = "BTCUSDT"
if "order_result"    not in st.session_state: st.session_state.order_result    = None
if "order_error"     not in st.session_state: st.session_state.order_error     = None
if "orders_history"  not in st.session_state: st.session_state.orders_history  = []

# ─────────────────────────────────────────────────────────────────────────────
# BACKEND — single initialisation, cached for the session lifetime
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _init_backend():
    load_dotenv()
    key    = os.getenv("BINANCE_API_KEY",    "")
    secret = os.getenv("BINANCE_API_SECRET", "")
    client = BinanceClient(key, secret)
    logger = setup_logging()
    return client, logger, bool(key and secret)

client, logger, creds_ok = _init_backend()

# ─────────────────────────────────────────────────────────────────────────────
# LIVE MARKET DATA — Binance Futures Testnet public ticker endpoint
# ─────────────────────────────────────────────────────────────────────────────
TESTNET = "https://testnet.binancefuture.com"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

@st.cache_data(ttl=6, show_spinner=False)
def fetch_ticker(symbol: str) -> dict:
    """Fetch 24-hr stats for *symbol* from the Binance Futures Testnet.

    Uses the public unauthenticated endpoint — /fapi/v1/ticker/24hr.
    Falls back to zeros on any network error so the UI never crashes.
    """
    try:
        r = requests.get(
            f"{TESTNET}/fapi/v1/ticker/24hr",
            params={"symbol": symbol},
            timeout=5,
        ).json()
        return {
            "price":  float(r.get("lastPrice",          0)),
            "change": float(r.get("priceChangePercent",  0)),
            "volume": float(r.get("quoteVolume",         0)),
            "high":   float(r.get("highPrice",           0)),
            "low":    float(r.get("lowPrice",            0)),
        }
    except Exception:
        return {"price": 0.0, "change": 0.0, "volume": 0.0, "high": 0.0, "low": 0.0}

def _fmt(n, d=2): return f"{n:,.{d}f}"

def get_display_price(order: dict) -> str:
    """Robust price fallback chain: avgPrice -> price -> MARKET -> —"""
    ap = order.get("avgPrice")
    if ap is not None and ap != "":
        try:
            ap_f = float(ap)
            if ap_f > 0:
                return f"${_fmt(ap_f)}"
        except (ValueError, TypeError):
            pass

    p = order.get("price")
    if p is not None and p != "":
        try:
            p_f = float(p)
            if p_f > 0:
                return f"${_fmt(p_f)}"
        except (ValueError, TypeError):
            pass

    o_type = order.get("type")
    if o_type == "MARKET":
        return "MARKET"

    return "—"

# Fetch all tickers once per render cycle (TTL=6s cache prevents hammering)
tickers = {s: fetch_ticker(s) for s in SYMBOLS}
btc = tickers["BTCUSDT"]
eth = tickers["ETHUSDT"]
bnb = tickers["BNBUSDT"]

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS  (identical to the designed UI — untouched)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

/* --- MAIN ENVIRONMENT WRAPPERS --- */
.stApp {
    background-color: #0B1220 !important;
    color: #E2E8F0 !important;
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}

/* Hide standard streamlit UI elements completely */
[data-testid="stHeader"] {
    background-color: transparent !important;
}
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display:none;}
[data-testid="stToolbar"] {display: none;}
[data-testid="stStatusWidget"] {display: none;}

/* Adjust container padding for sleek, high-density dashboard grid */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    max-width: 1300px !important;
}

/* --- THEME COLORS & TYPOGRAPHY UTILS --- */
.text-success { color: #4ADE80 !important; font-weight: 600; }
.text-danger { color: #F87171 !important; font-weight: 600; }
.text-warning { color: #F59E0B !important; font-weight: 600; }
.text-primary { color: #3B82F6 !important; font-weight: 600; }
.mono-font { font-family: 'JetBrains Mono', monospace !important; }

/* Pulse animation for Live connections */
@keyframes glow-pulse {
    0% { opacity: 0.6; box-shadow: 0 0 4px rgba(34, 197, 94, 0.4); }
    50% { opacity: 1; box-shadow: 0 0 12px rgba(34, 197, 94, 0.8); }
    100% { opacity: 0.6; box-shadow: 0 0 4px rgba(34, 197, 94, 0.4); }
}

@keyframes slide-up {
    from { transform: translateY(8px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}

/* --- SLEEK NAVBAR SPECIFICATION --- */
.navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(11, 18, 32, 0.8);
    border-bottom: 1px solid #1E293B;
    padding: 14px 24px;
    margin-bottom: 24px;
    backdrop-filter: blur(12px);
    z-index: 10;
}
.nav-left {
    display: flex;
    align-items: center;
    gap: 16px;
}
.logo-icon-box {
    width: 32px;
    height: 32px;
    background-color: #3B82F6;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    color: white;
    font-style: italic;
    font-size: 16px;
}
.nav-title {
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    font-size: 20px;
    letter-spacing: -0.025em;
    color: #FFFFFF;
}
.nav-title-span {
    color: #3B82F6;
}
.demo-badge-sleek {
    border: 1px solid rgba(245, 158, 11, 0.3);
    background-color: rgba(245, 158, 11, 0.1);
    color: #F59E0B;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.nav-center {
    display: flex;
    gap: 32px;
}
.price-ticker {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
}
.ticker-lbl {
    font-size: 10px;
    color: #64748B;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.025em;
}
.ticker-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    font-weight: 700;
}
.nav-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-left: 16px;
    border-left: 1px solid #1E293B;
}
.status-dot {
    width: 8px;
    height: 8px;
    background-color: #22C55E;
    border-radius: 50%;
    animation: glow-pulse 1.8s infinite;
}
.status-txt {
    font-size: 11px;
    font-weight: 600;
    color: #94A3B8;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* --- COMPONENT CARDS --- */
.trade-card {
    background: #111827;
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 18px;
    backdrop-filter: blur(8px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    transition: border-color 0.2s ease;
}
.trade-card:hover {
    border-color: #334155;
}
.card-header-term {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 700;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid #1E293B;
    padding-bottom: 10px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Watchlist Item Selection Design */
.crypto-card {
    background: transparent;
    border-bottom: 1px solid rgba(30, 41, 59, 0.5);
    padding: 14px 16px;
    transition: all 0.2s ease;
    height: 88px;
    box-sizing: border-box;
}
.crypto-card:hover {
    background: rgba(30, 41, 59, 0.3);
}

/* Position and size the stButton container to overlay the card invisibly */
div[data-testid="column"]:nth-of-type(1) div[data-testid="element-container"]:has(.stButton) {
    margin-top: -1rem !important;
    height: 0px !important;
}

div[data-testid="column"]:nth-of-type(1) .stButton {
    position: absolute !important;
    margin-top: -88px !important;
    height: 88px !important;
    width: 100% !important;
    z-index: 10 !important;
}

div[data-testid="column"]:nth-of-type(1) .stButton button {
    opacity: 0 !important;
    width: 100% !important;
    height: 88px !important;
    border: none !important;
    background: transparent !important;
    cursor: pointer !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* Custom hover highlight on card when the button overlay is hovered */
div[data-testid="column"]:nth-of-type(1) div[data-testid="element-container"]:has(+ div[data-testid="element-container"] .stButton button:hover) .crypto-card {
    background: rgba(30, 41, 59, 0.3) !important;
}

/* Trading parameters summary */
.summary-box {
    background: #0B1220;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 14px;
    margin-bottom: 14px;
}

/* Streamlit Native Overrides to match Sleek Theme drop shadows & colors */
div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex !important;
    background-color: #0F172A !important;
    border-radius: 8px !important;
    padding: 3px !important;
    border: 1px solid #1E293B !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] label {
    flex: 1 !important;
    justify-content: center !important;
    padding: 6px 12px !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] label[data-baseweb="radio"] div:first-child {
    display: none !important;
}

/* High contrast modern Inputs configuration */
div[data-baseweb="input"] {
    background-color: #0F172A !important;
    border: 1px solid #1E293B !important;
    border-radius: 8px !important;
}
div[data-baseweb="input"]:focus-within {
    border-color: #3B82F6 !important;
}

/* Submit order button wrappers and action handlers */
div.place-order-wrapper button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.025em;
    text-transform: uppercase;
    padding: 12px 16px !important;
    border-radius: 8px !important;
    color: #FFFFFF !important;
    width: 100% !important;
    border: none !important;
    transition: all 0.2s ease !important;
}

/* --- FEEDBACK STATUS NOTIFICATION CARD --- */
.status-bill {
    border-radius: 8px;
    padding: 14px;
    background: #0F172A;
    border: 1px solid #1E293B;
    margin-top: 14px;
    animation: slide-up 0.2s ease-out;
}
.status-bill-success {
    border-left: 2px solid #22C55E;
    background: rgba(34, 197, 94, 0.05);
}
.status-bill-rejected {
    border-left: 2px solid #EF4444;
    background: rgba(239, 68, 68, 0.05);
}

/* --- FINTECH DATA TABLES SPECIFICATION --- */
.trading-table-container {
    background: #111827;
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 0px;
    overflow: hidden;
    margin-top: 16px;
}
.fintech-table {
    width: 100%;
    border-collapse: collapse;
}
.fintech-table th {
    color: #64748B;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 12px 18px;
    text-align: left;
    background: #0F172A;
    border-bottom: 2px solid #1E293B;
}
.fintech-table td {
    padding: 14px 18px;
    font-size: 13px;
    color: #E2E8F0;
    border-bottom: 1px solid #1E293B;
}
.fintech-table tr:hover {
    background: rgba(30, 41, 59, 0.3);
}

.badge-filled {
    background: rgba(34, 197, 94, 0.1);
    color: #4ADE80;
    border: 1px solid rgba(34, 197, 94, 0.2);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
}
.badge-rejected {
    background: rgba(239, 68, 68, 0.1);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.2);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
}
.badge-buy {
    color: #4ADE80;
    font-weight: 700;
    background: rgba(34, 197, 94, 0.08);
    padding: 2px 6px;
    border-radius: 4px;
}
.badge-sell {
    color: #F87171;
    font-weight: 700;
    background: rgba(239, 68, 68, 0.08);
    padding: 2px 6px;
    border-radius: 4px;
}

/* Session stat rows */
.stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid #1E293B;
    font-size: 13px;
}
.stat-row:last-child { border-bottom: none; }
.stat-label { color: #64748B; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TOP NAVIGATION BAR — live prices from fetch_ticker()
# ─────────────────────────────────────────────────────────────────────────────
btc_cls = "text-success" if btc["change"] >= 0 else "text-danger"
eth_cls = "text-success" if eth["change"] >= 0 else "text-danger"
bnb_cls = "text-success" if bnb["change"] >= 0 else "text-danger"
conn_label = "Connected • Binance Futures Testnet" if creds_ok else "Credentials Missing"

st.markdown(f"""
<div class="navbar">
    <div class="nav-left">
        <div class="logo-icon-box">F</div>
        <span class="nav-title">Futures<span class="nav-title-span">Bot</span></span>
        <span class="demo-badge-sleek">Demo / Testnet</span>
    </div>
    <div class="nav-center">
        <div class="price-ticker">
            <span class="ticker-lbl">BTCUSDT</span>
            <span class="ticker-val {btc_cls}">${_fmt(btc['price'])}</span>
        </div>
        <div class="price-ticker">
            <span class="ticker-lbl">ETHUSDT</span>
            <span class="ticker-val {eth_cls}">${_fmt(eth['price'])}</span>
        </div>
        <div class="price-ticker">
            <span class="ticker-lbl">BNBUSDT</span>
            <span class="ticker-val {bnb_cls}">${_fmt(bnb['price'])}</span>
        </div>
    </div>
    <div class="nav-right">
        <div class="nav-status">
            <span class="status-dot"></span>
            <span class="status-txt">{conn_label}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TRADINGVIEW CHART  — live symbol, dark theme, 400 px
# ─────────────────────────────────────────────────────────────────────────────
_tv_sym = f"BINANCE:{st.session_state.selected_symbol}"
_chart_html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ margin:0; padding:0; background:#0B1220; }}
  #tv_chart_wrap {{
    width: 100%;
    height: 400px;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #1E293B;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  }}
  .tradingview-widget-container, #tv_chart {{ height:100%; width:100%; }}
</style>
</head>
<body>
<div id="tv_chart_wrap">
  <div class="tradingview-widget-container">
    <div id="tv_chart"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    new TradingView.widget({{
      autosize: true,
      symbol: "{_tv_sym}",
      interval: "15",
      timezone: "Asia/Kolkata",
      theme: "dark",
      style: "1",
      locale: "en",
      toolbar_bg: "#111827",
      backgroundColor: "rgba(11,18,32,1)",
      gridColor: "rgba(30,41,59,0.6)",
      enable_publishing: false,
      hide_side_toolbar: false,
      allow_symbol_change: false,
      hide_legend: false,
      save_image: false,
      container_id: "tv_chart"
    }});
    </script>
  </div>
</div>
</body>
</html>
"""
components.html(_chart_html, height=418)

st.markdown("<div style='margin-bottom:4px;'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN THREE-COLUMN LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
col_left, col_center, col_right = st.columns([1, 1.1, 1.1])

# ═══════════════════════════════════════════════════════════════════════════
# LEFT — Watchlist
# ═══════════════════════════════════════════════════════════════════════════
with col_left:
    st.markdown("""
    <div class="trade-card">
        <div class="card-header-term">
            <span>📊 Market Watchlist</span>
            <span style="font-size:11px; color:#9CA3AF;">TESTNET-FEED</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for symbol in SYMBOLS:
        t         = tickers[symbol]
        is_active = st.session_state.selected_symbol == symbol
        chg_cls   = "text-success" if t["change"] >= 0 else "text-danger"
        ind_lbl   = "Bullish"      if t["change"] >= 0 else "Bearish"
        sign      = "+"            if t["change"] >= 0 else ""
        border    = "border-left: 4px solid #3B82F6;" if is_active else ""
        bg        = "background: rgba(59,130,246,0.08);"  if is_active else ""

        st.markdown(f"""
        <div class="crypto-card" style="{border}{bg}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-family:'Space Grotesk',sans-serif; font-weight:700; color:#FFFFFF;">{symbol}</span>
                <span class="{chg_cls}" style="font-size:12px; font-family:'JetBrains Mono',monospace;">{sign}{_fmt(t['change'])}%</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top:8px;">
                <span style="font-family:'JetBrains Mono',monospace; font-size:18px; font-weight:600; color:#F3F4F6;">${_fmt(t['price'])}</span>
                <span style="font-size:10px; color:#9CA3AF; text-transform:uppercase;">Trend: <b class="{chg_cls}">{ind_lbl}</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"Switch to {symbol}", key=f"sel_{symbol}", use_container_width=True):
            st.session_state.selected_symbol = symbol
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════
# CENTER — Trading Ticket
# ═══════════════════════════════════════════════════════════════════════════
with col_center:
    sel_sym      = st.session_state.selected_symbol
    sym_ticker   = tickers[sel_sym]
    crypto_price = sym_ticker["price"]

    st.markdown(f"""
    <div class="trade-card">
        <div class="card-header-term">
            <span>⚡ Direct Trade Ticket</span>
            <span style="color:#22C55E; font-weight:700;">{sel_sym} PERP</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Active asset banner
    st.markdown(f"""
    <div style="background:rgba(59,130,246,0.05); padding:10px 14px; border-radius:8px;
                border:1px dashed rgba(59,130,246,0.2); margin-bottom:14px;
                display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:13px; color:#9CA3AF;">Active Asset</span>
        <span style="font-family:'Space Grotesk',sans-serif; font-weight:700; color:#FFFFFF; font-size:14px;">
            {sel_sym} @ ${_fmt(crypto_price)}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # BUY / SELL segmented radio
    side_selection = st.radio(
        "Order side",
        ["BUY / LONG", "SELL / SHORT"],
        label_visibility="collapsed",
        key="trade_side",
    )
    side_action = "BUY" if "BUY" in side_selection else "SELL"

    # MARKET / LIMIT segmented radio
    exec_type = st.radio(
        "Order type",
        ["MARKET EXECUTION", "LIMIT SPECIFICATION"],
        label_visibility="collapsed",
        key="trade_type",
    )
    order_type = "MARKET" if "MARKET" in exec_type else "LIMIT"

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

    # Quantity input  — precision scaled to the asset
    step_qty    = 0.001 if "BTC" in sel_sym else (0.01  if "ETH" in sel_sym else 0.1)
    default_qty = 0.01  if "BTC" in sel_sym else (0.1   if "ETH" in sel_sym else 1.0)

    quantity = st.number_input(
        f"Order Quantity ({sel_sym.replace('USDT', '')})",
        min_value=step_qty,
        value=default_qty,
        step=step_qty,
        format="%f",
    )

    # Price input — only shown for LIMIT orders
    order_price: float | None = None
    if order_type == "LIMIT":
        order_price = st.number_input(
            "Limit Trigger Price (USDT)",
            min_value=0.01,
            value=round(crypto_price, 2) if crypto_price else 50_000.0,
            step=0.5,
            format="%.2f",
        )

    # Order value estimate
    effective_price = order_price if order_price else crypto_price
    est_value       = quantity * effective_price
    est_margin      = est_value / 10   # illustrative 10× display only

    st.markdown(f"""
    <div class="summary-box">
        <table style="width:100%; font-size:12px; color:#9CA3AF;">
            <tr>
                <td style="padding-bottom:4px;">Order Value</td>
                <td style="text-align:right; padding-bottom:4px;" class="mono-font">${_fmt(est_value)} USDT</td>
            </tr>
            <tr>
                <td>Est. Margin (10×)</td>
                <td style="text-align:right;" class="text-warning mono-font">${_fmt(est_margin)}</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # Inline feedback from the last order attempt
    if st.session_state.order_error:
        st.markdown(
            f'<div class="status-bill status-bill-rejected" style="margin-bottom:10px;">'
            f'⛔ {st.session_state.order_error}</div>',
            unsafe_allow_html=True,
        )
    if st.session_state.order_result and not st.session_state.order_error:
        oid = st.session_state.order_result.get("orderId", "—")
        st.markdown(
            f'<div class="status-bill status-bill-success" style="margin-bottom:10px;">'
            f'✅ Order #{oid} placed successfully!</div>',
            unsafe_allow_html=True,
        )

    # Gradient colour for the action button
    if side_action == "BUY":
        st.markdown("""
        <style>
        div.place-order-wrapper button {
            background: linear-gradient(135deg, #22C55E 0%, #15803D 100%) !important;
            box-shadow: 0 4px 15px rgba(34,197,94,0.3) !important;
        }
        div.place-order-wrapper button:hover {
            box-shadow: 0 6px 20px rgba(34,197,94,0.45) !important;
            transform: translateY(-1px) !important;
        }
        </style>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        div.place-order-wrapper button {
            background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%) !important;
            box-shadow: 0 4px 15px rgba(239,68,68,0.3) !important;
        }
        div.place-order-wrapper button:hover {
            box-shadow: 0 6px 20px rgba(239,68,68,0.45) !important;
            transform: translateY(-1px) !important;
        }
        </style>""", unsafe_allow_html=True)

    st.markdown('<div class="place-order-wrapper">', unsafe_allow_html=True)

    if st.button(f"PLACE {side_action} {order_type} ORDER", use_container_width=True):
        if not creds_ok:
            st.session_state.order_error  = "API credentials missing — check your .env file."
            st.session_state.order_result = None
        else:
            with st.spinner("Sending to Binance Testnet…"):
                try:
                    resp = place_order(
                        client, logger,
                        sel_sym, side_action, order_type,
                        quantity, order_price,
                    )
                    # Stamp a local timestamp and persist in session state
                    resp["_ts"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.order_result = resp
                    st.session_state.order_error  = None
                    st.session_state.orders_history.insert(0, resp)
                except BinanceAPIError as exc:
                    st.session_state.order_error  = f"Binance API Error: {exc}"
                    st.session_state.order_result = None
                except ValueError as exc:
                    st.session_state.order_error  = f"Validation: {exc}"
                    st.session_state.order_result = None
                except Exception as exc:
                    st.session_state.order_error  = f"Unexpected error: {exc}"
                    st.session_state.order_result = None
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)   # /place-order-wrapper
    st.markdown(
        '<div style="margin-top:8px; font-size:11px; color:#334155; text-align:center;">'
        'Orders execute on Binance Futures Testnet · No real funds involved</div>',
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════════════════
# RIGHT — Session Overview + Latest Order Confirmation
# ═══════════════════════════════════════════════════════════════════════════
with col_right:

    # ── Session overview card ──────────────────────────────────────────────
    api_color = "#22C55E" if creds_ok else "#EF4444"
    api_label = "Connected" if creds_ok else "No Key"

    st.markdown(f"""
    <div class="trade-card">
        <div class="card-header-term">
            <span>📊 Session Overview</span>
            <span style="color:#22C55E; font-size:11px;">● TESTNET</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Network</span>
            <span class="mono-font" style="color:#22C55E;">Testnet</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">API Status</span>
            <span class="mono-font" style="color:{api_color};">{api_label}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Active Symbol</span>
            <span class="mono-font" style="color:#3B82F6;">{st.session_state.selected_symbol}</span>
        </div>
        <div class="stat-row" style="border-bottom:none;">
            <span class="stat-label">Orders This Session</span>
            <span class="mono-font" style="color:#F1F5F9;">{len(st.session_state.orders_history)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Latest order confirmation feed ────────────────────────────────────
    st.markdown(
        "<div style='margin-top:16px; font-size:13px; font-weight:600; color:#CCCCCC;'>"
        "Latest Order Confirmation</div>",
        unsafe_allow_html=True,
    )

    lat = st.session_state.order_result

    if not lat:
        st.markdown("""
        <div class="status-bill" style="border-left:4px solid #F59E0B; text-align:center; padding:20px 10px; margin-top:10px;">
            <span style="font-size:24px;">📥</span>
            <div style="font-size:13px; font-weight:600; color:#FFFFFF; margin-top:6px;">No orders executed this session</div>
            <div style="font-size:11px; color:#9CA3AF; margin-top:2px;">Use the Trade Ticket to place an order</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        side_val = lat.get("side",   "—")
        status   = lat.get("status", "—")

        is_ok       = status in ("NEW", "FILLED", "PARTIALLY_FILLED")
        bill_cls    = "status-bill-success"  if is_ok else "status-bill-rejected"
        hdr_color   = "#22C55E"              if is_ok else "#EF4444"
        hdr_label   = "✅ ORDER PLACED"       if is_ok else "❌ ORDER FAILED"
        status_cls  = "badge-filled"         if is_ok else "badge-rejected"
        side_cls    = "badge-buy"            if side_val == "BUY" else "badge-sell"
        side_html   = f'<span class="{side_cls}">{"BUY LONG" if side_val=="BUY" else "SELL SHORT"}</span>'

        price_display = get_display_price(lat)

        st.markdown(f"""
        <div class="status-bill {bill_cls}" style="margin-top:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; font-size:14px; color:{hdr_color};">{hdr_label}</span>
                <span class="{status_cls}">{status}</span>
            </div>
            <div style="margin-top:10px; font-size:12px; color:#D1D5DB;">
                <table style="width:100%;">
                    <tr><td style="color:#9CA3AF; padding:2px 0;">Order ID</td>
                        <td class="mono-font" style="text-align:right;">{str(lat.get('orderId','—'))[:16]}</td></tr>
                    <tr><td style="color:#9CA3AF; padding:2px 0;">Asset</td>
                        <td style="text-align:right; font-weight:600; color:#FFFFFF;">{lat.get('symbol','—')}</td></tr>
                    <tr><td style="color:#9CA3AF; padding:2px 0;">Direction</td>
                        <td style="text-align:right;">{side_html}</td></tr>
                    <tr><td style="color:#9CA3AF; padding:2px 0;">Type</td>
                        <td class="mono-font" style="text-align:right;">{lat.get('type','—')}</td></tr>
                    <tr><td style="color:#9CA3AF; padding:2px 0;">Orig Qty</td>
                        <td class="mono-font" style="text-align:right;">{lat.get('origQty','—')}</td></tr>
                    <tr><td style="color:#9CA3AF; padding:2px 0;">Avg Price</td>
                        <td class="mono-font" style="text-align:right;">{price_display}</td></tr>
                    <tr><td style="color:#9CA3AF; padding:2px 0;">Time</td>
                        <td class="mono-font" style="text-align:right;">{lat.get('_ts','—')}</td></tr>
                </table>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Clear", key="clear_order_btn", use_container_width=True):
            st.session_state.order_result = None
            st.session_state.order_error  = None
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# BOTTOM — Order history table (session state only, no Binance fetch)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

hdr_col, btn_col = st.columns([8, 1])
with hdr_col:
    st.markdown("### 📋 Order History", unsafe_allow_html=True)
with btn_col:
    if st.button("CLEAR LOGS", use_container_width=True, key="clear_log_btn"):
        st.session_state.orders_history = []
        st.session_state.order_result   = None
        st.session_state.order_error    = None
        st.rerun()

if not st.session_state.orders_history:
    st.markdown("""
    <div style="background:rgba(17,24,39,0.4); border:1px solid rgba(255,255,255,0.04);
                border-radius:12px; padding:40px; text-align:center;">
        <span style="font-size:36px; opacity:0.6;">📭</span>
        <h4 style="margin-top:10px;">No orders placed this session</h4>
        <p style="color:#9CA3AF; font-size:12px; max-width:400px; margin:0 auto;">
            Place a MARKET or LIMIT order using the trading ticket above.
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    rows_html = ""
    for order in st.session_state.orders_history:
        side_val   = order.get("side",   "—")
        status_val = order.get("status", "—")

        is_ok_row   = status_val in ("NEW", "FILLED", "PARTIALLY_FILLED")
        stat_badge  = (f'<span class="badge-filled">{status_val}</span>'
                       if is_ok_row else
                       f'<span class="badge-rejected">{status_val}</span>')
        side_badge  = (f'<span class="badge-buy">BUY LONG</span>'
                       if side_val == "BUY" else
                       f'<span class="badge-sell">SELL SHORT</span>')

        price_str = get_display_price(order)

        rows_html += f"""
        <tr>
            <td class="mono-font" style="font-size:12px; color:#9CA3AF;">{order.get('_ts', '—')}</td>
            <td class="mono-font" style="font-weight:600;">{order.get('symbol', '—')}</td>
            <td>{side_badge}</td>
            <td class="mono-font" style="font-size:12px; color:#F59E0B;">{order.get('type', '—')}</td>
            <td class="mono-font">{order.get('origQty', '—')}</td>
            <td class="mono-font" style="color:#E5E7EB;">{price_str}</td>
            <td>{stat_badge}</td>
            <td class="mono-font" style="font-size:11px; color:#9CA3AF;">{str(order.get('orderId','—'))[:16]}</td>
        </tr>"""

    st.markdown(f"""
    <div class="trading-table-container">
        <table class="fintech-table">
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Asset Pair</th>
                    <th>Direction</th>
                    <th>Order Type</th>
                    <th>Orig Qty</th>
                    <th>Price (USDT)</th>
                    <th>Status</th>
                    <th>Order ID</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)
