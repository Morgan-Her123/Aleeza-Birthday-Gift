(function () {
  var ui = window.SummitLog;
  var container = document.getElementById('weeksContainer');

  fetch('/api/calendar')
    .then(function (res) { return res.json(); })
    .then(function (data) {
      container.innerHTML = data.weeks.map(function (week) {
        return [
          '<section class="panel week-panel">',
          '<div class="section-head">',
          '<div><div class="eyebrow">' + week.label + '</div><h3>' + ui.fmt(week.distance, 1) + ' mi · ' + ui.fmt(week.duration_hours, 1) + ' h · stress ' + ui.fmt(week.stress, 1) + '</h3></div>',
          '</div>',
          '<div class="stack-list">',
          week.workouts.map(function (workout) {
            return '<a class="list-link" href="/workouts/' + workout.id + '"><strong>' + ui.fmtDate(workout.start_time) + ' · ' + workout.title + '</strong><span>' +
              workout.sport + ' · ' + ui.fmt(workout.distance_miles, 1) + ' mi · ' + workout.duration_minutes + ' min · ' + workout.pace +
              ' · ' + workout.stress_label + ' ' + ui.fmt(workout.stress_score, 1) + ' · IF ' + ui.fmt(workout.intensity_factor, 2) +
              '</span></a>';
          }).join(''),
          '</div>',
          '</section>'
        ].join('');
      }).join('');
    });
})();
