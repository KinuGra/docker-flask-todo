FROM python:3.11-slim

# 作業ディレクトリを /app に設定
WORKDIR /app

# requirements.txt をコンテナにコピー
COPY requirements.txt .

# パッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# 環境変数の設定（FLASK_APPの指定）
ENV FLASK_APP=main.py

# Flask のポートを公開
EXPOSE 5000

# Flask アプリを起動
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]