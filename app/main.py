from flask import Flask, render_template, request, redirect, url_for
from app.models import db, Memo
from dotenv import load_dotenv
from flask_migrate import Migrate
import os
from uuid import UUID
from datetime import datetime, timedelta

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


@app.before_request
def create_tables():
    db.create_all()

# メモ一覧を表示
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
