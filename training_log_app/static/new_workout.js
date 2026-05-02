(function () {
  var form = document.getElementById('workoutForm');
  var status = document.getElementById('formStatus');

  function toIsoLocal(value) {
    if (!value) return '';
    return new Date(value).toISOString();
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var data = new FormData(form);
    var payload = Object.fromEntries(data.entries());
    payload.start_time = toIsoLocal(payload.start_time);

    fetch('/api/workouts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return res.json().then(function (body) { return { ok: res.ok, body: body }; });
      })
      .then(function (result) {
        if (!result.ok || !result.body.ok) throw new Error(result.body.error || 'Could not save workout');
        status.textContent = 'Workout saved. Opening detail page...';
        window.location.href = '/workouts/' + result.body.workout_id;
      })
      .catch(function (err) {
        status.textContent = err.message;
      });
  });
})();
