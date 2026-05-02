(function () {
  function fmt(value, digits) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
    return Number(value).toFixed(digits == null ? 1 : digits);
  }

  function fmtDate(raw, compact) {
    if (!raw) return '-';
    var date = new Date(raw);
    if (isNaN(date.getTime())) return raw;
    return date.toLocaleString(undefined, compact ? {
      month: 'short',
      day: 'numeric'
    } : {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  function drawLineChart(canvas, series, labels) {
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var width = canvas.clientWidth || 800;
    var height = canvas.clientHeight || 320;
    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    var margin = { top: 24, right: 20, bottom: 40, left: 46 };
    var chartW = width - margin.left - margin.right;
    var chartH = height - margin.top - margin.bottom;
    var values = [];
    series.forEach(function (line) {
      line.values.forEach(function (value) {
        if (value !== null && value !== undefined && !Number.isNaN(Number(value))) values.push(Number(value));
      });
    });

    if (!values.length) {
      ctx.fillStyle = '#68767d';
      ctx.font = '14px sans-serif';
      ctx.fillText('No data yet', 20, 30);
      return;
    }

    var min = Math.min.apply(null, values);
    var max = Math.max.apply(null, values);
    var range = max - min || 1;

    function xFor(i) {
      return margin.left + (i / Math.max(labels.length - 1, 1)) * chartW;
    }

    function yFor(v) {
      return margin.top + (1 - (Number(v) - min) / range) * chartH;
    }

    ctx.strokeStyle = 'rgba(24, 46, 56, 0.12)';
    ctx.lineWidth = 1;
    for (var i = 0; i < 4; i += 1) {
      var y = margin.top + i * (chartH / 3);
      ctx.beginPath();
      ctx.moveTo(margin.left, y);
      ctx.lineTo(margin.left + chartW, y);
      ctx.stroke();
    }

    series.forEach(function (line) {
      ctx.strokeStyle = line.color;
      ctx.lineWidth = 3;
      ctx.beginPath();
      var started = false;
      line.values.forEach(function (value, index) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) return;
        var x = xFor(index);
        var y = yFor(value);
        if (!started) {
          ctx.moveTo(x, y);
          started = true;
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.stroke();
    });

    ctx.fillStyle = '#68767d';
    ctx.font = '12px sans-serif';
    ctx.fillText(String(Math.round(max * 10) / 10), 8, margin.top + 4);
    ctx.fillText(String(Math.round(min * 10) / 10), 8, margin.top + chartH);
    if (labels.length) {
      ctx.fillText(labels[0], margin.left, height - 12);
      var last = labels[labels.length - 1];
      var lastWidth = ctx.measureText(last).width;
      ctx.fillText(last, margin.left + chartW - lastWidth, height - 12);
    }
  }

  window.SummitLog = {
    fmt: fmt,
    fmtDate: fmtDate,
    drawLineChart: drawLineChart
  };
})();
