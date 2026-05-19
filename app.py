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

# カスタムCSS（スマホ完全対応版）v1.7 - カラム設定を限定
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
    
    /* タブナビゲーション v1.7 - カラム設定を限定 */
    .tab-nav-container div[data-testid="column"] {
        padding: 0 3px !important;
    }
    
    .tab-nav-container .stButton > button {
        min-height: 70px !important;
        height: 70px !important;
        font-size: 10px !important;
        line-height: 1.3 !important;
        border-radius: 16px !important;
        white-space: pre-line !important;
        word-break: keep-all !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        padding: 4px !important;
    }
    
    /* スタンプボタン v1.7 - カラム設定を限定 */
    .stamp-container div[data-testid="column"] {
        padding: 0 3px !important;
    }
    
    .stamp-container .stButton > button {
        min-height: 80px !important;
        padding: 8px 4px !important;
        font-size: 11px !important;
        line-height: 1.3 !important;
        border-radius: 16px !important;
        white-space: pre-line !important;
        word-break: keep-all !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
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
        return pd.DataFrame(columns=[
            'id', 'user_id', 'entry_date', 'morning_stamp_emoji', 'morning_stamp_label',
            'morning_message', 'evening_stamp_emoji', 'evening_stamp_label',
            'evening_diary_text', 'image_data', 'is_favorite', 'created_at', 'updated_at'
        ])


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


@st.cache_data(ttl=600)
def load_comments():
    """Google Sheetsからコメントを読み込み（キャッシュ10分）"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('comments')
        data = worksheet.get_all_records()
        
        if not data:
            return pd.DataFrame(columns=['id', 'entry_id', 'user_id', 'comment_text', 'created_at'])
        
        return pd.DataFrame(data)
    except Exception as e:
        # クォータ超過などのエラーの場合、空のDataFrameを返す
        return pd.DataFrame(columns=['id', 'entry_id', 'user_id', 'comment_text', 'created_at'])


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


def toggle_favorite(user_id, entry_date):
    """お気に入りをトグル"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('entries')
        
        all_data = worksheet.get_all_records()
        df = pd.DataFrame(all_data)
        
        entry_date_str = entry_date.isoformat()
        
        if not df.empty:
            existing = df[(df['user_id'] == user_id) & (df['entry_date'] == entry_date_str)]
            if not existing.empty:
                row_index = existing.index[0] + 2
                current_favorite = str(existing.iloc[0]['is_favorite']).upper() == 'TRUE'
                new_favorite = 'FALSE' if current_favorite else 'TRUE'
                
                worksheet.update(f'K{row_index}', new_favorite)
                
                # キャッシュをクリア
                st.cache_data.clear()
                
                return True
        return False
    except Exception as e:
        st.error(f"お気に入り更新エラー: {e}")
        return False


def update_settings(key, value):
    """設定を更新"""
    try:
        sheet = init_gspread()
        worksheet = sheet.worksheet('settings')
        
        all_data = worksheet.get_all_records()
        df = pd.DataFrame(all_data)
        
        if not df.empty:
            existing = df[df['key'] == key]
            if not existing.empty:
                row_index = existing.index[0] + 2
                worksheet.update(f'B{row_index}', value)
            else:
                # 新規追加
                worksheet.append_row([key, value])
        else:
            # 最初の設定
            worksheet.append_row([key, value])
        
        # キャッシュをクリア
        st.cache_data.clear()
        
        return True
    except Exception as e:
        st.error(f"設定更新エラー: {e}")
        return False


def open_image(uploaded_file):
    """画像を開く（HEIF形式対応）"""
    try:
        if uploaded_file.name.lower().endswith(('.heic', '.heif')):
            heif_file = pillow_heif.read_heif(uploaded_file)
            img = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
            )
        else:
            img = Image.open(uploaded_file)
        return img
    except Exception as e:
        st.error(f"画像読み込みエラー: {e}")
        return None


def process_image(uploaded_file):
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

# ヘッダーHTML（通知バッジを削除）
header_html = f"""
<div class="header-container">
    <div class="header-flex">
        <div class="header-avatar">{user_avatar}</div>
        <div class="header-text">
            <div class="header-title">📔 ふたりの日記</div>
            <div class="header-subtitle">{user_name} でログイン中</div>
        </div>
    </div>
</div>
"""

st.markdown(header_html, unsafe_allow_html=True)

