// Shared rendering helpers for both pages
const MP = {
  info: null,
  async loadInfo() {
    if (!this.info) this.info = await (await fetch('/api/info')).json();
    return this.info;
  },
  esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); },
  // The server keeps nothing, so the latest result lives in the browser for the Report page
  saveLast(r) {
    try { localStorage.setItem('mp_last_result', JSON.stringify(r)); return true; }
    catch (e) { try { sessionStorage.setItem('mp_last_result', JSON.stringify(r)); return true; } catch (e2) { return false; } }
  },
  getLast() {
    try { return JSON.parse(localStorage.getItem('mp_last_result') || sessionStorage.getItem('mp_last_result') || 'null'); }
    catch (e) { return null; }
  },
  async downloadPdf(r, btn) {
    const label = btn.querySelector('span'), old = label.textContent;
    btn.disabled = true; label.textContent = 'Preparing PDF…';
    try {
      const res = await fetch('/api/report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(r) });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.error || 'Could not create the PDF.'); }
      const blob = await res.blob(), a = document.createElement('a');
      const name = (r.sample_name || (r.filename || 'image').replace(/\.[^.]+$/, '')).replace(/[^A-Za-z0-9_-]+/g, '_').slice(0, 40);
      a.href = URL.createObjectURL(blob); a.download = `microplastic_report_${name}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    } catch (e) { alert(e.message); }
    finally { btn.disabled = false; label.textContent = old; }
  },

  stats(el, s, compact) {
    const tiles = [
      ['Particles detected', s.total],
      ['Contamination', `<span class="level-pill" style="background:${s.level_color}">${s.level}</span>`],
      ['Dominant type', s.dominant || '—'],
      ['Mean confidence', s.mean_conf != null ? (s.mean_conf * 100).toFixed(1) + '<small>%</small>' : '—'],
    ];
    if (s.per_litre != null) tiles.push(['Particles per litre', `${s.per_litre} <small>(${s.conc_level})</small>`]);
    el.innerHTML = tiles.slice(0, compact ? undefined : undefined).map(([k, v]) =>
      `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
  },

  bars(el, s) {
    const mx = Math.max(1, ...s.per_class.map(p => p.count));
    el.innerHTML = s.per_class.map(p => `
      <div class="row"><span class="name"><span class="dot" style="background:${p.color}"></span>${p.name}</span>
      <div class="track"><div class="fill" style="width:0;background:${p.color}" data-w="${100 * p.count / mx}"></div></div>
      <span class="num">${p.count} · ${p.percent}%</span></div>`).join('');
    requestAnimationFrame(() => el.querySelectorAll('.fill').forEach(f => f.style.width = f.dataset.w + '%'));
  },

  types(el, s, info) {
    const found = s.per_class.filter(p => p.count > 0);
    if (!found.length) { el.innerHTML = '<div class="card empty" style="grid-column:1/-1">No microplastics were detected above the confidence threshold. Try lowering the threshold or using a clearer image.</div>'; return; }
    el.innerHTML = found.map(p => {
      const k = info.info[p.label] || {};
      return `<div class="type-card" style="border-top-color:${p.color}">
        <h3>${MP.esc(k.name || p.name)} <span class="count">${p.count} detected</span></h3>
        <dl><dt>Appearance</dt><dd>${MP.esc(k.shape)}</dd>
        <dt>Common sources</dt><dd>${MP.esc(k.sources)}</dd>
        <dt>Typical polymers</dt><dd>${MP.esc(k.polymers)}</dd>
        <dt>Why it matters</dt><dd>${MP.esc(k.impact)}</dd>
        <dt>How to reduce</dt><dd>${MP.esc(k.reduce)}</dd></dl></div>`;
    }).join('');
  },

  table(el, dets, colors) {
    if (!dets.length) { el.innerHTML = '<tr><td class="empty">No detections</td></tr>'; return; }
    el.innerHTML = '<thead><tr><th>#</th><th>Type</th><th>Confidence</th><th>Box (x1, y1, x2, y2) px</th><th>Size (w × h) px</th></tr></thead><tbody>' +
      dets.map(d => `<tr><td>${d.id}</td><td><span class="dot" style="background:${colors[d.label] || '#0f8b8d'}"></span> ${MP.esc(d.name)}</td>
        <td>${(d.conf * 100).toFixed(1)}%</td><td>${d.box.map(v => Math.round(v)).join(', ')}</td>
        <td>${Math.round(d.width_px)} × ${Math.round(d.height_px)}</td></tr>`).join('') + '</tbody>';
  },
};

