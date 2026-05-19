import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import json
import calendar
import base64
from io import BytesIO
from PIL import Image
import pillow_heif
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid

JST = timezone(timedelta(hours=9))

def get_today_jst():
    return datetime.now(JST).date()


st.set_page_config(
    page_title="📔 ふたりの日記",
    page_icon="📔",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* ===== ベースリセット ===== */
    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

    /* ===== ページ全体 ===== */
    .main .block-container {
        max-width: 480px !important;
        margin: 0 auto !important;
        padding: 0 14px 100px 14px !important;
    }

    /* ===== ボトムナビゲーション (iPhone ネイティブ風) ===== */
    /* Streamlit のタブボタンをボトムナビとして使うためのスタイル上書き */
    div[data-testid="stHorizontalBlock"]:has(> div > div[data-testid="stButton"]:nth-child(1)):has(> div > div[data-testid="stButton"]:nth-child(2)):has(> div > div[data-testid="stButton"]:nth-child(3)):has(> div > div[data-testid="stButton"]:nth-child(4)) {
        /* ナビバー用のブロックには追加スタイルなし (JS不使用のため通常表示) */
    }

    /* ===== ボタン共通 ===== */
    .stButton > button {
        width: 100% !important;
        min-height: 48px !important;          /* タッチターゲット 48px */
        border-radius: 14px !important;
        font-size: 16px !important;            /* iOS zoom 防止: 16px以上 */
        font-weight: 600 !important;
        letter-spacing: -0.2px;
        border: 1.5px solid rgba(236,72,153,0.25) !important;
        background: white !important;
        color: #ec4899 !important;
        transition: background 0.15s, transform 0.1s;
        touch-action: manipulation;
    }
    .stButton > button:active {
        transform: scale(0.97) !important;
        background: rgba(236,72,153,0.07) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #f472b6, #ec4899) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 2px 12px rgba(236,72,153,0.3);
    }

    /* ===== カード ===== */
    .card {
        background: white;
        border-radius: 20px;
        padding: 18px 16px;
        margin: 10px 0;
        border: 1px solid rgba(0,0,0,0.07);
        box-shadow: 0 2px 16px rgba(0,0,0,0.06);
    }

    /* ===== 統計ボックス ===== */
    .stat-box {
        border-radius: 18px;
        padding: 16px 10px;
        text-align: center;
        background: linear-gradient(135deg,rgba(244,114,182,0.12),rgba(236,72,153,0.12));
        border: 1.5px solid rgba(244,114,182,0.25);
    }
    .stat-box .stat-num {
        font-size: 28px;
        font-weight: 700;
        color: #ec4899;
        line-height: 1.1;
    }
    .stat-box .stat-label {
        font-size: 12px;
        color: #9ca3af;
        margin-top: 2px;
    }
    .stat-box .stat-icon { font-size: 20px; margin-bottom: 4px; }

    /* ===== コメント ===== */
    .comment-box {
        background: #fdf2f8;
        border-radius: 12px;
        padding: 10px 12px;
        margin: 6px 0;
        border-left: 3px solid #f472b6;
    }
    .comment-meta {
        font-size: 12px;
        color: #9ca3af;
        margin-bottom: 4px;
    }
    .comment-text { font-size: 15px; color: #374151; }

    /* ===== ヘッダー ===== */
    .header-bar {
        background: linear-gradient(135deg, #f472b6, #db2777);
        padding: 16px 18px 14px;
        border-radius: 0 0 24px 24px;
        margin: -14px -14px 14px -14px;   /* block-container padding を打ち消して端まで伸ばす */
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .header-avatar { font-size: 40px; line-height: 1; }
    .header-title  { color: white; font-size: 17px; font-weight: 700; letter-spacing: -0.3px; }
    .header-sub    { color: rgba(255,255,255,0.75); font-size: 12px; margin-top: 1px; }
    .header-badge  {
        margin-left: auto;
        background: #ef4444;
        color: white;
        border-radius: 12px;
        padding: 3px 9px;
        font-size: 13px;
        font-weight: 700;
        min-width: 26px;
        text-align: center;
    }

    /* ===== タブナビゲーション ===== */
    .tab-nav {
        display: flex;
        background: #f3f4f6;
        border-radius: 14px;
        padding: 4px;
        gap: 2px;
        margin-bottom: 16px;
    }
    .tab-nav-item {
        flex: 1;
        text-align: center;
        padding: 8px 4px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 600;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.15s;
        user-select: none;
    }
    .tab-nav-item.active {
        background: white;
        color: #ec4899;
        box-shadow: 0 1px 6px rgba(0,0,0,0.1);
    }
    .tab-nav-icon { font-size: 18px; display: block; }

    /* ===== スタンプグリッド ===== */
    /* スタンプは2列×N行で大きめに */
    .stamp-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin: 12px 0;
    }
    .stamp-btn-wrapper .stButton > button {
        min-height: 64px !important;
        border-radius: 16px !important;
        font-size: 22px !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
    }

    /* ===== セクションヘッダー ===== */
    .section-header {
        background: linear-gradient(135deg, #f472b6, #ec4899);
        padding: 13px 16px;
        border-radius: 14px;
        color: white;
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* ===== ユーザーカードヘッダー ===== */
    .user-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
        padding-bottom: 10px;
        border-bottom: 1px solid #f3e8f5;
    }
    .user-card-avatar { font-size: 26px; }
    .user-card-name   { font-size: 15px; font-weight: 600; color: #374151; }
    .user-card-date   { font-size: 12px; color: #9ca3af; }

    /* ===== インフォメッセージ ===== */
    .info-empty {
        text-align: center;
        color: #9ca3af;
        font-size: 14px;
        padding: 18px 0;
    }

    /* ===== 投稿プレビュー行 ===== */
    .entry-row {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 10px 0;
        border-bottom: 1px solid #f3f4f6;
    }
    .entry-row:last-child { border-bottom: none; }
    .entry-row-icon { font-size: 20px; min-width: 24px; }
    .entry-row-body { flex: 1; min-width: 0; }
    .entry-row-stamp { font-size: 14px; font-weight: 600; color: #374151; }
    .entry-row-text  { font-size: 14px; color: #6b7280; margin-top: 2px; word-break: break-all; }

    /* ===== テキスト入力・テキストエリア ===== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        font-size: 16px !important;   /* iOS zoom 防止 */
        border-radius: 12px !important;
        min-height: 48px !important;
        padding: 12px 14px !important;
    }

    /* ===== セレクトボックス ===== */
    .stSelectbox > div > div {
        font-size: 16px !important;
        border-radius: 12px !important;
        min-height: 48px !important;
    }

    /* ===== 区切り線 ===== */
    hr { margin: 10px 0 !important; border-color: #f3f4f6 !important; }

    /* ===== expander ===== */
    .streamlit-expanderHeader {
        font-size: 15px !important;
        border-radius: 12px !important;
        min-height: 48px !important;
    }

    /* ===== iPhone Safe Area ===== */
    @supports (padding-bottom: env(safe-area-inset-bottom)) {
        .main .block-container {
            padding-bottom: calc(90px + env(safe-area-inset-bottom)) !important;
        }
    }

    /* ===== タイポグラフィ ===== */
    h1, h2, h3 { color: #1f2937; }
    h1 { font-size: 20px !important; }
    h2 { font-size: 17px !important; color: #ec4899; }
    h3 { font-size: 15px !important; }

    /* ===== スクロールバー非表示 ===== */
    ::-webkit-scrollbar { display: none; }

    /* ===== ダークモード ===== */
    @media (prefers-color-scheme: dark) {
        .card { background: #1f2937; border-color: rgba(255,255,255,0.08); }
        .comment-box { background: #111827; }
        .comment-text { color: #e5e7eb; }
        .tab-nav { background: #111827; }
        .tab-nav-item.active { background: #1f2937; }
        .user-card-name { color: #f3f4f6; }
        .entry-row-stamp { color: #f3f4f6; }
    }
</style>
""", unsafe_allow_html=True)

# スタンプ定義
CONDITION_STAMPS = [
    {"emoji": "🤩", "label": "最高!"},
    {"emoji": "😊", "label": "良い"},
    {"emoji": "😴", "label": "よく眠れた"},
    {"emoji": "😪", "label": "眠い…"},
    {"emoji": "💪", "label": "元気いっぱい"},
    {"emoji": "🤒", "label": "体調不良"},
    {"emoji": "😐", "label": "普通"},
    {"emoji": "😔", "label": "微妙"},
]

MOOD_STAMPS = [
    {"emoji": "🥰", "label": "ラブラブ"},
    {"emoji": "😊", "label": "幸せ"},
    {"emoji": "🤗", "label": "楽しい"},
    {"emoji": "😌", "label": "平和"},
    {"emoji": "😐", "label": "普通"},
    {"emoji": "🤔", "label": "考え中"},
    {"emoji": "😰", "label": "不安"},
    {"emoji": "😢", "label": "悲しい"},
]


def open_image(file):
    try:
        if file.name.lower().endswith(('.heic', '.heif')):
            heif_file = pillow_heif.read_heif(file)
            image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
        else:
            image = Image.open(file)
        return image
    except Exception as e:
        raise ValueError(f"画像の読み込みに失敗しました: {e}")


def process_image_for_storage(uploaded_file):
    try:
        image = open_image(uploaded_file)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            if 'A' in image.mode:
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        image.thumbnail((500, 500), Image.Resampling.LANCZOS)
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=80, optimize=True)
        image_data = base64.b64encode(buffered.getvalue()).decode()
        if len(image_data) > 45000:
            buffered = BytesIO()
            image.thumbnail((400, 400), Image.Resampling.LANCZOS)
            image.save(buffered, format="JPEG", quality=60, optimize=True)
            image_data = base64.b64encode(buffered.getvalue()).decode()
            if len(image_data) > 45000:
                raise ValueError("画像が大きすぎます。別の画像を選んでください。")
        return image_data, image
    except Exception as e:
        raise ValueError(f"画像の処理に失敗しました: {e}")


@st.cache_resource
def init_gspread():
    try:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(st.secrets["spreadsheet_key"])
        return spreadsheet
    except Exception as e:
        st.error(f"スプレッドシート接続エラー: {e}")
        st.info("Streamlit CloudのSecretsが正しく設定されているか確認してください")
        st.stop()


def get_or_create_worksheet(spreadsheet, sheet_name, headers):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
        worksheet.append_row(headers)
    return worksheet


def init_database():
    spreadsheet = init_gspread()
    get_or_create_worksheet(
        spreadsheet, "entries",
        ["id", "user_id", "entry_date", "morning_stamp_emoji", "morning_stamp_label",
         "morning_message", "evening_stamp_emoji", "evening_stamp_label", "evening_diary_text",
         "image_data", "is_favorite", "created_at", "updated_at"]
    )
    get_or_create_worksheet(
        spreadsheet, "comments",
        ["id", "entry_id", "user_id", "comment_text", "created_at"]
    )
    settings_ws = get_or_create_worksheet(
        spreadsheet, "settings", ["key", "value"]
    )
    if len(settings_ws.get_all_values()) <= 1:
        for setting in [
            ["user_a_name", "あなた"], ["user_a_avatar", "👩"],
            ["user_b_name", "パートナー"], ["user_b_avatar", "👨"],
            ["anniversary", ""]
        ]:
            settings_ws.append_row(setting)


@st.cache_data(ttl=300)
def load_settings():
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("settings")
    rows = worksheet.get_all_values()[1:]
    return {row[0]: row[1] for row in rows if len(row) >= 2}


def save_settings(settings):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("settings")
    for key, value in settings.items():
        cell = worksheet.find(key)
        if cell:
            worksheet.update_cell(cell.row, 2, value)
        else:
            worksheet.append_row([key, value])
    st.cache_data.clear()


@st.cache_data(ttl=300, show_spinner=False)
def load_entries(_date_key=None):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("entries")
    data = worksheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=[
            'id', 'user_id', 'entry_date', 'morning_stamp_emoji', 'morning_stamp_label',
            'morning_message', 'evening_stamp_emoji', 'evening_stamp_label', 'evening_diary_text',
            'image_data', 'is_favorite', 'created_at', 'updated_at'
        ])
    df = pd.DataFrame(data)
    df = df.replace('', pd.NA)
    if 'is_favorite' in df.columns:
        df['is_favorite'] = pd.to_numeric(df['is_favorite'], errors='coerce').fillna(0).astype(int)
    df = df.sort_values('entry_date', ascending=False)
    return df


def load_comments(entry_id):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("comments")
    rows = worksheet.get_all_values()[1:]
    return [row for row in rows if len(row) >= 5 and row[1] == entry_id]


def add_comment(entry_id, user_id, comment_text):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("comments")
    worksheet.append_row([str(uuid.uuid4()), entry_id, user_id, comment_text, datetime.now().isoformat()])
    st.cache_data.clear()


def update_comment(comment_id, new_text):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("comments")
    cell = worksheet.find(comment_id)
    if cell:
        worksheet.update_cell(cell.row, 4, new_text)
    st.cache_data.clear()


def delete_comment(comment_id):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("comments")
    cell = worksheet.find(comment_id)
    if cell:
        worksheet.delete_rows(cell.row)
    st.cache_data.clear()


def toggle_favorite(entry_id):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("entries")
    cell = worksheet.find(entry_id)
    if cell:
        current = worksheet.cell(cell.row, 11).value
        worksheet.update_cell(cell.row, 11, 0 if str(current) == "1" else 1)
    st.cache_data.clear()


def calculate_streak(entries):
    if entries.empty:
        return 0
    streak = 0
    expected_date = get_today_jst()
    for entry_date_str in entries.sort_values('entry_date', ascending=False)['entry_date']:
        try:
            entry_date = datetime.strptime(str(entry_date_str), "%Y-%m-%d").date()
            if entry_date == expected_date:
                streak += 1
                expected_date -= timedelta(days=1)
            elif entry_date < expected_date:
                break
        except:
            continue
    return streak


def get_statistics(entries):
    return {
        "total_entries": len(entries),
        "this_month": len(entries[pd.to_datetime(entries['entry_date']).dt.month == get_today_jst().month]) if not entries.empty else 0,
        "streak": calculate_streak(entries)
    }


def get_unread_comments_count(user_id, entries):
    if entries.empty:
        return 0
    partner_entries = entries[entries['user_id'] != user_id]
    unread_count = 0
    for _, entry in partner_entries.iterrows():
        for comment in load_comments(entry['id']):
            if len(comment) >= 3 and comment[2] == user_id:
                unread_count += 1
    return unread_count


def save_entry(user_id, entry_date, morning=None, evening=None, image_data=None):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("entries")
    all_data = worksheet.get_all_values()
    entry_id = None
    entry_row = None
    for i, row in enumerate(all_data[1:], start=2):
        if len(row) >= 3 and row[1] == user_id and row[2] == entry_date:
            entry_id = row[0]
            entry_row = i
            break
    now = datetime.now().isoformat()
    if entry_row:
        if morning:
            worksheet.update_cell(entry_row, 4, morning['stamp']['emoji'])
            worksheet.update_cell(entry_row, 5, morning['stamp']['label'])
            worksheet.update_cell(entry_row, 6, morning.get('message', ''))
        if evening:
            worksheet.update_cell(entry_row, 7, evening['stamp']['emoji'])
            worksheet.update_cell(entry_row, 8, evening['stamp']['label'])
            worksheet.update_cell(entry_row, 9, evening['diary_text'])
        if image_data:
            worksheet.update_cell(entry_row, 10, image_data)
        worksheet.update_cell(entry_row, 13, now)
    else:
        entry_id = str(uuid.uuid4())
        worksheet.append_row([
            entry_id, user_id, entry_date,
            morning['stamp']['emoji'] if morning else '',
            morning['stamp']['label'] if morning else '',
            morning.get('message', '') if morning else '',
            evening['stamp']['emoji'] if evening else '',
            evening['stamp']['label'] if evening else '',
            evening['diary_text'] if evening else '',
            image_data if image_data else '',
            0, now, now
        ])
    st.cache_data.clear()
    return entry_id


def delete_morning_entry(entry_id):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("entries")
    cell = worksheet.find(entry_id)
    if cell:
        row = cell.row
        if worksheet.cell(row, 7).value:
            worksheet.update_cell(row, 4, '')
            worksheet.update_cell(row, 5, '')
            worksheet.update_cell(row, 6, '')
            worksheet.update_cell(row, 13, datetime.now().isoformat())
        else:
            worksheet.delete_rows(row)
            comments_ws = spreadsheet.worksheet("comments")
            for c in reversed(comments_ws.findall(entry_id)):
                if comments_ws.cell(c.row, 2).value == entry_id:
                    comments_ws.delete_rows(c.row)
    st.cache_data.clear()


def delete_evening_entry(entry_id):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("entries")
    cell = worksheet.find(entry_id)
    if cell:
        row = cell.row
        if worksheet.cell(row, 4).value:
            for col in [7, 8, 9, 10]:
                worksheet.update_cell(row, col, '')
            worksheet.update_cell(row, 13, datetime.now().isoformat())
        else:
            worksheet.delete_rows(row)
            comments_ws = spreadsheet.worksheet("comments")
            for c in reversed(comments_ws.findall(entry_id)):
                if comments_ws.cell(c.row, 2).value == entry_id:
                    comments_ws.delete_rows(c.row)
    st.cache_data.clear()


def reset_database():
    spreadsheet = init_gspread()
    for sheet_name in ["entries", "comments"]:
        ws = spreadsheet.worksheet(sheet_name)
        ws.resize(rows=1)
        ws.resize(rows=1000)
    st.cache_data.clear()


# ===== 初期化 =====
if 'initialized' not in st.session_state:
    init_database()
    st.session_state.initialized = True
    st.session_state.current_user = None
    st.session_state.tab = "home"
    st.session_state.screen = "main"
    st.session_state.cal_month = get_today_jst()
    st.session_state.last_date = get_today_jst().isoformat()

current_date = get_today_jst().isoformat()
if st.session_state.get('last_date') != current_date:
    st.cache_data.clear()
    st.session_state.last_date = current_date

try:
    settings = load_settings()
    entries = load_entries(_date_key=get_today_jst().isoformat())
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.stop()


# ===== ユーザー選択画面 =====
if st.session_state.current_user is None:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center; font-size:72px; line-height:1; margin-bottom:8px;'>📔</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='text-align:center; font-size:26px; font-weight:700; color:#1f2937; margin-bottom:4px;'>ふたりの日記</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='text-align:center; font-size:15px; color:#6b7280; margin-bottom:32px;'>あなたはどちらですか？</div>",
        unsafe_allow_html=True
    )
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        if st.button(f"{settings['user_a_avatar']}  {settings['user_a_name']}として使う", use_container_width=True):
            st.session_state.current_user = "A"
            st.rerun()
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button(f"{settings['user_b_avatar']}  {settings['user_b_name']}として使う", use_container_width=True):
            st.session_state.current_user = "B"
            st.rerun()
    st.stop()


# ===== メインアプリ =====
user_key    = "user_a" if st.session_state.current_user == "A" else "user_b"
partner_key = "user_b" if st.session_state.current_user == "A" else "user_a"
me      = {"id": st.session_state.current_user,
           "name": settings[f"{user_key}_name"],
           "avatar": settings[f"{user_key}_avatar"]}
partner = {"id": "A" if st.session_state.current_user == "B" else "B",
           "name": settings[f"{partner_key}_name"],
           "avatar": settings[f"{partner_key}_avatar"]}

unread_count = get_unread_comments_count(st.session_state.current_user, entries)


# ===== ヘルパー: 戻るボタン付きセクションヘッダー =====
def section_header(icon, title, back_screen="main"):
    if st.button("← 戻る"):
        for k in ['selected_morning_stamp', 'selected_evening_stamp', 'edit_entry_id']:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state.screen = back_screen
        st.rerun()
    st.markdown(
        f"<div class='section-header'><span>{icon}</span><span>{title}</span></div>",
        unsafe_allow_html=True
    )


# ===== ヘルパー: スタンプ選択グリッド (2列) =====
def stamp_selector(stamps, key_prefix, session_key):
    cols_count = 2
    for row_start in range(0, len(stamps), cols_count):
        row_stamps = stamps[row_start:row_start + cols_count]
        cols = st.columns(cols_count)
        for i, stamp in enumerate(row_stamps):
            with cols[i]:
                label = f"{stamp['emoji']}\n{stamp['label']}"
                if st.button(label, key=f"{key_prefix}_{row_start+i}", use_container_width=True):
                    st.session_state[session_key] = stamp


# ============================================================
# 朝の投稿画面
# ============================================================
if st.session_state.get('screen') == 'post_morning':
    section_header("☀️", "朝の体調報告")
    st.markdown("##### 今の体調は？")
    stamp_selector(CONDITION_STAMPS, "morning", "selected_morning_stamp")

    if 'selected_morning_stamp' in st.session_state:
        sel = st.session_state.selected_morning_stamp
        st.success(f"選択中: {sel['emoji']} {sel['label']}")
        message = st.text_input(f"💬 {partner['name']}へひとこと（任意）", max_chars=60, key="morning_msg")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("投稿する ✓", type="primary", use_container_width=True):
                save_entry(st.session_state.current_user, get_today_jst().isoformat(),
                           morning={"stamp": sel, "message": message})
                st.success("朝の投稿を保存しました!")
                del st.session_state.selected_morning_stamp
                st.session_state.screen = 'main'
                st.rerun()
        with col2:
            if st.button("キャンセル", use_container_width=True):
                if 'selected_morning_stamp' in st.session_state:
                    del st.session_state.selected_morning_stamp
                st.session_state.screen = 'main'
                st.rerun()
    st.stop()


# ============================================================
# 夜の投稿画面
# ============================================================
elif st.session_state.get('screen') == 'post_evening':
    section_header("🌙", "今日の日記")
    st.markdown("##### 今日の気分は？")
    stamp_selector(MOOD_STAMPS, "evening", "selected_evening_stamp")

    if 'selected_evening_stamp' in st.session_state:
        sel = st.session_state.selected_evening_stamp
        st.success(f"選択中: {sel['emoji']} {sel['label']}")
        st.markdown("##### 今日の出来事")
        diary_text = st.text_area("日記を書く", height=160, max_chars=500, key="diary_text",
                                  placeholder="今日はどんな日だった？")
        uploaded_file = st.file_uploader("📷 写真を追加（任意）",
                                         type=["jpg", "jpeg", "png", "heic", "heif"], key="photo")
        image_data = None
        if uploaded_file:
            try:
                image_data, preview_image = process_image_for_storage(uploaded_file)
                st.image(preview_image, use_container_width=True)
                st.caption(f"画像サイズ: {len(image_data):,} 文字（上限 45,000）")
            except Exception as e:
                st.error(f"画像の処理に失敗しました: {e}")
                image_data = None
        col1, col2 = st.columns(2)
        with col1:
            if st.button("投稿する ✓", type="primary", use_container_width=True):
                if diary_text.strip():
                    save_entry(st.session_state.current_user, get_today_jst().isoformat(),
                               evening={"stamp": sel, "diary_text": diary_text},
                               image_data=image_data)
                    st.success("夜の日記を保存しました!")
                    del st.session_state.selected_evening_stamp
                    st.session_state.screen = 'main'
                    st.rerun()
                else:
                    st.warning("日記を書いてください")
        with col2:
            if st.button("キャンセル", use_container_width=True):
                if 'selected_evening_stamp' in st.session_state:
                    del st.session_state.selected_evening_stamp
                st.session_state.screen = 'main'
                st.rerun()
    st.stop()


# ============================================================
# 朝の編集画面
# ============================================================
elif st.session_state.get('screen') == 'edit_morning':
    section_header("✏️", "朝の体調を編集")
    entry_id = st.session_state.get('edit_entry_id')
    current_entry = entries[entries['id'] == entry_id].iloc[0]

    st.markdown("##### スタンプを選択")
    stamp_selector(CONDITION_STAMPS, "edit_morning", "selected_morning_stamp")

    if 'selected_morning_stamp' not in st.session_state and pd.notna(current_entry['morning_stamp_emoji']):
        for s in CONDITION_STAMPS:
            if s['emoji'] == current_entry['morning_stamp_emoji']:
                st.session_state.selected_morning_stamp = s
                break

    if 'selected_morning_stamp' in st.session_state:
        sel = st.session_state.selected_morning_stamp
        st.success(f"選択中: {sel['emoji']} {sel['label']}")
        default_msg = str(current_entry['morning_message']) if pd.notna(current_entry['morning_message']) else ""
        message = st.text_input(f"💬 {partner['name']}へひとこと（任意）", max_chars=60,
                                key="edit_morning_msg", value=default_msg)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("更新する", type="primary", use_container_width=True):
                save_entry(st.session_state.current_user, str(current_entry['entry_date']),
                           morning={"stamp": sel, "message": message})
                st.success("更新しました!")
                for k in ['selected_morning_stamp', 'edit_entry_id']:
                    if k in st.session_state: del st.session_state[k]
                st.session_state.screen = 'main'
                st.rerun()
        with col2:
            if st.button("削除する", use_container_width=True):
                delete_morning_entry(entry_id)
                st.success("削除しました!")
                for k in ['selected_morning_stamp', 'edit_entry_id']:
                    if k in st.session_state: del st.session_state[k]
                st.session_state.screen = 'main'
                st.rerun()
        with col3:
            if st.button("キャンセル", use_container_width=True):
                for k in ['selected_morning_stamp', 'edit_entry_id']:
                    if k in st.session_state: del st.session_state[k]
                st.session_state.screen = 'main'
                st.rerun()
    st.stop()


# ============================================================
# 夜の編集画面
# ============================================================
elif st.session_state.get('screen') == 'edit_evening':
    section_header("✏️", "夜の日記を編集")
    entry_id = st.session_state.get('edit_entry_id')
    current_entry = entries[entries['id'] == entry_id].iloc[0]

    st.markdown("##### 今日の気分")
    stamp_selector(MOOD_STAMPS, "edit_evening", "selected_evening_stamp")

    if 'selected_evening_stamp' not in st.session_state and pd.notna(current_entry['evening_stamp_emoji']):
        for s in MOOD_STAMPS:
            if s['emoji'] == current_entry['evening_stamp_emoji']:
                st.session_state.selected_evening_stamp = s
                break

    if 'selected_evening_stamp' in st.session_state:
        sel = st.session_state.selected_evening_stamp
        st.success(f"選択中: {sel['emoji']} {sel['label']}")
        default_diary = str(current_entry['evening_diary_text']) if pd.notna(current_entry['evening_diary_text']) else ""
        diary_text = st.text_area("日記を書く", height=160, max_chars=500,
                                  key="edit_diary_text", value=default_diary)
        if pd.notna(current_entry.get('image_data')) and current_entry.get('image_data'):
            st.markdown("**現在の写真:**")
            st.image(f"data:image/jpeg;base64,{current_entry['image_data']}", use_container_width=True)
        uploaded_file = st.file_uploader("📷 写真を変更（任意）",
                                         type=["jpg", "jpeg", "png", "heic", "heif"], key="edit_photo")
        image_data = None
        if uploaded_file:
            try:
                image_data, preview_image = process_image_for_storage(uploaded_file)
                st.image(preview_image, use_container_width=True)
                st.caption(f"画像サイズ: {len(image_data):,} 文字（上限 45,000）")
            except Exception as e:
                st.error(f"画像の処理に失敗しました: {e}")
                image_data = None
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("更新する", type="primary", use_container_width=True):
                if diary_text.strip():
                    save_entry(st.session_state.current_user, str(current_entry['entry_date']),
                               evening={"stamp": sel, "diary_text": diary_text},
                               image_data=image_data)
                    st.success("更新しました!")
                    for k in ['selected_evening_stamp', 'edit_entry_id']:
                        if k in st.session_state: del st.session_state[k]
                    st.session_state.screen = 'main'
                    st.rerun()
                else:
                    st.warning("日記を書いてください")
        with col2:
            if st.button("削除する", use_container_width=True):
                delete_evening_entry(entry_id)
                st.success("削除しました!")
                for k in ['selected_evening_stamp', 'edit_entry_id']:
                    if k in st.session_state: del st.session_state[k]
                st.session_state.screen = 'main'
                st.rerun()
        with col3:
            if st.button("キャンセル", use_container_width=True):
                for k in ['selected_evening_stamp', 'edit_entry_id']:
                    if k in st.session_state: del st.session_state[k]
                st.session_state.screen = 'main'
                st.rerun()
    st.stop()


# ============================================================
# メイン画面
# ============================================================

# ヘッダー
badge_html = f"<span class='header-badge'>{unread_count}</span>" if unread_count > 0 else ""
st.markdown(f"""
<div class='header-bar'>
    <div class='header-avatar'>{me['avatar']}</div>
    <div>
        <div class='header-title'>📔 ふたりの日記</div>
        <div class='header-sub'>{me['name']} と {partner['name']}</div>
    </div>
    {badge_html}
</div>
""", unsafe_allow_html=True)

# タブナビゲーション（セグメントコントロール風）
tabs = [
    ("home",     "🏠", "ホーム"),
    ("calendar", "📅", "カレンダー"),
    ("history",  "📖", "履歴"),
    ("settings", "⚙️", "設定"),
]
current_tab = st.session_state.tab

tab_cols = st.columns(4)
for (tab_id, icon, label), col in zip(tabs, tab_cols):
    active_style = "background:white; color:#ec4899; box-shadow:0 1px 6px rgba(0,0,0,0.1);" if tab_id == current_tab else ""
    with col:
        if st.button(f"{icon}\n{label}", key=f"nav_{tab_id}", use_container_width=True):
            st.session_state.tab = tab_id
            st.rerun()

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ============================================================
# ホームタブ
# ============================================================
if st.session_state.tab == "home":
    today_str = get_today_jst().isoformat()

    # 統計 (2列)
    col1, col2 = st.columns(2)
    with col1:
        if settings.get('anniversary'):
            try:
                anniv_date = datetime.strptime(settings['anniversary'], "%Y-%m-%d").date()
                days_since = (get_today_jst() - anniv_date).days + 1
                st.markdown(f"""
                <div class='stat-box'>
                    <div class='stat-icon'>💑</div>
                    <div class='stat-num'>{days_since}</div>
                    <div class='stat-label'>一緒に {days_since} 日目</div>
                </div>""", unsafe_allow_html=True)
            except:
                pass
    with col2:
        streak = calculate_streak(entries)
        st.markdown(f"""
        <div class='stat-box'>
            <div class='stat-icon'>🔥</div>
            <div class='stat-num'>{streak}</div>
            <div class='stat-label'>{streak} 日連続投稿中</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ---- 自分の今日カード ----
    today_entries = entries[entries['entry_date'] == today_str] if not entries.empty else pd.DataFrame()
    my_today = today_entries[today_entries['user_id'] == st.session_state.current_user] if not today_entries.empty else pd.DataFrame()
    has_morning = not my_today.empty and pd.notna(my_today.iloc[0]['morning_stamp_emoji'])
    has_evening = not my_today.empty and pd.notna(my_today.iloc[0]['evening_stamp_emoji'])

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='user-card-header'>
        <span class='user-card-avatar'>{me['avatar']}</span>
        <div>
            <div class='user-card-name'>{me['name']}（あなた）</div>
            <div class='user-card-date'>{today_str}</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # 朝
    if has_morning:
        entry = my_today.iloc[0]
        st.markdown(f"""
        <div class='entry-row'>
            <span class='entry-row-icon'>☀️</span>
            <div class='entry-row-body'>
                <div class='entry-row-stamp'>{entry['morning_stamp_emoji']} {entry['morning_stamp_label']}</div>
                {"<div class='entry-row-text'>💬 " + str(entry['morning_message']) + "</div>" if pd.notna(entry['morning_message']) and str(entry['morning_message']) else ""}
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button("☀️ 朝の投稿を編集", key="edit_my_morning", use_container_width=True):
            st.session_state.edit_entry_id = entry['id']
            st.session_state.screen = 'edit_morning'
            st.rerun()
    else:
        if st.button("☀️ 朝の体調を投稿する", type="primary", use_container_width=True):
            st.session_state.screen = 'post_morning'
            st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # 夜
    if has_evening:
        entry = my_today.iloc[0]
        st.markdown(f"""
        <div class='entry-row'>
            <span class='entry-row-icon'>🌙</span>
            <div class='entry-row-body'>
                <div class='entry-row-stamp'>{entry['evening_stamp_emoji']} {entry['evening_stamp_label']}</div>
                <div class='entry-row-text'>{str(entry['evening_diary_text'])[:80]}{"…" if len(str(entry['evening_diary_text'])) > 80 else ""}</div>
            </div>
        </div>""", unsafe_allow_html=True)
        if pd.notna(entry.get('image_data')) and str(entry.get('image_data')):
            st.image(f"data:image/jpeg;base64,{entry['image_data']}", use_container_width=True)
        if st.button("🌙 夜の日記を編集", key="edit_my_evening", use_container_width=True):
            st.session_state.edit_entry_id = entry['id']
            st.session_state.screen = 'edit_evening'
            st.rerun()
    else:
        if st.button("🌙 今日の日記を書く", type="primary", use_container_width=True):
            st.session_state.screen = 'post_evening'
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # /card

    # ---- パートナーの今日カード ----
    partner_today = today_entries[today_entries['user_id'] == partner['id']] if not today_entries.empty else pd.DataFrame()

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='user-card-header'>
        <span class='user-card-avatar'>{partner['avatar']}</span>
        <div>
            <div class='user-card-name'>{partner['name']}</div>
            <div class='user-card-date'>{today_str}</div>
        </div>
    </div>""", unsafe_allow_html=True)

    if not partner_today.empty:
        entry = partner_today.iloc[0]
        entry_id = entry['id']
        is_fav = int(entry.get('is_favorite', 0)) == 1
        fav_label = "❤️ お気に入り解除" if is_fav else "🤍 お気に入り"
        if st.button(fav_label, key=f"fav_{entry_id}", use_container_width=True):
            toggle_favorite(entry_id)
            st.rerun()

        if pd.notna(entry['morning_stamp_emoji']):
            st.markdown(f"""
            <div class='entry-row'>
                <span class='entry-row-icon'>☀️</span>
                <div class='entry-row-body'>
                    <div class='entry-row-stamp'>{entry['morning_stamp_emoji']} {entry['morning_stamp_label']}</div>
                    {"<div class='entry-row-text'>💬 " + str(entry['morning_message']) + "</div>" if pd.notna(entry['morning_message']) and str(entry['morning_message']) else ""}
                </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-empty'>まだ朝の投稿がありません 🌅</div>", unsafe_allow_html=True)

        if pd.notna(entry['evening_stamp_emoji']):
            st.markdown(f"""
            <div class='entry-row'>
                <span class='entry-row-icon'>🌙</span>
                <div class='entry-row-body'>
                    <div class='entry-row-stamp'>{entry['evening_stamp_emoji']} {entry['evening_stamp_label']}</div>
                    <div class='entry-row-text'>{entry['evening_diary_text']}</div>
                </div>
            </div>""", unsafe_allow_html=True)

            if pd.notna(entry.get('image_data')) and str(entry.get('image_data')):
                st.image(f"data:image/jpeg;base64,{entry['image_data']}", use_container_width=True)

            # コメント
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("**💬 コメント**")
            comments = load_comments(entry_id)
            for comment in comments:
                if len(comment) >= 5:
                    comment_id, _, comment_user_id, comment_text, created_at = comment[:5]
                    comment_user = me if comment_user_id == st.session_state.current_user else partner
                    st.markdown(f"""
                    <div class='comment-box'>
                        <div class='comment-meta'>{comment_user['avatar']} {comment_user['name']} · {created_at[:10]}</div>
                        <div class='comment-text'>{comment_text}</div>
                    </div>""", unsafe_allow_html=True)
                    if comment_user_id == st.session_state.current_user:
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("編集", key=f"edit_comment_{comment_id}", use_container_width=True):
                                st.session_state.edit_comment_id = comment_id
                                st.session_state.edit_comment_text = comment_text
                                st.rerun()
                        with cc2:
                            if st.button("削除", key=f"delete_comment_{comment_id}", use_container_width=True):
                                delete_comment(comment_id)
                                st.success("コメントを削除しました!")
                                st.rerun()

            if st.session_state.get('edit_comment_id'):
                st.markdown("**コメントを編集**")
                edit_text = st.text_input("コメント", value=st.session_state.get('edit_comment_text', ''),
                                          key="edit_comment_input", max_chars=200)
                ec1, ec2 = st.columns(2)
                with ec1:
                    if st.button("更新", key="update_comment", use_container_width=True):
                        if edit_text.strip():
                            update_comment(st.session_state.edit_comment_id, edit_text)
                            del st.session_state.edit_comment_id
                            del st.session_state.edit_comment_text
                            st.success("更新しました!")
                            st.rerun()
                with ec2:
                    if st.button("キャンセル", key="cancel_edit_comment", use_container_width=True):
                        del st.session_state.edit_comment_id
                        del st.session_state.edit_comment_text
                        st.rerun()
            else:
                counter_key = f"comment_counter_{entry_id}"
                if counter_key not in st.session_state:
                    st.session_state[counter_key] = 0
                comment_text = st.text_input(
                    f"💬 {partner['name']}にコメント",
                    key=f"comment_input_{entry_id}_{st.session_state[counter_key]}",
                    max_chars=200, placeholder="優しいコメントを残そう…"
                )
                if st.button("送信 ✓", key=f"send_{entry_id}", use_container_width=True):
                    if comment_text.strip():
                        add_comment(entry_id, st.session_state.current_user, comment_text)
                        st.session_state[counter_key] += 1
                        st.success("コメントを送信しました!")
                        st.rerun()
        else:
            st.markdown("<div class='info-empty'>まだ夜の投稿がありません 🌙</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='info-empty'>{partner['name']}はまだ投稿していません 🌿</div>",
                    unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# カレンダータブ
# ============================================================
elif st.session_state.tab == "calendar":
    st.markdown("### 📅 カレンダー")

    st.markdown("""
    <div style='display:flex; gap:8px; font-size:12px; margin-bottom:12px; flex-wrap:wrap;'>
        <span style='background:#fef3c7; border:2px solid #f59e0b; padding:3px 8px; border-radius:6px;'>今日</span>
        <span style='background:#fce7f3; border:2px solid #f472b6; padding:3px 8px; border-radius:6px;'>投稿あり</span>
        <span style='background:#f9fafb; border:1px solid #e5e7eb; padding:3px 8px; border-radius:6px;'>通常</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ 前月", key="prev_month", use_container_width=True):
            st.session_state.cal_month = st.session_state.cal_month.replace(day=1) - timedelta(days=1)
            st.rerun()
    with col2:
        st.markdown(
            f"<div style='text-align:center; font-weight:700; color:#ec4899; font-size:17px; padding:10px;'>"
            f"{st.session_state.cal_month.strftime('%Y年%m月')}</div>",
            unsafe_allow_html=True
        )
    with col3:
        if st.button("次月 ▶", key="next_month", use_container_width=True):
            st.session_state.cal_month = (st.session_state.cal_month.replace(day=28) + timedelta(days=4)).replace(day=1)
            st.rerun()

    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(st.session_state.cal_month.year, st.session_state.cal_month.month)

    cal_html = """
    <style>
    .cal-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:3px; width:100%; }
    .cal-hdr  { text-align:center; font-size:11px; font-weight:600; padding:5px 0; }
    .cal-cell { aspect-ratio:1; display:flex; justify-content:center; align-items:center;
                border-radius:6px; font-size:13px; font-weight:400; }
    </style>
    <div class='cal-grid'>
    """
    for i, d in enumerate(["日","月","火","水","木","金","土"]):
        color = "#ef4444" if i == 0 else "#3b82f6" if i == 6 else "#6b7280"
        cal_html += f"<div class='cal-hdr' style='color:{color}'>{d}</div>"

    for week in cal:
        for i, day in enumerate(week):
            if day == 0:
                cal_html += "<div class='cal-cell' style='background:transparent'></div>"
            else:
                day_date = date(st.session_state.cal_month.year, st.session_state.cal_month.month, day)
                day_str = day_date.isoformat()
                has_entries = not entries.empty and (entries['entry_date'] == day_str).any()
                is_today = day_date == get_today_jst()
                day_color = "#dc2626" if i == 0 else "#2563eb" if i == 6 else "#374151"
                if is_today:
                    bg, border, fw = "#fef3c7", "2px solid #f59e0b", "700"
                elif has_entries:
                    bg, border, fw = "#fce7f3", "2px solid #f472b6", "600"
                else:
                    bg, border, fw = "#f9fafb", "1px solid #e5e7eb", "400"
                cal_html += (f"<div class='cal-cell' style='background:{bg};border:{border};"
                             f"color:{day_color};font-weight:{fw}'>{day}</div>")

    cal_html += "</div>"
    st.markdown(cal_html, unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    month_entries = pd.DataFrame()
    if not entries.empty:
        dt = pd.to_datetime(entries['entry_date'])
        month_entries = entries[(dt.dt.year == st.session_state.cal_month.year) &
                                (dt.dt.month == st.session_state.cal_month.month)]

    if not month_entries.empty:
        st.markdown(f"**📊 今月の記録: {len(month_entries)} 件**")
        for _, entry in month_entries.head(3).iterrows():
            user = me if entry['user_id'] == st.session_state.current_user else partner
            with st.expander(f"{user['avatar']} {entry['entry_date']} — {user['name']}"):
                if pd.notna(entry['morning_stamp_emoji']):
                    st.markdown(f"☀️ {entry['morning_stamp_emoji']} {entry['morning_stamp_label']}")
                if pd.notna(entry['evening_stamp_emoji']):
                    st.markdown(f"🌙 {entry['evening_stamp_emoji']} {entry['evening_stamp_label']}")
                    if pd.notna(entry['evening_diary_text']):
                        txt = str(entry['evening_diary_text'])
                        st.markdown(f"_{txt[:60]}{'…' if len(txt) > 60 else ''}_")
    else:
        st.info("今月はまだ投稿がありません")


# ============================================================
# 履歴タブ
# ============================================================
elif st.session_state.tab == "history":
    st.markdown("### 📖 履歴")

    search_query = st.text_input("🔍 日記を検索…", key="search")
    col1, col2 = st.columns(2)
    with col1:
        filter_user = st.selectbox("ユーザー", ["すべて", me['name'], partner['name']])
    with col2:
        filter_type = st.selectbox("種類", ["すべて", "お気に入りのみ"])

    if not entries.empty:
        filtered = entries.copy()
        if search_query:
            filtered = filtered[
                filtered['evening_diary_text'].astype(str).str.contains(search_query, na=False, case=False) |
                filtered['morning_message'].astype(str).str.contains(search_query, na=False, case=False)
            ]
        if filter_user != "すべて":
            fuid = me['id'] if filter_user == me['name'] else partner['id']
            filtered = filtered[filtered['user_id'] == fuid]
        if filter_type == "お気に入りのみ":
            filtered = filtered[filtered['is_favorite'] == 1]

        if filtered.empty:
            st.info("該当する日記が見つかりませんでした")
        else:
            st.markdown(f"**{len(filtered)} 件の日記**")
            for _, entry in filtered.head(30).iterrows():
                user = me if entry['user_id'] == st.session_state.current_user else partner
                is_fav = int(entry.get('is_favorite', 0)) == 1
                fav_icon = " ❤️" if is_fav else ""
                comments_count = len(load_comments(entry['id']))
                comment_badge = f" 💬{comments_count}" if comments_count > 0 else ""
                with st.expander(f"{user['avatar']} {user['name']} — {entry['entry_date']}{fav_icon}{comment_badge}"):
                    if pd.notna(entry['morning_stamp_emoji']):
                        st.markdown(f"**☀️ 朝:** {entry['morning_stamp_emoji']} {entry['morning_stamp_label']}")
                        if pd.notna(entry['morning_message']) and str(entry['morning_message']):
                            st.markdown(f"💬 {entry['morning_message']}")
                    if pd.notna(entry['evening_stamp_emoji']):
                        st.markdown(f"**🌙 夜:** {entry['evening_stamp_emoji']} {entry['evening_stamp_label']}")
                        st.markdown(entry['evening_diary_text'])
                        if pd.notna(entry.get('image_data')) and str(entry.get('image_data')):
                            st.image(f"data:image/jpeg;base64,{entry['image_data']}", use_container_width=True)
    else:
        st.info("まだ日記がありません")


# ============================================================
# 設定タブ
# ============================================================
elif st.session_state.tab == "settings":
    st.markdown("### 📊 統計")
    stats = get_statistics(entries)
    c1, c2, c3 = st.columns(3)
    c1.metric("総投稿数", stats['total_entries'])
    c2.metric("今月", stats['this_month'])
    c3.metric("連続", f"{stats['streak']} 日")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("### ⚙️ 設定")

    with st.form("settings_form"):
        user_a_name   = st.text_input("ユーザーA の名前",   value=settings['user_a_name'])
        user_a_avatar = st.text_input("ユーザーA のアバター", value=settings['user_a_avatar'])
        user_b_name   = st.text_input("ユーザーB の名前",   value=settings['user_b_name'])
        user_b_avatar = st.text_input("ユーザーB のアバター", value=settings['user_b_avatar'])
        anniversary   = st.date_input(
            "記念日",
            value=datetime.strptime(settings['anniversary'], "%Y-%m-%d").date()
                  if settings.get('anniversary') else None
        )
        if st.form_submit_button("保存する", use_container_width=True):
            save_settings({
                "user_a_name": user_a_name, "user_a_avatar": user_a_avatar,
                "user_b_name": user_b_name, "user_b_avatar": user_b_avatar,
                "anniversary": anniversary.isoformat() if anniversary else ""
            })
            st.success("設定を保存しました!")
            st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if st.button("🔄 ユーザーを切り替える", use_container_width=True):
        st.session_state.current_user = None
        st.rerun()

    st.markdown("---")
    st.warning("⚠️ 危険: すべての投稿とコメントが削除されます")
    if st.button("🗑 履歴をリセット", use_container_width=True):
        reset_database()
        st.success("リセットしました!")
        st.rerun()
