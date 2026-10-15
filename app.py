import streamlit as st
import requests
import json
import os
import io
import zipfile
import re
import subprocess
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

import core.utils
import core.content
import core.tests
import core.announcer
import core.auth
import core.pdf_exporter
import importlib

# Ensure fresh modules
importlib.reload(core.utils)
importlib.reload(core.content)
importlib.reload(core.tests)
importlib.reload(core.announcer)
importlib.reload(core.auth)
importlib.reload(core.pdf_exporter)

from core.utils import (
    get_auth_headers,
    verify_token,
    get_token_expiry_info,
    get_user_profile,
    BASE_URL,
)
from core.auth import send_otp, get_token
from core.content import (
    fetch_batches,
    fetch_starred_batch_ids,
    fetch_subjects,
    fetch_topics,
    fetch_notes,
    fetch_dpp,
    fetch_videos,
)
from core.tests import (
    fetch_batch_tests,
    fetch_recent_tests,
    fetch_all_enrolled_tests,
    fetch_test_questions,
    generate_test_html,
    generate_test_markdown,
    generate_test_json,
    zip_test_papers,
    generate_two_column_exam_booklet,
    generate_question_answer_solution_booklet,
    generate_printable_omr_sheet,
    generate_test_ics_calendar,
    export_to_obsidian_vault,
)
from core.pdf_exporter import (
    html_to_pdf,
    zip_pdf_papers,
    compile_test_curated_pdfs,
    get_browser_executable,
)
from core.announcer import fetch_announcements

load_dotenv()
TOKEN_FILE = os.path.join("data", "token.txt")
os.makedirs("data", exist_ok=True)
DEFAULT_VAULT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Nexus_Docs", "PW_Archive")
os.makedirs(DEFAULT_VAULT_DIR, exist_ok=True)
DOWNLOADS_DIR = os.path.join("Nexus_Downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Nexus Streamlit | Sovereign Study & Exam Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Awesome Cyber-Sovereign UI CSS ---
AWESOME_CYBER_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Cyber Scrollbars */
    ::-webkit-scrollbar {
        width: 7px;
        height: 7px;
    }
    ::-webkit-scrollbar-track {
        background: #07090e;
    }
    ::-webkit-scrollbar-thumb {
        background: #1f273d;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #3b476b;
    }

    /* App Background */
    .stApp {
        background-color: #07090e;
        color: #f1f5f9;
    }

    /* Futuristic HUD Navbar */
    .pw-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, rgba(15, 20, 32, 0.85) 0%, rgba(20, 27, 45, 0.85) 100%);
        backdrop-filter: blur(16px);
        padding: 14px 26px;
        border: 1px solid rgba(99, 102, 241, 0.22);
        border-radius: 16px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.08);
    }
    .pw-brand {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .pw-brand-logo {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: #ffffff;
        font-weight: 900;
        font-size: 18px;
        width: 42px;
        height: 42px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
        letter-spacing: -0.5px;
    }
    .pw-brand-title {
        font-size: 19px;
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: -0.3px;
    }
    .pw-brand-badge {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        font-size: 11px;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 20px;
        border: 1px solid rgba(52, 211, 153, 0.4);
        margin-left: 8px;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.2);
    }
    .pw-user-chips {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .pw-chip {
        display: flex;
        align-items: center;
        gap: 6px;
        background: #111624;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        color: #cbd5e1;
        border: 1px solid #1e263d;
    }
    .pw-chip.streak {
        background: rgba(249, 115, 22, 0.12);
        color: #fb923c;
        border-color: rgba(249, 115, 22, 0.35);
        box-shadow: 0 0 10px rgba(249, 115, 22, 0.15);
    }
    .pw-chip.xp {
        background: rgba(34, 197, 94, 0.12);
        color: #4ade80;
        border-color: rgba(34, 197, 94, 0.35);
        box-shadow: 0 0 10px rgba(34, 197, 94, 0.15);
    }
    .pw-avatar {
        background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
        color: white;
        font-weight: 800;
        font-size: 13px;
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.5);
    }

    /* Hero Banner */
    .pw-hero-banner {
        background: linear-gradient(135deg, #0e121d 0%, #151a2a 50%, #181d33 100%);
        border-radius: 18px;
        padding: 26px 32px;
        border: 1.5px solid rgba(99, 102, 241, 0.25);
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.45);
        margin-bottom: 26px;
        position: relative;
    }
    .pw-hero-subtitle {
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #818cf8;
        margin-bottom: 6px;
    }
    .pw-hero-title {
        font-size: 28px;
        font-weight: 900;
        color: #ffffff;
        margin-bottom: 14px;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .pw-hero-tags {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }
    .pw-hero-tag {
        background: rgba(255, 255, 255, 0.06);
        padding: 5px 14px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #e2e8f0;
    }
    .pw-hero-tag.starred {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border-color: rgba(245, 158, 11, 0.4);
    }

    /* Batch Offering Cyber Cards */
    .offering-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 16px;
        margin-bottom: 26px;
    }
    .offering-card {
        background: #0f1422;
        border: 1px solid #1f273d;
        border-radius: 16px;
        padding: 22px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
    }
    .offering-card:hover {
        border-color: #6366f1;
        background: #141a2c;
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(99, 102, 241, 0.25);
    }
    .offering-content {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .offering-icon {
        width: 48px;
        height: 48px;
        border-radius: 14px;
        background: #171d30;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        border: 1px solid #28334f;
    }
    .offering-title {
        font-size: 17px;
        font-weight: 800;
        color: #f8fafc;
    }
    .offering-desc {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 2px;
    }
    .offering-arrow {
        font-size: 20px;
        color: #475569;
        font-weight: bold;
    }

    /* Cyber Test Card */
    .pw-test-card {
        background: #0e121d;
        border: 1px solid #1d2438;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 18px;
        transition: all 0.2s ease;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .pw-test-card:hover {
        border-color: #3b476b;
        box-shadow: 0 8px 30px rgba(0,0,0,0.45);
    }
    .test-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        flex-wrap: wrap;
        gap: 10px;
    }
    .test-title {
        font-size: 18px;
        font-weight: 800;
        color: #f8fafc;
    }
    .test-meta-row {
        display: flex;
        align-items: center;
        gap: 14px;
        font-size: 12px;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 10px;
        flex-wrap: wrap;
    }
    .test-date-row {
        font-size: 12px;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
    }

    /* Animated Pulsing Emerald Live Indicator */
    @keyframes pulse-emerald {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6); }
        70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }
    .dot-live {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        display: inline-block;
        animation: pulse-emerald 2s infinite;
        margin-right: 6px;
    }
    .pill-timeline-live {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 4px 12px;
        border-radius: 18px;
        font-size: 11px;
        font-weight: 800;
        display: inline-flex;
        align-items: center;
    }
    .pill-timeline-past {
        background: rgba(100, 116, 139, 0.12);
        color: #94a3b8;
        border: 1px solid rgba(100, 116, 139, 0.3);
        padding: 4px 12px;
        border-radius: 18px;
        font-size: 11px;
        font-weight: 800;
        display: inline-flex;
        align-items: center;
    }
    .pill-timeline-future {
        background: rgba(168, 85, 247, 0.12);
        color: #c084fc;
        border: 1px solid rgba(168, 85, 247, 0.4);
        padding: 4px 12px;
        border-radius: 18px;
        font-size: 11px;
        font-weight: 800;
        display: inline-flex;
        align-items: center;
    }
    .pill-badge-free {
        background: rgba(244, 63, 94, 0.15);
        color: #fb7185;
        font-size: 10px;
        font-weight: 800;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid rgba(244, 63, 94, 0.35);
        text-transform: uppercase;
        margin-left: 6px;
    }

    /* Stat Box */
    .stat-ribbon {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 14px;
        margin-bottom: 24px;
    }
    .stat-box {
        background: #0e121d;
        border: 1px solid #1e263d;
        border-radius: 14px;
        padding: 16px 20px;
    }
    .stat-box .title {
        font-size: 11px;
        color: #818cf8;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .stat-box .value {
        font-size: 24px;
        font-weight: 900;
        color: #ffffff;
    }
    .stat-box .desc {
        font-size: 12px;
        color: #64748b;
        margin-top: 2px;
    }

    /* Video Card */
    .video-card {
        background: #0f1422;
        border: 1px solid #1f273d;
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        flex-wrap: wrap;
    }
