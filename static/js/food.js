(() => {
  const form = document.getElementById('pantry-form');
  if (!form) return;
  const status = document.getElementById('ai-status');
  const results = document.getElementById('ai-results');
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const button = form.querySelector('button[type=submit]');
    button.disabled = true;
    status.hidden = false;
    status.textContent = '食材からレシピを考えています。少しお待ちください…';
    try {
      const response = await fetch(form.dataset.url, {
        method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': document.querySelector('meta[name=csrf-token]').content},
        body: JSON.stringify({ingredients: data.get('ingredients'), avoid: data.get('avoid'), goal: data.get('goal'), minutes: Number(data.get('minutes')), servings: Number(data.get('servings')), consent: data.get('consent') === 'on'}),
        signal: AbortSignal.timeout(65000),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || '提案を読み込めませんでした。');
      results.replaceChildren();
      for (const recipe of payload.recipes) {
        const card = document.createElement('article'); card.className = 's-panel ai-result-card';
        const label = document.createElement('span'); label.className = 'eyebrow'; label.textContent = 'AI RECIPE / 自分だけの下書き';
        const title = document.createElement('h3'); title.textContent = recipe.title;
        const description = document.createElement('p'); description.textContent = recipe.subtitle;
        const ingredients = document.createElement('p'); ingredients.className = 's-fineprint'; ingredients.textContent = recipe.ingredients.map(i => i[0]).join(' / ');
        const link = document.createElement('a'); link.className = 'text-link'; link.href = recipe.url; link.textContent = '材料・手順を確認する →';
        card.append(label, title, description, ingredients, link); results.append(card);
      }
      status.textContent = '提案を下書きに保存しました。材料・手順を確認し、必要に応じて実写写真を添えて公開できます。';
    } catch (error) {
      status.textContent = error.name === 'TimeoutError' ? '応答に時間がかかっています。下書き一覧に保存されていないか確認してから再度お試しください。' : error.message;
    } finally { button.disabled = false; }
  });
})();
