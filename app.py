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

# 日本時間(JST)の定義
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

# カスタムCSS（スマホ完全対応版）v1.1
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
    .notification-badge {
        background: #ef4444;
        color: white;
        border-radius: 16px;
        padding: 6px 12px;
        font-size: 12px;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 4px;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
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
    
    /* タブナビゲーション v1.1 - 統一サイズ */
    .tab-nav-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 6px;
        width: 100%;
        margin-bottom: 8px;
    }
    .tab-nav-item {
        aspect-ratio: 1;
        display: flex;
        justify-content: center;
        align-items: center;
        border-radius: 16px;
        font-size: 11px;
        font-weight: 700;
        transition: all 0.3s ease;
        background: #f9fafb;
        border: 2px solid #e5e7eb;
        color: #9ca3af;
        flex-direction: column;
        gap: 4px;
        padding: 8px;
        text-align: center;
        line-height: 1.2;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        box-sizing: border-box;
    }
    .tab-nav-item.active {
        background: linear-gradient(135deg, #f472b6, #ec4899);
        color: white;
        border-color: #ec4899;
        box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3);
    }
    .tab-nav-emoji {
        font-size: 24px;
        line-height: 1;
    }
    .tab-nav-item.active .tab-nav-emoji {
        opacity: 1;
    }
    .tab-nav-label {
        font-size: 10px;
        font-weight: 600;
        line-height: 1;
    }
    
    /* 隠しボタングリッド */
    .tab-btn-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 6px;
        margin-top: -8px;
        margin-bottom: 8px;
    }
    .tab-btn-container .stButton {
        aspect-ratio: 1;
    }
    .tab-btn-container .stButton > button {
        height: 100%;
        width: 100%;
        opacity: 0.01;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        min-height: 0 !important;
    }
    
    @media (max-width: 320px) {
        .tab-nav-emoji {
            font-size: 20px;
        }
        .tab-nav-label {
            font-size: 9px;
        }
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
    {"emoji": "😮", "label": "驚き"},
    {"emoji": "😢", "label": "悲しい"},
]

def get_current_user():
    """現在ログイン中のユーザーを取得"""
    if 'current_user' not in st.session_state:
        st.session_state.current_user = 'A'
    return st.session_state.current_user

def switch_user():
    """ユーザーを切り替え"""
    st.session_state.current_user = 'B' if get_current_user() == 'A' else 'A'


def init_gspread():
    """Google Sheetsに接続"""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 認証情報を辞書形式で取得
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # スプレッドシートを開く
    spreadsheet_id = "1z2R2Da4CxP4U3Spboz5_R9tkrahgTwGukWaGXjIdjSg"
    return client.open_by_key(spreadsheet_id)


@st.cache_data(ttl=300)
def load_entries(_date_key=None):
    """Google Sheetsからエントリーを読み込み（キャッシュ5分）"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('entries')
        data = worksheet.get_all_records()
        
        if not data:
            return pd.DataFrame(columns=[
                'id', 'user_id', 'entry_date', 'morning_stamp_emoji', 'morning_stamp_label',
                'morning_message', 'evening_stamp_emoji', 'evening_stamp_label',
                'evening_diary_text', 'image_data', 'is_favorite', 'created_at', 'updated_at'
            ])
        
        df = pd.DataFrame(data)
        
        # 日付をdate型に変換
        if 'entry_date' in df.columns:
            df['entry_date'] = pd.to_datetime(df['entry_date']).dt.date
        
        # booleanに変換
        if 'is_favorite' in df.columns:
            df['is_favorite'] = df['is_favorite'].astype(str).str.upper() == 'TRUE'
        
        return df
        
    except Exception as e:
        st.error(f"エントリー読み込みエラー: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_settings():
    """Google Sheetsから設定を読み込み（キャッシュ5分）"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('settings')
        data = worksheet.get_all_records()
        
        settings = {}
        for row in data:
            settings[row['key']] = row['value']
        
        # デフォルト値
        defaults = {
            'user_a_name': 'ユーザーA',
            'user_a_avatar': '👦',
            'user_b_name': 'ユーザーB',
            'user_b_avatar': '👧',
            'anniversary': str(date.today())
        }
        
        for key, value in defaults.items():
            if key not in settings:
                settings[key] = value
        
        return settings
    except Exception as e:
        st.error(f"設定読み込みエラー: {e}")
        return {
            'user_a_name': 'ユーザーA',
            'user_a_avatar': '👦',
            'user_b_name': 'ユーザーB',
            'user_b_avatar': '👧',
            'anniversary': str(date.today())
        }


