from flask import Flask, render_template, request, redirect, url_for, jsonify
from app.models import db, Memo
from dotenv import load_dotenv
from flask_migrate import Migrate
import os
import requests
from uuid import UUID

import google.generativeai as genai
import traceback  # 追加


# .envファイルを読み込む
load_dotenv()

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
migrate = Migrate(app, db)  # Flask-Migrate の設定

# 環境変数から Gemini APIキーを取得
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

@app.route("/memo/<uuid:memo_id>/summarize", methods=["POST"])
def summarize_memo(memo_id):
    memo = Memo.query.get_or_404(str(memo_id))

    if not memo.content:
        return jsonify({"summary": "内容がありません"}), 400

    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": f"要約してください: {memo.content}"}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 100},
    }

    response = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        headers=headers,
        json=data
    )

    if response.status_code != 200:
        return jsonify({"error": "要約の取得に失敗しました"}), 500

    result = response.json()
    summary = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "要約できませんでした")

    memo.summary = summary
    db.session.commit()

    return jsonify({"summary": summary})


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

@app.route('/create', methods=['POST'])
def create_memo():
    title = request.form['title']
    content = request.form['content']
    deadline = request.form.get('deadline')
    new_memo = Memo(title=title, content=content, deadline=deadline if deadline else None)
    db.session.add(new_memo)
    db.session.commit()

    # 自動で要約を取得
    summarize_memo(new_memo.id)

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

    # 更新後に要約を取得
    summarize_memo(memo.id)

    return redirect(url_for('view_memo', memo_id=memo_id))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
