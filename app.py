import hashlib
import hmac
import html
import math
import os
import json
import re
import urllib.parse
from datetime import date, datetime
import gspread
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

st.set_page_config(
    page_title="TIMESH Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

SPREADSHEET_NAME = "Untitled spreadsheet"
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
PHOTO_DIR = "faculty_photos"
os.makedirs(PHOTO_DIR, exist_ok=True)

USERS_TAB_NAME = "Users"
LOGS_TAB_NAME = "Activity_Logs"
REQUESTS_TAB_NAME = "Feature_Requests"

USERS_HEADERS = ["Username", "Name", "Role", "Password_Hash", "Created_At"]
LOGS_HEADERS = ["Timestamp", "Username", "Name", "Role", "Action", "Module", "Details"]
REQUESTS_HEADERS = ["Timestamp", "Username", "Name", "Role", "Question", "Status", "Admin_Note"]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

STATUS_OPTIONS = ["All", "(Blanks)", "Exit", "Expire", "OK"]
FORM_STATUS_OPTIONS = ["OK", "Exit", "Expire", ""]

LEAVE_TYPE_OPTIONS = ["CL", "El", "CCL"]
APPLYING_STATUS_OPTIONS = ["YES", "NO"]
TAKE_ACTION_BY_OPTIONS = ["Julfikkar", "Azad", "Safiur"]


def hash_password(password: str, salt: str = "timesh_secure_salt_2026") -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), str(stored_hash).strip())


DEFAULT_USERS = {
    "admin": {
        "name": "System Admin",
        "role": "admin",
        "password_hash": hash_password("admin@123"),
        "created_at": "2026-01-01 00:00:00",
    },
    "staff": {
        "name": "Staff User",
        "role": "user",
        "password_hash": hash_password("timesh@123"),
        "created_at": "2026-01-01 00:00:00",
    },
}

NAV_ITEMS = [
    {
        "key": "Analytics Dashboard",
        "icon": "📊",
        "title": "Analytics",
    },
    {
        "key": "FACULTY_CORNER",
        "icon": "👨‍🏫",
        "title": "FACULTY_CORNER",
    },
    {
        "key": "Leave",
        "icon": "🗓️",
        "title": "Leave",
    },
    {
        "key": "Do Not Punch",
        "icon": "🚫",
        "title": "Do Not Punch",
    },
    {
        "key": "Other Sheet Tabs",
        "icon": "📑",
        "title": "Other Tabs",
    },
    {
        "key": "Users",
        "icon": "🔐",
        "title": "Users & Logs",
    },
]

CHART_COLORS = [
    "#14b8a6",
    "#38bdf8",
    "#f59e0b",
    "#f43f5e",
    "#a855f7",
    "#22c55e",
    "#fb923c",
    "#6366f1",
    "#ec4899",
    "#94a3b8",
]

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
    background: radial-gradient(circle at top right, rgba(20, 184, 166, 0.08), transparent 36%),
                radial-gradient(circle at top left, rgba(56, 189, 248, 0.07), transparent 32%),
                #0b1120;
    color: #f1f5f9;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #0b1120 100%);
    border-right: 1px solid rgba(148, 163, 184, 0.14);
}

section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.2rem;
}

.sidebar-brand {
    background: linear-gradient(135deg, rgba(20, 184, 166, 0.20), rgba(56, 189, 248, 0.10));
    border: 1px solid rgba(20, 184, 166, 0.38);
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 14px;
}

.sidebar-brand-title {
    font-size: 16px;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: 0.3px;
}

.sidebar-brand-sub {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 2px;
}

.nav-section-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    color: #64748b;
    margin: 8px 0 10px 4px;
}

div[data-testid="stSidebar"] div.stButton > button {
    width: 100%;
    text-align: left !important;
    justify-content: flex-start !important;
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 11px;
    padding: 10px 13px;
    color: #cbd5e1;
    font-weight: 600;
    font-size: 14px;
    transition: all 0.16s ease;
    margin-bottom: 6px;
}

div[data-testid="stSidebar"] div.stButton > button:hover {
    background: rgba(30, 41, 59, 0.9);
    border-color: rgba(20, 184, 166, 0.45);
    color: #f8fafc;
}

div[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, rgba(20, 184, 166, 0.24), rgba(13, 148, 136, 0.14)) !important;
    border: 1px solid rgba(45, 212, 191, 0.65) !important;
    border-left: 4px solid #2dd4bf !important;
    color: #5eead4 !important;
    font-weight: 700 !important;
    box-shadow: 0 6px 16px -8px rgba(20, 184, 166, 0.45);
}

.sidebar-info-box {
    background: rgba(15, 23, 42, 0.72);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 12px;
    padding: 12px 14px;
    font-size: 12px;
    color: #94a3b8;
    margin-top: 8px;
}

.sidebar-info-row {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 5px;
}

.sidebar-info-row:last-child {
    margin-bottom: 0;
}

.sidebar-info-val {
    color: #e2e8f0;
    font-weight: 600;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* Top page banner */
.page-banner {
    background: linear-gradient(120deg, rgba(17, 24, 39, 0.96), rgba(15, 23, 42, 0.92));
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-left: 4px solid #14b8a6;
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 18px;
    box-shadow: 0 10px 25px -10px rgba(0, 0, 0, 0.55);
}

.page-banner-title {
    font-size: 24px;
    font-weight: 700;
    color: #f8fafc;
    margin: 0;
    line-height: 1.25;
}

.page-banner-meta {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 6px;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background: rgba(17, 24, 39, 0.88);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 12px;
    padding: 14px 18px;
    box-shadow: 0 6px 18px -8px rgba(0, 0, 0, 0.45);
}

div[data-testid="stMetric"] label {
    color: #94a3b8 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #f8fafc !important;
    font-weight: 700 !important;
}

/* Tabs styling */
button[data-baseweb="tab"] {
    background-color: rgba(15, 23, 42, 0.7) !important;
    border: 1px solid rgba(148, 163, 184, 0.14) !important;
    border-radius: 10px 10px 0 0 !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    padding: 10px 18px !important;
    margin-right: 6px !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background-color: rgba(20, 184, 166, 0.16) !important;
    border-color: rgba(20, 184, 166, 0.5) !important;
    color: #5eead4 !important;
}

/* Main content primary buttons */
.stMain .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0d9488, #14b8a6);
    color: #06202a;
    font-weight: 700;
    border: none;
    border-radius: 9px;
}

.stMain .stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #14b8a6, #2dd4bf);
    color: #041820;
}

.stMain .stButton > button {
    border-radius: 9px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    font-weight: 500;
}

/* Section card wrapper */
.form-panel {
    background: rgba(17, 24, 39, 0.86);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 14px;
    padding: 18px 20px;
    margin: 12px 0 18px 0;
}

.section-tag {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: #5eead4;
    background: rgba(20, 184, 166, 0.14);
    border: 1px solid rgba(20, 184, 166, 0.3);
    padding: 3px 9px;
    border-radius: 999px;
    margin-bottom: 10px;
}

.leave-badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    background: rgba(56, 189, 248, 0.15);
    color: #7dd3fc;
    border: 1px solid rgba(56, 189, 248, 0.3);
}

.days-pill {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    background: rgba(245, 158, 11, 0.16);
    color: #fcd34d;
    border: 1px solid rgba(245, 158, 11, 0.32);
}

.notice-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    background: rgba(244, 63, 94, 0.18);
    color: #fda4af;
    border: 1px solid rgba(244, 63, 94, 0.4);
}

.muted-sub {
    color: #94a3b8;
    font-size: 12.5px;
}

.ai-reply-box {
    background: rgba(15, 23, 42, 0.92);
    border: 1px solid rgba(45, 212, 191, 0.45);
    border-left: 4px solid #14b8a6;
    border-radius: 12px;
    padding: 14px 16px;
    margin: 10px 0;
    color: #f1f5f9;
    font-size: 14px;
    line-height: 1.55;
}

