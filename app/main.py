from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from app.models import db, Memo
from dotenv import load_dotenv
from flask_migrate import Migrate
import os
from uuid import UUID
from datetime import datetime, timedelta

import logging
from google import genai
import google.auth.credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import id_token
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials


# .envファイルを読み込む
load_dotenv()

# 環境変数からAPIキーを取得
# Gmail APIの認証情報をcredentials.jsonから読み込む
GOOGLE_CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'credentials.json')

# Gemini APIの初期化
api_key = os.getenv('YOUR_API_KEY')
if not api_key:
    raise ValueError("APIキーが設定されていません。")
client = genai.Client(api_key=api_key)
# response = client.models.generate_content(
#     model="gemini-2.0-flash", contents="ここにgeminiに与えるプロンプトを入れる"
# )

# 環境変数からデータベース接続情報を取得
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')

app = Flask(__name__)
app.secret_key = 'SECRET_KEY'  # 適当な秘密鍵を設定してください

# SQLAlchemy設定
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)  # Flask-Migrate の設定


@app.before_request
def create_tables():
    db.create_all()

def recognize_speech(audio_file):
    r = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = r.record(source)

    try:
        text = r.recognize_google(audio, language='ja-JP')
        return text
    except sr.UnknownValueError:
        return "音声が認識できませんでした"
    except sr.RequestError as e:
        return f"音声認識APIへのリクエストに失敗しました: {e}"
    

@app.route('/speech', methods=['POST'])
def speech():
    data = request.get_json()
    text = data.get('text')

    if not text:
        return jsonify({'error': 'テキストがありません'}), 400

    # 音声認識の結果をメモとして追加
    new_memo = Memo(title=text, content="")
    db.session.add(new_memo)
    db.session.commit()
    print(f"New memo created with id: {new_memo.id}, title: {new_memo.title}")

    # indexにリダイレクト
    return redirect(url_for('index'))
@app.route('/')
def index():
    sort = request.args.get('sort', 'created_at_desc')
    filter = request.args.get('filter', None)
    query = Memo.query

    if filter == 'week':
        one_week_later = datetime.now() + timedelta(days=7)
        query = query.filter(Memo.deadline <= one_week_later, Memo.deadline >= datetime.now())

    if sort == 'deadline_asc':
        memos = query.order_by(Memo.deadline.asc()).all()
    elif sort == 'deadline_desc':
        memos = query.order_by(Memo.deadline.desc()).all()
    else:
        memos = query.order_by(Memo.created_at.desc()).all()

    return render_template('index.html', memos=memos)

@app.route('/summarize', methods=['GET'])
def summarize_tasks():
    memos = Memo.query.all()
    prompt = "1. **のようなマークダウン記法は使わない方法で見やすく答えて\n2. 20行以内にまとめて\n3. まずどのタスクからこなすべきですか？\n4. 以下のタスクを効率的にこなすための助言を、中学生でもわかるように教えて:\n"
    for memo in memos:
        prompt += f"タイトル: {memo.title}\n詳細: {memo.content}\n期限: {memo.deadline}\n\n"

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )
    ai_summary = response.text

    return render_template('summary.html', ai_summary=ai_summary)

@app.route('/memo/<uuid:memo_id>/toggle_complete', methods=['POST'])
def toggle_complete(memo_id):
    memo = Memo.query.get_or_404(str(memo_id))

    # チェックボックスが送信されていれば "True"、外れていれば None
    completed_form_value = request.form.get('completed')
    memo.completed = (completed_form_value == 'True')

    db.session.commit()

    # 現在の並び替えパラメータを取得
    sort = request.form.get('sort', 'created_at_desc')
    filter = request.form.get('filter', None)

    return redirect(url_for('index', sort=sort, filter=filter))

# メモの詳細を表示
@app.route('/memo/<uuid:memo_id>')
def view_memo(memo_id):
    memo = Memo.query.get_or_404(str(memo_id))
    return render_template('view_memo.html', memo=memo)

# 新しいメモの作成フォームを表示
@app.route('/create', methods=['GET'])
def show_create_memo():
    return render_template('create_memo.html')

# 新しいメモを作成
@app.route('/create', methods=['POST'])
def create_memo():
    title = request.form['title']
    content = request.form['content']
    deadline = request.form.get('deadline')
    new_memo = Memo(title=title, content=content, deadline=deadline if deadline else None)
    db.session.add(new_memo)
    db.session.commit()
    return redirect(url_for('index'))

# メモを削除
# ===============================
# エンドポイント /memo/(メモのID)/delete
# メソッド　　POST
# 返すもの　index.html (リダイレクト)
# ===============================
@app.route('/memo/<uuid:memo_id>/delete', methods=['POST'])
def delete_memo(memo_id):
    memo = Memo.query.get_or_404(str(memo_id))
    db.session.delete(memo)
    db.session.commit()
    return redirect(url_for('index'))

# 編集フォーム
@app.route('/memo/<uuid:memo_id>/edit', methods=['GET'])
def edit_memo(memo_id):
    memo = Memo.query.get_or_404(str(memo_id))
    return render_template('edit_memo.html', memo=memo)

# 編集内容の保存
@app.route('/memo/<uuid:memo_id>/edit', methods=['POST'])
def update_memo(memo_id):
    memo = Memo.query.get_or_404(str(memo_id))
    memo.title = request.form['title']
    memo.content = request.form['content']
    deadline = request.form.get('deadline')
    memo.deadline = deadline if deadline else None
    db.session.commit()
    return redirect(url_for('view_memo', memo_id=memo_id))

