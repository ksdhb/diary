# 📔 ふたりの日記 (Couple's Diary)

カップル専用の日記アプリ。朝の体調報告、夜の日記、コメント機能、カレンダー表示など、ふたりの思い出を記録できます。

## 🌟 特徴

* **朝の体調報告** - スタンプで簡単に今日の調子を共有
* **夜の日記** - 今日の気分と出来事を記録、写真もアップロード可能
* **コメント機能** - パートナーの日記にコメントを残せる
* **カレンダー** - 月ごとの投稿をカレンダー形式で確認
* **お気に入り** - 大切な日記をお気に入り登録
* **統計情報** - 記念日からの日数、連続投稿日数を表示
* **スマホ完全対応** - iPhone/Androidブラウザで快適に使える

## 📊 データ保存

**Googleスプレッドシート**をデータベースとして使用します。データはGoogleドライブに永続保存されるため、アプリを再起動してもデータが消えません。

---

## 🚀 永続的なデプロイ手順（Streamlit Cloud - 無料）

### 必要なもの
* Googleアカウント（スプレッドシート用）
* GitHubアカウント（無料）

---

### ステップ1: Googleスプレッドシートの準備 ✅

#### 1-1. スプレッドシート作成
1. [Google Sheets](https://sheets.google.com/)にアクセス
2. 「空白のスプレッドシート」を作成
3. 名前を「ふたりの日記」に変更
4. URLから**スプレッドシートID**をメモ
   ```
   https://docs.google.com/spreadsheets/d/【ここがID】/edit
   ```

#### 1-2. Google Cloud Platform設定
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成（例: `couple-diary`）
3. 「APIとサービス」→「ライブラリ」で以下を有効化：
   * **Google Sheets API**
   * **Google Drive API**
4. 「APIとサービス」→「認証情報」→「認証情報を作成」→「サービスアカウント」
5. サービスアカウント名を入力（例: `diary-app`）
6. 作成後、「キー」タブ→「鍵を追加」→「新しい鍵を作成」
7. **JSON形式**を選択してダウンロード ← **このファイルを保存！**

#### 1-3. スプレッドシートに権限付与
1. ダウンロードしたJSONファイルを開く
2. `"client_email"` の値をコピー（例: `diary-app@...iam.gserviceaccount.com`）
3. スプレッドシートを開く
4. 右上の「共有」ボタンをクリック
5. コピーしたメールアドレスを追加、**編集者**権限を付与

---

### ステップ2: GitHubリポジトリ作成

#### 2-1. 必要なファイルをダウンロード
Databricksワークスペースから以下のファイルをダウンロード：
* `app.py`
* `requirements.txt`
* `README.md`
* `.gitignore`

#### 2-2. GitHubリポジトリを作成
1. [GitHub](https://github.com/)にログイン
2. 右上の「+」→「New repository」
3. リポジトリ名: `couple-diary`（任意）
4. 「Public」を選択（無料プラン用）
5. 「Create repository」をクリック

#### 2-3. ファイルをアップロード
GitHubリポジトリページで：
1. 「uploading an existing file」をクリック
2. ダウンロードした4ファイルをドラッグ&ドロップ
3. 「Commit changes」をクリック

---

### ステップ3: Streamlit Cloudにデプロイ

#### 3-1. Streamlit Cloudに登録
1. [Streamlit Cloud](https://streamlit.io/cloud)にアクセス
2. 「Sign up」をクリック
3. **GitHubアカウント**でサインイン

#### 3-2. アプリをデプロイ
1. ダッシュボードで「New app」をクリック
2. 設定を入力：
   * **Repository**: `あなたのユーザー名/couple-diary`
   * **Branch**: `main`
   * **Main file path**: `app.py`
3. 「Advanced settings」をクリック

#### 3-3. Secretsを設定（重要！）
「Secrets」欄に以下を貼り付け：

```toml
spreadsheet_key = "あなたのスプレッドシートID"

[gcp_service_account]
type = "service_account"
project_id = "【JSONのproject_id】"
private_key_id = "【JSONのprivate_key_id】"
private_key = "【JSONのprivate_key - 改行を含めてそのまま】"
client_email = "【JSONのclient_email】"
client_id = "【JSONのclient_id】"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "【JSONのclient_x509_cert_url】"
universe_domain = "googleapis.com"
```

**ポイント**:
* `spreadsheet_key`：ステップ1-1でメモしたID
* `gcp_service_account`：ステップ1-2でダウンロードしたJSONの内容
* `private_key`は改行（`\n`）をそのまま含める

#### 3-4. デプロイ！
「Deploy!」ボタンをクリック → 数分待つ

#### 3-5. 完成！
デプロイが完了すると、永続的なURL（例: `https://couple-diary-xxxxx.streamlit.app`）が発行されます。

このURLは：
* ✅ **永続的**（消えません）
* ✅ **無料**
* ✅ **スマホ対応**
* ✅ **パートナーと共有可能**

---

## 📱 使い方

### 初回起動時
1. アプリURLを開く
2. 「あなた」または「パートナー」を選択

### 日記を書く
* **朝の投稿**: 「☀️ 朝の投稿」ボタンから体調スタンプを選択
* **夜の投稿**: 「🌙 夜の投稿」ボタンから気分スタンプと日記を記入

### コメントを残す
1. パートナーの日記の下部にコメント入力欄があります
2. コメントを入力して「送信」ボタンをクリック

### 設定
1. 「⚙️ 設定」タブをクリック
2. ユーザー名、アバター、記念日を設定可能

---

## 🛠️ 技術スタック

* **フロントエンド**: Streamlit
* **データベース**: Google Sheets (gspread経由)
* **画像処理**: Pillow
* **認証**: OAuth 2.0 (Service Account)
* **デプロイ**: Streamlit Cloud

---

## 📝 データ構造

### entriesシート
| 列名 | 説明 |
|------|------|
| id | エントリーID (UUID) |
| user_id | ユーザーID (A or B) |
| entry_date | 日付 (YYYY-MM-DD) |
| morning_stamp_emoji | 朝のスタンプ絵文字 |
| morning_stamp_label | 朝のスタンプラベル |
| morning_message | 朝のメッセージ |
| evening_stamp_emoji | 夜のスタンプ絵文字 |
| evening_stamp_label | 夜のスタンプラベル |
| evening_diary_text | 夜の日記本文 |
| image_data | 画像データ (Base64) |
| is_favorite | お気に入りフラグ (0 or 1) |
| created_at | 作成日時 (ISO 8601) |
| updated_at | 更新日時 (ISO 8601) |

### commentsシート
| 列名 | 説明 |
|------|------|
| id | コメントID (UUID) |
| entry_id | 関連エントリーID |
| user_id | コメント投稿者ID |
| comment_text | コメント本文 |
| created_at | 作成日時 (ISO 8601) |

### settingsシート
| 列名 | 説明 |
|------|------|
| key | 設定キー |
| value | 設定値 |

---

## 🐛 トラブルシューティング

### "スプレッドシート接続エラー"が表示される
* Streamlit CloudのSecretsが正しく設定されているか確認
* Google Sheets API/Drive APIが有効化されているか確認
* サービスアカウントにスプレッドシートの編集権限があるか確認
* `private_key`に改行（`\n`）が含まれているか確認

### データが表示されない
* スプレッドシートに3つのシート（entries, comments, settings）が自動作成されているか確認
* Streamlit Cloudのログを確認（アプリページの右下「Manage app」→「Logs」）

### 画像がアップロードできない
* 画像サイズが大きすぎる可能性（自動で800x800にリサイズされます）
* JPG/PNG形式か確認

### アプリがスリープする
* Streamlit Cloud無料プランは1週間アクセスがないとスリープします
* アクセスすれば自動的に再起動します（データは消えません）

---

## 🔧 ローカル開発（オプション）

ローカル環境でテストする場合：

```bash
# リポジトリをクローン
git clone https://github.com/あなたのユーザー名/couple-diary.git
cd couple-diary

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate

# パッケージインストール
pip install -r requirements.txt

# Secretsファイル作成
mkdir .streamlit
nano .streamlit/secrets.toml  # 上記のSecretsを貼り付け

# アプリ起動
streamlit run app.py
```

---

## 📄 ライセンス

MIT License

---

❤️ ふたりの思い出を大切に記録しましょう