.ai-missing-box {
    background: rgba(30, 27, 75, 0.55);
    border: 1px solid rgba(251, 191, 36, 0.55);
    border-left: 4px solid #f59e0b;
    border-radius: 12px;
    padding: 14px 16px;
    margin: 10px 0;
    color: #fef3c7;
    font-size: 14px;
    line-height: 1.55;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_banner(title, subtitle):
    st.markdown(
        f"<div class='page-banner'>"
        f"<div class='page-banner-title'>{html.escape(title)}</div>"
        f"<div class='page-banner-meta'>{subtitle}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


@st.cache_resource
def get_gspread_client():
    creds = None
    if "TOKEN_JSON" in st.secrets:
        token_info = json.loads(st.secrets["TOKEN_JSON"])
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    elif os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if "CREDENTIALS_JSON" in st.secrets:
                client_config = json.loads(st.secrets["CREDENTIALS_JSON"])
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
    return gspread.authorize(creds)

def clear_sheet_cache():
    st.cache_data.clear()


def ensure_system_tabs(sheet_name):
    """Ensure 'Users', 'Activity_Logs', and 'Feature_Requests' tabs exist in Google Sheet."""
    client = get_gspread_client()
    sh = client.open(sheet_name)
    existing_titles = {ws.title: ws for ws in sh.worksheets()}

    if USERS_TAB_NAME not in existing_titles:
        ws_users = sh.add_worksheet(title=USERS_TAB_NAME, rows=100, cols=10)
        ws_users.append_row(USERS_HEADERS, value_input_option="USER_ENTERED")
        for uname, info in DEFAULT_USERS.items():
            ws_users.append_row(
                [
                    uname,
                    info["name"],
                    info["role"],
                    info["password_hash"],
                    info.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ],
                value_input_option="USER_ENTERED",
            )
    else:
        ws_users = existing_titles[USERS_TAB_NAME]
        vals = ws_users.get_all_values()
        if not vals:
            ws_users.append_row(USERS_HEADERS, value_input_option="USER_ENTERED")
            for uname, info in DEFAULT_USERS.items():
                ws_users.append_row(
                    [
                        uname,
                        info["name"],
                        info["role"],
                        info["password_hash"],
                        info.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    ],
                    value_input_option="USER_ENTERED",
                )
        elif len(vals) == 1:
            for uname, info in DEFAULT_USERS.items():
                ws_users.append_row(
                    [
                        uname,
                        info["name"],
                        info["role"],
                        info["password_hash"],
                        info.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    ],
                    value_input_option="USER_ENTERED",
                )

    if LOGS_TAB_NAME not in existing_titles:
        ws_logs = sh.add_worksheet(title=LOGS_TAB_NAME, rows=1000, cols=10)
        ws_logs.append_row(LOGS_HEADERS, value_input_option="USER_ENTERED")
    else:
        ws_logs = existing_titles[LOGS_TAB_NAME]
        lvals = ws_logs.get_all_values()
        if not lvals:
            ws_logs.append_row(LOGS_HEADERS, value_input_option="USER_ENTERED")

    if REQUESTS_TAB_NAME not in existing_titles:
        ws_req = sh.add_worksheet(title=REQUESTS_TAB_NAME, rows=500, cols=10)
        ws_req.append_row(REQUESTS_HEADERS, value_input_option="USER_ENTERED")
    else:
        ws_req = existing_titles[REQUESTS_TAB_NAME]
        rvals = ws_req.get_all_values()
        if not rvals:
            ws_req.append_row(REQUESTS_HEADERS, value_input_option="USER_ENTERED")


@st.cache_data(ttl=30)
def load_users_from_sheet(sheet_name):
    client = get_gspread_client()
    sh = client.open(sheet_name)
    ws = sh.worksheet(USERS_TAB_NAME)
    values = ws.get_all_values()
    users_map = {}
    if not values or len(values) < 2:
        return users_map

    headers = [str(h).strip() for h in values[0]]
    for row_idx, raw in enumerate(values[1:], start=2):
        if not any(str(c).strip() for c in raw):
            continue
        rec = {headers[i]: (raw[i] if i < len(raw) else "") for i in range(len(headers)) if headers[i]}
        uname = str(rec.get("Username", "")).strip().lower()
        if not uname:
            continue
        users_map[uname] = {
            "_sheet_row": row_idx,
            "name": str(rec.get("Name", uname)).strip(),
            "role": str(rec.get("Role", "user")).strip().lower() or "user",
            "password_hash": str(rec.get("Password_Hash", "")).strip(),
            "created_at": str(rec.get("Created_At", "")).strip(),
        }
    return users_map


def add_user_to_sheet(sheet_name, username, full_name, role, raw_password):
    client = get_gspread_client()
    sh = client.open(sheet_name)
    ws = sh.worksheet(USERS_TAB_NAME)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row(
        [
            username.strip().lower(),
            full_name.strip() or username.strip().lower(),
            role.strip().lower(),
            hash_password(raw_password),
            now_str,
        ],
        value_input_option="USER_ENTERED",
    )
    clear_sheet_cache()


def update_user_password_in_sheet(sheet_name, username, new_password):
    client = get_gspread_client()
    sh = client.open(sheet_name)
    ws = sh.worksheet(USERS_TAB_NAME)
    values = ws.get_all_values()
    if not values:
        return False
    headers = [str(h).strip() for h in values[0]]
    uname_col = headers.index("Username") + 1 if "Username" in headers else 1
    hash_col = headers.index("Password_Hash") + 1 if "Password_Hash" in headers else 4

    for r_idx in range(2, len(values) + 1):
        cell_u = str(values[r_idx - 1][uname_col - 1]).strip().lower() if len(values[r_idx - 1]) >= uname_col else ""
        if cell_u == username.strip().lower():
            ws.update_cell(r_idx, hash_col, hash_password(new_password))
            clear_sheet_cache()
            return True
    return False


def write_activity_log(sheet_name, actor_user, action, module, details):
    """Append an action audit entry into 'Activity_Logs' tab."""
    try:
        client = get_gspread_client()
        sh = client.open(sheet_name)
        if LOGS_TAB_NAME not in [w.title for w in sh.worksheets()]:
            ws_logs = sh.add_worksheet(title=LOGS_TAB_NAME, rows=1000, cols=10)
            ws_logs.append_row(LOGS_HEADERS, value_input_option="USER_ENTERED")
        else:
            ws_logs = sh.worksheet(LOGS_TAB_NAME)
            if not ws_logs.get_all_values():
                ws_logs.append_row(LOGS_HEADERS, value_input_option="USER_ENTERED")

        u = actor_user or {}
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws_logs.append_row(
            [
                ts_str,
                str(u.get("username", "unknown")).strip(),
                str(u.get("name", "Unknown")).strip(),
                str(u.get("role", "user")).strip().upper(),
                str(action).strip(),
                str(module).strip(),
                str(details).strip(),
            ],
            value_input_option="USER_ENTERED",
        )
        clear_sheet_cache()
    except Exception:
        pass


def send_feature_notice_to_admin(sheet_name, actor_user, question_text):
    """Save a missing-feature / user question notice into 'Feature_Requests' sheet for Admin."""
    client = get_gspread_client()
    sh = client.open(sheet_name)
    if REQUESTS_TAB_NAME not in [w.title for w in sh.worksheets()]:
        ws_req = sh.add_worksheet(title=REQUESTS_TAB_NAME, rows=500, cols=10)
        ws_req.append_row(REQUESTS_HEADERS, value_input_option="USER_ENTERED")
    else:
        ws_req = sh.worksheet(REQUESTS_TAB_NAME)
        if not ws_req.get_all_values():
            ws_req.append_row(REQUESTS_HEADERS, value_input_option="USER_ENTERED")

    u = actor_user or {}
    ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws_req.append_row(
        [
            ts_str,
            str(u.get("username", "unknown")).strip(),
            str(u.get("name", "Unknown")).strip(),
            str(u.get("role", "user")).strip().upper(),
            str(question_text).strip(),
            "Pending",
            "",
        ],
        value_input_option="USER_ENTERED",
    )
    clear_sheet_cache()


def update_feature_notice_status(sheet_name, sheet_row, new_status, admin_note=""):
    client = get_gspread_client()
    sh = client.open(sheet_name)
    ws = sh.worksheet(REQUESTS_TAB_NAME)
    ws.update_cell(int(sheet_row), 6, str(new_status).strip())
    ws.update_cell(int(sheet_row), 7, str(admin_note).strip())
    clear_sheet_cache()


@st.cache_data(ttl=30)
def load_worksheet_rows_with_index(sheet_name, tab_name):
    client = get_gspread_client()
    sh = client.open(sheet_name)
    ws = sh.worksheet(tab_name)
    values = ws.get_all_values()
    if not values:
        return [], []
    headers = [str(h).strip() for h in values[0]]
    rows = []
    for idx, raw_row in enumerate(values[1:], start=2):
        if not any(str(cell).strip() for cell in raw_row):
            continue
        row_dict = {"_sheet_row": idx}
        for col_i, h in enumerate(headers):
            if h:
                row_dict[h] = raw_row[col_i] if col_i < len(raw_row) else ""
        rows.append(row_dict)
    return headers, rows


@st.cache_data(ttl=30)
def get_all_tab_names(sheet_name):
    client = get_gspread_client()
    sh = client.open(sheet_name)
    return [ws.title for ws in sh.worksheets()]


# ================= AI KNOWLEDGE BASE & QUESTION ANSWER ENGINE =================
AI_KNOWLEDGE_BASE = [
    {
        "id": "apply_leave",
        "keywords": [
            "leave apply", "apply leave", "add leave", "leave add", "chuti", "ছুটি",
            "leave debo", "leave korbo", "leave suggest", "upcoming leave", "leave entry",
        ],
        "title": "Leave Apply / Add করার নিয়ম",
        "answer_user": (
            "✅ **এই অপশনটি অ্যাপে রয়েছে! কীভাবে Leave যোগ করবেন:**\n"
            "1. বাম পাশের মেনু থেকে **🗓️ Leave** সেকশনে যান।\n"
            "2. **💡 Leave Suggest** ট্যাবে ক্লিক করুন এবং ফ্যাকাল্টির নাম/কোড সার্চ করে তাঁর নামের ডান পাশের **Add** বাটনে ক্লিক করুন।\n"
            "3. **From** এবং **Upto** তারিখ, **Leave_types** (CL / El / CCL), **Applying_Stutas.** (YES / NO) এবং **Take_Action_By** সিলেক্ট করে **Save Leave** চাপুন।\n"
            "4. আসন্ন ছুটি দেখতে **📅 Upcoming Leave** ট্যাব এবং সব পুরনো রেকর্ড দেখতে **🗂️ All Leave Records** ট্যাব ব্যবহার করুন।"
        ),
        "answer_admin": (
            "✅ **এই অপশনটি অ্যাপে রয়েছে! কীভাবে Leave যোগ করবেন:**\n"
            "1. বাম পাশের মেনু থেকে **🗓️ Leave** সেকশনে যান।\n"
            "2. **💡 Leave Suggest** ট্যাবে ক্লিক করুন এবং ফ্যাকাল্টির নাম/কোড সার্চ করে ডান পাশের **Add** বাটনে ক্লিক করুন।\n"
            "3. **From**, **Upto**, **Leave_types** (CL / El / CCL), **Applying_Stutas.** এবং **Take_Action_By** দিয়ে **Save Leave** চাপুন।"
        ),
    },
    {
        "id": "edit_record",
        "keywords": [
            "edit", "update", "modify", "change record", "poriborton", "সংশোধন",
            "এডিট", "ভুল ঠিক", "edit korbo", "update korbo",
        ],
        "title": "যেকোনো রেকর্ড Edit / Update করার নিয়ম",
        "answer_user": (
            "✅ **এই অপশনটি অ্যাপে রয়েছে! কীভাবে Edit করবেন:**\n"
            "- **Faculty তথ্য Edit করতে:** **👨‍🏫 FACULTY_CORNER → ✏️ Edit Faculty** ট্যাবে গিয়ে ফ্যাকাল্টি সিলেক্ট করে তথ্য বদলে **Save Changes** চাপুন (EMP_Code, EMP_Name, SL ফ্রোজেন থাকবে)।\n"
            "- **Leave Edit করতে:** **🗓️ Leave → 🗂️ All Leave Records** ট্যাবে গিয়ে নির্দিষ্ট রেকর্ডের পাশে **Edit** বাটনে ক্লিক করে তারিখ বা তথ্য বদলে **Update Leave** চাপুন।\n"
            "- **Do Not Punch Edit করতে:** **🚫 Do Not Punch → 📄 Do Not Punch Record** ট্যাবে গিয়ে **Edit** বাটনে ক্লিক করে **Update Record** চাপুন।"
        ),
        "answer_admin": (
            "✅ **এই অপশনটি অ্যাপে রয়েছে! কীভাবে Edit করবেন:**\n"
            "- **Faculty তথ্য Edit করতে:** **👨‍🏫 FACULTY_CORNER → ✏️ Edit Faculty** ট্যাবে গিয়ে ফ্যাকাল্টি সিলেক্ট করে তথ্য বদলে **Save Changes** চাপুন।\n"
            "- **Leave Edit করতে:** **🗓️ Leave → 🗂️ All Leave Records** ট্যাবে গিয়ে **Edit** বাটনে ক্লিক করে **Update Leave** চাপুন।\n"
            "- **Do Not Punch Edit করতে:** **🚫 Do Not Punch → 📄 Do Not Punch Record** ট্যাবে গিয়ে **Edit** বাটনে ক্লিক করে **Update Record** চাপুন।"
        ),
    },
    {
        "id": "delete_record",
        "keywords": [
            "delete", "delet", "remove", "cancel record", "ডিলিট", "মুছব", "delet korbo", "delete korbo",
        ],
        "title": "রেকর্ড Delete করার নিয়ম",
        "answer_user": (
            "🔒 **নিরাপত্তার কারণে সাধারণ User-এর জন্য Delete অপশন বন্ধ রাখা হয়েছে।**\n"
            "- শুধুমাত্র **Admin** অ্যাকাউন্ট থেকে **Leave** বা **Do Not Punch** রেকর্ড ডিলিট করা যায়।\n"
            "- কোনো রেকর্ড ভুল হয়ে থাকলে আপনি **Edit** বাটন ব্যবহার করে সেটি সংশোধন করতে পারেন, অথবা ডিলিট করার জন্য **Admin**-কে অনুরোধ করতে পারেন।"
        ),
        "answer_admin": (
            "✅ **আপনি Admin হিসেবে Delete করতে পারবেন:**\n"
            "- **Leave Delete করতে:** **🗓️ Leave → 🗂️ All Leave Records** ট্যাবে গিয়ে নির্দিষ্ট সারির ডান পাশের **Delete** বাটনে ক্লিক করে **Confirm Delete** চাপুন।\n"
            "- **Do Not Punch Delete করতে:** **🚫 Do Not Punch → 📄 Do Not Punch Record** ট্যাবে গিয়ে **Delete** বাটনে ক্লিক করে **Confirm Delete** চাপুন।"
        ),
    },
    {
        "id": "do_not_punch",
        "keywords": [
            "do not punch", "don not punch", "dnp", "punch", "পাঞ্চ", "ডু নট পাঞ্চ",
        ],
        "title": "Do Not Punch এন্ট্রি দেওয়ার নিয়ম",
        "answer_user": (
            "✅ **এই অপশনটি অ্যাপে রয়েছে! কীভাবে Do Not Punch দেবেন:**\n"
            "1. বাম পাশের মেনু থেকে **🚫 Do Not Punch** সেকশনে যান।\n"
            "2. **➕ Add** ট্যাবে ফ্যাকাল্টির Name, EMP Code বা SL দিয়ে সার্চ করে সিলেক্ট করুন (বাকি তথ্য Sheet1 থেকে অটো-ফিল হয়ে যাবে)।\n"
            "3. **Do Not Punch From**, **Do Not Punch Upto**, **Notification Date** ও **Notification issue By** দিয়ে **Save Do Not Punch** চাপুন।\n"
            "4. পুরনো এন্ট্রি দেখতে বা এডিট করতে **📄 Do Not Punch Record** ট্যাব ব্যবহার করুন।"
        ),
        "answer_admin": (
            "✅ **এই অপশনটি অ্যাপে রয়েছে! কীভাবে Do Not Punch দেবেন:**\n"
            "1. **🚫 Do Not Punch → ➕ Add** ট্যাবে ফ্যাকাল্টি সার্চ করে সিলেক্ট করুন।\n"
            "2. তারিখ ও নোটিফিকেশন তথ্য দিয়ে **Save Do Not Punch** চাপুন। সব এন্ট্রি **📄 Do Not Punch Record** ট্যাবে দেখা যাবে।"
        ),
    },
    {
        "id": "faculty_corner",
        "keywords": [
            "faculty", "add faculty", "new faculty", "photo", "upload photo", "directory", "ফ্যাকাল্টি", "ছবি",
        ],
        "title": "Faculty Directory, নতুন Faculty ও Photo আপলোড",
        "answer_user": (
            "✅ **এই অপশনটি অ্যাপে রয়েছে! কীভাবে ব্যবহার করবেন:**\n"
            "- **View Faculty:** **👨‍🏫 FACULTY_CORNER → 📋 View Faculty** ট্যাবে Department, Status বা Category দিয়ে ফিল্টার ও সার্চ করুন।\n"
            "- **Add New Faculty:** **➕ Add New Faculty** ট্যাবে নতুন ফ্যাকাল্টি যোগ করুন (SL অটোমেটিক পরের নম্বর নেবে)।\n"
            "- **Upload Photo:** **🖼️ Upload Photo** ট্যাবে গিয়ে ফ্যাকাল্টি সিলেক্ট করে ছবি আপলোড করুন।"
        ),
        "answer_admin": (
            "✅ **এই অপশনটি অ্যাপে রয়েছে!** **👨‍🏫 FACULTY_CORNER** সেকশনে গিয়ে **View Faculty**, **Edit Faculty**, **Add New Faculty** এবং **Upload Photo**—এই ৪টি ট্যাব ব্যবহার করতে পারবেন।"
        ),
    },
    {
        "id": "analytics_dashboard",
        "keywords": [
            "analytics", "chart", "pie", "dashboard", "virtual", "inhouse", "status ok", "চার্ট",
        ],
        "title": "Analytics Dashboard ব্যবহারের নিয়ম",
        "answer_user": (
            "✅ **এই অপশনটি অ্যাপে রয়েছে!**\n"
            "1. বাম পাশের মেনু থেকে **📊 Analytics** সেকশনে যান।\n"
            "2. এখানে **Status = OK** থাকা ফ্যাকাল্টিদের **Total_Virtual**, **Pure_Inhouse** এবং Category, Department ও Designation অনুযায়ী Pie Chart দেখা যায়।\n"
            "3. যেকোনো পাই চার্টের স্লাইস বা নামের ওপর ক্লিক করলে নিচে সেই গ্রুপের ফ্যাকাল্টি তালিকা খুলে যাবে।"
        ),
        "answer_admin": (
            "✅ **এই অপশনটি অ্যাপে রয়েছে!** **📊 Analytics** সেকশনে Status = OK ফ্যাকাল্টিদের KPI ও ইন্টারঅ্যাক্টিভ Pie Chart-এ ক্লিক করে ড্রিলডাউন তালিকা দেখা যায়।"
        ),
    },
    {
        "id": "password_users",
        "keywords": [
            "password", "change password", "user", "create user", "login", "log", "activity log", "পাসওয়ার্ড", "লগ",
        ],
        "title": "Password পরিবর্তন, User ও Activity Log",
        "answer_user": (
            "✅ **নিজের Password বদলানোর অপশন রয়েছে:**\n"
            "- বাম পাশের মেনু থেকে **🔐 Users & Logs** সেকশনে গিয়ে **Change My Password** ফর্মে বর্তমান ও নতুন পাসওয়ার্ড দিয়ে **Update Password** চাপুন।\n"
            "- (নতুন ইউজার তৈরি ও Activity Log দেখার সুবিধা শুধু **Admin**-এর জন্য সংরক্ষিত।)"
        ),
        "answer_admin": (
            "✅ **Admin হিসেবে আপনি সবগুলো অপশন পাবেন:**\n"
            "- **🔐 Users & Logs → 👥 Users & Password** ট্যাবে নতুন ইউজার তৈরি ও নিজের পাসওয়ার্ড পরিবর্তন করতে পারবেন।\n"
            "- **📜 Activity Log List** ট্যাবে কে কখন কী কাজ করেছেন তার সম্পূর্ণ লগ দেখতে পারবেন।"
        ),
    },
]


def evaluate_ai_question(user_question: str, is_admin: bool):
    q_clean = re.sub(r"\s+", " ", str(user_question or "").strip()).lower()
    if not q_clean:
        return False, "", ""

    best_entry = None
    best_score = 0
    for entry in AI_KNOWLEDGE_BASE:
        score = 0
        for kw in entry["keywords"]:
            if kw in q_clean:
                score += max(1, len(kw.split()))
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_entry is not None and best_score >= 1:
        ans = best_entry["answer_admin"] if is_admin else best_entry["answer_user"]
        return True, best_entry["title"], ans

    missing_msg = (
        "⚠️ **এই বিষয় বা অপশনটি বর্তমানে আমাদের অ্যাপ্লিকেশনে নেই।**\n\n"
        "আমি আপনার এই চাহিদাটি **Admin Notice** হিসেবে পাঠিয়ে দিচ্ছি, যাতে Admin প্রয়োজন অনুযায়ী অ্যাপে এই নতুন অপশনটি তৈরি করে দিতে পারেন।"
    )
    return False, "New Feature / Option Request", missing_msg


def parse_sheet_date(raw_val):
    s = str(raw_val).strip()
    if not s:
        return None
    date_part = s.split(" ")[0].strip()
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d %B %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue
    return None


def get_leave_recent_sort_key(row):
    from_dt = parse_sheet_date(row.get("From", ""))
    upto_dt = parse_sheet_date(row.get("Upto", ""))
    primary_dt = from_dt or upto_dt
    secondary_dt = upto_dt or from_dt
    has_date = 1 if (primary_dt is not None or secondary_dt is not None) else 0
    p_ord = primary_dt.toordinal() if primary_dt is not None else -1
    s_ord = secondary_dt.toordinal() if secondary_dt is not None else -1
    return (has_date, p_ord, s_ord, row.get("_sheet_row", 0))


def get_dnp_recent_sort_key(row):
    from_dt = parse_sheet_date(row.get("Do Not Punch From", ""))
    upto_dt = parse_sheet_date(row.get("Do Not Punch Upto", ""))
    notif_dt = parse_sheet_date(row.get("Notification Date", ""))
    primary_dt = from_dt or notif_dt or upto_dt
    secondary_dt = upto_dt or from_dt or notif_dt
    has_date = 1 if (primary_dt is not None or secondary_dt is not None) else 0
    p_ord = primary_dt.toordinal() if primary_dt is not None else -1
    s_ord = secondary_dt.toordinal() if secondary_dt is not None else -1
    return (has_date, p_ord, s_ord, row.get("_sheet_row", 0))


def get_next_sl_number(rows, sl_column="SL"):
    max_num = 0
    for r in rows:
        raw_sl = str(r.get(sl_column, "")).strip()
        if not raw_sl:
            continue
        match = re.search(r"(\d+)\s*$", raw_sl)
        if match:
            val = int(match.group(1))
            if val > max_num:
                max_num = val
    return str(max_num + 1) if max_num >= 0 else "1"


def sanitize_filename(text):
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(text).strip())
    return cleaned.strip("_") or "faculty"


def find_faculty_photo(emp_code, emp_name):
    candidates = []
    if str(emp_code).strip():
        candidates.append(sanitize_filename(emp_code))
    if str(emp_code).strip() and str(emp_name).strip():
        candidates.append(f"{sanitize_filename(emp_code)}_{sanitize_filename(emp_name)}")
    if str(emp_name).strip():
        candidates.append(sanitize_filename(emp_name))
    for base in candidates:
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            p = os.path.join(PHOTO_DIR, base + ext)
            if os.path.exists(p):
                return p
    return None


def save_faculty_photo(uploaded_file, emp_code, emp_name):
    _, ext = os.path.splitext(uploaded_file.name.lower())
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        ext = ".png"
    base = (
        f"{sanitize_filename(emp_code)}_{sanitize_filename(emp_name)}"
        if (str(emp_code).strip() and str(emp_name).strip())
        else sanitize_filename(emp_code or emp_name)
    )
    save_path = os.path.join(PHOTO_DIR, f"{base}{ext}")
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return save_path


def update_sheet_row(sheet_name, tab_name, headers, sheet_row, updated_data):
    client = get_gspread_client()
    sh = client.open(sheet_name)
    ws = sh.worksheet(tab_name)
    new_values = [str(updated_data.get(h, "")) for h in headers]
    end_col_letter = gspread.utils.rowcol_to_a1(1, len(headers)).replace("1", "")
    ws.update(f"A{sheet_row}:{end_col_letter}{sheet_row}", [new_values], value_input_option="USER_ENTERED")
    clear_sheet_cache()


def append_sheet_row(sheet_name, tab_name, headers, new_data):
    client = get_gspread_client()
    sh = client.open(sheet_name)
    ws = sh.worksheet(tab_name)
    new_values = [str(new_data.get(h, "")) for h in headers]
    ws.append_row(new_values, value_input_option="USER_ENTERED")
    clear_sheet_cache()


def delete_sheet_row(sheet_name, tab_name, sheet_row, actor_user=None):
    """Delete a row from Google Sheet (Admin only)."""
    if not actor_user or actor_user.get("role") != "admin":
        raise PermissionError("Only Admin users are allowed to delete records.")
    client = get_gspread_client()
    sh = client.open(sheet_name)
    ws = sh.worksheet(tab_name)
    ws.delete_rows(int(sheet_row))
    clear_sheet_cache()


def resolve_field_value(row_dict, target_header):
    if target_header in row_dict:
        return str(row_dict.get(target_header, "")).strip()
    norm_target = re.sub(r"[^a-z0-9]", "", target_header.lower())
    for k, v in row_dict.items():
        if k == "_sheet_row":
            continue
        if re.sub(r"[^a-z0-9]", "", str(k).lower()) == norm_target:
            return str(v).strip()
    return ""


def normalize_category_label(raw_cat):
    s = re.sub(r"\s+", " ", str(raw_cat or "").strip()).lower()
    s = s.replace("-", " ").replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def compute_ok_category_metrics(ok_rows):
    total_virtual = 0
    pure_inhouse = 0

    for r in ok_rows:
        cat_raw = resolve_field_value(r, "CATEGORY")
        cat_norm = normalize_category_label(cat_raw)
        if not cat_norm:
            continue

        is_pure_virtual = cat_norm in {"pure virtual", "purevirtual"}
        is_inhouse_virtual = cat_norm in {
            "inhouse virtual",
            "in house virtual",
            "inhousevirtual",
            "inhou virtual",
        }
        is_pure_inhouse = cat_norm in {
            "pure inhouse",
            "pure in house",
            "pureinhouse",
            "inhouse",
            "in house",
        } or ("inhouse" in cat_norm and "virtual" not in cat_norm)

        if is_pure_virtual or is_inhouse_virtual:
            total_virtual += 1
        elif is_pure_inhouse:
            pure_inhouse += 1

    return total_virtual, pure_inhouse


def render_html_table(rows, max_rows=500):
    if not rows:
        st.info("No records to display.")
        return

    clean_rows = [{k: v for k, v in r.items() if k != "_sheet_row"} for r in rows[:max_rows]]
    if len(rows) > max_rows:
        st.info(f"Showing first {max_rows} of {len(rows)} records.")

    cols = list(clean_rows[0].keys())
    th_html = "".join(
        f"<th style='position:sticky;top:0;z-index:2;text-align:left;padding:10px 14px;"
        f"border-bottom:1px solid rgba(148,163,184,0.22);background:#0f172a;color:#5eead4;"
        f"font-size:12.5px;font-weight:700;letter-spacing:0.3px;white-space:nowrap;'>{html.escape(str(c))}</th>"
        for c in cols
    )
    body_html_parts = []
    for idx_r, r in enumerate(clean_rows):
        row_bg = "rgba(15, 23, 42, 0.75)" if idx_r % 2 == 0 else "rgba(30, 41, 59, 0.45)"
        tds = "".join(
            f"<td style='padding:9px 14px;border-bottom:1px solid rgba(148,163,184,0.10);"
            f"color:#e2e8f0;white-space:nowrap;'>{html.escape(str(r.get(c, '')))}</td>"
            for c in cols
        )
        body_html_parts.append(f"<tr style='background:{row_bg};'>{tds}</tr>")

    table_html = (
        "<div style='overflow-x:auto;max-height:480px;overflow-y:auto;"
        "border:1px solid rgba(148,163,184,0.18);border-radius:12px;"
        "background:rgba(15,23,42,0.85);box-shadow:0 8px 20px -10px rgba(0,0,0,0.5);'>"
        "<table style='width:100%;border-collapse:collapse;font-size:13.5px;'>"
        f"<thead><tr>{th_html}</tr></thead>"
        f"<tbody>{''.join(body_html_parts)}</tbody>"
        "</table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def make_slice_url(field_name, label_val):
    qs = urllib.parse.urlencode({
        "slice": "Analytics Dashboard",
        "pie_field": field_name,
        "pie_val": label_val,
    })
    return f"?{qs}"


def build_pie_chart_html(title, rows, field_name, active_field="", active_val="", top_n=8):
    counts = {}
    for r in rows:
        raw_val = str(r.get(field_name, "")).strip()
        label = raw_val if raw_val else "(Blanks)"
        counts[label] = counts.get(label, 0) + 1

    total = sum(counts.values())
    if total == 0:
        return (
            "<div style='border:1px solid rgba(148,163,184,0.18);border-radius:14px;padding:18px;"
            "background:rgba(17,24,39,0.9);'>"
            f"<div style='font-weight:700;font-size:16px;color:#f8fafc;margin-bottom:8px;'>{html.escape(title)}</div>"
            "<div style='color:#94a3b8;font-size:14px;'>No data available.</div></div>"
        )

    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_items) > top_n:
        main_items = sorted_items[:top_n]
        other_count = sum(v for _, v in sorted_items[top_n:])
        if other_count > 0:
            main_items.append(("Others", other_count))
    else:
        main_items = sorted_items

    cx, cy, radius = 92, 92, 82
    slices_svg = []
    legend_html = []

    if len(main_items) == 1:
        lbl, cnt = main_items[0]
        color = CHART_COLORS[0]
        href = html.escape(make_slice_url(field_name, lbl))
        slices_svg.append(
            f"<a href='{href}' target='_self' style='cursor:pointer;'>"
            f"<circle cx='{cx}' cy='{cy}' r='{radius}' fill='{color}'>"
            f"<title>{html.escape(lbl)}: {cnt} (100.0%)</title></circle></a>"
        )
        is_selected = (active_field == field_name and active_val == lbl)
        row_bg = "background:rgba(20,184,166,0.18);border:1px solid rgba(20,184,166,0.4);border-radius:7px;padding:5px 8px;" if is_selected else "padding:5px 8px;border-radius:7px;"
        legend_html.append(
            f"<a href='{href}' target='_self' style='text-decoration:none;display:flex;align-items:center;"
            f"justify-content:space-between;gap:8px;margin-bottom:4px;font-size:13px;color:#f1f5f9;{row_bg}'>"
            f"<span style='display:flex;align-items:center;gap:8px;'>"
            f"<span style='display:inline-block;width:11px;height:11px;border-radius:3px;background:{color};flex-shrink:0;'></span>"
            f"<span>{html.escape(lbl)}</span></span>"
            f"<span style='color:#94a3b8;white-space:nowrap;font-weight:600;'>{cnt} (100.0%)</span></a>"
        )
    else:
        start_angle = -90.0
        for idx, (lbl, cnt) in enumerate(main_items):
            pct = (cnt / total) * 100.0
            sweep = (cnt / total) * 360.0
            end_angle = start_angle + sweep
            large_arc = 1 if sweep > 180.0 else 0

            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)

            x1 = cx + radius * math.cos(start_rad)
            y1 = cy + radius * math.sin(start_rad)
            x2 = cx + radius * math.cos(end_rad)
            y2 = cy + radius * math.sin(end_rad)

            color = CHART_COLORS[idx % len(CHART_COLORS)]
            href = html.escape(make_slice_url(field_name, lbl))
            path_d = (
                f"M {cx},{cy} L {x1:.2f},{y1:.2f} "
                f"A {radius},{radius} 0 {large_arc},1 {x2:.2f},{y2:.2f} Z"
            )
            slices_svg.append(
                f"<a href='{href}' target='_self' style='cursor:pointer;'>"
                f"<path d='{path_d}' fill='{color}' stroke='#111827' stroke-width='2'>"
                f"<title>{html.escape(lbl)}: {cnt} ({pct:.1f}%)</title></path></a>"
            )

            is_selected = (active_field == field_name and active_val == lbl)
            row_bg = "background:rgba(20,184,166,0.18);border:1px solid rgba(20,184,166,0.4);border-radius:7px;padding:5px 8px;" if is_selected else "padding:5px 8px;border-radius:7px;"
            legend_html.append(
                f"<a href='{href}' target='_self' style='text-decoration:none;display:flex;align-items:center;"
                f"justify-content:space-between;gap:8px;margin-bottom:4px;font-size:13px;color:#f1f5f9;{row_bg}'>"
                f"<span style='display:flex;align-items:center;gap:8px;overflow:hidden;text-overflow:ellipsis;'>"
                f"<span style='display:inline-block;width:11px;height:11px;border-radius:3px;background:{color};flex-shrink:0;'></span>"
                f"<span style='overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{html.escape(lbl)}</span></span>"
                f"<span style='color:#94a3b8;white-space:nowrap;font-weight:600;'>{cnt} ({pct:.1f}%)</span></a>"
            )
            start_angle = end_angle

    svg_block = (
        f"<svg width='184' height='184' viewBox='0 0 184 184' style='flex-shrink:0;'>"
        f"{''.join(slices_svg)}</svg>"
    )

    card_html = (
        "<div style='border:1px solid rgba(148,163,184,0.18);border-radius:14px;padding:18px;"
        "background:rgba(17,24,39,0.9);box-shadow:0 8px 22px -10px rgba(0,0,0,0.5);height:100%;'>"
        f"<div style='font-weight:700;font-size:16px;color:#f8fafc;margin-bottom:12px;'>{html.escape(title)}</div>"
        "<div style='display:flex;align-items:center;gap:18px;flex-wrap:wrap;'>"
        f"{svg_block}"
        f"<div style='flex:1;min-width:155px;max-height:196px;overflow-y:auto;'>{''.join(legend_html)}</div>"
        "</div></div>"
    )
    return card_html