def load_comments():
    """Google Sheetsからコメントを読み込み"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('comments')
        data = worksheet.get_all_records()
        
        if not data:
            return pd.DataFrame(columns=['id', 'entry_id', 'user_id', 'comment_text', 'created_at'])
        
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"コメント読み込みエラー: {e}")
        return pd.DataFrame()


def save_entry(user_id, entry_date, morning_stamp_emoji=None, morning_stamp_label=None, 
               morning_message=None, evening_stamp_emoji=None, evening_stamp_label=None,
               evening_diary_text=None, image_data=None):
    """エントリーを保存または更新"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('entries')
        
        # 既存のエントリーをチェック
        all_data = worksheet.get_all_records()
        df = pd.DataFrame(all_data)
        
        entry_date_str = entry_date.isoformat()
        
        if not df.empty and 'entry_date' in df.columns:
            existing = df[(df['user_id'] == user_id) & (df['entry_date'] == entry_date_str)]
        else:
            existing = pd.DataFrame()
        
        now = datetime.now(JST).isoformat()
        
        if not existing.empty:
            # 既存エントリーを更新
            row_index = existing.index[0] + 2  # ヘッダー行を考慮
            
            # 既存の値を取得
            current_values = worksheet.row_values(row_index)
            
            # 列インデックス（1-indexed）
            col_map = {
                'morning_stamp_emoji': 4,
                'morning_stamp_label': 5,
                'morning_message': 6,
                'evening_stamp_emoji': 7,
                'evening_stamp_label': 8,
                'evening_diary_text': 9,
                'image_data': 10,
                'updated_at': 13
            }
            
            # 値が指定されている項目のみ更新
            updates = []
            if morning_stamp_emoji is not None:
                updates.append({'range': f'D{row_index}', 'values': [[morning_stamp_emoji]]})
            if morning_stamp_label is not None:
                updates.append({'range': f'E{row_index}', 'values': [[morning_stamp_label]]})
            if morning_message is not None:
                updates.append({'range': f'F{row_index}', 'values': [[morning_message]]})
            if evening_stamp_emoji is not None:
                updates.append({'range': f'G{row_index}', 'values': [[evening_stamp_emoji]]})
            if evening_stamp_label is not None:
                updates.append({'range': f'H{row_index}', 'values': [[evening_stamp_label]]})
            if evening_diary_text is not None:
                updates.append({'range': f'I{row_index}', 'values': [[evening_diary_text]]})
            if image_data is not None:
                updates.append({'range': f'J{row_index}', 'values': [[image_data]]})
            
            # 更新日時は常に更新
            updates.append({'range': f'M{row_index}', 'values': [[now]]})
            
            worksheet.batch_update(updates)
            
        else:
            # 新規エントリーを追加
            entry_id = str(uuid.uuid4())
            
            new_row = [
                entry_id,
                user_id,
                entry_date_str,
                morning_stamp_emoji or '',
                morning_stamp_label or '',
                morning_message or '',
                evening_stamp_emoji or '',
                evening_stamp_label or '',
                evening_diary_text or '',
                image_data or '',
                'FALSE',  # is_favorite
                now,  # created_at
                now   # updated_at
            ]
            
            worksheet.append_row(new_row)
        
        # キャッシュをクリア
        st.cache_data.clear()
        
        return True
    except Exception as e:
        st.error(f"保存エラー: {e}")
        return False


def delete_morning_entry(user_id, entry_date):
    """朝スタンプとメッセージを削除"""
    return save_entry(
        user_id, entry_date,
        morning_stamp_emoji='',
        morning_stamp_label='',
        morning_message=''
    )


def delete_evening_entry(user_id, entry_date):
    """夜スタンプ、日記、画像を削除"""
    return save_entry(
        user_id, entry_date,
        evening_stamp_emoji='',
        evening_stamp_label='',
        evening_diary_text='',
        image_data=''
    )


def add_comment(entry_id, user_id, comment_text):
    """コメントを追加"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('comments')
        
        comment_id = str(uuid.uuid4())
        now = datetime.now(JST).isoformat()
        
        new_row = [comment_id, entry_id, user_id, comment_text, now]
        worksheet.append_row(new_row)
        
        # キャッシュをクリア
        st.cache_data.clear()
        
        return True
    except Exception as e:
        st.error(f"コメント追加エラー: {e}")
        return False


def update_comment(comment_id, new_text):
    """コメントを更新"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('comments')
        
        all_data = worksheet.get_all_records()
        df = pd.DataFrame(all_data)
        
        if not df.empty:
            existing = df[df['id'] == comment_id]
            if not existing.empty:
                row_index = existing.index[0] + 2
                worksheet.update(f'D{row_index}', new_text)
                
                # キャッシュをクリア
                st.cache_data.clear()
                
                return True
        
        return False
    except Exception as e:
        st.error(f"コメント更新エラー: {e}")
        return False