# ===== タブナビゲーション（アイコンを枠内に配置） =====
tabs = [
    {"key": "home", "emoji": "🏠", "label": "ホーム"},
    {"key": "calendar", "emoji": "📅", "label": "カレンダー"},
    {"key": "history", "emoji": "📖", "label": "履歴"},
    {"key": "settings", "emoji": "⚙️", "label": "設定"}
]

st.markdown('<div class="tab-nav-container">', unsafe_allow_html=True)
cols = st.columns(4)
for i, tab in enumerate(tabs):
    with cols[i]:
        is_active = st.session_state.tab == tab["key"]
        
        # 絵文字とラベルを1つのボタンに含める
        if st.button(
            f"{tab['emoji']}\n{tab['label']}",
            key=f"tab_{tab['key']}",
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            st.session_state.tab = tab["key"]
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ===== ホームタブ =====
if st.session_state.tab == 'home':
    today = get_today_jst()
    partner_user = 'B' if current_user == 'A' else 'A'
    
    # 自分と相手のエントリーを取得
    my_entry = entries_df[
        (entries_df['user_id'] == current_user) & 
        (entries_df['entry_date'] == today)
    ]
    partner_entry = entries_df[
        (entries_df['user_id'] == partner_user) & 
        (entries_df['entry_date'] == today)
    ]
    
    has_my_morning = not my_entry.empty and my_entry.iloc[0]['morning_stamp_emoji']
    has_my_evening = not my_entry.empty and my_entry.iloc[0]['evening_stamp_emoji']
    has_partner_morning = not partner_entry.empty and partner_entry.iloc[0]['morning_stamp_emoji']
    has_partner_evening = not partner_entry.empty and partner_entry.iloc[0]['evening_stamp_emoji']
    
    # 相手の今日の状態を表示
    partner_name = settings.get(f'user_{partner_user.lower()}_name', f'ユーザー{partner_user}')
    partner_avatar = settings.get(f'user_{partner_user.lower()}_avatar', '👤')
    
    st.markdown(f"### 💕 {partner_name}の今日")
    
    if has_partner_morning or has_partner_evening:
        partner_data = partner_entry.iloc[0]
        
        card_html = '<div class="card">'
        
        # 朝の状態
        if has_partner_morning:
            card_html += f"""
            <div style="margin-bottom: {'12px' if has_partner_evening else '0'};">
                <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">☀️ 朝</div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="font-size: 32px;">{partner_data['morning_stamp_emoji']}</div>
                    <div>
                        <div style="font-weight: 700; color: #ec4899;">{partner_data['morning_stamp_label']}</div>
                        <div style="color: #6b7280; font-size: 14px;">{partner_data['morning_message'] if partner_data['morning_message'] else ''}</div>
                    </div>
                </div>
            </div>
            """
        
        # 夜の状態
        if has_partner_evening:
            card_html += f"""
            <div>
                <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">🌙 夜</div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="font-size: 32px;">{partner_data['evening_stamp_emoji']}</div>
                    <div style="font-weight: 700; color: #ec4899;">{partner_data['evening_stamp_label']}</div>
                </div>
            </div>
            """
        
        card_html += '</div>'
        st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info(f"{partner_name}はまだ今日の記録をしていません")
    
    st.markdown("---")
    
    # 朝の記録
    st.markdown("### ☀️ 朝の気分")
    
    if has_my_morning and not st.session_state.show_morning_form:
        # 朝の記録がある場合は表示
        entry = my_entry.iloc[0]
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
                    st.success("朝の記録を削除しました")
                    st.rerun()
    
    elif not has_my_morning and not st.session_state.show_morning_form:
        # 朝の記録がない場合は「追加」ボタンのみ表示
        if st.button("➕ 朝の気分を記録", key="add_morning_btn", type="primary", use_container_width=True):
            st.session_state.show_morning_form = True
            st.rerun()
    
    elif st.session_state.show_morning_form:
        # 朝の入力フォーム（別画面として表示）
        if st.button("← 戻る", key="back_from_morning_edit"):
            st.session_state.show_morning_form = False
            st.session_state.selected_morning_stamp = None
            st.rerun()
        
        st.markdown("**今日の調子は？**")
        
        # 8個のスタンプを2行 x 4列で表示（アイコンを枠内に配置）
        st.markdown('<div class="stamp-container">', unsafe_allow_html=True)
        for row in range(2):
            cols = st.columns(4)
            for col in range(4):
                i = row * 4 + col
                if i < len(CONDITION_STAMPS):
                    stamp = CONDITION_STAMPS[i]
                    is_selected = (st.session_state.selected_morning_stamp and 
                                 st.session_state.selected_morning_stamp['emoji'] == stamp['emoji'])
                    
                    with cols[col]:
                        # 絵文字とラベルを1つのボタンに含める
                        if st.button(
                            f"{stamp['emoji']}\n{stamp['label']}",
                            key=f"morning_{row}_{col}",
                            use_container_width=True,
                            type="primary" if is_selected else "secondary"
                        ):
                            st.session_state.selected_morning_stamp = stamp
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state.selected_morning_stamp:
            morning_message = st.text_area(
                "メッセージ（任意）",
                value=my_entry.iloc[0]['morning_message'] if has_my_morning else "",
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
                    st.success("朝の記録を保存しました！")
                    st.session_state.show_morning_form = False
                    st.session_state.selected_morning_stamp = None
                    st.rerun()
    
    st.markdown("---")
    
    # 夜の日記
    st.markdown("### 🌙 今日の日記")
    
    if has_my_evening and not st.session_state.show_evening_form:
        # 夜の記録がある場合は表示
        entry = my_entry.iloc[0]
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
        """, unsafe_allow_html=True)
        
        # 画像表示
        if entry['image_data']:
            st.markdown(f"""
            <div style="text-align: center; margin: 12px 0;">
                <img src="data:image/jpeg;base64,{entry['image_data']}" 
                     style="max-width: 100%; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ 編集", key="edit_evening_btn", use_container_width=True):
                st.session_state.show_evening_form = True
                st.rerun()
        with col2:
            if st.button("🗑️ 削除", key="delete_evening_btn", use_container_width=True):
                if delete_evening_entry(current_user, today):
                    st.success("日記を削除しました")
                    st.rerun()
    
    elif not has_my_evening and not st.session_state.show_evening_form:
        # 夜の記録がない場合は「追加」ボタンのみ表示
        if st.button("➕ 今日の日記を書く", key="add_evening_btn", type="primary", use_container_width=True):
            st.session_state.show_evening_form = True
            st.rerun()
    
    elif st.session_state.show_evening_form:
        # 夜の入力フォーム（別画面として表示）
        if st.button("← 戻る", key="back_from_evening_edit"):
            st.session_state.show_evening_form = False
            st.session_state.selected_evening_stamp = None
            st.rerun()
        
        st.markdown("**今日の気分は？**")
        
        # 8個のスタンプを2行 x 4列で表示（アイコンを枠内に配置）
        st.markdown('<div class="stamp-container">', unsafe_allow_html=True)
        for row in range(2):
            cols = st.columns(4)
            for col in range(4):
                i = row * 4 + col
                if i < len(MOOD_STAMPS):
                    stamp = MOOD_STAMPS[i]
                    is_selected = (st.session_state.selected_evening_stamp and 
                                 st.session_state.selected_evening_stamp['emoji'] == stamp['emoji'])
                    
                    with cols[col]:
                        # 絵文字とラベルを1つのボタンに含める
                        if st.button(
                            f"{stamp['emoji']}\n{stamp['label']}",
                            key=f"evening_{row}_{col}",
                            use_container_width=True,
                            type="primary" if is_selected else "secondary"
                        ):
                            st.session_state.selected_evening_stamp = stamp
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state.selected_evening_stamp:
            evening_diary_text = st.text_area(
                "今日の日記",
                value=my_entry.iloc[0]['evening_diary_text'] if has_my_evening else "",
                placeholder="今日あったことを書いてね",
                key="evening_diary_input",
                height=120
            )
            
            # 画像アップロード
            uploaded_file = st.file_uploader(
                "写真を追加（任意）",
                type=['jpg', 'jpeg', 'png', 'heic', 'heif'],
                key="evening_image_upload"
            )
            
            image_data = None
            if uploaded_file:
                img_str, img = process_image(uploaded_file)
                if img_str:
                    image_data = img_str
                    st.image(img, caption="アップロードした画像", use_column_width=True)
            
            if st.button("✅ 保存", key="save_evening_btn", type="primary", use_container_width=True):
                save_params = {
                    'user_id': current_user,
                    'entry_date': today,
                    'evening_stamp_emoji': st.session_state.selected_evening_stamp['emoji'],
                    'evening_stamp_label': st.session_state.selected_evening_stamp['label'],
                    'evening_diary_text': evening_diary_text
                }
                
                if image_data:
                    save_params['image_data'] = image_data
                
                if save_entry(**save_params):
                    st.success("日記を保存しました！")
                    st.session_state.show_evening_form = False
                    st.session_state.selected_evening_stamp = None
                    st.rerun()


# ===== カレンダータブ =====
elif st.session_state.tab == 'calendar':
    st.markdown("### 📅 カレンダー")
    
    # 今月の情報
    today = get_today_jst()
    year = today.year
    month = today.month
    
    # 月選択
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ 前月", key="prev_month", use_container_width=True):
            if month == 1:
                year -= 1
                month = 12
            else:
                month -= 1
            st.rerun()
    
    with col2:
        st.markdown(f"<div style='text-align: center; font-size: 18px; font-weight: 700; padding: 8px;'>{year}年 {month}月</div>", unsafe_allow_html=True)
    
    with col3:
        if st.button("次月 ▶", key="next_month", use_container_width=True):
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
            st.rerun()
    
    # カレンダー表示
    cal = calendar.monthcalendar(year, month)
    
    # 曜日ヘッダー
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    header_html = '<div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin: 12px 0 8px;">'
    for day in weekdays:
        header_html += f'<div style="text-align: center; font-weight: 700; color: #ec4899; padding: 4px;">{day}</div>'
    header_html += '</div>'
    st.markdown(header_html, unsafe_allow_html=True)
    
    # 日付セル
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True)
                else:
                    day_date = date(year, month, day)
                    day_entries = entries_df[
                        (entries_df['user_id'] == current_user) & 
                        (entries_df['entry_date'] == day_date)
                    ]
                    
                    has_entry = not day_entries.empty and (
                        day_entries.iloc[0]['morning_stamp_emoji'] or 
                        day_entries.iloc[0]['evening_stamp_emoji']
                    )
                    
                    is_today = day_date == today
                    
                    bg_color = "#fce7f3" if has_entry else "#f9fafb"
                    border = "2px solid #ec4899" if is_today else "1px solid #e5e7eb"
                    
                    cell_html = f"""
                    <div style="
                        background: {bg_color};
                        border: {border};
                        border-radius: 8px;
                        padding: 8px;
                        height: 60px;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        font-size: 14px;
                        font-weight: {'700' if is_today else '400'};
                        color: {'#ec4899' if is_today else '#374151'};
                    ">
                        <div>{day}</div>
                    """
                    
                    if has_entry:
                        entry = day_entries.iloc[0]
                        emojis = []
                        if entry['morning_stamp_emoji']:
                            emojis.append(entry['morning_stamp_emoji'])
                        if entry['evening_stamp_emoji']:
                            emojis.append(entry['evening_stamp_emoji'])
                        cell_html += f'<div style="font-size: 16px; margin-top: 2px;">{"".join(emojis)}</div>'
                    
                    cell_html += "</div>"
                    st.markdown(cell_html, unsafe_allow_html=True)


