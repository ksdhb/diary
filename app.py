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

# 日本時間（JST）の定義
JST = timezone(timedelta(hours=9))

def get_today_jst():
    """日本時間の今日の日付を取得"""
    return datetime.now(JST).date()


# ページ設定（レスポンシブ対応）
st.set_page_config(
    page_title="📔 ふたりの日記",
    page_icon="📔",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# カスタムCSS（スマホ完全対応版）
st.markdown("""
<style>
    /* 全デバイス共通: 2カラムレイアウト */
    .main { 
        max-width: 900px; 
        margin: 0 auto; 
        padding: 0 15px 90px 15px;
        -webkit-overflow-scrolling: touch;
    }
    
    /* 小さい画面では少しpaddingを減らす */
    @media (max-width: 400px) {
        .main {
            padding: 0 10px 90px 10px;
        }
    }
    
    /* ボタン */
    .stButton>button { 
        width: 100%; 
        border-radius: 20px; 
        font-weight: 700;
        min-height: 44px;
        -webkit-tap-highlight-color: transparent;
        touch-action: manipulation;
        transition: all 0.2s ease;
    }
    .stButton>button:active {
        transform: scale(0.98);
    }
    
    /* カード */
    .card { 
        background: rgba(255,255,255,0.95); 
        border-radius: 20px; 
        padding: 18px; 
        margin: 12px 0; 
        box-shadow: 0 4px 24px rgba(0,0,0,0.08);
        backdrop-filter: blur(10px);
    }
    
    /* 統計ボックス */
    .stat-box { 
        border-radius: 16px; 
        padding: 14px; 
        text-align: center; 
        background: linear-gradient(135deg,rgba(244,114,182,0.15),rgba(236,72,153,0.15));
        border: 2px solid rgba(244,114,182,0.3);
    }
    
    /* コメント */
    .comment-box {
        background: #f9fafb;
        border-radius: 12px;
        padding: 10px 12px;
        margin: 8px 0;
        border-left: 3px solid #f472b6;
    }
    
    /* ヘッダーコンテナ */
    .header-container {
        background: linear-gradient(135deg, #f472b6, #ec4899);
        padding: 14px 18px;
        border-radius: 10px;
        margin: 0 0 10px;
    }
    .header-flex {
        display: flex;
        align-items: center;
        gap: 10px;
        position: relative;
    }
    .header-avatar {
        font-size: 36px;
    }
    .header-text {
        flex: 1;
    }
    .header-title {
        color: white;
        font-weight: 800;
        font-size: 16px;
    }
    .header-subtitle {
        color: rgba(255,255,255,0.8);
        font-size: 10px;
    }
    .badge {
        background: #ef4444;
        color: white;
        border-radius: 12px;
        padding: 4px 8px;
        font-size: 11px;
        font-weight: 700;
        margin-left: auto;
    }
    
    /* フォント */
    h1 { font-size: 20px !important; }
    h2 { font-size: 16px !important; color: #ec4899; }
    h3 { font-size: 14px !important; }
    
    /* スクロールバー非表示（iOS風） */
    ::-webkit-scrollbar { display: none; }
    
    /* ダークモード対応 */
    @media (prefers-color-scheme: dark) {
        .card { 
            background: rgba(30,30,30,0.95);
            color: #e5e7eb;
        }
        .comment-box {
            background: #1f2937;
            color: #e5e7eb;
        }
    }
    
    /* タブナビゲーション（常に横並び） */
    .tab-navigation {
        width: 100%;
        margin-bottom: 16px;
    }
    /* Streamlitのcolumnsコンテナを強制的に横並びに */
    .tab-navigation [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 4px !important;
    }
    .tab-navigation [data-testid="stHorizontalBlock"] > div {
        flex: 1 !important;
        min-width: 0 !important;
    }
    .tab-navigation .stButton > button {
        padding: 8px 4px;
        font-size: 11px;
        white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

# スタンプ定義
CONDITION_STAMPS = [
    {"emoji": "🤩", "label": "最高!"},
    {"emoji": "😊", "label": "良い"},
    {"emoji": "😄", "label": "元気"},
    {"emoji": "😌", "label": "まあまあ"},
    {"emoji": "😐", "label": "普通"},
    {"emoji": "😪", "label": "眠い"},
    {"emoji": "😔", "label": "微妙"},
    {"emoji": "😷", "label": "体調悪い"},
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


# 画像を開く（HEIC対応）
def open_image(file):
    """画像ファイルを開く（HEIC/HEIF形式にも対応）"""
    try:
        # HEIC/HEIF形式のチェック
        if file.name.lower().endswith(('.heic', '.heif')):
            # pillow_heifでHEICを読み込み
            heif_file = pillow_heif.read_heif(file)
            # PILイメージに変換
            image = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
            )
        else:
            # 通常の画像形式
            image = Image.open(file)
        return image
    except Exception as e:
        raise ValueError(f"画像の読み込みに失敗しました: {e}")


def process_image_for_storage(uploaded_file):
    """画像を処理してGoogle Sheets用に最適化"""
    try:
        image = open_image(uploaded_file)
        
        # RGBモードに変換（透過PNG対応）
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
        
        # サイズを縮小（Google Sheetsのセル制限対策）
        image.thumbnail((500, 500), Image.Resampling.LANCZOS)
        
        # JPEGに変換（品質80、最適化ON）
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=80, optimize=True)
        image_data = base64.b64encode(buffered.getvalue()).decode()
        
        # サイズチェック（Google Sheetsのセル制限は50,000文字）
        if len(image_data) > 45000:  # 余裕を持って45,000文字まで
            # さらに品質を下げて再圧縮
            buffered = BytesIO()
            image.thumbnail((400, 400), Image.Resampling.LANCZOS)
            image.save(buffered, format="JPEG", quality=60, optimize=True)
            image_data = base64.b64encode(buffered.getvalue()).decode()
            
            if len(image_data) > 45000:
                raise ValueError("画像が大きすぎます。別の画像を選んでください。")
        
        return image_data, image
    except Exception as e:
        raise ValueError(f"画像の処理に失敗しました: {e}")

# Googleスプレッドシート接続
@st.cache_resource
def init_gspread():
    """Googleスプレッドシートに接続"""
    try:
        # Streamlit Secretsから認証情報を取得
        credentials_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(credentials)
        
        # スプレッドシートを開く
        spreadsheet = client.open_by_key(st.secrets["spreadsheet_key"])
        return spreadsheet
    except Exception as e:
        st.error(f"スプレッドシート接続エラー: {e}")
        st.info("Streamlit CloudのSecretsが正しく設定されているか確認してください")
        st.stop()

def get_or_create_worksheet(spreadsheet, sheet_name, headers):
    """ワークシートを取得または作成"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
        worksheet.append_row(headers)
    return worksheet

# データベース初期化
def init_database():
    """スプレッドシートのシートを初期化"""
    spreadsheet = init_gspread()
    
    # entriesシート
    get_or_create_worksheet(
        spreadsheet, 
        "entries",
        ["id", "user_id", "entry_date", "morning_stamp_emoji", "morning_stamp_label", 
         "morning_message", "evening_stamp_emoji", "evening_stamp_label", "evening_diary_text",
         "image_data", "is_favorite", "created_at", "updated_at"]
    )
    
    # commentsシート
    get_or_create_worksheet(
        spreadsheet,
        "comments",
        ["id", "entry_id", "user_id", "comment_text", "created_at"]
    )
    
    # settingsシート
    settings_ws = get_or_create_worksheet(
        spreadsheet,
        "settings",
        ["key", "value"]
    )
    
    # デフォルト設定を追加（シートが空の場合）
    if len(settings_ws.get_all_values()) <= 1:
        default_settings = [
            ["user_a_name", "あなた"],
            ["user_a_avatar", "👩"],
            ["user_b_name", "パートナー"],
            ["user_b_avatar", "👨"],
            ["anniversary", ""]
        ]
        for setting in default_settings:
            settings_ws.append_row(setting)

# 設定を読み込む
@st.cache_data(ttl=300)  # 5分間キャッシュ
def load_settings():
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("settings")
    rows = worksheet.get_all_values()[1:]  # ヘッダーをスキップ
    settings = {row[0]: row[1] for row in rows if len(row) >= 2}
    return settings

# 設定を保存する
def save_settings(settings):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("settings")
    
    for key, value in settings.items():
        cell = worksheet.find(key)
        if cell:
            worksheet.update_cell(cell.row, 2, value)
        else:
            worksheet.append_row([key, value])
    st.cache_data.clear()  # キャッシュをクリア

# エントリーを読み込む
@st.cache_data(ttl=300, show_spinner=False)  # 5分間キャッシュ
def load_entries(_date_key=None):
    """日付をキーにしてキャッシュを管理"""
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("entries")
    data = worksheet.get_all_records()
    
    if not data:
        # 空の場合は正しいカラムを持つ空のDataFrameを返す
        return pd.DataFrame(columns=[
            'id', 'user_id', 'entry_date', 'morning_stamp_emoji', 'morning_stamp_label',
            'morning_message', 'evening_stamp_emoji', 'evening_stamp_label', 'evening_diary_text',
            'image_data', 'is_favorite', 'created_at', 'updated_at'
        ])
    
    df = pd.DataFrame(data)
    
    # 空文字列をNaNに変換
    df = df.replace('', pd.NA)
    # is_favoriteを数値に変換
    if 'is_favorite' in df.columns:
        df['is_favorite'] = pd.to_numeric(df['is_favorite'], errors='coerce').fillna(0).astype(int)
    # entry_dateでソート
    df = df.sort_values('entry_date', ascending=False)
    
    return df

# コメントを読み込む
def load_comments(entry_id):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("comments")
    rows = worksheet.get_all_values()[1:]  # ヘッダーをスキップ
    comments = [row for row in rows if len(row) >= 5 and row[1] == entry_id]
    return comments

# コメントを追加
def add_comment(entry_id, user_id, comment_text):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("comments")
    
    comment_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    worksheet.append_row([comment_id, entry_id, user_id, comment_text, created_at])
    st.cache_data.clear()  # キャッシュをクリア

# コメントを更新
def update_comment(comment_id, new_text):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("comments")
    
    cell = worksheet.find(comment_id)
    if cell:
        worksheet.update_cell(cell.row, 4, new_text)  # comment_textは4列目
    st.cache_data.clear()  # キャッシュをクリア

# コメントを削除
def delete_comment(comment_id):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("comments")
    
    cell = worksheet.find(comment_id)
    if cell:
        worksheet.delete_rows(cell.row)
    st.cache_data.clear()  # キャッシュをクリア

# お気に入りトグル
def toggle_favorite(entry_id):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("entries")
    
    cell = worksheet.find(entry_id)
    if cell:
        current = worksheet.cell(cell.row, 11).value  # is_favoriteは11列目
        new_value = 0 if str(current) == "1" else 1
        worksheet.update_cell(cell.row, 11, new_value)
    st.cache_data.clear()  # キャッシュをクリア

# 連続投稿日数を計算
def calculate_streak(entries):
    if entries.empty:
        return 0
    
    entries_sorted = entries.sort_values('entry_date', ascending=False)
    streak = 0
    expected_date = get_today_jst()
    
    for entry_date_str in entries_sorted['entry_date']:
        try:
            entry_date = datetime.strptime(str(entry_date_str), "%Y-%m-%d").date()
            if entry_date == expected_date:
                streak += 1
                expected_date = expected_date - timedelta(days=1)
            elif entry_date < expected_date:
                break
        except:
            continue
    
    return streak

# 統計情報を取得
def get_statistics(entries):
    stats = {
        "total_entries": len(entries),
        "this_month": len(entries[pd.to_datetime(entries['entry_date']).dt.month == get_today_jst().month]) if not entries.empty else 0,
        "streak": calculate_streak(entries)
    }
    return stats

# 未読コメント数を取得
def get_unread_comments_count(user_id, entries):
    if entries.empty:
        return 0
    
    partner_entries = entries[entries['user_id'] != user_id]
    unread_count = 0
    
    for _, entry in partner_entries.iterrows():
        comments = load_comments(entry['id'])
        for comment in comments:
            if len(comment) >= 3 and comment[2] == user_id:
                unread_count += 1
    
    return unread_count

# エントリーを保存（既存or新規作成）
def save_entry(user_id, entry_date, morning=None, evening=None, image_data=None):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("entries")
    
    # 既存エントリーを検索
    all_data = worksheet.get_all_values()
    entry_id = None
    entry_row = None
    
    for i, row in enumerate(all_data[1:], start=2):  # ヘッダーをスキップ
        if len(row) >= 3 and row[1] == user_id and row[2] == entry_date:
            entry_id = row[0]
            entry_row = i
            break
    
    now = datetime.now().isoformat()
    
    if entry_row:  # 既存エントリーを更新
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
        
        worksheet.update_cell(entry_row, 13, now)  # updated_at
    else:  # 新規エントリー
        entry_id = str(uuid.uuid4())
        new_row = [
            entry_id,
            user_id,
            entry_date,
            morning['stamp']['emoji'] if morning else '',
            morning['stamp']['label'] if morning else '',
            morning.get('message', '') if morning else '',
            evening['stamp']['emoji'] if evening else '',
            evening['stamp']['label'] if evening else '',
            evening['diary_text'] if evening else '',
            image_data if image_data else '',
            0,  # is_favorite
            now,  # created_at
            now   # updated_at
        ]
        worksheet.append_row(new_row)
    
    st.cache_data.clear()  # キャッシュをクリアして最新データを取得
    return entry_id

# 朝の投稿を削除
def delete_morning_entry(entry_id):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("entries")
    
    cell = worksheet.find(entry_id)
    if cell:
        row = cell.row
        evening_stamp = worksheet.cell(row, 7).value
        
        if evening_stamp:  # 夜の投稿がある場合は朝のデータだけクリア
            worksheet.update_cell(row, 4, '')  # morning_stamp_emoji
            worksheet.update_cell(row, 5, '')  # morning_stamp_label
            worksheet.update_cell(row, 6, '')  # morning_message
            worksheet.update_cell(row, 13, datetime.now().isoformat())  # updated_at
        else:  # 夜の投稿もない場合はエントリー全体を削除
            worksheet.delete_rows(row)
            # コメントも削除
            comments_ws = spreadsheet.worksheet("comments")
            cells = comments_ws.findall(entry_id)
            for cell in reversed(cells):
                if comments_ws.cell(cell.row, 2).value == entry_id:
                    comments_ws.delete_rows(cell.row)
    st.cache_data.clear()  # キャッシュをクリア

# 夜の投稿を削除
def delete_evening_entry(entry_id):
    spreadsheet = init_gspread()
    worksheet = spreadsheet.worksheet("entries")
    
    cell = worksheet.find(entry_id)
    if cell:
        row = cell.row
        morning_stamp = worksheet.cell(row, 4).value
        
        if morning_stamp:  # 朝の投稿がある場合は夜のデータだけクリア
            worksheet.update_cell(row, 7, '')  # evening_stamp_emoji
            worksheet.update_cell(row, 8, '')  # evening_stamp_label
            worksheet.update_cell(row, 9, '')  # evening_diary_text
            worksheet.update_cell(row, 10, '')  # image_data
            worksheet.update_cell(row, 13, datetime.now().isoformat())  # updated_at
        else:  # 朝の投稿もない場合はエントリー全体を削除
            worksheet.delete_rows(row)
            # コメントも削除
            comments_ws = spreadsheet.worksheet("comments")
            cells = comments_ws.findall(entry_id)
            for cell in reversed(cells):
                if comments_ws.cell(cell.row, 2).value == entry_id:
                    comments_ws.delete_rows(cell.row)
    st.cache_data.clear()  # キャッシュをクリア

# データベースをリセット
def reset_database():
    spreadsheet = init_gspread()
    
    # entriesシートをクリア（ヘッダーは残す）
    entries_ws = spreadsheet.worksheet("entries")
    entries_ws.resize(rows=1)
    entries_ws.resize(rows=1000)
    
    # commentsシートをクリア
    comments_ws = spreadsheet.worksheet("comments")
    comments_ws.resize(rows=1)
    comments_ws.resize(rows=1000)
    
    st.cache_data.clear()  # キャッシュをクリア

# 初期化
if 'initialized' not in st.session_state:
    init_database()
    st.session_state.initialized = True
    st.session_state.current_user = None
    st.session_state.tab = "home"
    st.session_state.screen = "main"
    st.session_state.cal_month = get_today_jst()
    st.session_state.last_date = get_today_jst().isoformat()

# 日付が変わったらキャッシュをクリア
current_date = get_today_jst().isoformat()
if st.session_state.get('last_date') != current_date:
    st.cache_data.clear()
    st.session_state.last_date = current_date

try:
    settings = load_settings()
    entries = load_entries(_date_key=get_today_jst().isoformat())
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.info("Googleスプレッドシートの設定を確認してください")
    st.stop()

# ユーザー選択画面
if st.session_state.current_user is None:
    st.markdown("<h1 style='text-align: center; font-size: 52px !important;'>📔</h1>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>ふたりの日記</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>あなたはどちらですか?</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(f"{settings['user_a_avatar']} {settings['user_a_name']}として使う", use_container_width=True):
            st.session_state.current_user = "A"
            st.rerun()
        
        if st.button(f"{settings['user_b_avatar']} {settings['user_b_name']}として使う", use_container_width=True):
            st.session_state.current_user = "B"
            st.rerun()
    
    st.stop()

# メインアプリ
user_key = "user_a" if st.session_state.current_user == "A" else "user_b"
partner_key = "user_b" if st.session_state.current_user == "A" else "user_a"
me = {"id": st.session_state.current_user, "name": settings[f"{user_key}_name"], "avatar": settings[f"{user_key}_avatar"]}
partner = {"id": "A" if st.session_state.current_user == "B" else "B", "name": settings[f"{partner_key}_name"], "avatar": settings[f"{partner_key}_avatar"]}

# 未読コメント数
unread_count = get_unread_comments_count(st.session_state.current_user, entries)

# ============================================
# 朝の投稿画面
# ============================================
if st.session_state.get('screen') == 'post_morning':
    if st.button("← 戻る", key="back_from_morning_post"):
        if 'selected_morning_stamp' in st.session_state:
            del st.session_state.selected_morning_stamp
        st.session_state.screen = 'main'
        st.rerun()
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f472b6, #ec4899); padding: 14px 18px; border-radius: 10px; margin: 0 0 10px;'>
        <div style='color: white; font-weight: 800; font-size: 16px;'>☀️ 朝の体調報告</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### スタンプを選択")
    
    # 2行4列でスタンプを表示
    for row in range(2):
        cols = st.columns(4)
        for col in range(4):
            i = row * 4 + col
            if i < len(CONDITION_STAMPS):
                stamp = CONDITION_STAMPS[i]
                with cols[col]:
                    if st.button(f"{stamp['emoji']}\n{stamp['label']}", key=f"morning_{i}", use_container_width=True):
                        st.session_state.selected_morning_stamp = stamp
    
    if 'selected_morning_stamp' in st.session_state:
        st.success(f"選択中: {st.session_state.selected_morning_stamp['emoji']} {st.session_state.selected_morning_stamp['label']}")
        message = st.text_input(f"💬 {partner['name']}へひとこと(任意)", max_chars=60, key="morning_msg")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("投稿する", type="primary", use_container_width=True):
                morning_data = {"stamp": st.session_state.selected_morning_stamp, "message": message}
                save_entry(st.session_state.current_user, get_today_jst().isoformat(), morning=morning_data)
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

# ============================================
# 夜の投稿画面
# ============================================
elif st.session_state.get('screen') == 'post_evening':
    if st.button("← 戻る", key="back_from_evening_post"):
        if 'selected_evening_stamp' in st.session_state:
            del st.session_state.selected_evening_stamp
        st.session_state.screen = 'main'
        st.rerun()
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f472b6, #ec4899); padding: 14px 18px; border-radius: 10px; margin: 0 0 10px;'>
        <div style='color: white; font-weight: 800; font-size: 16px;'>🌙 今日の日記</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 今日の気分")
    
    cols = st.columns(4)
    for i, stamp in enumerate(MOOD_STAMPS):
        with cols[i % 4]:
            if st.button(f"{stamp['emoji']}\n{stamp['label']}", key=f"evening_{i}", use_container_width=True):
                st.session_state.selected_evening_stamp = stamp
    
    if 'selected_evening_stamp' in st.session_state:
        st.success(f"選択中: {st.session_state.selected_evening_stamp['emoji']} {st.session_state.selected_evening_stamp['label']}")
        
        st.markdown("### 今日の出来事")
        diary_text = st.text_area("日記を書く", height=150, max_chars=500, key="diary_text", placeholder="今日はどんな日だった?")
        
        # 画像アップロード
        uploaded_file = st.file_uploader("📷 写真を追加（任意）", type=["jpg", "jpeg", "png", "heic", "heif"], key="photo")
        image_data = None
        if uploaded_file:
            try:
                image_data, preview_image = process_image_for_storage(uploaded_file)
                st.image(preview_image, use_container_width=True)
                st.caption(f"画像サイズ: {len(image_data):,} 文字（上限45,000）")
            except Exception as e:
                st.error(f"画像の処理に失敗しました: {e}")
                image_data = None
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("投稿する", type="primary", use_container_width=True):
                if diary_text.strip():
                    evening_data = {"stamp": st.session_state.selected_evening_stamp, "diary_text": diary_text}
                    save_entry(st.session_state.current_user, get_today_jst().isoformat(), evening=evening_data, image_data=image_data)
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

# ============================================
# 朝の編集画面
# ============================================
elif st.session_state.get('screen') == 'edit_morning':
    if st.button("← 戻る", key="back_from_morning_edit"):
        if 'selected_morning_stamp' in st.session_state:
            del st.session_state.selected_morning_stamp
        if 'edit_entry_id' in st.session_state:
            del st.session_state.edit_entry_id
        st.session_state.screen = 'main'
        st.rerun()
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f472b6, #ec4899); padding: 14px 18px; border-radius: 10px; margin: 0 0 10px;'>
        <div style='color: white; font-weight: 800; font-size: 16px;'>✏️ 朝の体調を編集</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    entry_id = st.session_state.get('edit_entry_id')
    current_entry = entries[entries['id'] == entry_id].iloc[0]
    
    st.markdown("### スタンプを選択")
    # 2行4列でスタンプを表示
    for row in range(2):
        cols = st.columns(4)
        for col in range(4):
            i = row * 4 + col
            if i < len(CONDITION_STAMPS):
                stamp = CONDITION_STAMPS[i]
                with cols[col]:
                    if st.button(f"{stamp['emoji']}\n{stamp['label']}", key=f"edit_morning_{i}", use_container_width=True):
                        st.session_state.selected_morning_stamp = stamp
    
    if 'selected_morning_stamp' not in st.session_state and pd.notna(current_entry['morning_stamp_emoji']):
        for stamp in CONDITION_STAMPS:
            if stamp['emoji'] == current_entry['morning_stamp_emoji']:
                st.session_state.selected_morning_stamp = stamp
                break
    
    if 'selected_morning_stamp' in st.session_state:
        st.success(f"選択中: {st.session_state.selected_morning_stamp['emoji']} {st.session_state.selected_morning_stamp['label']}")
        
        default_msg = str(current_entry['morning_message']) if pd.notna(current_entry['morning_message']) else ""
        message = st.text_input(f"💬 {partner['name']}へひとこと(任意)", max_chars=60, key="edit_morning_msg", value=default_msg)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("更新する", type="primary", use_container_width=True):
                morning_data = {"stamp": st.session_state.selected_morning_stamp, "message": message}
                save_entry(st.session_state.current_user, str(current_entry['entry_date']), morning=morning_data)
                st.success("朝の投稿を更新しました!")
                del st.session_state.selected_morning_stamp
                del st.session_state.edit_entry_id
                st.session_state.screen = 'main'
                st.rerun()
        with col2:
            if st.button("削除する", use_container_width=True):
                delete_morning_entry(entry_id)
                st.success("朝の投稿を削除しました!")
                if 'selected_morning_stamp' in st.session_state:
                    del st.session_state.selected_morning_stamp
                if 'edit_entry_id' in st.session_state:
                    del st.session_state.edit_entry_id
                st.session_state.screen = 'main'
                st.rerun()
        with col3:
            if st.button("キャンセル", use_container_width=True):
                if 'selected_morning_stamp' in st.session_state:
                    del st.session_state.selected_morning_stamp
                if 'edit_entry_id' in st.session_state:
                    del st.session_state.edit_entry_id
                st.session_state.screen = 'main'
                st.rerun()
    st.stop()

# ============================================
# 夜の編集画面
# ============================================
elif st.session_state.get('screen') == 'edit_evening':
    if st.button("← 戻る", key="back_from_evening_edit"):
        if 'selected_evening_stamp' in st.session_state:
            del st.session_state.selected_evening_stamp
        if 'edit_entry_id' in st.session_state:
            del st.session_state.edit_entry_id
        st.session_state.screen = 'main'
        st.rerun()
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f472b6, #ec4899); padding: 14px 18px; border-radius: 10px; margin: 0 0 10px;'>
        <div style='color: white; font-weight: 800; font-size: 16px;'>✏️ 夜の日記を編集</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    entry_id = st.session_state.get('edit_entry_id')
    current_entry = entries[entries['id'] == entry_id].iloc[0]
    
    st.markdown("### 今日の気分")
    cols = st.columns(4)
    for i, stamp in enumerate(MOOD_STAMPS):
        with cols[i % 4]:
            if st.button(f"{stamp['emoji']}\n{stamp['label']}", key=f"edit_evening_{i}", use_container_width=True):
                st.session_state.selected_evening_stamp = stamp
    
    if 'selected_evening_stamp' not in st.session_state and pd.notna(current_entry['evening_stamp_emoji']):
        for stamp in MOOD_STAMPS:
            if stamp['emoji'] == current_entry['evening_stamp_emoji']:
                st.session_state.selected_evening_stamp = stamp
                break
    
    if 'selected_evening_stamp' in st.session_state:
        st.success(f"選択中: {st.session_state.selected_evening_stamp['emoji']} {st.session_state.selected_evening_stamp['label']}")
        
        default_diary = str(current_entry['evening_diary_text']) if pd.notna(current_entry['evening_diary_text']) else ""
        diary_text = st.text_area("日記を書く", height=150, max_chars=500, key="edit_diary_text", value=default_diary)
        
        if pd.notna(current_entry.get('image_data')) and current_entry.get('image_data'):
            st.markdown("**現在の写真:**")
            st.image(f"data:image/jpeg;base64,{current_entry['image_data']}", use_container_width=True)
        
        uploaded_file = st.file_uploader("📷 写真を変更（任意）", type=["jpg", "jpeg", "png", "heic", "heif"], key="edit_photo")
        image_data = None
        if uploaded_file:
            try:
                image_data, preview_image = process_image_for_storage(uploaded_file)
                st.image(preview_image, use_container_width=True)
                st.caption(f"画像サイズ: {len(image_data):,} 文字（上限45,000）")
            except Exception as e:
                st.error(f"画像の処理に失敗しました: {e}")
                image_data = None
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("更新する", type="primary", use_container_width=True):
                if diary_text.strip():
                    evening_data = {"stamp": st.session_state.selected_evening_stamp, "diary_text": diary_text}
                    save_entry(st.session_state.current_user, str(current_entry['entry_date']), evening=evening_data, image_data=image_data)
                    st.success("夜の日記を更新しました!")
                    del st.session_state.selected_evening_stamp
                    del st.session_state.edit_entry_id
                    st.session_state.screen = 'main'
                    st.rerun()
                else:
                    st.warning("日記を書いてください")
        with col2:
            if st.button("削除する", use_container_width=True):
                delete_evening_entry(entry_id)
                st.success("夜の日記を削除しました!")
                if 'selected_evening_stamp' in st.session_state:
                    del st.session_state.selected_evening_stamp
                if 'edit_entry_id' in st.session_state:
                    del st.session_state.edit_entry_id
                st.session_state.screen = 'main'
                st.rerun()
        with col3:
            if st.button("キャンセル", use_container_width=True):
                if 'selected_evening_stamp' in st.session_state:
                    del st.session_state.selected_evening_stamp
                if 'edit_entry_id' in st.session_state:
                    del st.session_state.edit_entry_id
                st.session_state.screen = 'main'
                st.rerun()
    st.stop()

# ============================================
# メイン画面（通常のタブ表示）
# ============================================

# ヘッダー
badge_html = f"<span class='badge'>{unread_count}</span>" if unread_count > 0 else ""
st.markdown(f"""
<div class='header-container'>
    <div class='header-flex'>
        <div class='header-avatar'>{me['avatar']}</div>
        <div class='header-text'>
            <div class='header-title'>📔 ふたりの日記</div>
            <div class='header-subtitle'>{me['name']} と {partner['name']}</div>
        </div>
        {badge_html}
    </div>
</div>
""", unsafe_allow_html=True)

# タブナビゲーション（常に横並び）
st.markdown('<div class="tab-navigation">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🏠 ホーム", key="tab_home", use_container_width=True):
        st.session_state.tab = "home"
        st.rerun()
with col2:
    if st.button("📅 カレンダー", key="tab_calendar", use_container_width=True):
        st.session_state.tab = "calendar"
        st.rerun()
with col3:
    if st.button("📖 履歴", key="tab_history", use_container_width=True):
        st.session_state.tab = "history"
        st.rerun()
with col4:
    if st.button("⚙️ 設定", key="tab_settings", use_container_width=True):
        st.session_state.tab = "settings"
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ============================================
# ホームタブ
# ============================================
if st.session_state.tab == "home":
    today_str = get_today_jst().isoformat()
    
    # 統計表示
    col1, col2 = st.columns(2)
    
    with col1:
        if settings.get('anniversary'):
            try:
                anniv_date = datetime.strptime(settings['anniversary'], "%Y-%m-%d").date()
                days_since = (get_today_jst() - anniv_date).days + 1
                st.markdown(f"""
                <div class='stat-box'>
                    <div style='font-size: 22px;'>💑</div>
                    <div style='font-size: 22px; font-weight: 800; color: #ec4899;'>{days_since}</div>
                    <div style='font-size: 10px; color: #888;'>日目</div>
                </div>
                """, unsafe_allow_html=True)
            except:
                pass
    
    with col2:
        streak = calculate_streak(entries)
        st.markdown(f"""
        <div class='stat-box'>
            <div style='font-size: 22px;'>🔥</div>
            <div style='font-size: 22px; font-weight: 800; color: #ec4899;'>{streak}</div>
            <div style='font-size: 10px; color: #888;'>日連続</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 2カラムレイアウト
    col_me, col_partner = st.columns(2)
    
    # 自分の今日のエントリー
    with col_me:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"### 📅 今日 — {me['avatar']} {me['name']}")
        
        today_entries = entries[entries['entry_date'] == today_str] if not entries.empty else pd.DataFrame()
        my_today = today_entries[today_entries['user_id'] == st.session_state.current_user] if not today_entries.empty else pd.DataFrame()
        
        has_morning = not my_today.empty and pd.notna(my_today.iloc[0]['morning_stamp_emoji']) if not my_today.empty else False
        has_evening = not my_today.empty and pd.notna(my_today.iloc[0]['evening_stamp_emoji']) if not my_today.empty else False
        
        if has_morning:
            entry = my_today.iloc[0]
            st.markdown(f"**☀️ 朝:** {entry['morning_stamp_emoji']} {entry['morning_stamp_label']}")
            if pd.notna(entry['morning_message']) and str(entry['morning_message']):
                st.markdown(f"💬 {entry['morning_message']}")
            if st.button("編集", key="edit_my_morning", use_container_width=True):
                st.session_state.edit_entry_id = entry['id']
                st.session_state.screen = 'edit_morning'
                st.rerun()
        else:
            if st.button("☀️ 朝の投稿", use_container_width=True):
                st.session_state.screen = 'post_morning'
                st.rerun()
        
        st.markdown("---")
        
        if has_evening:
            entry = my_today.iloc[0]
            st.markdown(f"**🌙 夜:** {entry['evening_stamp_emoji']} {entry['evening_stamp_label']}")
            st.markdown(entry['evening_diary_text'])
            
            if pd.notna(entry.get('image_data')) and str(entry.get('image_data')):
                st.image(f"data:image/jpeg;base64,{entry['image_data']}", use_container_width=True)
            
            if st.button("編集", key="edit_my_evening", use_container_width=True):
                st.session_state.edit_entry_id = entry['id']
                st.session_state.screen = 'edit_evening'
                st.rerun()
        else:
            if st.button("🌙 夜の投稿", use_container_width=True):
                st.session_state.screen = 'post_evening'
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # パートナーの今日のエントリー
    with col_partner:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"### 📅 今日 — {partner['avatar']} {partner['name']}")
        
        partner_today = today_entries[today_entries['user_id'] == partner['id']] if not today_entries.empty else pd.DataFrame()
        
        if not partner_today.empty:
            entry = partner_today.iloc[0]
            entry_id = entry['id']
            
            is_fav = int(entry.get('is_favorite', 0)) == 1
            fav_label = "❤️ お気に入り解除" if is_fav else "🤍 お気に入りに追加"
            if st.button(fav_label, key=f"fav_{entry_id}", use_container_width=True):
                toggle_favorite(entry_id)
                st.rerun()
            
            if pd.notna(entry['morning_stamp_emoji']):
                st.markdown(f"**☀️ 朝:** {entry['morning_stamp_emoji']} {entry['morning_stamp_label']}")
                if pd.notna(entry['morning_message']) and str(entry['morning_message']):
                    st.markdown(f"💬 {entry['morning_message']}")
            else:
                st.info("まだ朝の投稿がありません 🌅")
            
            st.markdown("---")
            
            if pd.notna(entry['evening_stamp_emoji']):
                st.markdown(f"**🌙 夜:** {entry['evening_stamp_emoji']} {entry['evening_stamp_label']}")
                st.markdown(entry['evening_diary_text'])
                
                if pd.notna(entry.get('image_data')) and str(entry.get('image_data')):
                    st.image(f"data:image/jpeg;base64,{entry['image_data']}", use_container_width=True)
                
                st.markdown("---")
                st.markdown("**💬 コメント**")
                comments = load_comments(entry_id)
                if comments:
                    for comment in comments:
                        if len(comment) >= 5:
                            comment_id, _, comment_user_id, comment_text, created_at = comment[0], comment[1], comment[2], comment[3], comment[4]
                            comment_user = me if comment_user_id == st.session_state.current_user else partner
                            
                            st.markdown(f"""
                            <div class='comment-box'>
                                <div style='font-size: 11px; color: #888; margin-bottom: 4px;'>{comment_user['avatar']} {comment_user['name']} • {created_at[:10]}</div>
                                <div style='font-size: 13px;'>{comment_text}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if comment_user_id == st.session_state.current_user:
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("編集", key=f"edit_comment_{comment_id}", use_container_width=True):
                                        st.session_state.edit_comment_id = comment_id
                                        st.session_state.edit_comment_text = comment_text
                                        st.rerun()
                                with col2:
                                    if st.button("削除", key=f"delete_comment_{comment_id}", use_container_width=True):
                                        delete_comment(comment_id)
                                        st.success("コメントを削除しました!")
                                        st.rerun()
                
                if st.session_state.get('edit_comment_id'):
                    st.markdown("---")
                    st.markdown("**コメントを編集**")
                    edit_text = st.text_input(
                        "コメント", 
                        value=st.session_state.get('edit_comment_text', ''),
                        key="edit_comment_input",
                        max_chars=200
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("更新", key="update_comment", use_container_width=True):
                            if edit_text.strip():
                                update_comment(st.session_state.edit_comment_id, edit_text)
                                del st.session_state.edit_comment_id
                                del st.session_state.edit_comment_text
                                st.success("コメントを更新しました!")
                                st.rerun()
                    with col2:
                        if st.button("キャンセル", key="cancel_edit_comment", use_container_width=True):
                            del st.session_state.edit_comment_id
                            del st.session_state.edit_comment_text
                            st.rerun()
                else:
                    st.markdown("---")
                    
                    counter_key = f"comment_counter_{entry_id}"
                    if counter_key not in st.session_state:
                        st.session_state[counter_key] = 0
                    
                    comment_text = st.text_input(
                        f"💬 {partner['name']}にコメント", 
                        key=f"comment_input_{entry_id}_{st.session_state[counter_key]}",
                        max_chars=200, 
                        placeholder="優しいコメントを残そう..."
                    )
                    
                    if st.button("送信", key=f"send_{entry_id}", use_container_width=True):
                        if comment_text.strip():
                            add_comment(entry_id, st.session_state.current_user, comment_text)
                            st.session_state[counter_key] += 1
                            st.success("コメントを送信しました!")
                            st.rerun()
            else:
                st.info("まだ夜の投稿がありません 🌙")
        else:
            st.info(f"{partner['name']}はまだ投稿していません 🌿")
        
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================
# ============================================
# カレンダータブ（スマホ完全対応版）
# ============================================
elif st.session_state.tab == "calendar":
    st.markdown("### 📅 カレンダー")
    
    # 色の説明
    st.markdown("""
    <div style='display: flex; gap: 8px; font-size: 9px; margin-bottom: 10px; flex-wrap: wrap;'>
        <span style='background: #fef3c7; border: 2px solid #f59e0b; padding: 2px 6px; border-radius: 3px;'>今日</span>
        <span style='background: #fce7f3; border: 2px solid #f472b6; padding: 2px 6px; border-radius: 3px;'>投稿あり</span>
        <span style='background: #f9fafb; border: 1px solid #e5e7eb; padding: 2px 6px; border-radius: 3px;'>通常</span>
    </div>
    """, unsafe_allow_html=True)
    
    # 月移動ボタン
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ 前月", key="prev_month", use_container_width=True):
            st.session_state.cal_month = st.session_state.cal_month.replace(day=1) - timedelta(days=1)
            st.rerun()
    with col2:
        st.markdown(f"<div style='text-align: center; font-weight: 800; color: #ec4899; font-size: 16px; padding: 8px;'>{st.session_state.cal_month.strftime('%Y年%m月')}</div>", unsafe_allow_html=True)
    with col3:
        if st.button("次月 ▶", key="next_month", use_container_width=True):
            st.session_state.cal_month = (st.session_state.cal_month.replace(day=28) + timedelta(days=4)).replace(day=1)
            st.rerun()
    
    st.markdown("---")
    
    # 今月のエントリーを取得
    calendar.setfirstweekday(calendar.SUNDAY)  # 日曜日始まり（日本標準）
    cal = calendar.monthcalendar(st.session_state.cal_month.year, st.session_state.cal_month.month)
    
    # カレンダーHTMLを構築（CSS Grid使用）
    calendar_html = """
    <style>
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 2px;
        width: 100%;
        margin: 0 auto;
    }
    .calendar-header {
        text-align: center;
        font-size: 9px;
        font-weight: 600;
        padding: 4px 0;
    }
    .calendar-cell {
        aspect-ratio: 1;
        display: flex;
        justify-content: center;
        align-items: center;
        border-radius: 3px;
        font-size: 10px;
    }
    </style>
    <div class="calendar-grid">
    """
    
    # 曜日ヘッダー
    days_of_week = ["日", "月", "火", "水", "木", "金", "土"]
    for i, day_name in enumerate(days_of_week):
        color = "#f87171" if i == 0 else "#3b82f6" if i == 6 else "#666"
        calendar_html += f'<div class="calendar-header" style="color: {color};">{day_name}</div>'
    
    # 日付セル
    for week in cal:
        for i, day in enumerate(week):
            if day == 0:
                calendar_html += '<div class="calendar-cell" style="background: transparent;"></div>'
            else:
                day_date = date(st.session_state.cal_month.year, st.session_state.cal_month.month, day)
                day_str = day_date.isoformat()
                day_entries = entries[entries['entry_date'] == day_str] if not entries.empty else pd.DataFrame()
                
                is_today = day_date == get_today_jst()
                has_entries = not day_entries.empty
                
                # 日付の色
                day_color = "#dc2626" if i == 0 else "#2563eb" if i == 6 else "#374151"
                
                # セルの色
                if is_today:
                    bg_color = "#fef3c7"
                    border = "2px solid #f59e0b"
                    font_weight = "700"
                elif has_entries:
                    bg_color = "#fce7f3"
                    border = "2px solid #f472b6"
                    font_weight = "600"
                else:
                    bg_color = "#f9fafb"
                    border = "1px solid #e5e7eb"
                    font_weight = "400"
                
                cell_style = f"background: {bg_color}; border: {border}; color: {day_color}; font-weight: {font_weight};"
                calendar_html += f'<div class="calendar-cell" style="{cell_style}">{day}</div>'
    
    calendar_html += "</div>"
    
    st.markdown(calendar_html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 今月の概要
    month_entries = entries[pd.to_datetime(entries['entry_date']).dt.month == st.session_state.cal_month.month] if not entries.empty else pd.DataFrame()
    month_entries = month_entries[pd.to_datetime(month_entries['entry_date']).dt.year == st.session_state.cal_month.year] if not month_entries.empty else pd.DataFrame()
    
    if not month_entries.empty:
        st.markdown(f"**📊 今月の記録: {len(month_entries)}日**")
        
        # 最近のエントリーを3件表示
        st.markdown("**最近の日記:**")
        for _, entry in month_entries.head(3).iterrows():
            user = me if entry['user_id'] == st.session_state.current_user else partner
            entry_date = entry['entry_date']
            
            with st.expander(f"{user['avatar']} {entry_date} - {user['name']}"):
                if pd.notna(entry['morning_stamp_emoji']):
                    st.markdown(f"☀️ {entry['morning_stamp_emoji']} {entry['morning_stamp_label']}")
                if pd.notna(entry['evening_stamp_emoji']):
                    st.markdown(f"🌙 {entry['evening_stamp_emoji']} {entry['evening_stamp_label']}")
                    if pd.notna(entry['evening_diary_text']):
                        st.markdown(f"_{entry['evening_diary_text'][:50]}..._" if len(str(entry['evening_diary_text'])) > 50 else entry['evening_diary_text'])
    else:
        st.info("今月はまだ投稿がありません")


elif st.session_state.tab == "history":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 📖 履歴")
    
    search_query = st.text_input("🔍 検索", placeholder="日記を検索...", key="search")
    
    col1, col2 = st.columns(2)
    with col1:
        filter_user = st.selectbox("ユーザー", ["すべて", me['name'], partner['name']])
    with col2:
        filter_type = st.selectbox("種類", ["すべて", "お気に入りのみ"])
    
    if not entries.empty:
        filtered_entries = entries.copy()
        
        if search_query:
            filtered_entries = filtered_entries[
                filtered_entries['evening_diary_text'].astype(str).str.contains(search_query, na=False, case=False) |
                filtered_entries['morning_message'].astype(str).str.contains(search_query, na=False, case=False)
            ]
        
        if filter_user != "すべて":
            filter_user_id = me['id'] if filter_user == me['name'] else partner['id']
            filtered_entries = filtered_entries[filtered_entries['user_id'] == filter_user_id]
        
        if filter_type == "お気に入りのみ":
            filtered_entries = filtered_entries[filtered_entries['is_favorite'] == 1]
        
        if filtered_entries.empty:
            st.info("該当する日記が見つかりませんでした")
        else:
            st.markdown(f"**{len(filtered_entries)}件の日記**")
            
            for _, entry in filtered_entries.head(30).iterrows():
                user = me if entry['user_id'] == st.session_state.current_user else partner
                is_fav = int(entry.get('is_favorite', 0)) == 1
                fav_icon = " ❤️" if is_fav else ""
                
                comments_count = len(load_comments(entry['id']))
                comment_badge = f" 💬 {comments_count}" if comments_count > 0 else ""
                
                with st.expander(f"{user['avatar']} {user['name']} - {entry['entry_date']}{fav_icon}{comment_badge}"):
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
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================
# 設定タブ
# ============================================
elif st.session_state.tab == "settings":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 📊 統計")
    
    stats = get_statistics(entries)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総投稿数", stats['total_entries'])
    with col2:
        st.metric("今月の投稿", stats['this_month'])
    with col3:
        st.metric("連続投稿", f"{stats['streak']}日")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### ⚙️ 設定")
    
    with st.form("settings_form"):
        user_a_name = st.text_input("ユーザーA の名前", value=settings['user_a_name'])
        user_a_avatar = st.text_input("ユーザーA のアバター", value=settings['user_a_avatar'])
        user_b_name = st.text_input("ユーザーB の名前", value=settings['user_b_name'])
        user_b_avatar = st.text_input("ユーザーB のアバター", value=settings['user_b_avatar'])
        
        anniversary = st.date_input("記念日", value=datetime.strptime(settings['anniversary'], "%Y-%m-%d").date() if settings.get('anniversary') else None)
        
        if st.form_submit_button("保存", use_container_width=True):
            new_settings = {
                "user_a_name": user_a_name,
                "user_a_avatar": user_a_avatar,
                "user_b_name": user_b_name,
                "user_b_avatar": user_b_avatar,
                "anniversary": anniversary.isoformat() if anniversary else ""
            }
            save_settings(new_settings)
            st.success("設定を保存しました!")
            st.rerun()
    
    st.markdown("---")
    
    if st.button("ユーザーを切り替える", use_container_width=True):
        st.session_state.current_user = None
        st.rerun()
    
    st.markdown("---")
    
    st.warning("⚠️ 危険: すべての投稿とコメントが削除されます")
    if st.button("履歴をリセット", use_container_width=True, type="secondary"):
        reset_database()
        st.success("履歴をリセットしました!")
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
