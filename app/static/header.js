(() => {
  const header = document.querySelector(".site-header");
  if (!header) return;

  const updateScrollState = () => {
    header.classList.toggle("is-scrolled", window.scrollY > 24);
  };

  window.addEventListener("scroll", updateScrollState, { passive: true });
  updateScrollState();
})();
