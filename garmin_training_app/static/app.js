const statusEl = document.getElementById('status');
const importBtn = document.getElementById('importBtn');
const watchPathEl = document.getElementById('watchPath');
const tbody = document.querySelector('#activityTable tbody');
const plotImage = document.getElementById('plotImage');
const detailCards = document.getElementById('detailCards');
const sessionExtra = document.getElementById('sessionExtra');
const detailsPanel = document.querySelector('#view-records .details');

const overviewStats = document.getElementById('overviewStats');
const distanceChart = document.getElementById('distanceChart');
const paceChart = document.getElementById('paceChart');
const hrChart = document.getElementById('hrChart');
const rollingChart = document.getElementById('rollingChart');

const menuBtn = document.getElementById('menuBtn');
const menuFab = document.getElementById('menuFab');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('overlay');

let activities = [];
let selectedId = null;
const timeseriesCache = new Map();

function fmt(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return Number(value).toFixed(digits);
}

function fmtPace(minPerMile) {
  if (!minPerMile && minPerMile !== 0) return '-';
  const totalSec = Math.round(Number(minPerMile) * 60);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${String(sec).padStart(2, '0')}/mi`;
}

function fmtDuration(seconds) {
  if (!seconds && seconds !== 0) return '-';
  const s = Math.round(Number(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return h > 0
    ? `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
    : `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

function card(label, value) {
  return `<div class="card"><div class="k">${label}</div><div class="v">${value}</div></div>`;
}

function setDrawer(open) {
  if (!sidebar || !overlay) return;
  sidebar.classList.toggle('open', open);
  overlay.classList.toggle('show', open);
}

if (menuBtn) menuBtn.addEventListener('click', () => setDrawer(true));
if (menuFab) menuFab.addEventListener('click', () => setDrawer(true));
if (overlay) overlay.addEventListener('click', () => setDrawer(false));

function showView(view) {
  const validView = view === 'overall' ? 'overall' : 'records';
  document.querySelectorAll('.view').forEach((el) => el.classList.remove('active'));
  const targetView = document.getElementById(`view-${validView}`);
  if (targetView) targetView.classList.add('active');

  document.querySelectorAll('.drawer-link').forEach((link) => {
    link.classList.toggle('active', link.dataset.view === validView);
  });

  window.location.hash = validView;
  setDrawer(false);
}

document.querySelectorAll('.drawer-link').forEach((link) => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    showView(link.dataset.view);
  });
});

function computeTimeseriesStats(points) {
  if (!points || !points.length) return null;
  const avg = (arr) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null);

  const cadence = points.map((p) => Number(p.cadence_spm)).filter((v) => !Number.isNaN(v));
  const speed = points.map((p) => Number(p.speed_mph)).filter((v) => !Number.isNaN(v));
  const hr = points.map((p) => Number(p.heart_rate_bpm)).filter((v) => !Number.isNaN(v));
  const gain = points.map((p) => Number(p.cum_elevation_gain_ft)).filter((v) => !Number.isNaN(v));

  return {
    points: points.length,
    avgCadence: avg(cadence),
    maxCadence: cadence.length ? Math.max(...cadence) : null,
    avgSpeed: avg(speed),
    avgHr: avg(hr),
    totalGain: gain.length ? gain[gain.length - 1] : null,
  };
}

function renderTimeseriesStats(stats) {
  if (!sessionExtra) return;
  if (!stats) {
    sessionExtra.innerHTML = '';
    return;
  }

  sessionExtra.innerHTML = [
    card('Data Points', `${stats.points}`),
    card('Avg Cadence', `${fmt(stats.avgCadence, 1)} spm`),
    card('Max Cadence', `${fmt(stats.maxCadence, 0)} spm`),
    card('Avg Speed (records)', `${fmt(stats.avgSpeed, 2)} mph`),
    card('Avg HR (records)', `${fmt(stats.avgHr, 1)} bpm`),
    card('Total Gain (records)', `${fmt(stats.totalGain, 1)} ft`),
  ].join('');
}

async function loadTimeseriesStats(activityId) {
  if (timeseriesCache.has(activityId)) {
    renderTimeseriesStats(timeseriesCache.get(activityId));
    return;
  }

  try {
    const res = await fetch(`/api/activities/${activityId}/timeseries`);
    if (!res.ok) throw new Error('Unable to load session time-series');
    const points = await res.json();
    const stats = computeTimeseriesStats(points);
    timeseriesCache.set(activityId, stats);
    if (selectedId === activityId) renderTimeseriesStats(stats);
  } catch (err) {
    if (sessionExtra) sessionExtra.innerHTML = `<p class="sub">${err.message}</p>`;
  }
}

function renderDetails(activity) {
  if (!detailCards || !plotImage || !sessionExtra) return;

  if (!activity) {
    detailCards.innerHTML = '';
    sessionExtra.innerHTML = '';
    plotImage.removeAttribute('src');
    return;
  }

  detailCards.innerHTML = [
    card('Date', activity.start_time_local ? new Date(activity.start_time_local).toLocaleString() : '-'),
    card('Distance', `${fmt(activity.distance_miles, 3)} mi`),
    card('Elapsed', fmtDuration(activity.elapsed_seconds)),
    card('Moving', fmtDuration(activity.moving_seconds)),
    card('Avg Pace', fmtPace(activity.avg_pace_min_per_mile)),
    card('Best Pace', fmtPace(activity.best_pace_min_per_mile)),
    card('Avg Speed', `${fmt(activity.avg_speed_mph)} mph`),
    card('Max Speed', `${fmt(activity.max_speed_mph)} mph`),
    card('Avg / Max HR', `${activity.avg_hr_bpm ?? '-'} / ${activity.max_hr_bpm ?? '-'} bpm`),
    card('Ascent', `${fmt(activity.ascent_ft, 1)} ft`),
    card('Descent', `${fmt(activity.descent_ft, 1)} ft`),
    card('Records', `${activity.record_count ?? '-'}`),
  ].join('');

  if (activity.plot_path) {
    const fname = activity.plot_path.replace('plots/', '');
    plotImage.src = `/plots/${encodeURIComponent(fname)}?t=${Date.now()}`;
  } else {
    plotImage.removeAttribute('src');
  }

  sessionExtra.innerHTML = '<p class="sub">Loading selected session data...</p>';
  loadTimeseriesStats(activity.id);
}

function renderTable() {
  if (!tbody) return;
  tbody.innerHTML = '';

  activities.forEach((a) => {
    const tr = document.createElement('tr');
    tr.className = `pickable${a.id === selectedId ? ' selected' : ''}`;
    tr.innerHTML = `
      <td>${a.start_time_local ? new Date(a.start_time_local).toLocaleString() : '-'}</td>
      <td>${a.sport || '-'}</td>
      <td>${fmt(a.distance_miles, 3)}</td>
      <td>${fmtPace(a.avg_pace_min_per_mile)}</td>
      <td>${a.avg_hr_bpm ?? '-'}</td>
    `;

    tr.addEventListener('click', () => {
      selectedId = a.id;
      showView('records');
      renderTable();
      renderDetails(a);
      if (detailsPanel) {
        detailsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });

    tbody.appendChild(tr);
  });

  if (!selectedId && activities.length > 0) selectedId = activities[0].id;
  const selected = activities.find((a) => a.id === selectedId) || activities[0];
  renderDetails(selected);
}

async function fetchActivities() {
  const res = await fetch('/api/activities');
  if (!res.ok) throw new Error('Failed to fetch activities');
  activities = await res.json();
  renderTable();
}

async function importFromWatch() {
  if (!importBtn || !watchPathEl || !statusEl) return;
  importBtn.disabled = true;
  statusEl.textContent = 'Importing from watch...';

  try {
    const res = await fetch('/api/import-watch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ watch_path: watchPathEl.value.trim() }),
    });

    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || 'Import failed');

    statusEl.textContent = `Import complete: ${data.imported} new, ${data.skipped} skipped (${data.total_files} files scanned).`;
    timeseriesCache.clear();
    await fetchActivities();
    await loadOverview();
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  } finally {
    importBtn.disabled = false;
  }
}

function drawLineChart(canvas, labels, values, color, yLabel) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const width = canvas.clientWidth || canvas.width;
  const height = canvas.height;
  canvas.width = width;
  ctx.clearRect(0, 0, width, height);

  const margin = { top: 20, right: 16, bottom: 35, left: 50 };
  const chartW = width - margin.left - margin.right;
  const chartH = height - margin.top - margin.bottom;

  const filtered = values.filter((v) => v !== null && v !== undefined && !Number.isNaN(v));
  if (!filtered.length) {
    ctx.fillStyle = '#5e7487';
    ctx.font = '14px sans-serif';
    ctx.fillText('No data available', 20, 30);
    return;
  }

  const min = Math.min(...filtered);
  const max = Math.max(...filtered);
  const range = max - min || 1;
  const xFor = (i) => margin.left + (i / Math.max(values.length - 1, 1)) * chartW;
  const yFor = (v) => margin.top + (1 - (v - min) / range) * chartH;

  ctx.strokeStyle = '#d8e4ee';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(margin.left, margin.top);
  ctx.lineTo(margin.left, margin.top + chartH);
  ctx.lineTo(margin.left + chartW, margin.top + chartH);
  ctx.stroke();

  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  let moved = false;
  values.forEach((v, i) => {
    if (v === null || v === undefined || Number.isNaN(v)) return;
    const x = xFor(i);
    const y = yFor(v);
    if (!moved) {
      ctx.moveTo(x, y);
      moved = true;
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.fillStyle = '#5e7487';
  ctx.font = '12px sans-serif';
  ctx.fillText(yLabel, margin.left, 12);
  ctx.fillText(fmt(max, 2), 6, margin.top + 4);
  ctx.fillText(fmt(min, 2), 6, margin.top + chartH);

  const firstLabel = labels[0] || '';
  const lastLabel = labels[labels.length - 1] || '';
  ctx.fillText(firstLabel, margin.left, height - 10);
  const lw = ctx.measureText(lastLabel).width;
  ctx.fillText(lastLabel, margin.left + chartW - lw, height - 10);
}

function toLabel(isoDate) {
  if (!isoDate) return '';
  return new Date(isoDate).toLocaleDateString();
}

async function loadOverview() {
  if (!overviewStats) return;
  const res = await fetch('/api/overview');
  if (!res.ok) throw new Error('Failed to load overview');
  const data = await res.json();

  const sessions = data.sessions || [];
  const rolling = data.rolling_7 || [];

  const bestPace = sessions
    .map((s) => s.avg_pace_min_per_mile)
    .filter((v) => v !== null && v !== undefined)
    .reduce((a, b) => (a === null || b < a ? b : a), null);

  overviewStats.innerHTML = [
    card('Sessions', `${data.session_count}`),
    card('Total Distance', `${fmt(data.total_distance_miles, 2)} mi`),
    card('Avg Distance', `${fmt(data.avg_distance_miles, 2)} mi`),
    card('Best Avg Pace', fmtPace(bestPace)),
  ].join('');

  drawLineChart(distanceChart, sessions.map((s) => toLabel(s.start_time_local)), sessions.map((s) => Number(s.distance_miles)), '#1f77b4', 'Miles');
  drawLineChart(paceChart, sessions.map((s) => toLabel(s.start_time_local)), sessions.map((s) => (s.avg_pace_min_per_mile == null ? null : Number(s.avg_pace_min_per_mile))), '#ff7f0e', 'Min / Mile');
  drawLineChart(hrChart, sessions.map((s) => toLabel(s.start_time_local)), sessions.map((s) => (s.avg_hr_bpm == null ? null : Number(s.avg_hr_bpm))), '#d62728', 'BPM');
  drawLineChart(rollingChart, rolling.map((s) => toLabel(s.start_time_local)), rolling.map((s) => Number(s.rolling_distance_miles)), '#2ca02c', 'Rolling 7 (mi)');
}

if (importBtn) importBtn.addEventListener('click', importFromWatch);

Promise.all([fetchActivities(), loadOverview()]).catch((err) => {
  if (statusEl) statusEl.textContent = `Error loading data: ${err.message}`;
});

const initialHash = window.location.hash.replace('#', '').toLowerCase();
showView(initialHash === 'overall' ? 'overall' : 'records');
