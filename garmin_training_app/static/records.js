(function () {
  const statusEl = document.getElementById('status');
  const importBtn = document.getElementById('importBtn');
  const watchPathEl = document.getElementById('watchPath');
  const tbody = document.querySelector('#activityTable tbody');

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

  function fmtDateTime(raw) {
    if (!raw) return '-';
    var d = new Date(raw);
    if (isNaN(d.getTime())) return raw;
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  }

  function renderTable(activities) {
    if (!tbody) return;
    tbody.innerHTML = '';

    const weekdayRuns = activities.filter(function (a) {
      if (!a.start_time_local) return false;
      const d = new Date(a.start_time_local);
      const day = d.getDay(); // 0 Sun ... 6 Sat
      return day >= 1 && day <= 5; // Monday-Friday only
    });

    const groups = groupByWorkWeek(weekdayRuns);

    groups.forEach(function (group, idx) {
      const headerRow = document.createElement('tr');
      headerRow.className = 'week-row week-group-start';
      headerRow.innerHTML =
        '<td colspan="5">' +
        '<div class="week-head">' +
        '<strong>' + group.label + '</strong>' +
        '<button type="button" class="week-icon-btn" data-week-key="' + group.key + '" title="Open week page">Week&apos;s total</button>' +
        '</div>' +
        '</td>';
      tbody.appendChild(headerRow);

      group.records.forEach(function (a) {
        const tr = document.createElement('tr');
        tr.className = 'pickable week-group-mid';
        tr.innerHTML =
          '<td>' + fmtDateTime(a.start_time_local) + '</td>' +
          '<td>' + (a.sport || '-') + '</td>' +
          '<td>' + fmt(a.distance_miles, 3) + '</td>' +
          '<td>' + fmtPace(a.avg_pace_min_per_mile) + '</td>' +
          '<td>' + (a.avg_hr_bpm == null ? '-' : a.avg_hr_bpm) + '</td>';

        tr.addEventListener('click', function () {
          window.location.href = '/session/' + a.id;
        });
        tbody.appendChild(tr);
      });

      // Close the blue outline for this week group.
      if (group.records.length > 0) {
        const lastRow = tbody.lastElementChild;
        if (lastRow) {
          lastRow.classList.remove('week-group-mid');
          lastRow.classList.add('week-group-end');
        }
      }
    });

    tbody.querySelectorAll('.week-icon-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        const weekKey = btn.getAttribute('data-week-key');
        if (!weekKey) return;
        window.location.href = '/week/' + weekKey;
      });
    });
  }

  function toMonday(d) {
    const date = new Date(d);
    const day = date.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    date.setDate(date.getDate() + diff);
    date.setHours(0, 0, 0, 0);
    return date;
  }

  function fmtDate(d) {
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function groupByWorkWeek(records) {
    const map = new Map();
    records.forEach(function (r) {
      const dt = new Date(r.start_time_local);
      const monday = toMonday(dt);
      const key = monday.toISOString().slice(0, 10);
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(r);
    });

    const keys = Array.from(map.keys()).sort().reverse();
    return keys.map(function (k) {
      const monday = new Date(k + 'T00:00:00');
      const friday = new Date(monday);
      friday.setDate(monday.getDate() + 4);
      const records = map.get(k).sort(function (a, b) {
        return new Date(b.start_time_local) - new Date(a.start_time_local);
      });

      let totalSeconds = 0;
      let totalMiles = 0;
      let totalGain = 0;
      let totalLoss = 0;
      records.forEach(function (r) {
        totalSeconds += Number(r.moving_seconds || r.elapsed_seconds || 0);
        totalMiles += Number(r.distance_miles || 0);
        totalGain += Number(r.ascent_ft || 0);
        totalLoss += Number(r.descent_ft || 0);
      });

      return {
        key: k,
        label: 'Week ' + fmtDate(monday) + ' - ' + fmtDate(friday) + ' (Mon-Fri)',
        records: records,
        totals: {
          seconds: totalSeconds,
          miles: totalMiles,
          gain: totalGain,
          loss: totalLoss,
        },
      };
    });
  }

  function fetchActivities() {
    return fetch('/api/activities')
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to fetch activities');
        return res.json();
      })
      .then(function (activities) {
        renderTable(activities);
      });
  }

  function importFromWatch() {
    if (!importBtn || !watchPathEl || !statusEl) return;
    importBtn.disabled = true;
    statusEl.textContent = 'Importing from watch...';

    fetch('/api/import-watch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ watch_path: watchPathEl.value.trim() }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data.ok) {
          throw new Error(result.data.error || 'Import failed');
        }
        var plansCompleted = Number(result.data.plans_marked_completed || 0);
        statusEl.textContent =
          'Import complete: ' + result.data.imported + ' new, ' + result.data.skipped +
          ' skipped (' + result.data.total_files + ' files scanned).' +
          (plansCompleted > 0 ? (' Planned workouts marked complete: ' + plansCompleted + '.') : '');
        return fetchActivities();
      })
      .catch(function (err) {
        statusEl.textContent = 'Error: ' + err.message;
      })
      .finally(function () {
        importBtn.disabled = false;
      });
  }

  if (importBtn) importBtn.addEventListener('click', importFromWatch);
  fetchActivities().catch(function (err) {
    if (statusEl) statusEl.textContent = 'Error loading data: ' + err.message;
  });
})();