def delete_comment(comment_id):
    """コメントを削除"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('comments')
        
        all_data = worksheet.get_all_records()
        df = pd.DataFrame(all_data)
        
        if not df.empty:
            existing = df[df['id'] == comment_id]
            if not existing.empty:
                row_index = existing.index[0] + 2
                worksheet.delete_rows(row_index)
                
                # キャッシュをクリア
                st.cache_data.clear()
                
                return True
        
        return False
    except Exception as e:
        st.error(f"コメント削除エラー: {e}")
        return False


def toggle_favorite(entry_id, current_status):
    """お気に入りを切り替え"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('entries')
        
        all_data = worksheet.get_all_records()
        df = pd.DataFrame(all_data)
        
        if not df.empty:
            existing = df[df['id'] == entry_id]
            if not existing.empty:
                row_index = existing.index[0] + 2
                new_status = 'FALSE' if current_status else 'TRUE'
                worksheet.update(f'K{row_index}', new_status)
                
                # キャッシュをクリア
                st.cache_data.clear()
                
                return True
        
        return False
    except Exception as e:
        st.error(f"お気に入り更新エラー: {e}")
        return False


def save_settings(settings_dict):
    """設定を保存"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('settings')
        
        # 既存の設定を全て読み込み
        all_data = worksheet.get_all_records()
        df = pd.DataFrame(all_data) if all_data else pd.DataFrame(columns=['key', 'value'])
        
        # 各設定を更新または追加
        for key, value in settings_dict.items():
            if not df.empty and key in df['key'].values:
                # 既存の設定を更新
                row_index = df[df['key'] == key].index[0] + 2
                worksheet.update(f'B{row_index}', value)
            else:
                # 新規設定を追加
                worksheet.append_row([key, value])
        
        # キャッシュをクリア
        st.cache_data.clear()
        
        return True
    except Exception as e:
        st.error(f"設定保存エラー: {e}")
        return False


def open_image(file):
    """画像ファイルを開く（HEIC対応）"""
    try:
        # ファイル名の拡張子をチェック
        file_extension = file.name.lower().split('.')[-1] if hasattr(file, 'name') else ''
        
        if file_extension in ['heic', 'heif']:
            # HEICファイルの場合
            pillow_heif.register_heif_opener()
            img = Image.open(file)
            # RGBに変換（透過を削除）
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            return img
        else:
            # 通常の画像ファイル
            img = Image.open(file)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            return img
    except Exception as e:
        st.error(f"画像読み込みエラー: {e}")
        return None


def process_image_for_storage(uploaded_file):
    """画像を処理してbase64文字列として返す（サイズ制限対応）"""
    try:
        # 画像を開く
        img = open_image(uploaded_file)
        if img is None:
            return None, None
        
        # RGBに変換
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # まず500x500にリサイズ（アスペクト比維持）
        img.thumbnail((500, 500), Image.Resampling.LANCZOS)
        
        # JPEGとして保存（品質80）
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # サイズチェック（45,000文字以内）
        if len(img_str) > 45000:
            # さらに小さくリサイズ
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=60)
            img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return img_str, img
        
    except Exception as e:
        st.error(f"画像処理エラー: {e}")
        return None, None


def show_stamp_button(stamp, key_prefix, current_selection=None):
    """スタンプボタンを表示"""
    is_selected = current_selection and current_selection['emoji'] == stamp['emoji']
    
    button_style = """
        background: linear-gradient(135deg, #f472b6, #ec4899);
        color: white;
        border: 3px solid #ec4899;
        box-shadow: 0 4px 12px rgba(236, 72, 153, 0.4);
    """ if is_selected else """
        background: white;
        color: #374151;
        border: 2px solid #e5e7eb;
    """
    
    button_html = f"""
    <div style="
        {button_style}
        border-radius: 16px;
        padding: 12px 8px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        min-height: 80px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 4px;
    ">
        <div style="font-size: 32px;">{stamp['emoji']}</div>
        <div style="font-size: 11px; font-weight: 600; line-height: 1.2;">{stamp['label']}</div>
    </div>
    """
    
    st.markdown(button_html, unsafe_allow_html=True)
    
    return st.button(
        f"{stamp['emoji']} {stamp['label']}", 
        key=f"{key_prefix}_{stamp['emoji']}", 
        use_container_width=True,
        type="primary" if is_selected else "secondary"
    )


# ===== セッション状態の初期化 =====
if 'tab' not in st.session_state:
    st.session_state.tab = 'home'

if 'current_user' not in st.session_state:
    st.session_state.current_user = 'A'

if 'show_morning_form' not in st.session_state:
    st.session_state.show_morning_form = False

if 'show_evening_form' not in st.session_state:
    st.session_state.show_evening_form = False

if 'selected_morning_stamp' not in st.session_state:
    st.session_state.selected_morning_stamp = None

if 'selected_evening_stamp' not in st.session_state:
    st.session_state.selected_evening_stamp = None

if 'last_date' not in st.session_state:
    st.session_state.last_date = get_today_jst().isoformat()

# 日付が変わったらキャッシュをクリア
current_date_str = get_today_jst().isoformat()
if st.session_state.last_date != current_date_str:
    st.cache_data.clear()
    st.session_state.last_date = current_date_str

# ===== データ読み込み =====
settings = load_settings()
entries_df = load_entries(_date_key=get_today_jst().isoformat())
comments_df = load_comments()

# ===== ヘッダー =====
current_user = get_current_user()
user_name = settings.get(f'user_{current_user.lower()}_name', f'ユーザー{current_user}')
user_avatar = settings.get(f'user_{current_user.lower()}_avatar', '👤')

# 未読コメント数を計算
partner_user = 'B' if current_user == 'A' else 'A'
my_entry_ids = entries_df[entries_df['user_id'] == current_user]['id'].tolist()
unread_comments = comments_df[
    (comments_df['entry_id'].isin(my_entry_ids)) & 
    (comments_df['user_id'] == partner_user)
]
unread_count = len(unread_comments)

# ヘッダー表示
header_html = f"""
<div class="header-container">
    <div class="header-flex">
        <div class="header-avatar">{user_avatar}</div>
        <div class="header-text">
            <div class="header-title">{user_name}さん</div>
            <div class="header-subtitle">ふたりの日記</div>
        </div>
"""

if unread_count > 0:
    header_html += f"""
        <div class="notification-badge">
            💬 {unread_count}件の新着
        </div>
"""

header_html += """
    </div>
</div>
"""

st.markdown(header_html, unsafe_allow_html=True)

# ===== タブナビゲーション =====
tabs = [
    {"key": "home", "emoji": "🏠", "label": "ホーム"},
    {"key": "calendar", "emoji": "📅", "label": "カレンダー"},
    {"key": "history", "emoji": "📖", "label": "履歴"},
    {"key": "settings", "emoji": "⚙️", "label": "設定"}
]

# HTMLでタブを表示（見た目）
tab_grid_html = '<div class="tab-nav-grid">'
for tab in tabs:
    active_class = "active" if st.session_state.tab == tab["key"] else ""
    tab_grid_html += f'''
    <div class="tab-nav-item {active_class}">
        <div class="tab-nav-emoji">{tab["emoji"]}</div>
        <div class="tab-nav-label">{tab["label"]}</div>
    </div>
    '''
tab_grid_html += '</div>'
st.markdown(tab_grid_html, unsafe_allow_html=True)

# 隠しボタンでクリック検知
st.markdown('<div class="tab-btn-container">', unsafe_allow_html=True)
cols = st.columns(4)
for i, tab in enumerate(tabs):
    with cols[i]:
        button_key = f"tab_{tab['key']}_btn"
        if st.button("　", key=button_key, use_container_width=True):
            st.session_state.tab = tab["key"]
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ===== ホームタブ =====
if st.session_state.tab == 'home':
    today = get_today_jst()
    today_entry = entries_df[
        (entries_df['user_id'] == current_user) & 
        (entries_df['entry_date'] == today)
    ]
    
    has_morning = not today_entry.empty and today_entry.iloc[0]['morning_stamp_emoji']
    has_evening = not today_entry.empty and today_entry.iloc[0]['evening_stamp_emoji']
    
    # 朝のチェックイン
    st.markdown("### ☀️ 朝のチェックイン")
    
    if has_morning:
        entry = today_entry.iloc[0]
        st.markdown(f"""
        <div class="card">
            <div style="font-size: 48px; text-align: center; margin-bottom: 8px;">
                {entry['morning_stamp_emoji']}
            </div>
            <div style="text-align: center; font-size: 16px; font-weight: 700; color: #ec4899; margin-bottom: 12px;">
                {entry['morning_stamp_label']}
            </div>
            <div style="color: #6b7280; text-align: center;">
                {entry['morning_message'] if entry['morning_message'] else 'メッセージなし'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ 編集", key="edit_morning_btn", use_container_width=True):
                st.session_state.show_morning_form = True
                st.rerun()
        with col2:
            if st.button("🗑️ 削除", key="delete_morning_btn", use_container_width=True):
                if delete_morning_entry(current_user, today):
                    st.success("朝のチェックインを削除しました")
                    st.rerun()
    
    if not has_morning or st.session_state.show_morning_form:
        if st.session_state.show_morning_form and has_morning:
            if st.button("← 戻る", key="back_from_morning_edit"):
                st.session_state.show_morning_form = False
                st.session_state.selected_morning_stamp = None
                st.rerun()
        
        st.markdown("**今日の調子は？**")
        
        # 8個のスタンプを2行 x 4列で表示
        for row in range(2):
            cols = st.columns(4)
            for col in range(4):
                i = row * 4 + col
                if i < len(CONDITION_STAMPS):
                    with cols[col]:
                        if show_stamp_button(
                            CONDITION_STAMPS[i],
                            f"morning_{row}_{col}",
                            st.session_state.selected_morning_stamp
                        ):
                            st.session_state.selected_morning_stamp = CONDITION_STAMPS[i]
                            st.rerun()
        
        if st.session_state.selected_morning_stamp:
            morning_message = st.text_area(
                "メッセージ（任意）",
                value=today_entry.iloc[0]['morning_message'] if has_morning else "",
                placeholder="今日の気分やメッセージを書いてね",
                key="morning_message_input",
                height=80
            )
            
            if st.button("✅ 保存", key="save_morning_btn", type="primary", use_container_width=True):
                if save_entry(
                    current_user, today,
                    morning_stamp_emoji=st.session_state.selected_morning_stamp['emoji'],
                    morning_stamp_label=st.session_state.selected_morning_stamp['label'],
                    morning_message=morning_message
                ):
                    st.success("朝のチェックインを保存しました！")
                    st.session_state.show_morning_form = False
                    st.session_state.selected_morning_stamp = None
                    st.rerun()
    
    st.markdown("---")
    
    # 夜の日記
    st.markdown("### 🌙 夜の日記")
    
    if has_evening:
        entry = today_entry.iloc[0]
        st.markdown(f"""
        <div class="card">
            <div style="font-size: 48px; text-align: center; margin-bottom: 8px;">
                {entry['evening_stamp_emoji']}
            </div>
            <div style="text-align: center; font-size: 16px; font-weight: 700; color: #ec4899; margin-bottom: 12px;">
                {entry['evening_stamp_label']}
            </div>
            <div style="color: #374151; white-space: pre-wrap; margin-bottom: 12px;">
                {entry['evening_diary_text'] if entry['evening_diary_text'] else '日記なし'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if entry['image_data']:
            try:
                img_data = base64.b64decode(entry['image_data'])
                img = Image.open(BytesIO(img_data))
                st.image(img, use_container_width=True)
            except:
                pass
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ 編集", key="edit_evening_btn", use_container_width=True):
                st.session_state.show_evening_form = True
                st.rerun()
        with col2:
            if st.button("🗑️ 削除", key="delete_evening_btn", use_container_width=True):
                if delete_evening_entry(current_user, today):
                    st.success("夜の日記を削除しました")
                    st.rerun()
    
    if not has_evening or st.session_state.show_evening_form:
        if st.session_state.show_evening_form and has_evening:
            if st.button("← 戻る", key="back_from_evening_edit"):
                st.session_state.show_evening_form = False
                st.session_state.selected_evening_stamp = None
                st.rerun()
        
        st.markdown("**今日の気分は？**")
        
        # 8個のスタンプを2行 x 4列で表示
        for row in range(2):
            cols = st.columns(4)
            for col in range(4):
                i = row * 4 + col
                if i < len(MOOD_STAMPS):
                    with cols[col]:
                        if show_stamp_button(
                            MOOD_STAMPS[i],
                            f"evening_{row}_{col}",
                            st.session_state.selected_evening_stamp
                        ):
                            st.session_state.selected_evening_stamp = MOOD_STAMPS[i]
                            st.rerun()
        
        if st.session_state.selected_evening_stamp:
            evening_diary = st.text_area(
                "今日の日記",
                value=today_entry.iloc[0]['evening_diary_text'] if has_evening else "",
                placeholder="今日あったことを書いてね",
                key="evening_diary_input",
                height=120
            )
            
            uploaded_file = st.file_uploader(
                "写真を追加（任意）",
                type=["jpg", "jpeg", "png", "heic", "heif"],
                key="evening_image_upload"
            )
            
            # 画像プレビューとサイズ表示
            image_data_to_save = None
            if uploaded_file:
                img_str, img = process_image_for_storage(uploaded_file)
                if img_str and img:
                    image_data_to_save = img_str
                    st.image(img, caption="プレビュー", use_container_width=True)
                    st.info(f"画像サイズ: {len(img_str):,} 文字（上限45,000）")
            elif has_evening and today_entry.iloc[0]['image_data']:
                # 既存の画像を保持
                image_data_to_save = today_entry.iloc[0]['image_data']
                try:
                    img_data = base64.b64decode(image_data_to_save)
                    img = Image.open(BytesIO(img_data))
                    st.image(img, caption="現在の画像", use_container_width=True)
                except:
                    pass
            
            if st.button("✅ 保存", key="save_evening_btn", type="primary", use_container_width=True):
                if save_entry(
                    current_user, today,
                    evening_stamp_emoji=st.session_state.selected_evening_stamp['emoji'],
                    evening_stamp_label=st.session_state.selected_evening_stamp['label'],
                    evening_diary_text=evening_diary,
                    image_data=image_data_to_save
                ):
                    st.success("夜の日記を保存しました！")
                    st.session_state.show_evening_form = False
                    st.session_state.selected_evening_stamp = None
                    st.rerun()
    
    # パートナーの今日のエントリー
    st.markdown("---")
    partner_name = settings.get(f'user_{partner_user.lower()}_name', f'ユーザー{partner_user}')
    st.markdown(f"### 💕 {partner_name}さんの今日")
    
    partner_entry = entries_df[
        (entries_df['user_id'] == partner_user) & 
        (entries_df['entry_date'] == today)
    ]
    
    if not partner_entry.empty:
        entry = partner_entry.iloc[0]
        
        # 朝のチェックイン
        if entry['morning_stamp_emoji']:
            st.markdown("**☀️ 朝のチェックイン**")
            st.markdown(f"""
            <div class="card">
                <div style="font-size: 40px; text-align: center; margin-bottom: 6px;">
                    {entry['morning_stamp_emoji']}
                </div>
                <div style="text-align: center; font-size: 14px; font-weight: 700; color: #ec4899; margin-bottom: 8px;">
                    {entry['morning_stamp_label']}
                </div>
                <div style="color: #6b7280; text-align: center; font-size: 13px;">
                    {entry['morning_message'] if entry['morning_message'] else 'メッセージなし'}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # 夜の日記
        if entry['evening_stamp_emoji']:
            st.markdown("**🌙 夜の日記**")
            st.markdown(f"""
            <div class="card">
                <div style="font-size: 40px; text-align: center; margin-bottom: 6px;">
                    {entry['evening_stamp_emoji']}
                </div>
                <div style="text-align: center; font-size: 14px; font-weight: 700; color: #ec4899; margin-bottom: 8px;">
                    {entry['evening_stamp_label']}
                </div>
                <div style="color: #374151; white-space: pre-wrap; margin-bottom: 8px; font-size: 13px;">
                    {entry['evening_diary_text'] if entry['evening_diary_text'] else '日記なし'}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if entry['image_data']:
                try:
                    img_data = base64.b64decode(entry['image_data'])
                    img = Image.open(BytesIO(img_data))
                    st.image(img, use_container_width=True)
                except:
                    pass
            
            # コメント機能
            entry_comments = comments_df[comments_df['entry_id'] == entry['id']]
            
            if not entry_comments.empty:
                st.markdown("**💬 コメント**")
                for _, comment in entry_comments.iterrows():
                    comment_user_name = settings.get(
                        f"user_{comment['user_id'].lower()}_name",
                        f"ユーザー{comment['user_id']}"
                    )
                    
                    st.markdown(f"""
                    <div class="comment-box">
                        <div style="font-weight: 700; margin-bottom: 4px; font-size: 12px;">
                            {comment_user_name}
                        </div>
                        <div style="font-size: 13px;">
                            {comment['comment_text']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # コメント追加
            new_comment = st.text_area(
                "コメントを追加",
                placeholder="メッセージを書いてね",
                key="new_comment_input",
                height=60
            )
            
            if st.button("💬 コメントする", key="add_comment_btn", use_container_width=True):
                if new_comment.strip():
                    if add_comment(entry['id'], current_user, new_comment):
                        st.success("コメントを追加しました！")
                        st.rerun()
    else:
        st.info(f"{partner_name}さんはまだ今日の日記を書いていません")

# ===== カレンダータブ =====
elif st.session_state.tab == 'calendar':
    st.markdown("### 📅 カレンダー")
    
    # 月選択
    today = get_today_jst()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("◀️", key="prev_month_btn", use_container_width=True):
            if 'calendar_date' not in st.session_state:
                st.session_state.calendar_date = today
            
            first_day = st.session_state.calendar_date.replace(day=1)
            last_month = first_day - timedelta(days=1)
            st.session_state.calendar_date = last_month
            st.rerun()
    
    with col2:
        if 'calendar_date' not in st.session_state:
            st.session_state.calendar_date = today
        
        st.markdown(f"""
        <div style="text-align: center; font-size: 18px; font-weight: 700; color: #ec4899; padding: 8px;">
            {st.session_state.calendar_date.year}年{st.session_state.calendar_date.month}月
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        if st.button("▶️", key="next_month_btn", use_container_width=True):
            if 'calendar_date' not in st.session_state:
                st.session_state.calendar_date = today
            
            year = st.session_state.calendar_date.year
            month = st.session_state.calendar_date.month
            
            if month == 12:
                next_month = date(year + 1, 1, 1)
            else:
                next_month = date(year, month + 1, 1)
            
            st.session_state.calendar_date = next_month
            st.rerun()
    
    # カレンダー生成（日曜始まり）
    if 'calendar_date' not in st.session_state:
        st.session_state.calendar_date = today
    
    year = st.session_state.calendar_date.year
    month = st.session_state.calendar_date.month
    
    # 日曜日を週の始まりに設定
    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(year, month)
    
    # その月のエントリーを取得
    month_entries = entries_df[
        (entries_df['entry_date'] >= date(year, month, 1)) &
        (entries_df['entry_date'] < date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1))
    ]
    
    # 日付ごとのエントリー数をカウント
    entry_counts = month_entries.groupby('entry_date').size().to_dict()
    
    # CSS Gridでカレンダー表示
    calendar_html = """
    <style>
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 2px;
        width: 100%;
        margin: 10px 0;
    }
    .calendar-header {
        text-align: center;
        font-weight: 700;
        font-size: 11px;
        color: #6b7280;
        padding: 8px 4px;
        background: #f9fafb;
        border-radius: 6px;
    }
    .calendar-cell {
        aspect-ratio: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 600;
        border: 1px solid #e5e7eb;
        background: #f9fafb;
        position: relative;
        min-height: 20px;
    }
    .calendar-cell.today {
        background: #fef3c7;
        border-color: #fbbf24;
    }
    .calendar-cell.has-entry {
        background: #fce7f3;
        border-color: #f472b6;
    }
    .calendar-date {
        font-size: 10px;
        line-height: 1;
    }
    .calendar-weekday {
        font-size: 9px;
        color: #9ca3af;
        line-height: 1;
    }
    .entry-indicator {
        width: 4px;
        height: 4px;
        background: #ec4899;
        border-radius: 50%;
        margin-top: 2px;
    }
    </style>
    <div class="calendar-grid">
    """
    
    # 曜日ヘッダー（日曜始まり）
    weekdays = ["日", "月", "火", "水", "木", "金", "土"]
    for wd in weekdays:
        calendar_html += f'<div class="calendar-header">{wd}</div>'
    
    # 日付セル
    for week in cal:
        for day in week:
            if day == 0:
                calendar_html += '<div class="calendar-cell"></div>'
            else:
                current_date = date(year, month, day)
                is_today = current_date == today
                has_entry = current_date in entry_counts
                
                classes = "calendar-cell"
                if is_today:
                    classes += " today"
                elif has_entry:
                    classes += " has-entry"
                
                # 曜日を取得
                weekday_num = current_date.weekday()
                # Pythonのweekday()は月曜=0なので、日曜=0に変換
                weekday_num = (weekday_num + 1) % 7
                weekday_str = weekdays[weekday_num]
                
                calendar_html += f'''
                <div class="{classes}">
                    <div class="calendar-date">{day}</div>
                    <div class="calendar-weekday">{weekday_str}</div>
                '''
                
                if has_entry:
                    calendar_html += '<div class="entry-indicator"></div>'
                
                calendar_html += '</div>'
    
    calendar_html += '</div>'
    
    st.markdown(calendar_html, unsafe_allow_html=True)
    
    # 凡例
    st.markdown("""
    <div style="display: flex; gap: 12px; justify-content: center; margin-top: 10px; font-size: 11px;">
        <div><span style="color: #fbbf24;">●</span> 今日</div>
        <div><span style="color: #f472b6;">●</span> 日記あり</div>
    </div>
    """, unsafe_allow_html=True)

# ===== 履歴タブ =====
elif st.session_state.tab == 'history':
    st.markdown("### 📖 日記履歴")
    
    # フィルター
    col1, col2 = st.columns(2)
    
    with col1:
        filter_user = st.selectbox(
            "表示するユーザー",
            ["すべて", settings['user_a_name'], settings['user_b_name']],
            key="filter_user_select"
        )
    
    with col2:
        filter_favorite = st.checkbox("お気に入りのみ", key="filter_favorite_check")
    
    # フィルタリング
    filtered_entries = entries_df.copy()
    
    if filter_user != "すべて":
        user_id = 'A' if filter_user == settings['user_a_name'] else 'B'
        filtered_entries = filtered_entries[filtered_entries['user_id'] == user_id]
    
    if filter_favorite:
        filtered_entries = filtered_entries[filtered_entries['is_favorite'] == True]
    
    # 日付でソート（新しい順）
    filtered_entries = filtered_entries.sort_values('entry_date', ascending=False)
    
    if filtered_entries.empty:
        st.info("エントリーがありません")
    else:
        for _, entry in filtered_entries.iterrows():
            entry_user_name = settings.get(
                f"user_{entry['user_id'].lower()}_name",
                f"ユーザー{entry['user_id']}"
            )
            entry_date_str = entry['entry_date'].strftime('%Y年%m月%d日')
            
            is_favorite = entry.get('is_favorite', False)
            favorite_icon = "⭐" if is_favorite else "☆"
            
            with st.expander(f"{entry_date_str} - {entry_user_name} {favorite_icon}"):
                # お気に入りボタン
                if st.button(
                    f"{favorite_icon} お気に入り",
                    key=f"fav_{entry['id']}",
                    use_container_width=True
                ):
                    if toggle_favorite(entry['id'], is_favorite):
                        st.rerun()
                
                # 朝のチェックイン
                if entry['morning_stamp_emoji']:
                    st.markdown("**☀️ 朝のチェックイン**")
                    st.markdown(f"{entry['morning_stamp_emoji']} {entry['morning_stamp_label']}")
                    if entry['morning_message']:
                        st.markdown(f"> {entry['morning_message']}")
                    st.markdown("")
                
                # 夜の日記
                if entry['evening_stamp_emoji']:
                    st.markdown("**🌙 夜の日記**")
                    st.markdown(f"{entry['evening_stamp_emoji']} {entry['evening_stamp_label']}")
                    if entry['evening_diary_text']:
                        st.markdown(entry['evening_diary_text'])
                    
                    if entry['image_data']:
                        try:
                            img_data = base64.b64decode(entry['image_data'])
                            img = Image.open(BytesIO(img_data))
                            st.image(img, use_container_width=True)
                        except:
                            pass
                
                # コメント表示
                entry_comments = comments_df[comments_df['entry_id'] == entry['id']]
                
                if not entry_comments.empty:
                    st.markdown("**💬 コメント**")
                    for _, comment in entry_comments.iterrows():
                        comment_user_name = settings.get(
                            f"user_{comment['user_id'].lower()}_name",
                            f"ユーザー{comment['user_id']}"
                        )
                        
                        st.markdown(f"""
                        <div class="comment-box">
                            <div style="font-weight: 700; margin-bottom: 4px; font-size: 12px;">
                                {comment_user_name}
                            </div>
                            <div style="font-size: 13px;">
                                {comment['comment_text']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # コメント追加（相手のエントリーのみ）
                if entry['user_id'] != current_user:
                    new_comment = st.text_area(
                        "コメントを追加",
                        key=f"comment_{entry['id']}",
                        placeholder="メッセージを書いてね",
                        height=60
                    )
                    
                    if st.button("💬 コメントする", key=f"add_comment_{entry['id']}", use_container_width=True):
                        if new_comment.strip():
                            if add_comment(entry['id'], current_user, new_comment):
                                st.success("コメントを追加しました！")
                                st.rerun()

# ===== 設定タブ =====
elif st.session_state.tab == 'settings':
    st.markdown("### ⚙️ 設定")
    
    # ユーザー切り替え
    st.markdown("#### 👤 ユーザー切り替え")
    
    current_user_name = settings.get(f'user_{current_user.lower()}_name', f'ユーザー{current_user}')
    partner_user_name = settings.get(f'user_{partner_user.lower()}_name', f'ユーザー{partner_user}')
    
    st.info(f"現在のユーザー: {current_user_name}")
    
    if st.button(f"🔄 {partner_user_name}に切り替え", key="switch_user_btn", use_container_width=True):
        switch_user()
        st.rerun()
    
    st.markdown("---")
    
    # プロフィール設定
    st.markdown("#### 💑 プロフィール設定")
    
    with st.form("profile_form"):
        user_a_name = st.text_input("ユーザーAの名前", value=settings.get('user_a_name', 'ユーザーA'))
        user_a_avatar = st.text_input("ユーザーAのアバター（絵文字）", value=settings.get('user_a_avatar', '👦'))
        
        user_b_name = st.text_input("ユーザーBの名前", value=settings.get('user_b_name', 'ユーザーB'))
        user_b_avatar = st.text_input("ユーザーBのアバター（絵文字）", value=settings.get('user_b_avatar', '👧'))
        
        anniversary_str = settings.get('anniversary', str(date.today()))
        try:
            anniversary_date = datetime.strptime(anniversary_str, '%Y-%m-%d').date()
        except:
            anniversary_date = date.today()
        
        anniversary = st.date_input("記念日", value=anniversary_date)
        
        if st.form_submit_button("💾 保存", use_container_width=True):
            new_settings = {
                'user_a_name': user_a_name,
                'user_a_avatar': user_a_avatar,
                'user_b_name': user_b_name,
                'user_b_avatar': user_b_avatar,
                'anniversary': anniversary.isoformat()
            }
            
            if save_settings(new_settings):
                st.success("設定を保存しました！")
                st.rerun()
    
    st.markdown("---")
    
    # 統計情報
    st.markdown("#### 📊 統計情報")
    
    total_entries = len(entries_df)
    total_comments = len(comments_df)
    
    user_a_entries = len(entries_df[entries_df['user_id'] == 'A'])
    user_b_entries = len(entries_df[entries_df['user_id'] == 'B'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div style="font-size: 32px; font-weight: 800; color: #ec4899;">{total_entries}</div>
            <div style="font-size: 12px; color: #6b7280;">総エントリー数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div style="font-size: 32px; font-weight: 800; color: #ec4899;">{total_comments}</div>
            <div style="font-size: 12px; color: #6b7280;">総コメント数</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="text-align: center; margin-top: 12px; font-size: 13px; color: #6b7280;">
        {settings['user_a_name']}: {user_a_entries}件 | {settings['user_b_name']}: {user_b_entries}件
    </div>
    """, unsafe_allow_html=True)
