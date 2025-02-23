from flask import Flask, render_template, request, redirect, url_for
from app.models import db, Memo
from dotenv import load_dotenv
import os
from uuid import UUID
from flask import jsonify
from pywebpush import webpush
import json

# .envファイルを読み込む
load_dotenv()


# VAPIDキーを環境変数から取得
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")

if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
    print("❌ VAPID 公開鍵または秘密鍵が見つかりません。`.env` を確認してください。")
else:
    print("✅ VAPID_PUBLIC_KEY 読み込み成功！")
# 確認用（後で削除する）
print("VAPID_PUBLIC_KEY:", VAPID_PUBLIC_KEY)

# 環境変数からデータベース接続情報を取得
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')

app = Flask(__name__)

# SQLAlchemy設定
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.before_request
def create_tables():
    db.create_all()

# メモ一覧を表示
@app.route('/')
def index():
    memos = Memo.query.order_by(Memo.created_at.desc()).all()
    return render_template('index.html', memos=memos)

# メモの詳細を表示
@app.route('/memo/<uuid:memo_id>')
def view_memo(memo_id):
    memo = Memo.query.get_or_404(str(memo_id))
    return render_template('view_memo.html', memo=memo)

# 新しいメモの作成フォームを表示
@app.route('/create', methods=['GET'])
def show_create_memo():
    return render_template('create_memo.html')

# 購読データを保存しておく（超簡易版: メモリに保存するだけ）
subscriptions = []

@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.json
    # 本来はDBに保存するのが望ましいが、まずは動作テストのために配列に入れる
    subscriptions.append(data)
    return jsonify({"success": True})

@app.route('/send_push', methods=['POST'])
def send_push():
    data = request.json  # { "title": "...", "body": "..." } など
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps({
                    "title": data["title"],
                    "body": data["body"]
                }),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:example@example.com"}
            )
        except Exception as e:
            print("❌ Push通知エラー:", e)
            return jsonify({"error": str(e)}), 500
    return jsonify({"success": True})

# 新しいメモを作成
@app.route('/create', methods=['POST'])
def create_memo():
    title = request.form['title']
    content = request.form['content']
    new_memo = Memo(title=title, content=content)
    db.session.add(new_memo)
    db.session.commit()

    # メモ作成後に通知を送る
    requests.post("http://localhost:5000/send_push", json={
        "title": "新しいメモが追加されました",
        "body": f"「{title}」が作成されました！"
    })


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
    db.session.commit()
    return redirect(url_for('view_memo', memo_id=memo_id))


@app.route('/get_public_key', methods=['GET'])
def get_public_key():
    return jsonify(VAPID_PUBLIC_KEY)




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