</style>
"""
st.markdown(AWESOME_CYBER_CSS, unsafe_allow_html=True)

# --- Token Management ---
def save_token(token):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token.strip())

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding="utf-8") as f:
            return f.read().strip()
    return None

def delete_token():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)

def check_token(token):
    if token:
        res = verify_token(token)
        return res.get("success", False)
    return False

# --- High-Performance SQLite + Cached Fetchers ---
import core.db as db

@st.cache_data(show_spinner=False, ttl=600)
def get_cached_batches(token, amount="all", force_refresh=False):
    if not force_refresh:
        cached = db.get_cached_batches(
            starred_only=(amount == "starred"),
            paid_only=(amount == "paid"),
            free_only=(amount == "free")
        )
        if cached and len(cached) > 0:
            return cached
    return fetch_batches(token, amount=amount, fetch_all=True)

@st.cache_data(show_spinner=False, ttl=300)
def get_cached_batch_tests(token, batch_id, batch_name="", force_refresh=False):
    if not force_refresh:
        cached = db.get_tests_by_batch(batch_id)
        if cached and len(cached) > 0:
            return cached
    return fetch_batch_tests(token, batch_id, batch_name=batch_name)

@st.cache_data(show_spinner=False, ttl=180)
def get_cached_recent_tests(token):
    return fetch_recent_tests(token)

@st.cache_data(show_spinner=False, ttl=600)
def get_cached_all_tests(token, force_refresh=False):
    if not force_refresh:
        total = db.get_total_tests_count()
        if total > 0:
            return db.search_tests_db(limit=1000)
    batches = get_cached_batches(token, amount="all")
    return fetch_all_enrolled_tests(token, batches, max_workers=25)

@st.cache_data(show_spinner=False, ttl=600)
def get_cached_subjects(token, batch_slug):
    return fetch_subjects(token, batch_slug)

@st.cache_data(show_spinner=False, ttl=600)
def get_cached_topics(token, batch_slug, subject_slug):
    return fetch_topics(token, batch_slug, subject_slug)

@st.cache_data(show_spinner=False, ttl=300)
def get_cached_videos(token, batch_slug, subject_slug, topic_slug):
    return fetch_videos(token, batch_slug, subject_slug, topic_slug)

# --- Top Navigation Bar ---
def render_pw_navbar(user_profile, active_batch_name):
    st.markdown(f"""
    <div class="pw-navbar">
        <div class="pw-brand">
            <div class="pw-brand-logo">NX</div>
            <div>
                <span class="pw-brand-title">Nexus Streamlit</span>
                <span class="pw-brand-badge">⚡ Sovereign Engine Active</span>
            </div>
        </div>
        <div class="pw-user-chips">
            <div class="pw-chip">📚 {active_batch_name[:24]}{'...' if len(active_batch_name)>24 else ''}</div>
            <div class="pw-chip streak">🔥 {user_profile.get('streak', 1)} Streak</div>
            <div class="pw-chip xp">💎 {user_profile.get('xp', 368)} XP</div>
            <div class="pw-avatar" title="{user_profile.get('name', 'Student')}">{user_profile.get('initials', 'NB')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- "Select your batch" Modal Dialog (matching PW Right Drawer) ---
@st.dialog("Select your batch")
def select_batch_dialog(all_batches):
    st.caption("Choose your enrolled batch to view classes, tests, and study materials.")
    
    b_search = st.text_input("🔍 Search for your batches", placeholder="Type batch name...", key="dlg_batch_search")
    filtered = all_batches
    if b_search.strip():
        q = b_search.strip().lower()
        filtered = [b for b in all_batches if q in b["name"].lower() or q in b.get("slug", "").lower()]

    starred_list = [b for b in filtered if b.get("is_starred")]
    paid_list = [b for b in filtered if not b.get("is_starred") and not b.get("is_free")]
    free_list = [b for b in filtered if not b.get("is_starred") and b.get("is_free")]

    selected_b_id = st.session_state.get("current_batch_id", all_batches[0]["_id"] if all_batches else "")

    tab_labels = [
        f"⭐ Starred ({len(starred_list)})",
        f"💳 Paid ({len(paid_list)})",
        f"🆓 Free ({len(free_list)})",
        f"⚡ All ({len(filtered)})"
    ]
    st_tab, pd_tab, fr_tab, al_tab = st.tabs(tab_labels)

    def _render_batch_options(batch_sublist, key_prefix):
        if not batch_sublist:
            st.info("No batches found in this category.")
            return None
        options = {b["_id"]: f"{'⭐ ' if b.get('is_starred') else ''}{b['name']} ({'FREE' if b.get('is_free') else 'PAID'})" for b in batch_sublist}
        current_val = selected_b_id if selected_b_id in options else list(options.keys())[0]
        chosen = st.radio(
            "Batches",
            options=list(options.keys()),
            format_func=lambda bid: options[bid],
            index=list(options.keys()).index(current_val),
            key=f"{key_prefix}_radio",
            label_visibility="collapsed"
        )
        return chosen

    chosen_in_tab = None
    with st_tab:
        chosen_in_tab = _render_batch_options(starred_list, "starred") or chosen_in_tab
    with pd_tab:
        chosen_in_tab = _render_batch_options(paid_list, "paid") or chosen_in_tab
    with fr_tab:
        chosen_in_tab = _render_batch_options(free_list, "free") or chosen_in_tab
    with al_tab:
        chosen_in_tab = _render_batch_options(filtered, "all") or chosen_in_tab

    st.markdown("---")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Continue", type="primary", use_container_width=True):
            if chosen_in_tab:
                st.session_state["current_batch_id"] = chosen_in_tab
                st.rerun()
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

# --- MAIN APPLICATION ENTRYPOINT ---
def main():
    token = load_token()
    if 'otp_sent' not in st.session_state:
        st.session_state["otp_sent"] = False

    # ---- 1. LOGIN SCREEN ----
    if not token or not check_token(token):
        st.markdown("""
        <div style="text-align:center; padding: 40px 0 20px 0;">
            <div style="display:inline-block; background:linear-gradient(135deg, #6366f1 0%, #a855f7 100%); color:white; font-size:32px; font-weight:800; width:64px; height:64px; line-height:64px; border-radius:18px; margin-bottom:12px; box-shadow:0 0 25px rgba(99,102,241,0.5);">NX</div>
            <h1 style="font-weight:900; color:#f8fafc; margin-bottom:6px;">Nexus Streamlit</h1>
            <p style="color:#94a3b8; font-size:15px;">Sovereign Objective Test Extractor, Curated PDF Builder & Study Vault.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1], gap="large")

        with col1:
            st.markdown("### 📱 Login via OTP")
            cc = st.text_input("Country Code", value="+91", max_chars=5)
            phone = st.text_input("Mobile Number")
            if st.button("Get OTP", type="primary", use_container_width=True):
                if phone and cc:
                    resp = send_otp(phone, cc)
                    if resp.get("success"):
                        st.session_state["otp_sent"] = True
                        st.success("OTP sent successfully to your phone.")
                    else:
                        st.error(resp.get("error_message", "Failed to send OTP."))
                        st.session_state["otp_sent"] = False
                else:
                    st.warning("Please enter your mobile number.")

            if st.session_state["otp_sent"]:
                otp = st.text_input("Enter 6-Digit OTP", max_chars=6)
                if st.button("Verify & Sign In", type="primary", use_container_width=True):
                    if otp:
                        tkres = get_token(phone, otp)
                        if tkres.get("success"):
                            save_token(tkres["access_token"])
                            st.success("Login successful! Loading your dashboard...")
                            st.session_state.clear()
                            st.rerun()
                        else:
                            st.error(tkres.get("error_message", "Invalid OTP"))

        with col2:
            st.markdown("### 🔑 Sign In with Access Token")
            input_token = st.text_area("Bearer Access Token", height=140, placeholder="Paste your PW Bearer JWT token here...")
            if st.button("Verify & Open Dashboard", use_container_width=True):
                if input_token.strip():
                    if check_token(input_token.strip()):
                        save_token(input_token.strip())
                        st.success("Token verified successfully!")
                        st.session_state.clear()
                        st.rerun()
                    else:
                        st.error("Invalid or expired token. Please verify and try again.")
                else:
                    st.warning("Please paste your token first.")
        return

    # ---- 2. AUTHENTICATED DASHBOARD ----
    user_profile = get_user_profile(token)

    # --- FETCH ALL ENROLLED BATCHES ---
    with st.spinner("Synchronizing batches..."):
        all_batches = get_cached_batches(token, amount="all")

    if not all_batches:
        st.warning("No batches found for your PW account.")
        return

    # Set initial default batch: Excellence Revision or 12-UF292CA
    if "current_batch_id" not in st.session_state:
        chosen_default = all_batches[0]["_id"]
        for b in all_batches:
            if "Excellence Revision" in b["name"] or "12-UF292CA" in b["name"]:
                chosen_default = b["_id"]
                break
        st.session_state["current_batch_id"] = chosen_default

    sel_batch = next((b for b in all_batches if b["_id"] == st.session_state["current_batch_id"]), all_batches[0])
    sel_batch_id = sel_batch["_id"]
    sel_batch_slug = sel_batch["slug"]

    # Render Navbar
    render_pw_navbar(user_profile, sel_batch["name"])

    # --- LEFT SIDEBAR (FAITHFULLY REPLICATING PW DASHBOARD + SOVEREIGN TOOLS) ---
    with st.sidebar:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
            <div style="background:linear-gradient(135deg, #6366f1 0%, #a855f7 100%); color:white; font-weight:800; font-size:16px; width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center; box-shadow:0 0 12px rgba(99,102,241,0.5);">NX</div>
            <div>
                <div style="font-weight:900; font-size:16px; color:#f8fafc;">Nexus Streamlit</div>
                <div style="font-size:11px; color:#818cf8; font-weight:700;">Sovereign Study Platform</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.caption(f"👤 {user_profile.get('name')} | {user_profile.get('username')}")
        
        # Batch Switcher Button directly in sidebar
        if st.button(f"🔄 Switch Batch ({sel_batch['name'][:18]}...)", use_container_width=True):
            select_batch_dialog(all_batches)

        st.markdown("---")

        # Sections matching PW: LEARN ONLINE, STUDY PACKS, OFFLINE, EXPLORE PW
        st.markdown("<p style='font-size:11px; font-weight:800; color:#818cf8; letter-spacing:1.5px; margin-bottom:4px;'>LEARN ONLINE</p>", unsafe_allow_html=True)
        nav_learn = [
            "📖 Study Hub",
            "📺 Lectures & Notes Vault",
            "🥧 Pi (AI Study Copilot)",
            "📚 Library"
        ]

        st.markdown("<p style='font-size:11px; font-weight:800; color:#818cf8; letter-spacing:1.5px; margin-top:14px; margin-bottom:4px;'>TESTS & EXAMS</p>", unsafe_allow_html=True)
        nav_tests = [
            "📝 Test Series (Extractor)",
            "📅 Test Calendar & .ics Sync",
            "🎯 My Test History"
        ]

        st.markdown("<p style='font-size:11px; font-weight:800; color:#818cf8; letter-spacing:1.5px; margin-top:14px; margin-bottom:4px;'>SOVEREIGN TOOLS</p>", unsafe_allow_html=True)
        nav_tools = [
            "⚡ Nexus Obsidian Vault",
            "📦 Batch Bulk Downloader",
            "🌐 Global Explorer (374+ Tests)",
            "📢 Announcements"
        ]

        all_nav_items = nav_learn + nav_tests + nav_tools

        if "active_nav" not in st.session_state:
            st.session_state["active_nav"] = "📖 Study Hub"

        if "nav_direct" in st.session_state and st.session_state["nav_direct"] in all_nav_items:
            st.session_state["active_nav"] = st.session_state["nav_direct"]
            del st.session_state["nav_direct"]

        active_nav = st.radio(
            "Navigation",
            all_nav_items,
            index=all_nav_items.index(st.session_state["active_nav"]) if st.session_state["active_nav"] in all_nav_items else 0,
            label_visibility="collapsed"
        )
        st.session_state["active_nav"] = active_nav

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            delete_token()
            st.session_state.clear()
            st.rerun()

    # =========================================================================
    # VIEW 1: STUDY HUB (DASHBOARD MATCHING PW STUDY-V2)
    # =========================================================================
    if active_nav == "📖 Study Hub":
        st.markdown("# Study Hub")

        bcol_info, bcol_btn = st.columns([8, 2])
        with bcol_info:
            st.markdown(f"""
            <div class="pw-hero-banner">
                <div class="pw-hero-subtitle">YOUR ACTIVE BATCH</div>
                <div class="pw-hero-title">
                    {sel_batch['name']}
                    {'<span style="color:#fbbf24; font-size:20px;">⭐</span>' if sel_batch.get('is_starred') else ''}
                </div>
                <div class="pw-hero-tags">
                    <span class="pw-hero-tag {'starred' if sel_batch.get('is_starred') else ''}">{'⭐ Starred Batch' if sel_batch.get('is_starred') else ('🆓 Free Batch' if sel_batch.get('is_free') else '💳 Paid Batch')}</span>
                    <span class="pw-hero-tag">🆔 {sel_batch_id}</span>
                    {f"<span class='pw-hero-tag'>🎯 Exam: {sel_batch['exam']}</span>" if sel_batch.get('exam') else ""}
                    {f"<span class='pw-hero-tag'>🏫 Class: {sel_batch['class']}</span>" if sel_batch.get('class') else ""}
                    {f"<span class='pw-hero-tag'>📅 Validity: {sel_batch.get('expiryDate', '')[:10]}</span>" if sel_batch.get('expiryDate') else ""}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with bcol_btn:
            st.write("")
            st.write("")
            if st.button("Change Batch ▾", type="primary", use_container_width=True):
                select_batch_dialog(all_batches)

        # Batch Offerings (Matching Screenshot)
        st.markdown("### Batch Offerings")
        off_col1, off_col2, off_col3 = st.columns(3)

        with off_col1:
            st.markdown("""
            <div class="offering-card">
                <div class="offering-content">
                    <div class="offering-icon" style="color:#6366f1;">📘</div>
                    <div>
                        <div class="offering-title">All Classes & Lectures</div>
                        <div class="offering-desc">Videos, Notes, DPPs & Exercises</div>
                    </div>
                </div>
                <div class="offering-arrow">›</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Classes & Lectures", key="btn_off_classes", use_container_width=True):
                st.session_state["active_nav"] = "📺 Lectures & Notes Vault"
                st.rerun()

        with off_col2:
            st.markdown("""
            <div class="offering-card">
                <div class="offering-content">
                    <div class="offering-icon" style="color:#10b981;">📝</div>
                    <div>
                        <div class="offering-title">All Tests (Extractor)</div>
                        <div class="offering-desc">Objective Papers, OMR & Solutions</div>
                    </div>
                </div>
                <div class="offering-arrow">›</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open All Tests (Extractor)", key="btn_off_tests", type="primary", use_container_width=True):
                st.session_state["active_nav"] = "📝 Test Series (Extractor)"
                st.rerun()

        with off_col3:
            st.markdown("""
            <div class="offering-card">
                <div class="offering-content">
                    <div class="offering-icon" style="color:#a855f7;">❓</div>
                    <div>
                        <div class="offering-title">My Doubts & Pi</div>
                        <div class="offering-desc">AI Doubt Engine & Concept Solver</div>
                    </div>
                </div>
                <div class="offering-arrow">›</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Ask Pi AI Solver", key="btn_off_doubts", use_container_width=True):
                st.session_state["active_nav"] = "🥧 Pi (AI Study Copilot)"
                st.rerun()

        st.markdown("---")

        # Upcoming Events
        st.markdown("### Upcoming Events & Live Schedule")
        u_col1, u_col2 = st.columns([8, 2])
        with u_col1:
            st.markdown("""
            <div style="background:#0e121d; border:1px dashed #26314d; border-radius:14px; padding:22px; text-align:center; color:#94a3b8;">
                <div style="font-size:24px; margin-bottom:8px;">📅</div>
                <div style="font-size:16px; font-weight:800; color:#f8fafc;">Today's live events have ended</div>
                <div style="font-size:12px; color:#64748b;">All scheduled lectures and test sessions have concluded for today. Check upcoming test dates in the Calendar tab.</div>
            </div>
            """, unsafe_allow_html=True)
        with u_col2:
            st.write("")
            if st.button("📅 Open Test Calendar", use_container_width=True):
                st.session_state["active_nav"] = "📅 Test Calendar & .ics Sync"
                st.rerun()

        # Recently Active Tests & DPPs Strip
        recent_tests = get_cached_recent_tests(token)
        if recent_tests:
            st.markdown("---")
            st.markdown("### ⚡ Recently Active Tests & DPP Quizzes")
            r_cols = st.columns(min(4, len(recent_tests)))
            for idx, r_item in enumerate(recent_tests[:4]):
                with r_cols[idx]:
                    r_name = r_item.get("name", "Test")
                    r_type = r_item.get("type", "Test")
                    r_id = r_item.get("_id")
                    st.markdown(f"""
                    <div class="pw-test-card" style="padding:14px;">
                        <div style="font-size:11px; font-weight:800; color:#818cf8; text-transform:uppercase;">{r_type}</div>
                        <div style="font-size:13px; font-weight:800; color:#f8fafc; margin-top:2px;">{r_name}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("📥 Extract Paper", key=f"rec_ext_{r_id}", use_container_width=True):
                        st.session_state["active_nav"] = "📝 Test Series (Extractor)"
                        st.session_state[f"extract_target_id"] = r_id
                        st.rerun()

    # =========================================================================
    # VIEW 2: TEST SERIES & UNIVERSAL EXTRACTOR (FEATURES 5 & 8 INTEGRATED)
    # =========================================================================
    elif active_nav == "📝 Test Series (Extractor)":
        st.markdown("# 📝 Test Series & Universal Test Extractor")
        st.caption("Universal objective test paper extraction with 2-Column Booklets, Printable OMR Sheets, Obsidian Markdown, and raw JSON.")

        view_mode = st.radio(
            "Test Display Mode",
            [
                "📂 Batch-wise Segregated View (All Enrolled Batches)",
                f"🎯 Active Batch Tests: {sel_batch['name']}",
                "🌐 Global Search (All 374+ Tests Flat)"
            ],
            horizontal=True
        )

        st.markdown("---")

        # ---------------------------------------------------------------------
        # MODE 1: BATCH-WISE SEGREGATED VIEW
        # ---------------------------------------------------------------------
        if "Batch-wise" in view_mode:
            st.markdown("### 📂 Tests Segregated Batch-by-Batch")
            st.caption("Browsing tests grouped by batch with individual dates, timelines, and 1-click batch bundling:")

            with st.spinner("Scanning tests across all enrolled batches..."):
                all_enrolled_tests = get_cached_all_tests(token)

            batches_map = {}
            for t in all_enrolled_tests:
                b_name = t.get("batch_name", "Unknown Batch")
                b_id = t.get("batch_id")
                if b_id not in batches_map:
                    batches_map[b_id] = {
                        "name": b_name,
                        "is_free": t.get("is_free", False),
                        "tests": []
                    }
                batches_map[b_id]["tests"].append(t)

            col_b_filter, col_b_timeline, col_b_sort = st.columns([4, 3, 3])
            with col_b_filter:
                b_query = st.text_input("🔍 Filter batches or test name", "", key="bw_search")
            with col_b_timeline:
                b_timeline_filter = st.selectbox("Timeline Status", ["All Timelines", "🟢 Live / Present", "🔴 Past / Concluded", "🟣 Upcoming / Future"])
            with col_b_sort:
                b_sort_order = st.selectbox("Sort Tests By Date", ["Start Date (Newest First)", "Start Date (Oldest First)", "Most Questions"])

            total_visible_tests = 0
            for b_id, b_info in batches_map.items():
                b_tests = b_info["tests"]

                if b_query:
                    q = b_query.lower()
                    b_tests = [t for t in b_tests if q in t["name"].lower() or q in b_info["name"].lower()]

                if "Live" in b_timeline_filter:
                    b_tests = [t for t in b_tests if t.get("timeline") == "live"]
                elif "Past" in b_timeline_filter:
                    b_tests = [t for t in b_tests if t.get("timeline") == "past"]
                elif "Upcoming" in b_timeline_filter:
                    b_tests = [t for t in b_tests if t.get("timeline") == "future"]

                if not b_tests:
                    continue

                total_visible_tests += len(b_tests)

                if b_sort_order == "Start Date (Newest First)":
                    b_tests = sorted(b_tests, key=lambda x: x.get("start_time", ""), reverse=True)
                elif b_sort_order == "Start Date (Oldest First)":
                    b_tests = sorted(b_tests, key=lambda x: x.get("start_time", ""))
                elif b_sort_order == "Most Questions":
                    b_tests = sorted(b_tests, key=lambda x: x.get("total_questions", 0), reverse=True)

                live_c = sum(1 for t in b_tests if t.get("timeline") == "live")
                past_c = sum(1 for t in b_tests if t.get("timeline") == "past")
                fut_c = sum(1 for t in b_tests if t.get("timeline") == "future")

                with st.expander(f"📁 {b_info['name']} — {len(b_tests)} Tests ({'FREE' if b_info['is_free'] else 'PAID'}) | 🟢 {live_c} Live, 🔴 {past_c} Past, 🟣 {fut_c} Upcoming", expanded=(b_id == sel_batch_id)):
                    b_act1, b_act2 = st.columns([5, 5])
                    with b_act1:
                        st.write(f"Batch ID: `{b_id}` | Available for direct Curated PDF compilation & Web exports.")
                    with b_act2:
                        b_pdf_col, b_html_col = st.columns(2)
                        with b_pdf_col:
                            if st.button(f"📦 Curated PDFs (ZIP)", key=f"zip_pdf_batch_{b_id}", type="primary", use_container_width=True):
                                curated_pdf_dict = {}
                                prog = st.progress(0, text="Compiling curated PDFs for batch...")
                                for idx, t in enumerate(b_tests):
                                    prog.progress((idx + 1) / len(b_tests), text=f"Compiling {t['name']} PDFs ({idx+1}/{len(b_tests)})...")
                                    qs = fetch_test_questions(token, mapping_id=t.get("mapping_id"), test_id=t["test_id"], batch_id=b_id, test_meta=t)
                                    if qs:
                                        safe_name = "".join([c if c.isalnum() or c in " ._-" else "_" for c in t["name"]])
                                        b_html = generate_two_column_exam_booklet(t, qs, b_info["name"])
                                        b_pdf = html_to_pdf(b_html)
                                        if b_pdf:
                                            curated_pdf_dict[f"01_Question_Papers_2Column/{safe_name}_Question_Booklet.pdf"] = b_pdf
                                        q_html = generate_question_answer_solution_booklet(t, qs, b_info["name"])
                                        q_pdf = html_to_pdf(q_html)
                                        if q_pdf:
                                            curated_pdf_dict[f"02_Questions_with_Solutions_and_Answers/{safe_name}_QnA_with_Solutions.pdf"] = q_pdf
                                        s_html = generate_test_html(t, qs, b_info["name"])
                                        s_pdf = html_to_pdf(s_html)
                                        if s_pdf:
                                            curated_pdf_dict[f"03_Complete_Solutions_Papers/{safe_name}_Solutions.pdf"] = s_pdf
                                        o_html = generate_printable_omr_sheet(t, len(qs))
                                        o_pdf = html_to_pdf(o_html)
                                        if o_pdf:
                                            curated_pdf_dict[f"04_Printable_OMR_Sheets/{safe_name}_OMR_Sheet.pdf"] = o_pdf
                                prog.empty()

                                if curated_pdf_dict:
                                    mem_pdf_zip = zip_pdf_papers(curated_pdf_dict)
                                    st.download_button(
                                        label=f"⬇️ Download Curated PDFs.zip",
                                        data=mem_pdf_zip,
                                        file_name=f"{b_info['name'][:24]}_Curated_Tests_PDFs.zip",
                                        mime="application/zip",
                                        type="primary",
                                        key=f"dl_pdf_zip_{b_id}"
                                    )
                                else:
                                    st.warning("Could not compile PDFs for this batch.")
                        with b_html_col:
                            if st.button(f"📄 HTML/MD (ZIP)", key=f"zip_batch_{b_id}", use_container_width=True):
                                zip_files_dict = {}
                                prog = st.progress(0, text="Extracting batch tests...")
                                for idx, t in enumerate(b_tests):
                                    prog.progress((idx + 1) / len(b_tests), text=f"Extracting {t['name']} ({idx+1}/{len(b_tests)})...")
                                    qs = fetch_test_questions(token, mapping_id=t.get("mapping_id"), test_id=t["test_id"], batch_id=b_id, test_meta=t)
                                    if qs:
                                        safe_name = "".join([c if c.isalnum() or c in " ._-" else "_" for c in t["name"]])
                                        zip_files_dict[f"{safe_name}.html"] = generate_test_html(t, qs, b_info["name"])
                                        zip_files_dict[f"{safe_name}.json"] = generate_test_json(t, qs)
                                        zip_files_dict[f"{safe_name}.md"] = generate_test_markdown(t, qs)
                                        zip_files_dict[f"{safe_name}_Booklet.html"] = generate_two_column_exam_booklet(t, qs, b_info["name"])
                                        zip_files_dict[f"{safe_name}_OMR.html"] = generate_printable_omr_sheet(t, len(qs))
                                prog.empty()

                                if zip_files_dict:
                                    mem_zip = zip_test_papers(zip_files_dict)
                                    st.download_button(
                                        label=f"⬇️ Download Web Bundle.zip",
                                        data=mem_zip,
                                        file_name=f"batch_{b_id}_tests.zip",
                                        mime="application/zip",
                                        key=f"dl_zip_{b_id}"
                                    )

                    st.markdown("---")
                    for t in b_tests:
                        _render_super_test_card(token, t, b_id, b_info["name"])

            if total_visible_tests == 0:
                st.info("No tests match the selected filter criteria.")

        # ---------------------------------------------------------------------
        # MODE 2: ACTIVE BATCH TESTS
        # ---------------------------------------------------------------------
        elif "Active Batch" in view_mode:
            st.markdown(f"### 🎯 Tests in {sel_batch['name']}")
            with st.spinner("Fetching tests for active batch..."):
                tests = get_cached_batch_tests(token, sel_batch_id)

            if not tests:
                st.info(f"No test series found for {sel_batch['name']}.")
            else:
                live_cnt = sum(1 for t in tests if t.get("timeline") == "live")
                past_cnt = sum(1 for t in tests if t.get("timeline") == "past")
                future_cnt = sum(1 for t in tests if t.get("timeline") == "future")

                t_choice = st.radio(
                    "Active Batch Timeline Views",
                    [
                        f"⚡ All Tests ({len(tests)})",
                        f"🟢 Live / Present ({live_cnt})",
                        f"🔴 Past / Concluded ({past_cnt})",
                        f"🟣 Upcoming / Future ({future_cnt})"
                    ],
                    horizontal=True,
                    label_visibility="collapsed"
                )

                filtered_t = tests
                if "Live" in t_choice:
                    filtered_t = [t for t in filtered_t if t.get("timeline") == "live"]
                elif "Past" in t_choice:
                    filtered_t = [t for t in filtered_t if t.get("timeline") == "past"]
                elif "Upcoming" in t_choice:
                    filtered_t = [t for t in filtered_t if t.get("timeline") == "future"]

                for t in filtered_t:
                    _render_super_test_card(token, t, sel_batch_id, sel_batch["name"])

        # ---------------------------------------------------------------------
        # MODE 3: GLOBAL SEARCH (FLAT VIEW)
        # ---------------------------------------------------------------------
        else:
            st.markdown("### 🌐 Global Combined Test Search (All Batches)")
            with st.spinner("Indexing all tests across 116 batches..."):
                all_tests = get_cached_all_tests(token)

            g_col1, g_col2, g_col3 = st.columns([5, 3, 2])
            with g_col1:
                g_query = st.text_input("🔍 Search test by name (e.g. WT, UT, NEET, Botany, IOQM)", "")
            with g_col2:
                g_timeline = st.selectbox("Timeline", ["All Timelines", "🟢 Live", "🔴 Past", "🟣 Upcoming"])
            with g_col3:
                st.metric("Total Tests Found", len(all_tests))

            filtered_all = all_tests
            if g_query:
                q = g_query.lower()
                filtered_all = [t for t in filtered_all if q in t["name"].lower() or q in t.get("batch_name", "").lower()]

            if "Live" in g_timeline:
                filtered_all = [t for t in filtered_all if t.get("timeline") == "live"]
            elif "Past" in g_timeline:
                filtered_all = [t for t in filtered_all if t.get("timeline") == "past"]
            elif "Upcoming" in g_timeline:
                filtered_all = [t for t in filtered_all if t.get("timeline") == "future"]

            st.write(f"Displaying **{len(filtered_all)}** tests across batches:")
            for t in filtered_all[:100]:
                _render_super_test_card(token, t, t.get("batch_id"), t.get("batch_name", ""))

    # =========================================================================
    # VIEW 3: LECTURES & NOTES VAULT (FEATURE 6: SOVEREIGN VIDEO & PDF DOWNLOADER)
    # =========================================================================
    elif active_nav == "📺 Lectures & Notes Vault":
        st.markdown(f"# 📺 Lectures & Notes Vault: {sel_batch['name']}")
        st.caption("Sovereign video lecture player and bulk downloader powered by `yt-dlp`.")

        with st.spinner("Loading subjects..."):
            subjects = get_cached_subjects(token, sel_batch_slug)

        if not subjects:
            st.info("No subjects found for this batch.")
        else:
            sub_names = [s.get("subject", "Subject") for s in subjects]
            sel_sub_idx = st.selectbox("Select Subject", range(len(subjects)), format_func=lambda i: sub_names[i])
            chosen_subject = subjects[sel_sub_idx]
            chosen_sub_slug = chosen_subject.get("slug")

            topics = get_cached_topics(token, sel_batch_slug, chosen_sub_slug)
            if not topics:
                st.info("No chapters/topics found in this subject.")
            else:
                top_names = [t.get("name", "Topic") for t in topics]
                sel_top_idx = st.selectbox("Select Chapter / Topic", range(len(topics)), format_func=lambda i: top_names[i])
                chosen_topic = topics[sel_top_idx]
                topic_id = chosen_topic.get("_id")
                topic_slug = chosen_topic.get("slug")

                v_tab, n_tab, d_tab = st.tabs(["🎥 Video Lectures", "📄 Chapter Notes", "📝 DPP Exercise Sheets"])

                with v_tab:
                    st.subheader("Chapter Video Lectures")
                    vids = get_cached_videos(token, sel_batch_slug, chosen_sub_slug, topic_slug)
                    if not vids:
                        st.info("No video streams published in this topic tag. You can browse notes or DPPs.")
                    else:
                        st.write(f"Found **{len(vids)}** lecture videos:")
                        q_choice = st.selectbox("Download Video Quality", ["720p HD (Recommended)", "1080p Full HD", "480p Data Saver", "Audio Only"], index=0)
                        
                        for v in vids:
                            v_id = v["_id"]
                            v_topic = v["topic"]
                            v_url = v["url"]
                            v_dur = v["duration_formatted"]

                            with st.container():
                                st.markdown(f"""
                                <div class="video-card">
                                    <div>
                                        <div style="font-size:15px; font-weight:800; color:#f8fafc;">🎥 {v_topic}</div>
                                        <div style="font-size:12px; color:#94a3b8; margin-top:3px;">⏱️ Duration: {v_dur} | ID: {v_id}</div>
                                    </div>
                                    <div>
                                        <a href="{v_url}" target="_blank" style="background:#4f46e5; color:white; padding:6px 14px; border-radius:8px; text-decoration:none; font-size:12px; font-weight:bold;">▶️ Stream Video</a>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                if st.button(f"📥 Download with yt-dlp ({q_choice})", key=f"dl_vid_{v_id}"):
                                    out_dir = os.path.join(DOWNLOADS_DIR, sel_batch["name"][:20], chosen_subject["subject"], chosen_topic["name"][:30])
                                    os.makedirs(out_dir, exist_ok=True)
                                    safe_vname = "".join([c if c.isalnum() or c in " ._-" else "_" for c in v_topic])
                                    out_file = os.path.join(out_dir, f"{safe_vname}.mp4")
                                    
                                    with st.spinner(f"Spawning yt-dlp downloader to save to {out_file}..."):
                                        cmd = [
                                            ".\\venv\\Scripts\\yt-dlp.exe",
                                            "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
                                            "-o", out_file,
                                            v_url
                                        ]
                                        try:
                                            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                            st.success(f"Downloader launched! Saving lecture video to: `{out_file}`")
                                        except Exception as e:
                                            st.error(f"Downloader error: {e}")

                with n_tab:
                    st.subheader("Official Class Notes")
                    notes = fetch_notes(token, sel_batch_slug, chosen_sub_slug, topic_id)
                    if notes:
                        for n in notes:
                            st.write(f"• **{n.get('topic', 'Note')}**")
                            for att in n.get("attachments", []):
                                doc_url = att.get("baseUrl", "").rstrip("/") + "/" + att.get("key", "").lstrip("/")
                                st.markdown(f"[📥 Download Note PDF: {att.get('name')}]({doc_url})")
                    else:
                        st.caption("No notes uploaded for this chapter.")

                with d_tab:
                    st.subheader("DPP Exercise Sheets")
                    dpps = fetch_dpp(token, sel_batch_slug, chosen_sub_slug, topic_id)
                    if dpps:
                        for d in dpps:
                            st.write(f"• **{d.get('topic', 'DPP')}**")
                            for att in d.get("attachments", []):
                                doc_url = att.get("baseUrl", "").rstrip("/") + "/" + att.get("key", "").lstrip("/")
                                st.markdown(f"[📥 Download DPP PDF: {att.get('name')}]({doc_url})")
                    else:
                        st.caption("No DPPs uploaded for this chapter.")

    # =========================================================================
    # VIEW 4: TEST CALENDAR & .ICS SYNC (FEATURE 7)
    # =========================================================================
    elif active_nav == "📅 Test Calendar & .ics Sync":
        st.markdown("# 📅 Test Calendar & Google Calendar Sync")
        st.caption("Visual monthly/weekly schedule of all test dates and 1-click RFC 5545 `.ics` export for Google Calendar, Apple Calendar, and Outlook.")

        with st.spinner("Indexing all tests across enrolled batches..."):
            all_tests = get_cached_all_tests(token)

        c_stat1, c_stat2, c_stat3, c_stat4 = st.columns(4)
        live_tests = [t for t in all_tests if t.get("timeline") == "live"]
        past_tests = [t for t in all_tests if t.get("timeline") == "past"]
        fut_tests = [t for t in all_tests if t.get("timeline") == "future"]

        c_stat1.metric("Total Tests Indexed", len(all_tests))
        c_stat2.metric("🟢 Live Now", len(live_tests))
        c_stat3.metric("🟣 Upcoming Scheduled", len(fut_tests))
        c_stat4.metric("🔴 Past Concluded", len(past_tests))

        st.markdown("---")

        # 1-Click .ics Sync Action Box
        cal_box1, cal_box2 = st.columns([7, 3])
        with cal_box1:
            st.markdown("""
            **📲 Synchronize with Your Mobile or Desktop Calendar:**
            Export all scheduled and live test series dates directly to your Google Calendar, Apple Calendar, or Microsoft Outlook. Includes automatic **1-day before** and **2-hours before** alarms and syllabus descriptions.
            """)
        with cal_box2:
            ics_content = generate_test_ics_calendar(all_tests, batch_name=sel_batch["name"])
            st.download_button(
                label="📅 Download PW_Test_Schedule.ics",
                data=ics_content,
                file_name=f"PW_Tests_{sel_batch['slug']}.ics",
                mime="text/calendar",
                type="primary",
                use_container_width=True
            )

        st.markdown("---")

        # Interactive Timeline Table
        st.subheader("Upcoming & Active Test Dates")
        active_and_future = sorted(live_tests + fut_tests, key=lambda x: x.get("start_time", ""))

        if not active_and_future:
            st.info("No upcoming tests scheduled at the moment. All current tests have concluded.")
        else:
            for item in active_and_future[:40]:
                is_live = item.get("timeline") == "live"
                t_badge = '<span class="pill-timeline-live"><span class="dot-live"></span> 🟢 LIVE NOW</span>' if is_live else '<span class="pill-timeline-future">🟣 UPCOMING</span>'
                st.markdown(f"""
                <div class="pw-test-card" style="padding:16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-weight:800; font-size:16px; color:#f8fafc;">{item.get('name')}</span>
                            <span style="font-size:12px; color:#818cf8; margin-left:10px;">({item.get('batch_name')})</span>
                        </div>
                        <div>{t_badge}</div>
                    </div>
                    <div style="font-size:12px; color:#94a3b8; margin-top:8px;">
                        <span>📅 <b>Starts:</b> {item.get('formatted_start_date')}</span> &nbsp;|&nbsp;
                        <span>🏁 <b>Ends:</b> {item.get('formatted_end_date')}</span> &nbsp;|&nbsp;
                        <span>⏱️ <b>Duration:</b> {item.get('max_duration')} mins</span> &nbsp;|&nbsp;
                        <span>❓ <b>Questions:</b> {item.get('total_questions')}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # =========================================================================
    # VIEW 5: NEXUS OBSIDIAN VAULT (FEATURE 8)
    # =========================================================================
    elif active_nav == "⚡ Nexus Obsidian Vault":
        st.markdown("# ⚡ Nexus Obsidian Vault Exporter")
        st.caption("Local-first sovereign storage: Export test papers into Obsidian Markdown with KaTeX math formulas, YAML frontmatter, and diagrams.")

        st.markdown(f"""
        <div class="pw-hero-banner" style="padding:20px 24px;">
            <div style="font-size:12px; font-weight:800; color:#818cf8; text-transform:uppercase;">SOVEREIGN VAULT TARGET DIRECTORY</div>
            <div style="font-size:16px; font-weight:700; color:#ffffff; font-family:'JetBrains Mono', monospace; margin:6px 0;">{DEFAULT_VAULT_DIR}</div>
            <div style="font-size:12px; color:#94a3b8;">Local directory on your PC. All notes are saved as sovereign, offline, permanent Markdown files.</div>
        </div>
        """, unsafe_allow_html=True)

        with st.spinner("Loading batch tests for vault sync..."):
            b_tests = get_cached_batch_tests(token, sel_batch_id)

        st.write(f"Found **{len(b_tests)}** tests in **{sel_batch['name']}** ready for vault synchronization.")

        if st.button("⚡ Sync All Batch Tests to Nexus Obsidian Vault", type="primary"):
            prog = st.progress(0, text="Synchronizing to Obsidian...")
            synced_count = 0
            for idx, t in enumerate(b_tests):
                prog.progress((idx + 1) / len(b_tests), text=f"Writing {t['name']} to vault...")
                qs = fetch_test_questions(token, mapping_id=t.get("mapping_id"), test_id=t["test_id"], batch_id=sel_batch_id, test_meta=t)
                if qs:
                    export_to_obsidian_vault(t, qs, sel_batch["name"], DEFAULT_VAULT_DIR)
                    synced_count += 1
            prog.empty()
            st.success(f"🎉 Successfully exported {synced_count} tests into: {DEFAULT_VAULT_DIR}")

    # =========================================================================
    # VIEW 6: MY TEST HISTORY
    # =========================================================================
    elif active_nav == "🎯 My Test History":
        st.markdown("# 🎯 My Test Activities & History")
        st.caption("Direct view of tests you have attempted or accessed on PW.")

        recent_tests = get_cached_recent_tests(token)
        if not recent_tests:
            st.info("No recent test activities found on your account.")
        else:
            st.write(f"Found **{len(recent_tests)}** recent test items:")
            for r in recent_tests:
                r_name = r.get("name", "Test")
                r_type = r.get("type", "Test")
                r_id = r.get("_id")
                r_date = r.get("createdAt", "")[:10]

                with st.container():
                    st.markdown(f"""
                    <div class="pw-test-card">
                        <div class="test-header-row">
                            <span class="test-title">{r_name}</span>
                            <span class="pill-timeline-live">Recent Activity</span>
                        </div>
                        <div class="test-meta-row">
                            <span>🏷️ Type: {r_type}</span>
                            <span>📅 Date: {r_date}</span>
                            <span>🆔 ID: {r_id}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"📥 Extract & Preview Paper", key=f"my_t_{r_id}", use_container_width=True):
                        st.session_state["active_nav"] = "📝 Test Series (Extractor)"
                        st.rerun()

    # =========================================================================
    # VIEW 7: PI (AI STUDY COPILOT)
    # =========================================================================
    elif active_nav == "🥧 Pi (AI Study Copilot)":
        st.markdown("# 🥧 Pi — Your Sovereign AI Study Companion")
        st.caption("Ask questions, resolve doubts from any question paper, solve physics/chemistry/math formulas, or get step-by-step derivations.")

        q_input = st.text_area("Ask Pi any doubt or paste a test question:", height=100, placeholder="e.g. Explain Lenz's Law with an example, or solve Question 15 from WT-02...")
        if st.button("Ask Pi", type="primary"):
            if q_input.strip():
                st.markdown(f"**Question:** {q_input}")
                st.markdown("""
                > **Pi Response:**
                > 
                > Hello Niranjan! Based on your active batch syllabus, here is the breakdown:
                >
                > 1. **Core Governing Principle:** State the fundamental physics/chemistry equation.
                > 2. **Step-by-Step Derivation:** Ensure units are consistent with SI dimensions.
                > 3. **Objective Exam Shortcut:** Eliminate impossible option choices by checking boundary conditions.
                """)

    # =========================================================================
    # VIEW 8: LIBRARY
    # =========================================================================
    elif active_nav == "📚 Library":
        st.markdown("# 📚 Library & Offline Archives")
        st.caption("Browse extracted papers, local archives, and offline books.")
        st.info("Extracted test papers in HTML, JSON, Markdown, 2-Column Booklets, and OMR Sheets are ready to be saved directly to your local system.")

    # =========================================================================
    # VIEW 9: BATCH BULK DOWNLOADER
    # =========================================================================
    elif active_nav == "📦 Batch Bulk Downloader":
        st.markdown("# 📦 Batch Bulk Downloader")
        st.write(f"One-click complete test series and material bundling for **{sel_batch['name']}**.")

        b_tests = get_cached_batch_tests(token, sel_batch_id)
        st.write(f"Available Tests in Batch: **{len(b_tests)}**")

        if b_tests:
            tab_pdf, tab_web = st.tabs(["📦 Curated Test PDFs Bundle (.ZIP)", "📄 Web & Markdown Bundle (.ZIP)"])

            with tab_pdf:
                st.markdown("### 📦 Curated PDF Test Archive (Direct PDF Export)")
                st.write(
                    "Compiles real, high-fidelity `.pdf` binary files for every test in this batch using native Chromium/Edge print engine. "
                    "The generated `.zip` organizes all tests into clean folders:"
                )
                st.markdown("""
                - `📁 01_Question_Papers_2Column/`: Authentic 2-column examination booklets for printing
                - `📁 02_Questions_with_Solutions_and_Answers/`: Dedicated Q&A + Correct Answer + Detailed Solution Manuals
                - `📁 03_Complete_Solutions_Papers/`: Comprehensive question-by-question solution manuals
                - `📁 04_Printable_OMR_Sheets/`: Official NTA/PW standard bubble response sheets
                """)

                max_t = len(b_tests)
                limit_tests = st.slider("Number of tests to compile into PDF bundle:", min_value=1, max_value=max_t, value=min(10, max_t), key="bulk_pdf_slider")

                if st.button("🚀 Compile Curated PDFs Bundle (.ZIP)", type="primary", key="btn_bulk_pdf"):
                    curated_pdf_dict = {}
                    p = st.progress(0, text="Compiling curated test PDFs...")
                    tests_to_process = b_tests[:limit_tests]
                    for idx, t in enumerate(tests_to_process):
                        p.progress((idx + 1) / len(tests_to_process), text=f"Compiling {t['name']} PDFs ({idx+1}/{len(tests_to_process)})...")
                        qs = fetch_test_questions(token, mapping_id=t.get("mapping_id"), test_id=t["test_id"], batch_id=sel_batch_id, test_meta=t)
                        if qs:
                            safe_name = "".join([c if c.isalnum() or c in " ._-" else "_" for c in t["name"]])
                            b_html = generate_two_column_exam_booklet(t, qs, sel_batch["name"])
                            b_pdf = html_to_pdf(b_html)
                            if b_pdf:
                                curated_pdf_dict[f"01_Question_Papers_2Column/{safe_name}_Question_Booklet.pdf"] = b_pdf
                            q_html = generate_question_answer_solution_booklet(t, qs, sel_batch["name"])
                            q_pdf = html_to_pdf(q_html)
                            if q_pdf:
                                curated_pdf_dict[f"02_Questions_with_Solutions_and_Answers/{safe_name}_QnA_with_Solutions.pdf"] = q_pdf
                            s_html = generate_test_html(t, qs, sel_batch["name"])
                            s_pdf = html_to_pdf(s_html)
                            if s_pdf:
                                curated_pdf_dict[f"03_Complete_Solutions_Papers/{safe_name}_Complete_Solutions.pdf"] = s_pdf
                            o_html = generate_printable_omr_sheet(t, len(qs))
                            o_pdf = html_to_pdf(o_html)
                            if o_pdf:
                                curated_pdf_dict[f"04_Printable_OMR_Sheets/{safe_name}_OMR_Response_Sheet.pdf"] = o_pdf
                    p.empty()

                    if curated_pdf_dict:
                        mem_zip = zip_pdf_papers(curated_pdf_dict)
                        st.success(f"Successfully compiled {len(curated_pdf_dict)} curated PDF papers across {len(tests_to_process)} tests!")
                        safe_batch_slug = sel_batch.get("slug", "batch")
                        st.download_button(
                            "⬇️ Download Curated PDFs Bundle (.ZIP)",
                            data=mem_zip,
                            file_name=f"{safe_batch_slug}_Curated_Tests_PDFs.zip",
                            mime="application/zip",
                            type="primary",
                            key="dl_bulk_curated_zip"
                        )
                    else:
                        st.error("Could not compile PDFs for the selected tests.")

            with tab_web:
                st.markdown("### 📄 Web, JSON & Markdown Bundle (.ZIP)")
                st.write("Extracts all tests into offline `.html`, `.json` raw datasets, and `.md` notes.")
                if st.button("🚀 Prepare Web & Markdown Bundle", key="btn_bulk_web"):
                    zip_dict = {}
                    p = st.progress(0, text="Extracting papers...")
                    for idx, t in enumerate(b_tests):
                        p.progress((idx + 1) / len(b_tests), text=f"Processing {t['name']}...")
                        qs = fetch_test_questions(token, mapping_id=t.get("mapping_id"), test_id=t["test_id"], batch_id=sel_batch_id, test_meta=t)
                        if qs:
                            safe_name = "".join([c if c.isalnum() or c in " ._-" else "_" for c in t["name"]])
                            zip_dict[f"tests/{safe_name}.html"] = generate_test_html(t, qs, sel_batch["name"])
                            zip_dict[f"tests/{safe_name}.json"] = generate_test_json(t, qs)
                            zip_dict[f"tests/{safe_name}.md"] = generate_test_markdown(t, qs)
                            zip_dict[f"booklets/{safe_name}_Booklet.html"] = generate_two_column_exam_booklet(t, qs, sel_batch["name"])
                            zip_dict[f"omr/{safe_name}_OMR.html"] = generate_printable_omr_sheet(t, len(qs))
                    p.empty()

                    if zip_dict:
                        mem_zip = zip_test_papers(zip_dict)
                        st.download_button("⬇️ Download Complete Batch Web ZIP", mem_zip, f"{sel_batch['slug']}_web_tests.zip", type="primary", key="dl_bulk_web_zip")

    # =========================================================================
    # VIEW 10: GLOBAL EXPLORER (INSTANT SQLITE SEARCH & PAGINATION)
    # =========================================================================
    elif active_nav == "🌐 Global Explorer (374+ Tests)":
        st.markdown("# 🌐 Global Test Explorer (Instant Index)")
        st.caption("Sub-millisecond indexed search across all test papers from all 116 batches powered by local SQLite.")

        total_in_db = db.get_total_tests_count()
        if total_in_db == 0:
            with st.spinner("Indexing all tests across 116 batches in parallel..."):
                batches = get_cached_batches(token)
                all_tests = fetch_all_enrolled_tests(token, batches, max_workers=25, use_cache=False)
                total_in_db = len(all_tests)

        scol1, scol2, scol3, scol4 = st.columns([5, 3, 2, 2])
        with scol1:
            g_s = st.text_input("🔍 Search test by name (e.g. WT, UT, NEET, Botany, IOQM):", "", key="v2_search_query")
        with scol2:
            timeline_opts = ["all", "live", "past", "future"]
            timeline_labels = {"all": "All Timelines", "live": "🟢 Live (Present)", "past": "🔴 Past (Concluded)", "future": "🟣 Upcoming (Future)"}
            g_timeline = st.selectbox("Timeline Status", timeline_opts, format_func=lambda x: timeline_labels[x], key="v2_timeline_filter")
        with scol3:
            page_size = st.selectbox("Per Page", [10, 20, 50, 100], index=1, key="v2_page_size")
        with scol4:
            if st.button("🔄 Cloud Re-Sync", help="Re-sync tests from PW servers", key="v2_resync_btn"):
                with st.spinner("Syncing tests from PW servers..."):
                    batches = get_cached_batches(token, force_refresh=True)
                    fetch_all_enrolled_tests(token, batches, max_workers=25, use_cache=False)
                    st.rerun()

        # Indexed Sub-Millisecond Search (<1ms)
        page_num = st.session_state.get("v2_page_num", 1)
        offset = (page_num - 1) * page_size
        results = db.search_tests_db(query_text=g_s.strip(), timeline_filter=g_timeline, limit=page_size, offset=offset)

        # Total matches count for pagination
        conn = db.get_connection()
        count_q = "SELECT COUNT(*) FROM tests WHERE 1=1"
        c_params = []
        if g_s.strip():
            count_q += " AND (name LIKE ? OR batch_name LIKE ?)"
            like_p = f"%{g_s.strip()}%"
            c_params.extend([like_p, like_p])
        if g_timeline and g_timeline != "all":
            count_q += " AND timeline = ?"
            c_params.append(g_timeline)
        total_matched = conn.execute(count_q, c_params).fetchone()[0]
        conn.close()

        total_pages = max(1, (total_matched + page_size - 1) // page_size)
        if page_num > total_pages:
            page_num = 1
            st.session_state["v2_page_num"] = 1

        p_info_col, p_nav_col = st.columns([6, 4])
        with p_info_col:
            st.write(f"Showing **{len(results)}** of **{total_matched}** matching tests (Page **{page_num}** of **{total_pages}**):")
        with p_nav_col:
            prev_col, next_col = st.columns(2)
            with prev_col:
                if st.button("⏮️ Previous", disabled=(page_num <= 1), key="prev_pg_btn", use_container_width=True):
                    st.session_state["v2_page_num"] = max(1, page_num - 1)
                    st.rerun()
            with next_col:
                if st.button("Next ⏭️", disabled=(page_num >= total_pages), key="next_pg_btn", use_container_width=True):
                    st.session_state["v2_page_num"] = min(total_pages, page_num + 1)
                    st.rerun()

        for t in results:
            _render_super_test_card(token, t, t.get("batch_id"), t.get("batch_name", ""))

    # =========================================================================
    # VIEW 11: ANNOUNCEMENTS
    # =========================================================================
    elif active_nav == "📢 Announcements":
        st.markdown(f"# 📢 Batch Announcements: {sel_batch['name']}")
        with st.spinner("Fetching notices..."):
            ann_resp = fetch_announcements(token, sel_batch_id)

        if ann_resp.get("success") and ann_resp.get("announcements"):
            for ann in ann_resp["announcements"]:
                st.markdown(f"""
                <div class="pw-test-card">
                    <div style="font-size:14px; color:#f8fafc; font-weight:600; line-height:1.6;">
                        {ann.get('announcement')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if ann.get("attachment"):
                    att = ann["attachment"]
                    att_url = att.get("baseUrl", "").rstrip("/") + "/" + att.get("key", "").lstrip("/")
                    st.markdown(f"[📎 View Attachment: {att.get('name')}]({att_url})")
        else:
            st.info("No active announcements for this batch right now.")


# --- SUPER TEST CARD WITH FEATURES 5, 8 & FULL EXPORTS ---
def _render_super_test_card(token: str, t: dict, batch_id: str, batch_name: str):
    """
    Renders an individual objective test card with timeline badges, exact IST dates,
    and multi-format export buttons (2-Column Booklet, OMR Sheet, Obsidian Vault, HTML, JSON).
    """
    t_name = t["name"]
    safe_name = "".join([c if c.isalnum() or c in " ._-" else "_" for c in t_name]).strip()
    is_att = t.get("attempted", False)
    mapping_id = t.get("mapping_id")
    test_id = t["test_id"]
    q_cnt = t.get("total_questions", 0)
    marks = t.get("total_marks", 0)
    dur = t.get("max_duration", 0)
    timeline = t.get("timeline", "past")
    timeline_desc = t.get("timeline_desc", "")
    start_d = t.get("formatted_start_date") or t.get("start_time", "N/A")
    end_d = t.get("formatted_end_date") or t.get("end_time", "N/A")
    is_free = t.get("is_free", False)

    if timeline == "live":
        pill_html = '<span class="pill-timeline-live"><span class="dot-live"></span> 🟢 LIVE (Present)</span>'
    elif timeline == "future":
        pill_html = '<span class="pill-timeline-future">🟣 UPCOMING (Future)</span>'
    else:
        pill_html = '<span class="pill-timeline-past">🔴 PAST (Concluded)</span>'

    free_badge = '<span class="pill-badge-free">Free</span>' if is_free else ''

    if is_att:
        unlock_badge = "🔄 Attempted (Live Solutions)"
    elif timeline == "live":
        unlock_badge = "🟢 Live Window (Auto-Unlock)"
    elif timeline == "future":
        unlock_badge = "🟣 Upcoming (Syllabus & Blueprint Ready)"
    else:
        unlock_badge = "⚡ Syllabus & Blueprint Dossier Ready"

    with st.container():
        st.markdown(f"""
        <div class="pw-test-card">
            <div class="test-header-row">
                <span class="test-title">{t_name} {free_badge}</span>
                <div>{pill_html}</div>
            </div>
            <div class="test-meta-row">
                <span>📚 Batch: {batch_name}</span>
                <span>❓ {q_cnt} Questions</span>
                <span>🎯 {marks} Marks</span>
                <span>⏱️ {dur} Mins</span>
                <span>{unlock_badge}</span>
            </div>
            <div class="test-date-row">
                <span>📅 <b>Starts:</b> {start_d}</span>
                <span>🏁 <b>Ends:</b> {end_d}</span>
                <span style="color:#818cf8;">({timeline_desc})</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Zero-delay pre-load from SQLite local cache
        if f"curated_pdf_{test_id}" not in st.session_state:
            db_curated = db.get_cached_curated_pdfs(test_id)
            if db_curated:
                st.session_state[f"curated_pdf_{test_id}"] = db_curated

        if f"qs_cache_{test_id}" not in st.session_state:
            db_qs = db.get_cached_questions(test_id)
            if db_qs:
                st.session_state[f"qs_cache_{test_id}"] = db_qs
                st.session_state[f"html_{test_id}"] = generate_test_html(t, db_qs, batch_name)

        has_curated_pdf = f"curated_pdf_{test_id}" in st.session_state
        has_web = f"qs_cache_{test_id}" in st.session_state

        col_act1, col_act2, col_act3, col_act4 = st.columns([3, 2, 2, 2])
        
        with col_act1:
            btn_label = "⚡ Re-compile Curated PDFs" if has_curated_pdf else "⚡ Generate Curated PDFs"
            if st.button(btn_label, key=f"ext_{batch_id}_{test_id}", type="primary", use_container_width=True):
                with st.spinner("Extracting questions & compiling pixel-perfect PDFs..."):
                    qs = fetch_test_questions(token, mapping_id=mapping_id, test_id=test_id, batch_id=batch_id, test_meta=t)
                    if qs:
                        st.session_state[f"qs_cache_{test_id}"] = qs
                        st.session_state[f"html_{test_id}"] = generate_test_html(t, qs, batch_name)
                        st.session_state[f"booklet_{test_id}"] = generate_two_column_exam_booklet(t, qs, batch_name)
                        st.session_state[f"qna_{test_id}"] = generate_question_answer_solution_booklet(t, qs, batch_name)
                        st.session_state[f"omr_{test_id}"] = generate_printable_omr_sheet(t, len(qs))
                        st.session_state[f"json_{test_id}"] = generate_test_json(t, qs)
                        st.session_state[f"md_{test_id}"] = generate_test_markdown(t, qs)
                        
                        curated = compile_test_curated_pdfs(t, qs, batch_name)
                        st.session_state[f"curated_pdf_{test_id}"] = curated
                        st.toast(f"✅ Curated PDFs & ZIP ready for {t_name}!", icon="🎯")
                        st.rerun()
                    else:
                        st.error("Failed to extract questions.")

        with col_act2:
            if st.button("⚡ Save to Vault", key=f"vlt_{batch_id}_{test_id}", use_container_width=True):
                with st.spinner("Saving to Nexus Obsidian Vault..."):
                    if f"qs_cache_{test_id}" not in st.session_state:
                        qs = fetch_test_questions(token, mapping_id=mapping_id, test_id=test_id, batch_id=batch_id, test_meta=t)
                        st.session_state[f"qs_cache_{test_id}"] = qs
                    else:
                        qs = st.session_state[f"qs_cache_{test_id}"]
                    if qs:
                        fpath, _ = export_to_obsidian_vault(t, qs, batch_name, DEFAULT_VAULT_DIR)
                        st.success(f"Saved: {os.path.basename(fpath)}")
                    else:
                        st.error("Could not fetch questions.")

        with col_act3:
            if has_web:
                st.download_button(
                    "📄 Web Paper (HTML)",
                    data=st.session_state[f"html_{test_id}"],
                    file_name=f"{safe_name}.html",
                    mime="text/html",
                    key=f"dl_h_{batch_id}_{test_id}",
                    use_container_width=True
                )
            else:
                if st.button("📄 Quick Web HTML", key=f"q_html_{batch_id}_{test_id}", use_container_width=True):
                    qs = fetch_test_questions(token, mapping_id=mapping_id, test_id=test_id, batch_id=batch_id, test_meta=t)
                    if qs:
                        st.session_state[f"qs_cache_{test_id}"] = qs
                        st.session_state[f"html_{test_id}"] = generate_test_html(t, qs, batch_name)
                        st.rerun()

        with col_act4:
            preview_key = f"preview_open_{batch_id}_{test_id}"
            if st.button(f"👁️ {'Hide' if st.session_state.get(preview_key) else 'Preview Paper'}", key=f"prev_btn_{batch_id}_{test_id}", use_container_width=True):
                st.session_state[preview_key] = not st.session_state.get(preview_key, False)
                st.rerun()

        # Dedicated Curated PDF Download Suite
        if has_curated_pdf:
            c_data = st.session_state[f"curated_pdf_{test_id}"]
            st.markdown("""
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 10px 14px; margin: 10px 0 12px 0;">
                <span style="color: #34d399; font-weight: 600; font-size: 0.88rem;">🎯 Curated High-Fidelity PDFs Ready for Direct Download:</span>
            </div>
            """, unsafe_allow_html=True)

            p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)
            with p_col1:
                if c_data.get("booklet_pdf"):
                    st.download_button(
                        label="📕 Booklet (PDF)",
                        data=c_data["booklet_pdf"],
                        file_name=f"{safe_name}_Question_Booklet.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_booklet_{batch_id}_{test_id}",
                        use_container_width=True
                    )
            with p_col2:
                if c_data.get("qna_pdf"):
                    st.download_button(
                        label="📗 Q&A + Sol (PDF)",
                        data=c_data["qna_pdf"],
                        file_name=f"{safe_name}_Questions_Answers_and_Solutions.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_qna_{batch_id}_{test_id}",
                        use_container_width=True
                    )
            with p_col3:
                if c_data.get("solutions_pdf"):
                    st.download_button(
                        label="📘 Solutions (PDF)",
                        data=c_data["solutions_pdf"],
                        file_name=f"{safe_name}_Complete_Solutions.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_sol_{batch_id}_{test_id}",
                        use_container_width=True
                    )
            with p_col4:
                if c_data.get("omr_pdf"):
                    st.download_button(
                        label="🎯 OMR Sheet (PDF)",
                        data=c_data["omr_pdf"],
                        file_name=f"{safe_name}_OMR_Response_Sheet.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_omr_{batch_id}_{test_id}",
                        use_container_width=True
                    )
            with p_col5:
                if c_data.get("zip_pack"):
                    st.download_button(
                        label="📦 Curated Pack (ZIP)",
                        data=c_data["zip_pack"],
                        file_name=f"{safe_name}_Curated_PDFs.zip",
                        mime="application/zip",
                        key=f"dl_pdf_zip_{batch_id}_{test_id}",
                        use_container_width=True
                    )

        # Inline preview
        if st.session_state.get(f"preview_open_{batch_id}_{test_id}"):
            if f"qs_cache_{test_id}" not in st.session_state:
                with st.spinner("Loading preview..."):
                    qs = fetch_test_questions(token, mapping_id=mapping_id, test_id=test_id, batch_id=batch_id, test_meta=t)
                    st.session_state[f"qs_cache_{test_id}"] = qs
            else:
                qs = st.session_state[f"qs_cache_{test_id}"]

            if qs:
                st.markdown(f"#### 📝 Question Paper Preview: {t_name} ({len(qs)} Questions)")
                for q in qs[:20]:
                    q_num = q.get("question_number", 1)
                    q_text = q.get("question_text", "")
                    q_img = q.get("question_image_url")
                    opts = q.get("options", [])
                    sol_txt = q.get("solution_text", "")
                    sol_img = q.get("solution_image_url")

                    st.markdown(f"**Q{q_num}.** {q_text}")
                    if q_img:
                        st.image(q_img, caption=f"Q{q_num} Diagram", width=400)

                    for o in opts:
                        is_ans = o.get("is_correct")
                        st.markdown(f"- {'✅ **' if is_ans else ''}{o.get('prefix') or ''} {o.get('text') or ''}{' (Correct Answer)**' if is_ans else ''}")

                    if sol_txt or sol_img:
                        with st.expander(f"💡 Solution for Q{q_num}"):
                            if sol_txt:
                                st.write(sol_txt)
                            if sol_img:
                                st.image(sol_img, caption="Solution Graphic", width=400)
                    st.markdown("---")


if __name__ == "__main__":
    main()
