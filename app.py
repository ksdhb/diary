import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import json
import os

# ページ設定
st.set_page_config(
    page_title="📔 ふたりの日記",
    page_icon="📔",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# カスタムCSS
st.markdown("""
<style>
    .main { max-width: 430px; margin: 0 auto; padding-bottom: 80px; }
    .stButton>button { width: 100%; border-radius: 20px; font-weight: 700; }
    .card { background: rgba(255,255,255,0.9); border-radius: 20px; padding: 18px; margin: 12px 0; box-shadow: 0 4px 24px rgba(0,0,0,0.07); }
    .stat-box { border-radius: 16px; padding: 12px; text-align: center; background: linear-gradient(135deg,rgba(244,114,182,0.13),rgba(236,72,153,0.13)); }
    h1 { font-size: 20px !important; }
    h2 { font-size: 16px !important; color: #ec4899; }
    h3 { font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

# データベースパス
DB_PATH = "/tmp/diary.db"

# スタンプ定義
CONDITION_STAMPS = [
    {"emoji": "🤩", "label": "最高!"},
    {"emoji": "😊", "label": "良い"},
    {"emoji": "😐", "label": "普通"},
    {"emoji": "😔", "label": "微妙"},
    {"emoji": "😴", "label": "眠い"},
    {"emoji": "🤒", "label": "体調不良"},
]

DIARY_STAMPS = [
    {"emoji": "⭐", "label": "充実"},
    {"emoji": "😌", "label": "穏やか"},
    {"emoji": "😅", "label": "疲れた"},
    {"emoji": "😢", "label": "辛かった"},
    {"emoji": "🎉", "label": "楽しかった"},
    {"emoji": "💪", "label": "頑張った"},
]

AVATARS = ["🐱", "🐶", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐸", "🐧", "🦋", "🌸", "⭐", "🍀", "🌙", "☀️", "🍎", "🍓", "🎀"]

# データベース初期化
def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # エントリーテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            morning_stamp_emoji TEXT,
            morning_stamp_label TEXT,
            morning_message TEXT,
            evening_stamp_emoji TEXT,
            evening_stamp_label TEXT,
            evening_diary_text TEXT,
            evening_reactions TEXT,
            evening_reaction_msg TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # 設定テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # 初期設定の挿入
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        default_settings = [
            ("user_a_name", "あなた"),
            ("user_a_avatar", "🐱"),
            ("user_b_name", "パートナー"),
            ("user_b_avatar", "🐶"),
            ("anniversary", ""),
        ]
        cursor.executemany("INSERT INTO settings (key, value) VALUES (?, ?)", default_settings)
    
    conn.commit()
    conn.close()

# 設定の読み込み
def load_settings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return settings

# 設定の保存
def save_settings(settings):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for key, value in settings.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# エントリーの読み込み
def load_entries():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM entries ORDER BY entry_date DESC, created_at DESC", conn)
    conn.close()
    return df

# エントリーの保存
def save_entry(user_id, entry_date, morning=None, evening=None):
    import uuid
    from datetime import datetime
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 既存エントリーの確認
    cursor.execute("SELECT id FROM entries WHERE user_id = ? AND entry_date = ?", (user_id, entry_date))
    existing = cursor.fetchone()
    
    now = datetime.now().isoformat()
    
    if existing:
        entry_id = existing[0]
        updates = []
        params = []
        
        if morning:
            updates.extend([
                "morning_stamp_emoji = ?",
                "morning_stamp_label = ?",
                "morning_message = ?"
            ])
            params.extend([
                morning['stamp']['emoji'],
                morning['stamp']['label'],
                morning.get('message', '')
            ])
        
        if evening:
            reactions_json = json.dumps(evening.get('reactions', []))
            updates.extend([
                "evening_stamp_emoji = ?",
                "evening_stamp_label = ?",
                "evening_diary_text = ?",
                "evening_reactions = ?",
                "evening_reaction_msg = ?"
            ])
            params.extend([
                evening['stamp']['emoji'],
                evening['stamp']['label'],
                evening['diary_text'],
                reactions_json,
                evening.get('reaction_msg', '')
            ])
        
        updates.append("updated_at = ?")
        params.append(now)
        params.append(entry_id)
        
        query = f"UPDATE entries SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
    else:
        entry_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO entries (
                id, user_id, entry_date,
                morning_stamp_emoji, morning_stamp_label, morning_message,
                evening_stamp_emoji, evening_stamp_label, evening_diary_text,
                evening_reactions, evening_reaction_msg,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id, user_id, entry_date,
            morning['stamp']['emoji'] if morning else None,
            morning['stamp']['label'] if morning else None,
            morning.get('message', '') if morning else None,
            evening['stamp']['emoji'] if evening else None,
            evening['stamp']['label'] if evening else None,
            evening['diary_text'] if evening else None,
            json.dumps(evening.get('reactions', [])) if evening else None,
            evening.get('reaction_msg', '') if evening else None,
            now, now
        ))
    
    conn.commit()
    conn.close()

# 初期化
if 'initialized' not in st.session_state:
    init_database()
    st.session_state.initialized = True
    st.session_state.current_user = None
    st.session_state.tab = "home"

# 設定とデータの読み込み
settings = load_settings()
entries = load_entries()

# ユーザー選択
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

# ヘッダー
st.markdown(f"""
<div style='background: linear-gradient(135deg, #f472b6, #ec4899); padding: 14px 18px; border-radius: 10px; margin-bottom: 10px;'>
    <div style='display: flex; align-items: center; gap: 10px;'>
        <div style='font-size: 36px;'>{me['avatar']}</div>
        <div>
            <div style='color: white; font-weight: 800; font-size: 16px;'>📔 ふたりの日記</div>
            <div style='color: rgba(255,255,255,0.8); font-size: 10px;'>{me['name']} と {partner['name']}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# タブ
tab_col1, tab_col2, tab_col3, tab_col4 = st.columns(4)
with tab_col1:
    if st.button("🏠 ホーム"):
        st.session_state.tab = "home"
        st.rerun()
with tab_col2:
    if st.button("📅 カレンダー"):
        st.session_state.tab = "calendar"
        st.rerun()
with tab_col3:
    if st.button("📖 履歴"):
        st.session_state.tab = "history"
        st.rerun()
with tab_col4:
    if st.button("⚙️ 設定"):
        st.session_state.tab = "settings"
        st.rerun()

st.markdown("---")

# ホームタブ
if st.session_state.tab == "home":
    today_str = date.today().isoformat()
    
    # 統計
    if settings.get('anniversary'):
        try:
            anniv_date = datetime.strptime(settings['anniversary'], "%Y-%m-%d").date()
            days_since = (date.today() - anniv_date).days + 1
            st.markdown(f"""
            <div class='stat-box' style='margin-bottom: 12px;'>
                <div style='font-size: 22px;'>💑</div>
                <div style='font-size: 22px; font-weight: 800; color: #ec4899;'>{days_since}</div>
                <div style='font-size: 10px; color: #888;'>日目</div>
            </div>
            """, unsafe_allow_html=True)
        except:
            pass
    
    # 今日のエントリー
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"### 📅 今日 — {me['avatar']} {me['name']}")
    
    today_entries = entries[entries['entry_date'] == today_str] if not entries.empty else pd.DataFrame()
    my_today = today_entries[today_entries['user_id'] == st.session_state.current_user]
    
    has_morning = not my_today.empty and pd.notna(my_today.iloc[0]['morning_stamp_emoji']) if not my_today.empty else False
    has_evening = not my_today.empty and pd.notna(my_today.iloc[0]['evening_stamp_emoji']) if not my_today.empty else False
    
    if not my_today.empty and has_morning:
        entry = my_today.iloc[0]
        st.markdown(f"""
        <div style='background: #fffbeb; border: 1.5px solid #fde68a; border-radius: 14px; padding: 12px; margin: 8px 0;'>
            <div style='font-size: 11px; font-weight: 700; color: #b45309; margin-bottom: 6px;'>☀️ 朝の体調</div>
            <div style='font-size: 26px;'>{entry['morning_stamp_emoji']} {entry['morning_stamp_label']}</div>
            {f"<div style='background: #fef9c3; border-radius: 10px; padding: 7px 10px; margin-top: 8px; font-size: 13px; color: #78350f;'>💬 {entry['morning_message']}</div>" if entry['morning_message'] else ""}
        </div>
        """, unsafe_allow_html=True)
    
    if not my_today.empty and has_evening:
        entry = my_today.iloc[0]
        st.markdown(f"""
        <div style='background: #f5f3ff; border: 1.5px solid #ddd6fe; border-radius: 14px; padding: 12px; margin: 8px 0;'>
            <div style='font-size: 11px; font-weight: 700; color: #ec4899; margin-bottom: 6px;'>🌙 夜の日記</div>
            <div style='font-size: 26px;'>{entry['evening_stamp_emoji']} {entry['evening_stamp_label']}</div>
            <div style='font-size: 14px; color: #333; margin-top: 8px;'>{entry['evening_diary_text']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    if my_today.empty or not has_morning:
        st.info("まだ投稿していません")
    
    # アクションボタン
    if not has_morning:
        if st.button("☀️ 朝の体調を投稿", use_container_width=True, type="primary"):
            st.session_state.modal = "morning"
            st.rerun()
    
    if has_morning and not has_evening:
        if st.button("🌙 夜の日記を投稿", use_container_width=True, type="primary"):
            st.session_state.modal = "evening"
            st.rerun()
    
    if has_morning and has_evening:
        st.success("✅ 今日はすべて投稿済み!")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # パートナーの今日
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"### 📅 今日 — {partner['avatar']} {partner['name']}")
    
    partner_today = today_entries[today_entries['user_id'] == partner['id']]
    
    if not partner_today.empty:
        entry = partner_today.iloc[0]
        if pd.notna(entry['morning_stamp_emoji']):
            st.markdown(f"""
            <div style='background: #fffbeb; border: 1.5px solid #fde68a; border-radius: 14px; padding: 12px; margin: 8px 0;'>
                <div style='font-size: 11px; font-weight: 700; color: #b45309; margin-bottom: 6px;'>☀️ 朝の体調</div>
                <div style='font-size: 26px;'>{entry['morning_stamp_emoji']} {entry['morning_stamp_label']}</div>
                {f"<div style='background: #fef9c3; border-radius: 10px; padding: 7px 10px; margin-top: 8px; font-size: 13px; color: #78350f;'>💬 {entry['morning_message']}</div>" if entry['morning_message'] else ""}
            </div>
            """, unsafe_allow_html=True)
        
        if pd.notna(entry['evening_stamp_emoji']):
            st.markdown(f"""
            <div style='background: #f5f3ff; border: 1.5px solid #ddd6fe; border-radius: 14px; padding: 12px; margin: 8px 0;'>
                <div style='font-size: 11px; font-weight: 700; color: #ec4899; margin-bottom: 6px;'>🌙 夜の日記</div>
                <div style='font-size: 26px;'>{entry['evening_stamp_emoji']} {entry['evening_stamp_label']}</div>
                <div style='font-size: 14px; color: #333; margin-top: 8px;'>{entry['evening_diary_text']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"{partner['name']}はまだ投稿していません 🌿")
    
    st.markdown("</div>", unsafe_allow_html=True)

# カレンダータブ
elif st.session_state.tab == "calendar":
    st.markdown("### 📅 カレンダー")
    
    if not entries.empty:
        # 日付ごとにグループ化
        cal_data = entries.groupby('entry_date').size().reset_index(name='投稿数')
        cal_data.columns = ['日付', '投稿数']
        
        st.dataframe(
            cal_data,
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("まだ日記がありません")

# 履歴タブ
elif st.session_state.tab == "history":
    st.markdown("### 📖 履歴")
    
    if not entries.empty:
        for _, entry in entries.head(20).iterrows():
            user = me if entry['user_id'] == st.session_state.current_user else partner
            
            with st.expander(f"{user['avatar']} {user['name']} - {entry['entry_date']}"):
                if pd.notna(entry['morning_stamp_emoji']):
                    st.markdown(f"**☀️ 朝の体調:** {entry['morning_stamp_emoji']} {entry['morning_stamp_label']}")
                    if entry['morning_message']:
                        st.markdown(f"💬 {entry['morning_message']}")
                
                if pd.notna(entry['evening_stamp_emoji']):
                    st.markdown(f"**🌙 夜の日記:** {entry['evening_stamp_emoji']} {entry['evening_stamp_label']}")
                    st.markdown(entry['evening_diary_text'])
    else:
        st.info("まだ日記がありません")

# 設定タブ
elif st.session_state.tab == "settings":
    st.markdown("### ⚙️ 設定")
    
    with st.form("settings_form"):
        st.markdown("**👤 名前・アバター**")
        
        col1, col2 = st.columns(2)
        with col1:
            new_a_avatar = st.selectbox(f"{settings['user_a_name']} アバター", AVATARS, index=AVATARS.index(settings['user_a_avatar']) if settings['user_a_avatar'] in AVATARS else 0)
            new_a_name = st.text_input(f"{settings['user_a_name']} 名前", value=settings['user_a_name'])
        
        with col2:
            new_b_avatar = st.selectbox(f"{settings['user_b_name']} アバター", AVATARS, index=AVATARS.index(settings['user_b_avatar']) if settings['user_b_avatar'] in AVATARS else 1)
            new_b_name = st.text_input(f"{settings['user_b_name']} 名前", value=settings['user_b_name'])
        
        st.markdown("**💑 記念日**")
        new_anniversary = st.date_input("記念日", value=datetime.strptime(settings['anniversary'], "%Y-%m-%d").date() if settings.get('anniversary') else None)
        
        if st.form_submit_button("保存する", use_container_width=True, type="primary"):
            new_settings = {
                "user_a_name": new_a_name,
                "user_a_avatar": new_a_avatar,
                "user_b_name": new_b_name,
                "user_b_avatar": new_b_avatar,
                "anniversary": new_anniversary.isoformat() if new_anniversary else "",
            }
            
            save_settings(new_settings)
            st.success("設定を保存しました!")
            st.rerun()
    
    if st.button("ユーザーを切り替える"):
        st.session_state.current_user = None
        st.rerun()

# モーダル処理（朝・夜の投稿）
if 'modal' in st.session_state and st.session_state.modal == "morning":
    st.markdown("---")
    st.markdown("### ☀️ 朝の体調報告")
    st.markdown(f"今日の体調・気分は? → {partner['name']}に伝えよう")
    
    cols = st.columns(3)
    for i, stamp in enumerate(CONDITION_STAMPS):
        with cols[i % 3]:
            if st.button(f"{stamp['emoji']}\n{stamp['label']}", key=f"morning_{i}", use_container_width=True):
                st.session_state.selected_morning_stamp = stamp
    
    if 'selected_morning_stamp' in st.session_state:
        st.success(f"選択中: {st.session_state.selected_morning_stamp['emoji']} {st.session_state.selected_morning_stamp['label']}")
        message = st.text_input(f"💬 {partner['name']}へひとこと(任意)", max_chars=60, key="morning_msg")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("投稿する", type="primary", use_container_width=True):
                morning_data = {"stamp": st.session_state.selected_morning_stamp, "message": message}
                save_entry(st.session_state.current_user, date.today().isoformat(), morning=morning_data)
                st.success("朝の投稿を保存しました!")
                del st.session_state.modal
                del st.session_state.selected_morning_stamp
                st.rerun()
        with col2:
            if st.button("キャンセル", use_container_width=True):
                del st.session_state.modal
                if 'selected_morning_stamp' in st.session_state:
                    del st.session_state.selected_morning_stamp
                st.rerun()

elif 'modal' in st.session_state and st.session_state.modal == "evening":
    st.markdown("---")
    st.markdown("### 🌙 夜の日記")
    st.markdown("今日はどんな一日だった?")
    
    cols = st.columns(3)
    for i, stamp in enumerate(DIARY_STAMPS):
        with cols[i % 3]:
            if st.button(f"{stamp['emoji']}\n{stamp['label']}", key=f"evening_{i}", use_container_width=True):
                st.session_state.selected_evening_stamp = stamp
    
    if 'selected_evening_stamp' in st.session_state:
        st.success(f"選択中: {st.session_state.selected_evening_stamp['emoji']} {st.session_state.selected_evening_stamp['label']}")
        diary_text = st.text_area("今日のひとこと", max_chars=140, height=100, key="evening_diary")
        reaction_msg = st.text_input(f"💌 {partner['name']}へひとこと(任意)", max_chars=60, key="evening_reaction")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("投稿する", type="primary", use_container_width=True, disabled=not diary_text.strip()):
                evening_data = {"stamp": st.session_state.selected_evening_stamp, "diary_text": diary_text, "reaction_msg": reaction_msg}
                save_entry(st.session_state.current_user, date.today().isoformat(), evening=evening_data)
                st.success("夜の投稿を保存しました!")
                del st.session_state.modal
                del st.session_state.selected_evening_stamp
                st.rerun()
        with col2:
            if st.button("キャンセル", use_container_width=True):
                del st.session_state.modal
                if 'selected_evening_stamp' in st.session_state:
                    del st.session_state.selected_evening_stamp
                st.rerun()
