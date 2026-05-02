(function () {
  const overviewStats = document.getElementById('overviewStats');
  const distanceChart = document.getElementById('distanceChart');
  const paceChart = document.getElementById('paceChart');
  const hrChart = document.getElementById('hrChart');
  const rollingChart = document.getElementById('rollingChart');

  function fmt(value, digits) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
    return Number(value).toFixed(digits || 2);
  }

  function fmtPace(minPerMile) {
    if (!minPerMile && minPerMile !== 0) return '-';
    const totalSec = Math.round(Number(minPerMile) * 60);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return min + ':' + String(sec).padStart(2, '0') + '/mi';
  }

  function card(label, value) {
    return '<div class="card"><div class="k">' + label + '</div><div class="v">' + value + '</div></div>';
  }

  function drawLineChart(canvas, labels, values, color, yLabel) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cssWidth = canvas.clientWidth || canvas.width;
    const cssHeight = canvas.height;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(cssWidth * dpr);
    canvas.height = Math.floor(cssHeight * dpr);
    canvas.style.width = cssWidth + 'px';
    canvas.style.height = cssHeight + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssWidth, cssHeight);

    const margin = { top: 20, right: 16, bottom: 35, left: 50 };
    const chartW = cssWidth - margin.left - margin.right;
    const chartH = cssHeight - margin.top - margin.bottom;

    const filtered = values.filter(function (v) {
      return v !== null && v !== undefined && !Number.isNaN(v);
    });

    if (!filtered.length) {
      ctx.fillStyle = '#5e7487';
      ctx.font = '14px sans-serif';
      ctx.fillText('No data available', 20, 30);
      return;
    }

    const min = Math.min.apply(null, filtered);
    const max = Math.max.apply(null, filtered);
    const range = max - min || 1;

    function xFor(i) {
      return margin.left + (i / Math.max(values.length - 1, 1)) * chartW;
    }
    function yFor(v) {
      return margin.top + (1 - (v - min) / range) * chartH;
    }

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
    values.forEach(function (v, i) {
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
    ctx.fillText(firstLabel, margin.left, cssHeight - 10);
    const lw = ctx.measureText(lastLabel).width;
    ctx.fillText(lastLabel, margin.left + chartW - lw, cssHeight - 10);
  }

  function toLabel(isoDate) {
    if (!isoDate) return '';
    return new Date(isoDate).toLocaleDateString();
  }

  fetch('/api/overview')
    .then(function (res) {
      if (!res.ok) throw new Error('Failed to load overview');
      return res.json();
    })
    .then(function (data) {
      const sessions = data.sessions || [];
      const rolling = data.rolling_7 || [];

      let bestPace = null;
      sessions.forEach(function (s) {
        const p = s.avg_pace_min_per_mile;
        if (p === null || p === undefined) return;
        if (bestPace === null || p < bestPace) bestPace = p;
      });

      if (overviewStats) {
        overviewStats.innerHTML = [
          card('Sessions', String(data.session_count)),
          card('Total Distance', fmt(data.total_distance_miles, 2) + ' mi'),
          card('Avg Distance', fmt(data.avg_distance_miles, 2) + ' mi'),
          card('Best Avg Pace', fmtPace(bestPace)),
        ].join('');
      }

      drawLineChart(distanceChart, sessions.map(function (s) { return toLabel(s.start_time_local); }), sessions.map(function (s) { return Number(s.distance_miles); }), '#1f77b4', 'Miles');
      drawLineChart(paceChart, sessions.map(function (s) { return toLabel(s.start_time_local); }), sessions.map(function (s) { return s.avg_pace_min_per_mile == null ? null : Number(s.avg_pace_min_per_mile); }), '#ff7f0e', 'Min / Mile');
      drawLineChart(hrChart, sessions.map(function (s) { return toLabel(s.start_time_local); }), sessions.map(function (s) { return s.avg_hr_bpm == null ? null : Number(s.avg_hr_bpm); }), '#d62728', 'BPM');
      drawLineChart(rollingChart, rolling.map(function (s) { return toLabel(s.start_time_local); }), rolling.map(function (s) { return Number(s.rolling_distance_miles); }), '#2ca02c', 'Rolling 7 (mi)');
    })
    .catch(function (err) {
      if (overviewStats) overviewStats.innerHTML = '<p class="sub">Error: ' + err.message + '</p>';
    });
})();
