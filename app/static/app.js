
const $ = (id) => document.getElementById(id);
function setBadge(id, text){ const el=$(id); if(el) el.innerText=text; }

$('lk-generate').onclick = async function(){
  const payload = { lang: $('lk-story-lang').value, genre: $('lk-genre').value, region: $('lk-region').value,
                    seed: $('lk-seed').value, forced_model: $('lk-model').value || null };
  if (!payload.seed || payload.seed.length < 10) { alert('Prompt too short (min 10 chars).'); return; }
  if (payload.seed.length > 300) { alert('Prompt too long (max 300 chars).'); return; }
  const bar = $('lk-bar'); this.disabled = true; this.innerText = '⏳ Generating Story...'; if (bar) bar.style.width = '25%';
  try {
    const r = await fetch('/api/generate', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const j = await r.json(); if (j.error) { alert(j.error); return; }
    $('lk-story').innerText = j.story || ''; $('lk-transcript').innerText = j.transcript || '';
    setBadge('lk-model-badge', `Model: ${j.backend[0]} | ${j.backend[1]}`);
    $('lk-lang').value = (payload.lang === 'English') ? 'Hindi' : 'English';
    const sbar = $('lk-sbar'); if (sbar) { sbar.style.width = '60%'; setTimeout(()=>{ sbar.style.width = '0%'; }, 400); }
    setBadge('lk-smodel-badge', 'Model: local | sentence-tokenizer');
  } finally { this.disabled = false; this.innerText = '🚀 Generate Story'; if (bar) bar.style.width = '0%'; }
};

$('lk-translate').onclick = async function(){
  const payload = { target_lang: $('lk-lang').value, forced_model: $('lk-model').value || null, text: $('lk-story').innerText };
  if (!payload.text) { alert('Please generate a story first.'); return; }
  const tbar = $('lk-tbar'); this.disabled = true; this.innerText = '⏳ Translating Story...'; if (tbar) tbar.style.width = '35%';
  try {
    const r = await fetch('/api/translate', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const j = await r.json(); if (j.error) { alert(j.error); return; }
    $('lk-translation').innerText = j.translation || '';
    if (j.backend) setBadge('lk-tmodel-badge', `Model: ${j.backend[0]} | ${j.backend[1]}`);
  } finally { this.disabled = false; this.innerText = '🌐 Translate Story'; if (tbar) tbar.style.width = '0%'; }
};

$('lk-images').onclick = async function(){
  const styleEl = $('lk-img-style2');
  const payload = { count: parseInt($('lk-img-count').value || '2', 10), style: (styleEl && styleEl.value) || 'none',
                    prompt: ($('lk-story').innerText || '').split('Takeaway:')[0].trim() || $('lk-story').innerText };
  if (!payload.prompt) { alert('Please generate a story first.'); return; }
  const ibar = $('lk-ibar'); this.disabled = true; this.innerText = '⏳ Generating Images...'; if (ibar) ibar.style.width = '40%';
  try {
    const r = await fetch('/api/images', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const j = await r.json();
    const grid = $('lk-images-grid'); grid.innerHTML = ''; (j.images_b64 || []).forEach(src => { const img = new Image(); img.src = src; grid.appendChild(img); });
    if (j.backend) setBadge('lk-imodel-badge', `Model: ${j.backend[0]} | ${j.backend[1]}`);
  } finally { this.disabled = false; this.innerText = '🖼️ Generate Images'; if (ibar) ibar.style.width = '0%'; }
};

$('lk-audio-btn').onclick = async function(){
  const text = ($('lk-translation').innerText || $('lk-story').innerText || '').trim();
  if (!text) { alert('Please generate a story or translation first.'); return; }
  const accent = $('lk-accent').value || 'Indian';
  const abar = $('lk-abar'); this.disabled = true; this.innerText = '⏳ Generating Audio...'; if (abar) abar.style.width = '45%';
  try {
    const r = await fetch('/api/audio', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ text, accent }) });
    if (!r.ok) { const j = await r.json().catch(()=>({error:'TTS failed'})); alert(j.error || 'TTS failed'); return; }
    const backendHeader = r.headers.get('X-Backend'); if (backendHeader) setBadge('lk-amodel-badge', `Model: ${backendHeader.replace('|',' | ')}`);
    const blob = await r.blob(); const url = URL.createObjectURL(blob);
    const audio = $('lk-audio'); audio.src = url; audio.play().catch(()=>{});
  } finally { this.disabled = false; this.innerText = '🔊 Generate Audio'; if (abar) abar.style.width = '0%'; }
};

