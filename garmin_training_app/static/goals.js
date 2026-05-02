(function () {
  var form = document.getElementById('goalForm');
  var statusEl = document.getElementById('goalStatus');
  var goalType = document.getElementById('goalType');
  var goalTitleWrap = document.getElementById('goalTitleWrap');
  var goalTitle = document.getElementById('goalTitle');
  var goalNotes = document.getElementById('goalNotes');

  var weeklyCompletionDate = document.getElementById('weeklyCompletionDate');
  var weeklyTargetHours = document.getElementById('weeklyTargetHours');
  var weeklyTargetMiles = document.getElementById('weeklyTargetMiles');
  var weeklyTargetGain = document.getElementById('weeklyTargetGain');
  var weeklyPercentChange = document.getElementById('weeklyPercentChange');
  var weeklyRaceGoal = document.getElementById('weeklyRaceGoal');
  var finalTargetTime = document.getElementById('finalTargetTime');
  var finalTargetEvent = document.getElementById('finalTargetEvent');
  var finalTargetDate = document.getElementById('finalTargetDate');

  var weeklyWrap = document.getElementById('weeklyWrap');
  var weeklyHoursWrap = document.getElementById('weeklyHoursWrap');
  var weeklyMilesWrap = document.getElementById('weeklyMilesWrap');
  var weeklyGainWrap = document.getElementById('weeklyGainWrap');
  var weeklyChangeWrap = document.getElementById('weeklyChangeWrap');
  var weeklyRaceWrap = document.getElementById('weeklyRaceWrap');
  var finalTimeWrap = document.getElementById('finalTimeWrap');
  var finalEventWrap = document.getElementById('finalEventWrap');
  var finalDateWrap = document.getElementById('finalDateWrap');

  var weeklyGoals = document.getElementById('weeklyGoals');
  var finalGoals = document.getElementById('finalGoals');
  var goals = [];

  function isoDate(d) {
    var yy = d.getFullYear();
    var mm = String(d.getMonth() + 1).padStart(2, '0');
    var dd = String(d.getDate()).padStart(2, '0');
    return yy + '-' + mm + '-' + dd;
  }

  function parseNumberLike(raw) {
    if (raw === null || raw === undefined) return '';
    return String(raw).trim().replace(',', '.').replace(/[^0-9.\-]/g, '');
  }

  function fmtDateForCard(iso) {
    if (!iso) return '-';
    var d = new Date(iso + 'T00:00:00');
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'numeric', day: 'numeric' });
  }

  function fmtNumber(v, unit) {
    if (v === null || v === undefined || v === '') return '-';
    var n = Number(v);
    if (Number.isNaN(n)) return '-';
    var text = (n % 1 === 0) ? String(n.toFixed(0)) : String(n.toFixed(2));
    return unit ? (text + ' ' + unit) : text;
  }

  function setTypeUI() {
    var isFinal = goalType && goalType.value === 'final';
    if (goalTitleWrap) goalTitleWrap.style.display = isFinal ? '' : 'none';
    if (weeklyWrap) weeklyWrap.style.display = isFinal ? 'none' : '';
    if (weeklyHoursWrap) weeklyHoursWrap.style.display = isFinal ? 'none' : '';
    if (weeklyMilesWrap) weeklyMilesWrap.style.display = isFinal ? 'none' : '';
    if (weeklyGainWrap) weeklyGainWrap.style.display = isFinal ? 'none' : '';
    if (weeklyChangeWrap) weeklyChangeWrap.style.display = isFinal ? 'none' : '';
    if (weeklyRaceWrap) weeklyRaceWrap.style.display = isFinal ? 'none' : '';
    if (finalTimeWrap) finalTimeWrap.style.display = isFinal ? '' : 'none';
    if (finalEventWrap) finalEventWrap.style.display = isFinal ? '' : 'none';
    if (finalDateWrap) finalDateWrap.style.display = isFinal ? '' : 'none';
  }

  function weeklyTargetLine(g) {
    var ch = (g.weekly_percent_change === null || g.weekly_percent_change === undefined || g.weekly_percent_change === '')
      ? '-'
      : (((Number(g.weekly_percent_change) > 0 ? '+' : '') + fmtNumber(g.weekly_percent_change, '%')));
    var race = g.weekly_race_goal ? g.weekly_race_goal : '-';
    return (
      'Hours: ' + fmtNumber(g.weekly_target_hours, 'h') +
      ' | Miles: ' + fmtNumber(g.weekly_target_miles, 'mi') +
      ' | Gain: ' + fmtNumber(g.weekly_target_gain_ft, 'ft') +
      ' | Change: ' + ch +
      ' | Race Goal: ' + race
    );
  }

  function finalTargetLine(g) {
    var time = g.final_target_time || '-';
    var event = g.final_target_event || '-';
    var date = fmtDateForCard(g.final_target_date);
    return 'Time: ' + time + ' | Event: ' + event + ' | Date: ' + date;
  }

  function goalCard(g) {
    var heading = g.goal_type === 'weekly'
      ? ('Complete By: ' + fmtDateForCard(g.weekly_completion_date))
      : 'Final Goal';
    var detail = g.goal_type === 'weekly' ? weeklyTargetLine(g) : finalTargetLine(g);
    var completeTxt = g.completed ? 'Accomplished' : 'In Progress';
    var completeBtn = g.completed
      ? '<button type="button" class="goal-toggle-btn" data-id="' + g.id + '" data-completed="0">Mark Incomplete</button>'
      : '<button type="button" class="goal-toggle-btn" data-id="' + g.id + '" data-completed="1">Mark Accomplished</button>';

    return (
      '<div class="card">' +
        '<div class="k">' + heading + '</div>' +
        '<div class="v">' + (g.title || '-') + '</div>' +
        '<div class="k">' + detail + '</div>' +
        '<div class="k">Status: ' + completeTxt + '</div>' +
        (g.notes ? ('<div class="k" style="margin-top:6px;">Notes: ' + g.notes + '</div>') : '') +
        '<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">' +
          completeBtn +
          '<button type="button" class="delete-goal-btn" data-id="' + g.id + '">Delete</button>' +
        '</div>' +
      '</div>'
    );
  }

  function bindGoalActions() {
    Array.prototype.forEach.call(document.querySelectorAll('.goal-toggle-btn'), function (btn) {
      if (btn.dataset.bound === '1') return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-id');
        var completed = btn.getAttribute('data-completed') === '1';
        if (!id) return;
        toggleGoalCompletion(id, completed);
      });
    });

    Array.prototype.forEach.call(document.querySelectorAll('.delete-goal-btn'), function (btn) {
      if (btn.dataset.bound === '1') return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-id');
        if (!id) return;
        deleteGoal(id);
      });
    });
  }

  function renderGoals() {
    if (!weeklyGoals || !finalGoals) return;
    var weekly = goals.filter(function (g) { return g.goal_type === 'weekly'; });
    var finals = goals.filter(function (g) { return g.goal_type === 'final'; });

    weeklyGoals.innerHTML = weekly.length
      ? weekly.map(goalCard).join('')
      : '<div class="card"><div class="k">Weekly Goals</div><div class="v">No weekly goals yet</div></div>';

    finalGoals.innerHTML = finals.length
      ? finals.map(goalCard).join('')
      : '<div class="card"><div class="k">Final Goal</div><div class="v">No final goal yet</div></div>';

    bindGoalActions();
  }

  function loadGoals() {
    return fetch('/api/goals')
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to load goals');
        return res.json();
      })
      .then(function (data) {
        goals = data || [];
        renderGoals();
      });
  }

  function resetForm() {
    if (form) form.reset();
    if (goalType) goalType.value = 'weekly';
    if (weeklyCompletionDate) weeklyCompletionDate.value = isoDate(new Date());
    setTypeUI();
  }

  function saveGoal(evt) {
    evt.preventDefault();
    if (!goalType) return;

    var payload = {
      goal_type: goalType.value,
      title: '',
      notes: goalNotes ? goalNotes.value.trim() : ''
    };

    if (payload.goal_type === 'weekly') {
      payload.weekly_completion_date = weeklyCompletionDate ? weeklyCompletionDate.value.trim() : '';
      payload.weekly_target_hours = parseNumberLike(weeklyTargetHours ? weeklyTargetHours.value : '');
      payload.weekly_target_miles = parseNumberLike(weeklyTargetMiles ? weeklyTargetMiles.value : '');
      payload.weekly_target_gain_ft = parseNumberLike(weeklyTargetGain ? weeklyTargetGain.value : '');
      payload.weekly_percent_change = parseNumberLike(weeklyPercentChange ? weeklyPercentChange.value : '');
      payload.weekly_race_goal = weeklyRaceGoal ? weeklyRaceGoal.value.trim() : '';
      payload.title = payload.weekly_completion_date
        ? ('Weekly Goal ' + payload.weekly_completion_date)
        : 'Weekly Goal';
    } else {
      payload.title = goalTitle ? goalTitle.value.trim() : '';
      payload.final_target_time = finalTargetTime ? finalTargetTime.value.trim() : '';
      payload.final_target_event = finalTargetEvent ? finalTargetEvent.value.trim() : '';
      payload.final_target_date = finalTargetDate ? finalTargetDate.value.trim() : '';
    }

    statusEl.textContent = 'Saving goal...';
    fetch('/api/goals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return res.json().then(function (body) { return { ok: res.ok, body: body }; });
      })
      .then(function (result) {
        if (!result.ok || !result.body.ok) throw new Error(result.body.error || 'Save failed');
        statusEl.textContent = 'Goal saved.';
        resetForm();
        return loadGoals();
      })
      .catch(function (err) {
        statusEl.textContent = 'Error: ' + err.message;
      });
  }

  function toggleGoalCompletion(goalId, completed) {
    statusEl.textContent = completed
      ? 'Marking goal accomplished and sending watch notification...'
      : 'Marking goal incomplete...';
    fetch('/api/goals/' + goalId + '/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        completed: completed,
        send_watch_notification: completed
      })
    })
      .then(function (res) {
        return res.json().then(function (body) { return { ok: res.ok, body: body }; });
      })
      .then(function (result) {
        if (!result.ok || !result.body.ok) throw new Error(result.body.error || 'Update failed');
        var watch = result.body.watch_notification || {};
        if (completed) {
          statusEl.textContent = watch.sent
            ? 'Goal accomplished. Notification sent to watch.'
            : ('Goal accomplished. ' + (watch.message || 'Watch notification not sent.'));
        } else {
          statusEl.textContent = 'Goal marked incomplete.';
        }
        return loadGoals();
      })
      .catch(function (err) {
        statusEl.textContent = 'Error: ' + err.message;
      });
  }

  function deleteGoal(goalId) {
    statusEl.textContent = 'Deleting goal...';
    fetch('/api/goals/' + goalId, { method: 'DELETE' })
      .then(function (res) {
        if (!res.ok) throw new Error('Delete failed');
        statusEl.textContent = 'Goal deleted.';
        return loadGoals();
      })
      .catch(function (err) {
        statusEl.textContent = 'Error: ' + err.message;
      });
  }

  if (goalType) {
    goalType.addEventListener('change', setTypeUI);
  }
  if (weeklyCompletionDate) weeklyCompletionDate.value = isoDate(new Date());
  setTypeUI();
  if (form) form.addEventListener('submit', saveGoal);
  loadGoals().catch(function (err) {
    statusEl.textContent = 'Error: ' + err.message;
  });
})();