# ---- (A) OAuth フローの準備 ----
# credentials.json のパス (プロジェクトルートに配置している想定)
GOOGLE_CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'credentials.json')

# スコープ: Gmailでの送信を行うために、以下を指定
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

@app.route('/google_login')
def google_login():
    """
    ユーザーをGoogleの認証ページへリダイレクトする。
    ローカルの場合、http://localhost:3000/google_callback に返ってくる。
    """
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS,
        scopes=SCOPES,
        #redirect_uri=url_for('google_callback', _external=True)
        redirect_uri="http://localhost:3000/google_callback"  # ここを固定
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/google_callback')
def google_callback():
    """
    GoogleからリダイレクトされるコールバックURL。
    ここで認証コードを受け取り、アクセストークンを取得する。
    """
    credentials = None  # ここであらかじめ初期化しておく
    try:
        flow = Flow.from_client_secrets_file(
            GOOGLE_CLIENT_SECRETS,
            scopes=SCOPES,
            #redirect_uri=url_for('google_callback', _external=True)
            redirect_uri="http://localhost:3000/google_callback"  # ここを固定
        )

        logging.error(request.url)
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials
        # アクセストークンやリフレッシュトークンなどをセッションに保存（デモ用）
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat(),  # 文字列に変換
        }
        session.permanent = True  # 永続セッションを使用

        # もし「ログイン中かどうか」をフラグ管理したい場合は下記を追加
        session['logged_in'] = True

        # 認証完了メッセージを直接返す場合:
        # return "Googleアカウントとの連携が完了しました。<br><a href='/send_test_mail'>テストメール送信</a>", 200, {'Content-Type': 'text/html'}

        # 今はgoogle_callback.htmlテンプレートを返しているので、以下でOK
        return render_template('google_callback.html')

    except Exception as e:
        logging.error(e)
        # 以下をexceptブロック内に追加
        logging.error(f"Credentials: {credentials}")
        if credentials:
            logging.error(f"Refresh token: {credentials.refresh_token}")
        return f"Googleアカウントとの連携に失敗しました: {str(e)}", 500, {'Content-Type': 'text/html'}
    
@app.route('/logout')
def logout():
    session.clear()  # セッションを丸ごとクリア
    return redirect(url_for('index'))



# ------------------------------------------------------------------
# もしファイル先頭部に無ければ追加してください。
# from google.oauth2.credentials import Credentials
# ------------------------------------------------------------------

@app.route('/send_test_mail')
def send_test_mail():
    """
    セッションに保存したトークンを使ってGmail APIでメールを送信するテスト。
    URLパラメータ notify=off なら、メール送信をスキップします。
    """
    # もし「?notify=off」がURLについていたら送信をスキップする
    if request.args.get('notify', 'on') == 'off':
        message = "メール通知はオフに設定されています。"
        return render_template('send_test_mail.html', message=message)

    # セッションに認証情報がなければログインを促す
    if 'credentials' not in session:
        message = "認証情報がありません。<a href='/google_login'>Googleログイン</a>"
        return render_template('send_test_mail.html', message=message)

    # セッションからOAuthトークン情報を取り出し、Credentialsを生成
    creds_info = session['credentials']
    creds = Credentials(
        token=creds_info['token'],
        refresh_token=creds_info['refresh_token'],
        token_uri=creds_info['token_uri'],
        client_id=creds_info['client_id'],
        client_secret=creds_info['client_secret'],
        scopes=creds_info['scopes']
    )

    # Gmail APIクライアントを構築
    service = build('gmail', 'v1', credentials=creds)

    # メール本文作成に必要なクラスをインポート
    from email.mime.text import MIMEText
    import base64

    # 送信するメールの本文を組み立て
    message = MIMEText('これはテストメールです。')
    message['to'] = 'abcabcd@kagi.be'  # ここを実際のアドレスに変更
    message['subject'] = 'Gmail APIテスト'
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        # メールの送信を実行
        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        message = "メール送信に成功しました。"
    except Exception as e:
        message = f"メール送信に失敗しました: {str(e)}"

    return render_template('send_test_mail.html', message=message)

@app.route('/memo/<uuid:memo_id>/send_mail', methods=['POST'])
def send_mail_for_memo(memo_id):
    """
    このメモに関するメールを送信する処理
    """
    # 例: ログイン必須なら
    if 'credentials' not in session:
        return redirect(url_for('google_login'))

    # メモを取得
    memo = Memo.query.get_or_404(str(memo_id))

    # ここから先はsend_test_mail()と同じ要領でGmail API送信する
    creds_info = session['credentials']
    creds = Credentials(
        token=creds_info['token'],
        refresh_token=creds_info['refresh_token'],
        token_uri=creds_info['token_uri'],
        client_id=creds_info['client_id'],
        client_secret=creds_info['client_secret'],
        scopes=creds_info['scopes']
    )
    service = build('gmail', 'v1', credentials=creds)

    from email.mime.text import MIMEText
    import base64

    # メール本文を作成 (メモの情報を使うなど)
    mail_text = f"【タスク】\n\nタイトル: {memo.title}\n詳細: {memo.content}\n"
    if memo.deadline:
        mail_text += f"期限: {memo.deadline}\n"

    message = MIMEText(mail_text)
    message['to'] = 'abcabcd@kagi.be'  # 宛先
    message['subject'] = f"タスク通知: {memo.title}"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        # 送信が終わったらindexへ飛ばす or 何かメッセージ表示
        return redirect(url_for('index'))
    except Exception as e:
        return f"メール送信に失敗: {e}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
