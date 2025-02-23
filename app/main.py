from flask import Flask, render_template, request, redirect, url_for, session
from app.models import db, Memo
from dotenv import load_dotenv
from flask_migrate import Migrate
import os
from uuid import UUID
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# .envファイルを読み込む
load_dotenv()

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

# メモ一覧を表示
@app.route('/')
def index():
    sort = request.args.get('sort', 'created_at_desc')
    if sort == 'deadline_asc':
        memos = Memo.query.order_by(Memo.deadline.asc()).all()
    elif sort == 'deadline_desc':
        memos = Memo.query.order_by(Memo.deadline.desc()).all()
    else:
        memos = Memo.query.order_by(Memo.created_at.desc()).all()
    return render_template('index.html', memos=memos)


#sabo
@app.route('/memo/<uuid:memo_id>/toggle_complete', methods=['POST'])
def toggle_complete(memo_id):
    memo = Memo.query.get_or_404(str(memo_id))

    # チェックボックスが送信されていれば "True"、外れていれば None
    completed_form_value = request.form.get('completed')
    memo.completed = (completed_form_value == 'True')

    db.session.commit()
    return redirect(url_for('index'))

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
        redirect_uri=url_for('google_callback', _external=True)
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
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS,
        scopes=SCOPES,
        redirect_uri=url_for('google_callback', _external=True)
    )

    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    # アクセストークンやリフレッシュトークンなどをセッションに保存（デモ用）
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

    return "Googleアカウントとの連携が完了しました。<br><a href='/send_test_mail'>テストメール送信</a>"

@app.route('/send_test_mail')
def send_test_mail():
    """
    セッションに保存したトークンを使ってGmail APIでメールを送信するテスト。
    URLパラメータ notify=off なら、メール送信をスキップします。
    """
    if request.args.get('notify', 'on') == 'off':
        return "メール通知はオフに設定されています。"

    if 'credentials' not in session:
        return "認証情報がありません。<a href='/google_login'>Googleログイン</a>"

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

    message = MIMEText('これはテストメールです。')
    message['to'] = 'taiki.msw.sabu@gmail.com'  # ここを実際のアドレスに変更
    message['subject'] = 'Gmail APIテスト'
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        return "メール送信に成功しました。"
    except Exception as e:
        return f"メール送信に失敗しました: {str(e)}"

    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
