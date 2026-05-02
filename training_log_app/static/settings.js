(function () {
  var form = document.getElementById('settingsForm');
  var status = document.getElementById('settingsStatus');
  if (!form) return;

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var data = new FormData(form);
    var payload = Object.fromEntries(data.entries());

    fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return res.json().then(function (body) { return { ok: res.ok, body: body }; });
      })
      .then(function (result) {
        if (!result.ok || !result.body.ok) throw new Error('Could not save thresholds');
        status.textContent = 'Thresholds saved. Dashboard analytics will use the new baseline immediately.';
      })
      .catch(function (err) {
        status.textContent = err.message;
      });
  });
})();