# ===== 履歴タブ =====
elif st.session_state.tab == 'history':
    st.markdown("### 📖 ふたりの履歴")
    
    partner_user = 'B' if current_user == 'A' else 'A'
    
    # フィルター
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        show_user = st.selectbox(
            "表示するユーザー",
            ["すべて", "自分のみ", "相手のみ"],
            key="history_user_filter"
        )
    
    with filter_col2:
        show_favorites = st.checkbox("お気に入りのみ", key="history_favorite_filter")
    
    # フィルター適用
    filtered_df = entries_df.copy()
    
    if show_user == "自分のみ":
        filtered_df = filtered_df[filtered_df['user_id'] == current_user]
    elif show_user == "相手のみ":
        filtered_df = filtered_df[filtered_df['user_id'] == partner_user]
    
    if show_favorites:
        filtered_df = filtered_df[filtered_df['is_favorite'] == True]
    
    # 記録があるエントリーのみ（朝または夜のスタンプがある）
    filtered_df = filtered_df[
        (filtered_df['morning_stamp_emoji'].notna() & (filtered_df['morning_stamp_emoji'] != '')) |
        (filtered_df['evening_stamp_emoji'].notna() & (filtered_df['evening_stamp_emoji'] != ''))
    ]
    
    # 日付順に並び替え（新しい順）
    filtered_df = filtered_df.sort_values('entry_date', ascending=False)
    
    if filtered_df.empty:
        st.info("まだ記録がありません")
    else:
        for _, entry in filtered_df.iterrows():
            entry_user = entry['user_id']
            entry_name = settings.get(f'user_{entry_user.lower()}_name', f'ユーザー{entry_user}')
            entry_avatar = settings.get(f'user_{entry_user.lower()}_avatar', '👤')
            entry_date = entry['entry_date']
            
            # エントリーカード
            card_html = f"""
            <div class="card">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <div style="font-size: 24px;">{entry_avatar}</div>
                    <div style="flex: 1;">
                        <div style="font-weight: 700; color: #374151;">{entry_name}</div>
                        <div style="font-size: 12px; color: #9ca3af;">{entry_date}</div>
                    </div>
                </div>
            """
            
            # 朝の記録
            if entry['morning_stamp_emoji']:
                card_html += f"""
                <div style="margin-bottom: 12px;">
                    <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">☀️ 朝</div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="font-size: 32px;">{entry['morning_stamp_emoji']}</div>
                        <div>
                            <div style="font-weight: 700; color: #ec4899;">{entry['morning_stamp_label']}</div>
                            <div style="color: #6b7280; font-size: 14px;">{entry['morning_message'] if entry['morning_message'] else ''}</div>
                        </div>
                    </div>
                </div>
                """
            
            # 夜の記録
            if entry['evening_stamp_emoji']:
                card_html += f"""
                <div>
                    <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">🌙 夜</div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <div style="font-size: 32px;">{entry['evening_stamp_emoji']}</div>
                        <div style="font-weight: 700; color: #ec4899;">{entry['evening_stamp_label']}</div>
                    </div>
                    <div style="color: #374151; white-space: pre-wrap; font-size: 14px; margin-bottom: 8px;">
                        {entry['evening_diary_text'] if entry['evening_diary_text'] else ''}
                    </div>
                """
                
                # 画像
                if entry['image_data']:
                    card_html += f"""
                    <div style="text-align: center; margin-bottom: 8px;">
                        <img src="data:image/jpeg;base64,{entry['image_data']}" 
                             style="max-width: 100%; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    </div>
                    """
                
                card_html += "</div>"
            
            card_html += "</div>"
            st.markdown(card_html, unsafe_allow_html=True)
            
            # アクションボタン
            col1, col2, col3 = st.columns(3)
            with col1:
                favorite_label = "⭐ 解除" if entry['is_favorite'] else "⭐ お気に入り"
                if st.button(favorite_label, key=f"fav_{entry['id']}", use_container_width=True):
                    if toggle_favorite(entry_user, entry_date):
                        st.rerun()
            
            with col2:
                # コメント数を表示（DataFrameが空でない場合のみ）
                if not comments_df.empty and 'entry_id' in comments_df.columns:
                    entry_comments = comments_df[comments_df['entry_id'] == entry['id']]
                    comment_count = len(entry_comments)
                else:
                    comment_count = 0
                    
                if st.button(f"💬 コメント ({comment_count})", key=f"comment_{entry['id']}", use_container_width=True):
                    st.session_state[f'show_comments_{entry["id"]}'] = not st.session_state.get(f'show_comments_{entry["id"]}', False)
                    st.rerun()
            
            with col3:
                if entry_user == current_user:
                    if st.button("🗑️ 削除", key=f"delete_{entry['id']}", use_container_width=True):
                        # TODO: エントリー削除機能
                        pass
            
            # コメントセクション
            if st.session_state.get(f'show_comments_{entry["id"]}', False):
                st.markdown("---")
                st.markdown("**💬 コメント**")
                
                # 既存コメント表示
                if not comments_df.empty and 'entry_id' in comments_df.columns:
                    entry_comments = comments_df[comments_df['entry_id'] == entry['id']].sort_values('created_at')
                    for _, comment in entry_comments.iterrows():
                        comment_user = comment['user_id']
                        comment_name = settings.get(f'user_{comment_user.lower()}_name', f'ユーザー{comment_user}')
                        comment_avatar = settings.get(f'user_{comment_user.lower()}_avatar', '👤')
                        
                        st.markdown(f"""
                        <div class="comment-box">
                            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                                <div style="font-size: 16px;">{comment_avatar}</div>
                                <div style="font-size: 12px; font-weight: 700; color: #374151;">{comment_name}</div>
                            </div>
                            <div style="font-size: 14px; color: #374151;">{comment['comment_text']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # コメント追加
                new_comment = st.text_area(
                    "コメントを追加",
                    key=f"new_comment_{entry['id']}",
                    placeholder="コメントを書いてね",
                    height=60
                )
                
                if st.button("送信", key=f"send_comment_{entry['id']}", type="primary"):
                    if new_comment.strip():
                        if add_comment(entry['id'], current_user, new_comment):
                            st.success("コメントを追加しました")
                            st.rerun()
                    else:
                        st.warning("コメントを入力してください")


# ===== 設定タブ =====
elif st.session_state.tab == 'settings':
    st.markdown("### ⚙️ 設定")
    
    # ユーザー切り替え
    st.markdown("#### 👤 ユーザー切り替え")
    col1, col2 = st.columns(2)
    with col1:
        user_a_name = settings.get('user_a_name', 'ユーザーA')
        if st.button(f"{settings.get('user_a_avatar', '👦')} {user_a_name}", 
                    key="switch_to_a", 
                    use_container_width=True,
                    type="primary" if current_user == 'A' else "secondary"):
            st.session_state.current_user = 'A'
            st.rerun()
    
    with col2:
        user_b_name = settings.get('user_b_name', 'ユーザーB')
        if st.button(f"{settings.get('user_b_avatar', '👧')} {user_b_name}", 
                    key="switch_to_b", 
                    use_container_width=True,
                    type="primary" if current_user == 'B' else "secondary"):
            st.session_state.current_user = 'B'
            st.rerun()
    
    st.markdown("---")
    
    # プロフィール設定
    st.markdown("#### ✏️ プロフィール編集")
    
    # ユーザーAの設定
    st.markdown("**ユーザーA**")
    col1, col2 = st.columns([1, 3])
    with col1:
        new_avatar_a = st.text_input(
            "アバター",
            value=settings.get('user_a_avatar', '👦'),
            key="avatar_a",
            max_chars=2
        )
    with col2:
        new_name_a = st.text_input(
            "名前",
            value=settings.get('user_a_name', 'ユーザーA'),
            key="name_a"
        )
    
    if st.button("ユーザーAを更新", key="update_a", use_container_width=True):
        if update_settings('user_a_avatar', new_avatar_a) and update_settings('user_a_name', new_name_a):
            st.success("ユーザーAを更新しました")
            st.rerun()
    
    st.markdown("---")
    
    # ユーザーBの設定
    st.markdown("**ユーザーB**")
    col1, col2 = st.columns([1, 3])
    with col1:
        new_avatar_b = st.text_input(
            "アバター",
            value=settings.get('user_b_avatar', '👧'),
            key="avatar_b",
            max_chars=2
        )
    with col2:
        new_name_b = st.text_input(
            "名前",
            value=settings.get('user_b_name', 'ユーザーB'),
            key="name_b"
        )
    
    if st.button("ユーザーBを更新", key="update_b", use_container_width=True):
        if update_settings('user_b_avatar', new_avatar_b) and update_settings('user_b_name', new_name_b):
            st.success("ユーザーBを更新しました")
            st.rerun()
    
    st.markdown("---")
    
    # 記念日設定
    st.markdown("#### 💝 記念日設定")
    current_anniversary = settings.get('anniversary', str(date.today()))
    try:
        anniversary_date = datetime.strptime(current_anniversary, '%Y-%m-%d').date()
    except:
        anniversary_date = date.today()
    
    new_anniversary = st.date_input(
        "ふたりの記念日",
        value=anniversary_date,
        key="anniversary_input"
    )
    
    if st.button("記念日を更新", key="update_anniversary", use_container_width=True):
        if update_settings('anniversary', new_anniversary.isoformat()):
            st.success("記念日を更新しました")
            st.rerun()
    
    # 記念日からの日数
    days_together = (get_today_jst() - anniversary_date).days
    st.markdown(f"<div class='stat-box'><div style='font-size: 32px; font-weight: 800; color: #ec4899;'>{days_together}日</div><div style='font-size: 14px; color: #6b7280; margin-top: 4px;'>一緒に過ごした日々</div></div>", unsafe_allow_html=True)