def filter_rows_by_pie_selection(rows, field_name, selected_label):
    if not field_name or not selected_label:
        return []
    matched = []
    for r in rows:
        raw_val = str(r.get(field_name, "")).strip()
        norm_val = raw_val if raw_val else "(Blanks)"
        if norm_val == selected_label:
            matched.append(r)
    return matched


def find_option_index(options, current_val):
    curr = str(current_val).strip()
    if not curr:
        return None
    for i, opt in enumerate(options):
        if opt.lower() == curr.lower():
            return i
    return None


def build_leave_suggestions(leave_rows, today_date):
    by_faculty = {}
    for r in leave_rows:
        code = str(r.get("EMP_Code", "")).strip()
        name = str(r.get("Emp_Name", r.get("EMP_Name", ""))).strip()
        sl_val = str(r.get("SL", "")).strip()
        key = code if code else name
        if not key:
            continue

        upto_dt = parse_sheet_date(r.get("Upto", ""))
        from_dt = parse_sheet_date(r.get("From", ""))

        if key not in by_faculty:
            by_faculty[key] = {
                "EMP_Code": code,
                "Emp_Name": name,
                "Emp_Designation": str(r.get("Emp_Designation", "")).strip(),
                "Emp_Department": str(r.get("Emp_Department", "")).strip(),
                "SL": sl_val,
                "Total_Leave_Entries": 0,
                "Latest_Upto_Date": None,
                "Latest_From_Date": None,
                "Last_Leave_Type": str(r.get("Leave_types", "")).strip(),
                "Last_Applying_Status": str(r.get("Applying_Stutas.", r.get("Applying_Status", ""))).strip(),
                "Take_Action_By": str(r.get("Take_Action_By", "")).strip(),
                "Sample_Row": r,
            }

        entry = by_faculty[key]
        entry["Total_Leave_Entries"] += 1
        if not entry["Emp_Name"] and name:
            entry["Emp_Name"] = name
        if not entry["Emp_Designation"] and str(r.get("Emp_Designation", "")).strip():
            entry["Emp_Designation"] = str(r.get("Emp_Designation", "")).strip()
        if not entry["Emp_Department"] and str(r.get("Emp_Department", "")).strip():
            entry["Emp_Department"] = str(r.get("Emp_Department", "")).strip()
        if not entry["SL"] and sl_val:
            entry["SL"] = sl_val

        if upto_dt is not None:
            if entry["Latest_Upto_Date"] is None or upto_dt > entry["Latest_Upto_Date"]:
                entry["Latest_Upto_Date"] = upto_dt
                entry["Latest_From_Date"] = from_dt
                entry["Last_Leave_Type"] = str(r.get("Leave_types", "")).strip()
                entry["Last_Applying_Status"] = str(r.get("Applying_Stutas.", r.get("Applying_Status", ""))).strip()
                if str(r.get("Take_Action_By", "")).strip():
                    entry["Take_Action_By"] = str(r.get("Take_Action_By", "")).strip()
                entry["Sample_Row"] = r

    suggestions = []
    for uid, item in by_faculty.items():
        latest_upto = item["Latest_Upto_Date"]
        if latest_upto is not None:
            days_diff = (today_date - latest_upto).days
            latest_upto_str = latest_upto.strftime("%Y-%m-%d")
        else:
            days_diff = 999999
            latest_upto_str = "No Date"

        suggestions.append({
            "_uid": uid,
            "EMP_Code": item["EMP_Code"],
            "Emp_Name": item["Emp_Name"],
            "Emp_Designation": item["Emp_Designation"],
            "Emp_Department": item["Emp_Department"],
            "SL": item["SL"],
            "Latest_Upto": latest_upto_str,
            "Days_Since_Last_Upto": days_diff if latest_upto is not None else "N/A",
            "Total_Leave_Entries": item["Total_Leave_Entries"],
            "Last_Leave_Type": item["Last_Leave_Type"],
            "Last_Applying_Status": item["Last_Applying_Status"],
            "Take_Action_By": item["Take_Action_By"],
            "Sample_Row": item["Sample_Row"],
            "_sort_days": days_diff,
        })

    suggestions.sort(key=lambda x: x["_sort_days"], reverse=True)
    for rank, s in enumerate(suggestions, start=1):
        s["Priority_Rank"] = rank

    return suggestions


# ================= ENSURE SYSTEM SHEETS & LOAD USERS =================
try:
    ensure_system_tabs(SPREADSHEET_NAME)
    sheet_users_db = load_users_from_sheet(SPREADSHEET_NAME)
except Exception as e:
    st.error(f"Failed to connect or initialize system tabs in Google Sheet: {e}")
    st.stop()

if not sheet_users_db:
    sheet_users_db = dict(DEFAULT_USERS)

if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None

