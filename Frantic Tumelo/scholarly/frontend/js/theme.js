/* Theme toggle — persists to localStorage */
(function () {
  const saved = localStorage.getItem('scholarly_theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
})();

function initThemeToggle(btnId) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('scholarly_theme', next);
  });
}