$('lk-video-btn').onclick = async function(){
  const text = ($('lk-translation').innerText || $('lk-story').innerText || '').trim();
  if (!text) { alert('Please generate a story or translation first.'); return; }
  const accent = $('lk-vaccent').value || 'Indian';
  const vbar = $('lk-vbar'); this.disabled = true; this.innerText = '⏳ Generating Video...'; if (vbar) vbar.style.width = '55%';
  try {
    const r = await fetch('/api/video', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ text, accent }) });
    if (!r.ok) { const j = await r.json().catch(()=>({error:'Video generation failed'})); alert(j.error || 'Video generation failed'); return; }
    const backendHeader = r.headers.get('X-Backend'); if (backendHeader) document.getElementById('lk-vmodel-badge').innerText = `Model: ${backendHeader.replace('|',' | ')}`;
    const blob = await r.blob(); const url = URL.createObjectURL(blob);
    const video = $('lk-video'); video.src = url; try { await video.play(); } catch(e) {}
  } finally { this.disabled = false; this.innerText = '🎬 Generate Video'; if (vbar) vbar.style.width = '0%'; }
};

$('lk-dl-txt').onclick = async function(){
  const payload = { story: $('lk-story').innerText || '', translation: $('lk-translation').innerText || '' };
  if (!payload.story) { alert('Please generate a story first.'); return; }
  this.disabled = true; this.innerText = '⏳ Exporting TXT...';
  try {
    const r = await fetch('/api/download/txt', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const blob = await r.blob(); const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'lokkatha_story.txt'; a.click(); URL.revokeObjectURL(url);
  } finally { this.disabled = false; this.innerText = '⬇️ Export TXT'; }
};

$('lk-dl-pdf').onclick = async function(){
  const imgs = Array.from(document.querySelectorAll('#lk-images-grid img')).map(img => img.src).filter(x => x.startsWith('data:image'));
  const payload = { story: $('lk-story').innerText || '', translation: $('lk-translation').innerText || '', images_b64: imgs };
  if (!payload.story) { alert('Please generate a story first.'); return; }
  this.disabled = true; this.innerText = '⏳ Exporting PDF...';
  try {
    const r = await fetch('/api/download/pdf', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    if (!r.ok) { const j = await r.json().catch(()=>({error:'PDF failed'})); alert(j.error || 'PDF failed'); return; }
    const blob = await r.blob(); const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'lokkatha_story.pdf'; a.click(); URL.revokeObjectURL(url);
  } finally { this.disabled = false; this.innerText = '📄 Export PDF'; }
};

$('lk-reset').onclick = async function(){
  $('lk-story').innerText = ''; $('lk-translation').innerText = ''; $('lk-transcript').innerText = ''; $('lk-images-grid').innerHTML = '';
  setBadge('lk-model-badge','Model: —'); setBadge('lk-tmodel-badge','Model: —'); setBadge('lk-smodel-badge','Model: —'); setBadge('lk-imodel-badge','Model: —'); setBadge('lk-amodel-badge','Model: —'); setBadge('lk-vmodel-badge','Model: —');
  const audio = $('lk-audio'); audio.pause(); audio.src='';
  const video = $('lk-video'); video.pause(); video.src='';
  await fetch('/api/reset', { method: 'POST' });
};
