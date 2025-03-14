document.addEventListener('DOMContentLoaded', function() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  const startSpeechButton = document.getElementById('start-speech');
  const speechResult = document.getElementById('speech-result');

  const updateMemoList = function(data) {
    // todoリストを更新
    const memoList = document.querySelector('.memos ul');
    if (memoList) {
      const newMemo = document.createElement('li');
      newMemo.classList.add('card');
      newMemo.innerHTML = `
        <a href="/memo/\${data.memo_id}">\${data.title}</a>
        <p class="small">作成日: \${data.created_at}</p>
      `;
      memoList.appendChild(newMemo);
    }
  };

  if (startSpeechButton) {
    startSpeechButton.addEventListener('click', function() {
      const recognition = new SpeechRecognition();
      recognition.lang = 'ja-JP';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        console.log('Transcript: ' + transcript);
        if (speechResult) {
          speechResult.textContent = '認識中: ' + transcript;
        }

        fetch('/speech', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ text: transcript })
        })
        .then(function() {
          window.location.href = "/";
        })
        .catch(function(error) {
          console.error('There has been a problem with your fetch operation:', error);
          if (speechResult) {
            speechResult.textContent = '';
          }
        });
      };
      recognition.onerror = function(event) {
        console.error('Speech recognition error detected: ' + event.error);
        if (speechResult) {
          speechResult.textContent = 'エラー: ' + event.error;
        }
      }

      recognition.start();
    });
  }
});
