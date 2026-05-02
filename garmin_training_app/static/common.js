(function () {
  const menuBtn = document.getElementById('menuBtn');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');

  function setDrawer(open) {
    if (!sidebar || !overlay) return;
    sidebar.classList.toggle('open', open);
    overlay.classList.toggle('show', open);
  }

  if (menuBtn) {
    menuBtn.addEventListener('click', function () {
      setDrawer(true);
    });
  }

  if (overlay) {
    overlay.addEventListener('click', function () {
      setDrawer(false);
    });
  }
})();
