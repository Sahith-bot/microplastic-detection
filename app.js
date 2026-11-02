(() => {
  const $ = id => document.getElementById(id);
  const fileIn = $('file'), drop = $('drop'), go = $('go'), err = $('error');
  const MAX_SIDE = 2048, MAX_BYTES = 3.5 * 1024 * 1024;   // keeps uploads under Vercel's 4.5 MB request limit
  let file = null, previewUrl = null, result = null;

  function setFile(f) {
    if (!f) return;
    if (!f.type.startsWith('image/') && !/\.(tiff?|bmp|webp)$/i.test(f.name)) { showErr('Please choose an image file.'); return; }
    file = f; showErr('');
    $('fname').textContent = f.name;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(f);
    $('preview').src = previewUrl;
    $('drop-empty').style.display = 'none';
    $('drop-preview').style.display = 'block';
    drop.classList.add('has-img');
    go.disabled = false;
  }
  function showErr(m) { err.textContent = m; err.style.display = m ? 'block' : 'none'; }

  // Shrink very large photos in the browser before uploading (the model works at 640 px anyway)
  async function prepare(f) {
    let bmp;
    try { bmp = await createImageBitmap(f); } catch (e) { return f; }   // e.g. TIFF: browser can't decode, send as-is
    const s = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
    if (s === 1 && f.size <= MAX_BYTES) return f;
    const c = document.createElement('canvas');
    c.width = Math.round(bmp.width * s); c.height = Math.round(bmp.height * s);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    const blob = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.92));
    return new File([blob], f.name.replace(/\.[^.]+$/, '') + '.jpg', { type: 'image/jpeg' });
  }

  fileIn.addEventListener('change', e => setFile(e.target.files[0]));
  $('change').addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); fileIn.click(); });
  drop.addEventListener('click', e => { if (drop.classList.contains('has-img')) e.preventDefault(); });
  ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('drag'); }));
  ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('drag'); }));
  drop.addEventListener('drop', e => setFile(e.dataTransfer.files[0]));
  $('conf').addEventListener('input', e => $('conf-val').textContent = (+e.target.value).toFixed(2));

  $('form').addEventListener('submit', async e => {
    e.preventDefault();
    if (!file) return;
    showErr('');
    go.disabled = true;
    $('go-text').textContent = 'Analysing image…';
    go.insertAdjacentHTML('afterbegin', '<span class="spinner"></span>');
    try {
      const up = await prepare(file);
      if (up.size > 4.4 * 1024 * 1024) throw new Error('This image is too large to upload. Please use a JPG or PNG under 4 MB.');
      const fd = new FormData();
      fd.append('image', up);
      fd.append('original_name', file.name);
      fd.append('conf', $('conf').value);
      fd.append('volume', $('volume').value);
      fd.append('sample_name', $('sample_name').value);
      const [res, info] = await Promise.all([fetch('/api/detect', { method: 'POST', body: fd }), MP.loadInfo()]);
      const data = await res.json().catch(() => ({ error: res.status === 413 ? 'The image is too large to upload.' : 'The server returned an unexpected response.' }));
      if (!res.ok || data.error) throw new Error(data.error || 'Detection failed.');
      result = data;
      render(data, info);
    } catch (ex) {
      showErr(ex.message || 'Something went wrong. Please try again.');
    } finally {
      go.disabled = false;
      $('go-text').textContent = 'Detect microplastics';
      go.querySelector('.spinner')?.remove();
    }
  });

  document.querySelectorAll('.toggle button').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.toggle button').forEach(x => x.classList.toggle('on', x === b));
    if (result) $('result-img').src = b.dataset.v === 'original' ? previewUrl : result.annotated;
  }));
  $('pdf').addEventListener('click', () => result && MP.downloadPdf(result, $('pdf')));

  function render(r, info) {
    const s = r.summary;
    MP.saveLast(r);
    MP.stats($('stats'), s);
    MP.bars($('bars'), s);
    MP.types($('types'), s, info);
    MP.table($('det'), r.detections, info.colors);
    document.querySelectorAll('.toggle button').forEach((x, i) => x.classList.toggle('on', i === 0));
    $('result-img').src = r.annotated;
    $('level-text').innerHTML = `<b style="color:${s.level_color}">${s.level} contamination</b> — ${MP.esc(s.level_meaning)}`;
    $('results').style.display = 'block';
    $('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
})();
