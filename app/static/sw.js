// Service Worker のインストール
self.addEventListener('install', event => {
    console.log("📢 Service Worker installed");
    self.skipWaiting();
});

// Service Worker のアクティベーション
self.addEventListener('activate', event => {
    console.log("🚀 Service Worker activated");
    return self.clients.claim();
});

// Push 通知を受け取ったときの処理
self.addEventListener('push', function(event) {
    console.log("📩 Push event received!", event);

    let data = { title: "通知", body: "プッシュ通知が届きました！" }; // デフォルト通知

    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            console.error("❌ JSON 解析エラー", e);
        }
    } else {
        console.warn("⚠️ `event.data` が空です。デフォルト通知を使用します。");
    }

    // `event.waitUntil()` で非同期処理が完了するまで待つ
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/icon.png',
            vibrate: [200, 100, 200], // バイブレーション効果
            tag: 'push-notification'
        }).then(() => {
            console.log("✅ 通知が表示されました");
        }).catch(err => {
            console.error("❌ 通知の表示に失敗", err);
        })
    );
});

// 通知がクリックされたときの処理
self.addEventListener('notificationclick', function(event) {
    console.log("📢 通知がクリックされました", event.notification);
    event.notification.close();

    event.waitUntil(
        clients.matchAll({ type: "window", includeUncontrolled: true }).then(clientList => {
            if (clientList.length > 0) {
                clientList[0].focus();
            } else {
                clients.openWindow('/');
            }
        })
    );
});
