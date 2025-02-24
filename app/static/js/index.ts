document.addEventListener('DOMContentLoaded', function() {
  window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  const startSpeechButton = document.getElementById('start-speech');
  const speechResult = document.getElementById('speech-result');

  const updateMemoList = (data: any) => {
    // todoリストを更新
    const memoList = document.querySelector('.memos ul');
    const newMemo = document.createElement('li');
    newMemo.classList.add('card');
    newMemo.innerHTML = `
      <a href="/memo/${data.memo_id}">${data.title}</a>
      <p class="small">作成日: ${data.created_at}</p>
    `;
    memoList.appendChild(newMemo);
  };

  startSpeechButton.addEventListener('click', () => {
    const recognition = new SpeechRecognition() || new webkitSpeechRecognition();
    recognition.lang = 'ja-JP';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      console.log('Transcript: ' + transcript);
      speechResult.textContent = '認識中: ' + transcript;

      fetch('/speech', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: transcript })
      })
      .then(() => {
        window.location.href = "/";
      })
      .catch((error: any) => {
        console.error('There has been a problem with your fetch operation:', error);
        speechResult.textContent = '';
      });
    };
    recognition.onerror = (event: any) => {
      console.error('Speech recognition error detected: ' + event.error);
      speechResult.textContent = 'エラー: ' + event.error;
    }

    recognition.start();
  });
});