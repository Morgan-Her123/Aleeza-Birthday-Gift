(function () {
  var form = document.getElementById('planForm');
  var statusEl = document.getElementById('planStatus');
  var tableBody = document.querySelector('#planTable tbody');
  var todayPlans = document.getElementById('todayPlans');
  var calendarGrid = document.getElementById('calendarGrid');
  var monthLabel = document.getElementById('monthLabel');
  var selectedDateTitle = document.getElementById('selectedDateTitle');
  var selectedDateDetails = document.getElementById('selectedDateDetails');
  var prevMonth = document.getElementById('prevMonth');
  var nextMonth = document.getElementById('nextMonth');

  var planDate = document.getElementById('planDate');
  var planPeriod = document.getElementById('planPeriod');
  var planTitle = document.getElementById('planTitle');
  var planLabel = document.getElementById('planLabel');
  var planDistance = document.getElementById('planDistance');
  var planDuration = document.getElementById('planDuration');
  var planReminder = document.getElementById('planReminder');
  var planNotes = document.getElementById('planNotes');
  var savePlanBtn = document.getElementById('savePlanBtn');
  var cancelEditBtn = document.getElementById('cancelEditBtn');
  var raceForm = document.getElementById('raceForm');
  var raceStatus = document.getElementById('raceStatus');
  var raceDate = document.getElementById('raceDate');
  var raceName = document.getElementById('raceName');
  var raceNotes = document.getElementById('raceNotes');
  var raceTableBody = document.querySelector('#raceTable tbody');

  var plans = [];
  var races = [];
  var currentMonth = new Date();
  currentMonth.setDate(1);
  var selectedDateKey = isoDate(new Date());
  var editingPlanId = null;

  function defaultReminderForPeriod(period) {
    return period === 'Afternoon' ? '16:30' : '07:00';
  }

  function isoDate(d) {
    var yy = d.getFullYear();
    var mm = String(d.getMonth() + 1).padStart(2, '0');
    var dd = String(d.getDate()).padStart(2, '0');
    return yy + '-' + mm + '-' + dd;
  }

  function shortDateLabel(d) {
    return (d.getMonth() + 1) + '/' + d.getDate();
  }

  function fmt(v, digits) {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return '-';
    return Number(v).toFixed(digits == null ? 1 : digits);
  }

  function parseNumberLike(raw) {
    if (raw === null || raw === undefined) return '';
    var cleaned = String(raw).trim().replace(',', '.').replace(/[^0-9.\-]/g, '');
    return cleaned;
  }

  function parseApiResponse(res) {
    return res.text().then(function (text) {
      var body = null;
      if (text) {
        try {
          body = JSON.parse(text);
        } catch (err) {
          body = { ok: false, error: 'Server returned non-JSON response (' + res.status + ')' };
        }
      } else {
        body = {};
      }
      return { ok: res.ok, status: res.status, body: body };
    });
  }

  function byDateMap(items) {
    var map = new Map();
    items.forEach(function (p) {
      var key = p.plan_date;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(p);
    });
    return map;
  }

  function isCompletedPlan(p) {
    return Number(p && p.completed ? p.completed : 0) === 1;
  }

  function completedLabel(completed) {
    return completed ? '<span class="check-mark">&#10003;</span> Completed' : 'Planned';
  }

  function syncDayKeyForMonth(year, monthIndex) {
    var now = new Date();
    var currentMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    var shownMonthStart = new Date(year, monthIndex, 1);
    if (shownMonthStart < currentMonthStart) return null;
    var maxDay = new Date(year, monthIndex + 1, 0).getDate();
    var day = Math.min(now.getDate(), maxDay);
    return isoDate(new Date(year, monthIndex, day));
  }

  function renderSelectedDateDetails() {
    if (!selectedDateTitle || !selectedDateDetails) return;
    selectedDateTitle.textContent = 'Workout Details - ' + selectedDateKey;
    var items = plans.filter(function (p) { return p.plan_date === selectedDateKey; });
    if (!items.length) {
      selectedDateDetails.innerHTML = '<div class="card"><div class="k">' + selectedDateKey + '</div><div class="v">No workout planned</div></div>';
      return;
    }
    selectedDateDetails.innerHTML = items.map(function (p) {
      var completed = isCompletedPlan(p);
      var statusText = completedLabel(completed);
      return (
        '<div class="card">' +
          '<div class="k">' + p.plan_date + ' • ' + (p.session_period || 'Morning') + ' @ ' + (p.reminder_time || '-') + '</div>' +
          '<div class="v">' + p.title + '</div>' +
          (p.workout_label ? ('<div class="k">Label: ' + p.workout_label + '</div>') : '') +
          '<div class="k">' +
            'Distance: ' + (p.distance_miles == null ? '-' : (fmt(p.distance_miles, 2) + ' mi')) + ' | ' +
            'Duration: ' + (p.duration_min == null ? '-' : (fmt(p.duration_min, 0) + ' min')) +
          '</div>' +
          '<div class="k">Status: ' + statusText + '</div>' +
          (p.notes ? '<div class="k" style="margin-top:6px;">Notes: ' + p.notes + '</div>' : '') +
          '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">' +
            '<button type="button" class="edit-plan-btn" data-id="' + p.id + '">Edit Workout</button>' +
            '<button type="button" class="delete-plan-btn delete-plan-card-btn" data-id="' + p.id + '">Delete Workout</button>' +
          '</div>' +
        '</div>'
      );
    }).join('');
    bindActionButtons();
  }

  function renderToday() {
    if (!todayPlans) return;
    var key = isoDate(new Date());
    var todays = plans.filter(function (p) { return p.plan_date === key; });
    if (!todays.length) {
      todayPlans.innerHTML = '<div class="card"><div class="k">Today</div><div class="v">No workout planned</div></div>';
      return;
    }
    todayPlans.innerHTML = todays.map(function (p) {
      var completed = isCompletedPlan(p);
      var statusText = completedLabel(completed);
      return '<div class="card">' +
        '<div class="k">' + p.plan_date + ' • ' + (p.session_period || 'Morning') + ' @ ' + (p.reminder_time || '07:00') + '</div>' +
        '<div class="v">' + p.title + '</div>' +
        (p.workout_label ? ('<div class="k">Label: ' + p.workout_label + '</div>') : '') +
        '<div class="k">' +
          (p.distance_miles == null ? '' : (fmt(p.distance_miles, 2) + ' mi ')) +
          (p.duration_min == null ? '' : (fmt(p.duration_min, 0) + ' min')) +
        '</div>' +
        '<div class="k">Status: ' + statusText + '</div>' +
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">' +
          '<button type="button" class="edit-plan-btn" data-id="' + p.id + '">Edit Workout</button>' +
          '<button type="button" class="delete-plan-btn delete-plan-card-btn" data-id="' + p.id + '">Delete Workout</button>' +
        '</div>' +
      '</div>';
    }).join('');
    bindActionButtons();
  }

  function bindActionButtons() {
    Array.prototype.forEach.call(document.querySelectorAll('.edit-plan-btn'), function (btn) {
      if (btn.dataset.bound === '1') return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-id');
        if (!id) return;
        startEditPlan(id);
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll('.delete-plan-btn'), function (btn) {
      if (btn.dataset.bound === '1') return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-id');
        if (!id) return;
        deletePlan(id);
      });
    });
  }

  function renderTable() {
    if (!tableBody) return;
    tableBody.innerHTML = '';
    var sorted = plans.slice().sort(function (a, b) {
      var ak = (a.plan_date || '') + ' ' + (a.reminder_time || '00:00') + ' ' + String(a.id || 0).padStart(9, '0');
      var bk = (b.plan_date || '') + ' ' + (b.reminder_time || '00:00') + ' ' + String(b.id || 0).padStart(9, '0');
      if (ak > bk) return -1;
      if (ak < bk) return 1;
      return 0;
    });
    sorted.forEach(function (p) {
      var completed = isCompletedPlan(p);
      var tr = document.createElement('tr');
      if (completed) tr.className = 'plan-complete-row';
      tr.innerHTML =
        '<td>' + p.plan_date + '</td>' +
        '<td>' + (p.session_period || 'Morning') + '</td>' +
        '<td>' + (p.workout_label || '-') + '</td>' +
        '<td>' + p.title + '</td>' +
        '<td>' + (p.distance_miles == null ? '-' : fmt(p.distance_miles, 2)) + '</td>' +
        '<td>' + (p.duration_min == null ? '-' : fmt(p.duration_min, 0)) + '</td>' +
        '<td>' + (p.reminder_time || '-') + '</td>' +
        '<td>' + completedLabel(completed) + '</td>' +
        '<td>' +
          '<button type="button" class="edit-plan-btn" data-id="' + p.id + '">Edit</button> ' +
          '<button type="button" class="delete-plan-btn" data-id="' + p.id + '">Delete</button>' +
        '</td>';
      tableBody.appendChild(tr);
    });

    bindActionButtons();
  }

  function setEditMode(editing) {
    if (savePlanBtn) {
      savePlanBtn.textContent = editing ? 'Update Workout Plan' : 'Save Workout Plan';
    }
    if (cancelEditBtn) {
      cancelEditBtn.style.display = editing ? '' : 'none';
    }
  }

  function startEditPlan(id) {
    var plan = plans.find(function (p) { return String(p.id) === String(id); });
    if (!plan) return;
    editingPlanId = plan.id;
    if (planDate) planDate.value = plan.plan_date || '';
    if (planPeriod) planPeriod.value = plan.session_period || 'Morning';
    if (planTitle) planTitle.value = plan.title || '';
    if (planLabel) planLabel.value = plan.workout_label || '';
    if (planDistance) planDistance.value = (plan.distance_miles == null ? '' : String(plan.distance_miles));
    if (planDuration) planDuration.value = (plan.duration_min == null ? '' : String(plan.duration_min));
    if (planReminder) planReminder.value = plan.reminder_time || defaultReminderForPeriod(plan.session_period || 'Morning');
    if (planNotes) planNotes.value = plan.notes || '';
    selectedDateKey = plan.plan_date || selectedDateKey;
    setEditMode(true);
    renderCalendar();
    renderSelectedDateDetails();
    if (planTitle) planTitle.focus();
    statusEl.textContent = 'Editing workout #' + plan.id + '. Update fields then click Update Workout Plan.';
  }

  function stopEditMode() {
    editingPlanId = null;
    setEditMode(false);
    if (form) form.reset();
    if (planDate) planDate.value = isoDate(new Date());
    if (planPeriod) planPeriod.value = 'Morning';
    if (planLabel) planLabel.value = '';
    if (planReminder) planReminder.value = '07:00';
  }

  function renderCalendar() {
    if (!calendarGrid || !monthLabel) return;
    calendarGrid.innerHTML = '';
    var monthMap = byDateMap(plans);
    monthLabel.textContent = currentMonth.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

    var headers = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    headers.forEach(function (h) {
      var head = document.createElement('div');
      head.className = 'calendar-dow';
      head.textContent = h;
      calendarGrid.appendChild(head);
    });

    var first = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
    var firstDay = (first.getDay() + 6) % 7;
    var daysInMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0).getDate();
    var todayKey = isoDate(new Date());
    var syncDayKey = syncDayKeyForMonth(currentMonth.getFullYear(), currentMonth.getMonth());
    var syncPlaced = false;

    for (var i = 0; i < firstDay; i += 1) {
      var blank = document.createElement('div');
      blank.className = 'calendar-cell muted';
      calendarGrid.appendChild(blank);
    }

    for (var d = 1; d <= daysInMonth; d += 1) {
      var dateObj = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), d);
      var key = isoDate(dateObj);
      var items = monthMap.get(key) || [];
      var hasCompleted = items.some(function (p) { return isCompletedPlan(p); });
      var todayBadge = key === todayKey ? '<span class="today-pill">Today</span>' : '';
      var syncBadge = '';
      if (!syncPlaced && syncDayKey && key === syncDayKey) {
        syncBadge = '<span class="sync-pill">Sync Garmin</span>';
        syncPlaced = true;
      }
      var preview = items.slice(0, 2).map(function (p) {
        var periodTag = (p.session_period || 'Morning') === 'Afternoon' ? 'PM' : 'AM';
        var doneTag = isCompletedPlan(p) ? '[\u2713] ' : '';
        var labelTag = p.workout_label ? ('{' + p.workout_label + '} ') : '';
        return '<div class="day-workout">[' + periodTag + '] ' + doneTag + labelTag + p.title + '</div>';
      }).join('');
      var more = items.length > 2 ? '<div class="day-more">+' + (items.length - 2) + ' more</div>' : '';
      var cell = document.createElement('button');
      cell.type = 'button';
      cell.className =
        'calendar-cell day' +
        (key === todayKey ? ' today' : '') +
        (hasCompleted ? ' plan-day-complete' : '') +
        (key === selectedDateKey ? ' selected-day' : '');
      cell.innerHTML =
        '<div class="day-head"><div class="day-number">' + shortDateLabel(dateObj) + '</div><div class="day-badges">' + todayBadge + syncBadge + '</div></div>' +
        '<div class="day-workouts">' +
        (items.length ? (preview + more) : '<div class="day-count">No workout</div>') +
        '</div>';
      cell.addEventListener('click', function (picked) {
        return function () {
          selectedDateKey = picked;
          if (planDate) planDate.value = picked;
          renderCalendar();
          renderSelectedDateDetails();
          if (planTitle) planTitle.focus();
        };
      }(key));
      calendarGrid.appendChild(cell);
    }
  }

  function loadPlans() {
    return fetch('/api/training-plans')
      .then(parseApiResponse)
      .then(function (result) {
        if (!result.ok) throw new Error((result.body && result.body.error) || 'Failed to load plans');
        var data = result.body;
        if (!Array.isArray(data)) throw new Error('Invalid plans response');
        plans = data || [];
        renderTable();
        renderToday();
        renderCalendar();
        renderSelectedDateDetails();
      });
  }

  function renderRaceTable() {
    if (!raceTableBody) return;
    raceTableBody.innerHTML = '';
    var sorted = races.slice().sort(function (a, b) {
      var ak = (a.race_date || '') + ' ' + String(a.id || 0).padStart(9, '0');
      var bk = (b.race_date || '') + ' ' + String(b.id || 0).padStart(9, '0');
      if (ak < bk) return -1;
      if (ak > bk) return 1;
      return 0;
    });
    sorted.forEach(function (r) {
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + (r.race_date || '-') + '</td>' +
        '<td>' + (r.race_name || '-') + '</td>' +
        '<td>' + (r.notes || '-') + '</td>' +
        '<td><button type="button" class="delete-race-btn" data-id="' + r.id + '">Delete</button></td>';
      raceTableBody.appendChild(tr);
    });

    Array.prototype.forEach.call(document.querySelectorAll('.delete-race-btn'), function (btn) {
      if (btn.dataset.bound === '1') return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-id');
        if (!id) return;
        deleteRace(id);
      });
    });
  }

  function loadRaces() {
    return fetch('/api/races')
      .then(parseApiResponse)
      .then(function (result) {
        if (!result.ok) throw new Error((result.body && result.body.error) || 'Failed to load races');
        var data = result.body;
        if (!Array.isArray(data)) throw new Error('Invalid races response');
        races = data || [];
        renderRaceTable();
      });
  }

  function saveRace(evt) {
    evt.preventDefault();
    if (!raceDate || !raceName || !raceStatus) return;
    raceStatus.textContent = 'Saving race...';
    fetch('/api/races', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        race_date: raceDate.value.trim(),
        race_name: raceName.value.trim(),
        notes: raceNotes ? raceNotes.value.trim() : ''
      })
    })
      .then(parseApiResponse)
      .then(function (result) {
        if (!result.ok || !result.body.ok) throw new Error(result.body.error || 'Save failed');
        raceStatus.textContent = 'Race added.';
        if (raceForm) raceForm.reset();
        if (raceDate) raceDate.value = isoDate(new Date());
        return loadRaces();
      })
      .catch(function (err) {
        raceStatus.textContent = 'Error: ' + err.message;
      });
  }

  function deleteRace(id) {
    if (!raceStatus) return;
    raceStatus.textContent = 'Deleting race...';
    fetch('/api/races/' + id, { method: 'DELETE' })
      .then(function (res) {
        if (!res.ok) throw new Error('Delete failed');
        raceStatus.textContent = 'Race deleted.';
        return loadRaces();
      })
      .catch(function (err) {
        raceStatus.textContent = 'Error: ' + err.message;
      });
  }

  function savePlan(evt) {
    evt.preventDefault();
    if (!form) return;
    var distanceVal = parseNumberLike(planDistance.value);
    var durationVal = parseNumberLike(planDuration.value);
    var payload = {
      plan_date: planDate.value,
      session_period: (planPeriod && planPeriod.value) ? planPeriod.value : 'Morning',
      title: planTitle.value.trim(),
      workout_label: planLabel ? planLabel.value.trim() : '',
      distance_miles: distanceVal,
      duration_min: durationVal,
      reminder_time: planReminder.value || '07:00',
      notes: planNotes.value.trim()
    };
    var isEditing = editingPlanId !== null;
    statusEl.textContent = isEditing ? 'Updating workout plan...' : 'Saving workout plan...';
    var path = isEditing ? ('/api/training-plans/' + editingPlanId) : '/api/training-plans';
    var method = isEditing ? 'PUT' : 'POST';
    fetch(path, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(parseApiResponse)
      .then(function (result) {
        if (!result.ok || !result.body.ok) throw new Error(result.body.error || 'Save failed');
        statusEl.textContent = isEditing ? 'Workout plan updated.' : 'Workout plan saved.';
        selectedDateKey = payload.plan_date;
        stopEditMode();
        return loadPlans();
      })
      .catch(function (err) {
        statusEl.textContent = 'Error: ' + err.message;
      });
  }

  function deletePlan(id) {
    statusEl.textContent = 'Deleting workout...';
    fetch('/api/training-plans/' + id, { method: 'DELETE' })
      .then(function (res) {
        if (!res.ok) throw new Error('Delete failed');
        if (editingPlanId !== null && String(editingPlanId) === String(id)) {
          stopEditMode();
        }
        statusEl.textContent = 'Workout deleted.';
        return loadPlans();
      })
      .catch(function (err) {
        statusEl.textContent = 'Error: ' + err.message;
      });
  }

  if (prevMonth) {
    prevMonth.addEventListener('click', function () {
      currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1);
      renderCalendar();
    });
  }
  if (nextMonth) {
    nextMonth.addEventListener('click', function () {
      currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1);
      renderCalendar();
    });
  }

  if (planPeriod && planReminder) {
    planPeriod.addEventListener('change', function () {
      var nextDefault = defaultReminderForPeriod(planPeriod.value || 'Morning');
      if (!planReminder.value || planReminder.value === '07:00' || planReminder.value === '16:30') {
        planReminder.value = nextDefault;
      }
    });
  }

  if (planDate) planDate.value = isoDate(new Date());
  if (raceDate) raceDate.value = isoDate(new Date());
  if (raceForm) {
    raceForm.addEventListener('submit', saveRace);
  }
  if (cancelEditBtn) {
    cancelEditBtn.addEventListener('click', function () {
      stopEditMode();
      statusEl.textContent = 'Edit cancelled.';
      renderCalendar();
      renderSelectedDateDetails();
    });
  }
  setEditMode(false);
  if (form) form.addEventListener('submit', savePlan);
  loadPlans().catch(function (err) {
    statusEl.textContent = 'Error: ' + err.message;
  });
  loadRaces().catch(function (err) {
    if (raceStatus) raceStatus.textContent = 'Error: ' + err.message;
  });
})();
