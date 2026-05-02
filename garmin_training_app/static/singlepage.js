(function () {
  const sections = {
    home: document.getElementById('section-home'),
    sessions: document.getElementById('section-sessions'),
    overall: document.getElementById('section-overall'),
  };

  function showSection(name) {
    Object.entries(sections).forEach(([key, el]) => {
      if (!el) return;
      el.classList.toggle('hidden', key !== name);
    });

    document.querySelectorAll('.side-link').forEach((link) => {
      link.classList.toggle('active', link.dataset.target === name);
    });
  }

  document.querySelectorAll('[data-target]').forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const target = el.dataset.target;
      if (target && sections[target]) {
        showSection(target);
      }
    });
  });

  showSection('home');
})();
