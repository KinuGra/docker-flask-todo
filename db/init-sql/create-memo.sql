-- テーブル作成
CREATE TABLE IF NOT EXISTS Memo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);

-- ダミーデータ挿入
INSERT INTO Memo (id, title, content, created_at, updated_at) VALUES
('9c1a2b3d-5e67-48fa-910b-2d3c456789ab', 'プレゼン資料作成', 'マーケティング戦略についてのスライドを作成し、リハーサルを実施。2月10日 15時締め切り', '2025-02-01 10:30:45.123456', '2025-02-01 10:30:45.123456'),
('8b2d3c4e-6f78-491a-b23c-4e5f67890abc', '論文レビュー', '機械学習に関する最新論文を3本選び、それぞれ要約を作成。2月15日 18時締め切り', '2025-02-01 10:35:20.987654', '2025-02-01 10:35:20.987654'),
('7d4e5f6a-789b-4c12-834d-5f6a7890bcde', 'グループディスカッション', '経済学入門チームとオンラインでミーティングを実施し、議論の要点をまとめる。2月5日 20時締め切り', '2025-02-01 10:40:30.654321', '2025-02-01 10:40:30.654321'),
('6a7b8c9d-89ab-4d23-956c-6a7b8c90cdef', 'プログラムデバッグ', 'アルゴリズム最適化のためのコードを修正し、テストケースを実施。2月20日 23時締め切り', '2025-02-01 10:45:15.321987', '2025-02-01 10:45:15.321987');