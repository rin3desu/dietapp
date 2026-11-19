(() => {
  const token = document.querySelector('meta[name=csrf-token]').content;
  let unsavedGoal = false;
  document.getElementById('ideal-goal-form')?.addEventListener('input', () => { unsavedGoal = true; });
  for (const id of ['ideal-analysis-form', 'ideal-portrait-form']) {
    const form = document.getElementById(id);
    if (!form) continue;
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const button = form.querySelector('button');
      const status = form.querySelector('.ideal-status');
      const portrait = id === 'ideal-portrait-form';
      if (unsavedGoal) {
        status.hidden = false; status.textContent = '目標や人物情報が変更されています。先に「理想の自分を保存する」で保存してください。'; return;
      }
      if (portrait && form.elements.selfie.files[0].size > 5 * 1024 * 1024) {
        status.hidden = false; status.textContent = '写真は5MB以内にしてください。'; return;
      }
      button.disabled = true; status.hidden = false;
      status.textContent = portrait ? 'あなたの写真を基に、理想の姿を描いています。画面を閉じずにお待ちください…' : '憧れの理由をひもとき、行動と習慣を考えています…';
      try {
        const response = await fetch(form.dataset.url, {
          method: 'POST', headers: portrait ? {'X-CSRF-Token': token} : {'X-CSRF-Token': token, 'Content-Type': 'application/json'},
          body: portrait ? new FormData(form) : JSON.stringify({consent: form.elements.consent.checked}),
          signal: AbortSignal.timeout(portrait ? 110000 : 65000),
        });
        const data = response.headers.get('content-type')?.includes('application/json') ? await response.json() : {};
        if (!response.ok) throw new Error(data.error || '操作を完了できませんでした。ページを再読み込みしてからお試しください。');
        // Refresh server-rendered saved results, including a new revision of the private image.
        window.location.assign(data.url);
        if (new URL(data.url, location.href).pathname === location.pathname) window.location.reload();
      } catch (error) {
        status.textContent = error.name === 'TimeoutError' ? '応答に時間がかかっています。再読み込みして保存結果を確認してから、再度お試しください。' : error.message;
        button.disabled = false;
      }
    });
  }
  const file = document.getElementById('ideal-selfie');
  const preview = document.getElementById('ideal-selfie-preview');
  let objectUrl;
  if (file && preview) file.addEventListener('change', () => {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    preview.hidden = true;
    if (file.files[0] && file.files[0].size <= 5 * 1024 * 1024) {
      objectUrl = URL.createObjectURL(file.files[0]); preview.src = objectUrl; preview.hidden = false;
    }
  });
  window.addEventListener('pagehide', () => { if (objectUrl) URL.revokeObjectURL(objectUrl); });
})();