# ================= LOGIN SCREEN =================
if st.session_state["logged_in_user"] is None:
    st.markdown(
        "<div class='page-banner'>"
        "<div class='page-banner-title'>🔐 TIMESH Login</div>"
        "<div class='page-banner-meta'>Sign in to access Faculty, Leave & Do Not Punch management</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    _, login_col, _ = st.columns([1, 1.4, 1])
    with login_col:
        st.markdown("<div class='form-panel'><div class='section-tag'>User Authentication</div>", unsafe_allow_html=True)
        with st.form("timesh_login_form"):
            login_username = st.text_input("Username", placeholder="Enter username").strip().lower()
            login_password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

        if submitted:
            u_rec = sheet_users_db.get(login_username)
            if u_rec and verify_password(login_password, u_rec["password_hash"]):
                logged_user_obj = {
                    "username": login_username,
                    "name": u_rec["name"],
                    "role": u_rec["role"],
                }
                st.session_state["logged_in_user"] = logged_user_obj
                write_activity_log(
                    SPREADSHEET_NAME,
                    logged_user_obj,
                    action="Login",
                    module="Authentication",
                    details=f"User '{login_username}' signed in successfully.",
                )
                st.success(f"Welcome, {u_rec['name']}!")
                st.rerun()
            else:
                write_activity_log(
                    SPREADSHEET_NAME,
                    {"username": login_username or "guest", "name": "Unknown", "role": "guest"},
                    action="Failed Login",
                    module="Authentication",
                    details=f"Failed login attempt for username '{login_username}'.",
                )
                st.error("Invalid username or password.")

        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

current_user = st.session_state["logged_in_user"]
is_admin_user = current_user.get("role") == "admin"


# ================= AI "ASK ME" POP-UP DIALOG =================
@st.dialog("🤖 TIMESH AI Assistant — Ask Me", width="large")
def open_ask_me_dialog():
    if "ai_last_question" not in st.session_state:
        st.session_state["ai_last_question"] = ""
    if "ai_last_found" not in st.session_state:
        st.session_state["ai_last_found"] = None
    if "ai_last_title" not in st.session_state:
        st.session_state["ai_last_title"] = ""
    if "ai_last_answer" not in st.session_state:
        st.session_state["ai_last_answer"] = ""
    if "ai_notice_sent_for" not in st.session_state:
        st.session_state["ai_notice_sent_for"] = ""

    st.markdown(
        "<div class='muted-sub' style='margin-bottom:8px;'>"
        "অ্যাপটি কীভাবে ব্যবহার করবেন (যেমন: Leave Apply, Edit, Delete, Do Not Punch, Faculty Add, Password) তা জিজ্ঞেস করুন। "
        "যদি কোনো অপশন অ্যাপে না থাকে, তবে Admin-এর কাছে স্বয়ংক্রিয়ভাবে নোটিশ চলে যাবে।"
        "</div>",
        unsafe_allow_html=True,
    )

    q_cols = st.columns(3)
    quick_questions = [
        "Leave apply korbo kivabe?",
        "Record edit korbo kivabe?",
        "Record delete korbo kivabe?",
    ]
    for idx_q, qq in enumerate(quick_questions):
        with q_cols[idx_q]:
            if st.button(qq, key=f"quick_ai_q_{idx_q}", use_container_width=True):
                found, title, ans = evaluate_ai_question(qq, is_admin_user)
                st.session_state["ai_last_question"] = qq
                st.session_state["ai_last_found"] = found
                st.session_state["ai_last_title"] = title
                st.session_state["ai_last_answer"] = ans

    with st.form("ai_ask_me_form", clear_on_submit=False):
        user_q_input = st.text_input(
            "আপনার প্রশ্ন লিখুন",
            value=st.session_state.get("ai_last_question", ""),
            placeholder="যেমন: Leave কীভাবে দেব? বা নতুন কোনো ফিচার চাইলে লিখুন...",
        ).strip()
        ask_btn = st.form_submit_button("Ask AI", type="primary", use_container_width=True)

    if ask_btn and user_q_input:
        found, title, ans = evaluate_ai_question(user_q_input, is_admin_user)
        st.session_state["ai_last_question"] = user_q_input
        st.session_state["ai_last_found"] = found
        st.session_state["ai_last_title"] = title
        st.session_state["ai_last_answer"] = ans

        if not found and st.session_state.get("ai_notice_sent_for") != user_q_input:
            try:
                send_feature_notice_to_admin(SPREADSHEET_NAME, current_user, user_q_input)
                write_activity_log(
                    SPREADSHEET_NAME,
                    current_user,
                    action="AI Feature Notice",
                    module="AI Assistant",
                    details=f"Requested unavailable option: '{user_q_input}'",
                )
                st.session_state["ai_notice_sent_for"] = user_q_input
            except Exception as e:
                st.error(f"Notice পাঠাতে সমস্যা হয়েছে: {e}")

    if st.session_state.get("ai_last_answer"):
        if st.session_state.get("ai_last_found"):
            st.markdown(
                f"<div class='ai-reply-box'>"
                f"<div style='font-weight:700;color:#5eead4;margin-bottom:6px;'>💡 {html.escape(st.session_state['ai_last_title'])}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown(st.session_state["ai_last_answer"])
        else:
            st.markdown(
                "<div class='ai-missing-box'>"
                "<div style='font-weight:700;color:#fcd34d;margin-bottom:4px;'>🔔 Admin Notice পাঠানো হয়েছে</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(st.session_state["ai_last_answer"])
            if st.session_state.get("ai_notice_sent_for") == st.session_state.get("ai_last_question"):
                st.success(
                    f"আপনার অনুরোধটি ('{st.session_state['ai_last_question']}') Admin-এর কাছে নোটিশ হিসেবে পাঠানো হয়েছে। Admin চাইলে এই অপশনটি তৈরি করে দেবেন।"
                )


# Load pending admin notices count if admin
pending_notices_list = []
if is_admin_user:
    try:
        _, req_rows_all = load_worksheet_rows_with_index(SPREADSHEET_NAME, REQUESTS_TAB_NAME)
        pending_notices_list = [
            r for r in req_rows_all
            if str(r.get("Status", "")).strip().lower() == "pending"
        ]
    except Exception:
        pending_notices_list = []

q_params = st.query_params
qp_slice = str(q_params.get("slice", "")).strip()
qp_field = str(q_params.get("pie_field", "")).strip()
qp_val = str(q_params.get("pie_val", "")).strip()

valid_nav_keys = [item["key"] for item in NAV_ITEMS]
if "active_nav_slice" not in st.session_state:
    st.session_state["active_nav_slice"] = qp_slice if qp_slice in valid_nav_keys else "Analytics Dashboard"
elif qp_slice in valid_nav_keys and qp_slice != st.session_state.get("_last_qp_slice"):
    st.session_state["active_nav_slice"] = qp_slice
st.session_state["_last_qp_slice"] = qp_slice

try:
    all_tabs = get_all_tab_names(SPREADSHEET_NAME)
except Exception as e:
    st.error(f"Failed to connect to Google Sheet: {e}")
    st.stop()

faculty_tab_candidates = ["Sheet1", "Sheet 1", "Main Faculty List", "FACULTY CORNER", "Faculty Corner", "FACULTY_CORNER", "Faculty"]
faculty_tab = next((t for t in faculty_tab_candidates if t in all_tabs), None)
if faculty_tab is None and all_tabs:
    faculty_tab = all_tabs[0]

leave_tab_candidates = ["Sheet3", "Sheet 3", "Leave", "Leaves", "Faculty Leave", "FACULTY_LEAVE"]
leave_tab = next((t for t in leave_tab_candidates if t in all_tabs), None)
if leave_tab is None and len(all_tabs) >= 3:
    leave_tab = all_tabs[2]
elif leave_tab is None and all_tabs:
    leave_tab = all_tabs[-1]

dnp_tab_candidates = ["Don Not Punch", "Do Not Punch", "DON NOT PUNCH", "DO NOT PUNCH", "Do_Not_Punch", "Don_Not_Punch"]
dnp_tab = next((t for t in dnp_tab_candidates if t in all_tabs), None)

# ================= SIDEBAR NAVIGATION =================
with st.sidebar:
    st.markdown(
        "<div class='sidebar-brand'>"
        "<div class='sidebar-brand-title'>🎓 TIMESH</div>"
        "<div class='sidebar-brand-sub'>Faculty & Leave Management Suite</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    if st.button("💬 Ask Me (AI Help)", key="sidebar_ask_me_btn", type="primary", use_container_width=True):
        open_ask_me_dialog()

    if is_admin_user and len(pending_notices_list) > 0:
        if st.button(
            f"🔔 Admin Notices ({len(pending_notices_list)} New)",
            key="sidebar_admin_notice_btn",
            use_container_width=True,
        ):
            st.session_state["active_nav_slice"] = "Users"
            st.rerun()

    st.markdown("<div class='nav-section-label'>Navigation</div>", unsafe_allow_html=True)

    for nav in NAV_ITEMS:
        is_curr = st.session_state["active_nav_slice"] == nav["key"]
        nav_title = nav["title"]
        if nav["key"] == "Users" and not is_admin_user:
            nav_title = "Security"
        btn_label = f"{nav['icon']}  {nav_title}"
        if st.button(
            btn_label,
            key=f"nav_btn_{nav['key']}",
            type="primary" if is_curr else "secondary",
            use_container_width=True,
        ):
            st.session_state["active_nav_slice"] = nav["key"]
            st.rerun()

    st.markdown(
        f"<div class='sidebar-info-box'>"
        f"<div class='sidebar-info-row'><span>User</span><span class='sidebar-info-val'>{html.escape(str(current_user.get('name', '-')))}</span></div>"
        f"<div class='sidebar-info-row'><span>Role</span><span class='sidebar-info-val'>{html.escape(str(current_user.get('role', '-')).upper())}</span></div>"
        f"<div class='sidebar-info-row'><span>Sheet</span><span class='sidebar-info-val'>{html.escape(SPREADSHEET_NAME)}</span></div>"
        f"<div class='sidebar-info-row'><span>Faculty Tab</span><span class='sidebar-info-val'>{html.escape(str(faculty_tab or '-'))}</span></div>"
        f"<div class='sidebar-info-row'><span>Leave Tab</span><span class='sidebar-info-val'>{html.escape(str(leave_tab or '-'))}</span></div>"
        f"<div class='sidebar-info-row'><span>DNP Tab</span><span class='sidebar-info-val'>{html.escape(str(dnp_tab or 'Don Not Punch'))}</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button("🔄 Refresh Sheet Data", key="sidebar_refresh_btn", use_container_width=True):
        clear_sheet_cache()
        st.rerun()
    if st.button("🚪 Logout", key="sidebar_logout_btn", use_container_width=True):
        write_activity_log(
            SPREADSHEET_NAME,
            current_user,
            action="Logout",
            module="Authentication",
            details=f"User '{current_user.get('username', '')}' logged out.",
        )
        st.session_state["logged_in_user"] = None
        st.rerun()

# Top right floating-style quick Ask Me trigger bar
top_spacer, top_ai_col = st.columns([5.2, 1.3])
with top_ai_col:
    if st.button("💬 Ask Me", key="top_ask_me_btn", type="primary", use_container_width=True):
        open_ask_me_dialog()

slice_choice = st.session_state["active_nav_slice"]


# ================= SLICE 1: ANALYTICS PIE DASHBOARD =================
if slice_choice == "Analytics Dashboard":
    render_banner(
        "Analytics Dashboard",
        f"Active Filter: <b>Status = OK</b>  |  Spreadsheet: <b>{html.escape(SPREADSHEET_NAME)}</b>  |  Tab: <b>{html.escape(str(faculty_tab))}</b>",
    )

    if not faculty_tab:
        st.warning("No worksheet tab found.")
        st.stop()

    try:
        headers, all_rows = load_worksheet_rows_with_index(SPREADSHEET_NAME, faculty_tab)
    except Exception as e:
        st.error(f"Failed to load sheet rows: {e}")
        st.stop()

    ok_rows = [
        r for r in all_rows
        if str(r.get("Status", "")).strip().lower() == "ok"
    ]

    total_virtual_ok, pure_inhouse_ok = compute_ok_category_metrics(ok_rows)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Active Faculty (Status: OK)", len(ok_rows))
    with m2:
        st.metric("Total_Virtual", total_virtual_ok)
    with m3:
        st.metric("Pure_Inhouse", pure_inhouse_ok)

    st.write("")

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        st.markdown(
            build_pie_chart_html("Category Distribution", ok_rows, "CATEGORY", qp_field, qp_val),
            unsafe_allow_html=True,
        )
    with row1_col2:
        st.markdown(
            build_pie_chart_html("Department Distribution", ok_rows, "Emp_Department", qp_field, qp_val),
            unsafe_allow_html=True,
        )

    st.write("")

    row2_col1, _ = st.columns([1, 1])
    with row2_col1:
        st.markdown(
            build_pie_chart_html("Designation Distribution", ok_rows, "Emp_Designation", qp_field, qp_val),
            unsafe_allow_html=True,
        )

    valid_pie_fields = {"CATEGORY": "Category", "Emp_Department": "Department", "Emp_Designation": "Designation"}
    if qp_field in valid_pie_fields and qp_val:
        st.divider()
        field_title = valid_pie_fields[qp_field]
        drill_rows = filter_rows_by_pie_selection(ok_rows, qp_field, qp_val)
        hdr_c1, hdr_c2 = st.columns([4, 1])
        with hdr_c1:
            st.subheader(f"Filtered Records — {field_title}: {qp_val} ({len(drill_rows)})")
        with hdr_c2:
            if st.button("Clear Selection", use_container_width=True):
                st.query_params.clear()
                st.rerun()
        render_html_table(drill_rows, max_rows=500)


# ================= SLICE 2: FACULTY_CORNER =================
elif slice_choice == "FACULTY_CORNER":
    render_banner(
        "FACULTY_CORNER",
        f"Spreadsheet: <b>{html.escape(SPREADSHEET_NAME)}</b>  |  Tab: <b>{html.escape(str(faculty_tab))}</b>",
    )
    if not faculty_tab:
        st.warning("No worksheet tab found.")
        st.stop()
    try:
        headers, all_rows = load_worksheet_rows_with_index(SPREADSHEET_NAME, faculty_tab)
    except Exception as e:
        st.error(f"Failed to load sheet rows: {e}")
        st.stop()

    faculty_rows = all_rows

    tab_view, tab_edit, tab_add, tab_photo = st.tabs([
        "📋 View Faculty",
        "✏️ Edit Faculty",
        "➕ Add New Faculty",
        "🖼️ Upload Photo",
    ])

    with tab_view:
        st.markdown("<div class='form-panel'><div class='section-tag'>Search & Filter</div>", unsafe_allow_html=True)
        r1_c1, r1_c2 = st.columns([2, 1])
        with r1_c1:
            search_code_name = st.text_input(
                "Search by EMP_Code or Name",
                "",
                placeholder="Type EMP_Code or faculty name...",
                key="view_search_code_name",
            ).strip().lower()
        with r1_c2:
            search_sl = st.text_input(
                "Search by SL",
                "",
                placeholder="Type SL number...",
                key="view_search_sl",
            ).strip().lower()

        depts = sorted({str(r.get("Emp_Department", "")).strip() for r in faculty_rows if str(r.get("Emp_Department", "")).strip()})
        categories = sorted({str(r.get("CATEGORY", "")).strip() for r in faculty_rows if str(r.get("CATEGORY", "")).strip()})

        r2_c1, r2_c2, r2_c3 = st.columns(3)
        with r2_c1:
            sel_dept = st.selectbox("Department", ["All"] + depts, key="view_dept")
        with r2_c2:
            sel_status = st.selectbox(
                "Status",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index("OK"),
                key="view_status",
            )
        with r2_c3:
            sel_categories = st.multiselect(
                "Category (Multiple)",
                categories,
                default=[],
                placeholder="All Categories",
                key="view_categories",
            )
        st.markdown("</div>", unsafe_allow_html=True)

        selected_cat_set = {c.strip() for c in sel_categories}

        filtered_rows = []
        for r in faculty_rows:
            if sel_dept != "All" and str(r.get("Emp_Department", "")).strip() != sel_dept:
                continue
            row_status = str(r.get("Status", "")).strip()
            if sel_status == "(Blanks)":
                if row_status != "":
                    continue
            elif sel_status != "All":
                if row_status.lower() != sel_status.lower():
                    continue
            if selected_cat_set and str(r.get("CATEGORY", "")).strip() not in selected_cat_set:
                continue
            if search_code_name:
                code_name_hay = " ".join([
                    str(r.get("EMP_Code", "")),
                    str(r.get("EMP_Name", "")),
                ]).lower()
                if search_code_name not in code_name_hay:
                    continue
            if search_sl:
                sl_val = str(r.get("SL", "")).strip().lower()
                if search_sl not in sl_val:
                    continue
            filtered_rows.append(r)

        st.metric("Total Faculty Shown", len(filtered_rows))

        if filtered_rows:
            st.markdown("<div class='form-panel'><div class='section-tag'>Faculty Spotlight</div>", unsafe_allow_html=True)
            profile_options = {
                f"{r.get('EMP_Code', '')} — {r.get('EMP_Name', '')} (SL: {r.get('SL', '')})": r
                for r in filtered_rows[:200]
            }
            chosen_label = st.selectbox("Select Faculty for Profile", list(profile_options.keys()))
            chosen_row = profile_options[chosen_label]
            p1, p2 = st.columns([1, 3.5])
            with p1:
                photo_path = find_faculty_photo(chosen_row.get("EMP_Code", ""), chosen_row.get("EMP_Name", ""))
                if photo_path:
                    st.image(photo_path, caption=str(chosen_row.get("EMP_Name", "")), width=175)
                else:
                    st.info("No photo uploaded yet.")
            with p2:
                render_html_table([{k: v for k, v in chosen_row.items() if k != "_sheet_row"}], max_rows=1)
            st.markdown("</div>", unsafe_allow_html=True)

        st.subheader("Faculty Directory")
        render_html_table(filtered_rows, max_rows=100)

    with tab_edit:
        st.subheader("Edit Existing Faculty")
        if faculty_rows:
            ec1, ec2 = st.columns([2, 1])
            with ec1:
                edit_search_code_name = st.text_input(
                    "Search by EMP_Code or Name",
                    "",
                    key="edit_search_code_name",
                ).strip().lower()
            with ec2:
                edit_search_sl = st.text_input(
                    "Search by SL",
                    "",
                    key="edit_search_sl",
                ).strip().lower()

            matched_edit_rows = []
            for r in faculty_rows:
                if edit_search_code_name:
                    cn_hay = " ".join([
                        str(r.get("EMP_Code", "")),
                        str(r.get("EMP_Name", "")),
                    ]).lower()
                    if edit_search_code_name not in cn_hay:
                        continue
                if edit_search_sl:
                    sl_hay = str(r.get("SL", "")).strip().lower()
                    if edit_search_sl not in sl_hay:
                        continue
                matched_edit_rows.append(r)

            if not matched_edit_rows:
                st.warning("No matching faculty found for the search criteria.")
            else:
                edit_map = {
                    f"[Row {r['_sheet_row']}] {r.get('EMP_Code', '')} — {r.get('EMP_Name', '')} (SL: {r.get('SL', '')})": r
                    for r in matched_edit_rows
                }
                selected_edit_key = st.selectbox("Select Faculty to Edit", list(edit_map.keys()))
                target_row = edit_map[selected_edit_key]
                row_id = target_row["_sheet_row"]

                existing_col_options = {}
                for h in headers:
                    if h.upper() == "STATUS":
                        opts = list(dict.fromkeys(FORM_STATUS_OPTIONS + [
                            str(r.get(h, "")).strip() for r in all_rows if str(r.get(h, "")).strip()
                        ]))
                    else:
                        opts = sorted({
                            str(r.get(h, "")).strip()
                            for r in all_rows
                            if str(r.get(h, "")).strip()
                        })
                    existing_col_options[h] = opts

                st.markdown("<div class='form-panel'><div class='section-tag'>Frozen Identifiers</div>", unsafe_allow_html=True)
                frozen_cols = {"EMP_Code", "EMP_Name", "SL"}
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    st.text_input(
                        "EMP_Code (Frozen)",
                        value=str(target_row.get("EMP_Code", "")),
                        disabled=True,
                        key=f"edit_frozen_code_{row_id}",
                    )
                with fc2:
                    st.text_input(
                        "EMP_Name (Frozen)",
                        value=str(target_row.get("EMP_Name", "")),
                        disabled=True,
                        key=f"edit_frozen_name_{row_id}",
                    )
                with fc3:
                    st.text_input(
                        "SL (Frozen)",
                        value=str(target_row.get("SL", "")),
                        disabled=True,
                        key=f"edit_frozen_sl_{row_id}",
                    )
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div class='form-panel'><div class='section-tag'>Editable Fields</div>", unsafe_allow_html=True)
                editable_headers = [h for h in headers if h not in frozen_cols]
                updated_other_values = {}
                cols = st.columns(2)

                for i, h in enumerate(editable_headers):
                    with cols[i % 2]:
                        curr_val = str(target_row.get(h, "")).strip()
                        opts = existing_col_options.get(h, [])
                        if curr_val and curr_val not in opts:
                            opts = [curr_val] + opts

                        if not opts:
                            updated_other_values[h] = st.text_input(
                                h,
                                value=curr_val,
                                key=f"edit_text_{row_id}_{h}",
                            )
                        else:
                            dropdown_choices = list(opts) + ["+ Custom / New Value"]
                            def_idx = dropdown_choices.index(curr_val) if curr_val in dropdown_choices else 0
                            picked = st.selectbox(
                                h,
                                dropdown_choices,
                                index=def_idx,
                                key=f"edit_dd_{row_id}_{h}",
                            )
                            if picked == "+ Custom / New Value":
                                updated_other_values[h] = st.text_input(
                                    f"Custom {h}",
                                    value=curr_val,
                                    key=f"edit_custom_{row_id}_{h}",
                                )
                            else:
                                updated_other_values[h] = picked

                st.write("")
                if st.button("Save Changes", type="primary"):
                    final_updated = {}
                    for h in headers:
                        if h in frozen_cols:
                            final_updated[h] = str(target_row.get(h, ""))
                        else:
                            final_updated[h] = str(updated_other_values.get(h, "")).strip()
                    try:
                        update_sheet_row(SPREADSHEET_NAME, faculty_tab, headers, row_id, final_updated)
                        write_activity_log(
                            SPREADSHEET_NAME,
                            current_user,
                            action="Edit Faculty",
                            module="FACULTY_CORNER",
                            details=(
                                f"Updated row {row_id} — EMP_Code: {target_row.get('EMP_Code', '')}, "
                                f"EMP_Name: {target_row.get('EMP_Name', '')}"
                            ),
                        )
                        st.success("Faculty details updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")
                st.markdown("</div>", unsafe_allow_html=True)

    with tab_add:
        st.subheader("Add New Faculty")
        next_sl_suggested = get_next_sl_number(all_rows, "SL")

        existing_col_options = {}
        for h in headers:
            if h.upper() == "STATUS":
                opts = list(dict.fromkeys(FORM_STATUS_OPTIONS + [
                    str(r.get(h, "")).strip() for r in all_rows if str(r.get(h, "")).strip()
                ]))
            else:
                opts = sorted({
                    str(r.get(h, "")).strip()
                    for r in all_rows
                    if str(r.get(h, "")).strip()
                })
            existing_col_options[h] = opts

        st.markdown("<div class='form-panel'><div class='section-tag'>Basic Details</div>", unsafe_allow_html=True)
        top_c1, top_c2, top_c3 = st.columns(3)
        with top_c1:
            emp_code_input = st.text_input("EMP_Code", "", key="add_emp_code")
        with top_c2:
            emp_name_input = st.text_input("EMP_Name", "", key="add_emp_name")
        with top_c3:
            sl_input = st.text_input("SL (Auto Next)", value=next_sl_suggested, key="add_sl_auto")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='form-panel'><div class='section-tag'>Role & Profile</div>", unsafe_allow_html=True)
        other_headers = [
            h for h in headers
            if h not in {"EMP_Code", "EMP_Name", "SL"}
        ]
        selected_other_values = {}
        cols = st.columns(2)

        for idx, h in enumerate(other_headers):
            with cols[idx % 2]:
                opts = existing_col_options.get(h, [])
                dropdown_choices = list(opts) + ["+ Custom / New Value"]

                default_idx = 0
                if h.upper() == "CATEGORY" and "Faculty" in opts:
                    default_idx = opts.index("Faculty")
                elif h.upper() == "STATUS" and "OK" in opts:
                    default_idx = opts.index("OK")

                if not opts:
                    selected_other_values[h] = st.text_input(h, value="", key=f"add_text_{h}")
                else:
                    picked = st.selectbox(
                        h,
                        dropdown_choices,
                        index=default_idx,
                        key=f"add_dd_{h}",
                    )
                    if picked == "+ Custom / New Value":
                        selected_other_values[h] = st.text_input(
                            f"Custom {h}",
                            value="",
                            key=f"add_custom_{h}",
                        )
                    else:
                        selected_other_values[h] = picked

        new_photo = st.file_uploader(
            "Upload Photo (Optional)",
            type=["png", "jpg", "jpeg", "webp"],
            key="add_photo",
        )

        if st.button("Add Faculty", type="primary"):
            new_row_dict = {}
            for h in headers:
                if h == "EMP_Code":
                    new_row_dict[h] = emp_code_input.strip()
                elif h == "EMP_Name":
                    new_row_dict[h] = emp_name_input.strip()
                elif h == "SL":
                    new_row_dict[h] = sl_input.strip()
                else:
                    new_row_dict[h] = str(selected_other_values.get(h, "")).strip()

            try:
                append_sheet_row(SPREADSHEET_NAME, faculty_tab, headers, new_row_dict)
                if new_photo is not None:
                    save_faculty_photo(
                        new_photo,
                        new_row_dict.get("EMP_Code", ""),
                        new_row_dict.get("EMP_Name", ""),
                    )
                write_activity_log(
                    SPREADSHEET_NAME,
                    current_user,
                    action="Add Faculty",
                    module="FACULTY_CORNER",
                    details=(
                        f"Added faculty — EMP_Code: {new_row_dict.get('EMP_Code', '')}, "
                        f"EMP_Name: {new_row_dict.get('EMP_Name', '')}, SL: {new_row_dict.get('SL', '')}"
                    ),
                )
                st.success(f"New faculty added (SL: {new_row_dict.get('SL', '')})!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to add faculty: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_photo:
        st.markdown("<div class='form-panel'><div class='section-tag'>Faculty Photo Manager</div>", unsafe_allow_html=True)
        if faculty_rows:
            photo_target_map = {
                f"{r.get('EMP_Code', '')} — {r.get('EMP_Name', '')}": r
                for r in faculty_rows
            }
            chosen_photo_key = st.selectbox("Select Faculty", list(photo_target_map.keys()), key="photo_sel")
            p_row = photo_target_map[chosen_photo_key]
            emp_code_val = str(p_row.get("EMP_Code", "")).strip()
            emp_name_val = str(p_row.get("EMP_Name", "")).strip()
            existing_photo = find_faculty_photo(emp_code_val, emp_name_val)
            if existing_photo:
                st.image(existing_photo, caption="Current Photo", width=180)
            uploaded_img = st.file_uploader("Choose Photo", type=["png", "jpg", "jpeg", "webp"], key="photo_up")
            if st.button("Save Photo"):
                if uploaded_img is None:
                    st.warning("Please choose a photo first.")
                else:
                    saved_path = save_faculty_photo(uploaded_img, emp_code_val, emp_name_val)
                    write_activity_log(
                        SPREADSHEET_NAME,
                        current_user,
                        action="Upload Photo",
                        module="FACULTY_CORNER",
                        details=f"Uploaded photo for {emp_name_val} ({emp_code_val}) -> {saved_path}",
                    )
                    st.success(f"Photo saved to: {saved_path}")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ================= SLICE 3: LEAVE MANAGEMENT =================
elif slice_choice == "Leave":
    render_banner(
        "Leave Management",
        f"Spreadsheet: <b>{html.escape(SPREADSHEET_NAME)}</b>  |  Leave Tab: <b>{html.escape(str(leave_tab))}</b>",
    )

    if not leave_tab:
        st.warning("No leave worksheet tab found.")
        st.stop()

    try:
        leave_headers, leave_rows = load_worksheet_rows_with_index(SPREADSHEET_NAME, leave_tab)
    except Exception as e:
        st.error(f"Failed to load leave sheet rows: {e}")
        st.stop()

    if "active_leave_add_uid" not in st.session_state:
        st.session_state["active_leave_add_uid"] = None
    if "editing_leave_sheet_row" not in st.session_state:
        st.session_state["editing_leave_sheet_row"] = None
    if "confirm_delete_leave_row" not in st.session_state:
        st.session_state["confirm_delete_leave_row"] = None

    if not is_admin_user:
        st.session_state["confirm_delete_leave_row"] = None

    today_val = date.today()
    tab_upcoming, tab_suggest, tab_all_records = st.tabs([
        "📅 Upcoming Leave",
        "💡 Leave Suggest",
        "🗂️ All Leave Records",
    ])

    with tab_upcoming:
        st.subheader(f"Upcoming Leave (Upto ≥ {today_val.strftime('%Y-%m-%d')})")

        uc1, uc2, uc3 = st.columns([2, 1, 1])
        with uc1:
            leave_search = st.text_input(
                "Search by EMP_Code, Name, or SL",
                "",
                placeholder="Search faculty...",
                key="leave_upcoming_search",
            ).strip().lower()
        leave_depts = sorted({
            str(r.get("Emp_Department", "")).strip()
            for r in leave_rows
            if str(r.get("Emp_Department", "")).strip()
        })
        with uc2:
            sel_leave_dept = st.selectbox("Department", ["All"] + leave_depts, key="leave_upcoming_dept")
        with uc3:
            st.metric("Today's Date", today_val.strftime("%Y-%m-%d"))

        upcoming_rows = []
        for r in leave_rows:
            upto_dt = parse_sheet_date(r.get("Upto", ""))
            if upto_dt is None or upto_dt < today_val:
                continue
            if sel_leave_dept != "All" and str(r.get("Emp_Department", "")).strip() != sel_leave_dept:
                continue
            if leave_search:
                hay = " ".join([
                    str(r.get("EMP_Code", "")),
                    str(r.get("Emp_Name", r.get("EMP_Name", ""))),
                    str(r.get("SL", "")),
                ]).lower()
                if leave_search not in hay:
                    continue
            upcoming_rows.append(r)

        upcoming_rows.sort(key=lambda row: parse_sheet_date(row.get("Upto", "")) or date.max)
        st.metric("Total Upcoming Leave Records", len(upcoming_rows))
        render_html_table(upcoming_rows, max_rows=300)

    with tab_suggest:
        st.subheader("Leave Suggest (Longest Days Since Latest Upto)")

        sc1, sc2 = st.columns([2, 1])
        with sc1:
            suggest_search = st.text_input(
                "Search by EMP_Code, Name, or SL",
                "",
                placeholder="Search faculty...",
                key="leave_suggest_search",
            ).strip().lower()
        suggest_depts = sorted({
            str(r.get("Emp_Department", "")).strip()
            for r in leave_rows
            if str(r.get("Emp_Department", "")).strip()
        })
        with sc2:
            sel_suggest_dept = st.selectbox("Department", ["All"] + suggest_depts, key="leave_suggest_dept")

        filtered_source_rows = []
        for r in leave_rows:
            if sel_suggest_dept != "All" and str(r.get("Emp_Department", "")).strip() != sel_suggest_dept:
                continue
            if suggest_search:
                hay = " ".join([
                    str(r.get("EMP_Code", "")),
                    str(r.get("Emp_Name", r.get("EMP_Name", ""))),
                    str(r.get("SL", "")),
                ]).lower()
                if suggest_search not in hay:
                    continue
            filtered_source_rows.append(r)

        suggestion_list = build_leave_suggestions(filtered_source_rows, today_val)
        st.metric("Total Faculty Evaluated", len(suggestion_list))

        selected_uid = st.session_state.get("active_leave_add_uid")
        selected_person = next((s for s in suggestion_list if s["_uid"] == selected_uid), None)

        if selected_person is not None:
            sample = selected_person.get("Sample_Row", {})
            next_leave_sl = get_next_sl_number(leave_rows, "SL")

            st.markdown(
                f"<div class='form-panel'>"
                f"<div class='section-tag'>Add Leave Entry</div>"
                f"<div style='font-size:18px;font-weight:700;color:#f8fafc;margin-bottom:12px;'>"
                f"{html.escape(selected_person['Emp_Name'])} <span class='muted-sub'>({html.escape(selected_person['EMP_Code'])})</span></div>"
                f"<div class='muted-sub' style='margin-bottom:10px;'>Frozen Faculty Details</div>",
                unsafe_allow_html=True,
            )
            f_c1, f_c2, f_c3 = st.columns(3)
            with f_c1:
                st.text_input(
                    "Emp_Name (Frozen)",
                    value=selected_person["Emp_Name"],
                    disabled=True,
                    key=f"lv_f_name_{selected_uid}",
                )
            with f_c2:
                st.text_input(
                    "EMP_Code (Frozen)",
                    value=selected_person["EMP_Code"],
                    disabled=True,
                    key=f"lv_f_code_{selected_uid}",
                )
            with f_c3:
                st.text_input(
                    "SL (Frozen)",
                    value=next_leave_sl,
                    disabled=True,
                    key=f"lv_f_sl_{selected_uid}",
                )

            f_c4, f_c5 = st.columns(2)
            with f_c4:
                st.text_input(
                    "Emp_Designation (Frozen)",
                    value=selected_person["Emp_Designation"],
                    disabled=True,
                    key=f"lv_f_desig_{selected_uid}",
                )
            with f_c5:
                st.text_input(
                    "Emp_Department (Frozen)",
                    value=selected_person["Emp_Department"],
                    disabled=True,
                    key=f"lv_f_dept_{selected_uid}",
                )

            st.markdown("<div class='muted-sub' style='margin:14px 0 8px 0;'>Editable Leave Details</div>", unsafe_allow_html=True)
            d_c1, d_c2 = st.columns(2)
            with d_c1:
                from_date_val = st.date_input(
                    "From",
                    value=today_val,
                    key=f"lv_edit_from_{selected_uid}",
                )
            with d_c2:
                upto_date_val = st.date_input(
                    "Upto",
                    value=today_val,
                    key=f"lv_edit_upto_{selected_uid}",
                )

            e_c1, e_c2, e_c3 = st.columns(3)
            with e_c1:
                leave_type_val = st.selectbox(
                    "Leave_types",
                    LEAVE_TYPE_OPTIONS,
                    index=None,
                    placeholder="Select Leave Type",
                    key=f"lv_edit_type_{selected_uid}",
                )
            with e_c2:
                applying_status_val = st.selectbox(
                    "Applying_Stutas.",
                    APPLYING_STATUS_OPTIONS,
                    index=None,
                    placeholder="Select Status (YES / NO)",
                    key=f"lv_edit_status_{selected_uid}",
                )
            with e_c3:
                take_action_by_val = st.selectbox(
                    "Take_Action_By",
                    TAKE_ACTION_BY_OPTIONS,
                    index=None,
                    placeholder="Select Action By",
                    key=f"lv_edit_action_{selected_uid}",
                )

            frozen_leave_cols = {
                "", "EMP_Code", "Emp_Name", "EMP_Name", "Emp_Designation", "Emp_Department", "SL"
            }
            known_editable_cols = {
                "From", "Upto", "Leave_types", "Applying_Stutas.", "Applying_Status", "Take_Action_By"
            }
            extra_editable_headers = [
                h for h in leave_headers
                if h.strip() and h.strip() not in frozen_leave_cols and h.strip() not in known_editable_cols
            ]
            extra_values = {}
            if extra_editable_headers:
                ex_cols = st.columns(2)
                for idx_ex, eh in enumerate(extra_editable_headers):
                    with ex_cols[idx_ex % 2]:
                        extra_values[eh] = st.text_input(
                            eh,
                            value=str(sample.get(eh, "")),
                            key=f"lv_extra_{selected_uid}_{eh}",
                        )

            st.write("")
            b_c1, b_c2 = st.columns([1.2, 4])
            with b_c1:
                if st.button("Save Leave", type="primary", key=f"lv_save_btn_{selected_uid}", use_container_width=True):
                    if upto_date_val < from_date_val:
                        st.error("Upto date cannot be earlier than From date.")
                    else:
                        new_leave_record = {}
                        for h in leave_headers:
                            h_clean = h.strip()
                            if not h_clean:
                                continue
                            if h_clean == "EMP_Code":
                                new_leave_record[h] = selected_person["EMP_Code"]
                            elif h_clean in {"Emp_Name", "EMP_Name"}:
                                new_leave_record[h] = selected_person["Emp_Name"]
                            elif h_clean == "Emp_Designation":
                                new_leave_record[h] = selected_person["Emp_Designation"]
                            elif h_clean == "Emp_Department":
                                new_leave_record[h] = selected_person["Emp_Department"]
                            elif h_clean == "SL":
                                new_leave_record[h] = next_leave_sl
                            elif h_clean == "From":
                                new_leave_record[h] = from_date_val.strftime("%Y-%m-%d")
                            elif h_clean == "Upto":
                                new_leave_record[h] = upto_date_val.strftime("%Y-%m-%d")
                            elif h_clean == "Leave_types":
                                new_leave_record[h] = str(leave_type_val or "").strip()
                            elif h_clean in {"Applying_Stutas.", "Applying_Status"}:
                                new_leave_record[h] = str(applying_status_val or "").strip()
                            elif h_clean == "Take_Action_By":
                                new_leave_record[h] = str(take_action_by_val or "").strip()
                            else:
                                new_leave_record[h] = str(extra_values.get(h, sample.get(h, ""))).strip()

                        try:
                            append_sheet_row(SPREADSHEET_NAME, leave_tab, leave_headers, new_leave_record)
                            write_activity_log(
                                SPREADSHEET_NAME,
                                current_user,
                                action="Add Leave",
                                module="Leave",
                                details=(
                                    f"Added {new_leave_record.get('Leave_types', '') or 'Leave'} for "
                                    f"{selected_person['Emp_Name']} ({selected_person['EMP_Code']}) "
                                    f"from {from_date_val.strftime('%Y-%m-%d')} to {upto_date_val.strftime('%Y-%m-%d')}"
                                ),
                            )
                            st.session_state["active_leave_add_uid"] = None
                            st.success(
                                f"Leave added for {selected_person['Emp_Name']} "
                                f"({new_leave_record.get('Leave_types', '') or 'N/A'}, "
                                f"{from_date_val.strftime('%Y-%m-%d')} to {upto_date_val.strftime('%Y-%m-%d')})."
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to add leave: {e}")
            with b_c2:
                if st.button("Cancel", key=f"lv_cancel_btn_{selected_uid}"):
                    st.session_state["active_leave_add_uid"] = None
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        if not suggestion_list:
            st.info("No leave records found.")
        else:
            st.markdown("<div class='form-panel'><div class='section-tag'>Priority Queue</div>", unsafe_allow_html=True)
            for item in suggestion_list[:150]:
                c_rank, c_code, c_name, c_dept, c_upto, c_days, c_btn = st.columns([0.65, 1.15, 2.1, 1.5, 1.35, 1.2, 0.85])
                with c_rank:
                    st.markdown(f"<span style='color:#5eead4;font-weight:700;'>#{item['Priority_Rank']}</span>", unsafe_allow_html=True)
                with c_code:
                    st.markdown(f"<span class='muted-sub'>{html.escape(item['EMP_Code'] or '-')}</span>", unsafe_allow_html=True)
                with c_name:
                    st.markdown(f"<div style='font-weight:600;color:#f8fafc;'>{html.escape(item['Emp_Name'] or '-')}</div>", unsafe_allow_html=True)
                with c_dept:
                    st.markdown(f"<span class='muted-sub'>{html.escape(item['Emp_Department'] or '-')}</span>", unsafe_allow_html=True)
                with c_upto:
                    st.markdown(f"<span class='muted-sub'>Upto: {html.escape(item['Latest_Upto'])}</span>", unsafe_allow_html=True)
                with c_days:
                    st.markdown(f"<span class='days-pill'>{html.escape(str(item['Days_Since_Last_Upto']))} days</span>", unsafe_allow_html=True)
                with c_btn:
                    if st.button("Add", key=f"btn_add_leave_{item['_uid']}", use_container_width=True):
                        st.session_state["active_leave_add_uid"] = item["_uid"]
                        st.rerun()
                st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid rgba(148,163,184,0.10);'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with tab_all_records:
        st.subheader("All Leave Records")

        ac1, ac2, ac3 = st.columns([2, 1, 1])
        with ac1:
            all_lv_search = st.text_input(
                "Search by EMP_Code, Name, or SL",
                "",
                placeholder="Search faculty...",
                key="all_leave_search_in_leave",
            ).strip().lower()
        all_lv_depts = sorted({
            str(r.get("Emp_Department", "")).strip()
            for r in leave_rows
            if str(r.get("Emp_Department", "")).strip()
        })
        with ac2:
            sel_all_lv_dept = st.selectbox("Department", ["All"] + all_lv_depts, key="all_leave_dept_in_leave")

        all_lv_types = sorted({
            str(r.get("Leave_types", "")).strip()
            for r in leave_rows
            if str(r.get("Leave_types", "")).strip()
        })
        with ac3:
            sel_all_lv_type = st.selectbox("Leave Type", ["All"] + all_lv_types, key="all_leave_type_in_leave")

        filtered_all_leaves = []
        for r in leave_rows:
            if sel_all_lv_dept != "All" and str(r.get("Emp_Department", "")).strip() != sel_all_lv_dept:
                continue
            if sel_all_lv_type != "All" and str(r.get("Leave_types", "")).strip() != sel_all_lv_type:
                continue
            if all_lv_search:
                hay = " ".join([
                    str(r.get("EMP_Code", "")),
                    str(r.get("Emp_Name", r.get("EMP_Name", ""))),
                    str(r.get("SL", "")),
                ]).lower()
                if all_lv_search not in hay:
                    continue
            filtered_all_leaves.append(r)

        filtered_all_leaves.sort(key=get_leave_recent_sort_key, reverse=True)
        st.metric("Total Leave Records Shown", len(filtered_all_leaves))

        editing_row_num = st.session_state.get("editing_leave_sheet_row")
        row_to_edit = next(
            (r for r in leave_rows if r.get("_sheet_row") == editing_row_num),
            None,
        )
        if row_to_edit is not None:
            edit_name = str(row_to_edit.get("Emp_Name", row_to_edit.get("EMP_Name", ""))).strip()
            edit_code = str(row_to_edit.get("EMP_Code", "")).strip()
            st.markdown(
                f"<div class='form-panel'>"
                f"<div class='section-tag'>Edit Leave Record</div>"
                f"<div style='font-size:18px;font-weight:700;color:#f8fafc;margin-bottom:10px;'>"
                f"{html.escape(edit_name)} <span class='muted-sub'>({html.escape(edit_code)} · Row {editing_row_num})</span></div>"
                f"<div class='muted-sub' style='margin-bottom:8px;'>Frozen Faculty Details</div>",
                unsafe_allow_html=True,
            )

            ef1, ef2, ef3 = st.columns(3)
            with ef1:
                st.text_input(
                    "Emp_Name (Frozen)",
                    value=edit_name,
                    disabled=True,
                    key=f"ed_lv_f_name_{editing_row_num}",
                )
            with ef2:
                st.text_input(
                    "EMP_Code (Frozen)",
                    value=edit_code,
                    disabled=True,
                    key=f"ed_lv_f_code_{editing_row_num}",
                )
            with ef3:
                st.text_input(
                    "SL (Frozen)",
                    value=str(row_to_edit.get("SL", "")).strip(),
                    disabled=True,
                    key=f"ed_lv_f_sl_{editing_row_num}",
                )

            ef4, ef5 = st.columns(2)
            with ef4:
                st.text_input(
                    "Emp_Designation (Frozen)",
                    value=str(row_to_edit.get("Emp_Designation", "")).strip(),
                    disabled=True,
                    key=f"ed_lv_f_desig_{editing_row_num}",
                )
            with ef5:
                st.text_input(
                    "Emp_Department (Frozen)",
                    value=str(row_to_edit.get("Emp_Department", "")).strip(),
                    disabled=True,
                    key=f"ed_lv_f_dept_{editing_row_num}",
                )

            st.markdown("<div class='muted-sub' style='margin:12px 0 8px 0;'>Editable Leave Details</div>", unsafe_allow_html=True)
            parsed_from = parse_sheet_date(row_to_edit.get("From", "")) or today_val
            parsed_upto = parse_sheet_date(row_to_edit.get("Upto", "")) or parsed_from

            ed_d1, ed_d2 = st.columns(2)
            with ed_d1:
                ed_from_val = st.date_input(
                    "From",
                    value=parsed_from,
                    key=f"ed_lv_from_{editing_row_num}",
                )
            with ed_d2:
                ed_upto_val = st.date_input(
                    "Upto",
                    value=parsed_upto,
                    key=f"ed_lv_upto_{editing_row_num}",
                )

            curr_ltype = str(row_to_edit.get("Leave_types", "")).strip()
            curr_astatus = str(row_to_edit.get("Applying_Stutas.", row_to_edit.get("Applying_Status", ""))).strip()
            curr_action = str(row_to_edit.get("Take_Action_By", "")).strip()

            ltype_opts = list(dict.fromkeys(LEAVE_TYPE_OPTIONS + ([curr_ltype] if curr_ltype else [])))
            astatus_opts = list(dict.fromkeys(APPLYING_STATUS_OPTIONS + ([curr_astatus] if curr_astatus else [])))
            action_opts = list(dict.fromkeys(TAKE_ACTION_BY_OPTIONS + ([curr_action] if curr_action else [])))

            ed_e1, ed_e2, ed_e3 = st.columns(3)
            with ed_e1:
                ed_ltype_val = st.selectbox(
                    "Leave_types",
                    ltype_opts,
                    index=find_option_index(ltype_opts, curr_ltype),
                    placeholder="Select Leave Type",
                    key=f"ed_lv_type_{editing_row_num}",
                )
            with ed_e2:
                ed_astatus_val = st.selectbox(
                    "Applying_Stutas.",
                    astatus_opts,
                    index=find_option_index(astatus_opts, curr_astatus),
                    placeholder="Select Status (YES / NO)",
                    key=f"ed_lv_status_{editing_row_num}",
                )
            with ed_e3:
                ed_action_val = st.selectbox(
                    "Take_Action_By",
                    action_opts,
                    index=find_option_index(action_opts, curr_action),
                    placeholder="Select Action By",
                    key=f"ed_lv_action_{editing_row_num}",
                )

            frozen_leave_cols = {
                "", "EMP_Code", "Emp_Name", "EMP_Name", "Emp_Designation", "Emp_Department", "SL"
            }
            known_editable_cols = {
                "From", "Upto", "Leave_types", "Applying_Stutas.", "Applying_Status", "Take_Action_By"
            }
            extra_edit_headers = [
                h for h in leave_headers
                if h.strip() and h.strip() not in frozen_leave_cols and h.strip() not in known_editable_cols
            ]
            extra_edit_vals = {}
            if extra_edit_headers:
                ex_e_cols = st.columns(2)
                for idx_ex, eh in enumerate(extra_edit_headers):
                    with ex_e_cols[idx_ex % 2]:
                        extra_edit_vals[eh] = st.text_input(
                            eh,
                            value=str(row_to_edit.get(eh, "")),
                            key=f"ed_lv_extra_{editing_row_num}_{eh}",
                        )

            st.write("")
            eb1, eb2 = st.columns([1.2, 4])
            with eb1:
                if st.button("Update Leave", type="primary", key=f"ed_lv_save_{editing_row_num}", use_container_width=True):
                    if ed_upto_val < ed_from_val:
                        st.error("Upto date cannot be earlier than From date.")
                    else:
                        updated_rec = {}
                        for h in leave_headers:
                            h_clean = h.strip()
                            if not h_clean:
                                continue
                            if h_clean in frozen_leave_cols:
                                updated_rec[h] = str(row_to_edit.get(h, ""))
                            elif h_clean == "From":
                                updated_rec[h] = ed_from_val.strftime("%Y-%m-%d")
                            elif h_clean == "Upto":
                                updated_rec[h] = ed_upto_val.strftime("%Y-%m-%d")
                            elif h_clean == "Leave_types":
                                updated_rec[h] = str(ed_ltype_val or "").strip()
                            elif h_clean in {"Applying_Stutas.", "Applying_Status"}:
                                updated_rec[h] = str(ed_astatus_val or "").strip()
                            elif h_clean == "Take_Action_By":
                                updated_rec[h] = str(ed_action_val or "").strip()
                            else:
                                updated_rec[h] = str(extra_edit_vals.get(h, row_to_edit.get(h, ""))).strip()
                        try:
                            update_sheet_row(
                                SPREADSHEET_NAME,
                                leave_tab,
                                leave_headers,
                                editing_row_num,
                                updated_rec,
                            )
                            write_activity_log(
                                SPREADSHEET_NAME,
                                current_user,
                                action="Edit Leave",
                                module="Leave",
                                details=(
                                    f"Updated row {editing_row_num} for {edit_name} ({edit_code}) "
                                    f"-> {ed_from_val.strftime('%Y-%m-%d')} to {ed_upto_val.strftime('%Y-%m-%d')}"
                                ),
                            )
                            st.session_state["editing_leave_sheet_row"] = None
                            st.success(f"Leave record updated for {edit_name}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update leave: {e}")
            with eb2:
                if st.button("Cancel Edit", key=f"ed_lv_cancel_{editing_row_num}"):
                    st.session_state["editing_leave_sheet_row"] = None
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        del_row_num = st.session_state.get("confirm_delete_leave_row")
        row_to_del = next(
            (r for r in leave_rows if r.get("_sheet_row") == del_row_num),
            None,
        )
        if row_to_del is not None and is_admin_user:
            del_name = str(row_to_del.get("Emp_Name", row_to_del.get("EMP_Name", ""))).strip()
            del_code = str(row_to_del.get("EMP_Code", "")).strip()
            del_from = str(row_to_del.get("From", "")).strip()
            del_upto = str(row_to_del.get("Upto", "")).strip()
            st.warning(
                f"Are you sure you want to delete leave for **{del_name}** ({del_code}) "
                f"from **{del_from}** to **{del_upto}** [Sheet Row {del_row_num}]?"
            )
            dc1, dc2, _ = st.columns([1.4, 1.2, 4])
            with dc1:
                if st.button("Confirm Delete", type="primary", key=f"conf_del_lv_{del_row_num}"):
                    try:
                        delete_sheet_row(SPREADSHEET_NAME, leave_tab, del_row_num, actor_user=current_user)
                        write_activity_log(
                            SPREADSHEET_NAME,
                            current_user,
                            action="Delete Leave",
                            module="Leave",
                            details=f"Deleted row {del_row_num} for {del_name} ({del_code}) [{del_from} -> {del_upto}]",
                        )
                        st.session_state["confirm_delete_leave_row"] = None
                        if st.session_state.get("editing_leave_sheet_row") == del_row_num:
                            st.session_state["editing_leave_sheet_row"] = None
                        st.success("Leave record deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete leave: {e}")
            with dc2:
                if st.button("Keep Record", key=f"keep_del_lv_{del_row_num}"):
                    st.session_state["confirm_delete_leave_row"] = None
                    st.rerun()

        if not filtered_all_leaves:
            st.info("No leave records match your filter.")
        else:
            if len(filtered_all_leaves) > 150:
                st.info(f"Showing first 150 of {len(filtered_all_leaves)} records.")
            st.markdown("<div class='form-panel'><div class='section-tag'>Leave Ledger</div>", unsafe_allow_html=True)
            for rec in filtered_all_leaves[:150]:
                r_num = rec["_sheet_row"]
                r_code = str(rec.get("EMP_Code", "")).strip() or "-"
                r_name = str(rec.get("Emp_Name", rec.get("EMP_Name", ""))).strip() or "-"
                r_dept = str(rec.get("Emp_Department", "")).strip() or "-"
                r_from = str(rec.get("From", "")).strip() or "-"
                r_upto = str(rec.get("Upto", "")).strip() or "-"
                r_ltype = str(rec.get("Leave_types", "")).strip() or "-"

                if is_admin_user:
                    c1, c2, c3, c4, c5, c_edit, c_del = st.columns([1.05, 2.0, 1.5, 1.65, 0.85, 0.78, 0.85])
                else:
                    c1, c2, c3, c4, c5, c_edit = st.columns([1.15, 2.2, 1.6, 1.85, 0.9, 0.85])

                with c1:
                    st.markdown(f"<span class='muted-sub'>{html.escape(r_code)}</span>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"<div style='font-weight:600;color:#f8fafc;'>{html.escape(r_name)}</div>", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"<span class='muted-sub'>{html.escape(r_dept)}</span>", unsafe_allow_html=True)
                with c4:
                    st.markdown(f"<span style='font-size:13px;color:#e2e8f0;'>{html.escape(r_from)} → {html.escape(r_upto)}</span>", unsafe_allow_html=True)
                with c5:
                    st.markdown(f"<span class='leave-badge'>{html.escape(r_ltype)}</span>", unsafe_allow_html=True)
                with c_edit:
                    if st.button("Edit", key=f"btn_edit_lv_{r_num}", use_container_width=True):
                        st.session_state["editing_leave_sheet_row"] = r_num
                        st.session_state["confirm_delete_leave_row"] = None
                        st.rerun()
                if is_admin_user:
                    with c_del:
                        if st.button("Delete", key=f"btn_del_lv_{r_num}", use_container_width=True):
                            st.session_state["confirm_delete_leave_row"] = r_num
                            st.rerun()
                st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid rgba(148,163,184,0.10);'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


# ================= SLICE 4: DO NOT PUNCH =================
elif slice_choice == "Do Not Punch":
    target_dnp_tab = dnp_tab or "Don Not Punch"
    render_banner(
        "Do Not Punch",
        f"Source Faculty Tab: <b>{html.escape(str(faculty_tab))}</b>  |  Save To Tab: <b>{html.escape(str(target_dnp_tab))}</b>",
    )

    if not faculty_tab:
        st.warning("No faculty source worksheet tab found.")
        st.stop()

    try:
        _, source_faculty_rows = load_worksheet_rows_with_index(SPREADSHEET_NAME, faculty_tab)
    except Exception as e:
        st.error(f"Failed to load faculty source rows: {e}")
        st.stop()

    try:
        dnp_headers, dnp_rows = load_worksheet_rows_with_index(SPREADSHEET_NAME, target_dnp_tab)
    except Exception as e:
        st.error(f"Failed to load '{target_dnp_tab}' worksheet: {e}")
        st.stop()

    if "editing_dnp_sheet_row" not in st.session_state:
        st.session_state["editing_dnp_sheet_row"] = None
    if "confirm_delete_dnp_row" not in st.session_state:
        st.session_state["confirm_delete_dnp_row"] = None

    if not is_admin_user:
        st.session_state["confirm_delete_dnp_row"] = None

    today_val = date.today()
    tab_dnp_add, tab_dnp_records = st.tabs([
        "➕ Add",
        "📄 Do Not Punch Record",
    ])

    with tab_dnp_add:
        st.subheader("Add Do Not Punch (From Faculty Sheet)")
        st.markdown("<div class='form-panel'><div class='section-tag'>Search Faculty (Sheet1)</div>", unsafe_allow_html=True)

        sb1, sb2, sb3 = st.columns(3)
        with sb1:
            dnp_q_name = st.text_input(
                "Search Name",
                "",
                placeholder="Type faculty name...",
                key="dnp_search_name",
            ).strip().lower()
        with sb2:
            dnp_q_code = st.text_input(
                "Search EMP Code",
                "",
                placeholder="Type EMP_Code...",
                key="dnp_search_code",
            ).strip().lower()
        with sb3:
            dnp_q_sl = st.text_input(
                "Search SL",
                "",
                placeholder="Type SL...",
                key="dnp_search_sl",
            ).strip().lower()

        matched_faculties = []
        for fr in source_faculty_rows:
            f_code = resolve_field_value(fr, "EMP_Code")
            f_name = resolve_field_value(fr, "EMP_Name") or resolve_field_value(fr, "Emp_Name")
            f_sl = resolve_field_value(fr, "SL")

            if dnp_q_name and dnp_q_name not in f_name.lower():
                continue
            if dnp_q_code and dnp_q_code not in f_code.lower():
                continue
            if dnp_q_sl and dnp_q_sl not in f_sl.lower():
                continue
            matched_faculties.append(fr)

        if not matched_faculties:
            st.warning("No matching faculty found in Sheet1 for your search.")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            fac_choice_map = {}
            for fr in matched_faculties[:200]:
                c_val = resolve_field_value(fr, "EMP_Code")
                n_val = resolve_field_value(fr, "EMP_Name") or resolve_field_value(fr, "Emp_Name")
                s_val = resolve_field_value(fr, "SL")
                d_val = resolve_field_value(fr, "Emp_Department")
                lbl = f"{n_val or '-'}  |  EMP_Code: {c_val or '-'}  |  SL: {s_val or '-'}  ({d_val or '-'})"
                fac_choice_map[lbl] = fr

            selected_fac_lbl = st.selectbox(
                "Select Matched Faculty",
                list(fac_choice_map.keys()),
                key="dnp_selected_faculty_box",
            )
            chosen_fac = fac_choice_map[selected_fac_lbl]

            fac_emp_code = resolve_field_value(chosen_fac, "EMP_Code")
            fac_emp_name = resolve_field_value(chosen_fac, "EMP_Name") or resolve_field_value(chosen_fac, "Emp_Name")
            fac_desig = resolve_field_value(chosen_fac, "Emp_Designation")
            fac_dept = resolve_field_value(chosen_fac, "Emp_Department")
            fac_sl = resolve_field_value(chosen_fac, "SL")
            fac_status = resolve_field_value(chosen_fac, "Status")
            fac_category = resolve_field_value(chosen_fac, "CATEGORY")

            st.markdown("<div class='muted-sub' style='margin:12px 0 8px 0;'>Faculty Details (Auto-filled from Sheet1)</div>", unsafe_allow_html=True)
            fd1, fd2, fd3 = st.columns(3)
            with fd1:
                st.text_input("EMP_Code", value=fac_emp_code, disabled=True, key="dnp_auto_code")
            with fd2:
                st.text_input("EMP_Name", value=fac_emp_name, disabled=True, key="dnp_auto_name")
            with fd3:
                st.text_input("SL", value=fac_sl, disabled=True, key="dnp_auto_sl")

            fd4, fd5, fd6, fd7 = st.columns(4)
            with fd4:
                st.text_input("Emp_Designation", value=fac_desig, disabled=True, key="dnp_auto_desig")
            with fd5:
                st.text_input("Emp_Department", value=fac_dept, disabled=True, key="dnp_auto_dept")
            with fd6:
                st.text_input("Status", value=fac_status, disabled=True, key="dnp_auto_status")
            with fd7:
                st.text_input("CATEGORY", value=fac_category, disabled=True, key="dnp_auto_cat")

            st.markdown("<div class='muted-sub' style='margin:16px 0 8px 0;'>Do Not Punch Details (Save to 'Don Not Punch')</div>", unsafe_allow_html=True)
            dt1, dt2 = st.columns(2)
            with dt1:
                dnp_from_date = st.date_input("Do Not Punch From", value=today_val, key="dnp_from_input")
            with dt2:
                dnp_upto_date = st.date_input("Do Not Punch Upto", value=today_val, key="dnp_upto_input")

            nf1, nf2 = st.columns(2)
            with nf1:
                dnp_notif_date = st.date_input("Notification Date", value=today_val, key="dnp_notif_date_input")
            with nf2:
                dnp_issue_by = st.text_input(
                    "Notification issue By",
                    value=current_user.get("name", ""),
                    placeholder="Enter issuer name...",
                    key="dnp_issue_by_input",
                ).strip()

            st.write("")
            if st.button("Save Do Not Punch", type="primary", key="dnp_save_btn"):
                if dnp_upto_date < dnp_from_date:
                    st.error("Do Not Punch Upto date cannot be earlier than Do Not Punch From date.")
                else:
                    field_map = {
                        "empcode": fac_emp_code,
                        "empname": fac_emp_name,
                        "empdesignation": fac_desig,
                        "empdepartment": fac_dept,
                        "sl": fac_sl,
                        "status": fac_status,
                        "category": fac_category,
                        "donotpunchfrom": dnp_from_date.strftime("%Y-%m-%d"),
                        "donotpunchupto": dnp_upto_date.strftime("%Y-%m-%d"),
                        "notificationdate": dnp_notif_date.strftime("%Y-%m-%d"),
                        "notificationissueby": dnp_issue_by,
                    }
                    new_dnp_row = {}
                    for h in dnp_headers:
                        h_clean = h.strip()
                        if not h_clean:
                            continue
                        norm_h = re.sub(r"[^a-z0-9]", "", h_clean.lower())
                        new_dnp_row[h] = field_map.get(norm_h, "")

                    try:
                        append_sheet_row(SPREADSHEET_NAME, target_dnp_tab, dnp_headers, new_dnp_row)
                        write_activity_log(
                            SPREADSHEET_NAME,
                            current_user,
                            action="Add Do Not Punch",
                            module="Do Not Punch",
                            details=(
                                f"Added DNP for {fac_emp_name} ({fac_emp_code}) "
                                f"from {dnp_from_date.strftime('%Y-%m-%d')} to {dnp_upto_date.strftime('%Y-%m-%d')}"
                            ),
                        )
                        st.success(
                            f"Saved to '{target_dnp_tab}' for {fac_emp_name} "
                            f"({dnp_from_date.strftime('%Y-%m-%d')} to {dnp_upto_date.strftime('%Y-%m-%d')})."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save Do Not Punch record: {e}")

            st.markdown("</div>", unsafe_allow_html=True)

    with tab_dnp_records:
        st.subheader(f"Do Not Punch Record ({target_dnp_tab})")

        rc1, rc2, rc3 = st.columns([2, 1, 1])
        with rc1:
            dnp_rec_search = st.text_input(
                "Search by EMP_Code, Name, or SL",
                "",
                placeholder="Search records...",
                key="dnp_rec_search_box",
            ).strip().lower()
        dnp_depts = sorted({
            resolve_field_value(r, "Emp_Department")
            for r in dnp_rows
            if resolve_field_value(r, "Emp_Department")
        })
        with rc2:
            dnp_sel_dept = st.selectbox("Department", ["All"] + dnp_depts, key="dnp_rec_dept_box")
        with rc3:
            st.metric("Total DNP Records", len(dnp_rows))

        filtered_dnp = []
        for r in dnp_rows:
            r_code = resolve_field_value(r, "EMP_Code")
            r_name = resolve_field_value(r, "EMP_Name") or resolve_field_value(r, "Emp_Name")
            r_sl = resolve_field_value(r, "SL")
            r_dept = resolve_field_value(r, "Emp_Department")

            if dnp_sel_dept != "All" and r_dept != dnp_sel_dept:
                continue
            if dnp_rec_search:
                hay = f"{r_code} {r_name} {r_sl}".lower()
                if dnp_rec_search not in hay:
                    continue
            filtered_dnp.append(r)

        filtered_dnp.sort(key=get_dnp_recent_sort_key, reverse=True)

        ed_dnp_row_num = st.session_state.get("editing_dnp_sheet_row")
        dnp_row_to_edit = next(
            (r for r in dnp_rows if r.get("_sheet_row") == ed_dnp_row_num),
            None,
        )
        if dnp_row_to_edit is not None:
            ed_n = resolve_field_value(dnp_row_to_edit, "EMP_Name") or resolve_field_value(dnp_row_to_edit, "Emp_Name")
            ed_c = resolve_field_value(dnp_row_to_edit, "EMP_Code")
            st.markdown(
                f"<div class='form-panel'>"
                f"<div class='section-tag'>Edit Do Not Punch Record</div>"
                f"<div style='font-size:18px;font-weight:700;color:#f8fafc;margin-bottom:10px;'>"
                f"{html.escape(ed_n)} <span class='muted-sub'>({html.escape(ed_c)} · Row {ed_dnp_row_num})</span></div>",
                unsafe_allow_html=True,
            )

            parsed_dnp_from = parse_sheet_date(resolve_field_value(dnp_row_to_edit, "Do Not Punch From")) or today_val
            parsed_dnp_upto = parse_sheet_date(resolve_field_value(dnp_row_to_edit, "Do Not Punch Upto")) or parsed_dnp_from
            parsed_notif_dt = parse_sheet_date(resolve_field_value(dnp_row_to_edit, "Notification Date")) or today_val
            curr_issuer = resolve_field_value(dnp_row_to_edit, "Notification issue By")

            e_dc1, e_dc2 = st.columns(2)
            with e_dc1:
                ed_dnp_from = st.date_input("Do Not Punch From", value=parsed_dnp_from, key=f"ed_dnp_from_{ed_dnp_row_num}")
            with e_dc2:
                ed_dnp_upto = st.date_input("Do Not Punch Upto", value=parsed_dnp_upto, key=f"ed_dnp_upto_{ed_dnp_row_num}")

            e_nc1, e_nc2 = st.columns(2)
            with e_nc1:
                ed_notif_dt = st.date_input("Notification Date", value=parsed_notif_dt, key=f"ed_dnp_ndt_{ed_dnp_row_num}")
            with e_nc2:
                ed_issuer = st.text_input("Notification issue By", value=curr_issuer, key=f"ed_dnp_iss_{ed_dnp_row_num}").strip()

            st.write("")
            eb_a, eb_b = st.columns([1.2, 4])
            with eb_a:
                if st.button("Update Record", type="primary", key=f"ed_dnp_save_{ed_dnp_row_num}", use_container_width=True):
                    if ed_dnp_upto < ed_dnp_from:
                        st.error("Do Not Punch Upto date cannot be earlier than Do Not Punch From date.")
                    else:
                        upd_map = {
                            "donotpunchfrom": ed_dnp_from.strftime("%Y-%m-%d"),
                            "donotpunchupto": ed_dnp_upto.strftime("%Y-%m-%d"),
                            "notificationdate": ed_notif_dt.strftime("%Y-%m-%d"),
                            "notificationissueby": ed_issuer,
                        }
                        updated_dnp_rec = {}
                        for h in dnp_headers:
                            h_clean = h.strip()
                            if not h_clean:
                                continue
                            norm_h = re.sub(r"[^a-z0-9]", "", h_clean.lower())
                            if norm_h in upd_map:
                                updated_dnp_rec[h] = upd_map[norm_h]
                            else:
                                updated_dnp_rec[h] = str(dnp_row_to_edit.get(h, ""))
                        try:
                            update_sheet_row(SPREADSHEET_NAME, target_dnp_tab, dnp_headers, ed_dnp_row_num, updated_dnp_rec)
                            write_activity_log(
                                SPREADSHEET_NAME,
                                current_user,
                                action="Edit Do Not Punch",
                                module="Do Not Punch",
                                details=(
                                    f"Updated row {ed_dnp_row_num} for {ed_n} ({ed_c}) "
                                    f"-> {ed_dnp_from.strftime('%Y-%m-%d')} to {ed_dnp_upto.strftime('%Y-%m-%d')}"
                                ),
                            )
                            st.session_state["editing_dnp_sheet_row"] = None
                            st.success("Do Not Punch record updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update record: {e}")
            with eb_b:
                if st.button("Cancel", key=f"ed_dnp_cancel_{ed_dnp_row_num}"):
                    st.session_state["editing_dnp_sheet_row"] = None
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        del_dnp_row_num = st.session_state.get("confirm_delete_dnp_row")
        dnp_row_to_del = next(
            (r for r in dnp_rows if r.get("_sheet_row") == del_dnp_row_num),
            None,
        )
        if dnp_row_to_del is not None and is_admin_user:
            del_n = resolve_field_value(dnp_row_to_del, "EMP_Name") or resolve_field_value(dnp_row_to_del, "Emp_Name")
            del_c = resolve_field_value(dnp_row_to_del, "EMP_Code")
            st.warning(
                f"Are you sure you want to delete Do Not Punch record for **{del_n}** ({del_c}) [Sheet Row {del_dnp_row_num}]?"
            )
            ddc1, ddc2, _ = st.columns([1.4, 1.2, 4])
            with ddc1:
                if st.button("Confirm Delete", type="primary", key=f"conf_del_dnp_{del_dnp_row_num}"):
                    try:
                        delete_sheet_row(SPREADSHEET_NAME, target_dnp_tab, del_dnp_row_num, actor_user=current_user)
                        write_activity_log(
                            SPREADSHEET_NAME,
                            current_user,
                            action="Delete Do Not Punch",
                            module="Do Not Punch",
                            details=f"Deleted DNP row {del_dnp_row_num} for {del_n} ({del_c})",
                        )
                        st.session_state["confirm_delete_dnp_row"] = None
                        if st.session_state.get("editing_dnp_sheet_row") == del_dnp_row_num:
                            st.session_state["editing_dnp_sheet_row"] = None
                        st.success("Do Not Punch record deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete record: {e}")
            with ddc2:
                if st.button("Keep Record", key=f"keep_del_dnp_{del_dnp_row_num}"):
                    st.session_state["confirm_delete_dnp_row"] = None
                    st.rerun()

        if not filtered_dnp:
            st.info("No Do Not Punch records found.")
        else:
            st.markdown("<div class='form-panel'><div class='section-tag'>Saved Records</div>", unsafe_allow_html=True)
            for rec in filtered_dnp[:200]:
                r_num = rec["_sheet_row"]
                r_code = resolve_field_value(rec, "EMP_Code") or "-"
                r_name = resolve_field_value(rec, "EMP_Name") or resolve_field_value(rec, "Emp_Name") or "-"
                r_dept = resolve_field_value(rec, "Emp_Department") or "-"
                r_from = resolve_field_value(rec, "Do Not Punch From") or "-"
                r_upto = resolve_field_value(rec, "Do Not Punch Upto") or "-"
                r_iss = resolve_field_value(rec, "Notification issue By") or "-"

                if is_admin_user:
                    c1, c2, c3, c4, c5, c_edit, c_del = st.columns([1.05, 1.9, 1.35, 1.75, 1.15, 0.78, 0.85])
                else:
                    c1, c2, c3, c4, c5, c_edit = st.columns([1.15, 2.05, 1.45, 1.85, 1.25, 0.85])

                with c1:
                    st.markdown(f"<span class='muted-sub'>{html.escape(r_code)}</span>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"<div style='font-weight:600;color:#f8fafc;'>{html.escape(r_name)}</div>", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"<span class='muted-sub'>{html.escape(r_dept)}</span>", unsafe_allow_html=True)
                with c4:
                    st.markdown(f"<span style='font-size:13px;color:#e2e8f0;'>{html.escape(r_from)} → {html.escape(r_upto)}</span>", unsafe_allow_html=True)
                with c5:
                    st.markdown(f"<span class='leave-badge'>{html.escape(r_iss)}</span>", unsafe_allow_html=True)
                with c_edit:
                    if st.button("Edit", key=f"btn_edit_dnp_{r_num}", use_container_width=True):
                        st.session_state["editing_dnp_sheet_row"] = r_num
                        st.session_state["confirm_delete_dnp_row"] = None
                        st.rerun()
                if is_admin_user:
                    with c_del:
                        if st.button("Delete", key=f"btn_del_dnp_{r_num}", use_container_width=True):
                            st.session_state["confirm_delete_dnp_row"] = r_num
                            st.rerun()
                st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid rgba(148,163,184,0.10);'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.subheader("Full Table View")
        render_html_table(filtered_dnp, max_rows=300)


# ================= SLICE 5: OTHER SHEET TABS =================
elif slice_choice == "Other Sheet Tabs":
    render_banner(
        "Other Sheet Tabs",
        f"Spreadsheet: <b>{html.escape(SPREADSHEET_NAME)}</b>",
    )
    system_or_known = {t for t in [faculty_tab, leave_tab, dnp_tab, USERS_TAB_NAME, LOGS_TAB_NAME, REQUESTS_TAB_NAME] if t}
    other_tabs = [t for t in all_tabs if t not in system_or_known]
    if not other_tabs:
        other_tabs = [t for t in all_tabs if t not in {USERS_TAB_NAME, LOGS_TAB_NAME, REQUESTS_TAB_NAME}]
    if not other_tabs:
        st.info("No other tabs found.")
    else:
        selected_tab = st.selectbox("Select Tab", other_tabs)
        try:
            _, tab_rows = load_worksheet_rows_with_index(SPREADSHEET_NAME, selected_tab)
            render_html_table(tab_rows, max_rows=100)
        except Exception as e:
            st.error(f"Failed to load {selected_tab}: {e}")


# ================= SLICE 6: USERS, SECURITY, LOGS & ADMIN NOTICES =================
elif slice_choice == "Users":
    banner_meta = (
        f"Logged in as: <b>{html.escape(current_user['name'])}</b>"
        + (
            f"  |  Users: <b>{html.escape(USERS_TAB_NAME)}</b>  |  "
            f"Logs: <b>{html.escape(LOGS_TAB_NAME)}</b>  |  Notices: <b>{html.escape(REQUESTS_TAB_NAME)}</b>"
            if is_admin_user else ""
        )
    )
    render_banner(
        "Security & Password" if not is_admin_user else "Users, Activity Logs & Admin Notices",
        banner_meta,
    )

    if is_admin_user:
        notice_tab_label = (
            f"🔔 Admin Notices ({len(pending_notices_list)} Pending)"
            if pending_notices_list else "🔔 Admin Notices"
        )
        tab_users_mgmt, tab_admin_notices, tab_activity_logs = st.tabs([
            "👥 Users & Password",
            notice_tab_label,
            "📜 Activity Log List",
        ])
    else:
        tab_users_mgmt = st.container()
        tab_admin_notices = None
        tab_activity_logs = None

    with tab_users_mgmt:
        if is_admin_user:
            st.markdown("<div class='form-panel'><div class='section-tag'>Users (From Google Sheet)</div>", unsafe_allow_html=True)
            user_list_rows = [
                {
                    "Username": uname,
                    "Full Name": info["name"],
                    "Role": info["role"].upper(),
                    "Created At": info.get("created_at", ""),
                }
                for uname, info in sheet_users_db.items()
            ]
            render_html_table(user_list_rows, max_rows=100)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='form-panel'><div class='section-tag'>Add New User (Saved to 'Users' Sheet)</div>", unsafe_allow_html=True)
            with st.form("add_new_user_form"):
                u1, u2, u3 = st.columns(3)
                with u1:
                    new_uname = st.text_input("New Username", placeholder="e.g. hr_user").strip().lower()
                with u2:
                    new_fullname = st.text_input("Full Name", placeholder="e.g. HR Officer").strip()
                with u3:
                    new_role = st.selectbox("Role", ["user", "admin"])
                new_pass = st.text_input("Initial Password", type="password", placeholder="Set password")
                create_u_btn = st.form_submit_button("Create User", type="primary")

            if create_u_btn:
                if not new_uname or not new_pass:
                    st.error("Username and password are required.")
                elif new_uname in sheet_users_db:
                    st.warning("This username already exists in the Users sheet.")
                else:
                    try:
                        add_user_to_sheet(SPREADSHEET_NAME, new_uname, new_fullname, new_role, new_pass)
                        write_activity_log(
                            SPREADSHEET_NAME,
                            current_user,
                            action="Create User",
                            module="Users & Security",
                            details=f"Created user '{new_uname}' ({new_fullname or new_uname}) with role '{new_role}'.",
                        )
                        st.success(f"User '{new_uname}' saved to '{USERS_TAB_NAME}' sheet!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create user: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='form-panel'><div class='section-tag'>Change My Password</div>", unsafe_allow_html=True)
        with st.form("change_pw_form"):
            curr_pw = st.text_input("Current Password", type="password")
            next_pw = st.text_input("New Password", type="password")
            chg_btn = st.form_submit_button("Update Password", type="primary")

        if chg_btn:
            uname = current_user["username"]
            rec = sheet_users_db.get(uname)
            if rec and verify_password(curr_pw, rec["password_hash"]) and next_pw:
                try:
                    ok_upd = update_user_password_in_sheet(SPREADSHEET_NAME, uname, next_pw)
                    if ok_upd:
                        write_activity_log(
                            SPREADSHEET_NAME,
                            current_user,
                            action="Change Password",
                            module="Users & Security",
                            details=f"User '{uname}' updated their password in '{USERS_TAB_NAME}' sheet.",
                        )
                        st.success("Password updated in Google Sheet!")
                        st.rerun()
                    else:
                        st.error("User row not found in Users sheet.")
                except Exception as e:
                    st.error(f"Failed to update password: {e}")
            else:
                st.error("Current password is incorrect or new password is empty.")
        st.markdown("</div>", unsafe_allow_html=True)

    if is_admin_user and tab_admin_notices is not None:
        with tab_admin_notices:
            st.subheader(f"Admin Feature Notices ({REQUESTS_TAB_NAME})")
            try:
                _, all_notices = load_worksheet_rows_with_index(SPREADSHEET_NAME, REQUESTS_TAB_NAME)
            except Exception as e:
                st.error(f"Failed to load '{REQUESTS_TAB_NAME}' sheet: {e}")
                all_notices = []

            if not all_notices:
                st.info("No feature notices from users yet.")
            else:
                st.markdown("<div class='form-panel'><div class='section-tag'>User Feature Requests & Notices</div>", unsafe_allow_html=True)
                for n_rec in reversed(all_notices):
                    n_row = n_rec["_sheet_row"]
                    n_ts = str(n_rec.get("Timestamp", "")).strip()
                    n_user = str(n_rec.get("Name", n_rec.get("Username", ""))).strip()
                    n_q = str(n_rec.get("Question", "")).strip()
                    n_status = str(n_rec.get("Status", "Pending")).strip() or "Pending"
                    n_note = str(n_rec.get("Admin_Note", "")).strip()

                    nc1, nc2, nc3 = st.columns([3.2, 1.3, 1.2])
                    with nc1:
                        st.markdown(
                            f"<div style='font-weight:700;color:#f8fafc;'>“{html.escape(n_q)}”</div>"
                            f"<div class='muted-sub'>By: {html.escape(n_user)} · {html.escape(n_ts)}</div>",
                            unsafe_allow_html=True,
                        )
                    with nc2:
                        new_st = st.selectbox(
                            "Status",
                            ["Pending", "Option Created", "Dismissed"],
                            index=["Pending", "Option Created", "Dismissed"].index(n_status)
                            if n_status in ["Pending", "Option Created", "Dismissed"] else 0,
                            key=f"notice_st_{n_row}",
                            label_visibility="collapsed",
                        )
                    with nc3:
                        if st.button("Save Status", key=f"notice_save_{n_row}", use_container_width=True):
                            try:
                                update_feature_notice_status(SPREADSHEET_NAME, n_row, new_st, n_note)
                                write_activity_log(
                                    SPREADSHEET_NAME,
                                    current_user,
                                    action="Update Feature Notice",
                                    module="Admin Notices",
                                    details=f"Marked notice row {n_row} ('{n_q}') as '{new_st}'.",
                                )
                                st.success("Notice status updated!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update notice: {e}")
                    st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid rgba(148,163,184,0.10);'>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    if is_admin_user and tab_activity_logs is not None:
        with tab_activity_logs:
            st.subheader(f"Activity Log List ({LOGS_TAB_NAME})")

            try:
                _, raw_logs = load_worksheet_rows_with_index(SPREADSHEET_NAME, LOGS_TAB_NAME)
            except Exception as e:
                st.error(f"Failed to load '{LOGS_TAB_NAME}' sheet: {e}")
                raw_logs = []

            lc1, lc2, lc3 = st.columns([2, 1, 1])
            with lc1:
                log_q = st.text_input(
                    "Search by User, Action, Module, or Details",
                    "",
                    placeholder="Type keyword...",
                    key="activity_log_search_box",
                ).strip().lower()
            log_users = sorted({str(r.get("Username", "")).strip() for r in raw_logs if str(r.get("Username", "")).strip()})
            with lc2:
                sel_log_user = st.selectbox("Filter by User", ["All"] + log_users, key="activity_log_user_box")
            with lc3:
                st.metric("Total Log Entries", len(raw_logs))

            filtered_logs = []
            for lr in reversed(raw_logs):
                if sel_log_user != "All" and str(lr.get("Username", "")).strip() != sel_log_user:
                    continue
                if log_q:
                    hay = " ".join([
                        str(lr.get("Timestamp", "")),
                        str(lr.get("Username", "")),
                        str(lr.get("Name", "")),
                        str(lr.get("Action", "")),
                        str(lr.get("Module", "")),
                        str(lr.get("Details", "")),
                    ]).lower()
                    if log_q not in hay:
                        continue
                filtered_logs.append(lr)

            render_html_table(filtered_logs, max_rows=500)