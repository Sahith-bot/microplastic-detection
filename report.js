(async () => {
  const $ = id => document.getElementById(id);
  const r = MP.getLast();
  if (!r || !r.summary) { $('no-report').style.display = 'block'; return; }
  const info = await MP.loadInfo(), s = r.summary;

  $('r-title').textContent = r.sample_name ? `Report: ${r.sample_name}` : 'Microplastic Detection Report';
  $('r-id').textContent = `Report ID ${r.id} · ${new Date(r.created).toLocaleString()}`;
  $('pdf').addEventListener('click', () => MP.downloadPdf(r, $('pdf')));
  const meta = [['Image file', r.filename], ['Image size', `${r.width} × ${r.height} px`], ['Confidence threshold', r.conf.toFixed(2)]];
  if (s.volume_l) meta.push(['Water volume', s.volume_l + ' L']);
  meta.push(['Model', 'YOLOv8 (' + r.engine + ')'], ['Classes', Object.values(info.display_names).join(', ')]);
  $('meta').innerHTML = meta.map(([k, v]) => `<div><b>${k}</b>${MP.esc(v)}</div>`).join('');

  const conc = s.per_litre != null ? `<div>Estimated concentration: <b>${s.per_litre} particles/L</b> (${s.conc_level})</div>` : '';
  $('assess').style.borderColor = s.level_color;
  $('assess').innerHTML = `<div class="big" style="color:${s.level_color}">${s.total}</div>
    <div><div style="font-size:1.2rem;font-weight:700;color:${s.level_color}">${s.level} contamination</div>
    <div>${MP.esc(s.level_meaning)}</div>
    <div class="sub" style="margin:4px 0 0">${s.total} particle${s.total === 1 ? '' : 's'} detected${s.dominant ? ' · dominant type: <b>' + s.dominant + '</b>' : ''}</div>${conc}</div>`;
  let lo = 0;
  $('scale').innerHTML = s.thresholds.map(t => {
    const range = t.max == null ? `> ${lo - 1}` : `${lo}–${t.max}`;
    const html = `<div class="${t.level === s.level ? 'cur' : ''}" style="background:${t.color}">${t.level}<br><span style="font-weight:400">${range} particles</span></div>`;
    if (t.max != null) lo = t.max + 1;
    return html;
  }).join('');

  $('result-img').src = r.annotated;
  MP.bars($('bars'), s);
  $('stats').innerHTML = [['Total particles', s.total], ['Mean confidence', s.mean_conf != null ? (s.mean_conf * 100).toFixed(1) + '<small>%</small>' : '—']]
    .map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
  MP.types($('types'), s, info);
  MP.table($('det'), r.detections, info.colors);
  $('report-body').style.display = 'block';
})();
