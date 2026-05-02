const statsEl = document.getElementById('overviewStats');

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

function card(label, value) {
  return `<div class="card"><div class="k">${label}</div><div class="v">${value}</div></div>`;
}

function drawLineChart(canvas, labels, values, color, yLabel) {
  const ctx = canvas.getContext('2d');
  const cssWidth = canvas.clientWidth || canvas.width;
  const cssHeight = canvas.clientHeight || canvas.height || 260;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(cssWidth * dpr));
  canvas.height = Math.max(1, Math.floor(cssHeight * dpr));
  canvas.style.width = `${cssWidth}px`;
  canvas.style.height = `${cssHeight}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const width = cssWidth;
  const height = cssHeight;

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
  ctx.lineWidth = 2.2;
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
  const res = await fetch('/api/overview');
  if (!res.ok) throw new Error('Failed to load overview');
  const data = await res.json();

  const sessions = data.sessions || [];
  const rolling = data.rolling_7 || [];

  const bestPace = sessions
    .map((s) => s.avg_pace_min_per_mile)
    .filter((v) => v !== null && v !== undefined)
    .reduce((a, b) => (a === null || b < a ? b : a), null);

  statsEl.innerHTML = [
    card('Sessions', `${data.session_count}`),
    card('Total Distance', `${fmt(data.total_distance_miles, 2)} mi`),
    card('Avg Distance', `${fmt(data.avg_distance_miles, 2)} mi`),
    card('Best Avg Pace', fmtPace(bestPace)),
  ].join('');

  drawLineChart(
    document.getElementById('distanceChart'),
    sessions.map((s) => toLabel(s.start_time_local)),
    sessions.map((s) => Number(s.distance_miles)),
    '#1f77b4',
    'Miles'
  );

  drawLineChart(
    document.getElementById('paceChart'),
    sessions.map((s) => toLabel(s.start_time_local)),
    sessions.map((s) => s.avg_pace_min_per_mile === null ? null : Number(s.avg_pace_min_per_mile)),
    '#ff7f0e',
    'Min / Mile'
  );

  drawLineChart(
    document.getElementById('hrChart'),
    sessions.map((s) => toLabel(s.start_time_local)),
    sessions.map((s) => s.avg_hr_bpm === null ? null : Number(s.avg_hr_bpm)),
    '#d62728',
    'BPM'
  );

  drawLineChart(
    document.getElementById('rollingChart'),
    rolling.map((s) => toLabel(s.start_time_local)),
    rolling.map((s) => Number(s.rolling_distance_miles)),
    '#2ca02c',
    'Rolling 7 Distance (mi)'
  );
}

loadOverview().catch((err) => {
  statsEl.innerHTML = `<p class="sub">${err.message}</p>`;
});
