(function () {
  var ui = window.SummitLog;

  function metric(label, value, sub) {
    return '<article class="metric-card"><div class="k">' + label + '</div><div class="v">' + value + '</div><div class="subtle dark">' + sub + '</div></article>';
  }

  function card(label, value) {
    return '<article class="card"><div class="k">' + label + '</div><div class="v">' + value + '</div></article>';
  }

  fetch('/api/dashboard')
    .then(function (res) { return res.json(); })
    .then(function (data) {
      var headline = data.headline;
      document.getElementById('heroTitle').textContent =
        'Fitness ' + ui.fmt(headline.ctl, 1) + ', fatigue ' + ui.fmt(headline.atl, 1) + ', form ' + ui.fmt(headline.tsb, 1) + '.';
      document.getElementById('heroText').textContent =
        'Current week stress is ' + ui.fmt(headline.current_week_stress, 1) +
        ' with ' + ui.fmt(headline.current_week_distance, 1) + ' miles on the board.';

      document.getElementById('headlineMetrics').innerHTML = [
        metric('This Week Stress', ui.fmt(headline.current_week_stress, 1), ui.fmt(headline.stress_delta, 1) + ' vs last week'),
        metric('Fitness (CTL)', ui.fmt(headline.ctl, 1), '42-day load'),
        metric('Fatigue (ATL)', ui.fmt(headline.atl, 1), '7-day load'),
        metric('Form (TSB)', ui.fmt(headline.tsb, 1), 'fitness - fatigue')
      ].join('');

      document.getElementById('totalCards').innerHTML = [
        card('Sessions', String(data.totals.sessions)),
        card('Total Distance', ui.fmt(data.totals.distance, 1) + ' mi'),
        card('Total Stress', ui.fmt(data.totals.stress, 1)),
        card('Last 4 Weeks', ui.fmt(data.totals.last_4_distance, 1) + ' mi'),
        card('Last 4 Hours', ui.fmt(data.totals.last_4_hours, 1) + ' h'),
        card('Last 4 Stress', ui.fmt(data.totals.last_4_stress, 1))
      ].join('');

      document.getElementById('settingsCards').innerHTML = [
        '<div class="list-item"><strong>Athlete</strong><span>' + data.settings.athlete_name + '</span></div>',
        '<div class="list-item"><strong>FTP</strong><span>' + data.settings.ftp + ' W</span></div>',
        '<div class="list-item"><strong>Threshold Pace</strong><span>' + data.settings.threshold_pace_text + '</span></div>',
        '<div class="list-item"><strong>Threshold HR</strong><span>' + data.settings.threshold_hr + ' bpm</span></div>',
        '<div class="list-item"><strong>Swim Threshold</strong><span>' + data.settings.swim_threshold_text + '</span></div>',
        '<a class="list-link" href="/settings"><strong>Edit thresholds</strong><span>Update the analyzer baseline</span></a>'
      ].join('');

      document.getElementById('sportMix').innerHTML = data.sport_mix.map(function (item) {
        return '<div class="list-item"><strong>' + item.sport + '</strong><span>' + item.count + ' sessions</span></div>';
      }).join('');

      document.getElementById('recentWorkouts').innerHTML = data.recent.map(function (item) {
        return '<a class="list-link" href="/workouts/' + item.id + '"><strong>' + item.title + '</strong><span>' +
          item.sport + ' · ' + ui.fmt(item.distance_miles, 1) + ' mi · ' + item.pace + ' · ' +
          item.stress_label + ' ' + ui.fmt(item.stress_score, 1) + ' · IF ' + ui.fmt(item.intensity_factor, 2) +
          '</span></a>';
      }).join('');

      ui.drawLineChart(
        document.getElementById('weeklyChart'),
        [
          { color: '#e76f51', values: data.weekly.map(function (row) { return row.stress; }) },
          { color: '#2a9d8f', values: data.weekly.map(function (row) { return row.distance; }) }
        ],
        data.weekly.map(function (row) { return row.week_key.slice(5); })
      );

      ui.drawLineChart(
        document.getElementById('fitnessChart'),
        [
          { color: '#2a9d8f', values: data.fitness.map(function (row) { return row.ctl; }) },
          { color: '#e76f51', values: data.fitness.map(function (row) { return row.atl; }) },
          { color: '#e9c46a', values: data.fitness.map(function (row) { return row.tsb; }) }
        ],
        data.fitness.map(function (row) { return row.date.slice(5); })
      );
    });
})();
